from __future__ import annotations

import pandas as pd


class ExposureAnalyzer:
    """Portfolio exposure analysis."""

    def sector_exposure(self, weights: pd.Series, sector_map: dict[str, str]) -> pd.Series:
        sectors: dict[str, float] = {}
        for sym, w in weights.items():
            sector = sector_map.get(sym, "unknown")
            sectors[sector] = sectors.get(sector, 0.0) + w
        return pd.Series(sectors)

    def factor_exposure(self, weights: pd.Series, factor_loadings: pd.DataFrame) -> pd.Series:
        common = weights.index.intersection(factor_loadings.index)
        if common.empty:
            return pd.Series(dtype=float)
        return factor_loadings.loc[common].T @ weights.loc[common]

    def gross_exposure(self, weights: pd.Series) -> float:
        return float(weights.abs().sum())

    def net_exposure(self, weights: pd.Series) -> float:
        return float(weights.sum())

    def leverage(self, weights: pd.Series) -> float:
        return self.gross_exposure(weights)

    def turnover(self, weights: pd.DataFrame) -> float:
        return float(weights.diff().abs().sum(axis=1).mean())

    def beta_exposure(self, weights: pd.Series, betas: pd.Series) -> float:
        common = weights.index.intersection(betas.index)
        return float((weights.loc[common] * betas.loc[common]).sum())
