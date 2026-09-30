"""Command-line demonstration of the answer-to-claims Phase 2 pipeline."""

from __future__ import annotations

import argparse
import os
from typing import Sequence

from .claim_decomposer import OllamaClaimDecomposer
from .claim_validator import OllamaClaimValidator
from .evidence_mapper import OllamaEvidenceMapper
from .trust_engine import compute_trust
from .simplicity_client import ModelReference, SimplicityClient, SimplicityConfigurationError, Source


# `/api/search` includes web retrieval plus several local-model calls. On the
# CPU-only local setup it can legitimately exceed the client library's normal
# 120-second request timeout, so the end-to-end demo uses a longer budget.
DEMO_TIMEOUT_SECONDS = 300.0


def _model_reference(provider_id: str | None, key: str | None, name: str) -> ModelReference | None:
    if bool(provider_id) != bool(key):
        raise ValueError(f"{name} provider ID and model key must be supplied together.")
    return ModelReference(provider_id=provider_id, key=key) if provider_id and key else None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Query Simplicity, then decompose, map, and validate claims with local Ollama."
    )
    parser.add_argument("query")
    parser.add_argument("--base-url", default=os.environ.get("SIMPLICITY_BASE_URL", "http://127.0.0.1:3000"))
    parser.add_argument("--chat-provider-id", default=os.environ.get("SIMPLICITY_CHAT_PROVIDER_ID"))
    parser.add_argument("--chat-model-key", default=os.environ.get("SIMPLICITY_CHAT_MODEL_KEY"))
    parser.add_argument("--embedding-provider-id", default=os.environ.get("SIMPLICITY_EMBEDDING_PROVIDER_ID"))
    parser.add_argument("--embedding-model-key", default=os.environ.get("SIMPLICITY_EMBEDDING_MODEL_KEY"))
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEMO_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument("--ollama-base-url", default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--claim-model", default=os.environ.get("CLAIM_DECOMPOSER_MODEL", "qwen2.5:3b"))
    parser.add_argument("--evidence-model", default=os.environ.get("EVIDENCE_MAPPER_MODEL", "qwen2.5:3b"))
    parser.add_argument("--validator-model", default=os.environ.get("CLAIM_VALIDATOR_MODEL", "qwen2.5:3b"))
    parser.add_argument("--no-claims", action="store_true", help="Print only the Phase 1 answer and sources.")
    args = parser.parse_args(argv)

    try:
        client = SimplicityClient(
            args.base_url,
            chat_model=_model_reference(args.chat_provider_id, args.chat_model_key, "Chat"),
            embedding_model=_model_reference(args.embedding_provider_id, args.embedding_model_key, "Embedding"),
            timeout_seconds=args.timeout,
        )
        result = client.get_answer_and_sources(args.query)
        claims = [] if args.no_claims else OllamaClaimDecomposer(
            args.ollama_base_url, model=args.claim_model, timeout_seconds=args.timeout
        ).decompose_claims(result["answer"])
        mappings = [] if args.no_claims else OllamaEvidenceMapper(
            args.ollama_base_url, model=args.evidence_model, timeout_seconds=args.timeout
        ).map_evidence(claims, [Source(**source) for source in result["sources"]])
        validations = [] if args.no_claims else OllamaClaimValidator(
            args.ollama_base_url, model=args.validator_model, timeout_seconds=args.timeout
        ).validate_claims(claims, mappings)
        trust_report = None if args.no_claims else compute_trust(validations)
    except (ValueError, SimplicityConfigurationError, RuntimeError) as exc:
        parser.error(str(exc))

    print("ANSWER:")
    print(result["answer"])
    print("\nSOURCES:")
    for index, source in enumerate(result["sources"], start=1):
        print(f"\n{index}. {source['title'] or '(untitled)'}")
        print(f"   {source['url'] or '(no URL)'}")
        preview = " ".join(source["content"].split())[:300]
        print(f"   {preview}")
    if not args.no_claims:
        print("\nEXTRACTED CLAIMS:")
        if claims:
            for claim in claims:
                print(f"{claim.id}: {claim.claim}")
                mapping = next(item for item in mappings if item.claim_id == claim.id)
                if mapping.evidence:
                    print("  Evidence:")
                    for evidence in mapping.evidence:
                        print(f"  {evidence.source_id} — {evidence.title or '(untitled)'}")
                        print(f"  Relevance: {evidence.relevance:.2f}")
                        print(f'  "{evidence.snippet}"')
                else:
                    print("  Evidence: (No relevant returned source mapped.)")
                validation = next(item for item in validations if item.claim_id == claim.id)
                print("  Validation:")
                print(f"  Label: {validation.label}")
                print(f"  Confidence: {validation.confidence:.2f}")
                print(f"  Rationale: {validation.rationale}")
        else:
            print("(No factual claims extracted.)")
        if trust_report is not None:
            print("\nTRUST REPORT:")
            if trust_report.overall_trust is None:
                print("Overall Trust: unavailable")
            else:
                print(f"Overall Trust: {trust_report.overall_trust:.2f}")
                print(f"Supported: {trust_report.supported_count}/{trust_report.claim_count}")
                print(f"Contradicted: {trust_report.contradicted_count}/{trust_report.claim_count}")
                print(f"Uncertain: {trust_report.uncertain_count}/{trust_report.claim_count}")
                print(f"Evidence certainty: {trust_report.certainty_rate:.2f}")
            print(f"Explanation: {trust_report.explanation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
