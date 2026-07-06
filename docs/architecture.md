# Architecture

## Overview

Aegis Exchange is a modular electronic trading system designed for ultra-low latency order matching with production-grade risk controls and market data distribution.

## Component Diagram

```mermaid
graph TB
    subgraph Client Layer
        DASH[Dashboard]
        SDK[Python SDK]
        EXT[External Clients]
    end

    subgraph Gateway Layer
        API[REST API Server]
        SSE[SSE Stream]
        MET[Metrics /metrics]
    end

    subgraph Core Engine
        ME[Matching Engine]
        OB[Order Book]
        RE[Risk Engine]
    end

    subgraph Market Data
        PUB[Publisher]
        REC[Recorder]
        REP[Replay Engine]
    end

    DASH --> API
    SDK --> API
    EXT --> API
    API --> ME
    API --> RE
    ME --> OB
    ME --> PUB
    RE --> API
    PUB --> SSE
    PUB --> REC
    REC --> REP
    MET --> PUB
```

## Order Flow Sequence

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant R as Risk Engine
    participant M as Matching Engine
    participant B as Order Book
    participant P as Publisher

    C->>G: POST /api/v1/orders
    G->>R: validate_order()
    alt Risk Rejected
        R-->>G: rejected
        G-->>C: 200 REJECTED
    else Risk Approved
        R-->>G: approved
        G->>M: submit_order()
        M->>B: match / rest
        M->>P: order events + trades
        P-->>G: broadcast
        G-->>C: 200 events
    end
```

## Order Book Design

The order book uses a two-level structure:

1. **Price Level Map**: `std::map<Price, PriceLevel>` sorted by price (descending for bids, ascending for asks)
2. **FIFO Queue**: Intrusive doubly-linked list per price level for time priority

```
Bids (descending)          Asks (ascending)
┌──────────────┐           ┌──────────────┐
│ 100.05 → [O1→O2→O3]     │ 100.10 → [O4]│
│ 100.04 → [O5]           │ 100.11 → [O6→O7]│
│ 100.03 → [O8]           │ 100.12 → [O9]│
└──────────────┘           └──────────────┘
```

### Memory Management

Orders are stored in a fixed-capacity `ObjectPool<Order, 1'000'000>`:
- O(1) allocation via free-list
- No heap allocations in the matching hot path
- Stable memory addresses via pool indices

## Matching Algorithm

1. **Validate** order parameters (price, quantity, tick size)
2. **Risk check** via validation pipeline
3. **Post-Only check**: reject if order would cross spread
4. **FOK check**: reject if full quantity cannot be filled
5. **Match** against contra side at best price (price-time priority)
6. **Rest** remainder on book (Limit/GTC) or **cancel** (IOC/Market)
7. **Check stop orders** triggered by trade prices
8. **Publish** events to market data layer

## Threading Model

- Single-threaded matching per instrument (no locks in hot path)
- Mutex-protected risk engine and market data publisher
- API server handles concurrent HTTP requests via thread pool (httplib)

## Data Types

| Type | Representation | Notes |
|------|---------------|-------|
| Price | `int64_t` | Fixed-point, scale 10,000 |
| Quantity | `int64_t` | Whole units |
| OrderId | `uint64_t` | Monotonic counter |
| SequenceNum | `uint64_t` | Per-event ordering |
| Timestamp | `int64_t` | Nanoseconds |
