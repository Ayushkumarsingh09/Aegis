add_library(aegis_market_data
    src/publisher.cpp
    src/recorder.cpp
    src/replay.cpp
)
target_include_directories(aegis_market_data PUBLIC include)
target_link_libraries(aegis_market_data PUBLIC aegis_core aegis_matching)
