from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant


class FactorResearchEngine:
    """Cross-sectional and time-series factor research."""

    def compute_factor_returns(
        self,
        returns: pd.DataFrame,
        factors: pd.DataFrame,
    ) -> pd.DataFrame:
        """Regress asset returns on factor exposures (Fama-French style)."""
        aligned = returns.join(factors, how="inner").dropna()
        if aligned.empty:
            return pd.DataFrame()
        y_cols = [c for c in returns.columns if c in aligned.columns]
        x_cols = [c for c in factors.columns if c in aligned.columns]
        betas = {}
        for asset in y_cols:
            model = OLS(aligned[asset], add_constant(aligned[x_cols])).fit()
            betas[asset] = model.params.to_dict()
        return pd.DataFrame(betas).T

    def factor_ic(
        self,
        factor_values: pd.Series,
        forward_returns: pd.Series,
        method: str = "spearman",
    ) -> float:
        aligned = pd.concat([factor_values, forward_returns], axis=1).dropna()
        if len(aligned) < 3:
            return 0.0
        if method == "spearman":
            corr, _ = stats.spearmanr(aligned.iloc[:, 0], aligned.iloc[:, 1])
        else:
            corr, _ = stats.pearsonr(aligned.iloc[:, 0], aligned.iloc[:, 1])
        return float(corr)

    def rolling_ic(
        self,
        factor_values: pd.Series,
        forward_returns: pd.Series,
        window: int = 60,
    ) -> pd.Series:
        df = pd.DataFrame({"factor": factor_values, "fwd": forward_returns}).dropna()
        return df["factor"].rolling(window).corr(df["fwd"])

    def neutralize(
        self,
        signal: pd.Series,
        exposures: pd.DataFrame,
    ) -> pd.Series:
        """Orthogonalize signal against factor exposures."""
        aligned = pd.concat([signal.rename("signal"), exposures], axis=1).dropna()
        if aligned.empty:
            return signal
        y = aligned["signal"]
        X = add_constant(aligned.drop(columns=["signal"]))
        residuals = OLS(y, X).fit().resid
        out = signal.copy()
        out.loc[residuals.index] = residuals
        return out

    def build_style_factors(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Momentum, value proxy (inverse price), size proxy (volume), volatility."""
        factors = pd.DataFrame(index=prices.index)
        for col in prices.columns:
            ret = prices[col].pct_change()
            factors[f"{col}_mom"] = prices[col].pct_change(21)
            factors[f"{col}_vol"] = ret.rolling(21).std()
            factors[f"{col}_value"] = 1.0 / prices[col].replace(0, np.nan)
        return factors

    def quantile_spread(
        self,
        factor: pd.Series,
        forward_returns: pd.Series,
        n_quantiles: int = 5,
    ) -> dict[str, float]:
        aligned = pd.concat([factor.rename("f"), forward_returns.rename("r")], axis=1).dropna()
        if aligned.empty:
            return {"long_short": 0.0}
        aligned["q"] = pd.qcut(aligned["f"], n_quantiles, labels=False, duplicates="drop")
        top = aligned[aligned["q"] == aligned["q"].max()]["r"].mean()
        bottom = aligned[aligned["q"] == aligned["q"].min()]["r"].mean()
        return {"top": float(top), "bottom": float(bottom), "long_short": float(top - bottom)}
