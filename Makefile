# Solvia v2 Monorepo Makefile
# ============================

.PHONY: help dev build test lint clean docker-up docker-down api web db

# Colors
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

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
	@echo "$(GREEN)All services started!$(RESET)"
	@echo "API:    http://localhost:8080"
	@echo "Web:    http://localhost:3000 (if enabled)"
	@echo "DB:     localhost:5432"

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

db-up:
	docker-compose up -d postgres
	@echo "$(GREEN)PostgreSQL started on localhost:5432$(RESET)"

db-migrate:
	@echo "$(CYAN)Running migrations...$(RESET)"
	docker-compose exec postgres psql -U solvia -d solvia -f /docker-entrypoint-initdb.d/001_init.sql

db-reset:
	@echo "$(YELLOW)Resetting database...$(RESET)"
	docker-compose exec postgres psql -U solvia -d solvia -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) db-migrate

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
	cp .env.example .env
	$(MAKE) db-up
	sleep 5
	$(MAKE) db-migrate
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
