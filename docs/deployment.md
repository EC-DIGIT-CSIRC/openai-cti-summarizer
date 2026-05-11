# Deployment

This document describes the supported deployment flow for this repository.

## Supported Path

The supported admin path is Docker Compose behind Traefik.

Other reverse proxies can work, including Nginx, Apache, HAProxy, and Caddy. They are not covered here.

## Prerequisites

- Docker and Docker Compose
- A reverse proxy such as Traefik
- An external Docker network named `web`
- DNS record for `SERVERNAME`
- LLM provider credentials

Create the network if it does not already exist:

```bash
docker network create web
```

## Environment

Create `.env`:

```bash
cp env.example .env
```

Edit `.env`. See [Configuration](configuration.md).

Validate:

```bash
docker compose config --quiet
```

## Build And Start

```bash
docker compose up -d --build
```

The service container listens on port `9999`. The Compose file publishes host port `9001` and adds Traefik labels for HTTPS routing.

## Update

```bash
docker compose pull
docker compose up -d --build
```

If you use the Makefile:

```bash
make all
```

## Stop

```bash
docker compose down
```

## Logs

```bash
docker compose logs -f openai-summarizer
```

## TLS Modes

Let's Encrypt via Traefik resolver:

```env
TRAEFIK_TLS_CERT_RESOLVER=le
```

Local or externally configured certificate in Traefik:

```env
TRAEFIK_TLS_CERT_RESOLVER=
```

The app itself does not terminate TLS.

## Smoke Test

Set dry-run mode:

```env
DRY_RUN=1
```

Restart the service, open the web UI, submit sample text, and confirm that the sample response is rendered. Then disable dry-run and test the configured provider.
