# Developer Guide

## Prerequisites

- C++20 compiler (GCC 11+, Clang 14+, MSVC 19.30+)
- CMake 3.20+
- OpenSSL development libraries
- Node.js 20+ (dashboard)
- Python 3.8+ (SDK)
- Docker & Docker Compose (deployment)

## Project Structure

```
aegis-exchange/
├── core/                 # Types, memory pool, metrics, clock
├── orderbook/            # Limit order book
├── matching-engine/      # Matching logic
├── risk/                 # Risk engine
├── market-data/          # Publisher, recorder, replay
├── gateway/              # REST API
├── server/               # Main binary
├── benchmark/            # Performance benchmarks
├── tests/                # GoogleTest suite
├── dashboard/            # React frontend
├── sdk/python/           # Python client
├── docs/                 # Documentation
├── docker/               # Container configs
└── scripts/              # Build/deploy scripts
```

## Building

```bash
# Debug build with tests
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DAEGIS_BUILD_TESTS=ON
cmake --build build -j$(nproc)

# Release build
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)

# With sanitizers
cmake -B build -DAEGIS_ENABLE_SANITIZERS=ON
cmake --build build
```

## Running Tests

```bash
cd build && ctest --output-on-failure

# Run specific test
./build/tests/aegis_tests --gtest_filter=MatchingEngineTest.*
```

## Code Style

- Google C++ style with 4-space indent
- Format: `clang-format -i **/*.{cpp,hpp}`
- Lint: `clang-tidy` (see `.clang-tidy`)

## Adding a New Instrument

Instruments are configured in `server/src/main.cpp`:

```cpp
Instrument new_inst;
new_inst.id = 3;
new_inst.symbol = "SOL-USD";
new_inst.tick_size = double_to_price(0.01);
new_inst.max_order_qty = 1000000;
matching.add_instrument(new_inst);
```

## Adding Order Types

1. Add enum value to `OrderType` in `core/include/aegis/core/types.hpp`
2. Implement logic in `MatchingEngine::submit_order()` 
3. Add API parsing in `gateway/src/api_server.cpp`
4. Add tests in `tests/unit/test_matching_engine.cpp`

## Dashboard Development

```bash
cd dashboard
npm install
npm run dev    # http://localhost:4000 with API proxy to :9080
```

## Benchmarking

```bash
cmake -B build -DAEGIS_BUILD_BENCHMARKS=ON
cmake --build build --target aegis_benchmark
./build/benchmark/aegis_benchmark --benchmark_format=json > docs/benchmark-results.json
```
