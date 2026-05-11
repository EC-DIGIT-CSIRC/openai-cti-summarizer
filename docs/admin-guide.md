# Admin Guide

This guide is for administrators deploying and operating the service.

The documented deployment path is Docker Compose behind Traefik. Traefik is only one reverse proxy option. Nginx, Apache, HAProxy, Caddy, or another reverse proxy can also work, but this documentation only covers the Traefik case.

## Files To Know

- `docker-compose.yml`: service container, Traefik labels, network, ports, mounted app files.
- `env.example`: template for `.env`.
- `.env`: local runtime configuration. Do not commit secrets.
- `VERSION.txt`: image tag input used by Compose and the Makefile.

## Initial Setup

Create the environment file:

```bash
cp env.example .env
```

Edit `.env` and set at least:

- `SERVERNAME`
- `LLM_PROVIDER`
- `LLM_MODEL`
- provider credentials such as `LLM_API_KEY`, `OPENAI_API_KEY`, or Azure-specific values
- `BASIC_AUTH_USER`
- `BASIC_AUTH_PASSWORD`

Validate Compose parsing before deployment:

```bash
docker compose config --quiet
```

## Reverse Proxy And TLS

The app listens inside the container on port `9999`. The Compose file publishes it as `9001:9999` and also adds Traefik labels for routing through the external `web` network.

The Traefik router host comes from:

```env
SERVERNAME=cti.example.org
```

TLS is enabled by Traefik labels. Certificate resolver behavior is controlled by:

```env
TRAEFIK_TLS_CERT_RESOLVER=le
```

Use `le` for a Let's Encrypt resolver configured in Traefik.

For a certificate configured directly in Traefik, such as a local certificate signed by your own CA, set the variable to an empty value:

```env
TRAEFIK_TLS_CERT_RESOLVER=
```

The service does not generate or inspect certificates. The administrator chooses the mode explicitly.

## Docker Compose Deployment

The Compose file expects an external Docker network named `web`:

```bash
docker network create web
```

Start or update the service:

```bash
docker compose up -d --build
```

Stop it:

```bash
docker compose down
```

Inspect logs:

```bash
docker compose logs -f openai-summarizer
```

## Authentication

The web UI uses HTTP Basic auth. Configure:

```env
BASIC_AUTH_USER=<user>
BASIC_AUTH_PASSWORD=<password>
```

Use a strong password. Basic auth should be terminated over HTTPS by the reverse proxy.

## LLM Provider Setup

Supported provider values are:

- `openai`
- `azure`
- `openrouter`
- `ollama`
- `anthropic`

Provider selection and credentials are documented in [Configuration](configuration.md).

## JSON Output Mode

By default the web endpoint renders markdown into HTML. Set:

```env
OUTPUT_JSON=true
```

to return validated JSON directly.

## Dry Run

Set:

```env
DRY_RUN=1
```

to return a sample response without calling an LLM provider.

## Troubleshooting

If `docker compose` reports `.env` parse errors, check multiline values. Compose-compatible multiline values must be quoted:

```env
SYSTEM_PROMPT='first line
second line'
```

Do not use heredoc syntax such as `SYSTEM_PROMPT=<<EOT`.

If Traefik does not route to the app:

- verify `SERVERNAME`
- verify the external `web` network exists
- verify Traefik is attached to the same network
- verify the configured certificate resolver exists, or set `TRAEFIK_TLS_CERT_RESOLVER=` for direct Traefik certificate configuration

If summaries fail:

- check provider credentials
- check `LLM_PROVIDER` and `LLM_MODEL`
- inspect `docker compose logs -f openai-summarizer`
- test with `DRY_RUN=1` to isolate app/UI behavior from provider behavior
