#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <cassert>

namespace aegis {

/// Fixed-capacity slab allocator with O(1) allocate/deallocate via free list.
template <typename T, std::size_t Capacity>
class ObjectPool {
public:
    static constexpr std::size_t capacity = Capacity;
    static constexpr uint32_t INVALID_INDEX = UINT32_MAX;

    ObjectPool() {
        storage_.resize(Capacity);
        free_list_.reserve(Capacity);
        for (std::size_t i = 0; i < Capacity; ++i) {
            free_list_.push_back(static_cast<uint32_t>(Capacity - 1 - i));
        }
    }

    [[nodiscard]] uint32_t allocate() {
        assert(!free_list_.empty() && "ObjectPool exhausted");
        uint32_t idx = free_list_.back();
        free_list_.pop_back();
        ++allocated_;
        return idx;
    }

    void deallocate(uint32_t idx) {
        assert(idx < Capacity);
        free_list_.push_back(idx);
        --allocated_;
    }

    T& get(uint32_t idx) { return storage_[idx]; }
    const T& get(uint32_t idx) const { return storage_[idx]; }

    [[nodiscard]] std::size_t allocated() const { return allocated_; }
    [[nodiscard]] std::size_t available() const { return free_list_.size(); }
    [[nodiscard]] bool empty() const { return free_list_.size() == Capacity; }

private:
    std::vector<T> storage_;
    std::vector<uint32_t> free_list_;
    std::size_t allocated_{0};
};

}  // namespace aegis
