"""Fast, non-autoregressive claim scoring with LAYA.

Replaces the slow Ollama LLM entailment call with a single-forward-pass
encoder model (~35 ms on GPU, ~200-400 ms on CPU) that outputs calibrated
probabilities trained with reinforcement learning against strictly proper
scoring rules (Brier / log score).

The scorer produces the same ``ValidationResult`` the rest of the pipeline
consumes, so ``trust_engine.py`` and ``bridge.py`` need zero changes.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Sequence

from .claim_decomposer import Claim
from .evidence_mapper import ClaimEvidence, Evidence

# ── lazy import so ``import verification`` doesn't pay torch's startup cost ──
_router_lock = threading.Lock()
_router_instance = None

logger = logging.getLogger(__name__)


class LayaScorerError(RuntimeError):
    """LAYA prediction failed."""


@dataclass(frozen=True)
class LayaScoreResult:
    """Rich output from a single LAYA forward pass on one claim."""

    verdict: str                 # SUPPORTED | CONTRADICTED | UNCERTAIN
    verdict_confidence: float    # calibrated probability on the chosen label
    support_probability: float   # calibrated P(supported) from noul head
    support_strength: int        # 0-4 ordinal scale
    low_confidence: bool         # True when below the min_confidence gate


# ── LAYA question definitions ────────────────────────────────────────────────

_VERDICT_QUESTION = {
    "type": "choice",
    "instructions": (
        "Based only on the evidence provided, classify whether the claim "
        "is supported, contradicted, or uncertain."
    ),
    "criteria": {
        "supported": (
            "The evidence directly confirms or sufficiently entails the claim."
        ),
        "contradicted": (
            "The evidence directly conflicts with or disproves the claim."
        ),
        "uncertain": (
            "The evidence is insufficient, ambiguous, irrelevant, or "
            "conflicting without resolution."
        ),
    },
}

_SUPPORT_STRENGTH_QUESTION = {
    "type": "score",
    "instructions": "How strongly does the evidence substantiate the claim?",
    "criteria": [
        "Strongly contradicts the claim",
        "Weakly contradicts or undermines the claim",
        "Unrelated, neutral, or insufficient evidence",
        "Partially supports the claim",
        "Fully and directly supports the claim",
    ],
}

_IS_SUPPORTED_QUESTION = {
    "type": "noul",
    "instructions": "Does the evidence substantiate the claim?",
}

_QUESTIONS = {
    "verdict": _VERDICT_QUESTION,
    "support_strength": _SUPPORT_STRENGTH_QUESTION,
    "is_supported": _IS_SUPPORTED_QUESTION,
}

# ── label mapping ────────────────────────────────────────────────────────────

_LABEL_MAP = {
    "supported": "SUPPORTED",
    "contradicted": "CONTRADICTED",
    "uncertain": "UNCERTAIN",
}


def _get_router(*, device: str | None = None, preload: bool = False):
    """Return a lazily-initialised, process-wide ``laya.Router``."""
    global _router_instance
    if _router_instance is not None:
        return _router_instance
    with _router_lock:
        if _router_instance is not None:
            return _router_instance
        try:
            from laya import Router
        except ImportError as exc:
            raise LayaScorerError(
                "laya is not installed. Run: pip install laya"
            ) from exc
        logger.info("Initialising LAYA Router (first call downloads ~400 MB checkpoint)…")
        _router_instance = Router(preload=preload, device=device) if device else Router(preload=preload)
        return _router_instance


def _format_state(claim: Claim, evidence: tuple[Evidence, ...]) -> str:
    """Build the text state that LAYA's encoder reads.

    Keeps the same XML structure the Ollama validator uses so the model sees
    a clear claim / evidence boundary.
    """
    evidence_blocks = "\n".join(
        f'<evidence source_id="{item.source_id}">{item.snippet}</evidence>'
        for item in evidence
    )
    return (
        f'<claim id="{claim.id}">{claim.claim}</claim>\n'
        f"<evidence_set>\n{evidence_blocks}\n</evidence_set>"
    )


def score_claim(
    claim: Claim,
    claim_evidence: ClaimEvidence,
    *,
    device: str | None = None,
    min_confidence: float = 0.0,
) -> LayaScoreResult:
    """Score one claim against its mapped evidence in a single forward pass.

    Parameters
    ----------
    claim:
        The atomic claim to verify.
    claim_evidence:
        Evidence passages already mapped to this claim.
    device:
        PyTorch device string (``"cuda"``, ``"cpu"``, ``"mps"``).  Defaults
        to LAYA's own auto-detection.
    min_confidence:
        When the verdict confidence falls below this threshold the result is
        flagged ``low_confidence=True`` so the caller can escalate to an LLM.

    Returns
    -------
    LayaScoreResult
        Structured result with calibrated probabilities.
    """
    if claim.id != claim_evidence.claim_id:
        raise ValueError("claim.id must match claim_evidence.claim_id.")

    if not claim_evidence.evidence:
        return LayaScoreResult(
            verdict="UNCERTAIN",
            verdict_confidence=1.0,
            support_probability=0.0,
            support_strength=2,  # "neutral / insufficient"
            low_confidence=False,
        )

    router = _get_router(device=device)
    state = _format_state(claim, claim_evidence.evidence)

    try:
        result = router.predict(state, _QUESTIONS)
    except Exception as exc:
        raise LayaScorerError(f"LAYA prediction failed: {exc}") from exc

    answers = result["answers"]

    # ── verdict ──────────────────────────────────────────────────────────
    raw_verdict = answers["verdict"]["choice"]
    verdict = _LABEL_MAP.get(raw_verdict, "UNCERTAIN")
    verdict_confidence = float(answers["verdict"].get("confidence", 0.0))

    # ── support probability (calibrated noul head) ───────────────────────
    support_probability = float(answers["is_supported"].get("noul", 0.0))

    # ── support strength (ordinal 0-4) ───────────────────────────────────
    support_strength = int(answers["support_strength"].get("score", 2))

    low_confidence = verdict_confidence < min_confidence

    return LayaScoreResult(
        verdict=verdict,
        verdict_confidence=verdict_confidence,
        support_probability=support_probability,
        support_strength=support_strength,
        low_confidence=low_confidence,
    )


def score_claims(
    claims: Sequence[Claim],
    evidence: Sequence[ClaimEvidence],
    *,
    device: str | None = None,
    min_confidence: float = 0.0,
) -> list[LayaScoreResult]:
    """Score a batch of claims.  Uses ``Router.predict_batch`` when possible."""
    by_id = {item.claim_id: item for item in evidence}
    if len(by_id) != len(evidence):
        raise ValueError("Evidence mappings must have unique claim IDs.")
    missing = [claim.id for claim in claims if claim.id not in by_id]
    if missing:
        raise ValueError(f"Evidence mappings are missing claim IDs: {', '.join(missing)}")

    # ── fast path: batch forward pass ────────────────────────────────────
    router = _get_router(device=device)

    batch_claims: list[Claim] = []
    batch_evidence: list[ClaimEvidence] = []
    empty_results: dict[str, LayaScoreResult] = {}

    for claim in claims:
        ce = by_id[claim.id]
        if not ce.evidence:
            empty_results[claim.id] = LayaScoreResult(
                verdict="UNCERTAIN",
                verdict_confidence=1.0,
                support_probability=0.0,
                support_strength=2,
                low_confidence=False,
            )
        else:
            batch_claims.append(claim)
            batch_evidence.append(ce)

    batch_results: dict[str, LayaScoreResult] = {}
    if batch_claims:
        requests = [
            {
                "state": _format_state(c, by_id[c.id].evidence),
                "questions": _QUESTIONS,
            }
            for c in batch_claims
        ]
        try:
            raw_results = router.predict_batch(requests)
        except Exception as exc:
            raise LayaScorerError(f"LAYA batch prediction failed: {exc}") from exc

        for claim_obj, raw in zip(batch_claims, raw_results):
            answers = raw["answers"]
            raw_verdict = answers["verdict"]["choice"]
            verdict = _LABEL_MAP.get(raw_verdict, "UNCERTAIN")
            verdict_confidence = float(answers["verdict"].get("confidence", 0.0))
            support_probability = float(answers["is_supported"].get("noul", 0.0))
            support_strength = int(answers["support_strength"].get("score", 2))
            batch_results[claim_obj.id] = LayaScoreResult(
                verdict=verdict,
                verdict_confidence=verdict_confidence,
                support_probability=support_probability,
                support_strength=support_strength,
                low_confidence=verdict_confidence < min_confidence,
            )

    # ── reassemble in original order ─────────────────────────────────────
    return [
        empty_results.get(claim.id) or batch_results[claim.id]
        for claim in claims
    ]
