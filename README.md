# Markeitech

Markeitech is a greenfield market-analysis, strategy-research, backtesting, replay, dashboard, and later live-trading platform for discretionary and systematic futures trading.

Initial focus is explicit-expiry NQ futures through Interactive Brokers, with NautilusTrader used as the primary trading-system runtime wherever practical.

## Stage 0 Scope

This repository is currently bootstrapped only through Stage 0:

- Python 3.13 uv project
- NautilusTrader with Interactive Brokers and Docker extras declared
- FastAPI backend skeleton
- SQLite-ready standard-library persistence boundary
- Redis and Parquet dependencies declared
- pytest, ruff, and black configured
- Vite + React + TypeScript frontend skeleton
- Architecture and setup documentation

Trading execution is intentionally not implemented. Data-only mode is the default and only Stage 0 posture.

## Requirements

- Python 3.13
- uv
- Node.js 22.12 or newer for the frontend
- npm

The current Vite release requires Node.js 20.19+ or 22.12+. If your shell reports Node 22.4, upgrade Node before running the frontend dev server.

## Backend Setup

```bash
uv sync
uv run pytest
uv run ruff check .
uv run black --check .
uv run fastapi dev backend/src/markeitech/api.py
```

The backend exposes:

- `GET /health`
- `GET /readiness`

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Copy `.env.example` to `.env` when running locally. Stage 0 docs require:

- explicit NQ contract configuration before market-data startup
- IB Gateway or TWS timestamps configured to UTC
- IB read-only/data-only mode by default
- no live execution unless a later stage explicitly enables it

## Documentation

- [Project context](docs/00-project-context.md)
- [Decisions register](docs/01-decisions-register.md)
- [Phased implementation plan](docs/02-phased-implementation-plan.md)
- [Runtime architecture](docs/runtime-architecture.md)
- [Data contracts](docs/data-contracts.md)
- [Interactive Brokers setup](docs/ib-setup.md)
