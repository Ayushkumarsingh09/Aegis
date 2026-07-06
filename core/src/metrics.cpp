#include "aegis/core/metrics.hpp"

#include <algorithm>
#include <sstream>

#include "aegis/core/clock.hpp"

namespace aegis {

MetricsRegistry& MetricsRegistry::instance() {
    static MetricsRegistry registry;
    return registry;
}

void MetricsRegistry::increment(const std::string& name, int64_t delta) {
    std::lock_guard lock(mutex_);
    auto& counter = counters_[name];
    counter.fetch_add(delta, std::memory_order_relaxed);
}

void MetricsRegistry::set_gauge(const std::string& name, double value) {
    std::lock_guard lock(mutex_);
    gauges_[name] = value;
}

void MetricsRegistry::observe_histogram(const std::string& name, double value) {
    std::lock_guard lock(mutex_);
    auto& hist = histograms_[name];
    hist.push_back(value);
    if (hist.size() > 10000) {
        hist.erase(hist.begin(), hist.begin() + 5000);
    }
}

std::string MetricsRegistry::prometheus_text() const {
    std::lock_guard lock(mutex_);
    std::ostringstream oss;
    oss << "# HELP aegis_info Aegis Exchange metrics\n";
    oss << "# TYPE aegis_info gauge\n";
    oss << "aegis_info{version=\"1.0.0\"} 1\n";

    for (const auto& [name, val] : counters_) {
        oss << "# TYPE " << name << " counter\n";
        oss << name << " " << val.load(std::memory_order_relaxed) << "\n";
    }
    for (const auto& [name, val] : gauges_) {
        oss << "# TYPE " << name << " gauge\n";
        oss << name << " " << val << "\n";
    }
    for (const auto& [name, samples] : histograms_) {
        if (samples.empty()) continue;
        auto sorted = samples;
        std::sort(sorted.begin(), sorted.end());
        double sum = 0;
        for (double s : sorted) sum += s;
        oss << "# TYPE " << name << "_sum gauge\n";
        oss << name << "_sum " << sum << "\n";
        oss << "# TYPE " << name << "_count gauge\n";
        oss << name << "_count " << sorted.size() << "\n";
        oss << "# TYPE " << name << "_p50 gauge\n";
        oss << name << "_p50 " << sorted[sorted.size() / 2] << "\n";
        oss << "# TYPE " << name << "_p99 gauge\n";
        oss << name << "_p99 " << sorted[static_cast<size_t>(sorted.size() * 0.99)] << "\n";
    }
    return oss.str();
}

void MetricsRegistry::reset() {
    std::lock_guard lock(mutex_);
    counters_.clear();
    gauges_.clear();
    histograms_.clear();
}

ScopedTimer::ScopedTimer(const std::string& metric_name)
    : name_(metric_name), start_ns_(Clock::now_ns()) {}

ScopedTimer::~ScopedTimer() {
    double elapsed_us = static_cast<double>(Clock::now_ns() - start_ns_) / 1000.0;
    MetricsRegistry::instance().observe_histogram(name_, elapsed_us);
}

}  // namespace aegis
