"""Opt-in live test. It never starts or reconfigures Simplicity."""

import os
import unittest

from verification.simplicity_client import SimplicityClient


@unittest.skipUnless(
    os.environ.get("SIMPLICITY_RUN_INTEGRATION") == "1",
    "Set SIMPLICITY_RUN_INTEGRATION=1 after starting and configuring Simplicity.",
)
class SimplicityLiveIntegrationTests(unittest.TestCase):
    def test_query_returns_normalized_answer_and_sources(self) -> None:
        client = SimplicityClient(base_url=os.environ.get("SIMPLICITY_BASE_URL", "http://127.0.0.1:3000"))
        result = client.get_answer_and_sources("Who invented the telephone?")

        self.assertIsInstance(result["answer"], str)
        self.assertTrue(result["answer"].strip())
        self.assertIsInstance(result["sources"], list)
        for source in result["sources"]:
            self.assertIsInstance(source["content"], str)
            self.assertIn("title", source)
            self.assertIn("url", source)
