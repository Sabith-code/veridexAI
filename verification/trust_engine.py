"""Deterministic, interpretable aggregation of claim-validation results.

This is a baseline trust engine. It consumes Phase 4 verdicts only; it does
not call an LLM, reinterpret snippets, or assign source-quality scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .claim_validator import ValidationResult


class TrustEngineError(ValueError):
    """Validation results or optional claim weights violate the trust contract."""


@dataclass(frozen=True)
class ClaimTrust:
    """One transparently scored claim; weight defaults to the Phase 5 baseline."""

    validation: ValidationResult
    weight: float = 1.0
    signed_score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.validation.claim_id,
            "label": self.validation.label,
            "confidence": self.validation.confidence,
            "weight": self.weight,
            "signed_score": self.signed_score,
            "rationale": self.validation.rationale,
        }


@dataclass(frozen=True)
class TrustReport:
    """Claim-transparent baseline report; numeric values are deterministic."""

    overall_trust: float | None
    signed_score: float | None
    support_rate: float | None
    contradiction_rate: float | None
    uncertainty_rate: float | None
    certainty_rate: float | None
    claim_count: int
    supported_count: int
    contradicted_count: int
    uncertain_count: int
    claims: tuple[ClaimTrust, ...]
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "overall_trust": self.overall_trust,
            "signed_score": self.signed_score,
            "support_rate": self.support_rate,
            "contradiction_rate": self.contradiction_rate,
            "uncertainty_rate": self.uncertainty_rate,
            "certainty_rate": self.certainty_rate,
            "claim_count": self.claim_count,
            "supported_count": self.supported_count,
            "contradicted_count": self.contradicted_count,
            "uncertain_count": self.uncertain_count,
            "claims": [claim.to_dict() for claim in self.claims],
            "explanation": self.explanation,
        }


def _signed_confidence(result: ValidationResult) -> float:
    if result.label == "SUPPORTED":
        return result.confidence
    if result.label == "CONTRADICTED":
        return -result.confidence
    if result.label == "UNCERTAIN":
        return 0.0
    raise TrustEngineError(f"Invalid validation label for claim {result.claim_id}: {result.label!r}.")


def _validate_results(results: Sequence[ValidationResult], weights: Mapping[str, float]) -> None:
    seen_ids: set[str] = set()
    for result in results:
        if not isinstance(result.claim_id, str) or not result.claim_id:
            raise TrustEngineError("Every validation result must have a non-empty claim_id.")
        if result.claim_id in seen_ids:
            raise TrustEngineError(f"Duplicate claim ID: {result.claim_id}.")
        seen_ids.add(result.claim_id)
        if isinstance(result.confidence, bool) or not isinstance(result.confidence, (int, float)) or not math.isfinite(result.confidence) or not 0 <= result.confidence <= 1:
            raise TrustEngineError(f"Invalid confidence for claim {result.claim_id}; expected a finite value from 0 to 1.")
        _signed_confidence(result)
    unknown_weights = set(weights) - seen_ids
    if unknown_weights:
        raise TrustEngineError(f"Weights reference unknown claim IDs: {', '.join(sorted(unknown_weights))}.")
    for claim_id, weight in weights.items():
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0:
            raise TrustEngineError(f"Invalid weight for claim {claim_id}; expected a finite value greater than 0.")


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def _explanation(supported: int, contradicted: int, uncertain: int, total: int,
                 overall_trust: float, certainty_rate: float) -> str:
    parts = [
        f"The answer contains {supported} {_plural(supported, 'claim')} supported by the supplied evidence, "
        f"{contradicted} {_plural(contradicted, 'claim')} contradicted by the supplied evidence, and "
        f"{uncertain} {_plural(uncertain, 'claim')} for which the supplied evidence is insufficient or unresolved."
    ]
    if contradicted:
        parts.append("Contradicted claims reduce the signed trust score; uncertain claims contribute neither support nor contradiction.")
    elif uncertain:
        parts.append("Uncertain claims contribute neither support nor contradiction, so they reduce evidence certainty without being treated as contradictions.")
    else:
        parts.append("All claims received an evidence-based directional verdict.")
    parts.append(
        f"The baseline overall trust is {overall_trust:.2f}; evidence certainty coverage is {certainty_rate:.2f}."
    )
    return " ".join(parts)


def compute_trust(
    validation_results: Sequence[ValidationResult], *, claim_weights: Mapping[str, float] | None = None
) -> TrustReport:
    """Compute the Phase 5 equal-weight trust baseline.

    For claim ``i``, signed score is ``+confidence`` for SUPPORTED,
    ``-confidence`` for CONTRADICTED, and ``0`` for UNCERTAIN. With weights
    ``w_i`` (all ``1`` by default), ``raw = sum(w_i * signed_i) / sum(w_i)``.
    Overall trust is ``(raw + 1) / 2``. This maps the interpretable signed
    range ``[-1, 1]`` to ``[0, 1]`` without treating uncertainty as support.
    """

    results = tuple(validation_results)
    weights = dict(claim_weights or {})
    _validate_results(results, weights)
    if not results:
        return TrustReport(
            overall_trust=None, signed_score=None, support_rate=None,
            contradiction_rate=None, uncertainty_rate=None, certainty_rate=None,
            claim_count=0, supported_count=0, contradicted_count=0, uncertain_count=0,
            claims=(),
            explanation="No validation results were supplied, so no answer-level trust score can be computed.",
        )

    claim_trusts = tuple(
        ClaimTrust(result, float(weights.get(result.claim_id, 1.0)), _signed_confidence(result))
        for result in results
    )
    total_weight = sum(item.weight for item in claim_trusts)
    raw_score = sum(item.weight * item.signed_score for item in claim_trusts) / total_weight
    overall_trust = (raw_score + 1.0) / 2.0
    supported = sum(item.validation.label == "SUPPORTED" for item in claim_trusts)
    contradicted = sum(item.validation.label == "CONTRADICTED" for item in claim_trusts)
    uncertain = sum(item.validation.label == "UNCERTAIN" for item in claim_trusts)
    certainty_rate = sum(
        item.weight * item.validation.confidence
        for item in claim_trusts
        if item.validation.label != "UNCERTAIN"
    ) / total_weight
    total = len(claim_trusts)
    return TrustReport(
        overall_trust=overall_trust,
        signed_score=raw_score,
        support_rate=supported / total,
        contradiction_rate=contradicted / total,
        uncertainty_rate=uncertain / total,
        certainty_rate=certainty_rate,
        claim_count=total,
        supported_count=supported,
        contradicted_count=contradicted,
        uncertain_count=uncertain,
        claims=claim_trusts,
        explanation=_explanation(supported, contradicted, uncertain, total, overall_trust, certainty_rate),
    )
