# Changelog

All notable changes to the Aegis platform are documented here.

## [1.2.0] - 2026-07-07

### Added

- **Backtests** — drawdown and rolling-Sharpe series, trade blotter (last 100 fills), configurable capital
- **Executions** — all 5 algorithms exposed via API (TWAP, VWAP, POV, Iceberg, Arrival Price) with full TCA vs arrival/TWAP/VWAP benchmarks
- **Portfolio** — random-portfolio efficient frontier endpoint with max-Sharpe point, fixed-weight portfolio backtest with equity/drawdown, optimizer weights chart
- **Risk** — rolling Sharpe/volatility endpoints, cross-asset correlation matrix (heatmap), Monte Carlo fan chart with percentile bands
- **Factors** — multi-factor IC analysis endpoint (10 factors ranked by |IC|) with rolling IC of the strongest factor
- **Experiments** — every backtest, execution, portfolio, and market-making run auto-persisted to DuckDB; filterable history page
- **Options** — pricing method comparison (Black-Scholes vs American binomial vs Monte Carlo with stderr)
- 7 new API integration tests (30 quant tests total)

## [1.1.0] - 2026-07-07

### Added

- **Production ML system** — Persistent model registry (joblib artifacts + JSON metadata), background training jobs with live progress reporting, holdout evaluation (accuracy, precision, recall, F1, ROC AUC), confusion matrix, ROC curve, feature importance, per-fold CV scores
- **ML API** — `POST /ml/train` (async jobs), `GET /ml/train/{job}` (progress), `GET /ml/models` (registry), predict, compare, download, delete endpoints
- **ML Models page** — Full workflow UI: training progress bar, evaluation charts (ROC, confusion matrix, feature importance, CV folds), model registry table, predictions vs actuals, model comparison
- **Exchange Simulation Mode** — Dashboard auto-switches to a realistic random-walk market simulator (book, trades, risk) when the C++ backend is offline; status bar shows "Simulation"
- **Executions page** — Fill-level results with price/slippage charts and child order table
- **Market Making page** — PnL, inventory, and quotes-vs-mid time series from simulation history
- **Options page** — Price/delta profiles across spot, volatility smile chart from the surface API
- **Risk page** — Drawdown chart, stress scenarios, Monte Carlo VaR
- **Data Explorer** — Price/volume charts, feature catalog, latest bars table
- **Settings page** — Live service health, module status, configuration reference
- 11 new tests (ML registry, trainer, async jobs, API integration)

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
