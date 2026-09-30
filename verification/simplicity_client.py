"""Small, dependency-free client for Simplicity's non-streaming search API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 120.0


class SimplicityAPIError(RuntimeError):
    """The Simplicity server could not complete an API request."""


class SimplicityConfigurationError(RuntimeError):
    """The server does not expose the models needed to run a search."""


@dataclass(frozen=True)
class ModelReference:
    """A Simplicity model selected from ``GET /api/providers``."""

    provider_id: str
    key: str

    def to_api_dict(self) -> dict[str, str]:
        return {"providerId": self.provider_id, "key": self.key}


@dataclass(frozen=True)
class Source:
    content: str
    title: str | None
    url: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {"content": self.content, "title": self.title, "url": self.url}


@dataclass(frozen=True)
class AnswerAndSources:
    answer: str
    sources: tuple[Source, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": [source.to_dict() for source in self.sources],
        }


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SimplicityAPIError(f"Search response source {field_name} must be a string or null.")
    return value


def normalize_search_response(payload: Mapping[str, Any]) -> AnswerAndSources:
    """Normalize Simplicity's ``{message, sources}`` response without reordering it."""

    message = payload.get("message")
    sources = payload.get("sources")
    if not isinstance(message, str):
        raise SimplicityAPIError("Search response field 'message' must be a string.")
    if not isinstance(sources, list):
        raise SimplicityAPIError("Search response field 'sources' must be a list.")

    normalized_sources: list[Source] = []
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            raise SimplicityAPIError(f"Search response source {index} must be an object.")
        content = source.get("content")
        metadata = source.get("metadata", {})
        if not isinstance(content, str):
            raise SimplicityAPIError(f"Search response source {index} field 'content' must be a string.")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, Mapping):
            raise SimplicityAPIError(f"Search response source {index} field 'metadata' must be an object.")
        normalized_sources.append(
            Source(
                content=content,
                title=_optional_string(metadata.get("title"), "metadata.title"),
                url=_optional_string(metadata.get("url"), "metadata.url"),
            )
        )

    return AnswerAndSources(answer=message, sources=tuple(normalized_sources))


class SimplicityClient:
    """Client for Simplicity's ``POST /api/search`` integration boundary."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:3000",
        *,
        chat_model: ModelReference | None = None,
        embedding_model: ModelReference | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.timeout_seconds = timeout_seconds

    def _request_json(
        self, path: str, *, method: str = "GET", body: Mapping[str, Any] | None = None
    ) -> Any:
        encoded_body = None
        headers = {"Accept": "application/json"}
        if body is not None:
            encoded_body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{self.base_url}{path}", data=encoded_body, headers=headers, method=method
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            # Do not include request data here: it may contain credentials in a future API.
            raise SimplicityAPIError(f"Simplicity API returned HTTP {exc.code} for {path}.") from exc
        except URLError as exc:
            raise SimplicityAPIError(f"Could not reach Simplicity at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise SimplicityAPIError(f"Simplicity request to {path} timed out.") from exc

        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SimplicityAPIError(f"Simplicity returned invalid JSON for {path}.") from exc

    def get_providers(self) -> list[Mapping[str, Any]]:
        """Return the provider records exposed by Simplicity, in server order."""

        response = self._request_json("/api/providers")
        if not isinstance(response, Mapping) or not isinstance(response.get("providers"), list):
            raise SimplicityAPIError("Provider response must contain a 'providers' list.")
        providers = response["providers"]
        if not all(isinstance(provider, Mapping) for provider in providers):
            raise SimplicityAPIError("Each provider returned by Simplicity must be an object.")
        return providers

    @staticmethod
    def _first_model(providers: Sequence[Mapping[str, Any]], field: str) -> ModelReference | None:
        for provider in providers:
            provider_id = provider.get("id")
            models = provider.get(field)
            if not isinstance(provider_id, str) or not isinstance(models, list):
                continue
            for model in models:
                if isinstance(model, Mapping) and isinstance(model.get("key"), str):
                    return ModelReference(provider_id=provider_id, key=model["key"])
        return None

    def resolve_models(self) -> tuple[ModelReference, ModelReference]:
        """Use supplied models or select the first server-advertised models.

        Selection is intentionally deterministic and does not encode provider or
        model names. Explicit references always take precedence.
        """

        if self.chat_model is not None and self.embedding_model is not None:
            return self.chat_model, self.embedding_model

        providers = self.get_providers()
        chat_model = self.chat_model or self._first_model(providers, "chatModels")
        embedding_model = self.embedding_model or self._first_model(providers, "embeddingModels")
        if chat_model is None:
            raise SimplicityConfigurationError(
                "No chat model is exposed by GET /api/providers. Configure one in Simplicity or pass chat_model."
            )
        if embedding_model is None:
            raise SimplicityConfigurationError(
                "No embedding model is exposed by GET /api/providers. POST /api/search requires one; configure one in Simplicity or pass embedding_model."
            )
        return chat_model, embedding_model

    def get_answer_and_sources(
        self,
        query: str,
        *,
        sources: Sequence[str] = ("web",),
        optimization_mode: str = "speed",
        history: Sequence[Sequence[str]] = (),
        system_instructions: str | None = None,
    ) -> dict[str, Any]:
        """Run a non-streaming Simplicity search and return normalized data."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        if not sources:
            raise ValueError("sources must contain at least one Simplicity search source.")
        chat_model, embedding_model = self.resolve_models()
        request_body: dict[str, Any] = {
            "query": query,
            "sources": list(sources),
            "chatModel": chat_model.to_api_dict(),
            "embeddingModel": embedding_model.to_api_dict(),
            "optimizationMode": optimization_mode,
            "history": [list(turn) for turn in history],
            "stream": False,
        }
        if system_instructions is not None:
            request_body["systemInstructions"] = system_instructions

        response = self._request_json("/api/search", method="POST", body=request_body)
        if not isinstance(response, Mapping):
            raise SimplicityAPIError("Search response must be a JSON object.")
        return normalize_search_response(response).to_dict()
