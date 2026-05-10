from app.rendering import render_summary_markdown, summary_to_jsonable
from app.schema import CTISummary, Indicator


def _summary(**overrides):
    data = {
        "summary": "Only a summary.",
        "key_points": [],
        "ttps": [],
        "confidence_score": 0.5,
        "report_metadata": {},
    }
    data.update(overrides)
    return CTISummary(**data)


def test_render_summary_markdown_includes_non_empty_sections():
    summary = _summary(
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
    rendered = render_summary_markdown(_summary())

    assert "## Executive Summary" in rendered
    assert "## Indicators" not in rendered
    assert "## YARA Rules" not in rendered
    assert "## Confidence" in rendered
    assert "## Report Metadata" in rendered


def test_summary_to_jsonable_returns_model_dump():
    summary = _summary()

    assert summary_to_jsonable(summary)["summary"] == "Only a summary."


def test_render_summary_markdown_includes_yara_rules():
    summary = _summary(summary="Rule summary.", yara_rules=["rule test { condition: true }"])

    rendered = render_summary_markdown(summary)

    assert "## YARA Rules" in rendered
    assert "```yara" in rendered
    assert "rule test" in rendered
