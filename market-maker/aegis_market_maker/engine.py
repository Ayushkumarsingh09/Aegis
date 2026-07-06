from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from aegis_market_maker.inventory import InventoryManager
from aegis_market_maker.model import AvellanedaStoikov, QuoteResult


@dataclass
class MMConfig:
    symbol: str = "BTC-USD"
    gamma: float = 0.1
    k: float = 1.5
    base_size: float = 5.0
    max_inventory: float = 50.0
    session_hours: float = 8.0


@dataclass
class MMState:
    timestamp: datetime
    mid: float
    inventory: float
    quote: QuoteResult
    realized_pnl: float
    unrealized_pnl: float


class MarketMakingEngine:
    """Live market making quote engine."""

    def __init__(self, config: MMConfig | None = None):
        self.config = config or MMConfig()
        self.model = AvellanedaStoikov(gamma=self.config.gamma, k=self.config.k)
        self.inventory = InventoryManager(max_inventory=self.config.max_inventory)
        self._start: datetime | None = None
        self.history: list[MMState] = []

    def on_bar(self, timestamp: datetime, mid: float, volatility: float = 0.02) -> QuoteResult:
        if self._start is None:
            self._start = timestamp
        elapsed = (timestamp - self._start).total_seconds() / 3600
        remaining = max(0.01, self.config.session_hours - elapsed)
        self.model.sigma = volatility
        quote = self.model.compute_quotes(
            mid=mid,
            inventory=self.inventory.inventory,
            time_remaining=remaining,
            max_inventory=self.config.max_inventory,
            base_size=self.config.base_size,
        )
        unrealized = self.inventory.unrealized_at(mid)
        self.history.append(
            MMState(
                timestamp=timestamp,
                mid=mid,
                inventory=self.inventory.inventory,
                quote=quote,
                realized_pnl=self.inventory.realized_pnl,
                unrealized_pnl=unrealized,
            )
        )
        return quote

    def on_fill(self, side: str, quantity: float, price: float) -> float:
        return self.inventory.update_fill(side, quantity, price)

    @property
    def total_pnl(self) -> float:
        if not self.history:
            return self.inventory.realized_pnl
        return self.inventory.realized_pnl + self.history[-1].unrealized_pnl

    def pnl_series(self) -> pd.Series:
        if not self.history:
            return pd.Series(dtype=float)
        return pd.Series(
            [s.realized_pnl + s.unrealized_pnl for s in self.history],
            index=[s.timestamp for s in self.history],
            name="pnl",
        )
