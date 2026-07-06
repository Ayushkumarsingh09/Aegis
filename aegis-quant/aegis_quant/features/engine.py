from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA


class FeatureEngine:
    """Comprehensive feature engineering for quantitative research."""

    def compute_all(self, df: pd.DataFrame, book: pd.DataFrame | None = None) -> pd.DataFrame:
        out = df.copy()
        out = self._price_features(out)
        out = self._momentum_features(out)
        out = self._volatility_features(out)
        out = self._volume_features(out)
        out = self._microstructure_features(out, book)
        return out

    def _price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)
        df["twap"] = df["close"].expanding().mean()
        for w in (5, 10, 20, 60):
            df[f"zscore_{w}"] = (df["close"] - df["close"].rolling(w).mean()) / df["close"].rolling(w).std()
            df[f"return_lag_{w}"] = df["returns"].shift(w)
            df[f"rolling_vol_{w}"] = df["returns"].rolling(w).std() * np.sqrt(252)
        return df

    def _momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["momentum_12"] = df["close"] / df["close"].shift(12) - 1
        df["momentum_26"] = df["close"] / df["close"].shift(26) - 1
        df["rsi_14"] = _rsi(df["close"], 14)
        df["macd"], df["macd_signal"] = _macd(df["close"])
        df["atr_14"] = _atr(df, 14)
        return df

    def _volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["realized_vol_20"] = df["log_returns"].rolling(20).std() * np.sqrt(252)
        df["vol_clustering"] = df["returns"].rolling(20).apply(_autocorr_wrapper, raw=True)
        return df

    def _volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["volume_profile"] = df["volume"] / df["volume"].rolling(20).mean()
        df["volume_zscore"] = (df["volume"] - df["volume"].rolling(20).mean()) / df["volume"].rolling(20).std()
        return df

    def _microstructure_features(self, df: pd.DataFrame, book: pd.DataFrame | None) -> pd.DataFrame:
        if book is not None and not book.empty:
            df = df.merge(book, on="timestamp", how="left", suffixes=("", "_book"))
        if "bid_qty" in df.columns and "ask_qty" in df.columns:
            df["queue_imbalance"] = (df["bid_qty"] - df["ask_qty"]) / (df["bid_qty"] + df["ask_qty"] + 1e-9)
            df["order_flow_imbalance"] = df["queue_imbalance"].diff()
            df["spread"] = df["ask_price"] - df["bid_price"]
            df["microprice"] = (
                df["ask_price"] * df["bid_qty"] + df["bid_price"] * df["ask_qty"]
            ) / (df["bid_qty"] + df["ask_qty"] + 1e-9)
            df["depth"] = df["bid_qty"] + df["ask_qty"]
            df["liquidity"] = df["depth"] / (df["spread"] + 1e-9)
        return df

    @staticmethod
    def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
        return returns.corr()

    @staticmethod
    def cointegration_score(series_a: pd.Series, series_b: pd.Series) -> float:
        from statsmodels.tsa.stattools import coint

        score, pvalue, _ = coint(series_a.dropna(), series_b.dropna())
        return float(pvalue)

    @staticmethod
    def pca_factors(returns: pd.DataFrame, n_components: int = 3) -> pd.DataFrame:
        pca = PCA(n_components=n_components)
        factors = pca.fit_transform(returns.dropna())
        cols = [f"pc_{i+1}" for i in range(n_components)]
        return pd.DataFrame(factors, index=returns.dropna().index, columns=cols)

    @staticmethod
    def neutralize(features: pd.DataFrame, factor: pd.Series) -> pd.DataFrame:
        out = features.copy()
        for col in out.columns:
            beta = np.polyfit(factor.loc[out.index].fillna(0), out[col].fillna(0), 1)[0]
            out[col] = out[col] - beta * factor
        return out

    def evaluate_expression(self, df: pd.DataFrame, expr: str) -> pd.Series:
        allowed = {c: df[c] for c in df.select_dtypes(include=[np.number]).columns}
        allowed.update({"np": np, "pd": pd})
        return pd.Series(eval(expr, {"__builtins__": {}}, allowed), index=df.index)


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    return macd, macd.ewm(span=signal).mean()


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _autocorr_wrapper(x, lag=1):
    x = np.asarray(x)
    if len(x) <= lag or np.std(x) < 1e-12:
        return 0.0
    return float(np.corrcoef(x[lag:], x[:-lag])[0, 1])
