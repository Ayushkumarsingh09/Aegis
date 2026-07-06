import math

import pytest

from aegis_options.pricing import american_binomial, black_scholes, implied_volatility, monte_carlo_european
from aegis_options.greeks import compute_greeks, portfolio_greeks, scenario_pnl
from aegis_options.exotics import asian_price, barrier_price
from aegis_options.surface import VolatilitySurface, build_smile


def test_black_scholes_call():
    price = black_scholes(100, 100, 1.0, 0.05, 0.2, "call")
    assert 10 < price < 20


def test_black_scholes_put():
    price = black_scholes(100, 100, 1.0, 0.05, 0.2, "put")
    assert 5 < price < 15


def test_american_binomial():
    price = american_binomial(100, 100, 1.0, 0.05, 0.2, "put", steps=50)
    assert price > 0


def test_monte_carlo():
    price, se = monte_carlo_european(100, 100, 1.0, 0.05, 0.2, "call", n_paths=5000)
    bs = black_scholes(100, 100, 1.0, 0.05, 0.2, "call")
    assert abs(price - bs) < 2.0


def test_implied_volatility():
    market = black_scholes(100, 100, 1.0, 0.05, 0.25, "call")
    iv = implied_volatility(market, 100, 100, 1.0, 0.05, "call")
    assert abs(iv - 0.25) < 0.01


def test_greeks():
    g = compute_greeks(100, 100, 1.0, 0.05, 0.2, "call")
    assert 0 < g.delta < 1
    assert g.gamma > 0
    assert g.vega > 0


def test_portfolio_greeks():
    g1 = compute_greeks(100, 100, 1.0, 0.05, 0.2, "call")
    g2 = compute_greeks(100, 110, 1.0, 0.05, 0.2, "put")
    total = portfolio_greeks([(10, g1), (-5, g2)])
    assert total.delta != g1.delta


def test_scenario_pnl():
    g = compute_greeks(100, 100, 1.0, 0.05, 0.2, "call")
    pnl = scenario_pnl([(10, g)], dS=1.0, dVol=0.01)
    assert pnl != 0


def test_barrier_option():
    price = barrier_price(100, 100, 90, 1.0, 0.05, 0.2, "call", "down-and-out")
    vanilla = black_scholes(100, 100, 1.0, 0.05, 0.2, "call")
    assert 0 <= price <= vanilla


def test_asian_option():
    price = asian_price(100, 100, 1.0, 0.05, 0.2, "call", n_paths=5000)
    assert price > 0


def test_volatility_surface():
    surface = VolatilitySurface(spot=100, r=0.05)
    strikes = [90, 95, 100, 105, 110]
    for K in strikes:
        mkt = black_scholes(100, K, 0.5, 0.05, 0.2 + (100 - K) * 0.001, "call")
        surface.add_point(0.5, K, mkt)
    assert surface.interpolate(0.5, 100) > 0
    grid = surface.grid(3, 3)
    assert len(grid) == 9


def test_build_smile():
    spot = 100
    strikes = [90, 100, 110]
    prices = [black_scholes(spot, K, 1.0, 0.05, 0.2, "call") for K in strikes]
    smile = build_smile(spot, strikes, prices, 1.0, 0.05)
    assert len(smile) == 3
