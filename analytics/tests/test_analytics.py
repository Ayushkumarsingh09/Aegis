import numpy as np
import pandas as pd

from aegis_analytics.risk import RiskAnalytics
from aegis_analytics.attribution import PnLAttributor
from aegis_analytics.exposure import ExposureAnalyzer
from aegis_analytics.stress import StressTester


def test_risk_metrics():
    np.random.seed(42)
    rets = pd.Series(np.random.randn(252) * 0.01)
    eq = (1 + rets).cumprod()
    risk = RiskAnalytics()
    metrics = risk.compute_all(rets, eq)
    assert "sharpe" in metrics
    assert "cvar_95" in metrics
    assert metrics["max_drawdown"] <= 0


def test_rolling_metrics():
    rets = pd.Series(np.random.randn(100) * 0.01)
    eq = (1 + rets).cumprod()
    rolling = RiskAnalytics.rolling_sharpe(rets, window=20)
    assert len(rolling.dropna()) > 0


def test_beta_alpha():
    strat = pd.Series(np.random.randn(100) * 0.01)
    bench = pd.Series(np.random.randn(100) * 0.01)
    b = RiskAnalytics.beta(strat, bench)
    a = RiskAnalytics.alpha(strat, bench)
    assert isinstance(b, float)
    assert isinstance(a, float)


def test_brinson_attribution():
    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    pw = pd.DataFrame({"A": 0.6, "B": 0.4}, index=idx)
    bw = pd.DataFrame({"A": 0.5, "B": 0.5}, index=idx)
    ar = pd.DataFrame({"A": np.random.randn(10) * 0.01, "B": np.random.randn(10) * 0.01}, index=idx)
    result = PnLAttributor().brinson(pw, bw, ar)
    assert "active_return" in result


def test_exposure():
    weights = pd.Series({"AAPL": 0.3, "MSFT": 0.4, "GOOG": 0.3})
    sectors = {"AAPL": "tech", "MSFT": "tech", "GOOG": "tech"}
    exp = ExposureAnalyzer()
    assert exp.sector_exposure(weights, sectors)["tech"] == 1.0
    assert exp.gross_exposure(weights) == 1.0


def test_stress():
    rets = pd.Series(np.random.randn(252) * 0.01)
    stress = StressTester()
    scenarios = stress.scenario_analysis(rets)
    assert "market_crash" in scenarios
    mc = stress.monte_carlo_var(rets, n_sims=1000)
    assert "var" in mc
