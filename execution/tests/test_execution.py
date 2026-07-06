from datetime import datetime, timedelta

import pandas as pd
import pytest

from aegis_execution.algorithms import (
    ArrivalPriceExecutor,
    IcebergExecutor,
    OrderSide,
    POVExecutor,
    TWAPExecutor,
    VWAPExecutor,
    implementation_shortfall,
)
from aegis_execution.simulator import ExecutionSimulator, SimConfig
from aegis_execution.slippage import LinearImpactModel, SquareRootImpactModel
from aegis_execution.tca import TransactionCostAnalyzer
from aegis_execution.routing import SmartRouter, VenueQuote, Venue


@pytest.fixture
def market_data():
    n = 50
    return pd.DataFrame({
        "timestamp": [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)],
        "close": 100 + pd.Series(range(n)) * 0.1,
        "volume": [1000 + i * 10 for i in range(n)],
    })


def test_twap_schedule():
    start = datetime(2024, 1, 1)
    end = start + timedelta(hours=1)
    sched = TWAPExecutor(n_slices=5).schedule(100, OrderSide.BUY, "TEST", start, end)
    assert len(sched.children) == 5
    assert abs(sum(c.quantity for c in sched.children) - 100) < 1e-6


def test_vwap_schedule(market_data):
    start = datetime(2024, 1, 1)
    end = start + timedelta(hours=10)
    sched = VWAPExecutor(n_buckets=5).schedule(100, OrderSide.SELL, "TEST", start, end, market_data)
    assert len(sched.children) == 5
    assert sched.benchmark == "vwap"


def test_pov_schedule(market_data):
    start = datetime(2024, 1, 1)
    end = start + timedelta(hours=5)
    sched = POVExecutor(participation_rate=0.2, n_slices=5).schedule(50, OrderSide.BUY, "TEST", start, end, market_data)
    assert len(sched.children) >= 1


def test_iceberg_schedule():
    start = datetime(2024, 1, 1)
    end = start + timedelta(minutes=10)
    sched = IcebergExecutor(display_pct=0.2, interval_sec=60).schedule(100, OrderSide.BUY, "TEST", start, end)
    assert all(c.display_qty is not None for c in sched.children)


def test_arrival_price_schedule():
    start = datetime(2024, 1, 1)
    end = start + timedelta(hours=2)
    sched = ArrivalPriceExecutor(urgency=0.8).schedule(100, OrderSide.BUY, "TEST", start, end)
    assert sched.children[0].quantity > sched.children[-1].quantity


def test_execution_simulator(market_data):
    start = datetime(2024, 1, 1)
    end = start + timedelta(hours=5)
    sched = TWAPExecutor(n_slices=5).schedule(100, OrderSide.BUY, "TEST", start, end)
    result = ExecutionSimulator(SimConfig(seed=42)).run(sched, market_data)
    assert result.total_qty > 0
    assert "fill_rate" in result.metrics


def test_slippage_models():
    linear = LinearImpactModel()
    sqrt = SquareRootImpactModel()
    assert linear.estimate(100, 10000, 0.02, 0.0001) > 0
    assert sqrt.estimate(100, 10000, 0.02, 0.0001) > 0


def test_smart_router():
    router = SmartRouter()
    quotes = [
        VenueQuote(Venue.AEGIS, 99.9, 100.1, 50, 50, latency_ms=1, fee_bps=1),
        VenueQuote(Venue.BINANCE, 99.95, 100.05, 100, 100, latency_ms=5, fee_bps=0.5),
    ]
    decisions = router.route(10, "buy", quotes)
    assert sum(d.quantity for d in decisions) == 10


def test_tca():
    fills = pd.DataFrame({"price": [100, 101], "quantity": [50, 50], "commission": [0.5, 0.5]})
    tca = TransactionCostAnalyzer()
    result = tca.analyze(fills, {"arrival": 100.0, "vwap": 100.5}, "buy")
    assert "vs_arrival_bps" in result
