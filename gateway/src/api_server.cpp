#include "aegis/gateway/api_server.hpp"

#include "aegis/core/clock.hpp"
#include "aegis/core/metrics.hpp"

#include <httplib.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <sstream>

namespace aegis {

using json = nlohmann::json;

class ApiServerImpl {
public:
    httplib::Server server;
    std::thread thread;
};

void WebSocketHub::add_client(SendFn send) {
    std::lock_guard lock(mutex_);
    clients_[next_id_++] = std::move(send);
}

void WebSocketHub::remove_client(std::size_t id) {
    std::lock_guard lock(mutex_);
    clients_.erase(id);
}

void WebSocketHub::broadcast(const std::string& message) {
    std::vector<SendFn> sends;
    {
        std::lock_guard lock(mutex_);
        for (const auto& [id, fn] : clients_) {
            (void)id;
            sends.push_back(fn);
        }
    }
    for (const auto& fn : sends) {
        if (fn) fn(message);
    }
}

std::size_t WebSocketHub::client_count() const {
    std::lock_guard lock(mutex_);
    return clients_.size();
}

ApiServer::ApiServer(ExchangeMatching& matching, RiskEngine& risk,
                     MarketDataPublisher& publisher, GatewayConfig config)
    : matching_(matching),
      risk_(risk),
      publisher_(publisher),
      config_(std::move(config)),
      impl_(std::make_unique<ApiServerImpl>()) {}

ApiServer::~ApiServer() = default;

void ApiServer::setup_routes() {
    auto& s = impl_->server;

    s.Get("/health", [this](const httplib::Request&, httplib::Response& res) {
        res.set_content(R"({"status":"healthy","service":"aegis-exchange"})", "application/json");
    });

    s.Get("/metrics", [](const httplib::Request&, httplib::Response& res) {
        res.set_content(MetricsRegistry::instance().prometheus_text(), "text/plain; version=0.0.4");
    });

    s.Get("/api/v1/status", [this](const httplib::Request&, httplib::Response& res) {
        res.set_content(status_json(), "application/json");
    });

    s.Get(R"(/api/v1/instruments/(\d+)/book)", [this](const httplib::Request& req, httplib::Response& res) {
        auto id = static_cast<InstrumentId>(std::stoul(req.matches[1]));
        std::size_t depth = 20;
        if (req.has_param("depth")) depth = std::stoul(req.get_param_value("depth"));
        res.set_content(book_to_json(id, depth), "application/json");
    });

    s.Get(R"(/api/v1/instruments/(\d+)/trades)", [this](const httplib::Request& req, httplib::Response& res) {
        (void)req;
        json j = json::array();
        auto recent = publisher_.recent_messages(500);
        for (const auto& m : recent) {
            if (m.type == MarketDataMsgType::Trade) {
                j.push_back(json::parse(m.payload));
            }
        }
        res.set_content(j.dump(), "application/json");
    });

    s.Post("/api/v1/orders", [this](const httplib::Request& req, httplib::Response& res) {
        auto result = handle_submit_order(req.body);
        res.set_content(result, "application/json");
    });

    s.Delete("/api/v1/orders", [this](const httplib::Request& req, httplib::Response& res) {
        auto result = handle_cancel_order(req.body);
        res.set_content(result, "application/json");
    });

    s.Put("/api/v1/orders", [this](const httplib::Request& req, httplib::Response& res) {
        auto result = handle_modify_order(req.body);
        res.set_content(result, "application/json");
    });

    s.Get("/api/v1/risk", [this](const httplib::Request&, httplib::Response& res) {
        json j;
        j["kill_switch"] = risk_.kill_switch_active();
        j["reason"] = risk_.kill_switch_reason();
        auto limits = risk_.limits();
        j["limits"]["max_order_size"] = limits.max_order_size;
        j["limits"]["max_position"] = limits.max_position;
        j["limits"]["max_exposure"] = limits.max_exposure;
        j["limits"]["daily_loss_limit"] = limits.daily_loss_limit;
        j["accounts"] = json::object();
        for (const auto& [id, state] : risk_.all_accounts()) {
            j["accounts"][std::to_string(id)] = {
                {"net_position", state.net_position},
                {"realized_pnl", state.realized_pnl},
                {"exposure", state.exposure}};
        }
        res.set_content(j.dump(), "application/json");
    });

    s.Post("/api/v1/risk/kill-switch", [this](const httplib::Request& req, httplib::Response& res) {
        auto body = json::parse(req.body);
        if (body.value("active", false)) {
            risk_.activate_kill_switch(body.value("reason", "manual"));
        } else {
            risk_.deactivate_kill_switch();
        }
        res.set_content(R"({"status":"ok"})", "application/json");
    });

    s.Get("/api/v1/ws", [](const httplib::Request&, httplib::Response& res) {
        res.status = 426;
        res.set_content(R"({"error":"use SSE stream at /api/v1/stream"})", "application/json");
    });

    // SSE fallback for market data streaming
    s.Get("/api/v1/stream", [this](const httplib::Request&, httplib::Response& res) {
        res.set_header("Content-Type", "text/event-stream");
        res.set_header("Cache-Control", "no-cache");
        res.set_header("Connection", "keep-alive");

        auto recent = publisher_.recent_messages(50);
        std::ostringstream oss;
        for (const auto& m : recent) {
            oss << "data: " << m.payload << "\n\n";
        }
        res.set_content(oss.str(), "text/event-stream");
    });

    s.set_pre_routing_handler([](const httplib::Request& req, httplib::Response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        res.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
        res.set_header("Access-Control-Allow-Headers", "Content-Type");
        if (req.method == "OPTIONS") {
            res.status = 204;
            return httplib::Server::HandlerResponse::Handled;
        }
        return httplib::Server::HandlerResponse::Unhandled;
    });
}

std::string ApiServer::handle_submit_order(const std::string& body) {
    try {
        auto j = json::parse(body);
        OrderRequest req;
        req.client_order_id = j.at("client_order_id").get<ClientOrderId>();
        req.account_id = j.at("account_id").get<AccountId>();
        req.instrument_id = j.at("instrument_id").get<InstrumentId>();
        req.side = j.at("side").get<std::string>() == "BUY" ? Side::Buy : Side::Sell;
        req.quantity = j.at("quantity").get<Quantity>();

        std::string type_str = j.at("type").get<std::string>();
        if (type_str == "LIMIT") req.type = OrderType::Limit;
        else if (type_str == "MARKET") req.type = OrderType::Market;
        else if (type_str == "IOC") req.type = OrderType::IOC;
        else if (type_str == "FOK") req.type = OrderType::FOK;
        else if (type_str == "POST_ONLY") req.type = OrderType::PostOnly;
        else if (type_str == "STOP") req.type = OrderType::Stop;
        else if (type_str == "STOP_LIMIT") req.type = OrderType::StopLimit;

        if (j.contains("price")) req.price = double_to_price(j.at("price").get<double>());
        if (j.contains("stop_price")) req.stop_price = double_to_price(j.at("stop_price").get<double>());
        req.timestamp = Clock::wall_ns();

        auto* engine = matching_.get_engine(req.instrument_id);
        if (!engine) {
            return R"({"error":"unknown instrument"})";
        }

        Price mark = engine->book_snapshot(1).bids.empty()
                         ? (engine->book_snapshot(1).asks.empty()
                                ? 0
                                : engine->book_snapshot(1).asks[0].price)
                         : engine->book_snapshot(1).bids[0].price;

        auto risk = risk_.validate_order(req, mark);
        if (!risk.approved) {
            json rj;
            rj["status"] = "REJECTED";
            rj["reason"] = risk.message;
            return rj.dump();
        }

        auto events = engine->submit_order(req);
        json result = json::array();
        for (const auto& ev : events) {
            json ej;
            ej["event"] = static_cast<int>(ev.type);
            ej["order_id"] = ev.order.order_id;
            ej["status"] = to_string(ev.order.status);
            ej["filled"] = ev.order.filled_qty;
            ej["remaining"] = ev.order.remaining_qty;
            if (ev.trade) {
                ej["trade_price"] = price_to_double(ev.trade->price);
                ej["trade_qty"] = ev.trade->quantity;
                publisher_.publish_trade(*ev.trade);
            }
            publisher_.publish_order_event(ev);
            result.push_back(ej);
        }

        auto snap = engine->book_snapshot();
        publisher_.publish_snapshot(snap);

        json snap_json = json::parse(book_to_json(req.instrument_id, 20));
        ws_hub_.broadcast(snap_json.dump());

        MetricsRegistry::instance().increment("aegis_api_orders_total");
        return result.dump();
    } catch (const std::exception& e) {
        json err;
        err["error"] = e.what();
        return err.dump();
    }
}

std::string ApiServer::handle_cancel_order(const std::string& body) {
    try {
        auto j = json::parse(body);
        OrderId oid = j.at("order_id").get<OrderId>();
        AccountId aid = j.at("account_id").get<AccountId>();
        InstrumentId iid = j.at("instrument_id").get<InstrumentId>();

        auto* engine = matching_.get_engine(iid);
        if (!engine) return R"({"error":"unknown instrument"})";

        auto events = engine->cancel_order(oid, aid);
        json result = json::array();
        for (const auto& ev : events) {
            json ej;
            ej["order_id"] = ev.order.order_id;
            ej["status"] = to_string(ev.order.status);
            publisher_.publish_order_event(ev);
            result.push_back(ej);
        }
        publisher_.publish_snapshot(engine->book_snapshot());
        return result.dump();
    } catch (const std::exception& e) {
        return json{{"error", e.what()}}.dump();
    }
}

std::string ApiServer::handle_modify_order(const std::string& body) {
    try {
        auto j = json::parse(body);
        OrderId oid = j.at("order_id").get<OrderId>();
        AccountId aid = j.at("account_id").get<AccountId>();
        InstrumentId iid = j.at("instrument_id").get<InstrumentId>();
        Price new_price = j.contains("price") ? double_to_price(j.at("price").get<double>()) : 0;
        Quantity new_qty = j.at("quantity").get<Quantity>();

        auto* engine = matching_.get_engine(iid);
        if (!engine) return R"({"error":"unknown instrument"})";

        auto events = engine->modify_order(oid, aid, new_price, new_qty);
        json result = json::array();
        for (const auto& ev : events) {
            json ej;
            ej["order_id"] = ev.order.order_id;
            ej["status"] = to_string(ev.order.status);
            ej["price"] = price_to_double(ev.order.price);
            ej["remaining"] = ev.order.remaining_qty;
            publisher_.publish_order_event(ev);
            result.push_back(ej);
        }
        publisher_.publish_snapshot(engine->book_snapshot());
        return result.dump();
    } catch (const std::exception& e) {
        return json{{"error", e.what()}}.dump();
    }
}

std::string ApiServer::book_to_json(InstrumentId id, std::size_t depth) const {
    auto* engine = matching_.get_engine(id);
    if (!engine) return R"({"error":"unknown instrument"})";

    auto snap = engine->book_snapshot(depth);
    json j;
    j["instrument_id"] = snap.instrument_id;
    j["sequence"] = snap.sequence;
    j["timestamp"] = snap.timestamp;
    j["bids"] = json::array();
    j["asks"] = json::array();
    for (const auto& b : snap.bids) {
        j["bids"].push_back(
            {{"price", price_to_double(b.price)}, {"quantity", b.quantity}, {"orders", b.order_count}});
    }
    for (const auto& a : snap.asks) {
        j["asks"].push_back(
            {{"price", price_to_double(a.price)}, {"quantity", a.quantity}, {"orders", a.order_count}});
    }
    return j.dump();
}

std::string ApiServer::status_json() const {
    json j;
    j["service"] = "aegis-exchange";
    j["version"] = "1.0.0";
    j["uptime_ns"] = Clock::now_ns();
    j["instruments"] = json::array();
    for (const auto& [id, engine] : matching_.engines()) {
        (void)engine;
        j["instruments"].push_back({{"id", id}, {"symbol", engine.instrument().symbol}});
    }
    j["kill_switch"] = risk_.kill_switch_active();
    j["ws_clients"] = ws_hub_.client_count();
    return j.dump();
}

void ApiServer::start() {
    setup_routes();
    running_ = true;
    spdlog::info("Aegis API server starting on {}:{}", config_.host, config_.port);

    impl_->thread = std::thread([this]() {
        impl_->server.listen(config_.host.c_str(), config_.port);
    });
}

void ApiServer::stop() {
    if (!running_) return;
    running_ = false;
    impl_->server.stop();
    if (impl_->thread.joinable()) impl_->thread.join();
    spdlog::info("Aegis API server stopped");
}

}  // namespace aegis
