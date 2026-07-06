#include "aegis/risk/risk_engine.hpp"

#include <cmath>

namespace aegis {

void RiskEngine::set_limits(const RiskLimits& limits) {
    std::lock_guard lock(mutex_);
    limits_ = limits;
}

RiskLimits RiskEngine::limits() const {
    std::lock_guard lock(mutex_);
    return limits_;
}

void RiskEngine::activate_kill_switch(const std::string& reason) {
    std::lock_guard lock(mutex_);
    limits_.kill_switch = true;
    kill_reason_ = reason;
}

void RiskEngine::deactivate_kill_switch() {
    std::lock_guard lock(mutex_);
    limits_.kill_switch = false;
    kill_reason_.clear();
}

bool RiskEngine::kill_switch_active() const {
    std::lock_guard lock(mutex_);
    return limits_.kill_switch;
}

std::string RiskEngine::kill_switch_reason() const {
    std::lock_guard lock(mutex_);
    return kill_reason_;
}

RiskCheckResult RiskEngine::validate_order(const OrderRequest& req, Price mark_price) const {
    std::lock_guard lock(mutex_);
    RiskCheckResult result;

    if (limits_.kill_switch) {
        result.approved = false;
        result.reason = RejectReason::KillSwitch;
        result.message = "Kill switch active: " + kill_reason_;
        return result;
    }

    if (req.quantity > limits_.max_order_size) {
        result.approved = false;
        result.reason = RejectReason::RiskLimit;
        result.message = "Order size exceeds maximum";
        return result;
    }

    auto it = accounts_.find(req.account_id);
    const AccountState state = it != accounts_.end() ? it->second : AccountState{};
    Quantity projected_position = state.net_position;
    if (req.side == Side::Buy) {
        projected_position += req.quantity;
    } else {
        projected_position -= req.quantity;
    }

    if (std::llabs(projected_position) > limits_.max_position) {
        result.approved = false;
        result.reason = RejectReason::RiskLimit;
        result.message = "Position limit exceeded";
        return result;
    }

    Price ref_price = req.price > 0 ? req.price : mark_price;
    int64_t order_exposure = static_cast<int64_t>(ref_price) * req.quantity;
    if (state.exposure + order_exposure > limits_.max_exposure) {
        result.approved = false;
        result.reason = RejectReason::RiskLimit;
        result.message = "Exposure limit exceeded";
        return result;
    }

    if (state.realized_pnl < -limits_.daily_loss_limit) {
        result.approved = false;
        result.reason = RejectReason::RiskLimit;
        result.message = "Daily loss limit breached";
        return result;
    }

    return result;
}

void RiskEngine::on_fill(AccountId account, Side side, Price price, Quantity qty) {
    std::lock_guard lock(mutex_);
    auto& state = accounts_[account];
    if (side == Side::Buy) {
        state.net_position += qty;
        state.buy_volume += qty;
    } else {
        state.net_position -= qty;
        state.sell_volume += qty;
    }
    state.exposure = std::llabs(static_cast<int64_t>(state.net_position) * price);
}

void RiskEngine::on_trade_pnl(AccountId account, int64_t pnl_delta) {
    std::lock_guard lock(mutex_);
    accounts_[account].realized_pnl += pnl_delta;
}

AccountState RiskEngine::account_state(AccountId account) const {
    std::lock_guard lock(mutex_);
    auto it = accounts_.find(account);
    return it != accounts_.end() ? it->second : AccountState{};
}

std::unordered_map<AccountId, AccountState> RiskEngine::all_accounts() const {
    std::lock_guard lock(mutex_);
    return accounts_;
}

void RiskEngine::reset_daily() {
    std::lock_guard lock(mutex_);
    for (auto& [id, state] : accounts_) {
        state.realized_pnl = 0;
    }
}

}  // namespace aegis
