from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class QuoteResult:
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    reservation_price: float
    spread: float
    skew: float


class AvellanedaStoikov:
    """Avellaneda-Stoikov optimal market making quotes."""

    def __init__(self, gamma: float = 0.1, k: float = 1.5, sigma: float = 0.02):
        self.gamma = gamma  # risk aversion
        self.k = k  # order book depth parameter
        self.sigma = sigma  # volatility

    def compute_quotes(
        self,
        mid: float,
        inventory: float,
        time_remaining: float,
        max_inventory: float = 100.0,
        base_size: float = 10.0,
    ) -> QuoteResult:
        T = max(time_remaining, 1e-6)
        reservation = mid - inventory * self.gamma * self.sigma**2 * T
        optimal_spread = self.gamma * self.sigma**2 * T + (2 / self.gamma) * math.log(1 + self.gamma / self.k)
        half_spread = optimal_spread / 2
        bid = reservation - half_spread
        ask = reservation + half_spread
        inv_ratio = inventory / max_inventory if max_inventory > 0 else 0
        bid_size = base_size * max(0.1, 1 - inv_ratio)
        ask_size = base_size * max(0.1, 1 + inv_ratio)
        return QuoteResult(
            bid_price=bid,
            ask_price=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            reservation_price=reservation,
            spread=ask - bid,
            skew=-inventory * self.gamma * self.sigma**2,
        )

    def fill_probability(self, distance: float) -> float:
        """Exponential fill probability model."""
        return math.exp(-self.k * max(0, distance))
