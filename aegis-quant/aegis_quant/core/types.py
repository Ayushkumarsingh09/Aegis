from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "POST_ONLY"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Bar(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float | None = None
    trades: int | None = None


class Tick(BaseModel):
    symbol: str
    timestamp: datetime
    price: float
    size: float
    side: Side | None = None


class OrderBookLevel(BaseModel):
    price: float
    quantity: float
    orders: int = 1


class OrderBook(BaseModel):
    symbol: str
    timestamp: datetime
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    sequence: int = 0


class Order(BaseModel):
    id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    strategy_id: str | None = None


class Fill(BaseModel):
    order_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    commission: float = 0.0
    slippage: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Position(BaseModel):
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0


class PortfolioSnapshot(BaseModel):
    timestamp: datetime
    cash: float
    equity: float
    positions: dict[str, Position]
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
