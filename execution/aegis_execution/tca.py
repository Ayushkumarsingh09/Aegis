from __future__ import annotations

import pandas as pd


class TransactionCostAnalyzer:
    """Transaction cost analysis for execution quality measurement."""

    def analyze(
        self,
        fills: pd.DataFrame,
        benchmark_prices: dict[str, float],
        side: str,
    ) -> dict[str, float]:
        if fills.empty:
            return {"total_cost_bps": 0.0, "commission_bps": 0.0, "slippage_bps": 0.0}
        total_qty = fills["quantity"].sum()
        avg_price = (fills["price"] * fills["quantity"]).sum() / total_qty
        notional = avg_price * total_qty
        sign = 1 if side == "buy" else -1

        results = {}
        for bench_name, bench_price in benchmark_prices.items():
            if bench_price <= 0:
                continue
            cost_bps = sign * (avg_price - bench_price) / bench_price * 10_000
            results[f"vs_{bench_name}_bps"] = float(cost_bps)

        commission = fills["commission"].sum() if "commission" in fills.columns else 0.0
        slippage = fills["slippage"].sum() if "slippage" in fills.columns else 0.0
        results["commission_bps"] = float(commission / notional * 10_000) if notional > 0 else 0.0
        results["slippage_bps"] = float(slippage / notional * 10_000) if notional > 0 else 0.0
        results["avg_fill_price"] = float(avg_price)
        results["total_quantity"] = float(total_qty)
        results["total_notional"] = float(notional)
        return results

    def compare_algorithms(self, results: dict[str, dict[str, float]]) -> pd.DataFrame:
        rows = []
        for algo, metrics in results.items():
            row = {"algorithm": algo, **metrics}
            rows.append(row)
        return pd.DataFrame(rows).set_index("algorithm") if rows else pd.DataFrame()
