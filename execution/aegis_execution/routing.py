from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Venue(str, Enum):
    AEGIS = "aegis"
    BINANCE = "binance"
    ALPACA = "alpaca"


@dataclass
class RouteDecision:
    venue: Venue
    quantity: float
    expected_cost_bps: float
    latency_ms: float


@dataclass
class VenueQuote:
    venue: Venue
    bid: float
    ask: float
    bid_qty: float
    ask_qty: float
    latency_ms: float = 1.0
    fee_bps: float = 1.0


class SmartRouter:
    """Smart order routing abstraction — selects venue by effective cost."""

    def __init__(self, venues: list[Venue] | None = None):
        self.venues = venues or [Venue.AEGIS]

    def route(self, quantity: float, side: str, quotes: list[VenueQuote]) -> list[RouteDecision]:
        if not quotes:
            return [RouteDecision(venue=Venue.AEGIS, quantity=quantity, expected_cost_bps=5.0, latency_ms=1.0)]
        scored = []
        for q in quotes:
            mid = (q.bid + q.ask) / 2
            spread_bps = (q.ask - q.bid) / mid * 10_000 if mid > 0 else 999
            depth = q.ask_qty if side == "buy" else q.bid_qty
            fillable = min(quantity, depth) if depth > 0 else quantity
            cost = spread_bps / 2 + q.fee_bps
            scored.append((cost, q, fillable))
        scored.sort(key=lambda x: x[0])
        decisions = []
        remaining = quantity
        for cost, q, fillable in scored:
            if remaining <= 0:
                break
            qty = min(remaining, fillable)
            decisions.append(
                RouteDecision(venue=q.venue, quantity=qty, expected_cost_bps=cost, latency_ms=q.latency_ms)
            )
            remaining -= qty
        if remaining > 0 and decisions:
            decisions[-1].quantity += remaining
        elif remaining > 0:
            decisions.append(
                RouteDecision(venue=quotes[0].venue, quantity=remaining, expected_cost_bps=10.0, latency_ms=5.0)
            )
        return decisions
