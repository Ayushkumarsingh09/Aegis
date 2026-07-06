# Deployment Guide

## Docker Compose (Production)

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| exchange | 9080 | Matching engine + API |
| dashboard | 4000 | Trading UI |
| prometheus | 9190 | Metrics collection |
| grafana | 4001 | Dashboards (admin/aegis) |

### Volumes

- `exchange-data`: Market data recordings at `/app/data`

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| AEGIS_PORT | 8080 | API server port |

## Health Checks

```bash
curl http://localhost:9080/health
curl http://localhost:9080/metrics
curl http://localhost:9080/api/v1/status
```

## Monitoring

Prometheus scrapes `/metrics` every 5 seconds. Key metrics:

- `aegis_orders_received_total` — Order intake
- `aegis_orders_accepted_total` — Accepted orders
- `aegis_trades_total` — Executed trades
- `aegis_order_latency_us` — Order processing latency histogram

## Kill Switch

```bash
# Activate
curl -X POST http://localhost:9080/api/v1/risk/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"active": true, "reason": "emergency halt"}'

# Deactivate
curl -X POST http://localhost:9080/api/v1/risk/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"active": false}'
```

## Scaling Notes

For multi-instrument production deployment:
- Each instrument's matching engine is independent
- Consider sharding instruments across processes
- Use dedicated network interfaces for market data multicast
- Pin matching threads to isolated CPU cores
