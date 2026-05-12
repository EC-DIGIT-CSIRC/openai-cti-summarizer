import json

import pytest
from click.testing import CliRunner

from app import cli
from app.config import LLMOutputMode, LLMProvider
from app.schema import CTISummary
from app.summarizer import SummarizationError


class DummyResponse:
    text = "<html><body><p>URL report</p></body></html>"

    def raise_for_status(self):
        return None


class FakeResult:
    def __init__(self, summary):
        self.summary = summary


class FakeSummarizer:
    last_settings = None
    last_langsmith_settings = None
    last_trace_context = None

    def __init__(self, settings, *, langsmith_settings=None, trace_context=None):
        self.settings = settings
        self.langsmith_settings = langsmith_settings
        self.trace_context = trace_context
        type(self).last_settings = settings
        type(self).last_langsmith_settings = langsmith_settings
        type(self).last_trace_context = trace_context

    async def summarize(self, text, system_prompt=None):
        return FakeResult(
            CTISummary(
                summary=f"CLI {text[:10]}",
                key_points=[system_prompt or ""],
                ttps=[],
                confidence_score=0.8,
                report_metadata={"source": "cli-test"},
            )
        )


class FailingSummarizer:
    def __init__(self, settings, **kwargs):
        self.settings = settings

    async def summarize(self, text, system_prompt=None):
        raise SummarizationError("cli provider failed")


def test_read_input_requires_exactly_one_source():
    with pytest.raises(cli.click.ClickException, match="Provide exactly one"):
        cli._read_input("text", None, "https://example.test")


def test_read_input_reads_file(tmp_path):
    report_path = tmp_path / "report.txt"
    report_path.write_text("file report", encoding="utf-8")

    assert cli._read_input(None, str(report_path), None) == "file report"


def test_read_input_fetches_url(monkeypatch):
    monkeypatch.setattr(cli.requests, "get", lambda *args, **kwargs: DummyResponse())

    assert "URL report" in cli._read_input(None, None, "https://example.test/report")


def test_cli_outputs_markdown(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FakeSummarizer)
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--text", "APT28 report", "--system-prompt", "CLI prompt"])

    assert result.exit_code == 0
    assert "## Executive Summary" in result.output
    assert "CLI APT28 repo" in result.output
    assert "CLI prompt" in result.output


def test_cli_outputs_json(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FakeSummarizer)
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--text", "APT28 report", "--return-json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["summary"] == "CLI APT28 repo"


def test_cli_passes_environment_to_llm_settings(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FakeSummarizer)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("LLM_MAX_RETRIES", "3")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--text", "APT28 report"])

    assert result.exit_code == 0
    assert FakeSummarizer.last_settings.provider == LLMProvider.OPENAI
    assert FakeSummarizer.last_settings.model == "env-model"
    assert FakeSummarizer.last_settings.timeout_seconds == 12
    assert FakeSummarizer.last_settings.max_retries == 3


def test_cli_parameters_override_llm_settings(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FakeSummarizer)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "--text",
            "APT28 report",
            "--provider",
            "openrouter",
            "--model",
            "cli-model",
            "--base-url",
            "https://llm.example.test/v1",
            "--timeout-seconds",
            "9",
            "--max-retries",
            "5",
            "--output-mode",
            "tool",
            "--allow-output-fallback",
            "--prompt-grounding-hint-limit",
            "11",
        ],
    )

    assert result.exit_code == 0
    assert FakeSummarizer.last_settings.provider == LLMProvider.OPENROUTER
    assert FakeSummarizer.last_settings.model == "cli-model"
    assert FakeSummarizer.last_settings.base_url == "https://llm.example.test/v1"
    assert FakeSummarizer.last_settings.timeout_seconds == 9
    assert FakeSummarizer.last_settings.max_retries == 5
    assert FakeSummarizer.last_settings.output_mode == LLMOutputMode.TOOL
    assert FakeSummarizer.last_settings.allow_output_fallback is True
    assert FakeSummarizer.last_settings.prompt_grounding_hint_limit == 11


def test_cli_parameters_override_langsmith_tracing(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FakeSummarizer)
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        ["--text", "APT28 report", "--langsmith-tracing", "--sensitivity", "PA"],
    )

    assert result.exit_code == 0
    assert FakeSummarizer.last_langsmith_settings.tracing is True
    assert FakeSummarizer.last_trace_context.sensitivity.value == "PA"
    assert FakeSummarizer.last_trace_context.input_mode == "text"


def test_cli_rejects_invalid_sensitivity():
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--text", "APT28 report", "--sensitivity", "SECRET"])

    assert result.exit_code != 0
    assert "Invalid value for '--sensitivity'" in result.output


def test_cli_maps_summarization_error(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FailingSummarizer)
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--text", "APT28 report"])

    assert result.exit_code != 0
    assert "cli provider failed" in result.output
