from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from aegis_market_maker.engine import MarketMakingEngine, MMConfig


@dataclass
class SimResult:
    pnl: float
    n_fills: int
    avg_spread_captured: float
    max_inventory: float
    fill_rate: float
    history: pd.DataFrame = field(default_factory=pd.DataFrame)


class MMSimulator:
    """Simulate market making against historical mid-price series."""

    def __init__(self, config: MMConfig | None = None, seed: int = 42):
        self.config = config or MMConfig()
        self._rng = np.random.default_rng(seed)

    def run(self, bars: pd.DataFrame) -> SimResult:
        engine = MarketMakingEngine(self.config)
        fills = 0
        spread_captured = []
        max_inv = 0.0

        for _, row in bars.iterrows():
            mid = float(row["close"])
            vol = float(row.get("realized_vol", 0.02)) if "realized_vol" in row else 0.02
            ts = row["timestamp"]
            quote = engine.on_bar(ts, mid, vol)
            max_inv = max(max_inv, abs(engine.inventory.inventory))

            bid_dist = (mid - quote.bid_price) / mid
            ask_dist = (quote.ask_price - mid) / mid
            bid_prob = engine.model.fill_probability(bid_dist)
            ask_prob = engine.model.fill_probability(ask_dist)

            if self._rng.random() < bid_prob * 0.1:
                qty = min(quote.bid_size, self.config.base_size)
                engine.on_fill("buy", qty, quote.bid_price)
                spread_captured.append(mid - quote.bid_price)
                fills += 1
            if self._rng.random() < ask_prob * 0.1:
                qty = min(quote.ask_size, self.config.base_size)
                engine.on_fill("sell", qty, quote.ask_price)
                spread_captured.append(quote.ask_price - mid)
                fills += 1

        history = pd.DataFrame([
            {
                "timestamp": s.timestamp,
                "mid": s.mid,
                "inventory": s.inventory,
                "bid": s.quote.bid_price,
                "ask": s.quote.ask_price,
                "pnl": s.realized_pnl + s.unrealized_pnl,
            }
            for s in engine.history
        ])
        return SimResult(
            pnl=engine.total_pnl,
            n_fills=fills,
            avg_spread_captured=float(np.mean(spread_captured)) if spread_captured else 0.0,
            max_inventory=max_inv,
            fill_rate=fills / max(1, len(bars)),
            history=history,
        )
