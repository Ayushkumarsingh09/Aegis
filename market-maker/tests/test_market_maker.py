from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from aegis_market_maker.engine import MarketMakingEngine, MMConfig
from aegis_market_maker.inventory import InventoryManager
from aegis_market_maker.model import AvellanedaStoikov
from aegis_market_maker.simulator import MMSimulator


def test_avellaneda_stoikov_quotes():
    model = AvellanedaStoikov(gamma=0.1, k=1.5, sigma=0.02)
    quote = model.compute_quotes(mid=100, inventory=0, time_remaining=4.0)
    assert quote.bid_price < quote.ask_price
    assert quote.spread > 0


def test_inventory_skew():
    model = AvellanedaStoikov()
    q0 = model.compute_quotes(100, 0, 4.0)
    q_long = model.compute_quotes(100, 20, 4.0)
    assert q_long.bid_price < q0.bid_price


def test_inventory_manager():
    inv = InventoryManager(max_inventory=50)
    inv.update_fill("buy", 10, 100)
    assert inv.inventory == 10
    pnl = inv.update_fill("sell", 5, 105)
    assert pnl > 0
    assert inv.inventory == 5


def test_market_making_engine():
    engine = MarketMakingEngine(MMConfig(symbol="TEST"))
    ts = datetime(2024, 1, 1)
    quote = engine.on_bar(ts, 100.0, 0.02)
    assert quote.bid_price < quote.ask_price
    engine.on_fill("buy", 5, quote.bid_price)
    assert engine.inventory.inventory == 5


def test_mm_simulator():
    n = 100
    bars = pd.DataFrame({
        "timestamp": [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)],
        "close": 100 + np.cumsum(np.random.randn(n) * 0.1),
        "realized_vol": 0.02,
    })
    result = MMSimulator(MMConfig(), seed=42).run(bars)
    assert result.n_fills >= 0
    assert "pnl" in result.history.columns or result.n_fills == 0
