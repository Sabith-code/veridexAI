"""Opt-in full pipeline test: Simplicity -> claims -> evidence -> validation."""

import os
import unittest

from verification.claim_decomposer import OllamaClaimDecomposer
from verification.claim_validator import OllamaClaimValidator
from verification.evidence_mapper import OllamaEvidenceMapper
from verification.simplicity_client import SimplicityClient, Source


@unittest.skipUnless(os.environ.get("SIMPLICITY_RUN_INTEGRATION") == "1",
                     "Set SIMPLICITY_RUN_INTEGRATION=1 after starting and configuring Simplicity.")
class LiveClaimValidationTests(unittest.TestCase):
    def test_answer_to_validation_pipeline(self):
        result = SimplicityClient(os.environ.get("SIMPLICITY_BASE_URL", "http://127.0.0.1:3000")).get_answer_and_sources("Who invented the telephone?")
        claims = OllamaClaimDecomposer().decompose_claims(result["answer"])
        evidence = OllamaEvidenceMapper().map_evidence(claims, [Source(**source) for source in result["sources"]])
        validations = OllamaClaimValidator().validate_claims(claims, evidence)
        self.assertEqual([item.claim_id for item in validations], [claim.id for claim in claims])
        self.assertTrue(all(item.label in {"SUPPORTED", "CONTRADICTED", "UNCERTAIN"} for item in validations))
