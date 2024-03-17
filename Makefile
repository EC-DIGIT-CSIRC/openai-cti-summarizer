VERSION=$(shell cat VERSION.txt)


restart:
	docker compose down && docker compose  --env-file .env up -d

all:	app/*.py requirements.txt Dockerfile docker-compose.yml static/* templates/*
	@echo "Building version $(VERSION)" 
	docker build -t openai-summarizer:$(VERSION) . --network=host && docker compose down && docker compose  --env-file .env up -d
