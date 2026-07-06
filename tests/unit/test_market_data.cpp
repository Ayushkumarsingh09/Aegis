#include <cstdio>
#include <gtest/gtest.h>
#include "aegis/market_data/publisher.hpp"
#include "aegis/core/types.hpp"

using namespace aegis;

TEST(MarketDataTest, PublishAndSubscribe) {
    MarketDataPublisher pub;
    int count = 0;
    pub.subscribe([&](const MarketDataMessage& msg) {
        ++count;
        EXPECT_FALSE(msg.payload.empty());
    });

    Trade t;
    t.trade_id = 1;
    t.instrument_id = 1;
    t.price = double_to_price(100.0);
    t.quantity = 10;
    t.aggressor_side = Side::Buy;
    t.sequence = 1;
    t.timestamp = 12345;

    pub.publish_trade(t);
    EXPECT_EQ(count, 1);
    EXPECT_EQ(pub.subscriber_count(), 1);
}

TEST(MarketDataTest, BookSnapshot) {
    MarketDataPublisher pub;
    BookSnapshot snap;
    snap.instrument_id = 1;
    snap.sequence = 1;
    snap.bids.push_back({double_to_price(99.0), 100, 1});
    snap.asks.push_back({double_to_price(101.0), 50, 1});

    pub.publish_snapshot(snap);
    auto recent = pub.recent_messages(10);
    EXPECT_EQ(recent.size(), 1);
    EXPECT_EQ(recent[0].type, MarketDataMsgType::BookSnapshot);
}

TEST(MarketDataTest, RecorderAndReplay) {
    std::string path = "test_market_data.log";
    {
        MarketDataRecorder recorder(path);
        MarketDataMessage msg;
        msg.type = MarketDataMsgType::Trade;
        msg.instrument_id = 1;
        msg.sequence = 1;
        msg.timestamp = 1000;
        msg.payload = R"({"type":"trade"})";
        recorder.record(msg);
        recorder.flush();
        EXPECT_EQ(recorder.record_count(), 1);
    }

    ReplayEngine replay(path);
    ASSERT_TRUE(replay.load());
    EXPECT_EQ(replay.message_count(), 1);

    int replayed = 0;
    replay.replay([&](const MarketDataMessage& msg) {
        ++replayed;
        EXPECT_EQ(msg.timestamp, 1000);
    }, 0);
    EXPECT_EQ(replayed, 1);

    std::remove(path.c_str());
}
