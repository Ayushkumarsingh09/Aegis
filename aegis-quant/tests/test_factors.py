import numpy as np
import pandas as pd

from aegis_quant.factors.research import FactorResearchEngine
from aegis_quant.attribution.performance import PerformanceAttributor
from aegis_quant.data.feature_store import FeatureStore


def test_factor_ic():
    n = 100
    factor = pd.Series(np.random.randn(n))
    fwd = factor * 0.5 + np.random.randn(n) * 0.1
    engine = FactorResearchEngine()
    ic = engine.factor_ic(factor, pd.Series(fwd))
    assert isinstance(ic, float)


def test_quantile_spread():
    factor = pd.Series(np.arange(50, dtype=float))
    fwd = factor * 0.01
    engine = FactorResearchEngine()
    result = engine.quantile_spread(factor, fwd, n_quantiles=5)
    assert "long_short" in result
    assert result["long_short"] > 0


def test_brinson_attribution():
    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    pw = pd.DataFrame({"A": 0.6, "B": 0.4}, index=idx)
    bw = pd.DataFrame({"A": 0.5, "B": 0.5}, index=idx)
    ar = pd.DataFrame({"A": np.random.randn(10) * 0.01, "B": np.random.randn(10) * 0.01}, index=idx)
    attr = PerformanceAttributor()
    result = attr.brinson_attribution(pw, bw, ar)
    assert "active_return" in result
    assert len(result["active_return"]) == 10


def test_feature_store(tmp_path):
    db = str(tmp_path / "test.duckdb")
    store = FeatureStore(db)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="h"),
        "rsi_14": [50, 55, 60, 45, 40],
        "macd": [0.1, 0.2, -0.1, 0.0, 0.3],
    })
    count = store.write_features(df, "TEST")
    assert count == 10
    loaded = store.read_features("TEST")
    assert "rsi_14" in loaded.columns
    assert len(loaded) == 5
