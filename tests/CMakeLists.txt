add_executable(aegis_tests
    unit/test_order_book.cpp
    unit/test_matching_engine.cpp
    unit/test_risk_engine.cpp
    unit/test_market_data.cpp
    integration/test_exchange_flow.cpp
)
target_link_libraries(aegis_tests PRIVATE
    aegis_matching aegis_risk aegis_market_data aegis_gateway
    GTest::gtest_main)
include(GoogleTest)
gtest_discover_tests(aegis_tests)
