#include "aegis/core/types.hpp"

#include <cmath>
#include <iomanip>
#include <sstream>

namespace aegis {

double price_to_double(Price p) {
    return static_cast<double>(p) / PRICE_SCALE;
}

Price double_to_price(double p) {
    return static_cast<Price>(std::llround(p * PRICE_SCALE));
}

std::string format_price(Price p) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(4) << price_to_double(p);
    return oss.str();
}

std::string format_quantity(Quantity q) {
    return std::to_string(q);
}

}  // namespace aegis
