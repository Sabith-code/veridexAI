"""One-request JSON stdin/stdout bridge for the Simplicity verification API."""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping

from .claim_decomposer import decompose_claims
from .claim_validator import validate_claims
from .evidence_mapper import map_evidence
from .simplicity_client import Source
from .trust_engine import compute_trust


def run(payload: Mapping[str, Any]) -> dict[str, Any]:
    answer = payload.get("answer")
    sources = payload.get("sources")
    backend = payload.get("backend", "ollama")
    if not isinstance(answer, str):
        raise ValueError("answer must be a string")
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")
    if backend not in {"ollama", "laya", "hybrid"}:
        raise ValueError("backend must be 'ollama', 'laya', or 'hybrid'")
    normalized_sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping) or not isinstance(source.get("content"), str):
            raise ValueError(f"source {index} must contain string content")
        title, url = source.get("title"), source.get("url")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"source {index} title must be a string or null")
        if url is not None and not isinstance(url, str):
            raise ValueError(f"source {index} url must be a string or null")
        normalized_sources.append(Source(source["content"], title, url))

    claims = decompose_claims(answer)
    mappings = map_evidence(claims, normalized_sources)
    validations = validate_claims(claims, mappings, backend=backend)
    report = compute_trust(validations)
    return {"claims": [item.to_dict() for item in validations], "trust": report.to_dict()}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, Mapping):
            raise ValueError("request must be a JSON object")
        print(json.dumps(run(payload), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Verification bridge failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
