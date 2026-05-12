"""LangSmith tracing policy for CTI summarization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import langsmith as ls

from .config import LangSmithSettings, Sensitivity
from .rendering import summary_to_jsonable
from .settings import log


@dataclass(frozen=True)
class TraceContext:
    """Request metadata used for tracing policy and LangSmith metadata."""

    sensitivity: Sensitivity = Sensitivity.PA
    input_mode: str = "text"
    app_version: str = ""


def parse_sensitivity(value: str | Sensitivity | None) -> Sensitivity:
    """Validate and normalize a sensitivity value."""
    if isinstance(value, Sensitivity):
        return value

    normalized = (value or Sensitivity.PA.value).strip().upper()
    try:
        return Sensitivity(normalized)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Sensitivity)
        raise ValueError(f"Invalid sensitivity '{value}'. Expected one of: {allowed}.") from exc


def langsmith_tracing_allowed(settings: LangSmithSettings, sensitivity: Sensitivity) -> bool:
    """Return true when LangSmith may receive full report and summary content."""
    return settings.tracing and sensitivity == Sensitivity.PA


def _secret_value(value: Any | None) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    return str(value)


def _metadata(context: TraceContext, provider: str, model: str, output_mode: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "output_mode": output_mode,
        "sensitivity": context.sensitivity.value,
        "input_mode": context.input_mode,
        "app_version": context.app_version,
    }


def _tags(context: TraceContext, provider: str) -> list[str]:
    return ["cti", context.sensitivity.value.lower(), provider]


def _trace_output(result: Any) -> dict[str, Any]:
    output = getattr(result, "output", result)
    if hasattr(output, "model_dump"):
        return {"summary": summary_to_jsonable(output)}
    return {"summary": output}


async def run_with_langsmith_trace(
    settings: LangSmithSettings,
    context: TraceContext,
    *,
    report_text: str,
    provider: str,
    model: str,
    output_mode: str,
    operation: Callable[[], Awaitable[Any]],
) -> Any:
    """Run an async operation under LangSmith tracing when policy allows it."""
    if not langsmith_tracing_allowed(settings, context.sensitivity):
        if settings.tracing:
            log.info(
                "langsmith_tracing_skipped_for_sensitivity",
                extra={"sensitivity": context.sensitivity.value},
            )
        with ls.tracing_context(enabled=False):
            return await operation()

    client = ls.Client(
        api_url=settings.endpoint,
        api_key=_secret_value(settings.api_key),
    )
    metadata = _metadata(context, provider, model, output_mode)
    async with ls.trace(
        "cti-summary",
        run_type="chain",
        inputs={"report_text": report_text},
        project_name=settings.project,
        tags=_tags(context, provider),
        metadata=metadata,
        client=client,
    ) as run:
        result = await operation()
        run.end(outputs=_trace_output(result))
        return result
