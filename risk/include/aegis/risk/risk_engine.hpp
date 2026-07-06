#pragma once

#include <mutex>
#include <unordered_map>

#include "aegis/core/types.hpp"

namespace aegis {

struct RiskLimits {
    Quantity max_order_size{1'000'000};
    Quantity max_position{10'000'000};
    int64_t max_exposure{100'000'000'000LL};  // price*qty scaled
    int64_t daily_loss_limit{50'000'000'000LL};
    bool kill_switch{false};
};

struct AccountState {
    Quantity net_position{0};
    int64_t realized_pnl{0};
    int64_t exposure{0};
    Quantity buy_volume{0};
    Quantity sell_volume{0};
};

struct RiskCheckResult {
    bool approved{true};
    RejectReason reason{RejectReason::None};
    std::string message;
};

/// Pre-trade and post-trade risk validation engine.
class RiskEngine {
   public:
    void set_limits(const RiskLimits& limits);
    [[nodiscard]] RiskLimits limits() const;

    void activate_kill_switch(const std::string& reason);
    void deactivate_kill_switch();
    [[nodiscard]] bool kill_switch_active() const;
    [[nodiscard]] std::string kill_switch_reason() const;

    RiskCheckResult validate_order(const OrderRequest& req, Price mark_price) const;
    void on_fill(AccountId account, Side side, Price price, Quantity qty);
    void on_trade_pnl(AccountId account, int64_t pnl_delta);

    [[nodiscard]] AccountState account_state(AccountId account) const;
    [[nodiscard]] std::unordered_map<AccountId, AccountState> all_accounts() const;

    void reset_daily();

   private:
    mutable std::mutex mutex_;
    RiskLimits limits_;
    std::unordered_map<AccountId, AccountState> accounts_;
    std::string kill_reason_;
};

}  // namespace aegis
