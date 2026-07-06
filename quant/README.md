# Quant Research Module

The **Aegis Quant** research platform is located in [`aegis-quant/`](../aegis-quant/).

## Components

| Package | Path |
|---------|------|
| Market Data Engine | `aegis-quant/aegis_quant/data/` |
| Feature Engineering | `aegis-quant/aegis_quant/features/` |
| Factor Research | `aegis-quant/aegis_quant/factors/` |
| Strategy Framework | `aegis-quant/aegis_quant/strategy/` |
| Backtester | `aegis-quant/aegis_quant/backtest/` |
| ML Pipeline | `aegis-quant/aegis_quant/ml/` |
| Portfolio Optimizer | `aegis-quant/aegis_quant/portfolio/` |
| Paper Trading | `aegis-quant/aegis_quant/paper/` |

## Quick Start

```bash
python scripts/install-platform.py
aegis-quant serve
# API: http://localhost:8090
# Dashboard: http://localhost:4100
```

See [aegis-quant/README.md](../aegis-quant/README.md).
