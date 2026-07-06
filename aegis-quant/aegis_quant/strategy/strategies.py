from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import pandas as pd

from aegis_quant.backtest.engine import BacktestContext, BacktestResult, EventDrivenBacktester
from aegis_quant.core.types import OrderType, Side


class Strategy(ABC):
    """Base class for all trading strategies."""

    name: str = "base"
    symbols: list[str] = []

    @abstractmethod
    def on_bar(self, ctx: BacktestContext, bar: dict) -> None:
        ...

    def get_handler(self) -> Callable:
        def handler(ctx: BacktestContext, bar: dict) -> None:
            self.on_bar(ctx, bar)

        return handler


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"
    lookback = 20
    entry_z = 2.0
    exit_z = 0.5

    def __init__(self, symbol: str):
        self.symbols = [symbol]
        self.symbol = symbol
        self._prices: list[float] = []

    def on_bar(self, ctx: BacktestContext, bar: dict) -> None:
        self._prices.append(bar["close"])
        if len(self._prices) < self.lookback:
            return
        window = self._prices[-self.lookback :]
        mean = sum(window) / len(window)
        std = (sum((p - mean) ** 2 for p in window) / len(window)) ** 0.5
        if std < 1e-9:
            return
        z = (bar["close"] - mean) / std
        pos = ctx.positions.get(self.symbol, 0)
        if z < -self.entry_z and pos <= 0:
            ctx.order(self.symbol, Side.BUY, 10, strategy_id=self.name)
        elif z > self.entry_z and pos >= 0:
            ctx.order(self.symbol, Side.SELL, 10, strategy_id=self.name)
        elif abs(z) < self.exit_z and pos != 0:
            side = Side.SELL if pos > 0 else Side.BUY
            ctx.order(self.symbol, side, abs(pos), strategy_id=self.name)


class MomentumStrategy(Strategy):
    name = "momentum"
    lookback = 12

    def __init__(self, symbol: str):
        self.symbols = [symbol]
        self.symbol = symbol
        self._prices: list[float] = []

    def on_bar(self, ctx: BacktestContext, bar: dict) -> None:
        self._prices.append(bar["close"])
        if len(self._prices) < self.lookback + 1:
            return
        mom = bar["close"] / self._prices[-self.lookback - 1] - 1
        pos = ctx.positions.get(self.symbol, 0)
        if mom > 0.02 and pos <= 0:
            ctx.order(self.symbol, Side.BUY, 10, strategy_id=self.name)
        elif mom < -0.02 and pos >= 0:
            ctx.order(self.symbol, Side.SELL, 10, strategy_id=self.name)


class PairsTradingStrategy(Strategy):
    name = "pairs_trading"
    lookback = 60
    entry_z = 2.0

    def __init__(self, symbol_a: str, symbol_b: str):
        self.symbols = [symbol_a, symbol_b]
        self.sym_a, self.sym_b = symbol_a, symbol_b
        self._spread: list[float] = []
        self._last_b_price = 0.0

    def on_bar(self, ctx: BacktestContext, bar: dict) -> None:
        if bar["symbol"] == self.sym_b:
            self._last_b_price = bar["close"]
            return
        if self._last_b_price <= 0:
            return
        spread = bar["close"] - self._last_b_price
        self._spread.append(spread)
        if len(self._spread) < self.lookback:
            return
        window = self._spread[-self.lookback :]
        mean, std = sum(window) / len(window), pd.Series(window).std()
        if std < 1e-9:
            return
        z = (spread - mean) / std
        pos_a = ctx.positions.get(self.sym_a, 0)
        if z > self.entry_z and pos_a >= 0:
            ctx.order(self.sym_a, Side.SELL, 10, strategy_id=self.name)
            ctx.order(self.sym_b, Side.BUY, 10, strategy_id=self.name)
        elif z < -self.entry_z and pos_a <= 0:
            ctx.order(self.sym_a, Side.BUY, 10, strategy_id=self.name)
            ctx.order(self.sym_b, Side.SELL, 10, strategy_id=self.name)


class MarketMakingStrategy(Strategy):
    name = "market_making"
    spread_bps = 10

    def __init__(self, symbol: str, size: float = 5):
        self.symbols = [symbol]
        self.symbol = symbol
        self.size = size

    def on_bar(self, ctx: BacktestContext, bar: dict) -> None:
        mid = bar["close"]
        half_spread = mid * self.spread_bps / 10_000 / 2
        pos = ctx.positions.get(self.symbol, 0)
        if pos < self.size * 2:
            ctx.order(self.symbol, Side.BUY, self.size, OrderType.LIMIT, mid - half_spread, self.name)
        if pos > -self.size * 2:
            ctx.order(self.symbol, Side.SELL, self.size, OrderType.LIMIT, mid + half_spread, self.name)


STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "mean_reversion": MeanReversionStrategy,
    "momentum": MomentumStrategy,
    "pairs_trading": PairsTradingStrategy,
    "market_making": MarketMakingStrategy,
}


def run_strategy(strategy: Strategy, data: pd.DataFrame) -> BacktestResult:
    bt = EventDrivenBacktester()
    return bt.run(data, strategy.get_handler())
