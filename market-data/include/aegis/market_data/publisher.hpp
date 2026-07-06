#pragma once

#include "aegis/core/types.hpp"

#include <atomic>
#include <deque>
#include <functional>
#include <fstream>
#include <mutex>
#include <string>
#include <vector>

namespace aegis {

enum class MarketDataMsgType : uint8_t {
    BookSnapshot = 1,
    BookDelta = 2,
    Trade = 3,
    OrderEvent = 4,
    Heartbeat = 5
};

struct MarketDataMessage {
    MarketDataMsgType type{MarketDataMsgType::Heartbeat};
    InstrumentId instrument_id{0};
    SequenceNum sequence{0};
    Timestamp timestamp{0};
    std::string payload;  // JSON serialized
};

using MarketDataCallback = std::function<void(const MarketDataMessage&)>;

/// Publishes market data events to subscribers.
class MarketDataPublisher {
public:
    void subscribe(MarketDataCallback cb);
    void publish(const MarketDataMessage& msg);
    void publish_snapshot(const BookSnapshot& snap);
    void publish_trade(const Trade& trade);
    void publish_order_event(const OrderEvent& event);

    [[nodiscard]] std::size_t subscriber_count() const;
    [[nodiscard]] std::deque<MarketDataMessage> recent_messages(std::size_t limit = 100) const;

private:
    mutable std::mutex mutex_;
    std::vector<MarketDataCallback> subscribers_;
    std::deque<MarketDataMessage> history_;
    static constexpr std::size_t MAX_HISTORY = 10000;
};

/// Records market data to disk for replay.
class MarketDataRecorder {
public:
    explicit MarketDataRecorder(std::string path);
    ~MarketDataRecorder();

    void record(const MarketDataMessage& msg);
    void flush();
    [[nodiscard]] std::size_t record_count() const;

private:
    std::mutex mutex_;
    std::ofstream file_;
    std::atomic<std::size_t> count_{0};
};

/// Replays recorded market data.
class ReplayEngine {
public:
    explicit ReplayEngine(std::string path);

    [[nodiscard]] bool load();
    [[nodiscard]] std::size_t message_count() const { return messages_.size(); }

    void replay(MarketDataCallback cb, double speed_multiplier = 1.0);
    [[nodiscard]] const std::vector<MarketDataMessage>& messages() const { return messages_; }

private:
    std::string path_;
    std::vector<MarketDataMessage> messages_;
};

}  // namespace aegis
