import pytest
from pydantic import ValidationError

from app.config import AppSettings, LangSmithSettings, LLMOutputMode, LLMProvider, LLMSettings


def test_default_llm_model_is_gpt_5_5():
    assert LLMSettings.model_fields["model"].default == "gpt-5.5"


def test_llm_settings_read_prefixed_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_MODEL", "anthropic/claude-sonnet-4-5")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "42")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_OUTPUT_MODE", "tool")
    monkeypatch.setenv("LLM_ALLOW_OUTPUT_FALLBACK", "true")
    monkeypatch.setenv("LLM_PROMPT_GROUNDING_HINT_LIMIT", "17")

    settings = LLMSettings()

    assert settings.provider == LLMProvider.OPENROUTER
    assert settings.model == "anthropic/claude-sonnet-4-5"
    assert settings.base_url == "https://llm.example.test/v1"
    assert settings.timeout_seconds == 42
    assert settings.max_retries == 4
    assert settings.output_mode == LLMOutputMode.TOOL
    assert settings.allow_output_fallback is True
    assert settings.prompt_grounding_hint_limit == 17


def test_app_settings_read_environment(monkeypatch):
    monkeypatch.setenv("SYSTEM_PROMPT", "Prompt from env")
    monkeypatch.setenv("OUTPUT_JSON", "true")
    monkeypatch.setenv("DRY_RUN", "true")

    settings = AppSettings()

    assert settings.system_prompt == "Prompt from env"
    assert settings.output_json is True
    assert settings.dry_run is True


def test_langsmith_settings_read_environment(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "cti-test")

    settings = LangSmithSettings()

    assert settings.tracing is True
    assert settings.endpoint == "https://api.smith.langchain.com"
    assert settings.api_key is not None
    assert settings.project == "cti-test"


def test_langsmith_tracing_requires_api_key(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    with pytest.raises(ValidationError, match="LANGSMITH_API_KEY"):
        LangSmithSettings()


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


def test_model_must_not_be_empty():
    with pytest.raises(ValidationError, match="LLM model must not be empty"):
        LLMSettings(model="  ")


def test_max_retries_must_not_be_negative():
    with pytest.raises(ValidationError, match="LLM max retries must not be negative"):
        LLMSettings(max_retries=-1)
