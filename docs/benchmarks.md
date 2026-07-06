# Benchmarks

## Exchange (C++)

Run the Google Benchmark suite:

```bash
cmake -B build -DAEGIS_BUILD_BENCHMARKS=ON
cmake --build build --target aegis_benchmark
./build/benchmark/aegis_benchmark
```

### Expected Performance (Release build, modern CPU)

| Benchmark | Target |
|-----------|--------|
| Order insert latency | < 1 µs |
| Order match latency | < 2 µs |
| Throughput | > 100K orders/sec |
| Order book depth query | < 500 ns |

## Quant Platform (Python)

```bash
pytest execution/tests options/tests market-maker/tests analytics/tests aegis-quant/tests -v
# 45 tests, ~10s
```

### Backtest Performance

| Dataset | Bars | Strategy | Time |
|---------|------|----------|------|
| BTC-USD | 500 | Mean Reversion | < 1s |
| BTC-USD | 500 | Momentum | < 1s |

### ML Training

| Model | Features | Samples | CV Time |
|-------|----------|---------|---------|
| Random Forest | 30+ | 500 | ~2s |
| XGBoost | 30+ | 500 | ~3s |

## Reproducibility

All benchmarks use fixed random seeds where applicable:
- Execution simulator: `seed=42`
- Monte Carlo options: `seed=42`
- Market maker simulator: `seed=42`

## Reports

Generate benchmark report:

```bash
./build/benchmark/aegis_benchmark --benchmark_format=json > docs/benchmark-report.json
```
