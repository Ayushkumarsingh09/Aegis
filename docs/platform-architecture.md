# Platform Architecture

Unified quantitative trading platform within a single monorepo.

## Module Map

```
Repository Root
├── exchange/          → C++ modules at root (core/, matching-engine/, etc.)
├── quant/             → aegis-quant/ Python research platform
├── execution/         → aegis_execution — TWAP, VWAP, POV, TCA
├── options/           → aegis_options — pricing, Greeks, vol surface
├── market-maker/      → aegis_market_maker — Avellaneda-Stoikov
├── analytics/         → aegis_analytics — risk, attribution, stress
├── dashboard/         → Exchange React UI
├── aegis-quant/dashboard/ → Research React UI
├── sdk/               → Python exchange client + quant SDKs
├── benchmark/         → C++ latency/throughput benchmarks
├── tests/             → C++ exchange tests
└── docker/            → Container deployment
```

## Data Flow

```
Market Data Sources (CSV, DuckDB, Yahoo, Aegis Exchange)
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│  Quant Research │────▶│ Strategy Engine  │
│  Features/ML    │     │ Backtester       │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│ Execution Algos │────▶│ Aegis Exchange   │
│ TWAP/VWAP/POV   │     │ Matching Engine  │
└─────────────────┘     └────────┬─────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Market Maker    │     │ Options Analytics│     │ Risk/Analytics│
│ Quote Engine    │     │ Greeks/Surface   │     │ VaR/Stress   │
└─────────────────┘     └──────────────────┘     └──────────────┘
```

## Services

| Service | Port | Technology |
|---------|------|------------|
| Exchange API | 9080 | C++ / httplib |
| Exchange Dashboard | 4000 | React |
| Quant API | 8090 | FastAPI |
| Quant Dashboard | 4100 | React |

## Installation

```bash
python scripts/install-platform.py   # All Python modules
docker compose up --build            # Full stack
```

## API Integration

Platform modules are exposed via the Quant API:

- `POST /api/v1/execution/simulate` — Execution algorithm simulation
- `POST /api/v1/options/price` — Option pricing + Greeks
- `GET /api/v1/options/surface` — Volatility surface grid
- `POST /api/v1/market-maker/simulate` — MM simulation
- `GET /api/v1/analytics/stress/{symbol}` — Stress testing
- `GET /api/v1/platform/status` — Module availability

## Design Principles

1. **Extend, don't rewrite** — Exchange C++ code unchanged; new modules added as Python packages
2. **Single repo** — All components versioned together
3. **Testable** — Each module has independent pytest suite (45+ tests)
4. **API-first** — All platform capabilities accessible via REST
