# API

The service exposes a small web/API surface through FastAPI and a CLI entry point.

## Web Endpoints

### `GET /`

Returns the HTML form.

Requires HTTP Basic auth.

### `POST /`

Submits a report for summarization.

Requires HTTP Basic auth.

Form fields:

- `url`: report URL
- `pdffile`: uploaded PDF
- `text`: pasted report text
- `system_prompt`: optional prompt override
- `model`: optional model override

Provide one of `url`, `pdffile`, or `text`.

Response behavior:

- If `OUTPUT_JSON=false`, returns HTML containing rendered markdown.
- If `OUTPUT_JSON=true`, returns validated JSON.

## Structured Output

The validated output model is `CTISummary` in `app/schema.py`.

Main fields:

- `summary`
- `key_points`
- `ttps`
- `indicators`
- `threat_actors`
- `confidence_score`
- `report_metadata`
- `yara_rules`

## CLI

The CLI entry point is `cti-summarizer`.

Examples:

```bash
uv run cti-summarizer --file sample-data.txt
uv run cti-summarizer --file sample-data.txt --return-json
uv run cti-summarizer --url https://example.org/report.html
uv run cti-summarizer --text "Report text"
```

Provider overrides:

```bash
uv run cti-summarizer \
  --provider openai \
  --model gpt-5.5 \
  --file sample-data.txt \
  --return-json
```

The CLI reads the same environment-backed settings as the web app and allows selected overrides through command-line options.
