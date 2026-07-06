# Market Maker

Live market making engine with Avellaneda-Stoikov optimal quoting.

## Features

- Avellaneda-Stoikov reservation price and optimal spread
- Inventory management and risk limits
- Dynamic spread adjustment based on inventory skew
- Fill probability estimation
- Simulation against historical data
- Integration with Aegis Exchange for live quoting

## Usage

```python
from datetime import datetime
from aegis_market_maker import MarketMakingEngine, MMConfig, MMSimulator

engine = MarketMakingEngine(MMConfig(symbol="BTC-USD", gamma=0.1))
quote = engine.on_bar(datetime.utcnow(), mid=50000.0, volatility=0.02)
print(f"Bid: {quote.bid_price}, Ask: {quote.ask_price}")

result = MMSimulator().run(historical_bars)
print(f"PnL: {result.pnl}, Fills: {result.n_fills}")
```

## Tests

```bash
pytest market-maker/tests/ -v
```
