FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md VERSION.txt ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY templates ./templates
COPY static ./static

# expose the port for the FastAPI application
EXPOSE 9999

# run the FastAPI application
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--access-log", "--host", "0.0.0.0", "--port", "9999"]
