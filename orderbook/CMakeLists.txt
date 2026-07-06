add_library(aegis_orderbook
    src/order_book.cpp
)
target_include_directories(aegis_orderbook PUBLIC include)
target_link_libraries(aegis_orderbook PUBLIC aegis_core)
