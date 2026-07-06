Write-Host "=== Aegis Exchange - Docker Start ===" -ForegroundColor Cyan
docker compose up --build -d
Write-Host ""
Write-Host "  Dashboard:  http://localhost:4000" -ForegroundColor Green
Write-Host "  API:        http://localhost:9080" -ForegroundColor Green
Write-Host "  Prometheus: http://localhost:9190" -ForegroundColor Green
Write-Host "  Grafana:    http://localhost:4001 (admin/aegis)" -ForegroundColor Green
