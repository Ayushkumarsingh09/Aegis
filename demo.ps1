#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== Aegis Platform Demo ===" -ForegroundColor Cyan

Write-Host "[1/6] Installing platform packages..."
python scripts/install-platform.py

Write-Host "[2/6] Seeding sample data..."
Set-Location aegis-quant
python scripts/generate_sample_data.py
python -c @"
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.data.connectors import CSVConnector
e = MarketDataEngine()
e.ingest(CSVConnector('data/sample'), 'BTC-USD')
e.ingest(CSVConnector('data/sample'), 'ETH-USD')
print('Data seeded')
"@
Set-Location $Root

Write-Host "[3/6] Running tests..."
pytest execution/tests options/tests market-maker/tests analytics/tests aegis-quant/tests -q --tb=no

Write-Host "[4/6] Starting Quant API..."
$quantJob = Start-Job { Set-Location $using:Root/aegis-quant; python -m uvicorn aegis_quant.api.app:app --host 127.0.0.1 --port 8090 }
Start-Sleep -Seconds 4

Write-Host "[5/6] Starting Portal & Dashboard..."
$portalJob = Start-Job { Set-Location $using:Root/portal; npm run dev -- --host 127.0.0.1 --port 3000 2>&1 }
$dashJob = Start-Job { Set-Location $using:Root/aegis-quant/dashboard; npm run dev -- --host 127.0.0.1 --port 4100 2>&1 }
Start-Sleep -Seconds 5

Write-Host "[6/6] Demo API calls..."
try {
    $health = Invoke-RestMethod http://127.0.0.1:8090/health -TimeoutSec 5
    Write-Host "  Health: $($health.status)" -ForegroundColor Green
    $bt = Invoke-RestMethod -Method POST http://127.0.0.1:8090/api/v1/backtest `
        -ContentType "application/json" -Body '{"strategy":"momentum","symbol":"BTC-USD"}' -TimeoutSec 30
    Write-Host "  Backtest Sharpe: $($bt.metrics.sharpe)" -ForegroundColor Green
} catch {
    Write-Host "  API not ready yet — services still starting" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Aegis Platform Running ===" -ForegroundColor Green
Write-Host "  Portal:     http://localhost:3000"
Write-Host "  Quant API:  http://localhost:8090/docs"
Write-Host "  Dashboard:  http://localhost:4100"
Write-Host ""

Start-Process "http://localhost:3000"
Start-Process "http://localhost:4100"
Start-Process "http://localhost:8090/docs"

Write-Host "Press Enter to stop all services..."
Read-Host
Stop-Job $quantJob, $portalJob, $dashJob -ErrorAction SilentlyContinue
Remove-Job $quantJob, $portalJob, $dashJob -ErrorAction SilentlyContinue
