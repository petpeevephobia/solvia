# Solvia v2

SEO audit tool with Golang backend and React frontend.

## Architecture

```
solvia-v2/
├── api/              # Go backend (Gin + Clean Architecture)
├── web/              # React frontend (TypeScript + Vite)
├── migrations/       # PostgreSQL migrations
├── scripts/          # Utility scripts
└── docker-compose.yml
```

## Prerequisites

Before you can run this project, install the following tools:

- **Go 1.24** — [https://go.dev/dl/](https://go.dev/dl/) *(version required: see `api/go.mod`)*
- **Node.js 18+** with npm — [https://nodejs.org](https://nodejs.org) *(React 18 + Vite 5 require Node 18+)*
- **Docker Desktop** — [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) *(runs PostgreSQL and Redis)*
- **Make** — included on macOS/Linux; on Windows install via [Git Bash](https://gitforwindows.org/) or [Chocolatey](https://chocolatey.org/) (`choco install make`)

## Setup (New Device)

### 1. Copy your `.env`

The `.env` file is not committed to version control. Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Then open `.env` and set the real values for:
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — from [Google Cloud Console](https://console.cloud.google.com/)
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
- `FIRECRAWL_API_KEY` — from [Firecrawl](https://www.firecrawl.dev/)
- `JWT_SECRET` — any long random string
- `POSTGRES_PASSWORD` — your chosen local DB password (must match `DATABASE_URL`)

### 2. Install dependencies

```bash
# Install Go modules
cd api && go mod download && cd ..

# Install Node modules
cd web && npm install && cd ..
```

Or run both at once:

```bash
make install
```

### 3. Start the database and run migrations

```bash
# Start PostgreSQL via Docker
make db-up

# Run all SQL migrations
make db-migrate
```

Or do all of the above in one command:

```bash
make setup
```

> `make setup` = install deps + copy `.env.example` → `.env` + start Postgres + run migrations.

### 4. Start development

```bash
make dev
```

This starts:
- Docker services (PostgreSQL, Redis) via `docker-compose up -d`
- Go API at **http://localhost:8080**
- React dev server at **http://localhost:3000**

## Quick Start

```bash
# 1. Setup
make setup

# 2. Start development
make dev

# 3. Access
# API:  http://localhost:8080
# Web:  http://localhost:3000
```

## Tech Stack

### Backend
- Go 1.24 + Gin
- PostgreSQL 17
- Clean Architecture (Modular Monolith)

### Frontend
- React 18 + TypeScript
- Vite 5 + TailwindCSS
- React Query + Zustand

## Commands

```bash
make help         # Show all commands
make dev          # Start all services (Docker + API + Web)
make api          # Start API only (with hot reload via air)
make web          # Start frontend only
make test         # Run all tests
make build        # Build for production
make db-migrate   # Run SQL migrations
make db-reset     # Drop and re-run all migrations
make db-shell     # Open psql shell inside Docker
make docker-down  # Stop all Docker services
make clean        # Remove build artifacts
```

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [API Reference](./docs/API.md)
- [Deployment](./docs/DEPLOYMENT.md)
- [Local Development](./docs/LOCAL_DEV.md)
