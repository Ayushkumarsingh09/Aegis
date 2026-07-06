# Execution Engine

Institutional execution algorithms and transaction cost analysis.

## Algorithms

- **TWAP** — Time-Weighted Average Price
- **VWAP** — Volume-Weighted Average Price
- **POV** — Percentage of Volume
- **Iceberg** — Hidden quantity orders
- **Arrival Price** — Implementation shortfall minimization

## Components

| Module | Description |
|--------|-------------|
| `algorithms.py` | Execution schedule generators |
| `simulator.py` | Latency, slippage, partial fill simulation |
| `slippage.py` | Linear and square-root impact models |
| `routing.py` | Smart order routing abstraction |
| `tca.py` | Transaction cost analysis |

## Usage

```python
from datetime import datetime, timedelta
from aegis_execution import TWAPExecutor, ExecutionSimulator, OrderSide

start = datetime(2024, 1, 1)
end = start + timedelta(hours=1)
schedule = TWAPExecutor(n_slices=10).schedule(1000, OrderSide.BUY, "BTC-USD", start, end)
result = ExecutionSimulator().run(schedule, market_data)
print(result.implementation_shortfall_bps)
```

## Tests

```bash
pytest execution/tests/ -v
```
