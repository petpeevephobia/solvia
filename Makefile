# Solvia Makefile
# Simplify Docker and deployment commands

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_PROD = $(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml
APP_NAME = solvia-app
DOMAIN ?= localhost

# Development Commands
.PHONY: dev
dev: ## Start development environment
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

.PHONY: dev-build
dev-build: ## Build and start development environment
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up --build

.PHONY: dev-stop
dev-stop: ## Stop development environment
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml stop

.PHONY: dev-down
dev-down: ## Stop and remove development containers
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down

.PHONY: dev-logs
dev-logs: ## Show development logs
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml logs -f

.PHONY: dev-shell
dev-shell: ## Enter app container shell
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml exec app /bin/bash

.PHONY: dev-test
dev-test: ## Run tests in development
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml exec app pytest

# Production Commands
.PHONY: prod-up
prod-up: ## Start production environment
	DOMAIN=$(DOMAIN) $(DOCKER_COMPOSE_PROD) up -d

.PHONY: prod-build
prod-build: ## Build production images
	$(DOCKER_COMPOSE_PROD) build \
		--build-arg BUILD_VERSION=$$(git describe --tags --always) \
		--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ")

.PHONY: prod-deploy
prod-deploy: prod-build prod-up ## Build and deploy production

.PHONY: prod-stop
prod-stop: ## Stop production environment
	$(DOCKER_COMPOSE_PROD) stop

.PHONY: prod-down
prod-down: ## Stop and remove production containers
	$(DOCKER_COMPOSE_PROD) down

.PHONY: prod-logs
prod-logs: ## Show production logs
	$(DOCKER_COMPOSE_PROD) logs -f

.PHONY: prod-ps
prod-ps: ## Show production container status
	$(DOCKER_COMPOSE_PROD) ps

# Database Commands
.PHONY: db-migrate
db-migrate: ## Run database migrations
	$(DOCKER_COMPOSE) exec app python -m app.database.migrate

.PHONY: db-backup
db-backup: ## Create database backup
	@mkdir -p backups
	@BACKUP_FILE="backups/solvia-backup-$$(date +%Y%m%d-%H%M%S).sql"
	@echo "Creating backup: $$BACKUP_FILE"
	$(DOCKER_COMPOSE) exec -T app python -c "from app.database import export_data; export_data()" > $$BACKUP_FILE
	@echo "Backup created successfully"

.PHONY: db-restore
db-restore: ## Restore database from backup (BACKUP_FILE=path/to/backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Please specify BACKUP_FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) exec -T app python -c "from app.database import import_data; import_data()" < $(BACKUP_FILE)

# Utility Commands
.PHONY: clean
clean: ## Clean up Docker resources
	docker system prune -f
	docker volume prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

.PHONY: lint
lint: ## Run code linting
	$(DOCKER_COMPOSE) exec app python -m flake8 app/
	$(DOCKER_COMPOSE) exec app python -m black --check app/
	$(DOCKER_COMPOSE) exec app python -m isort --check-only app/

.PHONY: format
format: ## Format code
	$(DOCKER_COMPOSE) exec app python -m black app/
	$(DOCKER_COMPOSE) exec app python -m isort app/

.PHONY: security
security: ## Run security checks
	$(DOCKER_COMPOSE) exec app python -m bandit -r app/
	$(DOCKER_COMPOSE) exec app python -m safety check

.PHONY: stats
stats: ## Show Docker stats
	docker stats --no-stream

.PHONY: build
build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

.PHONY: pull
pull: ## Pull latest Docker images
	$(DOCKER_COMPOSE) pull

.PHONY: restart
restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

.PHONY: caddy-reload
caddy-reload: ## Reload Caddy configuration
	$(DOCKER_COMPOSE) exec caddy caddy reload --config /etc/caddy/Caddyfile

.PHONY: caddy-fmt
caddy-fmt: ## Format Caddyfile
	$(DOCKER_COMPOSE) exec caddy caddy fmt --overwrite /etc/caddy/Caddyfile

# Installation Commands
.PHONY: install
install: ## Initial setup for development
	@echo "Setting up Solvia development environment..."
	@cp .env.example .env
	@echo "Please edit .env with your configuration"
	@make dev-build

.PHONY: uninstall
uninstall: ## Remove all containers and volumes
	$(DOCKER_COMPOSE) down -v
	docker rmi $(APP_NAME):latest 2>/dev/null || true

# Monitoring Commands
.PHONY: health
health: ## Check service health
	@echo "Checking service health..."
	@curl -f http://localhost/health || echo "App health check failed"
	@curl -f http://localhost:8080/health || echo "Caddy health check failed"

.PHONY: metrics
metrics: ## Show metrics
	@curl -s http://localhost:8080/metrics

# Server Commands (requires SSH access)
.PHONY: server-setup
server-setup: ## Setup production server
	./deploy.sh setup

.PHONY: server-deploy
server-deploy: ## Deploy to production server
	./deploy.sh deploy

.PHONY: server-status
server-status: ## Check production server status
	./deploy.sh status

.PHONY: server-rollback
server-rollback: ## Rollback production deployment
	./deploy.sh rollback

# Quick Commands
.PHONY: up
up: dev ## Alias for dev

.PHONY: down
down: dev-down ## Alias for dev-down

.PHONY: logs
logs: dev-logs ## Alias for dev-logs

.PHONY: shell
shell: dev-shell ## Alias for dev-shell

.PHONY: ps
ps: ## Show all container status
	$(DOCKER_COMPOSE) ps

# Testing shortcuts
.PHONY: test
test: dev-test ## Alias for dev-test

.PHONY: test-unit
test-unit: ## Run unit tests only
	$(DOCKER_COMPOSE) exec app pytest tests/unit

.PHONY: test-integration
test-integration: ## Run integration tests only
	$(DOCKER_COMPOSE) exec app pytest tests/integration

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	$(DOCKER_COMPOSE) exec app pytest --cov=app --cov-report=html

# Version information
.PHONY: version
version: ## Show version information
	@echo "Solvia Version: $$(git describe --tags --always)"
	@echo "Build Date: $$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
	@echo "Docker Version: $$(docker --version)"
	@echo "Docker Compose Version: $$(docker-compose --version)"