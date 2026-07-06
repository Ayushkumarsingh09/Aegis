from __future__ import annotations

import pandas as pd

from aegis_analytics.risk import RiskAnalytics


class StressTester:
    """Scenario analysis and stress testing."""

    SCENARIOS = {
        "market_crash": -0.20,
        "flash_crash": -0.10,
        "rate_shock_up": -0.05,
        "rate_shock_down": 0.05,
        "vol_spike": -0.08,
        "recovery": 0.15,
    }

    def scenario_analysis(self, returns: pd.Series, scenarios: dict[str, float] | None = None) -> dict[str, float]:
        scenarios = scenarios or self.SCENARIOS
        base = returns.mean() * 252
        return {name: float(base + shock) for name, shock in scenarios.items()}

    def historical_stress(self, returns: pd.Series, window: int = 20) -> pd.Series:
        return returns.rolling(window).sum().sort_values()

    def monte_carlo_var(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
        n_sims: int = 10_000,
        horizon: int = 1,
        seed: int = 42,
    ) -> dict[str, float]:
        paths = RiskAnalytics.monte_carlo(returns, n_sims, horizon, seed)
        final_returns = paths.iloc[:, -1] - 1
        var = float(final_returns.quantile(1 - confidence))
        cvar = float(final_returns[final_returns <= var].mean())
        return {"var": var, "cvar": cvar, "n_sims": n_sims}

    def correlation_stress(self, returns: pd.DataFrame, shock_corr: float = 0.9) -> pd.DataFrame:
        """Stress test with elevated correlation."""
        n = len(returns.columns)
        stressed = returns.copy()
        avg = returns.mean(axis=1)
        for col in returns.columns:
            stressed[col] = shock_corr * avg + (1 - shock_corr) * returns[col]
        return stressed
