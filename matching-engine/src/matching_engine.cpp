#include "aegis/matching/matching_engine.hpp"

#include <algorithm>

#include "aegis/core/clock.hpp"
#include "aegis/core/metrics.hpp"

namespace aegis {

namespace {
constexpr uint32_t INVALID = ObjectPool<Order, MAX_ORDERS_PER_BOOK>::INVALID_INDEX;
}  // namespace

MatchingEngine::MatchingEngine(Instrument instrument)
    : instrument_(std::move(instrument)), book_(instrument_.id) {}

void MatchingEngine::set_event_callback(EventCallback cb) {
    callback_ = std::move(cb);
}

OrderId MatchingEngine::next_order_id() {
    return order_id_gen_++;
}

TradeId MatchingEngine::next_trade_id() {
    return trade_id_gen_++;
}

SequenceNum MatchingEngine::next_sequence() {
    return ++sequence_;
}

std::vector<OrderEvent> MatchingEngine::emit_event(OrderEvent::Type type, Order& order,
                                                   const std::optional<Trade>& trade) {
    OrderEvent ev;
    ev.type = type;
    ev.order = order;
    ev.trade = trade;
    ev.sequence = next_sequence();
    ev.timestamp = Clock::wall_ns();
    order.sequence = ev.sequence;
    order.updated_at = ev.timestamp;

    std::vector<OrderEvent> events;
    events.push_back(ev);
    if (callback_) callback_(ev);
    return events;
}

std::vector<OrderEvent> MatchingEngine::reject(const OrderRequest& req, RejectReason reason) {
    Order o{};
    o.client_order_id = req.client_order_id;
    o.account_id = req.account_id;
    o.instrument_id = req.instrument_id;
    o.side = req.side;
    o.type = req.type;
    o.price = req.price;
    o.original_qty = req.quantity;
    o.remaining_qty = req.quantity;
    o.stop_price = req.stop_price;
    o.status = OrderStatus::Rejected;
    o.created_at = Clock::wall_ns();

    OrderEvent ev;
    ev.type = OrderEvent::Type::Rejected;
    ev.order = o;
    ev.reject_reason = reason;
    ev.sequence = next_sequence();
    ev.timestamp = o.created_at;

    MetricsRegistry::instance().increment("aegis_orders_rejected_total");
    std::vector<OrderEvent> events{ev};
    if (callback_) callback_(ev);
    return events;
}

bool MatchingEngine::validate_request(const OrderRequest& req, RejectReason& reason) const {
    if (req.quantity <= 0) {
        reason = RejectReason::InvalidQuantity;
        return false;
    }
    if (req.quantity > instrument_.max_order_qty) {
        reason = RejectReason::RiskLimit;
        return false;
    }
    if (req.type == OrderType::Limit || req.type == OrderType::PostOnly ||
        req.type == OrderType::IOC || req.type == OrderType::FOK) {
        if (req.price <= 0) {
            reason = RejectReason::InvalidPrice;
            return false;
        }
        if (req.price < instrument_.min_price || req.price > instrument_.max_price) {
            reason = RejectReason::InvalidPrice;
            return false;
        }
        if (req.price % instrument_.tick_size != 0) {
            reason = RejectReason::InvalidPrice;
            return false;
        }
    }
    if (req.type == OrderType::Stop || req.type == OrderType::StopLimit) {
        if (req.stop_price <= 0) {
            reason = RejectReason::InvalidPrice;
            return false;
        }
    }
    if (req.type == OrderType::StopLimit && req.price <= 0) {
        reason = RejectReason::InvalidPrice;
        return false;
    }
    if (client_order_ids_.count(req.client_order_id)) {
        reason = RejectReason::DuplicateClientOrderId;
        return false;
    }
    return true;
}

bool MatchingEngine::would_cross(Side side, Price price) const {
    if (side == Side::Buy) {
        auto ask = book_.best_ask();
        return ask.has_value() && price >= *ask;
    }
    auto bid = book_.best_bid();
    return bid.has_value() && price <= *bid;
}

Quantity MatchingEngine::available_at_price(Side taker_side, Price limit_price) const {
    return book_.available_liquidity(taker_side, limit_price);
}

bool MatchingEngine::can_fill_fok(Side side, Price limit_price, Quantity qty) const {
    if (side == Side::Buy) {
        if (!limit_price) {
            auto ask = book_.best_ask();
            if (!ask) return false;
            limit_price = *ask;
        }
    } else {
        if (!limit_price) {
            auto bid = book_.best_bid();
            if (!bid) return false;
            limit_price = *bid;
        }
    }
    return available_at_price(side, limit_price) >= qty;
}

void MatchingEngine::match_order(uint32_t taker_idx, std::vector<OrderEvent>& events) {
    auto& taker = book_.order(taker_idx);
    Price last_trade_price = 0;

    while (taker.remaining_qty > 0) {
        std::optional<Price> contra_price;
        if (taker.side == Side::Buy) {
            contra_price = book_.best_ask();
            if (!contra_price) break;
            if (taker.type != OrderType::Market && taker.price < *contra_price) break;
        } else {
            contra_price = book_.best_bid();
            if (!contra_price) break;
            if (taker.type != OrderType::Market && taker.price > *contra_price) break;
        }

        uint32_t maker_idx =
            book_.front_order(taker.side == Side::Buy ? Side::Sell : Side::Buy, *contra_price);
        if (maker_idx == INVALID) break;

        auto& maker = book_.order(maker_idx);
        Quantity fill_qty = std::min(taker.remaining_qty, maker.remaining_qty);
        Price fill_price = maker.price;

        Trade trade;
        trade.trade_id = next_trade_id();
        trade.maker_order_id = maker.order_id;
        trade.taker_order_id = taker.order_id;
        trade.instrument_id = instrument_.id;
        trade.aggressor_side = taker.side;
        trade.price = fill_price;
        trade.quantity = fill_qty;
        trade.sequence = next_sequence();
        trade.timestamp = Clock::wall_ns();
        last_trade_price = fill_price;

        // Update average fill prices
        auto update_avg = [fill_qty, fill_price](Order& o) {
            int64_t total_value = o.avg_fill_price * o.filled_qty + fill_price * fill_qty;
            o.filled_qty += fill_qty;
            o.avg_fill_price = o.filled_qty > 0 ? total_value / o.filled_qty : 0;
            o.remaining_qty -= fill_qty;
        };
        update_avg(taker);
        book_.reduce_qty(maker_idx, fill_qty);
        maker.filled_qty = book_.order(maker_idx).filled_qty;
        maker.remaining_qty = book_.order(maker_idx).remaining_qty;

        if (maker.remaining_qty == 0) {
            maker.status = OrderStatus::Filled;
            book_.remove_from_book(maker_idx);
            auto evs = emit_event(OrderEvent::Type::Fill, maker, trade);
            events.insert(events.end(), evs.begin(), evs.end());
            book_.destroy_order(maker_idx);
        } else {
            maker.status = OrderStatus::PartiallyFilled;
            auto evs = emit_event(OrderEvent::Type::PartialFill, maker, trade);
            events.insert(events.end(), evs.begin(), evs.end());
        }

        auto taker_type = taker.filled_qty == taker.original_qty ? OrderEvent::Type::Fill
                                                                 : OrderEvent::Type::PartialFill;
        taker.status =
            taker.remaining_qty == 0 ? OrderStatus::Filled : OrderStatus::PartiallyFilled;
        auto tev = emit_event(taker_type, taker, trade);
        events.insert(events.end(), tev.begin(), tev.end());

        MetricsRegistry::instance().increment("aegis_trades_total");
    }

    if (last_trade_price > 0) {
        check_stop_triggers(last_trade_price, events);
    }
}

void MatchingEngine::check_stop_triggers(Price last_trade_price, std::vector<OrderEvent>& events) {
    std::vector<uint32_t> triggered;
    for (uint32_t idx : stop_orders_) {
        auto& o = book_.order(idx);
        bool hit = false;
        if (o.side == Side::Buy && last_trade_price >= o.stop_price) hit = true;
        if (o.side == Side::Sell && last_trade_price <= o.stop_price) hit = true;
        if (hit) triggered.push_back(idx);
    }
    for (uint32_t idx : triggered) {
        activate_stop(idx, events);
    }
}

void MatchingEngine::activate_stop(uint32_t stop_idx, std::vector<OrderEvent>& events) {
    auto& o = book_.order(stop_idx);
    o.status = OrderStatus::Triggered;
    auto tev = emit_event(OrderEvent::Type::Triggered, o);
    events.insert(events.end(), tev.begin(), tev.end());

    stop_orders_.erase(std::remove(stop_orders_.begin(), stop_orders_.end(), stop_idx),
                       stop_orders_.end());

    if (o.type == OrderType::Stop) {
        o.type = OrderType::Market;
        o.price = 0;
    } else {
        o.type = OrderType::Limit;
    }
    o.status = OrderStatus::Accepted;
    match_order(stop_idx, events);

    if (o.remaining_qty > 0 && o.type == OrderType::Limit) {
        book_.add_to_book(stop_idx, o.side, o.price);
        auto aev = emit_event(OrderEvent::Type::Accepted, o);
        events.insert(events.end(), aev.begin(), aev.end());
    } else if (o.remaining_qty > 0) {
        o.status = OrderStatus::Cancelled;
        auto cev = emit_event(OrderEvent::Type::Cancelled, o);
        events.insert(events.end(), cev.begin(), cev.end());
        book_.destroy_order(stop_idx);
    } else {
        book_.destroy_order(stop_idx);
    }
}

std::vector<OrderEvent> MatchingEngine::submit_order(const OrderRequest& req) {
    ScopedTimer timer("aegis_order_latency_us");
    MetricsRegistry::instance().increment("aegis_orders_received_total");

    RejectReason reason = RejectReason::None;
    if (!validate_request(req, reason)) {
        return reject(req, reason);
    }

    client_order_ids_.insert(req.client_order_id);

    // Stop orders go to pending queue
    if (req.type == OrderType::Stop || req.type == OrderType::StopLimit) {
        Order o{};
        o.order_id = next_order_id();
        o.client_order_id = req.client_order_id;
        o.account_id = req.account_id;
        o.instrument_id = req.instrument_id;
        o.side = req.side;
        o.type = req.type;
        o.price = req.price;
        o.original_qty = req.quantity;
        o.remaining_qty = req.quantity;
        o.stop_price = req.stop_price;
        o.status = OrderStatus::Accepted;
        o.created_at = Clock::wall_ns();

        uint32_t idx = book_.create_order(o);
        book_.register_order_id(o.order_id, idx);
        stop_orders_.push_back(idx);

        auto events = emit_event(OrderEvent::Type::Accepted, book_.order(idx));
        MetricsRegistry::instance().increment("aegis_orders_accepted_total");
        return events;
    }

    // Post-only: reject if would cross
    if (req.type == OrderType::PostOnly && would_cross(req.side, req.price)) {
        client_order_ids_.erase(req.client_order_id);
        return reject(req, RejectReason::PostOnlyWouldCross);
    }

    // FOK: reject if cannot fully fill
    if (req.type == OrderType::FOK && !can_fill_fok(req.side, req.price, req.quantity)) {
        client_order_ids_.erase(req.client_order_id);
        return reject(req, RejectReason::FOKNotFillable);
    }

    Order o{};
    o.order_id = next_order_id();
    o.client_order_id = req.client_order_id;
    o.account_id = req.account_id;
    o.instrument_id = req.instrument_id;
    o.side = req.side;
    o.type = req.type;
    o.price = req.type == OrderType::Market ? 0 : req.price;
    o.original_qty = req.quantity;
    o.remaining_qty = req.quantity;
    o.status = OrderStatus::Accepted;
    o.created_at = Clock::wall_ns();

    uint32_t idx = book_.create_order(o);
    book_.register_order_id(o.order_id, idx);

    std::vector<OrderEvent> events;
    auto aev = emit_event(OrderEvent::Type::Accepted, book_.order(idx));
    events.insert(events.end(), aev.begin(), aev.end());

    match_order(idx, events);

    auto& taker = book_.order(idx);
    bool is_ioc = req.type == OrderType::IOC || req.type == OrderType::FOK;

    if (taker.remaining_qty > 0) {
        if (is_ioc || req.type == OrderType::Market) {
            taker.status = OrderStatus::Cancelled;
            auto cev = emit_event(OrderEvent::Type::Cancelled, taker);
            events.insert(events.end(), cev.begin(), cev.end());
            book_.destroy_order(idx);
        } else if (req.type == OrderType::PostOnly || req.type == OrderType::Limit) {
            book_.add_to_book(idx, taker.side, taker.price);
        }
    } else {
        book_.destroy_order(idx);
    }

    MetricsRegistry::instance().increment("aegis_orders_accepted_total");
    return events;
}

std::vector<OrderEvent> MatchingEngine::cancel_order(OrderId order_id, AccountId account_id) {
    auto idx_opt = book_.find_by_order_id(order_id);
    if (!idx_opt) {
        OrderRequest dummy{};
        return reject(dummy, RejectReason::OrderNotFound);
    }

    uint32_t idx = *idx_opt;
    auto& o = book_.order(idx);
    if (o.account_id != account_id) {
        OrderRequest dummy{};
        return reject(dummy, RejectReason::OrderNotFound);
    }

    // Remove from stop list if pending
    stop_orders_.erase(std::remove(stop_orders_.begin(), stop_orders_.end(), idx),
                       stop_orders_.end());

    bool on_book = o.status == OrderStatus::Accepted || o.status == OrderStatus::PartiallyFilled;
    if (on_book && o.type != OrderType::Stop && o.type != OrderType::StopLimit) {
        book_.remove_from_book(idx);
    }

    o.status = OrderStatus::Cancelled;
    client_order_ids_.erase(o.client_order_id);
    auto events = emit_event(OrderEvent::Type::Cancelled, o);
    book_.destroy_order(idx);
    MetricsRegistry::instance().increment("aegis_orders_cancelled_total");
    return events;
}

std::vector<OrderEvent> MatchingEngine::modify_order(OrderId order_id, AccountId account_id,
                                                     Price new_price, Quantity new_qty) {
    auto idx_opt = book_.find_by_order_id(order_id);
    if (!idx_opt) {
        OrderRequest dummy{};
        return reject(dummy, RejectReason::OrderNotFound);
    }

    uint32_t idx = *idx_opt;
    auto& o = book_.order(idx);
    if (o.account_id != account_id) {
        OrderRequest dummy{};
        return reject(dummy, RejectReason::OrderNotFound);
    }

    if (new_qty <= 0) {
        OrderRequest dummy{};
        return reject(dummy, RejectReason::InvalidQuantity);
    }

    std::vector<OrderEvent> events;

    // Cancel-replace semantics: remove from book, update, re-add
    bool on_book =
        (o.status == OrderStatus::Accepted || o.status == OrderStatus::PartiallyFilled) &&
        o.type != OrderType::Stop && o.type != OrderType::StopLimit;
    if (on_book) book_.remove_from_book(idx);

    Quantity filled = o.filled_qty;
    o.price = new_price > 0 ? new_price : o.price;
    o.original_qty = filled + new_qty;
    o.remaining_qty = new_qty;
    o.updated_at = Clock::wall_ns();

    auto mev = emit_event(OrderEvent::Type::Modified, o);
    events.insert(events.end(), mev.begin(), mev.end());

    if (on_book) {
        match_order(idx, events);
        auto& updated = book_.order(idx);
        if (updated.remaining_qty > 0) {
            book_.add_to_book(idx, updated.side, updated.price);
        } else {
            book_.destroy_order(idx);
        }
    }

    MetricsRegistry::instance().increment("aegis_orders_modified_total");
    return events;
}

BookSnapshot MatchingEngine::book_snapshot(std::size_t depth) const {
    return book_.snapshot(depth, sequence_);
}

void ExchangeMatching::add_instrument(Instrument instrument) {
    engines_.emplace(instrument.id, MatchingEngine{std::move(instrument)});
}

MatchingEngine* ExchangeMatching::get_engine(InstrumentId id) {
    auto it = engines_.find(id);
    return it != engines_.end() ? &it->second : nullptr;
}

const MatchingEngine* ExchangeMatching::get_engine(InstrumentId id) const {
    auto it = engines_.find(id);
    return it != engines_.end() ? &it->second : nullptr;
}

void ExchangeMatching::for_each_engine(const std::function<void(MatchingEngine&)>& fn) {
    for (auto& [id, engine] : engines_) {
        (void)id;
        fn(engine);
    }
}

}  // namespace aegis
