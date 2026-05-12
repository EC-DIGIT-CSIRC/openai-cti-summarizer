import asyncio

import pytest

from app.config import LangSmithSettings, Sensitivity
from app.tracing import TraceContext, langsmith_tracing_allowed, parse_sensitivity, run_with_langsmith_trace


def test_parse_sensitivity_defaults_to_pa():
    assert parse_sensitivity(None) == Sensitivity.PA


def test_parse_sensitivity_rejects_unknown_value():
    with pytest.raises(ValueError, match="Invalid sensitivity"):
        parse_sensitivity("SECRET")


def test_langsmith_tracing_allowed_only_for_pa():
    settings = LangSmithSettings(tracing=True, api_key="test-key")

    assert langsmith_tracing_allowed(settings, Sensitivity.PA) is True
    assert langsmith_tracing_allowed(settings, Sensitivity.CU) is False
    assert langsmith_tracing_allowed(settings, Sensitivity.SNC) is False


def test_langsmith_tracing_disabled_when_not_enabled():
    settings = LangSmithSettings(tracing=False)

    assert langsmith_tracing_allowed(settings, Sensitivity.PA) is False


def test_run_with_langsmith_trace_disables_non_pa_even_when_enabled(monkeypatch):
    calls = []

    class FakeTracingContext:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    monkeypatch.setattr("app.tracing.ls.tracing_context", FakeTracingContext)

    async def operation():
        return "done"

    result = asyncio.run(
        run_with_langsmith_trace(
            LangSmithSettings(tracing=True, api_key="test-key"),
            TraceContext(sensitivity=Sensitivity.CU),
            report_text="CU report",
            provider="openai",
            model="gpt-5.5",
            output_mode="native",
            operation=operation,
        )
    )

    assert result == "done"
    assert calls == [{"enabled": False}]
