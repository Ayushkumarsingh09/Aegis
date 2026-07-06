add_library(aegis_gateway
    src/api_server.cpp
    src/websocket_hub.cpp
)
target_include_directories(aegis_gateway PUBLIC include)
target_link_libraries(aegis_gateway PUBLIC
    aegis_core aegis_matching aegis_risk aegis_market_data
    httplib::httplib)
