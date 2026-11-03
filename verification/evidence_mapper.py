"""Map atomic claims to relevant passages in already-retrieved sources.

This module ranks relevance only. It makes no supported/contradicted/truth
judgment, and never retrieves additional web sources.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .claim_decomposer import Claim
from .simplicity_client import Source


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_TIMEOUT_SECONDS = 90.0
MAX_CANDIDATE_SOURCES = 3
MAX_SOURCE_CHARACTERS = 3_000

_STOP_WORDS = frozenset({
    "about", "after", "again", "also", "and", "are", "as", "at", "be", "been", "by",
    "for", "from", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "this", "to", "was", "were", "which", "with",
})

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["evidence"],
    "properties": {
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["segment_id", "relevance"],
                "properties": {
                    "segment_id": {"type": "string", "minLength": 1},
                    "relevance": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}

_SYSTEM_PROMPT = """You select evidence segments for one factual claim.

Return only JSON matching the supplied schema. Select a segment only if its supplied text is useful evidence for the claim. Return only segment_id and a relevance score from 0 to 1. Never return source text, snippets, paraphrases, or any other fields.

Relevance means topical/evidentiary relevance only. Do not decide whether the claim is true, false, supported, contradicted, reliable, or trustworthy. Do not add facts or infer missing evidence. Return an empty evidence array when none of the supplied sources has a useful relevant passage."""


class EvidenceMappingError(RuntimeError):
    """Ollama failed or returned evidence outside the mapping contract."""


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str | None
    url: str | None
    relevance: float
    snippet: str

    def to_dict(self) -> dict[str, str | float | None]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "relevance": self.relevance,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class ClaimEvidence:
    claim_id: str
    evidence: tuple[Evidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "evidence": [item.to_dict() for item in self.evidence]}


@dataclass(frozen=True)
class SourceSegment:
    segment_id: str
    source_id: str
    text: str
    title: str | None
    url: str | None


def split_source_into_segments(source_id: str, source: Source) -> tuple[SourceSegment, ...]:
    """Split a source into sentence segments without changing their text."""

    segments: list[SourceSegment] = []
    for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", source.content, re.DOTALL):
        text = match.group(0)
        if text.strip():
            segments.append(SourceSegment(
                f"{source_id}-P{len(segments) + 1}", source_id, text, source.title, source.url
            ))
    return tuple(segments)


def assign_source_ids(sources: Sequence[Source]) -> tuple[tuple[str, Source], ...]:
    """Assign stable local IDs in the source order returned by Simplicity."""

    return tuple((f"S{index}", source) for index, source in enumerate(sources, start=1))


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-zA-Z0-9]+", text.casefold())
        if len(token) > 2 and token not in _STOP_WORDS
    }


def _lexical_score(claim: str, source: Source) -> float:
    claim_tokens = _tokens(claim)
    source_tokens = _tokens(f"{source.title or ''} {source.content}")
    if not claim_tokens or not source_tokens:
        return 0.0
    return len(claim_tokens & source_tokens) / math.sqrt(len(claim_tokens) * len(source_tokens))


def select_candidate_sources(claim: Claim, sources: Sequence[tuple[str, Source]]) -> list[tuple[str, Source]]:
    """Choose a small, deterministic candidate set before the LLM extraction call.

    The top sources are retained even with zero lexical overlap, so paraphrased
    but relevant evidence is not silently discarded before semantic review.
    """

    usable = [(source_id, source) for source_id, source in sources if source.content.strip()]
    return sorted(
        usable,
        key=lambda item: (-_lexical_score(claim.claim, item[1]), item[0]),
    )[:MAX_CANDIDATE_SOURCES]


def _source_excerpt(claim: Claim, source: Source) -> str:
    """Bound prompt size while retaining the highest lexical-overlap passage."""

    content = source.content
    if len(content) <= MAX_SOURCE_CHARACTERS:
        return content
    pieces = [piece for piece in re.split(r"(?<=[.!?])\s+|\n+", content) if piece.strip()]
    if not pieces:
        return content[:MAX_SOURCE_CHARACTERS]
    best_piece = max(pieces, key=lambda piece: _lexical_score(claim.claim, Source(piece, None, None)))
    position = content.find(best_piece)
    start = max(0, position - MAX_SOURCE_CHARACTERS // 4)
    end = min(len(content), start + MAX_SOURCE_CHARACTERS)
    return content[start:end]


def parse_evidence_response(
    payload: Mapping[str, Any], claim: Claim, segments: Mapping[str, SourceSegment]
) -> ClaimEvidence:
    """Validate segment selections and extract evidence from original segments."""

    raw_evidence = payload.get("evidence")
    if not isinstance(raw_evidence, list):
        raise EvidenceMappingError("Evidence mapping output must contain an 'evidence' list.")

    evidence: list[Evidence] = []
    seen_segment_ids: set[str] = set()
    for index, item in enumerate(raw_evidence):
        if not isinstance(item, Mapping) or set(item) != {"segment_id", "relevance"}:
            raise EvidenceMappingError(
                f"Evidence item {index} must contain exactly segment_id and relevance."
            )
        segment_id, relevance = item["segment_id"], item["relevance"]
        if not isinstance(segment_id, str) or segment_id not in segments:
            raise EvidenceMappingError(f"Evidence item {index} references an unknown segment ID.")
        if isinstance(relevance, bool) or not isinstance(relevance, (int, float)) or not 0 <= relevance <= 1:
            raise EvidenceMappingError(f"Evidence item {index} relevance must be a number from 0 to 1.")
        if segment_id in seen_segment_ids:
            raise EvidenceMappingError("Evidence mapping output contains duplicate segment IDs for one claim.")
        seen_segment_ids.add(segment_id)
        segment = segments[segment_id]
        evidence.append(
            Evidence(segment.source_id, segment.title, segment.url, float(relevance), segment.text)
        )
    return ClaimEvidence(claim_id=claim.id, evidence=tuple(evidence))


class OllamaEvidenceMapper:
    """Minimal local Ollama client for claim-to-source relevance mapping."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        model: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("EVIDENCE_MAPPER_MODEL") or DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds

    def _request_json(self, body: Mapping[str, Any]) -> Mapping[str, Any]:
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read()
        except HTTPError as exc:
            raise EvidenceMappingError(f"Ollama returned HTTP {exc.code} during evidence mapping.") from exc
        except URLError as exc:
            raise EvidenceMappingError(f"Could not reach Ollama at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise EvidenceMappingError("Ollama evidence mapping timed out.") from exc
        try:
            decoded = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceMappingError("Ollama returned invalid JSON during evidence mapping.") from exc
        if not isinstance(decoded, Mapping):
            raise EvidenceMappingError("Ollama response must be a JSON object.")
        return decoded

    def _map_one_claim(self, claim: Claim, candidates: Sequence[tuple[str, Source]]) -> ClaimEvidence:
        segments = tuple(
            segment
            for source_id, source in candidates
            for segment in split_source_into_segments(source_id, source)
        )
        segment_lookup = {segment.segment_id: segment for segment in segments}
        source_blocks = "\n\n".join(
            f'<segment id="{segment.segment_id}" source_id="{segment.source_id}">\n{segment.text}\n</segment>'
            for segment in segments
        )
        response = self._request_json(
            {
                "model": self.model,
                "stream": False,
                "format": _RESPONSE_SCHEMA,
                "options": {"temperature": 0, "num_predict": 768},
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f'<claim id="{claim.id}">{claim.claim}</claim>\n\n{source_blocks}',
                    },
                ],
            }
        )
        message = response.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str):
            raise EvidenceMappingError("Ollama response must contain message.content as a string.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise EvidenceMappingError("Ollama returned malformed evidence JSON.") from exc
        if not isinstance(parsed, Mapping):
            raise EvidenceMappingError("Ollama evidence JSON must be an object.")
        return parse_evidence_response(parsed, claim, segment_lookup)

    def map_evidence(self, claims: Sequence[Claim], sources: Sequence[Source]) -> list[ClaimEvidence]:
        """Map every claim to relevant returned sources, retaining claim order."""

        source_ids = assign_source_ids(sources)
        if not claims:
            return []
        if not source_ids:
            return [ClaimEvidence(claim_id=claim.id, evidence=()) for claim in claims]

        mappings: list[ClaimEvidence] = []
        for claim in claims:
            candidates = select_candidate_sources(claim, source_ids)
            mappings.append(
                self._map_one_claim(claim, candidates)
                if candidates
                else ClaimEvidence(claim_id=claim.id, evidence=())
            )
        return mappings


def map_evidence(claims: Sequence[Claim], sources: Sequence[Source]) -> list[ClaimEvidence]:
    """Convenience entry point using the configured local Ollama instance."""

    return OllamaEvidenceMapper().map_evidence(claims, sources)
