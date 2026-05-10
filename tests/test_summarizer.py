import asyncio

import pytest

from app import summarizer
from app.config import LLMSettings
from app.schema import CTISummary
from app.summarizer import CTISummarizer, LLMProviderError


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


def test_summarizer_returns_validated_summary_and_logs_usage(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    fake_agent = FakeAgent({"summary": "APT28 activity.", "threat_actors": ["APT28"]})

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


def test_summarizer_retries_with_fallback_when_enabled(monkeypatch):
    monkeypatch.setattr(summarizer, "_structured_output_type", lambda mode: CTISummary)
    calls = []

    def agent_factory(model, output_type, kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("native unsupported")
        return FakeAgent(CTISummary(summary="Fallback worked."))

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
        return FakeAgent(CTISummary(summary="unused"))

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
