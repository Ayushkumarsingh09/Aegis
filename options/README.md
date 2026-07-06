# Options Analytics

Options pricing, Greeks, volatility surfaces, and exotic instruments.

## Features

- Black-Scholes European pricing
- Cox-Ross-Rubinstein American binomial tree
- Monte Carlo pricing
- Implied volatility solver (Newton-Raphson)
- Full Greeks (delta, gamma, theta, vega, rho)
- Volatility smile and surface interpolation
- Barrier and Asian options

## Usage

```python
from aegis_options import black_scholes, compute_greeks, VolatilitySurface

price = black_scholes(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call")
greeks = compute_greeks(100, 100, 1.0, 0.05, 0.2, "call")

surface = VolatilitySurface(spot=100)
surface.add_point(T=0.5, K=100, market_price=price)
grid = surface.grid(10, 10)
```

## Tests

```bash
pytest options/tests/ -v
```
