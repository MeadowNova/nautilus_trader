# Nautilus Trader - Architecture & Core Concepts

**Last Updated:** October 2025

## Design Philosophy

NautilusTrader employs key architectural patterns:
- **Domain Driven Design (DDD)**: Trading domain modeling
- **Event-Driven Architecture**: Message-based communication
- **Messaging Patterns**: Pub/Sub, Req/Rep, point-to-point
- **Ports and Adapters**: Modular component integration
- **Crash-Only Design**: Robust failure handling

### Quality Attributes (Priority Order)
1. Reliability
2. Performance  
3. Modularity
4. Testability
5. Maintainability
6. Deployability

## Core Components

### NautilusKernel
Central orchestration component:
- Initializes and manages all system components
- Configures messaging infrastructure
- Maintains environment-specific behaviors
- Coordinates shared resources and lifecycle
- Provides unified entry point

### MessageBus
Backbone of inter-component communication:
- **Publish/Subscribe**: Broadcasting events/data
- **Request/Response**: Operations requiring acknowledgment
- **Command/Event**: Triggering actions and notifying changes
- **Optional Redis persistence**: Durability and restart capabilities

### Cache
High-performance in-memory storage:
- Stores instruments, accounts, orders, positions
- Provides fast fetching for trading components
- Maintains consistent state across system
- Optimized read/write access patterns

### DataEngine
Processes and routes market data:
- Handles multiple data types (quotes, trades, bars, order books, custom)
- Routes data to consumers based on subscriptions
- Manages data flow from external to internal components

### ExecutionEngine
Manages order lifecycle:
- Routes trading commands to adapters
- Tracks order and position states
- Coordinates with risk management
- Handles execution reports and fills
- Reconciles external execution state

### RiskEngine
Comprehensive risk management:
- Pre-trade risk checks and validation
- Position and exposure monitoring
- Real-time risk calculations
- Configurable risk rules and limits

## Environment Contexts

Three main operating environments:

1. **Backtest**: Historical data + simulated venues
2. **Sandbox**: Real-time data + simulated venues
3. **Live**: Real-time data + live venues (paper or real accounts)

### Common Core
- Shares maximum code between all environments
- Formal

ized in `system` subpackage
- `NautilusKernel` provides common core system
- *Ports and adapters* enables modular integration

## Data Flow Pattern

1. **External Data Ingestion**: Via venue-specific `DataClient` adapters (normalized)
2. **Data Processing**: `DataEngine` handles processing
3. **Caching**: Stored in high-performance `Cache`
4. **Event Publishing**: Published to `MessageBus`
5. **Consumer Delivery**: Delivered to subscribed Actors/Strategies

## Execution Flow Pattern

1. **Command Generation**: Strategies create trading commands
2. **Command Publishing**: Sent through `MessageBus`
3. **Risk Validation**: `RiskEngine` validates against rules
4. **Execution Routing**: `ExecutionEngine` routes to venues
5. **External Submission**: `ExecutionClient` submits to venues
6. **Event Flow Back**: Order events flow back through system
7. **State Updates**: Portfolio and positions updated

## Component State Machine

All components follow finite state machine:
- **PRE_INITIALIZED**: Created but not wired up
- **READY**: Configured and wired, not running
- **RUNNING**: Actively processing messages
- **STOPPED**: Gracefully stopped
- **DEGRADED**: Running with reduced functionality
- **FAULTED**: Critical error, cannot continue
- **DISPOSED**: Cleaned up, resources released

## Framework Organization

### Core / Low-Level
- `core`: Constants, functions, low-level components
- `common`: Common parts for assembling components
- `network`: Base networking clients
- `serialization`: Serialization base + implementations
- `model`: Rich trading domain model

### Components
- `accounting`: Account types and management
- `adapters`: Integration adapters (brokers, exchanges)
- `analysis`: Performance statistics and analysis
- `cache`: Common caching infrastructure
- `data`: Data stack and tooling
- `execution`: Execution stack
- `indicators`: Efficient indicators and analyzers
- `persistence`: Data storage, cataloging, retrieval
- `portfolio`: Portfolio management
- `risk`: Risk components and tooling
- `trading`: Trading domain components

### System Implementations
- `backtest`: Backtesting engine and node
- `live`: Live engine, clients, node
- `system`: Core kernel common across environments

## Code Structure

### Dependency Flow
```
Python/Cython (nautilus_trader)
         ↕ C API
    Rust (nautilus_core)
```

- Foundation: Rust crates in `crates/` directory
- Production code: Python/Cython in `nautilus_trader/`
- Python bindings: Via static linking at compile time

### Type Safety
- **Rust**: Type and memory safe (guaranteed by compiler)
- **Cython**: Type safe at C level (compile + runtime)
- Passing invalid types → `TypeError` at runtime
- Passing `None` to non-optional → `ValueError` at runtime

## Messaging

- Single-threaded by design for efficiency
- No context switching overhead
- Deterministic synchronous message consumption
- Similar to actor model
- Inspired by LMAX disruptor pattern

## Performance Notes

- Optimized to run efficiently on single thread
- Research showed context switching overhead didn't improve performance
- Each component consumes messages deterministically
- Similar to LMAX exchange architecture

## Best Practices

1. **Process Isolation**: Run each trader instance in separate process for optimal performance
2. **Type Safety**: Leverage type system for correctness
3. **Event-Driven**: Design strategies around event handlers
4. **Stateless Messages**: Messages should be self-contained
5. **Single Thread**: Don't introduce threading unless absolutely necessary
