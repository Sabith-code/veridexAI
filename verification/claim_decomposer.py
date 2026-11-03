"""LLM-assisted decomposition of an answer into independently checkable claims.

This module deliberately does not retrieve, map, validate, or score evidence.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_TIMEOUT_SECONDS = 90.0

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim"],
                "properties": {"claim": {"type": "string", "minLength": 1}},
            },
        }
    },
}

_SYSTEM_PROMPT = """You decompose an answer into atomic factual claims for later evidence verification.

Return only JSON matching the supplied schema.
Include a claim only when it is an externally verifiable factual assertion explicitly stated or directly entailed by the answer. Preserve the answer's meaning, qualifiers, uncertainty, and attribution. Do not add background knowledge.
Split conjunctions and clauses when they express independently verifiable facts. Keep a relationship in one claim only when separating it would lose its meaning.
Exclude opinions, advice, questions, greetings, rhetorical statements, citations, headings, and unsupported fragments. If there are no factual claims, return an empty claims array.
Do not include IDs: the caller assigns them deterministically."""


class ClaimDecompositionError(RuntimeError):
    """Ollama failed or returned data outside the claim-decomposition contract."""


@dataclass(frozen=True)
class Claim:
    id: str
    claim: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "claim": self.claim}


class ClaimDecomposer(Protocol):
    def decompose_claims(self, answer: str) -> list[Claim]: ...


def parse_claims_response(payload: Mapping[str, Any]) -> list[Claim]:
    """Validate Ollama's decoded JSON and assign stable claim IDs in model order."""

    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        raise ClaimDecompositionError("Claim decomposition output must contain a 'claims' list.")

    claims: list[Claim] = []
    seen_claims: set[str] = set()
    for index, item in enumerate(raw_claims):
        if not isinstance(item, Mapping) or set(item) != {"claim"}:
            raise ClaimDecompositionError(
                f"Claim decomposition item {index} must contain exactly one 'claim' field."
            )
        text = item["claim"]
        if not isinstance(text, str) or not text.strip():
            raise ClaimDecompositionError(f"Claim decomposition item {index} must be a non-empty string.")
        claim = " ".join(text.split())
        normalized = claim.casefold()
        if normalized in seen_claims:
            raise ClaimDecompositionError("Claim decomposition output contains duplicate claims.")
        seen_claims.add(normalized)
        claims.append(Claim(id=f"C{len(claims) + 1}", claim=claim))
    return claims


class OllamaClaimDecomposer:
    """Minimal client for Ollama's schema-constrained, non-streaming chat API."""

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
        self.model = model or os.environ.get("CLAIM_DECOMPOSER_MODEL") or DEFAULT_MODEL
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
            raise ClaimDecompositionError(f"Ollama returned HTTP {exc.code} during claim decomposition.") from exc
        except URLError as exc:
            raise ClaimDecompositionError(f"Could not reach Ollama at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ClaimDecompositionError("Ollama claim decomposition timed out.") from exc
        try:
            decoded = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClaimDecompositionError("Ollama returned invalid JSON during claim decomposition.") from exc
        if not isinstance(decoded, Mapping):
            raise ClaimDecompositionError("Ollama response must be a JSON object.")
        return decoded

    def decompose_claims(self, answer: str) -> list[Claim]:
        """Return atomic factual claims in the answer's original presentation order."""

        if not isinstance(answer, str):
            raise ValueError("answer must be a string.")
        if not answer.strip():
            return []

        response = self._request_json(
            {
                "model": self.model,
                "stream": False,
                "format": _RESPONSE_SCHEMA,
                "options": {"temperature": 0, "num_predict": 1024},
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"<answer>\n{answer}\n</answer>"},
                ],
            }
        )
        message = response.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str):
            raise ClaimDecompositionError("Ollama response must contain message.content as a string.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ClaimDecompositionError("Ollama returned malformed claim JSON.") from exc
        if not isinstance(parsed, Mapping):
            raise ClaimDecompositionError("Ollama claim JSON must be an object.")
        return parse_claims_response(parsed)


def decompose_claims(answer: str) -> list[Claim]:
    """Convenience entry point using the configured local Ollama instance."""

    return OllamaClaimDecomposer().decompose_claims(answer)
