"""Programmatic integration with a running Simplicity instance.

This package owns the generator/retrieval boundary and Phase 2 claim
decomposition. Evidence mapping and verification belong to later phases.
"""

from .claim_decomposer import (
    Claim,
    ClaimDecompositionError,
    OllamaClaimDecomposer,
    decompose_claims,
)
from .claim_validator import (
    ClaimValidationError,
    HybridClaimValidator,
    LayaClaimValidator,
    OllamaClaimValidator,
    ValidationResult,
    validate_claim,
    validate_claims,
)
from .laya_scorer import (
    LayaScoreResult,
    LayaScorerError,
    score_claim,
    score_claims,
)
from .evidence_mapper import (
    ClaimEvidence,
    Evidence,
    EvidenceMappingError,
    OllamaEvidenceMapper,
    assign_source_ids,
    map_evidence,
)
from .simplicity_client import (
    AnswerAndSources,
    ModelReference,
    SimplicityAPIError,
    SimplicityClient,
    SimplicityConfigurationError,
    Source,
    normalize_search_response,
)
from .trust_engine import ClaimTrust, TrustEngineError, TrustReport, compute_trust

__all__ = [
    "AnswerAndSources",
    "Claim",
    "ClaimDecompositionError",
    "ClaimValidationError",
    "ClaimTrust",
    "ClaimEvidence",
    "Evidence",
    "EvidenceMappingError",
    "HybridClaimValidator",
    "LayaClaimValidator",
    "LayaScoreResult",
    "LayaScorerError",
    "ModelReference",
    "OllamaClaimDecomposer",
    "OllamaClaimValidator",
    "OllamaEvidenceMapper",
    "SimplicityAPIError",
    "SimplicityClient",
    "SimplicityConfigurationError",
    "Source",
    "TrustEngineError",
    "TrustReport",
    "ValidationResult",
    "assign_source_ids",
    "compute_trust",
    "decompose_claims",
    "map_evidence",
    "normalize_search_response",
    "score_claim",
    "score_claims",
    "validate_claim",
    "validate_claims",
]
