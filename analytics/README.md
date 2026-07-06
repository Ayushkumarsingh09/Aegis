# Analytics

Risk analytics, performance attribution, exposure analysis, and stress testing.

## Features

- VaR, CVaR, Expected Shortfall
- Sharpe, Sortino, Calmar, Treynor, Information Ratio
- Rolling drawdown and rolling Sharpe
- Brinson-Fachler attribution
- Factor attribution
- Sector and factor exposure
- Scenario analysis and Monte Carlo stress tests

## Usage

```python
from aegis_analytics import RiskAnalytics, PnLAttributor, ExposureAnalyzer, StressTester

risk = RiskAnalytics()
metrics = risk.compute_all(returns, equity_curve)

stress = StressTester()
scenarios = stress.scenario_analysis(returns)
mc_var = stress.monte_carlo_var(returns)
```

## Tests

```bash
pytest analytics/tests/ -v
```
