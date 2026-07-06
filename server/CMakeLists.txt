add_executable(aegis-server src/main.cpp)
target_link_libraries(aegis-server PRIVATE
    aegis_gateway aegis_matching aegis_risk aegis_market_data aegis_core
    spdlog::spdlog)

install(TARGETS aegis-server RUNTIME DESTINATION bin)
