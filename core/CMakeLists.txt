add_library(aegis_core
    src/types.cpp
    src/memory_pool.cpp
    src/clock.cpp
    src/metrics.cpp
)
target_include_directories(aegis_core PUBLIC include)
target_link_libraries(aegis_core PUBLIC spdlog::spdlog nlohmann_json::nlohmann_json)
