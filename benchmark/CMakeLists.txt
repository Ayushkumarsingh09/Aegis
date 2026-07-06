add_executable(aegis_benchmark
    order_throughput.cpp
    latency_benchmark.cpp
)
target_link_libraries(aegis_benchmark PRIVATE
    aegis_matching aegis_core benchmark::benchmark_main)
