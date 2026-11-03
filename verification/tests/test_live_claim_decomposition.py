"""Opt-in end-to-end test: Simplicity answer -> local Ollama claims."""

import os
import unittest

from verification.claim_decomposer import OllamaClaimDecomposer
from verification.simplicity_client import SimplicityClient


@unittest.skipUnless(
    os.environ.get("SIMPLICITY_RUN_INTEGRATION") == "1",
    "Set SIMPLICITY_RUN_INTEGRATION=1 after starting and configuring Simplicity.",
)
class LiveClaimDecompositionTests(unittest.TestCase):
    def test_answer_to_claims_pipeline(self) -> None:
        answer = SimplicityClient(
            base_url=os.environ.get("SIMPLICITY_BASE_URL", "http://127.0.0.1:3000")
        ).get_answer_and_sources("Who invented the telephone?")["answer"]
        claims = OllamaClaimDecomposer().decompose_claims(answer)

        self.assertIsInstance(claims, list)
        for index, claim in enumerate(claims, start=1):
            self.assertEqual(claim.id, f"C{index}")
            self.assertTrue(claim.claim.strip())
