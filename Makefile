# Solvia v2 Monorepo Makefile
# ============================

.PHONY: help dev build test lint clean docker-up docker-down api web db

# Colors
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

# Windows vs Unix (copy and sleep). On Windows, Make uses sh (Git Bash) so "copy" isn't available; use cmd /c.
ifeq ($(OS),Windows_NT)
CP_CMD = cmd /c "copy /Y .env.example .env"
SLEEP_CMD = timeout /t 5 /nobreak > nul
else
CP_CMD = cp .env.example .env
SLEEP_CMD = sleep 5
endif

help:
	@echo ""
	@echo "$(CYAN)Solvia v2 - Available Commands$(RESET)"
	@echo "================================"
	@echo ""
	@echo "$(GREEN)Development:$(RESET)"
	@echo "  make dev          - Start all services (API + DB + Web)"
	@echo "  make api          - Start API only (hot reload)"
	@echo "  make web          - Start React dev server"
	@echo "  make build        - Build all services"
	@echo "  make test         - Run all tests"
	@echo "  make lint         - Run linters"
	@echo ""
	@echo "$(GREEN)Docker:$(RESET)"
	@echo "  make docker-up    - Start services via Docker"
	@echo "  make docker-down  - Stop all services"
	@echo "  make docker-logs  - View logs"
	@echo "  make docker-dev   - Start with dev tools (pgAdmin)"
	@echo "  make docker-prod  - Start production config"
	@echo ""
	@echo "$(GREEN)Database:$(RESET)"
	@echo "  make db-up        - Start PostgreSQL only"
	@echo "  make db-migrate   - Run migrations"
	@echo "  make db-reset     - Reset database"
	@echo "  make db-shell     - Open psql shell"
	@echo ""
	@echo "$(GREEN)Utilities:$(RESET)"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Initial project setup"
	@echo ""

# ===================
# Development
# ===================

dev: docker-up
	@echo "$(GREEN)Starting local API + Web...$(RESET)"
	@echo "API:    http://localhost:8080"
	@echo "Web:    http://localhost:3000"
	@(cd api && go run ./cmd/api) & \
	sleep 3 && cd web && npm run dev

api:
	@echo "$(CYAN)Starting API with hot reload...$(RESET)"
	cd api && air -c .air.toml

web:
	@echo "$(CYAN)Starting React dev server...$(RESET)"
	cd web && npm run dev

build:
	@echo "$(CYAN)Building all services...$(RESET)"
	cd api && go build -o ../bin/solvia-api ./cmd/api
	cd web && npm run build

test:
	@echo "$(CYAN)Running tests...$(RESET)"
	cd api && go test -v ./...
	cd web && npm test

lint:
	@echo "$(CYAN)Running linters...$(RESET)"
	cd api && golangci-lint run ./...
	cd web && npm run lint

# ===================
# Docker
# ===================

docker-up:
	@echo "$(CYAN)Starting services...$(RESET)"
	docker-compose up -d

docker-down:
	@echo "$(CYAN)Stopping services...$(RESET)"
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-dev:
	@echo "$(CYAN)Starting with dev tools...$(RESET)"
	docker-compose --profile dev up -d
	@echo "pgAdmin: http://localhost:5050"

docker-prod:
	@echo "$(CYAN)Starting production...$(RESET)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

docker-build:
	docker-compose build

docker-clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# ===================
# Database
# ===================

# Run migrations/00*.sql in order against docker-compose postgres (stdin; no init SQL mounted in the image).
# Uses sh + stdin so Windows paths with spaces work; avoids recursive $(MAKE) (breaks when MAKE path contains "(").
RUN_SQL_MIGRATIONS = sh -c 'set -e; cd "$(CURDIR)" && for f in migrations/0*.sql; do echo "=== $$f ==="; docker-compose exec -T postgres psql -U solvia -d solvia < "$$f"; done'

db-up:
	docker-compose up -d postgres
	@echo "$(GREEN)PostgreSQL started on localhost:5432$(RESET)"

db-migrate:
	@echo "$(CYAN)Running migrations...$(RESET)"
	@$(RUN_SQL_MIGRATIONS)

db-reset:
	@echo "$(YELLOW)Resetting database...$(RESET)"
	docker-compose exec postgres psql -U solvia -d solvia -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@echo "$(CYAN)Running migrations...$(RESET)"
	@$(RUN_SQL_MIGRATIONS)

db-shell:
	docker-compose exec postgres psql -U solvia -d solvia

db-backup:
	@echo "$(CYAN)Backing up database...$(RESET)"
	docker-compose exec postgres pg_dump -U solvia solvia > backups/solvia_$(shell date +%Y%m%d_%H%M%S).sql

# ===================
# Utilities
# ===================

install:
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	cd api && go mod download
	cd web && npm install

setup: install
	@echo "$(CYAN)Setting up project...$(RESET)"
	$(CP_CMD)
	docker-compose up -d postgres
	@echo "$(GREEN)PostgreSQL started on localhost:5432$(RESET)"
	$(SLEEP_CMD)
	@echo "$(CYAN)Running migrations...$(RESET)"
	@$(RUN_SQL_MIGRATIONS)
	@echo "$(GREEN)Setup complete!$(RESET)"

clean:
	@echo "$(CYAN)Cleaning...$(RESET)"
	rm -rf bin/
	rm -rf api/tmp/
	rm -rf web/dist/
	rm -rf web/node_modules/.cache/

# ===================
# API-specific
# ===================

api-build:
	cd api && go build -ldflags="-w -s" -o ../bin/solvia-api ./cmd/api

api-test:
	cd api && go test -v -cover ./...

api-lint:
	cd api && golangci-lint run ./...

api-generate:
	cd api && go generate ./...

# ===================
# Web-specific
# ===================

web-build:
	cd web && npm run build

web-test:
	cd web && npm test

web-lint:
	cd web && npm run lint

web-preview:
	cd web && npm run preview
