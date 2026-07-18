.PHONY: help build up down logs clean restart

PROJECT_NAME = KubePilot

help:
	@echo "\033[36m--- $(PROJECT_NAME) : Commandes d'administration ---\033[0m"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[32m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f kubepilot

clean:
	docker compose down --rmi all --volumes --remove-orphans