"""Command line interface for CTI summarization."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click
import requests
from bs4 import BeautifulSoup

from .config import AppSettings, LangSmithSettings, LLMOutputMode, LLMProvider, LLMSettings, Sensitivity
from .rendering import render_summary_markdown, summary_to_jsonable
from .summarizer import CTISummarizer, SummarizationError
from .tracing import TraceContext


def _read_input(text: str | None, file_path: str | None, url: str | None) -> str:
    supplied = [value is not None for value in (text, file_path, url)].count(True)
    if supplied != 1:
        raise click.ClickException("Provide exactly one of --text, --file, or --url.")

    if text is not None:
        return text
    if file_path is not None:
        return Path(file_path).read_text(encoding="utf-8")
    response = requests.get(url or "", timeout=5)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser").get_text()


@click.command()
@click.option("--provider", type=click.Choice([item.value for item in LLMProvider]), help="LLM provider.")
@click.option("--model", help="Model name or Azure deployment-compatible model name.")
@click.option("--api-key", help="Provider API key. Prefer environment variables for regular use.")
@click.option("--base-url", help="OpenAI-compatible or Ollama base URL.")
@click.option("--azure-endpoint", help="Azure OpenAI endpoint ending in /openai/v1/ when applicable.")
@click.option("--azure-api-key", help="Azure OpenAI API key. Prefer environment variables for regular use.")
@click.option("--azure-api-version", help="Azure OpenAI API version.")
@click.option("--timeout-seconds", type=float, help="Provider timeout in seconds.")
@click.option("--max-retries", type=int, help="Number of provider retries after the initial attempt.")
@click.option("--output-mode", type=click.Choice([item.value for item in LLMOutputMode]), help="Structured output mode.")
@click.option("--allow-output-fallback/--no-output-fallback", default=None, help="Retry with fallback output mode on provider failure.")
@click.option("--prompt-grounding-hint-limit", type=int, help="Number of cache hints to add to the prompt.")
@click.option("--sensitivity", type=click.Choice([item.value for item in Sensitivity]), default="PA", show_default=True)
@click.option("--langsmith-tracing/--no-langsmith-tracing", default=None, help="Override LANGSMITH_TRACING.")
@click.option("--return-json", is_flag=True, help="Print validated JSON instead of markdown.")
@click.option("--system-prompt", help="Override the default system prompt.")
@click.option("--text", help="Report text to summarize.")
@click.option("--file", "file_path", type=click.Path(exists=True, dir_okay=False), help="Text/markdown report file.")
@click.option("--url", help="Report URL to fetch and summarize.")
def main(
    provider: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    azure_endpoint: str | None,
    azure_api_key: str | None,
    azure_api_version: str | None,
    timeout_seconds: float | None,
    max_retries: int | None,
    output_mode: str | None,
    allow_output_fallback: bool | None,
    prompt_grounding_hint_limit: int | None,
    sensitivity: str,
    langsmith_tracing: bool | None,
    return_json: bool,
    system_prompt: str | None,
    text: str | None,
    file_path: str | None,
    url: str | None,
) -> None:
    """Summarize a CTI report from text, file, or URL."""
    llm_settings = LLMSettings().with_overrides(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        azure_endpoint=azure_endpoint,
        azure_api_key=azure_api_key,
        azure_api_version=azure_api_version,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        output_mode=output_mode,
        allow_output_fallback=allow_output_fallback,
        prompt_grounding_hint_limit=prompt_grounding_hint_limit,
    )
    langsmith_settings = LangSmithSettings().with_overrides(tracing=langsmith_tracing)
    app_settings = AppSettings()
    report_text = _read_input(text, file_path, url)
    prompt = system_prompt or app_settings.system_prompt
    input_mode = "text" if text is not None else "file" if file_path is not None else "url"

    try:
        result = asyncio.run(
            CTISummarizer(
                llm_settings,
                langsmith_settings=langsmith_settings,
                trace_context=TraceContext(
                    sensitivity=Sensitivity(sensitivity),
                    input_mode=input_mode,
                ),
            ).summarize(report_text, prompt)
        )
    except SummarizationError as exc:
        raise click.ClickException(str(exc)) from exc

    if return_json:
        click.echo(json.dumps(summary_to_jsonable(result.summary), indent=2, sort_keys=True))
    else:
        click.echo(render_summary_markdown(result.summary))


if __name__ == "__main__":
    main()
