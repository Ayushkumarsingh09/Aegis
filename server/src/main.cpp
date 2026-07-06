#include <spdlog/spdlog.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <thread>

#include "aegis/gateway/api_server.hpp"
#include "aegis/market_data/publisher.hpp"
#include "aegis/matching/matching_engine.hpp"
#include "aegis/risk/risk_engine.hpp"

namespace {
std::atomic<bool> g_running{true};

void signal_handler(int) {
    g_running = false;
}
}  // namespace

int main(int argc, char* argv[]) {
    spdlog::set_level(spdlog::level::info);
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] %v");

    int port = 8080;
    if (argc > 1) port = std::atoi(argv[1]);

    spdlog::info("===========================================");
    spdlog::info("  AEGIS EXCHANGE v1.0.0");
    spdlog::info("  Institutional-Grade Matching Engine");
    spdlog::info("===========================================");

    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    aegis::ExchangeMatching matching;
    aegis::RiskEngine risk;
    aegis::MarketDataPublisher publisher;
    aegis::MarketDataRecorder recorder("data/market_data.log");
    std::filesystem::create_directories("data");

    // Default instruments
    aegis::Instrument btc;
    btc.id = 1;
    btc.symbol = "BTC-USD";
    btc.tick_size = aegis::double_to_price(0.01);
    btc.lot_size = 1;
    btc.min_price = aegis::double_to_price(0.01);
    btc.max_price = aegis::double_to_price(1000000.0);
    btc.max_order_qty = 1000000;
    btc.active = true;

    aegis::Instrument eth;
    eth.id = 2;
    eth.symbol = "ETH-USD";
    eth.tick_size = aegis::double_to_price(0.01);
    eth.lot_size = 1;
    eth.min_price = aegis::double_to_price(0.01);
    eth.max_price = aegis::double_to_price(100000.0);
    eth.max_order_qty = 1000000;
    eth.active = true;

    matching.add_instrument(btc);
    matching.add_instrument(eth);

    matching.for_each_engine([&](aegis::MatchingEngine& engine) {
        engine.set_event_callback([&](const aegis::OrderEvent& ev) {
            publisher.publish_order_event(ev);
            if (ev.trade) {
                publisher.publish_trade(*ev.trade);
                risk.on_fill(ev.order.account_id, ev.order.side, ev.trade->price,
                             ev.trade->quantity);
            }
        });
    });

    publisher.subscribe([&](const aegis::MarketDataMessage& msg) { recorder.record(msg); });

    aegis::GatewayConfig config;
    config.port = port;
    aegis::ApiServer api(matching, risk, publisher, config);
    api.start();

    spdlog::info("Exchange running on port {}", port);
    spdlog::info("API: http://0.0.0.0:{}/api/v1/status", port);
    spdlog::info("Metrics: http://0.0.0.0:{}/metrics", port);

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    api.stop();
    spdlog::info("Aegis Exchange shutdown complete");
    return 0;
}
