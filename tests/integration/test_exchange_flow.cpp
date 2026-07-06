#include <gtest/gtest.h>

#include <unordered_set>

#include "aegis/market_data/publisher.hpp"
#include "aegis/matching/matching_engine.hpp"
#include "aegis/risk/risk_engine.hpp"

using namespace aegis;

TEST(ExchangeIntegrationTest, FullTradingFlow) {
    Instrument inst;
    inst.id = 1;
    inst.symbol = "BTC-USD";
    inst.tick_size = double_to_price(0.01);
    inst.max_order_qty = 1000000;

    MatchingEngine engine(inst);
    RiskEngine risk;
    MarketDataPublisher publisher;

    int trade_count = 0;
    std::unordered_set<TradeId> seen_trades;
    engine.set_event_callback([&](const OrderEvent& ev) {
        publisher.publish_order_event(ev);
        if (ev.trade) {
            if (seen_trades.insert(ev.trade->trade_id).second) {
                publisher.publish_trade(*ev.trade);
                ++trade_count;
            }
            risk.on_fill(ev.order.account_id, ev.order.side, ev.trade->price, ev.trade->quantity);
        }
    });

    // Seed liquidity
    OrderRequest sell;
    sell.client_order_id = 1;
    sell.account_id = 1;
    sell.instrument_id = 1;
    sell.side = Side::Sell;
    sell.type = OrderType::Limit;
    sell.price = double_to_price(50000.0);
    sell.quantity = 100;
    engine.submit_order(sell);

    publisher.publish_snapshot(engine.book_snapshot());

    // Buy order matches
    OrderRequest buy;
    buy.client_order_id = 2;
    buy.account_id = 2;
    buy.instrument_id = 1;
    buy.side = Side::Buy;
    buy.type = OrderType::Limit;
    buy.price = double_to_price(50000.0);
    buy.quantity = 50;

    auto risk_check = risk.validate_order(buy, double_to_price(50000.0));
    ASSERT_TRUE(risk_check.approved);

    engine.submit_order(buy);
    publisher.publish_snapshot(engine.book_snapshot());

    EXPECT_EQ(trade_count, 1);

    auto snap = engine.book_snapshot();
    EXPECT_EQ(snap.asks.size(), 1);
    EXPECT_EQ(snap.asks[0].quantity, 50);

    auto acct1 = risk.account_state(1);
    auto acct2 = risk.account_state(2);
    EXPECT_EQ(acct1.net_position, -50);
    EXPECT_EQ(acct2.net_position, 50);

    auto recent = publisher.recent_messages(100);
    EXPECT_GT(recent.size(), 0);
}

TEST(ExchangeIntegrationTest, MultiLevelMatching) {
    Instrument inst;
    inst.id = 1;
    inst.symbol = "ETH-USD";
    inst.tick_size = double_to_price(0.01);
    inst.max_order_qty = 1000000;

    MatchingEngine engine(inst);

    for (int i = 0; i < 5; ++i) {
        OrderRequest sell;
        sell.client_order_id = i + 1;
        sell.account_id = 1;
        sell.instrument_id = 1;
        sell.side = Side::Sell;
        sell.type = OrderType::Limit;
        sell.price = double_to_price(3000.0 + i);
        sell.quantity = 10;
        engine.submit_order(sell);
    }

    OrderRequest buy;
    buy.client_order_id = 100;
    buy.account_id = 2;
    buy.instrument_id = 1;
    buy.side = Side::Buy;
    buy.type = OrderType::Limit;
    buy.price = double_to_price(3004.0);
    buy.quantity = 35;

    auto events = engine.submit_order(buy);

    int fills = 0;
    for (const auto& ev : events) {
        if (ev.type == OrderEvent::Type::Fill || ev.type == OrderEvent::Type::PartialFill) {
            if (ev.trade) ++fills;
        }
    }
    EXPECT_GE(fills, 3);

    auto snap = engine.book_snapshot();
    EXPECT_GE(snap.asks.size(), 1);
}
