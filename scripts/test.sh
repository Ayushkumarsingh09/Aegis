#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Aegis Exchange - Test ==="
cmake -B "$ROOT_DIR/build" -DCMAKE_BUILD_TYPE=Debug -DAEGIS_BUILD_TESTS=ON
cmake --build "$ROOT_DIR/build" -j"$(nproc 2>/dev/null || echo 4)"
cd "$ROOT_DIR/build" && ctest --output-on-failure
echo "All tests passed."
