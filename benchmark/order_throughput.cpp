#include <benchmark/benchmark.h>

#include "aegis/matching/matching_engine.hpp"

using namespace aegis;

static Instrument make_inst() {
    Instrument inst;
    inst.id = 1;
    inst.symbol = "BENCH";
    inst.tick_size = double_to_price(0.01);
    inst.max_order_qty = 10000000;
    return inst;
}

static OrderRequest make_req(ClientOrderId id, Side side, double price, Quantity qty) {
    OrderRequest req;
    req.client_order_id = id;
    req.account_id = 1;
    req.instrument_id = 1;
    req.side = side;
    req.type = OrderType::Limit;
    req.price = double_to_price(price);
    req.quantity = qty;
    return req;
}

static void BM_LimitOrderInsert(benchmark::State& state) {
    MatchingEngine engine(make_inst());
    ClientOrderId id = 1;
    for (auto _ : state) {
        engine.submit_order(make_req(id++, Side::Buy, 100.0 - (id % 50), 10));
    }
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_LimitOrderInsert);

static void BM_MatchTrade(benchmark::State& state) {
    for (auto _ : state) {
        state.PauseTiming();
        MatchingEngine engine(make_inst());
        engine.submit_order(make_req(1, Side::Sell, 100.0, 1000));
        state.ResumeTiming();

        engine.submit_order(make_req(2, Side::Buy, 100.0, 1000));
    }
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_MatchTrade);

static void BM_BookSnapshot(benchmark::State& state) {
    MatchingEngine engine(make_inst());
    for (int i = 0; i < 100; ++i) {
        engine.submit_order(make_req(i + 1, Side::Buy, 99.0 - i * 0.01, 10));
        engine.submit_order(make_req(i + 100, Side::Sell, 101.0 + i * 0.01, 10));
    }
    for (auto _ : state) {
        auto snap = engine.book_snapshot(20);
        benchmark::DoNotOptimize(snap);
    }
}
BENCHMARK(BM_BookSnapshot);

static void BM_CancelOrder(benchmark::State& state) {
    MatchingEngine engine(make_inst());
    std::vector<OrderId> order_ids;
    for (int i = 0; i < 1000; ++i) {
        auto ev = engine.submit_order(make_req(i + 1, Side::Buy, 50.0, 10));
        order_ids.push_back(ev[0].order.order_id);
    }
    size_t idx = 0;
    for (auto _ : state) {
        engine.cancel_order(order_ids[idx % order_ids.size()], 1);
        ++idx;
    }
}
BENCHMARK(BM_CancelOrder);
