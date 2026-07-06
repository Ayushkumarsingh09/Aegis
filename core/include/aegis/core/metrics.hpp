#pragma once

#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace aegis {

class MetricsRegistry {
   public:
    static MetricsRegistry& instance();

    void increment(const std::string& name, int64_t delta = 1);
    void set_gauge(const std::string& name, double value);
    void observe_histogram(const std::string& name, double value);

    std::string prometheus_text() const;

    void reset();

   private:
    MetricsRegistry() = default;

    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::atomic<int64_t>> counters_;
    std::unordered_map<std::string, double> gauges_;
    std::unordered_map<std::string, std::vector<double>> histograms_;
};

class ScopedTimer {
   public:
    explicit ScopedTimer(const std::string& metric_name);
    ~ScopedTimer();

    ScopedTimer(const ScopedTimer&) = delete;
    ScopedTimer& operator=(const ScopedTimer&) = delete;

   private:
    std::string name_;
    int64_t start_ns_;
};

}  // namespace aegis
