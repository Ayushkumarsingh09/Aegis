# Aegis Quant

**Institutional quantitative research platform** — successor to [Aegis Exchange](../README.md).

End-to-end pipeline from market data ingestion through feature engineering, factor research, strategy backtesting, portfolio optimization, ML model training, and paper trading against the live exchange.

```
Market Data → Cleaning → Features → Factors → Strategy → Backtest
    → Execution Sim → Risk → Portfolio → Attribution → Walk-Forward → Paper Trading
```

## Quick Start

```bash
cd aegis-quant
pip install -e ".[dev]"
python scripts/generate_sample_data.py
python -c "from aegis_quant.data.engine import MarketDataEngine; from aegis_quant.data.connectors import CSVConnector; e=MarketDataEngine(); e.ingest(CSVConnector('data/sample'),'BTC-USD')"
aegis-quant serve
```

| Service | URL |
|---------|-----|
| API | http://localhost:8090 |
| Dashboard | http://localhost:4100 |
| API Docs | http://localhost:8090/docs |
| Grafana | http://localhost:4101 |

### Docker

```bash
docker compose up --build
```

## Architecture

| Module | Description |
|--------|-------------|
| `data/` | Market data engine, connectors (CSV, Parquet, DuckDB, Postgres, Yahoo, Aegis Exchange) |
| `features/` | 30+ features: VWAP, RSI, MACD, microprice, OFI, PCA, cointegration |
| `factors/` | Cross-sectional IC, quantile spreads, factor neutralization |
| `attribution/` | Brinson attribution, trade PnL, factor attribution |
| `strategy/` | Plugin strategies: mean reversion, momentum, pairs, market making |
| `backtest/` | Event-driven backtester with latency, slippage, commissions |
| `risk/` | VaR, CVaR, Sharpe, Sortino, drawdown, Monte Carlo |
| `portfolio/` | Markowitz, Black-Litterman, risk parity, Kelly, HRP |
| `ml/` | XGBoost, LightGBM, CatBoost, RF + MLflow tracking |
| `validation/` | Walk-forward validation, Optuna hyperparameter search |
| `paper/` | Paper trading via Aegis Exchange API |
| `api/` | FastAPI REST + Prometheus metrics |

## Data Sources

- CSV / Parquet / DuckDB / PostgreSQL
- Yahoo Finance (live)
- **Aegis Exchange** (live order book + trades at `:9080`)
- Polygon, Alpaca, Binance (connector interfaces ready)

## Example: Backtest

```python
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.features.engine import FeatureEngine
from aegis_quant.strategy.strategies import MeanReversionStrategy, run_strategy

engine = MarketDataEngine()
df = engine.get_bars("BTC-USD")
df = FeatureEngine().compute_all(df)
result = run_strategy(MeanReversionStrategy("BTC-USD"), df)
print(result.metrics)
```

## Python SDK

```python
from aegis_quant_client import AegisQuantClient

client = AegisQuantClient("http://localhost:8090")
print(client.backtest("momentum", "BTC-USD"))
```

## CLI

```bash
aegis-quant ingest --source yahoo --symbol AAPL
aegis-quant backtest --strategy mean_reversion --symbol BTC-USD
aegis-quant serve --port 8090
```

## Testing

```bash
pytest tests/ -v
```

## Documentation

- [Architecture](docs/architecture.md)
- [Research Guide](docs/research-guide.md)
- [Developer Guide](docs/developer-guide.md)

## License

MIT
