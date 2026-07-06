#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Aegis Platform Demo ==="

echo "[1/6] Installing platform packages..."
python3 scripts/install-platform.py

echo "[2/6] Seeding sample data..."
cd aegis-quant
python3 scripts/generate_sample_data.py
python3 -c "
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.data.connectors import CSVConnector
e = MarketDataEngine()
e.ingest(CSVConnector('data/sample'), 'BTC-USD')
e.ingest(CSVConnector('data/sample'), 'ETH-USD')
print('Data seeded')
"
cd "$ROOT"

echo "[3/6] Running tests..."
pytest execution/tests options/tests market-maker/tests analytics/tests aegis-quant/tests -q --tb=no

echo "[4/6] Starting Quant API..."
cd aegis-quant
python3 -m uvicorn aegis_quant.api.app:app --host 127.0.0.1 --port 8090 &
QUANT_PID=$!
cd "$ROOT"
sleep 3

echo "[5/6] Starting Portal & Dashboard..."
cd portal && npm install --silent && npm run dev -- --host 127.0.0.1 --port 3000 &
PORTAL_PID=$!
cd "$ROOT/aegis-quant/dashboard" && npm run dev -- --host 127.0.0.1 --port 4100 &
DASH_PID=$!
sleep 4

echo "[6/6] Demo API calls..."
curl -sf http://127.0.0.1:8090/health | head -c 200
echo ""
curl -sf -X POST http://127.0.0.1:8090/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d '{"strategy":"momentum","symbol":"BTC-USD"}' | head -c 300
echo ""

echo ""
echo "=== Aegis Platform Running ==="
echo "  Portal:     http://localhost:3000"
echo "  Quant API:  http://localhost:8090/docs"
echo "  Dashboard:  http://localhost:4100"
echo ""
echo "Press Ctrl+C to stop"

trap "kill $QUANT_PID $PORTAL_PID $DASH_PID 2>/dev/null" EXIT
wait
