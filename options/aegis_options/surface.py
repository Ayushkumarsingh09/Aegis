from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import griddata

from aegis_options.pricing import black_scholes, implied_volatility


def build_smile(
    spot: float,
    strikes: list[float],
    market_prices: list[float],
    T: float,
    r: float,
    option_type: str = "call",
) -> pd.DataFrame:
    """Build volatility smile from market option prices."""
    ivs = []
    for K, price in zip(strikes, market_prices):
        iv = implied_volatility(price, spot, K, T, r, option_type)
        ivs.append({"strike": K, "moneyness": K / spot, "iv": iv, "price": price})
    return pd.DataFrame(ivs)


class VolatilitySurface:
    """Implied volatility surface from strike/expiry grid."""

    def __init__(self, spot: float, r: float = 0.05):
        self.spot = spot
        self.r = r
        self._points: list[tuple[float, float, float]] = []  # (T, K, iv)

    def add_point(self, T: float, K: float, market_price: float, option_type: str = "call") -> None:
        iv = implied_volatility(market_price, self.spot, K, T, self.r, option_type)
        self._points.append((T, K, iv))

    def add_smile(self, T: float, strikes: list[float], prices: list[float], option_type: str = "call") -> None:
        for K, price in zip(strikes, prices):
            self.add_point(T, K, price, option_type)

    def interpolate(self, T: float, K: float) -> float:
        if not self._points:
            return 0.2
        Ts = np.array([p[0] for p in self._points])
        Ks = np.array([p[1] for p in self._points])
        IVs = np.array([p[2] for p in self._points])
        if len(self._points) < 4:
            return float(np.mean(IVs))
        if np.std(Ts) < 1e-9:
            idx = np.argsort(Ks)
            return float(np.interp(K, Ks[idx], IVs[idx]))
        if np.std(Ks) < 1e-9:
            idx = np.argsort(Ts)
            return float(np.interp(T, Ts[idx], IVs[idx]))
        return float(griddata((Ts, Ks), IVs, (T, K), method="linear", fill_value=float(np.mean(IVs))))

    def price(self, T: float, K: float, option_type: str = "call") -> float:
        iv = self.interpolate(T, K)
        return black_scholes(self.spot, K, T, self.r, iv, option_type)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self._points, columns=["expiry", "strike", "iv"])

    def grid(self, n_T: int = 10, n_K: int = 10) -> pd.DataFrame:
        if not self._points:
            return pd.DataFrame()
        Ts = np.linspace(min(p[0] for p in self._points), max(p[0] for p in self._points), n_T)
        Ks = np.linspace(min(p[1] for p in self._points), max(p[1] for p in self._points), n_K)
        rows = []
        for T in Ts:
            for K in Ks:
                rows.append({"expiry": T, "strike": K, "iv": self.interpolate(T, K)})
        return pd.DataFrame(rows)
