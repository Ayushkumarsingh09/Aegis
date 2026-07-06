#pragma once

#include "aegis/core/types.hpp"

namespace aegis {

class Clock {
   public:
    static Timestamp now_ns();
    static Timestamp wall_ns();
    static void set_simulated(Timestamp ts);
    static void advance_simulated(Timestamp delta);
    static bool is_simulated();
};

}  // namespace aegis
