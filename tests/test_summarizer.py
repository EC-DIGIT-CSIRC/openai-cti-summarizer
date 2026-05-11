import asyncio

import pytest
from pydantic import SecretStr

from app import schema, summarizer
from app.config import LLMOutputMode, LLMSettings
from app.schema import CTISummary
from app.summarizer import (
    CTISummarizer,
    LLMConfigurationError,
    LLMOutputValidationError,
    LLMProviderError,
)


class FakeUsage:
    input_tokens = 10
    output_tokens = 20
    total_tokens = 30
    requests = 1


class FakeRunResult:
    def __init__(self, output):
        self.output = output

    def usage(self):
        return FakeUsage()


class FakeAgent:
    def __init__(self, output):
        self.output = output
        self.calls = []

    async def run(self, text, model_settings=None):
        self.calls.append((text, model_settings))
        return FakeRunResult(self.output)


def _summary(**overrides):
    data = {
        "summary": "Test summary.",
        "key_points": [],
        "ttps": [],
        "confidence_score": 0.5,
        "report_metadata": {},
    }
    data.update(overrides)
    return CTISummary(**data)


def test_summarizer_returns_validated_summary_and_logs_usage(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    fake_agent = FakeAgent(
        {
            "summary": "APT28 activity.",
            "key_points": [],
            "ttps": [],
            "threat_actors": ["APT28"],
            "confidence_score": 0.8,
            "report_metadata": {},
        }
    )

    result = asyncio.run(
        CTISummarizer(
            LLMSettings(model="test-model"),
            agent_factory=lambda model, output_type, kwargs: fake_agent,
            model_factory=lambda settings: "test:model",
        ).summarize("report text", "system prompt")
    )

    assert result.summary.summary == "APT28 activity."
    assert result.usage.input_tokens == 10
    assert fake_agent.calls[0][0] == "report text"
    assert "cti_summary_completed" in caplog.text


def test_summarizer_sets_low_verbosity_for_gpt_5_5(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    fake_agent = FakeAgent(_summary())

    asyncio.run(
        CTISummarizer(
            LLMSettings(model="gpt-5.5"),
            agent_factory=lambda model, output_type, kwargs: fake_agent,
            model_factory=lambda settings: "test:model",
        ).summarize("report text", "system prompt")
    )

    assert fake_agent.calls[0][1]["openai_text_verbosity"] == "low"


def test_summarizer_does_not_set_low_verbosity_for_other_models(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    fake_agent = FakeAgent(_summary())

    asyncio.run(
        CTISummarizer(
            LLMSettings(model="gpt-5.4-mini"),
            agent_factory=lambda model, output_type, kwargs: fake_agent,
            model_factory=lambda settings: "test:model",
        ).summarize("report text", "system prompt")
    )

    assert "openai_text_verbosity" not in fake_agent.calls[0][1]


def test_summarizer_retries_with_fallback_when_enabled(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    calls = []

    def agent_factory(model, output_type, kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("native unsupported")
        return FakeAgent(_summary(summary="Fallback worked."))

    result = asyncio.run(
        CTISummarizer(
            LLMSettings(model="test-model", allow_output_fallback=True),
            agent_factory=agent_factory,
            model_factory=lambda settings: "test:model",
        ).summarize("report text", "system prompt")
    )

    assert result.summary.summary == "Fallback worked."
    assert len(calls) == 2


def test_summarizer_provider_error_without_fallback(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)

    def agent_factory(model, output_type, kwargs):
        return FakeAgent(_summary(summary="unused"))

    fake_agent = agent_factory(None, None, {})

    async def failing_run(text, model_settings=None):
        raise RuntimeError("provider down")

    fake_agent.run = failing_run

    with pytest.raises(LLMProviderError, match="provider down"):
        asyncio.run(
            CTISummarizer(
                LLMSettings(model="test-model"),
                agent_factory=lambda model, output_type, kwargs: fake_agent,
                model_factory=lambda settings: "test:model",
            ).summarize("report text", "system prompt")
        )


def test_secret_value_handles_none_secret_and_plain_string():
    assert summarizer._secret_value(None) is None
    assert summarizer._secret_value(SecretStr("secret")) == "secret"
    assert summarizer._secret_value("plain") == "plain"


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("openai", "openai:test-model"),
        ("openrouter", "openrouter:test-model"),
        ("ollama", "ollama:test-model"),
        ("anthropic", "anthropic:test-model"),
    ],
)
def test_build_pydantic_ai_model_returns_model_strings_without_explicit_provider_config(provider, expected):
    assert summarizer._build_pydantic_ai_model(LLMSettings(provider=provider, model="test-model")) == expected


@pytest.mark.parametrize(
    ("settings_kwargs", "class_name"),
    [
        (
            {"provider": "openai", "model": "gpt-4o-mini", "api_key": SecretStr("test-key")},
            "OpenAIChatModel",
        ),
        (
            {"provider": "azure", "model": "deployment", "azure_endpoint": "https://example.openai.azure.com/", "azure_api_key": SecretStr("test-key"), "azure_api_version": "2024-07-01-preview"},
            "OpenAIChatModel",
        ),
        (
            {"provider": "openrouter", "model": "openai/gpt-4o-mini", "api_key": SecretStr("test-key")},
            "OpenRouterModel",
        ),
        (
            {"provider": "ollama", "model": "llama3.2", "base_url": "http://localhost:11434/v1"},
            "OllamaModel",
        ),
        (
            {"provider": "anthropic", "model": "claude-3-5-sonnet-latest", "api_key": SecretStr("test-key")},
            "AnthropicModel",
        ),
    ],
)
def test_build_pydantic_ai_model_constructs_explicit_provider_models(settings_kwargs, class_name):
    model = summarizer._build_pydantic_ai_model(LLMSettings(**settings_kwargs))

    assert type(model).__name__ == class_name


def test_build_pydantic_ai_model_uses_responses_model_for_gpt_5_5():
    model = summarizer._build_pydantic_ai_model(LLMSettings(provider="openai", model="gpt-5.5"))

    assert type(model).__name__ == "OpenAIResponsesModel"


def test_build_pydantic_ai_model_wraps_provider_configuration_errors():
    with pytest.raises(LLMConfigurationError, match="Failed to configure LLM provider"):
        summarizer._build_pydantic_ai_model(
            LLMSettings(
                provider="azure",
                model="deployment",
                azure_endpoint="https://example.openai.azure.com/openai/v1/",
                azure_api_key=SecretStr("test-key"),
                azure_api_version="2024-07-01-preview",
            )
        )


@pytest.mark.parametrize("mode", [LLMOutputMode.NATIVE, LLMOutputMode.TOOL, LLMOutputMode.PROMPTED])
def test_structured_output_type_supports_configured_modes(mode):
    assert summarizer._structured_output_type(mode) is not None


def test_structured_output_type_rejects_unknown_mode():
    with pytest.raises(LLMConfigurationError, match="Unsupported output mode"):
        summarizer._structured_output_type("bogus")


def test_default_agent_factory_builds_agent():
    agent = summarizer._default_agent_factory("openai:gpt-4o-mini", CTISummary, {"instructions": "prompt"})

    assert agent is not None


def test_grounding_instruction_includes_cached_hints(tmp_path, monkeypatch):
    monkeypatch.setattr(schema, "TTP_CACHE_PATH", tmp_path / "cache" / "ttps.txt")
    monkeypatch.setattr(schema, "THREAT_ACTOR_CACHE_PATH", tmp_path / "cache" / "threat_actors.txt")
    schema.TTP_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema.TTP_CACHE_PATH.write_text("TA0001 - Initial Access\n", encoding="utf-8")
    schema.THREAT_ACTOR_CACHE_PATH.write_text("APT28\n", encoding="utf-8")

    instruction = summarizer._build_grounding_instruction(10)

    assert "TA0001 - Initial Access" in instruction
    assert "APT28" in instruction


def test_summarizer_instructions_include_yara_author_and_validation_note():
    instructions = CTISummarizer(
        LLMSettings(model="test-model"),
        agent_factory=lambda model, output_type, kwargs: FakeAgent(_summary()),
        model_factory=lambda settings: "test:model",
    )._build_instructions("system prompt")

    assert summarizer.YARA_AUTHOR in instructions
    assert summarizer.YARA_AI_VALIDATION_NOTE in instructions


def test_usage_attr_returns_first_available_name():
    class Usage:
        response_tokens = 12

    assert summarizer._usage_attr(Usage(), "output_tokens", "response_tokens") == 12
    assert summarizer._usage_attr(Usage(), "missing") is None


def test_summarizer_rejects_empty_text():
    with pytest.raises(LLMOutputValidationError, match="Report text is empty"):
        asyncio.run(
            CTISummarizer(
                LLMSettings(model="test-model"),
                agent_factory=lambda model, output_type, kwargs: FakeAgent(_summary(summary="unused")),
                model_factory=lambda settings: "test:model",
            ).summarize("   ", "prompt")
        )


def test_summarizer_preserves_configuration_errors(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)

    def fail_model_factory(settings):
        raise LLMConfigurationError("bad config")

    with pytest.raises(LLMConfigurationError, match="bad config"):
        asyncio.run(
            CTISummarizer(
                LLMSettings(model="test-model"),
                agent_factory=lambda model, output_type, kwargs: FakeAgent(_summary(summary="unused")),
                model_factory=fail_model_factory,
            ).summarize("report", "prompt")
        )


def test_summarizer_maps_agent_factory_error(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)

    def fail_agent_factory(model, output_type, kwargs):
        raise RuntimeError("agent init failed")

    with pytest.raises(LLMProviderError, match="agent init failed"):
        asyncio.run(
            CTISummarizer(
                LLMSettings(model="test-model"),
                agent_factory=fail_agent_factory,
                model_factory=lambda settings: "test:model",
            ).summarize("report", "prompt")
        )


def test_summarizer_maps_invalid_output_to_validation_error(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    fake_agent = FakeAgent({"not_summary": "missing required field"})

    with pytest.raises(LLMOutputValidationError, match="schema validation"):
        asyncio.run(
            CTISummarizer(
                LLMSettings(model="test-model"),
                agent_factory=lambda model, output_type, kwargs: fake_agent,
                model_factory=lambda settings: "test:model",
            ).summarize("report text", "system prompt")
        )
