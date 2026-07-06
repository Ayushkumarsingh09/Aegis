#include "aegis/market_data/publisher.hpp"

#include <spdlog/spdlog.h>

#include <chrono>
#include <fstream>
#include <nlohmann/json.hpp>
#include <thread>

#include "aegis/core/clock.hpp"

namespace aegis {

using json = nlohmann::json;

void MarketDataPublisher::subscribe(MarketDataCallback cb) {
    std::lock_guard lock(mutex_);
    subscribers_.push_back(std::move(cb));
}

void MarketDataPublisher::publish(const MarketDataMessage& msg) {
    std::vector<MarketDataCallback> subs;
    {
        std::lock_guard lock(mutex_);
        history_.push_back(msg);
        if (history_.size() > MAX_HISTORY) history_.pop_front();
        subs = subscribers_;
    }
    for (const auto& cb : subs) {
        if (cb) cb(msg);
    }
}

void MarketDataPublisher::publish_snapshot(const BookSnapshot& snap) {
    json j;
    j["type"] = "book_snapshot";
    j["instrument_id"] = snap.instrument_id;
    j["sequence"] = snap.sequence;
    j["timestamp"] = snap.timestamp;
    j["bids"] = json::array();
    j["asks"] = json::array();
    for (const auto& b : snap.bids) {
        j["bids"].push_back({{"price", price_to_double(b.price)},
                             {"quantity", b.quantity},
                             {"orders", b.order_count}});
    }
    for (const auto& a : snap.asks) {
        j["asks"].push_back({{"price", price_to_double(a.price)},
                             {"quantity", a.quantity},
                             {"orders", a.order_count}});
    }

    MarketDataMessage msg;
    msg.type = MarketDataMsgType::BookSnapshot;
    msg.instrument_id = snap.instrument_id;
    msg.sequence = snap.sequence;
    msg.timestamp = snap.timestamp;
    msg.payload = j.dump();
    publish(msg);
}

void MarketDataPublisher::publish_trade(const Trade& trade) {
    json j;
    j["type"] = "trade";
    j["trade_id"] = trade.trade_id;
    j["instrument_id"] = trade.instrument_id;
    j["price"] = price_to_double(trade.price);
    j["quantity"] = trade.quantity;
    j["side"] = to_string(trade.aggressor_side);
    j["sequence"] = trade.sequence;
    j["timestamp"] = trade.timestamp;

    MarketDataMessage msg;
    msg.type = MarketDataMsgType::Trade;
    msg.instrument_id = trade.instrument_id;
    msg.sequence = trade.sequence;
    msg.timestamp = trade.timestamp;
    msg.payload = j.dump();
    publish(msg);
}

void MarketDataPublisher::publish_order_event(const OrderEvent& event) {
    json j;
    j["type"] = "order_event";
    j["event"] = static_cast<int>(event.type);
    j["order_id"] = event.order.order_id;
    j["client_order_id"] = event.order.client_order_id;
    j["status"] = to_string(event.order.status);
    j["side"] = to_string(event.order.side);
    j["price"] = price_to_double(event.order.price);
    j["quantity"] = event.order.remaining_qty;
    j["filled"] = event.order.filled_qty;
    j["sequence"] = event.sequence;
    j["timestamp"] = event.timestamp;
    if (event.trade) {
        j["trade_price"] = price_to_double(event.trade->price);
        j["trade_qty"] = event.trade->quantity;
    }

    MarketDataMessage msg;
    msg.type = MarketDataMsgType::OrderEvent;
    msg.instrument_id = event.order.instrument_id;
    msg.sequence = event.sequence;
    msg.timestamp = event.timestamp;
    msg.payload = j.dump();
    publish(msg);
}

std::size_t MarketDataPublisher::subscriber_count() const {
    std::lock_guard lock(mutex_);
    return subscribers_.size();
}

std::deque<MarketDataMessage> MarketDataPublisher::recent_messages(std::size_t limit) const {
    std::lock_guard lock(mutex_);
    std::deque<MarketDataMessage> result;
    std::size_t start = history_.size() > limit ? history_.size() - limit : 0;
    std::size_t i = 0;
    for (const auto& m : history_) {
        if (i++ >= start) result.push_back(m);
    }
    return result;
}

MarketDataRecorder::MarketDataRecorder(std::string path) : file_(path, std::ios::app) {}

MarketDataRecorder::~MarketDataRecorder() {
    flush();
}

void MarketDataRecorder::record(const MarketDataMessage& msg) {
    std::lock_guard lock(mutex_);
    if (!file_.is_open()) return;
    file_ << msg.timestamp << "|" << static_cast<int>(msg.type) << "|" << msg.instrument_id << "|"
          << msg.sequence << "|" << msg.payload << "\n";
    count_.fetch_add(1, std::memory_order_relaxed);
}

void MarketDataRecorder::flush() {
    std::lock_guard lock(mutex_);
    if (file_.is_open()) file_.flush();
}

std::size_t MarketDataRecorder::record_count() const {
    return count_.load(std::memory_order_relaxed);
}

ReplayEngine::ReplayEngine(std::string path) : path_(std::move(path)) {}

bool ReplayEngine::load() {
    std::ifstream file(path_);
    if (!file.is_open()) {
        spdlog::error("Failed to open replay file: {}", path_);
        return false;
    }
    messages_.clear();
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        auto p1 = line.find('|');
        auto p2 = line.find('|', p1 + 1);
        auto p3 = line.find('|', p2 + 1);
        auto p4 = line.find('|', p3 + 1);
        if (p1 == std::string::npos || p4 == std::string::npos) continue;

        MarketDataMessage msg;
        msg.timestamp = std::stoll(line.substr(0, p1));
        msg.type = static_cast<MarketDataMsgType>(std::stoi(line.substr(p1 + 1, p2 - p1 - 1)));
        msg.instrument_id = static_cast<InstrumentId>(std::stoul(line.substr(p2 + 1, p3 - p2 - 1)));
        msg.sequence = static_cast<SequenceNum>(std::stoull(line.substr(p3 + 1, p4 - p3 - 1)));
        msg.payload = line.substr(p4 + 1);
        messages_.push_back(std::move(msg));
    }
    spdlog::info("Loaded {} replay messages from {}", messages_.size(), path_);
    return true;
}

void ReplayEngine::replay(MarketDataCallback cb, double speed_multiplier) {
    if (messages_.empty()) return;
    Timestamp prev_ts = messages_.front().timestamp;
    for (const auto& msg : messages_) {
        if (speed_multiplier > 0 && cb) {
            Timestamp delta = msg.timestamp - prev_ts;
            if (delta > 0) {
                auto sleep_us = static_cast<int64_t>(delta / 1000.0 / speed_multiplier);
                if (sleep_us > 0) {
                    std::this_thread::sleep_for(std::chrono::microseconds(sleep_us));
                }
            }
            prev_ts = msg.timestamp;
        }
        if (cb) cb(msg);
    }
}

}  // namespace aegis
