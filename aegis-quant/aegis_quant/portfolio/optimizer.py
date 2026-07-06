from __future__ import annotations

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, HRPOpt, risk_models


class PortfolioOptimizer:
    """Portfolio optimization with multiple methods."""

    def markowitz(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        target: str = "max_sharpe",
        weight_bounds: tuple = (0, 1),
    ) -> pd.Series:
        ef = EfficientFrontier(expected_returns, cov_matrix, weight_bounds=weight_bounds)
        if target == "max_sharpe":
            ef.max_sharpe()
        elif target == "min_volatility":
            ef.min_volatility()
        else:
            ef.efficient_return(float(target))
        return pd.Series(ef.clean_weights())

    def risk_parity(self, returns: pd.DataFrame) -> pd.Series:
        hrp = HRPOpt(returns)
        hrp.optimize()
        return pd.Series(hrp.clean_weights())

    def equal_weight(self, symbols: list[str]) -> pd.Series:
        w = 1.0 / len(symbols)
        return pd.Series({s: w for s in symbols})

    def kelly(self, win_rate: float, win_loss_ratio: float) -> float:
        if win_loss_ratio <= 0:
            return 0.0
        return max(0.0, min(1.0, win_rate - (1 - win_rate) / win_loss_ratio))

    def max_diversification(self, cov_matrix: pd.DataFrame) -> pd.Series:
        n = len(cov_matrix)
        vols = np.sqrt(np.diag(cov_matrix.values))
        inv_vol = 1.0 / vols
        w = inv_vol / inv_vol.sum()
        return pd.Series(w, index=cov_matrix.index)

    def black_litterman(
        self,
        market_caps: pd.Series,
        cov_matrix: pd.DataFrame,
        views: dict[str, float],
        tau: float = 0.05,
    ) -> pd.Series:
        from pypfopt import black_litterman

        pi = black_litterman.market_implied_prior_returns(market_caps, 0.05, cov_matrix)
        bl_returns = black_litterman.black_litterman_return(pi, cov_matrix, views)
        return self.markowitz(bl_returns, cov_matrix)

    @staticmethod
    def sample_cov(returns: pd.DataFrame) -> pd.DataFrame:
        return risk_models.sample_cov(returns)

    def rebalance(
        self,
        current: pd.Series,
        target: pd.Series,
        threshold: float = 0.05,
    ) -> pd.Series:
        diff = (target - current).abs()
        trades = pd.Series(0.0, index=current.index)
        for sym in diff[diff > threshold].index:
            trades[sym] = target[sym] - current[sym]
        return trades
