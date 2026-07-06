from __future__ import annotations

import numpy as np
import pandas as pd


class PnLAttributor:
    """Performance and PnL attribution."""

    def brinson(
        self,
        portfolio_weights: pd.DataFrame,
        benchmark_weights: pd.DataFrame,
        asset_returns: pd.DataFrame,
    ) -> dict[str, pd.Series]:
        common = portfolio_weights.columns.intersection(benchmark_weights.columns).intersection(asset_returns.columns)
        pw, bw, ar = portfolio_weights[common], benchmark_weights[common], asset_returns[common]
        bench_ret = (bw * ar).sum(axis=1)
        port_ret = (pw * ar).sum(axis=1)
        allocation = ((pw - bw) * ar.sub(ar.mean())).sum(axis=1)
        selection = (bw * ar.sub(bench_ret, axis=0)).sum(axis=1)
        interaction = ((pw - bw) * ar.sub(bench_ret, axis=0)).sum(axis=1)
        return {
            "portfolio_return": port_ret,
            "benchmark_return": bench_ret,
            "active_return": port_ret - bench_ret,
            "allocation": allocation,
            "selection": selection,
            "interaction": interaction,
        }

    def factor_attribution(self, portfolio_returns: pd.Series, factor_returns: pd.DataFrame) -> dict[str, float]:
        aligned = pd.concat([portfolio_returns.rename("port"), factor_returns], axis=1).dropna()
        if aligned.empty:
            return {}
        from statsmodels.regression.linear_model import OLS
        from statsmodels.tools import add_constant

        model = OLS(aligned["port"], add_constant(aligned.drop(columns=["port"]))).fit()
        return {k: float(v) for k, v in model.params.items()}

    def trade_attribution(self, fills: pd.DataFrame) -> pd.DataFrame:
        if fills.empty:
            return pd.DataFrame(columns=["symbol", "notional", "commission", "n_trades"])
        grouped = fills.groupby("symbol").agg(
            notional=("price", lambda x: float((x * fills.loc[x.index, "quantity"]).sum())),
            commission=("commission", "sum") if "commission" in fills.columns else ("price", "count"),
            n_trades=("quantity", "count"),
        )
        return grouped.reset_index()
