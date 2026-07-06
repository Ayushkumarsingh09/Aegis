add_library(aegis_risk
    src/risk_engine.cpp
)
target_include_directories(aegis_risk PUBLIC include)
target_link_libraries(aegis_risk PUBLIC aegis_core)
