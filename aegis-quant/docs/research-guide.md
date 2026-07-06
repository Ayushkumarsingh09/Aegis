# Research Guide

## Overview

Aegis Quant provides an end-to-end quantitative research workflow from raw market data through live paper trading.

## 1. Data Ingestion

```bash
# From CSV sample data
aegis-quant ingest --source csv --symbol BTC-USD

# From Yahoo Finance
aegis-quant ingest --source yahoo --symbol AAPL
```

Programmatic ingestion:

```python
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.data.connectors import YahooFinanceConnector, AegisExchangeConnector

engine = MarketDataEngine()
engine.ingest(YahooFinanceConnector(), "AAPL")
engine.ingest(AegisExchangeConnector("http://localhost:9080"), "BTC-USD")
```

## 2. Feature Engineering

```python
from aegis_quant.features.engine import FeatureEngine
from aegis_quant.data.feature_store import FeatureStore

df = engine.get_bars("BTC-USD")
featured = FeatureEngine().compute_all(df)
FeatureStore().write_features(featured, "BTC-USD")
```

Available features include VWAP, TWAP, RSI, MACD, ATR, microprice, order flow imbalance, PCA factors, and custom expressions.

## 3. Factor Research

```python
from aegis_quant.factors.research import FactorResearchEngine

factor_engine = FactorResearchEngine()
ic = factor_engine.factor_ic(featured["momentum_12"], forward_returns)
spread = factor_engine.quantile_spread(featured["momentum_12"], forward_returns)
```

## 4. Strategy Backtesting

```python
from aegis_quant.strategy.strategies import MomentumStrategy, run_strategy

result = run_strategy(MomentumStrategy("BTC-USD"), featured)
print(result.metrics)  # sharpe, max_drawdown, var_95, etc.
```

## 5. Portfolio Optimization

```python
from aegis_quant.portfolio.optimizer import PortfolioOptimizer

opt = PortfolioOptimizer()
weights = opt.markowitz(mu, cov, "max_sharpe")
weights = opt.risk_parity(returns)
weights = opt.hrp(returns)
```

## 6. Machine Learning

```python
from aegis_quant.ml.pipeline import MLPipeline

pipeline = MLPipeline()
result = pipeline.train(X, y, model_name="xgboost")
print(result.run_id)  # tracked in MLflow
```

## 7. Walk-Forward Validation

```python
from aegis_quant.validation.walk_forward import WalkForwardValidator

validator = WalkForwardValidator(n_splits=5)
scores = validator.validate(features, target, fit_predict_fn)
```

## 8. Paper Trading

```python
from aegis_quant.paper.engine import PaperTradingEngine

paper = PaperTradingEngine(exchange_url="http://localhost:9080")
paper.submit_order("BTC-USD", "buy", 1.0)
```

## Notebooks

See `notebooks/` for ready-to-run examples:

- `01_momentum_research.ipynb` — Momentum factor and backtest
- Additional notebooks cover pairs trading, mean reversion, and portfolio optimization

## Best Practices

1. Always clean data with `clean_bars()` before feature computation
2. Use walk-forward validation instead of in-sample optimization
3. Store features in the Feature Store for reproducibility
4. Track ML experiments via MLflow (`data/mlflow.db`)
5. Connect to Aegis Exchange for realistic execution simulation
