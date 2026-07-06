from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def barrier_price(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    barrier_type: str = "down-and-out",
) -> float:
    """Analytic barrier option price (continuous monitoring approximation)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    mu = (r - 0.5 * sigma**2) / sigma**2
    lam = math.sqrt(mu**2 + 2 * r / sigma**2)
    x1 = math.log(S / K) / (sigma * math.sqrt(T)) + (1 + mu) * sigma * math.sqrt(T)
    x2 = math.log(S / H) / (sigma * math.sqrt(T)) + (1 + mu) * sigma * math.sqrt(T)
    y1 = math.log(H**2 / (S * K)) / (sigma * math.sqrt(T)) + (1 + mu) * sigma * math.sqrt(T)
    y2 = math.log(H / S) / (sigma * math.sqrt(T)) + (1 + mu) * sigma * math.sqrt(T)
    eta = 1 if option_type == "call" else -1
    phi = 1 if "out" in barrier_type else -1

    if S <= H and "down" in barrier_type:
        return 0.0
    if S >= H and "up" in barrier_type:
        return 0.0

    from aegis_options.pricing import black_scholes

    vanilla = black_scholes(S, K, T, r, sigma, option_type)
    if barrier_type == "down-and-out":
        A = (phi * S * norm.cdf(phi * x1) - phi * K * math.exp(-r * T) * norm.cdf(phi * x1 - phi * sigma * math.sqrt(T)))
        B = (phi * S * norm.cdf(phi * x2) - phi * K * math.exp(-r * T) * norm.cdf(phi * x2 - phi * sigma * math.sqrt(T)))
        C = (phi * S * (H / S) ** (2 * (mu + 1)) * norm.cdf(eta * y1)
             - phi * K * math.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(eta * y1 - eta * sigma * math.sqrt(T)))
        return max(0.0, A - B + C)
    return vanilla


def asian_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    n_steps: int = 50,
    n_paths: int = 30_000,
    seed: int = 42,
) -> float:
    """Monte Carlo arithmetic Asian option price."""
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    payoffs = np.zeros(n_paths)
    for i in range(n_paths):
        path = [S]
        for _ in range(n_steps):
            z = rng.standard_normal()
            path.append(path[-1] * math.exp((r - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z))
        avg = np.mean(path[1:])
        if option_type == "call":
            payoffs[i] = max(avg - K, 0)
        else:
            payoffs[i] = max(K - avg, 0)
    return float(math.exp(-r * T) * payoffs.mean())
