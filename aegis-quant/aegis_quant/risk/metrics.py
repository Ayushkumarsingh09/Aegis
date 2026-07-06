from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


class RiskEngine:
    """Comprehensive risk analytics engine."""

    def compute_all(self, returns: pd.Series, equity: pd.Series | None = None) -> dict[str, float]:
        if returns.empty:
            return {}
        eq = equity if equity is not None else (1 + returns).cumprod()
        return {
            "sharpe": self.sharpe(returns),
            "sortino": self.sortino(returns),
            "calmar": self.calmar(returns, eq),
            "max_drawdown": self.max_drawdown(eq),
            "var_95": self.var(returns, 0.95),
            "cvar_95": self.cvar(returns, 0.95),
            "volatility": float(returns.std() * np.sqrt(252)),
            "total_return": float(eq.iloc[-1] / eq.iloc[0] - 1) if len(eq) > 1 else 0.0,
            "win_rate": float((returns > 0).mean()),
            "skewness": float(stats.skew(returns.dropna())),
            "kurtosis": float(stats.kurtosis(returns.dropna())),
        }

    @staticmethod
    def sharpe(returns: pd.Series, rf: float = 0.0, periods: int = 252) -> float:
        excess = returns - rf / periods
        if excess.std() == 0:
            return 0.0
        return float(excess.mean() / excess.std() * np.sqrt(periods))

    @staticmethod
    def sortino(returns: pd.Series, rf: float = 0.0, periods: int = 252) -> float:
        excess = returns - rf / periods
        downside = excess[excess < 0]
        if len(downside) == 0 or downside.std() == 0:
            return 0.0
        return float(excess.mean() / downside.std() * np.sqrt(periods))

    @staticmethod
    def calmar(returns: pd.Series, equity: pd.Series, periods: int = 252) -> float:
        ann_ret = returns.mean() * periods
        mdd = RiskEngine.max_drawdown(equity)
        return float(ann_ret / abs(mdd)) if mdd != 0 else 0.0

    @staticmethod
    def max_drawdown(equity: pd.Series) -> float:
        peak = equity.cummax()
        dd = (equity - peak) / peak
        return float(dd.min())

    @staticmethod
    def rolling_drawdown(equity: pd.Series, window: int = 60) -> pd.Series:
        peak = equity.rolling(window, min_periods=1).max()
        return (equity - peak) / peak

    @staticmethod
    def var(returns: pd.Series, confidence: float = 0.95) -> float:
        return float(np.percentile(returns.dropna(), (1 - confidence) * 100))

    @staticmethod
    def cvar(returns: pd.Series, confidence: float = 0.95) -> float:
        var = RiskEngine.var(returns, confidence)
        return float(returns[returns <= var].mean())

    @staticmethod
    def beta(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        aligned = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0.0
        cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
        return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] != 0 else 0.0

    @staticmethod
    def alpha(strategy_returns: pd.Series, benchmark_returns: pd.Series, rf: float = 0.0) -> float:
        b = RiskEngine.beta(strategy_returns, benchmark_returns)
        return float(strategy_returns.mean() * 252 - rf - b * (benchmark_returns.mean() * 252 - rf))

    @staticmethod
    def information_ratio(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        active = strategy_returns - benchmark_returns
        if active.std() == 0:
            return 0.0
        return float(active.mean() / active.std() * np.sqrt(252))

    @staticmethod
    def tracking_error(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        active = strategy_returns - benchmark_returns
        return float(active.std() * np.sqrt(252))

    @staticmethod
    def turnover(weights: pd.DataFrame) -> float:
        return float(weights.diff().abs().sum(axis=1).mean())

    @staticmethod
    def monte_carlo(returns: pd.Series, n_sims: int = 1000, horizon: int = 252) -> pd.DataFrame:
        mu, sigma = returns.mean(), returns.std()
        sims = np.random.default_rng(42).normal(mu, sigma, (n_sims, horizon))
        paths = np.cumprod(1 + sims, axis=1)
        return pd.DataFrame(paths)

    @staticmethod
    def stress_test(returns: pd.Series, scenarios: dict[str, float]) -> dict[str, float]:
        results = {}
        for name, shock in scenarios.items():
            results[name] = float(returns.mean() * 252 + shock)
        return results
