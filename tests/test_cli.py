import json

import pytest
from click.testing import CliRunner

from app import cli
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
    def __init__(self, settings):
        self.settings = settings

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
    def __init__(self, settings):
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


def test_cli_maps_summarization_error(monkeypatch):
    monkeypatch.setattr(cli, "CTISummarizer", FailingSummarizer)
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--text", "APT28 report"])

    assert result.exit_code != 0
    assert "cli provider failed" in result.output
