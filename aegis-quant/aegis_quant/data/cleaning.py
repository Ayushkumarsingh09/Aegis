from __future__ import annotations

import pandas as pd
import numpy as np


def clean_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates, fix OHLC consistency, handle missing values."""
    if df.empty:
        return df
    out = df.copy()
    out = out.drop_duplicates(subset=["symbol", "timestamp"], keep="last")
    out = out.sort_values("timestamp").reset_index(drop=True)

    # Forward-fill small gaps, drop rows with null close
    out["close"] = out["close"].ffill()
    out = out.dropna(subset=["close"])

    # Enforce OHLC constraints
    out["high"] = out[["open", "high", "low", "close"]].max(axis=1)
    out["low"] = out[["open", "high", "low", "close"]].min(axis=1)
    out["volume"] = out["volume"].fillna(0).clip(lower=0)

    # Remove obvious bad ticks (>50% jump without corporate action flag)
    ret = out["close"].pct_change().abs()
    out = out[ret.fillna(0) < 0.5].reset_index(drop=True)
    return out


def apply_splits(df: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    """Adjust prices for stock splits."""
    if actions.empty:
        return df
    out = df.copy()
    for _, row in actions.sort_values("date", ascending=False).iterrows():
        if row.get("type") == "split" and row.get("ratio"):
            mask = out["timestamp"] < row["date"]
            ratio = float(row["ratio"])
            for col in ("open", "high", "low", "close"):
                out.loc[mask, col] /= ratio
            out.loc[mask, "volume"] *= ratio
    return out


def apply_dividends(df: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    """Backward-adjust prices for dividends."""
    if actions.empty:
        return df
    out = df.copy()
    for _, row in actions.sort_values("date", ascending=False).iterrows():
        if row.get("type") == "dividend" and row.get("amount"):
            mask = out["timestamp"] < row["date"]
            out.loc[mask, ["open", "high", "low", "close"]] -= float(row["amount"])
    return out
