import numpy as np
import pandas as pd
import pytest

from aegis_quant.features.engine import FeatureEngine
from aegis_quant.risk.metrics import RiskEngine
from aegis_quant.portfolio.optimizer import PortfolioOptimizer
from aegis_quant.strategy.strategies import MeanReversionStrategy, run_strategy
from aegis_quant.data.cleaning import clean_bars


@pytest.fixture
def sample_bars():
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    price = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "symbol": "TEST",
        "timestamp": dates,
        "open": price,
        "high": price + 1,
        "low": price - 1,
        "close": price,
        "volume": np.random.randint(100, 1000, n),
    })


def test_feature_engine(sample_bars):
    fe = FeatureEngine()
    result = fe.compute_all(sample_bars)
    assert "returns" in result.columns
    assert "rsi_14" in result.columns
    assert "macd" in result.columns
    assert "realized_vol_20" in result.columns


def test_risk_metrics(sample_bars):
    rets = sample_bars["close"].pct_change().dropna()
    eq = (1 + rets).cumprod()
    risk = RiskEngine()
    metrics = risk.compute_all(rets, eq)
    assert "sharpe" in metrics
    assert "max_drawdown" in metrics
    assert "var_95" in metrics


def test_portfolio_optimizer():
    np.random.seed(42)
    returns = pd.DataFrame({
        "A": np.random.randn(200) * 0.01,
        "B": np.random.randn(200) * 0.015,
    })
    opt = PortfolioOptimizer()
    w = opt.equal_weight(["A", "B"])
    assert abs(w.sum() - 1.0) < 1e-6
    w2 = opt.risk_parity(returns)
    assert len(w2) == 2


def test_backtest(sample_bars):
    featured = FeatureEngine().compute_all(sample_bars)
    result = run_strategy(MeanReversionStrategy("TEST"), featured)
    assert result.equity_curve is not None
    assert len(result.equity_curve) > 0
    assert "sharpe" in result.metrics


def test_clean_bars(sample_bars):
    cleaned = clean_bars(sample_bars)
    assert len(cleaned) <= len(sample_bars)
    assert cleaned["high"].ge(cleaned["low"]).all()


def test_correlation_matrix(sample_bars):
    rets = pd.DataFrame({"A": sample_bars["close"].pct_change(), "B": sample_bars["close"].pct_change() * 0.8})
    corr = FeatureEngine.correlation_matrix(rets)
    assert corr.shape == (2, 2)
