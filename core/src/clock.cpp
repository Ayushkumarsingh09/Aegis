#include "aegis/core/clock.hpp"

#include <atomic>
#include <chrono>

namespace aegis {

namespace {
std::atomic<bool> simulated{false};
std::atomic<Timestamp> simulated_time{0};
}  // namespace

Timestamp Clock::now_ns() {
    if (simulated.load(std::memory_order_acquire)) {
        return simulated_time.load(std::memory_order_relaxed);
    }
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

Timestamp Clock::wall_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::system_clock::now().time_since_epoch())
        .count();
}

void Clock::set_simulated(Timestamp ts) {
    simulated_time.store(ts, std::memory_order_relaxed);
    simulated.store(true, std::memory_order_release);
}

void Clock::advance_simulated(Timestamp delta) {
    simulated_time.fetch_add(delta, std::memory_order_relaxed);
}

bool Clock::is_simulated() {
    return simulated.load(std::memory_order_acquire);
}

}  // namespace aegis
