from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class SlippageModel(ABC):
    @abstractmethod
    def estimate(self, quantity: float, adv: float, volatility: float, spread: float) -> float:
        """Return estimated slippage in basis points."""
        ...


class LinearImpactModel(SlippageModel):
    """Linear market impact: slippage proportional to participation rate."""

    def __init__(self, coefficient: float = 10.0):
        self.coefficient = coefficient

    def estimate(self, quantity: float, adv: float, volatility: float, spread: float) -> float:
        if adv <= 0:
            return spread * 10_000
        participation = quantity / adv
        return self.coefficient * participation * 10_000 + spread * 10_000 / 2


class SquareRootImpactModel(SlippageModel):
    """Square-root law of market impact (Almgren-Chriss style)."""

    def __init__(self, eta: float = 0.1, gamma: float = 0.05):
        self.eta = eta
        self.gamma = gamma

    def estimate(self, quantity: float, adv: float, volatility: float, spread: float) -> float:
        if adv <= 0:
            return spread * 10_000
        participation = quantity / adv
        temporary = self.eta * volatility * np.sqrt(participation) * 10_000
        permanent = self.gamma * volatility * participation * 10_000
        return temporary + permanent + spread * 10_000 / 2
