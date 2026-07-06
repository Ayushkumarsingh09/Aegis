from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Iterator

import numpy as np
import pandas as pd


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class ChildOrder:
    timestamp: datetime
    quantity: float
    side: OrderSide
    order_type: str = "LIMIT"
    price: float | None = None
    display_qty: float | None = None


@dataclass
class ExecutionSchedule:
    parent_qty: float
    side: OrderSide
    symbol: str
    children: list[ChildOrder] = field(default_factory=list)
    benchmark: str = "arrival"


class ExecutionAlgorithm(ABC):
    @abstractmethod
    def schedule(
        self,
        quantity: float,
        side: OrderSide,
        symbol: str,
        start: datetime,
        end: datetime,
        market_data: pd.DataFrame | None = None,
    ) -> ExecutionSchedule:
        ...


class TWAPExecutor(ExecutionAlgorithm):
    """Time-Weighted Average Price — equal slices over the horizon."""

    def __init__(self, n_slices: int = 10):
        self.n_slices = max(1, n_slices)

    def schedule(
        self,
        quantity: float,
        side: OrderSide,
        symbol: str,
        start: datetime,
        end: datetime,
        market_data: pd.DataFrame | None = None,
    ) -> ExecutionSchedule:
        duration = (end - start).total_seconds()
        interval = duration / self.n_slices
        slice_qty = quantity / self.n_slices
        children = []
        for i in range(self.n_slices):
            ts = start + timedelta(seconds=interval * i)
            children.append(ChildOrder(timestamp=ts, quantity=slice_qty, side=side))
        return ExecutionSchedule(
            parent_qty=quantity, side=side, symbol=symbol, children=children, benchmark="twap"
        )


class VWAPExecutor(ExecutionAlgorithm):
    """Volume-Weighted Average Price — slice proportional to historical volume profile."""

    def __init__(self, n_buckets: int = 10):
        self.n_buckets = max(1, n_buckets)

    def schedule(
        self,
        quantity: float,
        side: OrderSide,
        symbol: str,
        start: datetime,
        end: datetime,
        market_data: pd.DataFrame | None = None,
    ) -> ExecutionSchedule:
        duration = (end - start).total_seconds()
        interval = duration / self.n_buckets
        if market_data is not None and "volume" in market_data.columns and len(market_data) >= self.n_buckets:
            vol_profile = market_data["volume"].values[-self.n_buckets :]
            vol_profile = vol_profile / vol_profile.sum()
        else:
            vol_profile = np.ones(self.n_buckets) / self.n_buckets
        children = []
        for i, w in enumerate(vol_profile):
            ts = start + timedelta(seconds=interval * i)
            children.append(ChildOrder(timestamp=ts, quantity=quantity * w, side=side))
        return ExecutionSchedule(
            parent_qty=quantity, side=side, symbol=symbol, children=children, benchmark="vwap"
        )


class POVExecutor(ExecutionAlgorithm):
    """Percentage of Volume — target fraction of market volume."""

    def __init__(self, participation_rate: float = 0.1, n_slices: int = 10):
        self.participation_rate = min(1.0, max(0.01, participation_rate))
        self.n_slices = max(1, n_slices)

    def schedule(
        self,
        quantity: float,
        side: OrderSide,
        symbol: str,
        start: datetime,
        end: datetime,
        market_data: pd.DataFrame | None = None,
    ) -> ExecutionSchedule:
        duration = (end - start).total_seconds()
        interval = duration / self.n_slices
        children = []
        remaining = quantity
        for i in range(self.n_slices):
            ts = start + timedelta(seconds=interval * i)
            if market_data is not None and "volume" in market_data.columns:
                idx = min(i, len(market_data) - 1)
                mkt_vol = float(market_data["volume"].iloc[idx])
                slice_qty = min(remaining, mkt_vol * self.participation_rate)
            else:
                slice_qty = quantity / self.n_slices
            if slice_qty <= 0:
                continue
            children.append(ChildOrder(timestamp=ts, quantity=slice_qty, side=side))
            remaining -= slice_qty
            if remaining <= 1e-9:
                break
        return ExecutionSchedule(
            parent_qty=quantity, side=side, symbol=symbol, children=children, benchmark="pov"
        )


class IcebergExecutor(ExecutionAlgorithm):
    """Iceberg — display only a fraction of total quantity per child order."""

    def __init__(self, display_pct: float = 0.1, interval_sec: float = 60.0):
        self.display_pct = min(1.0, max(0.01, display_pct))
        self.interval_sec = interval_sec

    def schedule(
        self,
        quantity: float,
        side: OrderSide,
        symbol: str,
        start: datetime,
        end: datetime,
        market_data: pd.DataFrame | None = None,
    ) -> ExecutionSchedule:
        display_qty = quantity * self.display_pct
        n_slices = max(1, int((end - start).total_seconds() / self.interval_sec))
        slice_qty = quantity / n_slices
        children = []
        for i in range(n_slices):
            ts = start + timedelta(seconds=self.interval_sec * i)
            children.append(
                ChildOrder(
                    timestamp=ts,
                    quantity=slice_qty,
                    side=side,
                    display_qty=min(display_qty, slice_qty),
                )
            )
        return ExecutionSchedule(
            parent_qty=quantity, side=side, symbol=symbol, children=children, benchmark="iceberg"
        )


class ArrivalPriceExecutor(ExecutionAlgorithm):
    """Minimize implementation shortfall vs arrival price — front-loaded schedule."""

    def __init__(self, urgency: float = 0.5, n_slices: int = 10):
        self.urgency = min(1.0, max(0.0, urgency))
        self.n_slices = max(1, n_slices)

    def schedule(
        self,
        quantity: float,
        side: OrderSide,
        symbol: str,
        start: datetime,
        end: datetime,
        market_data: pd.DataFrame | None = None,
    ) -> ExecutionSchedule:
        duration = (end - start).total_seconds()
        weights = np.exp(-self.urgency * np.linspace(0, 3, self.n_slices))
        weights /= weights.sum()
        interval = duration / self.n_slices
        children = []
        for i, w in enumerate(weights):
            ts = start + timedelta(seconds=interval * i)
            children.append(ChildOrder(timestamp=ts, quantity=quantity * w, side=side))
        return ExecutionSchedule(
            parent_qty=quantity,
            side=side,
            symbol=symbol,
            children=children,
            benchmark="arrival_price",
        )


def implementation_shortfall(
    fills: pd.DataFrame,
    arrival_price: float,
    side: OrderSide,
) -> float:
    """Compute IS = (avg_fill - arrival) / arrival for buys (inverted for sells)."""
    if fills.empty:
        return 0.0
    avg_fill = (fills["price"] * fills["quantity"]).sum() / fills["quantity"].sum()
    sign = 1 if side == OrderSide.BUY else -1
    return sign * (avg_fill - arrival_price) / arrival_price
