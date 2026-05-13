"""Redis-backed cache helpers for report inputs and LLM summaries."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from .config import LLMSettings
from .rendering import summary_to_jsonable
from .schema import CTISummary

CACHE_VERSION = 1
SCHEMA_NAME = "CTISummary"


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 hex digest for bytes."""
    return hashlib.sha256(value).hexdigest()


def cache_timestamp() -> str:
    """Return the current UTC timestamp for cache metadata."""
    return datetime.now(UTC).isoformat()


def canonical_json(value: dict[str, Any]) -> str:
    """Return deterministic JSON for hashing cache contracts."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def url_cache_key(url: str) -> str:
    """Return the Redis key for a fetched URL."""
    return f"cti:url:v{CACHE_VERSION}:{sha256_text(url.strip())}"


def pdf_cache_key(pdf_bytes: bytes) -> str:
    """Return the Redis key for extracted PDF text."""
    return f"cti:pdf:v{CACHE_VERSION}:{sha256_bytes(pdf_bytes)}"


def text_cache_key(text: str) -> str:
    """Return the Redis key for submitted text."""
    return f"cti:text:v{CACHE_VERSION}:{sha256_text(text)}"


def llm_cache_contract(text: str, system_prompt: str, settings: LLMSettings) -> dict[str, Any]:
    """Return the deterministic contract that defines an LLM cache hit."""
    return {
        "cache_version": CACHE_VERSION,
        "text_sha256": sha256_text(text),
        "system_prompt_sha256": sha256_text(system_prompt),
        "schema": SCHEMA_NAME,
        "schema_sha256": sha256_text(canonical_json(CTISummary.model_json_schema())),
        "provider": settings.provider.value,
        "model": settings.model,
        "output_mode": settings.output_mode.value,
        "output_fallback_mode": settings.output_fallback_mode.value,
        "allow_output_fallback": settings.allow_output_fallback,
        "prompt_grounding_hint_limit": settings.prompt_grounding_hint_limit,
    }


def llm_cache_key(contract: dict[str, Any]) -> str:
    """Return the Redis key for an LLM summary contract."""
    return f"cti:llm:v{CACHE_VERSION}:{sha256_text(canonical_json(contract))}"


def usage_to_jsonable(usage: Any | None) -> dict[str, Any] | None:
    """Return token usage when the provider result exposes it."""
    if usage is None:
        return None

    values = {
        "request_tokens": _usage_attr(usage, "input_tokens", "request_tokens"),
        "response_tokens": _usage_attr(usage, "output_tokens", "response_tokens"),
        "total_tokens": _usage_attr(usage, "total_tokens"),
        "requests": _usage_attr(usage, "requests"),
    }
    return {key: value for key, value in values.items() if value is not None} or None


def _usage_attr(usage: Any, *names: str) -> Any:
    for name in names:
        if hasattr(usage, name):
            return getattr(usage, name)
    return None


class RedisCacheStore:
    """Small JSON cache wrapper over Redis."""

    def __init__(self, redis_url: str):
        self.client = Redis.from_url(redis_url, decode_responses=True)

    async def ping(self) -> None:
        """Verify Redis is reachable."""
        await self.client.ping()

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Read a JSON object from Redis."""
        value = await self.client.get(key)
        if value is None:
            return None
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else None

    async def set_json(self, key: str, value: dict[str, Any]) -> None:
        """Write a JSON object to Redis without expiration."""
        await self.client.set(key, json.dumps(value, sort_keys=True, ensure_ascii=False))


def input_cache_payload(source_type: str, text: str, **metadata: Any) -> dict[str, Any]:
    """Return the standard cache payload for extracted input text."""
    return {
        "cache_version": CACHE_VERSION,
        "created_at": cache_timestamp(),
        "source_type": source_type,
        "text_sha256": sha256_text(text),
        "text": text,
        **metadata,
    }


def llm_cache_payload(
    summary: CTISummary,
    contract: dict[str, Any],
    *,
    duration_ms: int,
    usage: Any | None,
) -> dict[str, Any]:
    """Return the standard cache payload for a validated LLM summary."""
    return {
        "cache_version": CACHE_VERSION,
        "created_at": cache_timestamp(),
        "schema": SCHEMA_NAME,
        "contract": contract,
        "duration_ms": duration_ms,
        "usage": usage_to_jsonable(usage),
        "summary": summary_to_jsonable(summary),
    }
