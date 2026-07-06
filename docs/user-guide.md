# User Guide

## Getting Started

Start the full stack:

```bash
docker compose up --build
```

Open the dashboard at **http://localhost:4000**

## Trading

### Order Types

| Type | Description |
|------|-------------|
| **Limit** | Rests on book at specified price |
| **Market** | Executes immediately at best available price |
| **IOC** | Immediate-or-Cancel: fills what it can, cancels remainder |
| **FOK** | Fill-or-Kill: must fill entirely or reject |
| **Post Only** | Only adds liquidity; rejects if it would cross |
| **Stop** | Becomes market order when stop price is triggered |
| **Stop Limit** | Becomes limit order when stop price is triggered |

### Placing Orders

Use the **Order Entry** panel on the dashboard sidebar:
1. Select Buy or Sell
2. Choose order type
3. Enter price (for limit orders) and quantity
4. Click submit

### Viewing Market Data

- **Order Book**: Live bid/ask levels with depth bars
- **Market Depth**: Visual depth chart
- **Recent Trades**: Time-stamped trade feed

## API Access

See [API documentation](docs/api/openapi.yaml) for full REST API reference.

### Python SDK

```bash
pip install ./sdk/python
python sdk/python/examples/submit_order.py
```

## Risk Controls

The risk engine enforces:
- Maximum order size per order
- Maximum net position per account
- Maximum exposure limits
- Daily loss limits
- Kill switch (halts all new orders)

View risk status on the dashboard or via `GET /api/v1/risk`.

## Monitoring

- **Prometheus**: http://localhost:9190
- **Grafana**: http://localhost:4001 (login: admin / aegis)
