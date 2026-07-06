#pragma once

#include "aegis/market_data/publisher.hpp"
#include "aegis/matching/matching_engine.hpp"
#include "aegis/risk/risk_engine.hpp"

#include <atomic>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace aegis {

struct GatewayConfig {
    std::string host{"0.0.0.0"};
    int port{8080};
    std::string data_dir{"data"};
};

/// WebSocket subscriber hub for streaming market data.
class WebSocketHub {
public:
    using SendFn = std::function<void(const std::string&)>;

    void add_client(SendFn send);
    void remove_client(std::size_t id);
    void broadcast(const std::string& message);
    [[nodiscard]] std::size_t client_count() const;

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::size_t, SendFn> clients_;
    std::atomic<std::size_t> next_id_{0};
};

/// REST + WebSocket API gateway.
class ApiServer {
public:
    ApiServer(ExchangeMatching& matching, RiskEngine& risk, MarketDataPublisher& publisher,
              GatewayConfig config = {});

    void start();
    void stop();
    ~ApiServer();
    [[nodiscard]] bool running() const { return running_; }

    WebSocketHub& ws_hub() { return ws_hub_; }

private:
    void setup_routes();
    std::string handle_submit_order(const std::string& body);
    std::string handle_cancel_order(const std::string& body);
    std::string handle_modify_order(const std::string& body);
    std::string book_to_json(InstrumentId id, std::size_t depth) const;
    std::string status_json() const;

    ExchangeMatching& matching_;
    RiskEngine& risk_;
    MarketDataPublisher& publisher_;
    GatewayConfig config_;
    WebSocketHub ws_hub_;

    std::unique_ptr<class ApiServerImpl> impl_;
    std::atomic<bool> running_{false};
};

}  // namespace aegis
