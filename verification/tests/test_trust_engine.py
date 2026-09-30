import unittest

from verification.claim_validator import ValidationResult
from verification.trust_engine import TrustEngineError, compute_trust


def result(claim_id, label, confidence):
    return ValidationResult(claim_id, f"Claim {claim_id}", label, confidence, (), "Test rationale.")


class TrustEngineTests(unittest.TestCase):
    def test_all_supported(self):
        report = compute_trust([result("C1", "SUPPORTED", 1), result("C2", "SUPPORTED", .8)])
        self.assertEqual(report.overall_trust, .95)
        self.assertEqual((report.supported_count, report.contradicted_count, report.uncertain_count), (2, 0, 0))

    def test_all_contradicted(self):
        report = compute_trust([result("C1", "CONTRADICTED", 1), result("C2", "CONTRADICTED", .8)])
        self.assertAlmostEqual(report.overall_trust, .05)
        self.assertEqual(report.contradiction_rate, 1)

    def test_all_uncertain_is_neutral_but_has_no_evidence_certainty(self):
        report = compute_trust([result("C1", "UNCERTAIN", .9), result("C2", "UNCERTAIN", .2)])
        self.assertEqual((report.overall_trust, report.signed_score, report.certainty_rate), (.5, 0, 0))
        self.assertEqual(report.uncertainty_rate, 1)

    def test_mixed_results_follow_the_documented_formula(self):
        report = compute_trust([
            result("C1", "SUPPORTED", .95), result("C2", "SUPPORTED", .90),
            result("C3", "UNCERTAIN", .5), result("C4", "CONTRADICTED", .90),
        ])
        self.assertAlmostEqual(report.signed_score, .2375)
        self.assertAlmostEqual(report.overall_trust, .61875)
        self.assertEqual((report.support_rate, report.contradiction_rate, report.uncertainty_rate), (.5, .25, .25))

    def test_confidence_extremes(self):
        report = compute_trust([result("C1", "SUPPORTED", 0), result("C2", "CONTRADICTED", 1)])
        self.assertEqual(report.overall_trust, .25)

    def test_empty_input(self):
        report = compute_trust([])
        self.assertIsNone(report.overall_trust)
        self.assertIn("No validation results", report.explanation)

    def test_invalid_confidence_and_label_fail(self):
        with self.assertRaisesRegex(TrustEngineError, "confidence"):
            compute_trust([result("C1", "SUPPORTED", 1.1)])
        with self.assertRaisesRegex(TrustEngineError, "label"):
            compute_trust([result("C1", "INVALID", .5)])

    def test_duplicate_claims_fail(self):
        with self.assertRaisesRegex(TrustEngineError, "Duplicate"):
            compute_trust([result("C1", "SUPPORTED", .9), result("C1", "UNCERTAIN", .2)])

    def test_explanation_and_output_are_deterministic(self):
        values = [result("C1", "SUPPORTED", .8), result("C2", "CONTRADICTED", .6)]
        first, second = compute_trust(values), compute_trust(values)
        self.assertEqual(first, second)
        self.assertIn("supported", first.explanation)
        self.assertIn("contradicted", first.explanation)

    def test_optional_future_weights_are_explicit_and_validated(self):
        report = compute_trust([result("C1", "SUPPORTED", 1), result("C2", "CONTRADICTED", 1)], claim_weights={"C1": 2})
        self.assertAlmostEqual(report.overall_trust, 2 / 3)
        with self.assertRaisesRegex(TrustEngineError, "unknown"):
            compute_trust([result("C1", "SUPPORTED", 1)], claim_weights={"C9": 1})
