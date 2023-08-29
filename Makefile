VERSION=`cat VERSION.txt`

all:	app/*.py requirements.txt Dockerfile docker-compose.yml static/* templates/*
	docker build -t openai-summarizer:$(VERSION) . --network=host && docker compose down && docker compose  --env-file .env up -d
