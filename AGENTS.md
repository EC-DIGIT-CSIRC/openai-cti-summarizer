# AGENTS

This file is for coding agents working in this repository.

## Mission

Build and maintain a FastAPI based web service plus a simple HTML webfrontend (also directly served by the FastAPI app) and a structured JSON output for summarizing Cyber Threat Intelligence (CTI) reports.

In detail: the app 
- can fetch a URL given which points to a CTI report (txt or PDF or HTML page)
- or the pure text of the CTI gets uploaded in the text area
- or a PDF of a CTI report gets uploaded

The CTI report is then parse, converted (via bs4) to markdown

After the conversion, the text is submitted together with a SYSTEM_PROMPT + a pydantic schema to the LLM provider (either openai, or an openai compatible API or MS Azure's OpenAI API).

The result shall be structured output

If the parameter "return JSON" is True, then the result is 1-1 the JSON answer from the LLM.
Otherwise, the  output is rendered as markdown and displayed at the bottom in a markdown answer field.


## Fixed Assumptions

* user supplied URLs are OK, the service is in a trusted environment and protected via firewall rules as well as via .htaccess auth


## Chosen Stack

Use this stack unless the user asks to change it.

### Runtime And Tooling

1. Python `3.13`
2. `uv` for dependency management and command execution
3. `pytest` for tests
4. fastapi for the service
5. openai client lib

### Stdlib First

Prefer the standard library for:

1. MIME parsing: `email`
2. mailbox support: `mailbox`
3. CLI: `click`
4. filesystem paths: `pathlib`
5. structured data: `json`, `pydantic`, `pydantic-settings`, `typing`, `python-multipart`
6. concurrency: `concurrent.futures`
7. timing: `time`
8. hashing: `hashlib`
9. logging: `logging`, `QueueHandler`, `QueueListener`
10. conversions: `Markdown`, `MarkupSafe`, `beautifulsoup4`
### Approved Third-Party Dependencies

Use these by default when needed:

1. `beautifulsoup4` for HTML conversion
2. `requests` for network connections. Always respect a HTTP_PROXY and HTTPS_PROXY env var whenever using it!
yarl
3. `python-dotenv` for .env file loading


### Software Supply Chain checks
1. every dependency might pull in other dependencies. This is a DAG.
2. Check those if there are known vulnerabilities
3. If possible, use github for these checks
4. Reduce the number of dependencies to a minimum
5. If a dependency (pip package) is needed, ask first before installing it.
6. Remember and pin versions and their hashes

**When something looks wrong:**
7. If a package was published <48 hours ago, flag it.
8. If a maintainer account changed recently, flag it.
9. If the package name is close to a popular package, flag it (typosquatting).

### Security and coding best practices scans
1. Use the tools in .github/workflows also locally to check (before git pushing) if they complain.
2. If one of the tools complains, try to fix it.
3. Running pytest is not sufficient for good code. 

### Approved External Tools

n/a

### Dependency Policy

Keep the baseline dependency set permissive-license friendly.

You may add GPL or AGPL dependencies even without explicit user approval.


## Packaging And Layout

Use a normal `app/` layout for the FastAPI service once implementation starts.

Target structure:

```text
pyproject.toml
app/        # for the FastAPI app
templates/  # for Jinja2 templates
static/     # for static files
tests/
  fixtures/
```

Do not create ad hoc scripts in the repository root if the code belongs in the package.

## Project Commands

Use `uv` for all local commands.

Examples:

```bash
uv sync
uv run pytest
```

Do not introduce `requirements.txt` if `pyproject.toml` can express the same thing.

## CLI Contract

Use the standard fastapi CLI tool when possible

## Implementation Rules


### 1. Logging

Logging, Traces and Metrics are a first-class feature, not an afterthought.
Use PROMETHEUS_HOST etc env vars to point to OTEL


Measure: per-step duration for each request



## Testing Expectations

Add tests as implementation grows. For every new .py file, make sure there is a decent coverage of test cases. 


## Decision Summary

When in doubt, keep these decisions fixed:

1. Python `3.13`
2. `uv`
3. FastAPI
4. generic LLM support
5. make it configurable via .env vars
