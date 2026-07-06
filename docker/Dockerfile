# Build stage
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    build-essential cmake git g++ libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . .

RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
    -DAEGIS_BUILD_TESTS=ON \
    -DAEGIS_BUILD_BENCHMARKS=OFF \
    && cmake --build build -j$(nproc) \
    && cd build && ctest --output-on-failure

# Runtime stage
FROM ubuntu:22.04 AS runtime

RUN apt-get update && apt-get install -y libssl3 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/build/server/aegis-server /app/
RUN mkdir -p /app/data

EXPOSE 8080
ENV AEGIS_PORT=8080

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/app/aegis-server"]
