from app.rendering import render_summary_markdown, summary_to_jsonable
from app.schema import CTISummary, Indicator


def test_render_summary_markdown_includes_non_empty_sections():
    summary = CTISummary(
        summary="APT28 targeted edge devices.",
        key_points=["Initial access used exposed services."],
        ttps=["TA0001 - Initial Access"],
        indicators=[Indicator(type="domain", value="example.test")],
        threat_actors=["APT28"],
        confidence_score=0.8,
        report_metadata={"source": "unit-test"},
    )

    rendered = render_summary_markdown(summary)

    assert "## Executive Summary" in rendered
    assert "- Initial access used exposed services." in rendered
    assert "| domain | example.test |" in rendered
    assert '"source": "unit-test"' in rendered


def test_render_summary_markdown_omits_empty_optional_sections():
    rendered = render_summary_markdown(CTISummary(summary="Only a summary."))

    assert "## Executive Summary" in rendered
    assert "## Indicators" not in rendered
    assert "## YARA Rules" not in rendered


def test_summary_to_jsonable_returns_model_dump():
    summary = CTISummary(summary="Only a summary.")

    assert summary_to_jsonable(summary)["summary"] == "Only a summary."
