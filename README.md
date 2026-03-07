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

### Quick start (local)

Run the API and frontend on your machine with hot reload (Postgres in Docker): copy `.env` to `api/.env`, set `DATABASE_URL=...@localhost:5432/...`, start Postgres with `docker-compose up -d postgres` (ensure `postgres` has `ports: "5432:5432"`), then run the API (`cd api && go run ./cmd/api`) and frontend (`make web`). Full steps: [Local Development Guide](./docs/LOCAL_DEV.md).

## Tech Stack

### Backend
- Go 1.23 + Gin
- PostgreSQL 17
- Clean Architecture (Modular Monolith)

### Frontend
- React 18 + TypeScript
- Vite + TailwindCSS
- React Query + Zustand

## Commands

```bash
make help       # Show all commands
make dev        # Start all services
make api        # Start API only
make web        # Start frontend only
make test       # Run tests
make build      # Build for production
```

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [API Reference](./docs/API.md)
- [Deployment](./docs/DEPLOYMENT.md)
- [Local Development](./docs/LOCAL_DEV.md)
