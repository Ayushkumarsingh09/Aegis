from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable

import pandas as pd

from aegis_quant.core.types import Fill, Order, OrderStatus, OrderType, Side


class EventType(Enum):
    MARKET = auto()
    ORDER = auto()
    FILL = auto()
    TIMER = auto()


@dataclass
class Event:
    type: EventType
    timestamp: datetime
    data: Any = None
    priority: int = 0


@dataclass
class BacktestConfig:
    initial_cash: float = 1_000_000.0
    commission_bps: float = 1.0
    slippage_bps: float = 2.0
    latency_ms: float = 1.0
    borrow_cost_annual: float = 0.02
    deterministic: bool = True


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    trades: pd.DataFrame
    orders: list[Order]
    fills: list[Fill]
    metrics: dict[str, float]
    positions_history: pd.DataFrame = field(default_factory=pd.DataFrame)


class ExecutionSimulator:
    """Simulates order execution with latency, slippage, and partial fills."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self._order_queue: list[tuple[datetime, Order]] = []

    def submit(self, order: Order, market_price: float, timestamp: datetime) -> Order:
        order.status = OrderStatus.SUBMITTED
        exec_time = timestamp + pd.Timedelta(milliseconds=self.config.latency_ms)
        self._order_queue.append((exec_time, order))
        return order

    def process_queue(self, timestamp: datetime, market_data: dict) -> list[Fill]:
        fills = []
        remaining = []
        for exec_time, order in self._order_queue:
            if exec_time > timestamp:
                remaining.append((exec_time, order))
                continue
            fill = self._try_fill(order, market_data, timestamp)
            if fill:
                fills.append(fill)
            else:
                remaining.append((exec_time, order))
        self._order_queue = remaining
        return fills

    def _try_fill(self, order: Order, market_data: dict, timestamp: datetime) -> Fill | None:
        price = market_data.get("close", market_data.get("price", 0))
        bid = market_data.get("bid", price * 0.9999)
        ask = market_data.get("ask", price * 1.0001)

        slip = self.config.slippage_bps / 10_000
        if order.order_type == OrderType.MARKET:
            fill_price = ask * (1 + slip) if order.side == Side.BUY else bid * (1 - slip)
        elif order.order_type == OrderType.LIMIT:
            if order.price is None:
                return None
            if order.side == Side.BUY and order.price < ask:
                return None
            if order.side == Side.SELL and order.price > bid:
                return None
            fill_price = order.price
        else:
            fill_price = price

        qty = order.quantity - order.filled_qty
        if qty <= 0:
            return None

        commission = abs(qty * fill_price) * self.config.commission_bps / 10_000
        slippage_cost = abs(qty * fill_price) * self.config.slippage_bps / 10_000

        order.filled_qty += qty
        order.avg_fill_price = fill_price
        order.status = OrderStatus.FILLED

        return Fill(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=qty,
            price=fill_price,
            commission=commission,
            slippage=slippage_cost,
            timestamp=timestamp,
        )


class EventDrivenBacktester:
    """Institutional event-driven backtesting engine."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.executor = ExecutionSimulator(self.config)
        self.cash = self.config.initial_cash
        self.positions: dict[str, float] = {}
        self.avg_prices: dict[str, float] = {}
        self.fills: list[Fill] = []
        self.orders: list[Order] = []
        self.equity_history: list[tuple[datetime, float]] = []

    def run(self, data: pd.DataFrame, strategy_fn: Callable) -> BacktestResult:
        data = data.sort_values("timestamp").reset_index(drop=True)
        context = BacktestContext(self)

        for i, row in data.iterrows():
            ts = row["timestamp"]
            market = row.to_dict()
            context._current_bar = market
            context._timestamp = ts

            # Process pending orders
            new_fills = self.executor.process_queue(ts, market)
            for fill in new_fills:
                self._apply_fill(fill)
                context.on_fill(fill)

            # Strategy signal
            strategy_fn(context, market)

            # Mark to market
            equity = self._equity(market)
            self.equity_history.append((ts, equity))

        return self._build_result(data)

    def _apply_fill(self, fill: Fill) -> None:
        self.fills.append(fill)
        sign = 1 if fill.side == Side.BUY else -1
        cost = fill.quantity * fill.price * sign + fill.commission + fill.slippage
        self.cash -= cost

        sym = fill.symbol
        prev_qty = self.positions.get(sym, 0)
        new_qty = prev_qty + sign * fill.quantity
        if new_qty == 0:
            self.positions.pop(sym, None)
            self.avg_prices.pop(sym, None)
        else:
            if prev_qty == 0 or (prev_qty > 0) == (new_qty > 0):
                total_cost = self.avg_prices.get(sym, 0) * abs(prev_qty) + fill.price * fill.quantity
                self.avg_prices[sym] = total_cost / abs(new_qty)
            self.positions[sym] = new_qty

    def _equity(self, market: dict) -> float:
        price = market.get("close", 0)
        pos_value = sum(qty * price for qty in self.positions.values())
        return self.cash + pos_value

    def _build_result(self, data: pd.DataFrame) -> BacktestResult:
        eq = pd.Series(
            [e for _, e in self.equity_history],
            index=[t for t, _ in self.equity_history],
            name="equity",
        )
        rets = eq.pct_change().dropna()
        from aegis_quant.risk.metrics import RiskEngine

        risk = RiskEngine()
        metrics = risk.compute_all(rets, eq)
        trades_df = pd.DataFrame([f.model_dump() for f in self.fills]) if self.fills else pd.DataFrame()
        return BacktestResult(
            equity_curve=eq,
            returns=rets,
            trades=trades_df,
            orders=self.orders,
            fills=self.fills,
            metrics=metrics,
        )


class BacktestContext:
    def __init__(self, engine: EventDrivenBacktester):
        self._engine = engine
        self._current_bar: dict = {}
        self._timestamp: datetime | None = None
        self._fill_callbacks: list[Callable] = []

    @property
    def cash(self) -> float:
        return self._engine.cash

    @property
    def positions(self) -> dict[str, float]:
        return self._engine.positions.copy()

    @property
    def timestamp(self) -> datetime | None:
        return self._timestamp

    def order(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: float | None = None,
        strategy_id: str | None = None,
    ) -> Order:
        import uuid

        order = Order(
            id=str(uuid.uuid4())[:8],
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            strategy_id=strategy_id,
        )
        self._engine.orders.append(order)
        price_ref = self._current_bar.get("close", 0)
        self._engine.executor.submit(order, price_ref, self._timestamp)
        return order

    def register_fill_callback(self, callback: Callable) -> None:
        self._fill_callbacks.append(callback)

    def _dispatch_fill(self, fill: Fill) -> None:
        for cb in self._fill_callbacks:
            cb(fill)

    def on_fill(self, fill: Fill) -> None:
        self._dispatch_fill(fill)
