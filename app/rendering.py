"""Render validated CTI summaries into deterministic markdown."""

from __future__ import annotations

import json
from typing import Any

from .schema import CTISummary


def _append_list(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return

    lines.extend([f"## {title}", ""])
    lines.extend(f"- {value}" for value in values)
    lines.append("")


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
            lines.extend(["```yara", rule.strip(), "```", ""])

    return "\n".join(lines).strip() + "\n"


def summary_to_jsonable(summary: CTISummary) -> dict[str, Any]:
    """Return a JSON-serializable summary mapping."""
    return summary.model_dump(mode="json")
