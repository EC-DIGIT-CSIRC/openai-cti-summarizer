"""Typed application configuration."""

from __future__ import annotations

from enum import Enum
from typing import Any

from dotenv import find_dotenv, load_dotenv
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv(), verbose=True, override=False)


class LLMProvider(str, Enum):
    """Supported LLM provider families."""

    OPENAI = "openai"
    AZURE = "azure"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


class LLMOutputMode(str, Enum):
    """Structured output strategy."""

    NATIVE = "native"
    TOOL = "tool"
    PROMPTED = "prompted"


class LLMSettings(BaseSettings):
    """Settings for constructing a Pydantic AI model and summarizer."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-5.4-mini"
    api_key: SecretStr | None = None
    base_url: str | None = None
    azure_endpoint: str | None = None
    azure_api_key: SecretStr | None = None
    azure_api_version: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2
    output_mode: LLMOutputMode = LLMOutputMode.NATIVE
    output_fallback_mode: LLMOutputMode = LLMOutputMode.TOOL
    allow_output_fallback: bool = False
    prompt_grounding_hint_limit: int = 50

    @field_validator("model")
    @classmethod
    def _model_must_not_be_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("LLM model must not be empty.")
        return cleaned

    @model_validator(mode="after")
    def _validate_provider_specific_settings(self) -> "LLMSettings":
        if self.provider == LLMProvider.AZURE:
            missing = [
                name
                for name, value in (
                    ("LLM_AZURE_ENDPOINT", self.azure_endpoint),
                    ("LLM_AZURE_API_KEY", self.azure_api_key),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"Azure provider requires {', '.join(missing)}.")
        return self

    def with_overrides(self, **overrides: Any) -> "LLMSettings":
        """Return a copy with CLI or request-level overrides applied."""
        cleaned = {key: value for key, value in overrides.items() if value is not None}
        return type(self)(**{**self.model_dump(), **cleaned})


class AppSettings(BaseSettings):
    """General web app settings."""

    model_config = SettingsConfigDict(extra="ignore")

    system_prompt: str = Field(
        default=(
            "You are a Cyber Threat Intelligence Analyst. Extract a concise, factual, "
            "structured summary of the report. Prefer canonical MITRE ATT&CK and "
            "Malpedia values when they match the report. Leave yara_rules empty unless "
            "the report contains enough concrete strings, conditions, and context to "
            "support useful candidate rules."
        ),
        alias="SYSTEM_PROMPT",
    )
    output_json: bool = Field(default=False, alias="OUTPUT_JSON")
    dry_run: bool = Field(default=False, alias="DRY_RUN")
