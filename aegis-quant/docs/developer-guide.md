# Developer Guide

## Project Structure

```
aegis-quant/
├── aegis_quant/          # Core Python package
│   ├── core/             # Config, types, logging
│   ├── data/             # Market data engine, connectors, feature store
│   ├── features/         # Feature engineering
│   ├── factors/          # Factor research
│   ├── strategy/         # Strategy plugins
│   ├── backtest/         # Event-driven backtester
│   ├── risk/             # Risk metrics
│   ├── portfolio/        # Portfolio optimization
│   ├── attribution/      # Performance attribution
│   ├── ml/               # ML pipeline + MLflow
│   ├── validation/       # Walk-forward validation
│   ├── paper/            # Paper trading
│   ├── api/              # FastAPI application
│   └── cli/              # CLI entry point
├── dashboard/            # React research dashboard
├── sdk/                  # Python and TypeScript SDKs
├── tests/                # pytest suite
├── notebooks/            # Research notebooks
├── docker/               # Dockerfiles and configs
└── docs/                 # Documentation
```

## Adding a Strategy

1. Create a class extending `Strategy` in `aegis_quant/strategy/strategies.py`
2. Implement `on_bar(ctx, bar)` with order logic
3. Register in `STRATEGY_REGISTRY`

```python
class MyStrategy(Strategy):
    name = "my_strategy"

    def __init__(self, symbol: str):
        self.symbol = symbol

    def on_bar(self, ctx: BacktestContext, bar: dict) -> None:
        if bar["close"] > bar["open"]:
            ctx.order(self.symbol, Side.BUY, 10, strategy_id=self.name)

STRATEGY_REGISTRY["my_strategy"] = MyStrategy
```

## Adding a Data Connector

Extend `DataConnector` in `aegis_quant/data/connectors.py`:

```python
class MyConnector(DataConnector):
    def load_bars(self, symbol, start=None, end=None) -> pd.DataFrame:
        # Return DataFrame with columns: symbol, timestamp, open, high, low, close, volume
        ...
```

## Running Locally

```bash
pip install -e ".[dev]"
python scripts/generate_sample_data.py
aegis-quant ingest --source csv --symbol BTC-USD
aegis-quant serve --port 8090
cd dashboard && npm install && npm run dev
```

## Testing

```bash
pytest tests/ -v
pytest tests/ -v --cov=aegis_quant
ruff check aegis_quant/
```

## Docker

```bash
docker compose up --build
```

Services: API (8090), Dashboard (4100), Postgres (5433), Redis (6380), Prometheus (9290), Grafana (4101).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AEGIS_QUANT_API_PORT` | 8090 | API port |
| `AEGIS_QUANT_DUCKDB_PATH` | data/aegis_quant.duckdb | DuckDB path |
| `AEGIS_QUANT_AEGIS_EXCHANGE_URL` | http://localhost:9080 | Exchange API |
| `AEGIS_QUANT_MLFLOW_URI` | sqlite:///data/mlflow.db | MLflow tracking |
| `AEGIS_QUANT_POLYGON_API_KEY` | | Polygon.io key |
| `AEGIS_QUANT_ALPACA_API_KEY` | | Alpaca key |

## API Endpoints

Full OpenAPI docs at `http://localhost:8090/docs`.

Key endpoints:
- `GET /api/v1/symbols` — List available symbols
- `POST /api/v1/backtest` — Run strategy backtest
- `POST /api/v1/portfolio/optimize` — Portfolio optimization
- `POST /api/v1/ml/train` — Train ML model
- `GET /api/v1/factors/{symbol}/ic` — Factor IC analysis
- `GET /metrics` — Prometheus metrics

## CI

GitHub Actions workflow at `.github/workflows/aegis-quant-ci.yml` runs pytest and dashboard build on push.
