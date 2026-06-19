.PHONY: help dev up down build test clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ──

dev: ## Start all services in development mode
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build

up: ## Start all services in production mode
	docker compose -f docker/docker-compose.yml up -d --build

down: ## Stop all services
	docker compose -f docker/docker-compose.yml down

logs: ## View service logs
	docker compose -f docker/docker-compose.yml logs -f

# ── Build ──

build: ## Build all Docker images
	docker compose -f docker/docker-compose.yml build

build-backend: ## Build backend image
	docker build -t pdf-platform/backend:latest ./backend

build-worker: ## Build worker image
	docker build -t pdf-platform/worker:latest ./worker

build-frontend: ## Build frontend image
	docker build -t pdf-platform/frontend:latest ./frontend

# ── Testing ──

test: ## Run all tests
	cd backend && pytest tests/ -v --cov=app
	cd frontend && npm test

test-backend: ## Run backend tests
	cd backend && pytest tests/ -v --cov=app

test-frontend: ## Run frontend tests
	cd frontend && npm test

lint: ## Run linters
	cd backend && ruff check .
	cd frontend && npm run lint

# ── Database ──

db-migrate: ## Run database migrations
	cd backend && alembic upgrade head

db-reset: ## Reset database
	docker compose -f docker/docker-compose.yml exec postgres psql -U pdf_admin -d pdf_platform -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	make db-migrate

# ── Utilities ──

clean: ## Remove all containers, volumes, and images
	docker compose -f docker/docker-compose.yml down -v --rmi all

status: ## Show service status
	docker compose -f docker/docker-compose.yml ps

shell-backend: ## Open shell in backend container
	docker compose -f docker/docker-compose.yml exec backend /bin/bash

shell-worker: ## Open shell in worker container
	docker compose -f docker/docker-compose.yml exec worker /bin/bash

# ── Kubernetes ──

k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/backend-deployment.yaml
	kubectl apply -f k8s/worker-frontend-deployment.yaml
	kubectl apply -f k8s/ingress.yaml

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -f k8s/ --ignore-not-found
