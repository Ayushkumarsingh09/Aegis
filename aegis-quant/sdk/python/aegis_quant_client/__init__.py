"""Aegis Quant Python SDK."""

from __future__ import annotations

from typing import Any

import httpx


class AegisQuantClient:
    def __init__(self, base_url: str = "http://localhost:8090", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, **params) -> Any:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.get(f"{self.base_url}{path}", params=params)
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, body: dict) -> Any:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.base_url}{path}", json=body)
            r.raise_for_status()
            return r.json()

    def health(self) -> dict:
        return self._get("/health")

    def symbols(self) -> list[str]:
        return self._get("/api/v1/symbols")["symbols"]

    def get_bars(self, symbol: str) -> list[dict]:
        return self._get(f"/api/v1/data/{symbol}")

    def backtest(self, strategy: str, symbol: str, **kwargs) -> dict:
        return self._post("/api/v1/backtest", {"strategy": strategy, "symbol": symbol, **kwargs})

    def optimize(self, symbols: list[str], method: str = "max_sharpe") -> dict:
        return self._post("/api/v1/portfolio/optimize", {"symbols": symbols, "method": method})

    def train_model(self, symbol: str, model: str = "random_forest") -> dict:
        return self._post("/api/v1/ml/train", {"symbol": symbol, "model": model})

    def risk_metrics(self, symbol: str) -> dict:
        return self._get(f"/api/v1/risk/metrics/{symbol}")

    def list_strategies(self) -> list[str]:
        return self._get("/api/v1/strategies")["strategies"]
