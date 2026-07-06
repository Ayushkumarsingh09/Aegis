# Getting Started

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| Docker | 24+ (optional) |
| CMake | 3.20+ (exchange build) |
| C++20 compiler | GCC 11+ / Clang 14+ |

## One-Command Demo

```powershell
# Windows
.\demo.ps1

# Linux/macOS
./demo.sh
```

## Manual Setup

### 1. Install Platform Packages

```bash
python scripts/install-platform.py
```

### 2. Seed Data

```bash
cd aegis-quant
python scripts/generate_sample_data.py
python -c "from aegis_quant.data.engine import MarketDataEngine; from aegis_quant.data.connectors import CSVConnector; e=MarketDataEngine(); e.ingest(CSVConnector('data/sample'),'BTC-USD'); e.ingest(CSVConnector('data/sample'),'ETH-USD')"
```

### 3. Start Services

```bash
# Terminal 1 — Quant API
cd aegis-quant && aegis-quant serve

# Terminal 2 — Portal
cd portal && npm install && npm run dev

# Terminal 3 — Research Dashboard
cd aegis-quant/dashboard && npm install && npm run dev
```

### 4. Open

- Portal: http://localhost:3000
- Research Dashboard: http://localhost:4100
- API Docs: http://localhost:8090/docs

## Docker (Full Stack)

```bash
docker compose up --build
```

## Run Tests

```bash
pytest execution/tests options/tests market-maker/tests analytics/tests aegis-quant/tests -v
```

## Exchange (C++)

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DAEGIS_BUILD_TESTS=ON
cmake --build build -j
cd build && ctest --output-on-failure
./server/aegis-server
```

## Next Steps

- [Developer Guide](developer-guide.md)
- [Platform Architecture](platform-architecture.md)
- [Deployment](deployment.md)
- [Benchmarks](benchmarks.md)
