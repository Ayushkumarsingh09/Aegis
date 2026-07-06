from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm

from aegis_options.pricing import black_scholes


@dataclass
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


def compute_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> Greeks:
    if T <= 0 or sigma <= 0:
        return Greeks(delta=0, gamma=0, theta=0, vega=0, rho=0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    pdf_d1 = norm.pdf(d1)

    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (
            -S * pdf_d1 * sigma / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * norm.cdf(d2)
        ) / 365
        rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
    else:
        delta = norm.cdf(d1) - 1
        theta = (
            -S * pdf_d1 * sigma / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * norm.cdf(-d2)
        ) / 365
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100

    gamma = pdf_d1 / (S * sigma * math.sqrt(T))
    vega = S * pdf_d1 * math.sqrt(T) / 100

    return Greeks(delta=float(delta), gamma=float(gamma), theta=float(theta), vega=float(vega), rho=float(rho))


def portfolio_greeks(positions: list[tuple[float, Greeks]]) -> Greeks:
    """Aggregate Greeks across a portfolio of (quantity, Greeks) pairs."""
    total = Greeks(0, 0, 0, 0, 0)
    for qty, g in positions:
        total.delta += qty * g.delta
        total.gamma += qty * g.gamma
        total.theta += qty * g.theta
        total.vega += qty * g.vega
        total.rho += qty * g.rho
    return total


def scenario_pnl(positions: list[tuple[float, Greeks]], dS: float, dVol: float, dt: float = 1 / 365) -> float:
    """First-order scenario PnL from spot/vol/time moves."""
    pnl = 0.0
    for qty, g in positions:
        pnl += qty * (g.delta * dS + 0.5 * g.gamma * dS**2 + g.vega * dVol * 100 + g.theta * dt)
    return pnl
