import json
import unittest
from unittest.mock import patch

from verification.claim_decomposer import Claim
from verification.evidence_mapper import (
    EvidenceMappingError,
    OllamaEvidenceMapper,
    assign_source_ids,
    parse_evidence_response,
    split_source_into_segments,
)
from verification.simplicity_client import Source


def _ollama_response(evidence):
    return {"message": {"content": json.dumps({"evidence": evidence})}}


class EvidenceMapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bell = Source(
            content="Alexander Graham Bell is widely credited with inventing the telephone.",
            title="Library of Congress",
            url="https://example.test/bell",
        )
        self.morse = Source(
            content="Samuel Morse helped develop the electric telegraph and Morse code.",
            title="Telegraph history",
            url="https://example.test/morse",
        )

    def test_one_claim_with_one_relevant_source(self) -> None:
        claim = Claim("C1", "Alexander Graham Bell is credited with inventing the telephone.")
        response = _ollama_response([{"segment_id": "S1-P1", "relevance": 0.97}])
        with patch.object(OllamaEvidenceMapper, "_request_json", return_value=response):
            result = OllamaEvidenceMapper().map_evidence([claim], [self.bell])
        self.assertEqual(result[0].evidence[0].source_id, "S1")
        self.assertEqual(result[0].evidence[0].title, "Library of Congress")
        self.assertEqual(result[0].evidence[0].snippet, self.bell.content)

    def test_one_claim_can_map_multiple_relevant_sources(self) -> None:
        claim = Claim("C1", "Alexander Graham Bell is credited with inventing the telephone.")
        second = Source("Bell patented the telephone in 1876.", "Patent history", "https://example.test/patent")
        response = _ollama_response([
            {"segment_id": "S1-P1", "relevance": 0.97},
            {"segment_id": "S2-P1", "relevance": 0.82},
        ])
        with patch.object(OllamaEvidenceMapper, "_request_json", return_value=response):
            result = OllamaEvidenceMapper().map_evidence([claim], [self.bell, second])
        self.assertEqual([item.source_id for item in result[0].evidence], ["S1", "S2"])

    def test_irrelevant_source_is_not_mapped(self) -> None:
        claim = Claim("C1", "Alexander Graham Bell invented the telephone.")
        response = _ollama_response([])
        with patch.object(OllamaEvidenceMapper, "_request_json", return_value=response):
            result = OllamaEvidenceMapper().map_evidence([claim], [self.morse])
        self.assertEqual(result[0].evidence, ())

    def test_multiple_claims_can_share_one_source(self) -> None:
        source = Source(
            "Alexander Graham Bell invented the telephone in 1876.", "History", "https://example.test/history"
        )
        claims = [
            Claim("C1", "Alexander Graham Bell invented the telephone."),
            Claim("C2", "The telephone was invented in 1876."),
        ]
        responses = [
            _ollama_response([{"segment_id": "S1-P1", "relevance": 0.95}]),
            _ollama_response([{"segment_id": "S1-P1", "relevance": 0.90}]),
        ]
        with patch.object(OllamaEvidenceMapper, "_request_json", side_effect=responses):
            result = OllamaEvidenceMapper().map_evidence(claims, [source])
        self.assertEqual([mapping.evidence[0].source_id for mapping in result], ["S1", "S1"])

    def test_empty_claims_skip_the_model(self) -> None:
        with patch.object(OllamaEvidenceMapper, "_request_json") as request_json:
            result = OllamaEvidenceMapper().map_evidence([], [self.bell])
        self.assertEqual(result, [])
        request_json.assert_not_called()

    def test_empty_sources_returns_empty_evidence_for_each_claim(self) -> None:
        with patch.object(OllamaEvidenceMapper, "_request_json") as request_json:
            result = OllamaEvidenceMapper().map_evidence([Claim("C1", "A fact.")], [])
        self.assertEqual(result[0].evidence, ())
        request_json.assert_not_called()

    def test_malformed_model_output_is_rejected(self) -> None:
        with patch.object(OllamaEvidenceMapper, "_request_json", return_value={"message": {"content": "not json"}}):
            with self.assertRaisesRegex(EvidenceMappingError, "malformed"):
                OllamaEvidenceMapper().map_evidence([Claim("C1", "A fact.")], [self.bell])

    def test_snippet_must_be_from_the_supplied_source(self) -> None:
        with self.assertRaisesRegex(EvidenceMappingError, "unknown segment ID"):
            parse_evidence_response(
                {"evidence": [{"segment_id": "S1-P9", "relevance": 0.9}]},
                Claim("C1", "A fact."),
                {segment.segment_id: segment for segment in split_source_into_segments("S1", self.bell)},
            )

    def test_s14_style_misattribution_is_rejected_without_free_text(self) -> None:
        sources = [
            Source(f"Unrelated source {index}.", f"Source {index}", None)
            for index in range(1, 14)
        ]
        source_14 = Source("Source fourteen has unrelated material.", "Source 14", None)
        source_2 = Source("Bell invented the telephone in 1876.", "Source 2", None)
        sources[1] = source_2
        sources.append(source_14)
        segments = {
            segment.segment_id: segment
            for source_id, source in assign_source_ids(sources)
            for segment in split_source_into_segments(source_id, source)
        }
        with self.assertRaisesRegex(EvidenceMappingError, "unknown segment ID"):
            parse_evidence_response(
                {"evidence": [{"segment_id": "S14-P2", "relevance": 0.9}]},
                Claim("C1", "Bell invented the telephone in 1876."),
                segments,
            )

    def test_model_cannot_inject_evidence_text(self) -> None:
        segments = {segment.segment_id: segment for segment in split_source_into_segments("S1", self.bell)}
        with self.assertRaisesRegex(EvidenceMappingError, "exactly segment_id and relevance"):
            parse_evidence_response(
                {"evidence": [{"segment_id": "S1-P1", "relevance": 0.9, "snippet": "Tokyo is the capital of Japan."}]},
                Claim("C1", "A fact."),
                segments,
            )

    def test_invalid_relevance_and_duplicate_segments_are_rejected(self) -> None:
        segments = {segment.segment_id: segment for segment in split_source_into_segments("S1", self.bell)}
        with self.assertRaisesRegex(EvidenceMappingError, "relevance"):
            parse_evidence_response({"evidence": [{"segment_id": "S1-P1", "relevance": 2}]}, Claim("C1", "A fact."), segments)
        with self.assertRaisesRegex(EvidenceMappingError, "duplicate segment IDs"):
            parse_evidence_response({"evidence": [{"segment_id": "S1-P1", "relevance": 0.9}, {"segment_id": "S1-P1", "relevance": 0.8}]}, Claim("C1", "A fact."), segments)

    def test_tokyo_generated_text_is_not_accepted(self) -> None:
        source = Source("Tokyo was renamed from Edo in 1868.", "History", None)
        segments = {segment.segment_id: segment for segment in split_source_into_segments("S5", source)}
        with self.assertRaisesRegex(EvidenceMappingError, "exactly segment_id and relevance"):
            parse_evidence_response(
                {"evidence": [{"segment_id": "S5-P1", "relevance": 0.9, "snippet": "Tokyo is the capital city of Japan."}]},
                Claim("C1", "What is the capital of Japan?"),
                segments,
            )
