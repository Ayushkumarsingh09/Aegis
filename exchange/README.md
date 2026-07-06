# Exchange Module

The **Aegis Exchange** matching engine and related C++ infrastructure lives at the repository root.

## Components

| Directory | Module |
|-----------|--------|
| `core/` | Types, memory pool, metrics, clock |
| `orderbook/` | Price-time priority order book |
| `matching-engine/` | Order matching (Limit, Market, IOC, FOK, etc.) |
| `risk/` | Pre-trade risk validation, kill switch |
| `market-data/` | Publisher, recorder, replay engine |
| `gateway/` | REST API + WebSocket/SSE streaming |
| `server/` | Exchange process (`aegis-server`) |

## Quick Start

```bash
docker compose up --build
# API: http://localhost:9080
# Dashboard: http://localhost:4000
```

See [README](../README.md) and [docs/architecture.md](../docs/architecture.md).
