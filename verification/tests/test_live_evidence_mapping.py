"""Opt-in end-to-end test: Simplicity -> claims -> evidence mapping."""

import os
import unittest

from verification.claim_decomposer import OllamaClaimDecomposer
from verification.evidence_mapper import OllamaEvidenceMapper
from verification.simplicity_client import SimplicityClient, Source


@unittest.skipUnless(
    os.environ.get("SIMPLICITY_RUN_INTEGRATION") == "1",
    "Set SIMPLICITY_RUN_INTEGRATION=1 after starting and configuring Simplicity.",
)
class LiveEvidenceMappingTests(unittest.TestCase):
    def test_answer_to_evidence_pipeline(self) -> None:
        result = SimplicityClient(
            base_url=os.environ.get("SIMPLICITY_BASE_URL", "http://127.0.0.1:3000")
        ).get_answer_and_sources("Who invented the telephone?")
        claims = OllamaClaimDecomposer().decompose_claims(result["answer"])
        mappings = OllamaEvidenceMapper().map_evidence(claims, [Source(**source) for source in result["sources"]])

        self.assertEqual([mapping.claim_id for mapping in mappings], [claim.id for claim in claims])
        for mapping in mappings:
            for evidence in mapping.evidence:
                self.assertGreaterEqual(evidence.relevance, 0)
                self.assertLessEqual(evidence.relevance, 1)
