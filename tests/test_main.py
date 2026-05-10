from types import SimpleNamespace

import fitz
from fastapi.testclient import TestClient

from app import main
from app.config import LLMSettings
from app.schema import CTISummary
from app.summarizer import SummarizationError


class DummyResponse:
    text = "<html><body><h1>Report</h1><p>APT28 activity</p></body></html>"


class FakeSummaryResult:
    def __init__(self, summary: CTISummary):
        self.summary = summary


class FakeSummarizer:
    def __init__(self, settings):
        self.settings = settings

    async def summarize(self, text, system_prompt=None):
        return FakeSummaryResult(
            CTISummary(
                summary=f"Summarized {text[:10]}",
                key_points=[system_prompt or "default prompt"],
                threat_actors=["APT28"],
            )
        )


class FailingSummarizer:
    def __init__(self, settings):
        self.settings = settings

    async def summarize(self, text, system_prompt=None):
        raise SummarizationError("provider failed cleanly")


def _client(monkeypatch, *, dry_run=False, output_json=False):
    main.app.dependency_overrides[main.get_current_username] = lambda: "tester"
    monkeypatch.setattr(
        main,
        "app_settings",
        SimpleNamespace(
            system_prompt="Default CTI prompt",
            dry_run=dry_run,
            output_json=output_json,
        ),
    )
    monkeypatch.setattr(main, "llm_settings", LLMSettings(model="test-model"))
    return TestClient(main.app)


def teardown_function():
    main.app.dependency_overrides.clear()


def test_get_index_renders_form(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/", headers={"X-Forwarded-Proto": "https"})

    assert response.status_code == 200
    assert "Summarize this" in response.text
    assert "Default CTI prompt" in response.text


def test_post_without_input_returns_400(monkeypatch):
    client = _client(monkeypatch)

    response = client.post("/", data={})

    assert response.status_code == 400
    assert "Expected either url field or text field or a PDF file" in response.text


def test_post_text_dry_run_renders_markdown_summary(monkeypatch):
    client = _client(monkeypatch, dry_run=True)

    response = client.post("/", data={"text": "APT28 used phishing.", "model": "dry-model"})

    assert response.status_code == 200
    assert "DRY_RUN is enabled" in response.text
    assert "No request was sent to an LLM provider" in response.text


def test_post_text_uses_summarizer_and_renders_result(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(main, "CTISummarizer", FakeSummarizer)

    response = client.post(
        "/",
        data={
            "text": "APT28 used phishing.",
            "system_prompt": "Custom prompt",
            "model": "override-model",
        },
    )

    assert response.status_code == 200
    assert "Summarized APT28 used" in response.text
    assert "Custom prompt" in response.text
    assert "APT28" in response.text


def test_post_text_returns_clean_summarization_error(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(main, "CTISummarizer", FailingSummarizer)

    response = client.post("/", data={"text": "report text"})

    assert response.status_code == 400
    assert "provider failed cleanly" in response.text


def test_post_json_response(monkeypatch):
    client = _client(monkeypatch, output_json=True)
    monkeypatch.setattr(main, "CTISummarizer", FakeSummarizer)

    response = client.post("/", data={"text": "APT28 report"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["summary"] == "Summarized APT28 repo"


def test_post_url_fetches_text(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(main, "CTISummarizer", FakeSummarizer)
    monkeypatch.setattr(main.requests, "get", lambda *args, **kwargs: DummyResponse())

    response = client.post("/", data={"url": "https://example.test/report"})

    assert response.status_code == 200
    assert "Summarized ReportAPT2" in response.text


def test_post_invalid_url_returns_400(monkeypatch):
    client = _client(monkeypatch)

    response = client.post("/", data={"url": "not-a-url"})

    assert response.status_code == 400
    assert "Could not fetch URL. Reason Invalid URL" in response.text


def test_post_pdf_uses_converter(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(main, "CTISummarizer", FakeSummarizer)
    monkeypatch.setattr(main, "convert_pdf_to_markdown", lambda filename: "PDF report text")

    response = client.post(
        "/",
        files={"pdffile": ("report.pdf", b"%PDF-pretend", "application/pdf")},
    )

    assert response.status_code == 200
    assert "Summarized PDF report" in response.text


def test_post_pdf_conversion_error_returns_400(monkeypatch):
    client = _client(monkeypatch)

    def fail_convert(filename):
        raise ValueError("bad pdf")

    monkeypatch.setattr(main, "convert_pdf_to_markdown", fail_convert)

    response = client.post(
        "/",
        files={"pdffile": ("report.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert "Could not process the PDF file. Reason bad pdf" in response.text


def test_convert_pdf_to_markdown_extracts_pages(tmp_path):
    pdf_path = tmp_path / "report.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "PDF CTI report")
    document.save(pdf_path)
    document.close()

    markdown_text = main.convert_pdf_to_markdown(str(pdf_path))

    assert "PDF CTI report" in markdown_text
    assert "---" in markdown_text
