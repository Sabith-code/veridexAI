import unittest
from unittest.mock import patch

from verification.claim_decomposer import (
    ClaimDecompositionError,
    OllamaClaimDecomposer,
    parse_claims_response,
)


def _ollama_response(claims):
    return {"message": {"content": __import__("json").dumps({"claims": claims})}}


class ClaimDecomposerTests(unittest.TestCase):
    def test_simple_factual_sentence(self) -> None:
        with patch.object(OllamaClaimDecomposer, "_request_json", return_value=_ollama_response([
            {"claim": "The Eiffel Tower was completed in 1889."}
        ])):
            claims = OllamaClaimDecomposer().decompose_claims("The Eiffel Tower was completed in 1889.")
        self.assertEqual([claim.to_dict() for claim in claims], [
            {"id": "C1", "claim": "The Eiffel Tower was completed in 1889."}
        ])

    def test_multiple_facts_are_returned_in_order(self) -> None:
        output = [
            {"claim": "Alexander Graham Bell is credited with inventing the telephone."},
            {"claim": "Samuel Morse contributed to telegraphy."},
            {"claim": "Telegraphy preceded the telephone."},
        ]
        with patch.object(OllamaClaimDecomposer, "_request_json", return_value=_ollama_response(output)):
            claims = OllamaClaimDecomposer().decompose_claims("A paragraph with several facts.")
        self.assertEqual([claim.id for claim in claims], ["C1", "C2", "C3"])
        self.assertEqual([claim.claim for claim in claims], [item["claim"] for item in output])

    def test_sentence_with_multiple_facts_can_be_split(self) -> None:
        output = [
            {"claim": "The Eiffel Tower was completed in 1889."},
            {"claim": "The Eiffel Tower is located in Paris."},
        ]
        with patch.object(OllamaClaimDecomposer, "_request_json", return_value=_ollama_response(output)):
            claims = OllamaClaimDecomposer().decompose_claims(
                "The Eiffel Tower was completed in 1889 and is located in Paris."
            )
        self.assertEqual(len(claims), 2)

    def test_opinion_text_can_produce_no_claims(self) -> None:
        with patch.object(OllamaClaimDecomposer, "_request_json", return_value=_ollama_response([])):
            claims = OllamaClaimDecomposer().decompose_claims("I think this is the best movie ever.")
        self.assertEqual(claims, [])

    def test_empty_answer_skips_the_model_call(self) -> None:
        with patch.object(OllamaClaimDecomposer, "_request_json") as request_json:
            claims = OllamaClaimDecomposer().decompose_claims("   ")
        self.assertEqual(claims, [])
        request_json.assert_not_called()

    def test_malformed_llm_output_is_rejected(self) -> None:
        with patch.object(OllamaClaimDecomposer, "_request_json", return_value={"message": {"content": "not json"}}):
            with self.assertRaisesRegex(ClaimDecompositionError, "malformed"):
                OllamaClaimDecomposer().decompose_claims("A factual answer.")

    def test_invalid_claim_schema_is_rejected(self) -> None:
        with self.assertRaisesRegex(ClaimDecompositionError, "exactly one"):
            parse_claims_response({"claims": [{"claim": "Fact", "extra": "not allowed"}]})
