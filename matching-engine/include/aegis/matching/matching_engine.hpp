#pragma once

#include "aegis/core/types.hpp"
#include "aegis/orderbook/order_book.hpp"

#include <functional>
#include <mutex>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace aegis {

using EventCallback = std::function<void(const OrderEvent&)>;

/// Single-instrument matching engine with full order type support.
class MatchingEngine {
public:
    explicit MatchingEngine(Instrument instrument);

    void set_event_callback(EventCallback cb);

    std::vector<OrderEvent> submit_order(const OrderRequest& req);
    std::vector<OrderEvent> cancel_order(OrderId order_id, AccountId account_id);
    std::vector<OrderEvent> modify_order(OrderId order_id, AccountId account_id, Price new_price,
                                         Quantity new_qty);

    [[nodiscard]] BookSnapshot book_snapshot(std::size_t depth = 20) const;
    [[nodiscard]] const Instrument& instrument() const { return instrument_; }
    [[nodiscard]] SequenceNum sequence() const { return sequence_; }
    [[nodiscard]] std::size_t pending_stop_count() const { return stop_orders_.size(); }

private:
    OrderId next_order_id();
    TradeId next_trade_id();
    SequenceNum next_sequence();

    std::vector<OrderEvent> reject(const OrderRequest& req, RejectReason reason);
    std::vector<OrderEvent> emit_event(OrderEvent::Type type, Order& order,
                                       const std::optional<Trade>& trade = std::nullopt);

    bool validate_request(const OrderRequest& req, RejectReason& reason) const;
    bool would_cross(Side side, Price price) const;
    Quantity available_at_price(Side side, Price limit_price) const;
    bool can_fill_fok(Side side, Price limit_price, Quantity qty) const;

    void match_order(uint32_t taker_idx, std::vector<OrderEvent>& events);
    void check_stop_triggers(Price last_trade_price, std::vector<OrderEvent>& events);
    void activate_stop(uint32_t stop_idx, std::vector<OrderEvent>& events);

    Instrument instrument_;
    OrderBook book_;
    EventCallback callback_;

    OrderId order_id_gen_{1};
    TradeId trade_id_gen_{1};
    SequenceNum sequence_{0};

    std::unordered_set<ClientOrderId> client_order_ids_;
    std::vector<uint32_t> stop_orders_;
};

/// Multi-instrument exchange matching coordinator.
class ExchangeMatching {
public:
    void add_instrument(Instrument instrument);
    [[nodiscard]] MatchingEngine* get_engine(InstrumentId id);
    [[nodiscard]] const MatchingEngine* get_engine(InstrumentId id) const;
    [[nodiscard]] const std::unordered_map<InstrumentId, MatchingEngine>& engines() const {
        return engines_;
    }

    void for_each_engine(const std::function<void(MatchingEngine&)>& fn);

private:
    std::unordered_map<InstrumentId, MatchingEngine> engines_;
};

}  // namespace aegis
