from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from aegis_execution.algorithms import ChildOrder, ExecutionSchedule, OrderSide
from aegis_execution.slippage import SquareRootImpactModel


@dataclass
class SimConfig:
    commission_bps: float = 1.0
    latency_ms: float = 2.0
    partial_fill_prob: float = 0.05
    seed: int = 42


@dataclass
class SimFill:
    timestamp: datetime
    quantity: float
    price: float
    commission: float
    slippage_bps: float
    latency_ms: float


@dataclass
class SimResult:
    fills: list[SimFill]
    avg_price: float
    total_qty: float
    total_cost: float
    implementation_shortfall_bps: float
    metrics: dict[str, float] = field(default_factory=dict)


class ExecutionSimulator:
    """Simulate child order execution with latency, slippage, and partial fills."""

    def __init__(self, config: SimConfig | None = None):
        self.config = config or SimConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self._impact = SquareRootImpactModel()

    def run(self, schedule: ExecutionSchedule, market_data: pd.DataFrame) -> SimResult:
        if market_data.empty:
            raise ValueError("market_data required for simulation")
        arrival_price = float(market_data["close"].iloc[0])
        fills: list[SimFill] = []
        adv = float(market_data["volume"].mean()) if "volume" in market_data.columns else 1000.0
        vol = float(market_data["close"].pct_change().std()) if len(market_data) > 1 else 0.01
        spread = 0.0001

        for child in schedule.children:
            bar = self._bar_at(market_data, child.timestamp)
            mid = float(bar.get("close", arrival_price))
            slip_bps = self._impact.estimate(child.quantity, adv, vol, spread)
            slip = mid * slip_bps / 10_000
            fill_price = mid + slip if child.side == OrderSide.BUY else mid - slip
            qty = child.quantity
            if self._rng.random() < self.config.partial_fill_prob:
                qty *= self._rng.uniform(0.5, 0.95)
            commission = abs(qty * fill_price) * self.config.commission_bps / 10_000
            fills.append(
                SimFill(
                    timestamp=child.timestamp,
                    quantity=qty,
                    price=fill_price,
                    commission=commission,
                    slippage_bps=slip_bps,
                    latency_ms=self.config.latency_ms,
                )
            )

        total_qty = sum(f.quantity for f in fills)
        avg_price = sum(f.quantity * f.price for f in fills) / total_qty if total_qty > 0 else 0.0
        total_cost = sum(f.commission + f.quantity * f.price * f.slippage_bps / 10_000 for f in fills)
        sign = 1 if schedule.side == OrderSide.BUY else -1
        is_bps = sign * (avg_price - arrival_price) / arrival_price * 10_000 if arrival_price > 0 else 0.0

        return SimResult(
            fills=fills,
            avg_price=avg_price,
            total_qty=total_qty,
            total_cost=total_cost,
            implementation_shortfall_bps=is_bps,
            metrics={
                "avg_slippage_bps": float(np.mean([f.slippage_bps for f in fills])) if fills else 0.0,
                "fill_rate": total_qty / schedule.parent_qty if schedule.parent_qty > 0 else 0.0,
                "n_fills": len(fills),
            },
        )

    @staticmethod
    def _bar_at(data: pd.DataFrame, ts: datetime) -> dict:
        if "timestamp" not in data.columns:
            return data.iloc[min(len(data) - 1, 0)].to_dict()
        idx = data["timestamp"].searchsorted(ts, side="right") - 1
        idx = max(0, min(idx, len(data) - 1))
        return data.iloc[idx].to_dict()
