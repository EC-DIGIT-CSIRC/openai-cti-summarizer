"""CTI summarization via Pydantic AI."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import ValidationError

from .config import LLMOutputMode, LLMProvider, LLMSettings
from .rendering import YARA_AI_VALIDATION_NOTE, YARA_AUTHOR
from .schema import CTISummary
from .settings import log


class SummarizationError(Exception):
    """Base class for summarization failures."""


class LLMConfigurationError(SummarizationError):
    """The configured provider/model cannot be constructed."""


class LLMProviderError(SummarizationError):
    """The provider request failed."""


class LLMOutputValidationError(SummarizationError):
    """The provider returned output that did not validate as CTISummary."""


@dataclass(frozen=True)
class SummarizationResult:
    """Successful summarization result plus operational metadata."""

    summary: CTISummary
    duration_ms: int
    usage: Any | None = None
    provider: str = ""
    model: str = ""
    output_mode: str = ""


AgentFactory = Callable[[Any, Any, dict[str, Any]], Any]


def _secret_value(value: Any | None) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    return str(value)


def _build_pydantic_ai_model(settings: LLMSettings) -> Any:
    """Build a Pydantic AI model or model string from settings."""
    try:
        if settings.provider == LLMProvider.OPENAI:
            if settings.api_key or settings.base_url:
                from pydantic_ai.models.openai import OpenAIChatModel
                from pydantic_ai.providers.openai import OpenAIProvider

                provider = OpenAIProvider(
                    api_key=_secret_value(settings.api_key),
                    base_url=settings.base_url,
                )
                return OpenAIChatModel(settings.model, provider=provider)
            return f"openai:{settings.model}"

        if settings.provider == LLMProvider.AZURE:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.azure import AzureProvider

            provider = AzureProvider(
                azure_endpoint=settings.azure_endpoint,
                api_key=_secret_value(settings.azure_api_key),
                api_version=settings.azure_api_version,
            )
            return OpenAIChatModel(settings.model, provider=provider)

        if settings.provider == LLMProvider.OPENROUTER:
            if settings.api_key:
                from pydantic_ai.models.openrouter import OpenRouterModel
                from pydantic_ai.providers.openrouter import OpenRouterProvider

                return OpenRouterModel(
                    settings.model,
                    provider=OpenRouterProvider(api_key=_secret_value(settings.api_key)),
                )
            return f"openrouter:{settings.model}"

        if settings.provider == LLMProvider.OLLAMA:
            if settings.base_url or settings.api_key:
                from pydantic_ai.models.ollama import OllamaModel
                from pydantic_ai.providers.ollama import OllamaProvider

                return OllamaModel(
                    settings.model,
                    provider=OllamaProvider(
                        base_url=settings.base_url,
                        api_key=_secret_value(settings.api_key),
                    ),
                )
            return f"ollama:{settings.model}"

        if settings.provider == LLMProvider.ANTHROPIC:
            if settings.api_key:
                from pydantic_ai.models.anthropic import AnthropicModel
                from pydantic_ai.providers.anthropic import AnthropicProvider

                return AnthropicModel(
                    settings.model,
                    provider=AnthropicProvider(api_key=_secret_value(settings.api_key)),
                )
            return f"anthropic:{settings.model}"
    except ImportError as exc:
        raise LLMConfigurationError(
            "Pydantic AI provider dependencies are not installed. Run `uv sync`."
        ) from exc
    except Exception as exc:
        raise LLMConfigurationError(f"Failed to configure LLM provider: {exc}") from exc

    raise LLMConfigurationError(f"Unsupported LLM provider: {settings.provider}")


def _structured_output_type(mode: LLMOutputMode) -> Any:
    try:
        if mode == LLMOutputMode.NATIVE:
            from pydantic_ai import NativeOutput

            return NativeOutput(CTISummary)
        if mode == LLMOutputMode.TOOL:
            from pydantic_ai import ToolOutput

            return ToolOutput(CTISummary)
        if mode == LLMOutputMode.PROMPTED:
            from pydantic_ai import PromptedOutput

            return PromptedOutput(CTISummary)
    except ImportError as exc:
        raise LLMConfigurationError(
            "Pydantic AI is not installed. Run `uv sync`."
        ) from exc

    raise LLMConfigurationError(f"Unsupported output mode: {mode}")


def _default_agent_factory(model: Any, output_type: Any, agent_kwargs: dict[str, Any]) -> Any:
    try:
        from pydantic_ai import Agent
    except ImportError as exc:
        raise LLMConfigurationError("Pydantic AI is not installed. Run `uv sync`.") from exc

    return Agent(model, output_type=output_type, **agent_kwargs)


def _build_grounding_instruction(limit: int) -> str:
    hints = CTISummary.grounding_hints(limit=limit)
    lines: list[str] = []

    if hints["ttps"]:
        lines.append("Prefer these MITRE ATT&CK values when they match the report:")
        lines.extend(f"- {value}" for value in hints["ttps"])

    if hints["threat_actors"]:
        if lines:
            lines.append("")
        lines.append("Prefer these Malpedia threat actor names when they match the report:")
        lines.extend(f"- {value}" for value in hints["threat_actors"])

    return "\n".join(lines)


def _usage_attr(usage: Any, *names: str) -> Any:
    for name in names:
        if hasattr(usage, name):
            return getattr(usage, name)
    return None


class CTISummarizer:
    """CTI-specific summarizer over Pydantic AI Agent."""

    def __init__(
        self,
        settings: LLMSettings,
        *,
        agent_factory: AgentFactory | None = None,
        model_factory: Callable[[LLMSettings], Any] = _build_pydantic_ai_model,
    ) -> None:
        self.settings = settings
        self._agent_factory = agent_factory or _default_agent_factory
        self._model_factory = model_factory

    async def summarize(self, text: str, system_prompt: str | None = None) -> SummarizationResult:
        """Summarize report text into a validated CTISummary."""
        if not text or not text.strip():
            raise LLMOutputValidationError("Report text is empty.")

        try:
            return await self._run_once(text, system_prompt, self.settings.output_mode)
        except LLMProviderError:
            if not self.settings.allow_output_fallback:
                raise
            log.warning(
                "cti_summary_retrying_with_output_fallback",
                extra={
                    "provider": self.settings.provider.value,
                    "model": self.settings.model,
                    "from_output_mode": self.settings.output_mode.value,
                    "to_output_mode": self.settings.output_fallback_mode.value,
                },
            )
            return await self._run_once(text, system_prompt, self.settings.output_fallback_mode)

    async def _run_once(
        self,
        text: str,
        system_prompt: str | None,
        output_mode: LLMOutputMode,
    ) -> SummarizationResult:
        instructions = self._build_instructions(system_prompt)
        try:
            model = self._model_factory(self.settings)
            output_type = _structured_output_type(output_mode)
            agent = self._agent_factory(
                model,
                output_type,
                {"instructions": instructions},
            )
        except LLMConfigurationError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc
        model_settings = {
            "timeout": self.settings.timeout_seconds,
        }

        started = time.perf_counter()
        try:
            result = await agent.run(text, model_settings=model_settings)
        except ValidationError as exc:
            raise LLMOutputValidationError(f"LLM output failed schema validation: {exc}") from exc
        except Exception as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        summary = result.output
        if not isinstance(summary, CTISummary):
            try:
                summary = CTISummary.model_validate(summary)
            except ValidationError as exc:
                raise LLMOutputValidationError(
                    f"LLM output failed schema validation: {exc}"
                ) from exc

        usage = result.usage() if hasattr(result, "usage") else None
        self._log_success(duration_ms, usage, output_mode)
        return SummarizationResult(
            summary=summary,
            duration_ms=duration_ms,
            usage=usage,
            provider=self.settings.provider.value,
            model=self.settings.model,
            output_mode=output_mode.value,
        )

    def _build_instructions(self, system_prompt: str | None) -> str:
        base_prompt = system_prompt.strip() if system_prompt else ""
        grounding = _build_grounding_instruction(self.settings.prompt_grounding_hint_limit)
        guardrails = (
            "Return only facts supported by the report. Use empty lists when a section is not "
            "supported. Keep yara_rules empty unless the report contains enough concrete "
            "strings, conditions, and context to support useful candidate rules. If you propose "
            f"any YARA rule, include author metadata naming {YARA_AUTHOR} and include this note "
            f"in or next to the rule: {YARA_AI_VALIDATION_NOTE}"
        )
        return "\n\n".join(part for part in (base_prompt, grounding, guardrails) if part)

    def _log_success(self, duration_ms: int, usage: Any | None, output_mode: LLMOutputMode) -> None:
        log.info(
            "cti_summary_completed",
            extra={
                "provider": self.settings.provider.value,
                "model": self.settings.model,
                "output_mode": output_mode.value,
                "duration_ms": duration_ms,
                "usage_available": usage is not None,
                "request_tokens": _usage_attr(usage, "input_tokens", "request_tokens") if usage else None,
                "response_tokens": _usage_attr(usage, "output_tokens", "response_tokens") if usage else None,
                "total_tokens": _usage_attr(usage, "total_tokens") if usage else None,
                "requests": _usage_attr(usage, "requests") if usage else None,
            },
        )
