#include "aegis/orderbook/order_book.hpp"

#include "aegis/core/clock.hpp"

namespace aegis {

namespace {
constexpr uint32_t INVALID = ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX;
}  // namespace

OrderBook::OrderBook(InstrumentId instrument_id)
    : instrument_id_(instrument_id), nodes_(MAX_ORDERS_PER_BOOK) {}

std::optional<Price> OrderBook::best_bid() const {
    if (bids_.empty()) return std::nullopt;
    return bids_.begin()->first;
}

std::optional<Price> OrderBook::best_ask() const {
    if (asks_.empty()) return std::nullopt;
    return asks_.begin()->first;
}

Quantity OrderBook::bid_qty_at(Price price) const {
    auto it = bids_.find(price);
    return it != bids_.end() ? it->second.total_qty : 0;
}

Quantity OrderBook::ask_qty_at(Price price) const {
    auto it = asks_.find(price);
    return it != asks_.end() ? it->second.total_qty : 0;
}

uint32_t OrderBook::create_order(const Order& o) {
    uint32_t idx = pool_.allocate();
    pool_.get(idx) = o;
    pool_.get(idx).pool_index = idx;
    nodes_[idx] = OrderNode{idx, INVALID, INVALID};
    return idx;
}

void OrderBook::destroy_order(uint32_t idx) {
    unregister_order_id(pool_.get(idx).order_id);
    pool_.deallocate(idx);
    nodes_[idx] = OrderNode{};
}

std::optional<uint32_t> OrderBook::find_by_order_id(OrderId id) const {
    auto it = order_id_map_.find(id);
    if (it == order_id_map_.end()) return std::nullopt;
    return it->second;
}

void OrderBook::register_order_id(OrderId id, uint32_t pool_index) {
    order_id_map_[id] = pool_index;
}

void OrderBook::unregister_order_id(OrderId id) {
    order_id_map_.erase(id);
}

void OrderBook::link_at_tail(PriceLevel& level, uint32_t idx) {
    nodes_[idx].prev = level.tail;
    nodes_[idx].next = INVALID;
    if (level.tail != INVALID) {
        nodes_[level.tail].next = idx;
    } else {
        level.head = idx;
    }
    level.tail = idx;
    ++level.order_count;
}

void OrderBook::unlink(PriceLevel& level, uint32_t idx) {
    uint32_t prev = nodes_[idx].prev;
    uint32_t next = nodes_[idx].next;
    if (prev != INVALID) {
        nodes_[prev].next = next;
    } else {
        level.head = next;
    }
    if (next != INVALID) {
        nodes_[next].prev = prev;
    } else {
        level.tail = prev;
    }
    nodes_[idx].prev = INVALID;
    nodes_[idx].next = INVALID;
    --level.order_count;
}

void OrderBook::add_to_book(uint32_t pool_index, Side side, Price price) {
    if (side == Side::Buy) {
        auto& level = bids_[price];
        level.price = price;
        link_at_tail(level, pool_index);
        level.total_qty += pool_.get(pool_index).remaining_qty;
    } else {
        auto& level = asks_[price];
        level.price = price;
        link_at_tail(level, pool_index);
        level.total_qty += pool_.get(pool_index).remaining_qty;
    }
}

void OrderBook::remove_from_book(uint32_t pool_index) {
    auto& o = pool_.get(pool_index);
    if (o.side == Side::Buy) {
        auto it = bids_.find(o.price);
        if (it == bids_.end()) return;
        it->second.total_qty -= o.remaining_qty;
        unlink(it->second, pool_index);
        if (it->second.order_count == 0) bids_.erase(it);
    } else {
        auto it = asks_.find(o.price);
        if (it == asks_.end()) return;
        it->second.total_qty -= o.remaining_qty;
        unlink(it->second, pool_index);
        if (it->second.order_count == 0) asks_.erase(it);
    }
}

void OrderBook::reduce_qty(uint32_t pool_index, Quantity fill_qty) {
    auto& o = pool_.get(pool_index);
    o.remaining_qty -= fill_qty;
    o.filled_qty += fill_qty;

    if (o.side == Side::Buy) {
        auto it = bids_.find(o.price);
        if (it != bids_.end()) it->second.total_qty -= fill_qty;
    } else {
        auto it = asks_.find(o.price);
        if (it != asks_.end()) it->second.total_qty -= fill_qty;
    }
}

uint32_t OrderBook::front_order(Side side, Price price) const {
    if (side == Side::Buy) {
        auto it = bids_.find(price);
        return it != bids_.end() ? it->second.head : INVALID;
    }
    auto it = asks_.find(price);
    return it != asks_.end() ? it->second.head : INVALID;
}

bool OrderBook::empty_level(Side side, Price price) const {
    if (side == Side::Buy) {
        auto it = bids_.find(price);
        return it == bids_.end() || it->second.order_count == 0;
    }
    auto it = asks_.find(price);
    return it == asks_.end() || it->second.order_count == 0;
}

BookSnapshot OrderBook::snapshot(std::size_t depth, SequenceNum seq) const {
    BookSnapshot snap;
    snap.instrument_id = instrument_id_;
    snap.sequence = seq;
    snap.timestamp = Clock::wall_ns();

    std::size_t n = 0;
    for (const auto& [price, level] : bids_) {
        if (n++ >= depth) break;
        snap.bids.push_back({price, level.total_qty, level.order_count});
    }
    n = 0;
    for (const auto& [price, level] : asks_) {
        if (n++ >= depth) break;
        snap.asks.push_back({price, level.total_qty, level.order_count});
    }
    return snap;
}

Quantity OrderBook::available_liquidity(Side taker_side, Price limit_price) const {
    Quantity available = 0;
    if (taker_side == Side::Buy) {
        for (const auto& [price, level] : asks_) {
            if (price > limit_price) break;
            available += level.total_qty;
        }
    } else {
        for (const auto& [price, level] : bids_) {
            if (price < limit_price) break;
            available += level.total_qty;
        }
    }
    return available;
}

}  // namespace aegis
