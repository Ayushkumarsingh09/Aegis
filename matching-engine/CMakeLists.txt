add_library(aegis_matching
    src/matching_engine.cpp
)
target_include_directories(aegis_matching PUBLIC include)
target_link_libraries(aegis_matching PUBLIC aegis_orderbook aegis_core)
