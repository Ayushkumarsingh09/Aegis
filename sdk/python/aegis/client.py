"""Aegis Exchange REST API client."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from aegis.types import OrderRequest


class AegisClient:
    """Synchronous REST client for the Aegis Exchange API."""

    def __init__(self, base_url: str = "http://localhost:9080", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if body else {}
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"API error {e.code}: {error_body}") from e
        except URLError as e:
            raise ConnectionError(f"Failed to connect to {url}: {e}") from e

    def health(self) -> Dict[str, str]:
        return self._request("GET", "/health")

    def status(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/status")

    def get_book(self, instrument_id: int, depth: int = 20) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/instruments/{instrument_id}/book?depth={depth}")

    def get_trades(self, instrument_id: int) -> List[Dict[str, Any]]:
        return self._request("GET", f"/api/v1/instruments/{instrument_id}/trades")

    def get_risk(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/risk")

    def submit_order(self, order: OrderRequest) -> List[Dict[str, Any]]:
        body = {
            "client_order_id": order.client_order_id,
            "account_id": order.account_id,
            "instrument_id": order.instrument_id,
            "side": order.side.value,
            "type": order.type.value,
            "quantity": order.quantity,
        }
        if order.price is not None:
            body["price"] = order.price
        if order.stop_price is not None:
            body["stop_price"] = order.stop_price
        return self._request("POST", "/api/v1/orders", body)

    def cancel_order(self, order_id: int, account_id: int, instrument_id: int) -> List[Dict[str, Any]]:
        return self._request("DELETE", "/api/v1/orders", {
            "order_id": order_id,
            "account_id": account_id,
            "instrument_id": instrument_id,
        })

    def modify_order(
        self, order_id: int, account_id: int, instrument_id: int,
        quantity: int, price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {
            "order_id": order_id,
            "account_id": account_id,
            "instrument_id": instrument_id,
            "quantity": quantity,
        }
        if price is not None:
            body["price"] = price
        return self._request("PUT", "/api/v1/orders", body)

    def set_kill_switch(self, active: bool, reason: str = "manual") -> Dict[str, str]:
        return self._request("POST", "/api/v1/risk/kill-switch", {
            "active": active,
            "reason": reason,
        })

    def get_metrics(self) -> str:
        url = f"{self.base_url}/metrics"
        req = Request(url, method="GET")
        with urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode()
