# Aegis Platform Demo

Automated demonstration of the unified trading platform.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (optional, for full stack)

## Quick Demo (Local)

### Windows
```powershell
.\demo.ps1
```

### Linux / macOS
```bash
chmod +x demo.sh
./demo.sh
```

## What the Demo Does

1. Installs all Python platform packages
2. Seeds sample market data (BTC-USD, ETH-USD)
3. Starts Quant API (port 8090)
4. Starts Portal homepage (port 3000)
5. Starts Quant Research Dashboard (port 4100)
6. Opens browser to the unified portal

## Manual Workflows

### Run a Backtest
```bash
curl -X POST http://localhost:8090/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d '{"strategy":"momentum","symbol":"BTC-USD"}'
```

### Price an Option
```bash
curl -X POST http://localhost:8090/api/v1/options/price \
  -H "Content-Type: application/json" \
  -d '{"spot":100,"strike":100,"expiry":1.0,"volatility":0.2,"option_type":"call"}'
```

### Simulate Execution
```bash
curl -X POST http://localhost:8090/api/v1/execution/simulate \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC-USD","quantity":100,"algorithm":"twap","n_slices":10}'
```

### Simulate Market Making
```bash
curl -X POST http://localhost:8090/api/v1/market-maker/simulate \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC-USD","gamma":0.1}'
```

## Full Stack (Docker)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Portal | http://localhost:3000 |
| Exchange Dashboard | http://localhost:4000 |
| Quant Dashboard | http://localhost:4100 |
| Exchange API | http://localhost:9080 |
| Quant API | http://localhost:8090 |
