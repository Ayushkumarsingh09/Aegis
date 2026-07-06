#pragma once

#include "aegis/core/memory_pool.hpp"
#include "aegis/core/types.hpp"

#include <map>
#include <unordered_map>
#include <vector>

namespace aegis {

static constexpr std::size_t MAX_ORDERS_PER_BOOK = 1'000'000;

/// Intrusive doubly-linked list node for price-time FIFO within a level.
struct OrderNode {
    uint32_t pool_index{ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX};
    uint32_t prev{ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX};
    uint32_t next{ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX};
};

/// Aggregated quantity at a single price level.
struct PriceLevel {
    Price price{0};
    Quantity total_qty{0};
    uint32_t order_count{0};
    uint32_t head{ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX};
    uint32_t tail{ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX};
};

/// Cache-friendly limit order book with price-time priority.
class OrderBook {
public:
    explicit OrderBook(InstrumentId instrument_id);

    [[nodiscard]] InstrumentId instrument_id() const { return instrument_id_; }

  [[nodiscard]] std::optional<Price> best_bid() const;
  [[nodiscard]] std::optional<Price> best_ask() const;
  [[nodiscard]] Quantity bid_qty_at(Price price) const;
  [[nodiscard]] Quantity ask_qty_at(Price price) const;

    void add_to_book(uint32_t pool_index, Side side, Price price);
    void remove_from_book(uint32_t pool_index);
    void reduce_qty(uint32_t pool_index, Quantity fill_qty);

    [[nodiscard]] uint32_t front_order(Side side, Price price) const;
    [[nodiscard]] bool empty_level(Side side, Price price) const;

    [[nodiscard]] BookSnapshot snapshot(std::size_t depth, SequenceNum seq) const;

    Order& order(uint32_t idx) { return pool_.get(idx); }
    const Order& order(uint32_t idx) const { return pool_.get(idx); }

    uint32_t create_order(const Order& o);
    void destroy_order(uint32_t idx);

    [[nodiscard]] std::optional<uint32_t> find_by_order_id(OrderId id) const;
    void register_order_id(OrderId id, uint32_t pool_index);
    void unregister_order_id(OrderId id);

    [[nodiscard]] std::size_t order_count() const { return pool_.allocated(); }
    [[nodiscard]] std::size_t bid_levels() const { return bids_.size(); }
    [[nodiscard]] std::size_t ask_levels() const { return asks_.size(); }

    /// Total contra-side quantity available up to limit_price (inclusive for bids/asks).
    [[nodiscard]] Quantity available_liquidity(Side taker_side, Price limit_price) const;

private:
    using BidMap = std::map<Price, PriceLevel, std::greater<Price>>;
    using AskMap = std::map<Price, PriceLevel, std::less<Price>>;

    void link_at_tail(PriceLevel& level, uint32_t idx);
    void unlink(PriceLevel& level, uint32_t idx);

    InstrumentId instrument_id_;
    ObjectPool<Order, MAX_ORDERS_PER_BOOK> pool_;
    std::vector<OrderNode> nodes_;
    BidMap bids_;
    AskMap asks_;
    std::unordered_map<OrderId, uint32_t> order_id_map_;
};

}  // namespace aegis
