from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InventoryManager:
    max_inventory: float = 100.0
    target_inventory: float = 0.0
    inventory: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl: float = 0.0

    def update_fill(self, side: str, quantity: float, price: float) -> float:
        sign = 1 if side == "buy" else -1
        trade_pnl = 0.0
        if self.inventory != 0 and sign != (1 if self.inventory > 0 else -1):
            close_qty = min(abs(self.inventory), quantity)
            trade_pnl = close_qty * (price - self.avg_entry_price) * (1 if self.inventory > 0 else -1)
            self.realized_pnl += trade_pnl
        new_inv = self.inventory + sign * quantity
        if new_inv == 0:
            self.avg_entry_price = 0.0
        elif self.inventory == 0 or (self.inventory > 0) == (new_inv > 0):
            total_cost = self.avg_entry_price * abs(self.inventory) + price * quantity
            self.avg_entry_price = total_cost / abs(new_inv)
        self.inventory = new_inv
        return trade_pnl

    @property
    def unrealized_pnl(self) -> float:
        return 0.0

    def unrealized_at(self, mid: float) -> float:
        if self.inventory == 0:
            return 0.0
        return self.inventory * (mid - self.avg_entry_price)

    def within_limits(self) -> bool:
        return abs(self.inventory) <= self.max_inventory

    def inventory_skew(self) -> float:
        if self.max_inventory <= 0:
            return 0.0
        return self.inventory / self.max_inventory
