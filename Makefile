VERSION=$(shell cat VERSION.txt)


restart:
	docker compose down && docker compose  --env-file .env up -d

all:	app/*.py pyproject.toml uv.lock Dockerfile docker-compose.yml static/* templates/*
	@echo "Building version $(VERSION)" 
	docker build -t openai-summarizer:$(VERSION) . --network=host && docker compose down && docker compose  --env-file .env up -d

tests:
	@echo "Running tests"
	uv run pytest -v

clean: 
	@echo "Cleaning up"
	docker compose down && docker rmi openai-summarizer:$(VERSION) 
