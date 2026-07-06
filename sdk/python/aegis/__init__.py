"""Aegis Exchange Python SDK."""

from aegis.client import AegisClient
from aegis.types import OrderRequest, OrderSide, OrderType

__version__ = "1.0.0"
__all__ = ["AegisClient", "OrderRequest", "OrderSide", "OrderType"]
