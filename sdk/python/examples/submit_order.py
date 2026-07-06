#!/usr/bin/env python3
"""Example: submit orders to Aegis Exchange."""

import time
from aegis import AegisClient, OrderRequest, OrderSide, OrderType

def main():
    client = AegisClient("http://localhost:9080")

    print("Health:", client.health())
    print("Status:", client.status())

    # Seed sell liquidity
    sell = OrderRequest(
        client_order_id=int(time.time() * 1000),
        account_id=1,
        instrument_id=1,
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        price=50000.0,
        quantity=100,
    )
    print("Submit sell:", client.submit_order(sell))

    # Buy order
    buy = OrderRequest(
        client_order_id=int(time.time() * 1000) + 1,
        account_id=2,
        instrument_id=1,
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        price=50000.0,
        quantity=50,
    )
    print("Submit buy:", client.submit_order(buy))

    print("Book:", client.get_book(1))
    print("Trades:", client.get_trades(1))
    print("Risk:", client.get_risk())

if __name__ == "__main__":
    main()
