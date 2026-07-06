from enum import Enum
from dataclasses import dataclass
from typing import Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "POST_ONLY"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


@dataclass
class OrderRequest:
    client_order_id: int
    account_id: int
    instrument_id: int
    side: OrderSide
    type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
