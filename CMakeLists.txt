cmake_minimum_required(VERSION 3.20)
project(aegis-exchange VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(AEGIS_BUILD_TESTS "Build tests" ON)
option(AEGIS_BUILD_BENCHMARKS "Build benchmarks" ON)
option(AEGIS_ENABLE_SANITIZERS "Enable sanitizers" OFF)

if(AEGIS_ENABLE_SANITIZERS AND CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
endif()

include(FetchContent)
set(FETCHCONTENT_QUIET OFF)

FetchContent_Declare(spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG v1.14.1
    GIT_SHALLOW TRUE)
FetchContent_Declare(nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE)
FetchContent_Declare(httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.16.3
    GIT_SHALLOW TRUE)

if(AEGIS_BUILD_TESTS)
    FetchContent_Declare(googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
        GIT_SHALLOW TRUE)
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
endif()

if(AEGIS_BUILD_BENCHMARKS)
    FetchContent_Declare(benchmark
        GIT_REPOSITORY https://github.com/google/benchmark.git
        GIT_TAG v1.8.3
        GIT_SHALLOW TRUE)
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
endif()

FetchContent_MakeAvailable(spdlog nlohmann_json httplib)

if(NOT TARGET httplib::httplib)
    if(TARGET httplib)
        add_library(httplib::httplib ALIAS httplib)
    else()
        add_library(httplib_iface INTERFACE)
        target_include_directories(httplib_iface INTERFACE ${httplib_SOURCE_DIR})
        add_library(httplib::httplib ALIAS httplib_iface)
    endif()
endif()
if(AEGIS_BUILD_TESTS)
    FetchContent_MakeAvailable(googletest)
endif()
if(AEGIS_BUILD_BENCHMARKS)
    FetchContent_MakeAvailable(benchmark)
endif()

add_subdirectory(core)
add_subdirectory(orderbook)
add_subdirectory(matching-engine)
add_subdirectory(risk)
add_subdirectory(market-data)
add_subdirectory(gateway)
add_subdirectory(server)

if(AEGIS_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

if(AEGIS_BUILD_BENCHMARKS)
    add_subdirectory(benchmark)
endif()
