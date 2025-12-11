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
