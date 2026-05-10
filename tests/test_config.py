import pytest
from pydantic import ValidationError

from app.config import LLMOutputMode, LLMProvider, LLMSettings


def test_llm_settings_support_cli_style_overrides(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")

    settings = LLMSettings().with_overrides(
        provider="openrouter",
        model="anthropic/claude-sonnet-4-5",
        output_mode="tool",
    )

    assert settings.provider == LLMProvider.OPENROUTER
    assert settings.model == "anthropic/claude-sonnet-4-5"
    assert settings.output_mode == LLMOutputMode.TOOL


def test_azure_settings_require_endpoint_and_key():
    with pytest.raises(ValidationError, match="Azure provider requires"):
        LLMSettings(provider="azure", model="deployment-name")


def test_native_output_is_default(monkeypatch):
    monkeypatch.delenv("LLM_OUTPUT_MODE", raising=False)

    assert LLMSettings().output_mode == LLMOutputMode.NATIVE
