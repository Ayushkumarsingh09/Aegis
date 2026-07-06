# Aegis Exchange Benchmark Results

Generated from Docker build (Release, GCC 11.4, Ubuntu 22.04).

## Test Suite

```
25/25 tests passed (100%)
Total Test time: ~1.1 sec
```

## Live Metrics (after demo trade)

| Metric | Value |
|--------|-------|
| `aegis_orders_received_total` | 2 |
| `aegis_orders_accepted_total` | 2 |
| `aegis_trades_total` | 1 |
| `aegis_order_latency_us_sum` | ~90 μs |

## Benchmark Targets (Release build)

| Benchmark | Expected |
|-----------|----------|
| Limit Order Insert | ~500K ops/sec |
| Match Trade | ~300K ops/sec |
| Book Snapshot | ~2M ops/sec |
| Order Latency | 1-5 μs |

Run locally:
```bash
cmake -B build -DAEGIS_BUILD_BENCHMARKS=ON
cmake --build build --target aegis_benchmark
./build/benchmark/aegis_benchmark
```
