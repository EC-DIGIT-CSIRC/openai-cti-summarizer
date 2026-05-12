# Configuration

Configuration is read from environment variables. For Docker Compose deployments, copy `env.example` to `.env` and edit `.env`.

```bash
cp env.example .env
```

Do not commit `.env` because it may contain secrets.

## `.env` Syntax

Docker Compose reads `.env` before starting services. Multiline values must use quoted values:

```env
SYSTEM_PROMPT='first line
second line'
```

Do not use shell heredoc syntax:

```env
SYSTEM_PROMPT=<<EOT
...
EOT
```

Compose will reject that format.

## Service Identity

### `VERSION`

Image version/tag used by Docker Compose and the build flow.

### `SERVERNAME`

Fully qualified DNS name for the service. The Traefik label uses this value for host routing and TLS certificate selection.

## LLM Provider

### `LLM_PROVIDER`

Supported values:

- `openai`
- `azure`
- `openrouter`
- `ollama`
- `anthropic`

### `LLM_MODEL`

Model name passed to the selected provider. For Azure, this should match the deployment-compatible model name.

### `LLM_API_KEY`

Canonical app-level API key used by OpenAI, OpenRouter, Ollama cloud, or Anthropic when provider-specific variables are not preferred.

### `LLM_BASE_URL`

Optional base URL for OpenAI-compatible providers or Ollama.

Example:

```env
LLM_BASE_URL=http://localhost:11434/v1
```

## Azure OpenAI

### `LLM_AZURE_ENDPOINT`

Azure OpenAI endpoint.

### `LLM_AZURE_API_KEY`

Azure OpenAI API key.

### `LLM_AZURE_API_VERSION`

Azure OpenAI API version, when required by the endpoint.

## Structured Output

### `LLM_OUTPUT_MODE`

Structured output strategy.

Supported values:

- `native`
- `tool`
- `prompted`

Use `native` by default. Some providers or models may require `tool` or `prompted`.

### `LLM_ALLOW_OUTPUT_FALLBACK`

When `true`, provider failures during the primary output mode retry with `LLM_OUTPUT_FALLBACK_MODE`.

### `LLM_OUTPUT_FALLBACK_MODE`

Fallback structured output mode. Default example value is `tool`.

## Runtime Behavior

### `LLM_TIMEOUT_SECONDS`

Provider request timeout in seconds.

### `LLM_MAX_RETRIES`

Maximum number of retries for provider/runtime failures. Schema validation failures are not retried.

### `LLM_PROMPT_GROUNDING_HINT_LIMIT`

Maximum number of cached MITRE ATT&CK and Malpedia grounding hints added to the prompt.

### `DRY_RUN`

When set to `1` or `true`, the app returns a sample response without sending a provider request.

## Output Behavior

### `OUTPUT_JSON`

When `true`, the web endpoint returns validated JSON directly. When `false`, the app renders the validated summary as markdown HTML.

## Prompt

### `SYSTEM_PROMPT`

Default system prompt shown in the UI and used by the web endpoint when the user does not override it.

The app always asks for structured `CTISummary` output. Markdown rendering is performed locally after schema validation.

## Authentication

### `BASIC_AUTH_USER`

HTTP Basic auth username for the web UI.

### `BASIC_AUTH_PASSWORD`

HTTP Basic auth password for the web UI.

## Reverse Proxy

### `TRAEFIK_TLS_CERT_RESOLVER`

Traefik certificate resolver name.

Use:

```env
TRAEFIK_TLS_CERT_RESOLVER=le
```

for a Let's Encrypt resolver named `le`.

Use:

```env
TRAEFIK_TLS_CERT_RESOLVER=
```

to leave the resolver empty and use certificates configured directly in Traefik, such as local CA-signed certificates.

## Provider-Native Variables

Pydantic AI and provider SDKs may also read native provider variables:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY`
- `OLLAMA_BASE_URL`
- `OLLAMA_API_KEY`

Prefer one clear configuration style per deployment.

## OTEL And Observability

OTEL metrics and tracing options are planned but not documented yet.

TODO: Add supported OTEL variables, exporter configuration, Prometheus settings, and operational examples when observability support is implemented.
