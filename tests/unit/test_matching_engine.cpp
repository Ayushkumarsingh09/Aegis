#include <gtest/gtest.h>
#include "aegis/matching/matching_engine.hpp"
#include "aegis/core/types.hpp"

using namespace aegis;

class MatchingEngineTest : public ::testing::Test {
protected:
    Instrument make_instrument() {
        Instrument inst;
        inst.id = 1;
        inst.symbol = "TEST-USD";
        inst.tick_size = double_to_price(0.01);
        inst.lot_size = 1;
        inst.min_price = double_to_price(0.01);
        inst.max_price = double_to_price(1000000.0);
        inst.max_order_qty = 1000000;
        inst.active = true;
        return inst;
    }

    OrderRequest make_limit(Side side, double price, Quantity qty, ClientOrderId coid) {
        OrderRequest req;
        req.client_order_id = coid;
        req.account_id = 1;
        req.instrument_id = 1;
        req.side = side;
        req.type = OrderType::Limit;
        req.price = double_to_price(price);
        req.quantity = qty;
        return req;
    }
};

TEST_F(MatchingEngineTest, LimitOrderRestsOnBook) {
    MatchingEngine engine(make_instrument());
    auto events = engine.submit_order(make_limit(Side::Buy, 100.0, 10, 1));
    ASSERT_FALSE(events.empty());
    EXPECT_EQ(events[0].order.status, OrderStatus::Accepted);

    auto snap = engine.book_snapshot();
    EXPECT_EQ(snap.bids.size(), 1);
    EXPECT_EQ(snap.bids[0].quantity, 10);
}

TEST_F(MatchingEngineTest, LimitOrdersMatch) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 10, 1));
    auto events = engine.submit_order(make_limit(Side::Buy, 100.0, 10, 2));

    bool has_fill = false;
    for (const auto& ev : events) {
        if (ev.type == OrderEvent::Type::Fill) has_fill = true;
    }
    EXPECT_TRUE(has_fill);

    auto snap = engine.book_snapshot();
    EXPECT_TRUE(snap.bids.empty());
    EXPECT_TRUE(snap.asks.empty());
}

TEST_F(MatchingEngineTest, PartialFill) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 10, 1));
    auto events = engine.submit_order(make_limit(Side::Buy, 100.0, 5, 2));

    bool has_partial = false;
    for (const auto& ev : events) {
        if (ev.type == OrderEvent::Type::PartialFill) has_partial = true;
    }
    EXPECT_TRUE(has_partial);

    auto snap = engine.book_snapshot();
    EXPECT_EQ(snap.asks.size(), 1);
    EXPECT_EQ(snap.asks[0].quantity, 5);
}

TEST_F(MatchingEngineTest, MarketOrder) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 10, 1));

    OrderRequest mkt;
    mkt.client_order_id = 2;
    mkt.account_id = 1;
    mkt.instrument_id = 1;
    mkt.side = Side::Buy;
    mkt.type = OrderType::Market;
    mkt.quantity = 10;

    auto events = engine.submit_order(mkt);
    bool filled = false;
    for (const auto& ev : events) {
        if (ev.order.status == OrderStatus::Filled) filled = true;
    }
    EXPECT_TRUE(filled);
}

TEST_F(MatchingEngineTest, IOCPartialCancel) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 5, 1));

    OrderRequest ioc;
    ioc.client_order_id = 2;
    ioc.account_id = 1;
    ioc.instrument_id = 1;
    ioc.side = Side::Buy;
    ioc.type = OrderType::IOC;
    ioc.price = double_to_price(100.0);
    ioc.quantity = 10;

    auto events = engine.submit_order(ioc);
    bool has_cancel = false;
    for (const auto& ev : events) {
        if (ev.type == OrderEvent::Type::Cancelled) has_cancel = true;
    }
    EXPECT_TRUE(has_cancel);
}

TEST_F(MatchingEngineTest, FOKReject) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 5, 1));

    OrderRequest fok;
    fok.client_order_id = 2;
    fok.account_id = 1;
    fok.instrument_id = 1;
    fok.side = Side::Buy;
    fok.type = OrderType::FOK;
    fok.price = double_to_price(100.0);
    fok.quantity = 10;

    auto events = engine.submit_order(fok);
    EXPECT_EQ(events[0].type, OrderEvent::Type::Rejected);
}

TEST_F(MatchingEngineTest, PostOnlyReject) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 10, 1));

    OrderRequest po;
    po.client_order_id = 2;
    po.account_id = 1;
    po.instrument_id = 1;
    po.side = Side::Buy;
    po.type = OrderType::PostOnly;
    po.price = double_to_price(100.0);
    po.quantity = 5;

    auto events = engine.submit_order(po);
    EXPECT_EQ(events[0].type, OrderEvent::Type::Rejected);
}

TEST_F(MatchingEngineTest, CancelOrder) {
    MatchingEngine engine(make_instrument());
    auto events = engine.submit_order(make_limit(Side::Buy, 100.0, 10, 1));
    OrderId oid = events[0].order.order_id;

    auto cancel_events = engine.cancel_order(oid, 1);
    EXPECT_EQ(cancel_events[0].order.status, OrderStatus::Cancelled);
    EXPECT_TRUE(engine.book_snapshot().bids.empty());
}

TEST_F(MatchingEngineTest, ModifyOrder) {
    MatchingEngine engine(make_instrument());
    auto events = engine.submit_order(make_limit(Side::Buy, 100.0, 10, 1));
    OrderId oid = events[0].order.order_id;

    auto mod_events = engine.modify_order(oid, 1, double_to_price(99.0), 20);
    EXPECT_FALSE(mod_events.empty());

    auto snap = engine.book_snapshot();
    EXPECT_EQ(snap.bids.size(), 1);
    EXPECT_EQ(snap.bids[0].price, double_to_price(99.0));
    EXPECT_EQ(snap.bids[0].quantity, 20);
}

TEST_F(MatchingEngineTest, StopOrderTrigger) {
    MatchingEngine engine(make_instrument());
    engine.submit_order(make_limit(Side::Sell, 100.0, 100, 1));

    OrderRequest stop;
    stop.client_order_id = 2;
    stop.account_id = 1;
    stop.instrument_id = 1;
    stop.side = Side::Buy;
    stop.type = OrderType::Stop;
    stop.stop_price = double_to_price(100.0);
    stop.quantity = 10;

    engine.submit_order(stop);

    OrderRequest trigger;
    trigger.client_order_id = 3;
    trigger.account_id = 1;
    trigger.instrument_id = 1;
    trigger.side = Side::Buy;
    trigger.type = OrderType::Limit;
    trigger.price = double_to_price(100.0);
    trigger.quantity = 5;

    auto events = engine.submit_order(trigger);
    bool triggered = false;
    for (const auto& ev : events) {
        if (ev.type == OrderEvent::Type::Triggered) triggered = true;
    }
    EXPECT_TRUE(triggered);
}
