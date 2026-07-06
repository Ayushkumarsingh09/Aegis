#include <gtest/gtest.h>
#include "aegis/risk/risk_engine.hpp"

using namespace aegis;

TEST(RiskEngineTest, ApproveValidOrder) {
    RiskEngine risk;
    OrderRequest req;
    req.account_id = 1;
    req.quantity = 100;
    req.side = Side::Buy;
    req.price = double_to_price(100.0);

    auto result = risk.validate_order(req, double_to_price(100.0));
    EXPECT_TRUE(result.approved);
}

TEST(RiskEngineTest, RejectOversizedOrder) {
    RiskEngine risk;
    RiskLimits limits;
    limits.max_order_size = 50;
    risk.set_limits(limits);

    OrderRequest req;
    req.account_id = 1;
    req.quantity = 100;

    auto result = risk.validate_order(req, double_to_price(100.0));
    EXPECT_FALSE(result.approved);
    EXPECT_EQ(result.reason, RejectReason::RiskLimit);
}

TEST(RiskEngineTest, KillSwitch) {
    RiskEngine risk;
    risk.activate_kill_switch("test");

    OrderRequest req;
    req.account_id = 1;
    req.quantity = 10;

    auto result = risk.validate_order(req, double_to_price(100.0));
    EXPECT_FALSE(result.approved);
    EXPECT_EQ(result.reason, RejectReason::KillSwitch);

    risk.deactivate_kill_switch();
    result = risk.validate_order(req, double_to_price(100.0));
    EXPECT_TRUE(result.approved);
}

TEST(RiskEngineTest, PositionTracking) {
    RiskEngine risk;
    risk.on_fill(1, Side::Buy, double_to_price(100.0), 50);
    risk.on_fill(1, Side::Sell, double_to_price(110.0), 20);

    auto state = risk.account_state(1);
    EXPECT_EQ(state.net_position, 30);
    EXPECT_EQ(state.buy_volume, 50);
    EXPECT_EQ(state.sell_volume, 20);
}

TEST(RiskEngineTest, PositionLimit) {
    RiskEngine risk;
    RiskLimits limits;
    limits.max_position = 100;
    risk.set_limits(limits);

    risk.on_fill(1, Side::Buy, double_to_price(100.0), 90);

    OrderRequest req;
    req.account_id = 1;
    req.quantity = 20;
    req.side = Side::Buy;
    req.price = double_to_price(100.0);

    auto result = risk.validate_order(req, double_to_price(100.0));
    EXPECT_FALSE(result.approved);
}
