"""Unit tests for laya_scorer.py — mocks the LAYA Router to avoid GPU/download."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from verification.claim_decomposer import Claim
from verification.claim_validator import (
    HybridClaimValidator,
    LayaClaimValidator,
    ValidationResult,
)
from verification.evidence_mapper import ClaimEvidence, Evidence
from verification.laya_scorer import (
    LayaScoreResult,
    LayaScorerError,
    _format_state,
    score_claim,
    score_claims,
)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_claim():
    return Claim(id="C1", claim="Python was created by Guido van Rossum.")


@pytest.fixture
def sample_evidence():
    return ClaimEvidence(
        claim_id="C1",
        evidence=(
            Evidence(
                source_id="S1",
                title="Wikipedia",
                url="https://en.wikipedia.org/wiki/Python",
                relevance=0.95,
                snippet="Python was created by Guido van Rossum and first released in 1991.",
            ),
        ),
    )


@pytest.fixture
def empty_evidence():
    return ClaimEvidence(claim_id="C1", evidence=())


def _mock_predict_result(verdict="supported", confidence=0.92, noul=0.88, score=4):
    """Build the dict that laya.Router.predict() returns."""
    return {
        "answers": {
            "verdict": {"choice": verdict, "confidence": confidence},
            "is_supported": {"noul": noul},
            "support_strength": {"score": score},
        },
    }


# ── _format_state ────────────────────────────────────────────────────────────

def test_format_state_includes_claim_and_evidence(sample_claim, sample_evidence):
    state = _format_state(sample_claim, sample_evidence.evidence)
    assert '<claim id="C1">' in state
    assert '<evidence source_id="S1">' in state
    assert "Guido van Rossum" in state


# ── score_claim ──────────────────────────────────────────────────────────────

@patch("verification.laya_scorer._get_router")
def test_score_claim_supported(mock_get_router, sample_claim, sample_evidence):
    router = MagicMock()
    router.predict.return_value = _mock_predict_result("supported", 0.92, 0.88, 4)
    mock_get_router.return_value = router

    result = score_claim(sample_claim, sample_evidence)

    assert isinstance(result, LayaScoreResult)
    assert result.verdict == "SUPPORTED"
    assert result.verdict_confidence == pytest.approx(0.92)
    assert result.support_probability == pytest.approx(0.88)
    assert result.support_strength == 4
    assert result.low_confidence is False


@patch("verification.laya_scorer._get_router")
def test_score_claim_contradicted(mock_get_router, sample_claim, sample_evidence):
    router = MagicMock()
    router.predict.return_value = _mock_predict_result("contradicted", 0.85, 0.12, 0)
    mock_get_router.return_value = router

    result = score_claim(sample_claim, sample_evidence)

    assert result.verdict == "CONTRADICTED"
    assert result.verdict_confidence == pytest.approx(0.85)
    assert result.support_strength == 0


@patch("verification.laya_scorer._get_router")
def test_score_claim_uncertain(mock_get_router, sample_claim, sample_evidence):
    router = MagicMock()
    router.predict.return_value = _mock_predict_result("uncertain", 0.55, 0.45, 2)
    mock_get_router.return_value = router

    result = score_claim(sample_claim, sample_evidence)

    assert result.verdict == "UNCERTAIN"
    assert result.support_strength == 2


def test_score_claim_empty_evidence(sample_claim, empty_evidence):
    """No evidence → UNCERTAIN without calling the router at all."""
    result = score_claim(sample_claim, empty_evidence)

    assert result.verdict == "UNCERTAIN"
    assert result.verdict_confidence == 1.0
    assert result.support_probability == 0.0
    assert result.support_strength == 2
    assert result.low_confidence is False


def test_score_claim_mismatched_ids(sample_evidence):
    wrong_claim = Claim(id="WRONG", claim="Something")
    with pytest.raises(ValueError, match="must match"):
        score_claim(wrong_claim, sample_evidence)


@patch("verification.laya_scorer._get_router")
def test_score_claim_low_confidence_flag(mock_get_router, sample_claim, sample_evidence):
    router = MagicMock()
    router.predict.return_value = _mock_predict_result("supported", 0.50, 0.55, 3)
    mock_get_router.return_value = router

    result = score_claim(sample_claim, sample_evidence, min_confidence=0.65)

    assert result.low_confidence is True


# ── score_claims (batch) ─────────────────────────────────────────────────────

@patch("verification.laya_scorer._get_router")
def test_score_claims_batch(mock_get_router):
    router = MagicMock()
    router.predict_batch.return_value = [
        _mock_predict_result("supported", 0.90, 0.85, 4),
        _mock_predict_result("contradicted", 0.80, 0.10, 0),
    ]
    mock_get_router.return_value = router

    claims = [
        Claim(id="C1", claim="Claim one"),
        Claim(id="C2", claim="Claim two"),
    ]
    evidence = [
        ClaimEvidence(claim_id="C1", evidence=(
            Evidence("S1", "t", "u", 0.9, "snippet one"),
        )),
        ClaimEvidence(claim_id="C2", evidence=(
            Evidence("S2", "t", "u", 0.8, "snippet two"),
        )),
    ]

    results = score_claims(claims, evidence)

    assert len(results) == 2
    assert results[0].verdict == "SUPPORTED"
    assert results[1].verdict == "CONTRADICTED"


def test_score_claims_missing_evidence():
    claims = [Claim(id="C1", claim="X")]
    evidence = [ClaimEvidence(claim_id="C99", evidence=())]
    with pytest.raises(ValueError, match="missing claim IDs"):
        score_claims(claims, evidence)


# ── LayaClaimValidator ───────────────────────────────────────────────────────

@patch("verification.laya_scorer._get_router")
def test_laya_validator_produces_validation_result(mock_get_router, sample_claim, sample_evidence):
    router = MagicMock()
    router.predict.return_value = _mock_predict_result("supported", 0.92, 0.88, 4)
    mock_get_router.return_value = router

    validator = LayaClaimValidator()
    result = validator.validate_claim(sample_claim, sample_evidence)

    assert isinstance(result, ValidationResult)
    assert result.claim_id == "C1"
    assert result.label == "SUPPORTED"
    assert result.confidence == pytest.approx(0.92)
    assert "LAYA System 1" in result.rationale
    assert result.cited_source_ids == ("S1",)


@patch("verification.laya_scorer._get_router")
def test_laya_validator_batch(mock_get_router):
    router = MagicMock()
    router.predict_batch.return_value = [
        _mock_predict_result("supported", 0.91, 0.87, 4),
    ]
    mock_get_router.return_value = router

    claims = [Claim(id="C1", claim="X")]
    evidence = [ClaimEvidence(claim_id="C1", evidence=(
        Evidence("S1", "t", "u", 0.9, "snippet"),
    ))]

    validator = LayaClaimValidator()
    results = validator.validate_claims(claims, evidence)

    assert len(results) == 1
    assert results[0].label == "SUPPORTED"


# ── HybridClaimValidator ────────────────────────────────────────────────────

@patch("verification.laya_scorer._get_router")
def test_hybrid_validator_uses_laya_when_confident(mock_get_router, sample_claim, sample_evidence):
    router = MagicMock()
    # First call from HybridClaimValidator.validate_claim -> score_claim
    # Second call from LayaClaimValidator.validate_claim -> score_claim
    router.predict.return_value = _mock_predict_result("supported", 0.90, 0.85, 4)
    mock_get_router.return_value = router

    validator = HybridClaimValidator(escalation_threshold=0.65)
    result = validator.validate_claim(sample_claim, sample_evidence)

    assert result.label == "SUPPORTED"
    assert "LAYA" in result.rationale


# ── validate_claim / validate_claims with backend ────────────────────────────

def test_validate_claim_invalid_backend():
    from verification.claim_validator import validate_claim as vc
    claim = Claim(id="C1", claim="X")
    evidence = ClaimEvidence(claim_id="C1", evidence=())
    with pytest.raises(ValueError, match="backend"):
        vc(claim, evidence, backend="invalid")


def test_validate_claims_invalid_backend():
    from verification.claim_validator import validate_claims as vcs
    with pytest.raises(ValueError, match="backend"):
        vcs([], [], backend="invalid")
