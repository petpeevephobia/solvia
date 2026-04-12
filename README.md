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
- **Make** — included on macOS/Linux; on Windows install via [Chocolatey](https://chocolatey.org/) (`choco install make`), [Scoop](https://scoop.sh/), or [Git for Windows](https://gitforwindows.org/) (includes `make` in Git Bash; `make setup` still works from PowerShell when `make` is on your `PATH`)

## Setup (New Device)

Use a **single `.env` at the repository root** (not under `api/`). Docker Compose, `make setup`, and the Go API (via `../.env` when started from `api/`) all expect that file.

### 1. Copy your `.env`

The `.env` file is not committed to version control. Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

On Windows (cmd or PowerShell), if `cp` is not available:

```bat
copy .env.example .env
```

Then open `.env` and set the real values for:
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — from [Google Cloud Console](https://console.cloud.google.com/)
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
- `FIRECRAWL_API_KEY` — from [Firecrawl](https://www.firecrawl.dev/)
- `JWT_SECRET` — any long random string
- `POSTGRES_PASSWORD` — your chosen local DB password (must match `DATABASE_URL`)

Optional keys (`SUPABASE_*`, `SMTP_*`, etc.) are listed in `.env.example`; leave them blank unless you use those integrations. Docker Compose supplies empty defaults so local runs stay quiet.

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

> `make setup` = install deps + copy `.env.example` → `.env` (Windows: `copy` when `cp` is unavailable) + start Postgres + run migrations.

On **Windows**, migrations are applied with `scripts/run-sql-migrations-windows.ps1` (PowerShell + `cmd`), so you do **not** need a Unix `sh` on `PATH` for `make db-migrate` or the migration step inside `make setup`.

If you previously ran an older Postgres image without pgvector, pull and recreate the DB container once so the extension is available: `docker-compose pull postgres` then `docker-compose up -d postgres --force-recreate` (or `make db-up` after a pull). This keeps your Docker volume; only recreate if migrations still fail on `CREATE EXTENSION vector`.

### 4. Start development

```bash
make dev
```

This starts:
- Docker services (PostgreSQL, Redis) via `docker-compose up -d`
- Go API at **http://localhost:8080**
- React dev server at **http://localhost:3000**

On **Windows**, `make dev` uses `scripts/run-dev-windows.ps1`: the API runs in a **minimized** console window, then the web app runs in your **current** terminal. On macOS/Linux, the API and web still run from the same shell recipe as before.

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
- PostgreSQL 16 (Docker image with pgvector)
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
