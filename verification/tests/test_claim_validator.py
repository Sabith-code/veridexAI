import json
import unittest
from unittest.mock import patch

from verification.claim_decomposer import Claim
from verification.claim_validator import ClaimValidationError, OllamaClaimValidator, parse_validation_response
from verification.evidence_mapper import ClaimEvidence, Evidence


def _response(label="SUPPORTED", confidence=0.95, cited_source_ids=None, rationale=None):
    cited_source_ids = cited_source_ids or ["S1"]
    rationale = rationale or "The supplied evidence directly supports the claim."
    return {"message": {"content": json.dumps({"label": label, "confidence": confidence,
        "cited_source_ids": cited_source_ids, "rationale": rationale})}}


class ClaimValidatorTests(unittest.TestCase):
    def setUp(self):
        self.claim = Claim("C1", "Bell invented the telephone in 1876.")
        self.evidence = ClaimEvidence("C1", (Evidence("S1", "History", "https://example.test", 0.9,
            "Bell invented the telephone in 1876."),))

    def _validate(self, response):
        with patch.object(OllamaClaimValidator, "_request_json", return_value=response):
            return OllamaClaimValidator().validate_claim(self.claim, self.evidence)

    def test_clearly_supported_claim(self):
        result = self._validate(_response())
        self.assertEqual(result.label, "SUPPORTED")
        self.assertEqual(result.cited_source_ids, ("S1",))
        self.assertEqual(result.evidence[0].snippet, "Bell invented the telephone in 1876.")

    def test_clearly_contradicted_claim(self):
        self.claim = Claim("C1", "Bell invented the telephone in 1900.")
        result = self._validate(_response("CONTRADICTED", 0.93))
        self.assertEqual(result.label, "CONTRADICTED")

    def test_insufficient_evidence_can_be_uncertain(self):
        self.assertEqual(self._validate(_response("UNCERTAIN", 0.7)).label, "UNCERTAIN")

    def test_multiple_supporting_items_are_all_preserved(self):
        extra = Evidence("S2", "Archive", "https://example.test/2", 0.8, "The telephone was invented by Bell in 1876.")
        self.evidence = ClaimEvidence("C1", (self.evidence.evidence[0], extra))
        result = self._validate(_response("SUPPORTED", 0.95, ["S1", "S2"],
            'S1 states "Bell invented the telephone in 1876." S2 states "The telephone was invented by Bell in 1876."'))
        self.assertEqual(len(result.evidence), 2)

    def test_conflicting_evidence_can_be_uncertain(self):
        conflicting = Evidence("S2", "Archive", None, 0.8, "Bell invented the telephone in 1900.")
        self.evidence = ClaimEvidence("C1", (self.evidence.evidence[0], conflicting))
        result = self._validate(_response("UNCERTAIN", 0.88, ["S1", "S2"],
            'S1 states "Bell invented the telephone in 1876." while S2 states "Bell invented the telephone in 1900."'))
        self.assertEqual(result.label, "UNCERTAIN")

    def test_empty_evidence_is_deterministically_uncertain(self):
        result = OllamaClaimValidator().validate_claim(self.claim, ClaimEvidence("C1", ()))
        self.assertEqual((result.label, result.confidence), ("UNCERTAIN", 1.0))

    def test_malformed_model_json_is_rejected(self):
        with patch.object(OllamaClaimValidator, "_request_json", return_value={"message": {"content": "not json"}}):
            with self.assertRaisesRegex(ClaimValidationError, "malformed"):
                OllamaClaimValidator().validate_claim(self.claim, self.evidence)

    def test_invalid_label_and_confidence_are_rejected(self):
        with self.assertRaisesRegex(ClaimValidationError, "label"):
            parse_validation_response({"label": "TRUE", "confidence": .9, "cited_source_ids": ["S1"], "rationale": 'S1 "Bell invented the telephone in 1876."'}, self.claim, self.evidence)
        with self.assertRaisesRegex(ClaimValidationError, "confidence"):
            parse_validation_response({"label": "SUPPORTED", "confidence": 1.1, "cited_source_ids": ["S1"], "rationale": 'S1 "Bell invented the telephone in 1876."'}, self.claim, self.evidence)

    def test_rationale_must_be_present_and_grounded(self):
        with self.assertRaisesRegex(ClaimValidationError, "present"):
            parse_validation_response({"label": "SUPPORTED", "confidence": .9, "cited_source_ids": ["S1"], "rationale": ""}, self.claim, self.evidence)

    def test_paraphrased_rationale_passes_without_rewriting_evidence(self):
        result = parse_validation_response(
            {"label": "SUPPORTED", "confidence": .95, "cited_source_ids": ["S1"], "rationale": "The evidence directly supports the claim."},
            self.claim,
            self.evidence,
        )
        self.assertEqual(result.rationale, "The evidence directly supports the claim.")
        self.assertEqual(result.evidence, self.evidence.evidence)

    def test_fabricated_source_id_is_rejected(self):
        with self.assertRaisesRegex(ClaimValidationError, "not supplied"):
            parse_validation_response(
                {"label": "SUPPORTED", "confidence": .95, "cited_source_ids": ["S5"], "rationale": "The evidence supports the claim."},
                self.claim,
                self.evidence,
            )

    def test_multiple_cited_sources_are_preserved(self):
        extra = Evidence("S2", "Archive", "https://example.test/2", 0.8, "The telephone was invented by Bell in 1876.")
        result = parse_validation_response(
            {"label": "SUPPORTED", "confidence": .95, "cited_source_ids": ["S1", "S2"], "rationale": "Both supplied sources support the claim."},
            self.claim,
            ClaimEvidence("C1", (self.evidence.evidence[0], extra)),
        )
        self.assertEqual(result.cited_source_ids, ("S1", "S2"))

    def test_model_cannot_inject_evidence_quotation(self):
        result = self._validate(_response(rationale="The claim is supported."))
        self.assertNotIn("Bell invented", result.rationale)
        self.assertEqual(result.evidence[0].snippet, self.evidence.evidence[0].snippet)

    def test_request_contains_only_claim_and_mapped_snippets(self):
        validator = OllamaClaimValidator()
        with patch.object(validator, "_request_json", return_value=_response()) as request_json:
            validator.validate_claim(self.claim, self.evidence)
        request_text = request_json.call_args.args[0]["messages"][1]["content"]
        self.assertIn(self.claim.claim, request_text)
        self.assertIn(self.evidence.evidence[0].snippet, request_text)
        self.assertNotIn("outside knowledge", request_text.casefold())
