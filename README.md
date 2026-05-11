# OpenAI CTI Summarizer

FastAPI service and simple web frontend for summarizing Cyber Threat Intelligence (CTI) reports into a validated structured schema.

The service accepts CTI report input as:

- a URL to an HTML/text/PDF-style report page
- pasted report text
- an uploaded PDF

The report text is extracted, converted where needed, sent to a configured LLM provider, validated as `CTISummary`, and then returned either as JSON or rendered markdown.

## Documentation

- [User Guide](docs/user-guide.md): short guide for analysts using the web UI.
- [Admin Guide](docs/admin-guide.md): deployment and operations with Docker Compose and Traefik.
- [Developer Guide](docs/developer-guide.md): local setup, architecture, tests, and contribution notes.
- [Configuration](docs/configuration.md): environment variables and `.env` syntax.
- [Deployment](docs/deployment.md): deployment flow and reverse proxy notes.
- [API](docs/api.md): HTTP and CLI surfaces.

## Quick Start For Developers

```bash
uv sync
uv run pytest
```

Run locally:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 9999
```

## Quick Start For Admins

```bash
cp env.example .env
docker compose config --quiet
docker compose up -d
```

See [Admin Guide](docs/admin-guide.md) before deploying. The documented reverse proxy example is Traefik, but the app can run behind other reverse proxies.

## License

This code is released under the [EUPL license 1.2](LICENSE.txt).
