#include <gtest/gtest.h>
#include "aegis/orderbook/order_book.hpp"
#include "aegis/core/types.hpp"

using namespace aegis;

TEST(OrderBookTest, EmptyBook) {
    OrderBook book(1);
    EXPECT_FALSE(book.best_bid().has_value());
    EXPECT_FALSE(book.best_ask().has_value());
    EXPECT_EQ(book.order_count(), 0);
}

TEST(OrderBookTest, AddBidAndAsk) {
    OrderBook book(1);
    Order bid{};
    bid.order_id = 1;
    bid.side = Side::Buy;
    bid.price = double_to_price(100.0);
    bid.remaining_qty = 10;
    bid.original_qty = 10;

    uint32_t idx = book.create_order(bid);
    book.add_to_book(idx, Side::Buy, bid.price);

    EXPECT_TRUE(book.best_bid().has_value());
    EXPECT_EQ(*book.best_bid(), bid.price);
    EXPECT_EQ(book.bid_qty_at(bid.price), 10);

    Order ask{};
    ask.order_id = 2;
    ask.side = Side::Sell;
    ask.price = double_to_price(101.0);
    ask.remaining_qty = 5;
    ask.original_qty = 5;

    uint32_t idx2 = book.create_order(ask);
    book.add_to_book(idx2, Side::Sell, ask.price);

    EXPECT_TRUE(book.best_ask().has_value());
    EXPECT_EQ(*book.best_ask(), ask.price);
}

TEST(OrderBookTest, PriceTimePriority) {
    OrderBook book(1);
    Price p = double_to_price(100.0);

    for (int i = 0; i < 3; ++i) {
        Order o{};
        o.order_id = i + 1;
        o.side = Side::Buy;
        o.price = p;
        o.remaining_qty = 10;
        o.original_qty = 10;
        uint32_t idx = book.create_order(o);
        book.add_to_book(idx, Side::Buy, p);
    }

    EXPECT_EQ(book.bid_qty_at(p), 30);
    auto snap = book.snapshot(5, 1);
    EXPECT_EQ(snap.bids.size(), 1);
    EXPECT_EQ(snap.bids[0].quantity, 30);
    EXPECT_EQ(snap.bids[0].order_count, 3);
}

TEST(OrderBookTest, RemoveOrder) {
    OrderBook book(1);
    Order o{};
    o.order_id = 1;
    o.side = Side::Buy;
    o.price = double_to_price(50.0);
    o.remaining_qty = 100;
    o.original_qty = 100;

    uint32_t idx = book.create_order(o);
    book.register_order_id(1, idx);
    book.add_to_book(idx, Side::Buy, o.price);
    EXPECT_EQ(book.order_count(), 1);

    book.remove_from_book(idx);
    book.destroy_order(idx);
    EXPECT_FALSE(book.best_bid().has_value());
}

TEST(OrderBookTest, SnapshotDepth) {
    OrderBook book(1);
    for (int i = 1; i <= 5; ++i) {
        Order o{};
        o.order_id = i;
        o.side = Side::Buy;
        o.price = double_to_price(100.0 - i);
        o.remaining_qty = i * 10;
        o.original_qty = i * 10;
        uint32_t idx = book.create_order(o);
        book.add_to_book(idx, Side::Buy, o.price);
    }
    auto snap = book.snapshot(3, 1);
    EXPECT_EQ(snap.bids.size(), 3);
}
