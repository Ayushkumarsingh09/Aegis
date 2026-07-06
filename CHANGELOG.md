# Changelog

All notable changes to the Aegis platform are documented here.

## [1.0.0] - 2026-07-07

### Added

- **Unified Platform Portal** — Homepage with live status, module navigation, architecture overview
- **Exchange** — C++20 matching engine with price-time priority, 7 order types, risk engine, market data
- **Quant Research** — Feature engineering, backtesting, ML pipeline, portfolio optimization
- **Execution Engine** — TWAP, VWAP, POV, iceberg, arrival price, TCA, smart routing
- **Options Analytics** — Black-Scholes, binomial American, Monte Carlo, Greeks, vol surface, exotics
- **Market Making** — Avellaneda-Stoikov model, inventory management, simulation
- **Risk Analytics** — VaR, CVaR, Sharpe, attribution, stress testing, Monte Carlo
- **Dashboards** — Exchange UI, Research UI with 12+ pages
- **SDKs** — Python clients for exchange and quant APIs
- **Docker** — Full stack compose with portal, exchange, quant, Prometheus, Grafana
- **CI/CD** — GitHub Actions for C++ tests, Python tests, dashboard builds
- **Documentation** — Architecture, getting started, developer guide, benchmarks
- **Demo scripts** — `demo.sh`, `demo.ps1`, `demo.bat`

### Performance

- 45 integration tests passing
- Exchange designed for sub-microsecond matching latency
- Event-driven backtester with latency and slippage simulation

[1.0.0]: https://github.com/Ayushkumarsingh09/Aegis/releases/tag/v1.0.0
