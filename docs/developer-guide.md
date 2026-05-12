# Developer Guide

This guide is for contributors working on the codebase.

## Local Setup

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check app tests
```

Run the web app locally:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 9999
```

## Project Layout

```text
app/
  main.py          FastAPI app, routes, URL/PDF/text ingestion
  auth.py          Basic auth dependency
  config.py        Pydantic settings loaded from environment
  schema.py        CTISummary schema and grounding cache helpers
  summarizer.py    LLM provider construction and structured summarization
  rendering.py     Markdown and JSON rendering helpers
  cli.py           CLI entry point
templates/
  index.html       Simple web UI
static/            CSS and static assets
tests/             Pytest suite
docs/              Project documentation
```

## Architecture

The service accepts report input through the web UI or CLI. URL and HTML inputs are converted with BeautifulSoup. PDF input is converted with PyMuPDF. The resulting text is sent to `CTISummarizer`.

`CTISummarizer` builds a Pydantic AI model from `LLMSettings`, requests a structured `CTISummary`, validates the result, and returns operational metadata such as duration and usage when available.

Rendered markdown is produced locally from the validated schema. The LLM is not expected to produce final HTML.

## Configuration Changes

Add new environment-backed settings in `app/config.py` using Pydantic settings. Mirror stable variables in `env.example` and document them in [Configuration](configuration.md).

When adding settings, include tests in `tests/test_config.py`.

## Provider Changes

Provider construction lives in `app/summarizer.py`.

When adding or changing provider behavior:

- keep provider-specific code isolated in `_build_pydantic_ai_model`
- add tests in `tests/test_summarizer.py`
- avoid breaking OpenAI-compatible APIs when adding OpenAI-specific features
- keep timeout, retry, and structured output behavior explicit

## Schema Changes

The public structured output is `CTISummary` in `app/schema.py`.

When adding fields:

- update the Pydantic model
- update rendering in `app/rendering.py`
- update tests
- update prompt/config documentation when the LLM should fill the field
- keep optional fields optional when reports may not support them

## Prompt Changes

The default prompt is configured by `SYSTEM_PROMPT`. The code also appends grounding hints and guardrails in `CTISummarizer._build_instructions`.

Prompt changes should preserve these rules:

- extract only report-supported facts
- do not infer or enrich missing details
- prefer MITRE ATT&CK and Malpedia canonical values when supported
- keep YARA rules empty unless the report contains enough concrete evidence

## CLI

The `cti-summarizer` script is defined in `pyproject.toml` and implemented in `app/cli.py`.

Example:

```bash
uv run cti-summarizer --file sample-data.txt --return-json
```

## Testing Expectations

Run at least:

```bash
uv run pytest
uv run ruff check app tests
```

For deployment-related changes, also run:

```bash
docker compose config --quiet
```

Add tests for every meaningful behavior change. Tests should cover both success and failure paths where practical.

## Known Gaps And Planned Work

- OTEL metrics/tracing configuration is not implemented yet. The documentation has a placeholder in [Configuration](configuration.md).
- Reverse proxy examples only cover Traefik.
- The user guide is intentionally short because the UI is expected to change.
- The README has been modernized into an entry point; detailed operational content belongs in `docs/`.
- Some legacy files remain for reference or compatibility. Prefer `pyproject.toml` and `uv` over `requirements.txt`.
