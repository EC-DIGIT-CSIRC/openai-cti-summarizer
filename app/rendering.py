"""Render validated CTI summaries into deterministic markdown."""

from __future__ import annotations

import json
from typing import Any

from .schema import CTISummary

YARA_AUTHOR = "https://github.com/EC-DIGIT-CSIRC/openai-cti-summarizer"
YARA_AI_VALIDATION_NOTE = (
    "This set of YARA rules was AI generated and absolutely needs human validation."
)
_YARA_AUTHOR_META = f'    author = "{YARA_AUTHOR}"'
_YARA_NOTE_META = f'    ai_generated_note = "{YARA_AI_VALIDATION_NOTE}"'


def _append_list(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return

    lines.extend([f"## {title}", ""])
    lines.extend(f"- {value}" for value in values)
    lines.append("")


def _ensure_yara_meta(rule: str) -> str:
    """Ensure generated YARA rules carry mandatory AI provenance metadata."""
    cleaned_rule = rule.strip()
    if not cleaned_rule:
        return cleaned_rule

    has_author = "author =" in cleaned_rule
    has_ai_note = "ai_generated_note =" in cleaned_rule or YARA_AI_VALIDATION_NOTE in cleaned_rule
    if has_author and has_ai_note:
        return cleaned_rule

    lines = cleaned_rule.splitlines()
    meta_index = next((index for index, line in enumerate(lines) if line.strip() == "meta:"), None)
    if meta_index is not None:
        insertions = []
        if not has_author:
            insertions.append(_YARA_AUTHOR_META)
        if not has_ai_note:
            insertions.append(_YARA_NOTE_META)
        lines[meta_index + 1:meta_index + 1] = insertions
        return "\n".join(lines)

    opening_brace_index = next((index for index, line in enumerate(lines) if line.strip() == "{"), None)
    if opening_brace_index is None:
        return "\n".join(["meta:", _YARA_AUTHOR_META, _YARA_NOTE_META, cleaned_rule])

    lines[opening_brace_index + 1:opening_brace_index + 1] = [
        "meta:",
        _YARA_AUTHOR_META,
        _YARA_NOTE_META,
    ]
    return "\n".join(lines)


def render_summary_markdown(summary: CTISummary) -> str:
    """Render a CTISummary as markdown for the web UI and CLI."""
    lines = ["## Executive Summary", "", summary.summary.strip(), ""]

    _append_list(lines, "Key Points", summary.key_points)
    _append_list(lines, "TTPs", summary.ttps)

    if summary.indicators:
        lines.extend(["## Indicators", "", "| Type | Value |", "|---|---|"])
        for indicator in summary.indicators:
            lines.append(f"| {indicator.type} | {indicator.value} |")
        lines.append("")

    _append_list(lines, "Threat Actors", summary.threat_actors or [])

    lines.extend(["## Confidence", "", f"{summary.confidence_score}", ""])

    lines.extend(["## Report Metadata", "", "```json"])
    lines.append(json.dumps(summary.report_metadata, indent=2, sort_keys=True))
    lines.extend(["```", ""])

    if summary.yara_rules:
        lines.extend(["## YARA Rules", ""])
        for rule in summary.yara_rules:
            lines.extend(["```yara", _ensure_yara_meta(rule), "```", ""])

    return "\n".join(lines).strip() + "\n"


def summary_to_jsonable(summary: CTISummary) -> dict[str, Any]:
    """Return a JSON-serializable summary mapping."""
    return summary.model_dump(mode="json")
