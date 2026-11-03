"""Evidence-bounded claim validation.

This module classifies only the relationship between a claim and supplied
evidence snippets. It does not retrieve information, assess source quality,
or aggregate trust.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .claim_decomposer import Claim
from .evidence_mapper import ClaimEvidence, Evidence


ValidationLabel = Literal["SUPPORTED", "CONTRADICTED", "UNCERTAIN"]
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_TIMEOUT_SECONDS = 90.0

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["label", "confidence", "cited_source_ids", "rationale"],
    "properties": {
        "label": {"type": "string", "enum": ["SUPPORTED", "CONTRADICTED", "UNCERTAIN"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "cited_source_ids": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
        "rationale": {"type": "string", "minLength": 1},
    },
}

_SYSTEM_PROMPT = """You are an evidence-bounded claim validator.

Classify ONLY the relationship between the CLAIM and the supplied EVIDENCE SNIPPETS. Never use outside knowledge, web searches, source credibility, or facts not written in the snippets.

SUPPORTED means the supplied evidence directly or sufficiently entails the claim.
CONTRADICTED means supplied evidence directly conflicts with the claim.
UNCERTAIN means the supplied evidence is insufficient, ambiguous, irrelevant, or conflicting without a supplied resolution.

Return only JSON matching the schema. `cited_source_ids` must identify the supplied evidence items used for the verdict. Explain the reasoning in `rationale`, but never reproduce, paraphrase, or generate evidence quotations. Do not claim an evidentiary relationship beyond what those snippets establish. Confidence is your non-calibrated judgment of this evidence-only classification, from 0 to 1."""


class ClaimValidationError(RuntimeError):
    """Ollama failed or returned data outside the validation contract."""


@dataclass(frozen=True)
class ValidationResult:
    claim_id: str
    claim: str
    label: ValidationLabel
    confidence: float
    evidence: tuple[Evidence, ...]
    rationale: str
    cited_source_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim": self.claim,
            "label": self.label,
            "confidence": self.confidence,
            "evidence": [item.to_dict() for item in self.evidence],
            "rationale": self.rationale,
            "cited_source_ids": list(self.cited_source_ids),
        }


def parse_validation_response(
    payload: Mapping[str, Any], claim: Claim, claim_evidence: ClaimEvidence
) -> ValidationResult:
    """Validate an LLM verdict and preserve evidence selected by source ID."""

    expected_fields = {"label", "confidence", "cited_source_ids", "rationale"}
    if set(payload) != expected_fields:
        raise ClaimValidationError("Validation output must contain exactly label, confidence, cited_source_ids, and rationale.")
    label = payload["label"]
    confidence = payload["confidence"]
    cited_source_ids = payload["cited_source_ids"]
    rationale = payload["rationale"]
    if label not in {"SUPPORTED", "CONTRADICTED", "UNCERTAIN"}:
        raise ClaimValidationError("Validation label must be SUPPORTED, CONTRADICTED, or UNCERTAIN.")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ClaimValidationError("Validation confidence must be a number from 0 to 1.")
    if not isinstance(cited_source_ids, list) or not cited_source_ids or not all(isinstance(item, str) for item in cited_source_ids):
        raise ClaimValidationError("Validation cited_source_ids must be a non-empty list of strings.")
    cited_source_ids = list(dict.fromkeys(cited_source_ids))
    if not isinstance(rationale, str) or not rationale.strip():
        raise ClaimValidationError("Validation rationale must be present.")

    by_id = {item.source_id: item for item in claim_evidence.evidence}
    if not set(cited_source_ids).issubset(by_id):
        raise ClaimValidationError("Validation cites a source not supplied as mapped evidence.")
    return ValidationResult(
        claim_id=claim.id,
        claim=claim.claim,
        label=label,
        confidence=float(confidence),
        evidence=claim_evidence.evidence,
        rationale=rationale.strip(),
        cited_source_ids=tuple(cited_source_ids),
    )


class OllamaClaimValidator:
    """Minimal local Ollama client for evidence-only claim validation."""

    def __init__(self, base_url: str | None = None, *, model: str | None = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("CLAIM_VALIDATOR_MODEL") or DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds

    def _request_json(self, body: Mapping[str, Any]) -> Mapping[str, Any]:
        request = Request(f"{self.base_url}/api/chat", data=json.dumps(body).encode("utf-8"), method="POST",
                          headers={"Accept": "application/json", "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read()
        except HTTPError as exc:
            raise ClaimValidationError(f"Ollama returned HTTP {exc.code} during claim validation.") from exc
        except URLError as exc:
            raise ClaimValidationError(f"Could not reach Ollama at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ClaimValidationError("Ollama claim validation timed out.") from exc
        try:
            decoded = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClaimValidationError("Ollama returned invalid JSON during claim validation.") from exc
        if not isinstance(decoded, Mapping):
            raise ClaimValidationError("Ollama response must be a JSON object.")
        return decoded

    def validate_claim(self, claim: Claim, claim_evidence: ClaimEvidence) -> ValidationResult:
        if claim.id != claim_evidence.claim_id:
            raise ValueError("claim.id must match claim_evidence.claim_id.")
        if not claim_evidence.evidence:
            return ValidationResult(
                claim_id=claim.id, claim=claim.claim, label="UNCERTAIN", confidence=1.0,
                evidence=(),
                rationale="No relevant evidence snippets were supplied for this claim, so the evidence cannot establish it.",
            )
        evidence_blocks = "\n".join(
            f'<evidence source_id="{item.source_id}">{item.snippet}</evidence>'
            for item in claim_evidence.evidence
        )
        response = self._request_json({
            "model": self.model, "stream": False, "format": _RESPONSE_SCHEMA,
            "options": {"temperature": 0, "num_predict": 512},
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"<claim id=\"{claim.id}\">{claim.claim}</claim>\n<evidence_set>\n{evidence_blocks}\n</evidence_set>"},
            ],
        })
        message = response.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str):
            raise ClaimValidationError("Ollama response must contain message.content as a string.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ClaimValidationError("Ollama returned malformed validation JSON.") from exc
        if not isinstance(parsed, Mapping):
            raise ClaimValidationError("Ollama validation JSON must be an object.")
        return parse_validation_response(parsed, claim, claim_evidence)

    def validate_claims(self, claims: Sequence[Claim], evidence: Sequence[ClaimEvidence]) -> list[ValidationResult]:
        by_id = {item.claim_id: item for item in evidence}
        if len(by_id) != len(evidence):
            raise ValueError("Evidence mappings must have unique claim IDs.")
        missing = [claim.id for claim in claims if claim.id not in by_id]
        if missing:
            raise ValueError(f"Evidence mappings are missing claim IDs: {', '.join(missing)}")
        return [self.validate_claim(claim, by_id[claim.id]) for claim in claims]



class LayaClaimValidator:
    """Fast claim validator using LAYA's non-autoregressive decision engine.

    Produces the same ``ValidationResult`` as ``OllamaClaimValidator`` but runs
    in ~35 ms per claim (GPU) with calibrated probabilities.  No LLM call,
    no text generation, nothing to parse.
    """

    def __init__(self, *, device: str | None = None, min_confidence: float = 0.0) -> None:
        self.device = device
        self.min_confidence = min_confidence

    def validate_claim(self, claim: Claim, claim_evidence: ClaimEvidence) -> ValidationResult:
        from .laya_scorer import score_claim

        result = score_claim(
            claim, claim_evidence,
            device=self.device,
            min_confidence=self.min_confidence,
        )
        return ValidationResult(
            claim_id=claim.id,
            claim=claim.claim,
            label=result.verdict,
            confidence=result.verdict_confidence,
            evidence=claim_evidence.evidence,
            rationale=(
                f"LAYA System 1 classifier: {result.verdict} "
                f"(calibrated confidence {result.verdict_confidence:.2f}, "
                f"support probability {result.support_probability:.2f}, "
                f"strength {result.support_strength}/4)."
            ),
            cited_source_ids=tuple(
                dict.fromkeys(item.source_id for item in claim_evidence.evidence)
            ),
        )

    def validate_claims(
        self, claims: Sequence[Claim], evidence: Sequence[ClaimEvidence]
    ) -> list[ValidationResult]:
        from .laya_scorer import score_claims

        by_id = {item.claim_id: item for item in evidence}
        if len(by_id) != len(evidence):
            raise ValueError("Evidence mappings must have unique claim IDs.")
        missing = [claim.id for claim in claims if claim.id not in by_id]
        if missing:
            raise ValueError(f"Evidence mappings are missing claim IDs: {', '.join(missing)}")

        scores = score_claims(
            claims, evidence,
            device=self.device,
            min_confidence=self.min_confidence,
        )
        results: list[ValidationResult] = []
        for claim_obj, result in zip(claims, scores):
            ce = by_id[claim_obj.id]
            results.append(ValidationResult(
                claim_id=claim_obj.id,
                claim=claim_obj.claim,
                label=result.verdict,
                confidence=result.verdict_confidence,
                evidence=ce.evidence,
                rationale=(
                    f"LAYA System 1 classifier: {result.verdict} "
                    f"(calibrated confidence {result.verdict_confidence:.2f}, "
                    f"support probability {result.support_probability:.2f}, "
                    f"strength {result.support_strength}/4)."
                ),
                cited_source_ids=tuple(
                    dict.fromkeys(item.source_id for item in ce.evidence)
                ),
            ))
        return results


class HybridClaimValidator:
    """LAYA-first with Ollama LLM fallback for low-confidence claims.

    High-confidence claims are resolved in ~35 ms by LAYA's encoder.
    Low-confidence claims are escalated to the Ollama LLM for a full
    chain-of-thought rationale.
    """

    DEFAULT_ESCALATION_THRESHOLD = 0.65

    def __init__(
        self,
        base_url: str | None = None,
        *,
        model: str | None = None,
        device: str | None = None,
        escalation_threshold: float | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.escalation_threshold = (
            escalation_threshold
            if escalation_threshold is not None
            else self.DEFAULT_ESCALATION_THRESHOLD
        )
        self._laya = LayaClaimValidator(
            device=device, min_confidence=self.escalation_threshold
        )
        self._ollama = OllamaClaimValidator(
            base_url, model=model, timeout_seconds=timeout_seconds
        )

    def validate_claim(self, claim: Claim, claim_evidence: ClaimEvidence) -> ValidationResult:
        from .laya_scorer import score_claim

        try:
            laya_result = score_claim(
                claim, claim_evidence,
                device=self._laya.device,
                min_confidence=self.escalation_threshold,
            )
            if not laya_result.low_confidence:
                return self._laya.validate_claim(claim, claim_evidence)
        except Exception:
            pass
        # Escalate to Ollama for a full rationale
        return self._ollama.validate_claim(claim, claim_evidence)

    def validate_claims(
        self, claims: Sequence[Claim], evidence: Sequence[ClaimEvidence]
    ) -> list[ValidationResult]:
        from .laya_scorer import score_claims

        by_id = {item.claim_id: item for item in evidence}
        if len(by_id) != len(evidence):
            raise ValueError("Evidence mappings must have unique claim IDs.")
        missing = [claim.id for claim in claims if claim.id not in by_id]
        if missing:
            raise ValueError(f"Evidence mappings are missing claim IDs: {', '.join(missing)}")

        try:
            scores = score_claims(
                claims, evidence,
                device=self._laya.device,
                min_confidence=self.escalation_threshold,
            )
            results: list[ValidationResult] = []
            for claim_obj, laya_result in zip(claims, scores):
                ce = by_id[claim_obj.id]
                if not laya_result.low_confidence:
                    results.append(self._laya.validate_claim(claim_obj, ce))
                else:
                    results.append(self._ollama.validate_claim(claim_obj, ce))
            return results
        except Exception:
            return self._ollama.validate_claims(claims, evidence)


_BACKENDS = {"ollama", "laya", "hybrid"}


def validate_claim(
    claim: Claim,
    evidence: ClaimEvidence,
    *,
    backend: str = "ollama",
) -> ValidationResult:
    """Validate a single claim.

    ``backend`` selects the engine: ``"ollama"`` (default, original LLM),
    ``"laya"`` (fast encoder, ~35 ms), or ``"hybrid"`` (LAYA first,
    Ollama fallback for low-confidence claims).
    """
    if backend not in _BACKENDS:
        raise ValueError(f"backend must be one of {_BACKENDS}, got {backend!r}")
    if backend == "laya":
        return LayaClaimValidator().validate_claim(claim, evidence)
    if backend == "hybrid":
        return HybridClaimValidator().validate_claim(claim, evidence)
    return OllamaClaimValidator().validate_claim(claim, evidence)


def validate_claims(
    claims: Sequence[Claim],
    evidence: Sequence[ClaimEvidence],
    *,
    backend: str = "ollama",
) -> list[ValidationResult]:
    """Validate a batch of claims.

    ``backend`` selects the engine: ``"ollama"`` (default, original LLM),
    ``"laya"`` (fast encoder, ~35 ms), or ``"hybrid"`` (LAYA first,
    Ollama fallback for low-confidence claims).
    """
    if backend not in _BACKENDS:
        raise ValueError(f"backend must be one of {_BACKENDS}, got {backend!r}")
    if backend == "laya":
        return LayaClaimValidator().validate_claims(claims, evidence)
    if backend == "hybrid":
        return HybridClaimValidator().validate_claims(claims, evidence)
    return OllamaClaimValidator().validate_claims(claims, evidence)

