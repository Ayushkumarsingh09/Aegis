#include <benchmark/benchmark.h>
#include "aegis/matching/matching_engine.hpp"
#include "aegis/risk/risk_engine.hpp"
#include "aegis/core/clock.hpp"

using namespace aegis;

static void BM_OrderLatency(benchmark::State& state) {
    Instrument inst;
    inst.id = 1;
    inst.symbol = "LAT";
    inst.tick_size = double_to_price(0.01);
    inst.max_order_qty = 10000000;

    MatchingEngine engine(inst);
    engine.submit_order([] {
        OrderRequest r;
        r.client_order_id = 0;
        r.account_id = 1;
        r.instrument_id = 1;
        r.side = Side::Sell;
        r.type = OrderType::Limit;
        r.price = double_to_price(100.0);
        r.quantity = 1000000;
        return r;
    }());

    ClientOrderId id = 1;
    for (auto _ : state) {
        OrderRequest req;
        req.client_order_id = id++;
        req.account_id = 1;
        req.instrument_id = 1;
        req.side = Side::Buy;
        req.type = OrderType::Limit;
        req.price = double_to_price(100.0);
        req.quantity = 1;
        auto events = engine.submit_order(req);
        benchmark::DoNotOptimize(events);
    }
}
BENCHMARK(BM_OrderLatency)->Unit(benchmark::kNanosecond);

static void BM_RiskValidation(benchmark::State& state) {
    RiskEngine risk;
    OrderRequest req;
    req.account_id = 1;
    req.quantity = 100;
    req.side = Side::Buy;
    req.price = double_to_price(100.0);

    for (auto _ : state) {
        auto result = risk.validate_order(req, double_to_price(100.0));
        benchmark::DoNotOptimize(result);
    }
}
BENCHMARK(BM_RiskValidation)->Unit(benchmark::kNanosecond);
