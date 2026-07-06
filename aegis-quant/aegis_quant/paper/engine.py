from __future__ import annotations

import httpx

from aegis_quant.core.config import settings
from aegis_quant.core.logging import get_logger
from aegis_quant.core.types import Side
from aegis_quant.data.connectors import AegisExchangeConnector

logger = get_logger(__name__)


class PaperTradingEngine:
    """Paper trading against live Aegis Exchange."""

    def __init__(self, base_url: str | None = None, account_id: int = 100):
        self.base_url = (base_url or settings.aegis_exchange_url).rstrip("/")
        self.account_id = account_id
        self.connector = AegisExchangeConnector(self.base_url)
        self._client_order_id = 1

    def submit_order(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        order_type: str = "LIMIT",
        price: float | None = None,
    ) -> dict:
        iid = self.connector._resolve_instrument(symbol)
        payload = {
            "client_order_id": self._client_order_id,
            "account_id": self.account_id,
            "instrument_id": iid,
            "side": side.value,
            "type": order_type,
            "quantity": int(quantity),
        }
        self._client_order_id += 1
        if price is not None:
            payload["price"] = price

        with httpx.Client(timeout=10) as client:
            resp = client.post(f"{self.base_url}/api/v1/orders", json=payload)
            resp.raise_for_status()
            result = resp.json()
        logger.info("paper_order", symbol=symbol, side=side.value, qty=quantity)
        return result

    def get_book(self, symbol: str) -> dict:
        book = self.connector.get_order_book(symbol)
        return book.model_dump()

    def get_positions(self) -> dict:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{self.base_url}/api/v1/risk")
            resp.raise_for_status()
            return resp.json().get("accounts", {}).get(str(self.account_id), {})
