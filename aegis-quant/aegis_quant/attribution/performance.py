from __future__ import annotations

import numpy as np
import pandas as pd


class PerformanceAttributor:
    """Brinson-Fachler and factor-based PnL attribution."""

    def brinson_attribution(
        self,
        portfolio_weights: pd.DataFrame,
        benchmark_weights: pd.DataFrame,
        asset_returns: pd.DataFrame,
    ) -> dict[str, pd.Series]:
        """Decompose active return into allocation, selection, interaction."""
        common = portfolio_weights.columns.intersection(benchmark_weights.columns).intersection(asset_returns.columns)
        pw = portfolio_weights[common]
        bw = benchmark_weights[common]
        ar = asset_returns[common]
        active = pw - bw
        bench_ret = (bw * ar).sum(axis=1)
        port_ret = (pw * ar).sum(axis=1)
        allocation = ((pw - bw) * (ar.sub(ar.mean()))).sum(axis=1)
        selection = (bw * (ar.sub(bench_ret, axis=0))).sum(axis=1)
        interaction = ((pw - bw) * (ar.sub(bench_ret, axis=0))).sum(axis=1)
        return {
            "portfolio_return": port_ret,
            "benchmark_return": bench_ret,
            "active_return": port_ret - bench_ret,
            "allocation": allocation,
            "selection": selection,
            "interaction": interaction,
        }

    def factor_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> dict[str, float]:
        """Attribute portfolio return to factor exposures."""
        aligned = pd.concat([portfolio_returns.rename("port"), factor_returns], axis=1).dropna()
        if aligned.empty:
            return {}
        from statsmodels.regression.linear_model import OLS
        from statsmodels.tools import add_constant

        y = aligned["port"]
        X = add_constant(aligned.drop(columns=["port"]))
        model = OLS(y, X).fit()
        return {k: float(v) for k, v in model.params.items()}

    def trade_pnl_attribution(self, fills: pd.DataFrame) -> pd.DataFrame:
        """Per-symbol realized PnL from fills."""
        if fills.empty:
            return pd.DataFrame(columns=["symbol", "realized_pnl", "commission", "slippage"])
        df = fills.copy()
        df["signed_qty"] = np.where(df["side"] == "buy", df["quantity"], -df["quantity"])
        df["notional"] = df["quantity"] * df["price"]
        grouped = df.groupby("symbol").agg(
            realized_pnl=("notional", lambda x: float(x.sum())),
            commission=("commission", "sum"),
            slippage=("slippage", "sum"),
            trades=("quantity", "count"),
        )
        return grouped.reset_index()

    def sector_exposure(self, weights: pd.Series, sector_map: dict[str, str]) -> pd.Series:
        sectors: dict[str, float] = {}
        for sym, w in weights.items():
            sector = sector_map.get(sym, "unknown")
            sectors[sector] = sectors.get(sector, 0.0) + w
        return pd.Series(sectors)
