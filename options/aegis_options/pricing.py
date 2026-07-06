from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> float:
    """European Black-Scholes option price."""
    if T <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return float(intrinsic)
    if sigma <= 0:
        sigma = 1e-9
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return float(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))
    return float(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))


def american_binomial(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    steps: int = 100,
) -> float:
    """Cox-Ross-Rubinstein binomial tree for American options."""
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)
    discount = math.exp(-r * dt)

    prices = np.array([S * u**j * d ** (steps - j) for j in range(steps + 1)])
    if option_type == "call":
        values = np.maximum(prices - K, 0)
    else:
        values = np.maximum(K - prices, 0)

    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            S_ij = S * u**j * d ** (i - j)
            hold = discount * (p * values[j + 1] + (1 - p) * values[j])
            if option_type == "call":
                exercise = max(S_ij - K, 0)
            else:
                exercise = max(K - S_ij, 0)
            values[j] = max(hold, exercise)
    return float(values[0])


def monte_carlo_european(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    n_paths: int = 50_000,
    seed: int = 42,
) -> tuple[float, float]:
    """Monte Carlo European option price with standard error."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths)
    ST = S * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
    if option_type == "call":
        payoffs = np.maximum(ST - K, 0)
    else:
        payoffs = np.maximum(K - ST, 0)
    price = math.exp(-r * T) * payoffs.mean()
    se = math.exp(-r * T) * payoffs.std() / math.sqrt(n_paths)
    return float(price), float(se)


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """Newton-Raphson implied volatility solver."""
    sigma = 0.2
    for _ in range(max_iter):
        price = black_scholes(S, K, T, r, sigma, option_type)
        diff = price - market_price
        if abs(diff) < tol:
            return sigma
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        vega = S * norm.pdf(d1) * math.sqrt(T)
        if vega < 1e-12:
            break
        sigma -= diff / vega
        sigma = max(1e-6, min(sigma, 5.0))
    return sigma
