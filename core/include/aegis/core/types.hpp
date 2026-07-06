#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <chrono>
#include <optional>
#include <vector>

namespace aegis {

using OrderId = uint64_t;
using ClientOrderId = uint64_t;
using SequenceNum = uint64_t;
using TradeId = uint64_t;
using InstrumentId = uint32_t;
using AccountId = uint32_t;
using Price = int64_t;
using Quantity = int64_t;
using Timestamp = int64_t;

constexpr int64_t PRICE_SCALE = 10000;
constexpr Price INVALID_PRICE = 0;
constexpr Quantity INVALID_QTY = 0;

enum class Side : uint8_t { Buy = 0, Sell = 1 };
enum class OrderType : uint8_t {
    Limit = 0,
    Market = 1,
    IOC = 2,
    FOK = 3,
    PostOnly = 4,
    Stop = 5,
    StopLimit = 6
};
enum class OrderStatus : uint8_t {
    Pending = 0,
    Accepted = 1,
    PartiallyFilled = 2,
    Filled = 3,
    Cancelled = 4,
    Rejected = 5,
    Triggered = 6
};
enum class RejectReason : uint8_t {
    None = 0,
    InvalidQuantity,
    InvalidPrice,
    RiskLimit,
    PostOnlyWouldCross,
    FOKNotFillable,
    OrderNotFound,
    KillSwitch,
    UnknownInstrument,
    DuplicateClientOrderId
};

struct Instrument {
    InstrumentId id{0};
    std::string symbol;
    Price tick_size{1};
    Quantity lot_size{1};
    Price min_price{1};
    Price max_price{1'000'000'000};
    Quantity max_order_qty{1'000'000};
    bool active{true};
};

struct OrderRequest {
    ClientOrderId client_order_id{0};
    AccountId account_id{0};
    InstrumentId instrument_id{0};
    Side side{Side::Buy};
    OrderType type{OrderType::Limit};
    Price price{0};
    Quantity quantity{0};
    Price stop_price{0};
    Timestamp timestamp{0};
};

struct Order {
    OrderId order_id{0};
    ClientOrderId client_order_id{0};
    AccountId account_id{0};
    InstrumentId instrument_id{0};
    Side side{Side::Buy};
    OrderType type{OrderType::Limit};
    OrderStatus status{OrderStatus::Pending};
    Price price{0};
    Quantity original_qty{0};
    Quantity remaining_qty{0};
    Quantity filled_qty{0};
    Price stop_price{0};
    Price avg_fill_price{0};
    SequenceNum sequence{0};
    Timestamp created_at{0};
    Timestamp updated_at{0};
    uint32_t pool_index{0};
};

struct Trade {
    TradeId trade_id{0};
    OrderId maker_order_id{0};
    OrderId taker_order_id{0};
    InstrumentId instrument_id{0};
    Side aggressor_side{Side::Buy};
    Price price{0};
    Quantity quantity{0};
    SequenceNum sequence{0};
    Timestamp timestamp{0};
};

struct BookLevel {
    Price price{0};
    Quantity quantity{0};
    uint32_t order_count{0};
};

struct BookSnapshot {
    InstrumentId instrument_id{0};
    SequenceNum sequence{0};
    Timestamp timestamp{0};
    std::vector<BookLevel> bids;
    std::vector<BookLevel> asks;
};

struct OrderEvent {
    enum class Type : uint8_t {
        Accepted,
        Rejected,
        PartialFill,
        Fill,
        Cancelled,
        Modified,
        Triggered
    };
    Type type{Type::Accepted};
    Order order{};
    RejectReason reject_reason{RejectReason::None};
    std::optional<Trade> trade{};
    SequenceNum sequence{0};
    Timestamp timestamp{0};
};

inline const char* to_string(Side s) { return s == Side::Buy ? "BUY" : "SELL"; }
inline const char* to_string(OrderType t) {
    switch (t) {
        case OrderType::Limit: return "LIMIT";
        case OrderType::Market: return "MARKET";
        case OrderType::IOC: return "IOC";
        case OrderType::FOK: return "FOK";
        case OrderType::PostOnly: return "POST_ONLY";
        case OrderType::Stop: return "STOP";
        case OrderType::StopLimit: return "STOP_LIMIT";
    }
    return "UNKNOWN";
}
inline const char* to_string(OrderStatus s) {
    switch (s) {
        case OrderStatus::Pending: return "PENDING";
        case OrderStatus::Accepted: return "ACCEPTED";
        case OrderStatus::PartiallyFilled: return "PARTIALLY_FILLED";
        case OrderStatus::Filled: return "FILLED";
        case OrderStatus::Cancelled: return "CANCELLED";
        case OrderStatus::Rejected: return "REJECTED";
        case OrderStatus::Triggered: return "TRIGGERED";
    }
    return "UNKNOWN";
}

double price_to_double(Price p);
Price double_to_price(double p);
std::string format_price(Price p);
std::string format_quantity(Quantity q);

}  // namespace aegis
