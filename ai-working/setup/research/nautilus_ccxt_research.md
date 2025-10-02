# Nautilus Trader + CCXT Integration Research

## Executive Summary

This document provides a comprehensive analysis of the Nautilus Trader platform, its architecture, setup requirements, and a detailed plan for integrating the CCXT (CryptoCurrency eXchange Trading) library as an adapter.

**Date:** January 2025  
**Status:** Research Phase  
**Goal:** Understand Nautilus Trader architecture and create a roadmap for CCXT adapter integration

---

## 1. What is Nautilus Trader?

### Overview
Nautilus Trader is a **high-performance, production-grade algorithmic trading platform** designed for quantitative traders. It's built with a unique hybrid architecture:

- **Core Engine:** Written in Rust for maximum performance and safety
- **User Interface:** Python-native environment for strategy development
- **Philosophy:** "Write once, run anywhere" - same code for backtesting and live trading

### Key Features (Beginner-Friendly Explanation)

1. **Event-Driven Architecture**
   - Think of it like a restaurant kitchen: orders come in (events), chefs process them (handlers), and dishes go out (actions)
   - Every market update, order fill, or price change is an "event" that triggers specific actions

2. **Backtesting & Live Trading Parity**
   - You write your trading strategy once
   - Test it on historical data (backtesting)
   - Deploy it live with zero code changes
   - This eliminates the "it worked in testing but failed live" problem

3. **Multi-Venue Support**
   - Trade on multiple exchanges simultaneously
   - Each exchange connection is called an "adapter"
   - Adapters translate exchange-specific APIs into Nautilus's unified language

4. **Asset Class Agnostic**
   - Works with: Crypto, Stocks, Futures, Options, Forex, Sports Betting
   - The core system doesn't care what you're trading - it just processes events

---

## 2. Nautilus Trader Architecture

### System Components (Simplified)

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Trading Strategy                     │
│              (Python code you write)                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                  Nautilus Core Engine                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Message    │  │    Cache     │  │  Portfolio   │      │
│  │     Bus      │  │   (State)    │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                      Adapters Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Binance  │  │  Bybit   │  │   IB     │  │  CCXT    │   │
│  │ Adapter  │  │ Adapter  │  │ Adapter  │  │ (Future) │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼────────────┼─────────────┼──────────────┼──────────┘
        │            │              │              │
┌───────▼────────────▼──────────────▼──────────────▼──────────┐
│              External Exchange APIs                          │
│    (Binance.com, Bybit.com, Interactive Brokers, etc.)      │
└─────────────────────────────────────────────────────────────┘
```

### How Data Flows

1. **Market Data Flow (Incoming)**
   ```
   Exchange → Adapter → Message Bus → Cache → Strategy
   ```
   - Exchange sends price update
   - Adapter converts it to Nautilus format
   - Message bus distributes it
   - Cache stores current state
   - Strategy receives update and makes decisions

2. **Order Flow (Outgoing)**
   ```
   Strategy → Message Bus → Execution Client → Adapter → Exchange
   ```
   - Strategy decides to buy/sell
   - Creates order object
   - Execution client validates it
   - Adapter translates to exchange format
   - Exchange executes the order

---

## 3. Adapter Architecture Deep Dive

### What is an Adapter?

An adapter is a **translator** between Nautilus and an exchange. It has two main jobs:

1. **Data Adapter:** Fetches market data (prices, order books, trades)
2. **Execution Adapter:** Sends orders and manages positions

### Adapter Structure

Every Nautilus adapter has two layers:

#### Layer 1: Rust Core (Performance Layer)
Located in: `crates/adapters/your_adapter/`

**Components:**
- **HTTP Client:** Makes REST API calls to the exchange
- **WebSocket Client:** Maintains real-time data streams
- **Parsers:** Convert exchange JSON to Nautilus data structures
- **Python Bindings:** Expose Rust functions to Python

**Why Rust?**
- 10-100x faster than pure Python
- Memory safe (no crashes from memory bugs)
- Handles thousands of messages per second

#### Layer 2: Python Integration (User-Facing Layer)
Located in: `nautilus_trader/adapters/your_adapter/`

**Components:**
- **config.py:** User configuration (API keys, settings)
- **providers.py:** Loads instrument definitions (what can be traded)
- **data.py:** Market data client (prices, order books)
- **execution.py:** Order execution client (buy/sell orders)
- **factories.py:** Creates Nautilus objects from exchange data

### Existing Adapter Examples

| Adapter | Status | Complexity | Good Reference For |
|---------|--------|------------|-------------------|
| Binance | Stable | High | Full-featured implementation |
| Bybit | Stable | Medium | Modern WebSocket patterns |
| BitMEX | Beta | Medium | HTTP client patterns |
| OKX | Beta | Medium | Configuration patterns |
| Interactive Brokers | Stable | High | Multi-asset support |

---

## 4. What is CCXT?

### Overview
CCXT (CryptoCurrency eXchange Trading Library) is a **unified API library** that supports 100+ cryptocurrency exchanges.

### Key Features

1. **Unified Interface**
   - One API to rule them all
   - Same code works across 100+ exchanges
   - Example: `exchange.fetch_ticker('BTC/USDT')` works on any exchange

2. **Comprehensive Coverage**
   - Supports: Binance, Coinbase, Kraken, Bitfinex, Huobi, and 95+ more
   - Handles: Spot, Futures, Margin, Options trading
   - Provides: Market data, order management, account info

3. **Language Support**
   - Python (what we'll use)
   - JavaScript/TypeScript
   - PHP, C#, Go

### Why Integrate CCXT with Nautilus?

**Problem:** Building individual adapters for 100+ exchanges is time-consuming

**Solution:** Create ONE CCXT adapter that provides access to ALL CCXT-supported exchanges

**Benefits:**
- ✅ Instant support for 100+ exchanges
- ✅ CCXT team maintains exchange-specific code
- ✅ Nautilus users get more trading venues
- ✅ Reduced maintenance burden

**Trade-offs:**
- ⚠️ Slightly slower than native Rust adapters
- ⚠️ Less control over low-level optimizations
- ⚠️ Dependent on CCXT's update cycle

---

## 5. Historical Context: CCXT in Nautilus

### Discovery from Codebase

The RELEASES.md file reveals that **CCXT was previously integrated** but was **removed in release #428**.

**Historical References:**
```
- Removed CCXT adapter (#428)
- Fixed millis to nanos in CCXTExecutionClient
- CCXT TICK_SIZE precision mode - size precisions (BitMEX, FTX)
- CCXT data and execution clients regarding instrument_id vs symbol naming
- CCXT precision parsing bug
```

### Why Was It Removed?

Likely reasons (based on bug references):
1. **Precision Issues:** Converting between CCXT and Nautilus number formats
2. **Naming Conflicts:** `instrument_id` vs `symbol` inconsistencies
3. **Maintenance Burden:** Keeping up with CCXT API changes
4. **Performance:** Python-based CCXT slower than Rust adapters

### Lessons for New Integration

1. **Precision Handling:** Must carefully convert decimals and timestamps
2. **ID Mapping:** Need clear strategy for instrument identification
3. **Error Handling:** CCXT exceptions must map to Nautilus error types
4. **Testing:** Extensive testing across multiple exchanges
5. **Documentation:** Clear user guide for CCXT-specific quirks

---

## 6. System Requirements & Setup

### Supported Platforms

| Platform | Python Versions | Rust Version | Status |
|----------|----------------|--------------|--------|
| Linux (x86_64) | 3.11-3.13 | 1.90.0 | ✅ Fully Supported |
| Linux (ARM64) | 3.11-3.13 | 1.90.0 | ✅ Fully Supported |
| macOS (ARM64) | 3.11-3.13 | 1.90.0 | ✅ Fully Supported |
| Windows (x86_64) | 3.11-3.13 | 1.90.0 | ✅ Fully Supported |

### Development Tools Required

1. **Python Environment**
   - Python 3.11, 3.12, or 3.13
   - `uv` package manager (recommended)
   - Virtual environment support

2. **Rust Toolchain**
   - Rust 1.90.0 or later
   - `cargo` build tool
   - `rustup` for toolchain management

3. **Build Tools**
   - Cython 3.1.4 (for Python/Rust bindings)
   - C compiler (gcc/clang on Linux/Mac, MSVC on Windows)
   - Make (for build automation)

4. **Optional Services**
   - Docker (for local testing environment)
   - PostgreSQL (for data persistence)
   - Redis (for caching and message queuing)

### Installation Steps (Beginner-Friendly)

#### Step 1: Install Rust
```bash
# Linux/macOS
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env

# Windows
# Download and run: https://win.rustup.rs/x86_64

# Verify installation
rustc --version  # Should show: rustc 1.90.0 or later
```

#### Step 2: Install Python & uv
```bash
# Install uv (Python package manager)
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify Python version
python --version  # Should be 3.11, 3.12, or 3.13
```

#### Step 3: Clone and Setup Nautilus
```bash
# Clone the repository
git clone https://github.com/nautechsystems/nautilus_trader.git
cd nautilus_trader

# Install dependencies and build (debug mode for development)
make install-debug

# Or manually:
uv sync --active --all-groups --all-extras
BUILD_MODE=debug uv run --no-sync build.py
```

#### Step 4: Verify Installation
```bash
# Run tests to verify everything works
make test-unit

# Or start Python and import
python
>>> import nautilus_trader
>>> print(nautilus_trader.__version__)
```

---

## 7. Development Workflow

### Build Commands

```bash
# Full build (release mode - slow but optimized)
make build

# Debug build (fast, for development)
make build-debug

# Install dependencies only (no build)
make install-just-deps

# Clean everything and rebuild
make clean
make build-debug
```

### Testing Commands

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Run specific test file
pytest tests/unit_tests/adapters/test_binance.py
```

### Code Quality Commands

```bash
# Format code
make format

# Run linters
make pre-commit

# Type checking
make type-check
```

---

## 8. CCXT Adapter Integration Plan

### Phase 1: Research & Design ✅ (Current Phase)

**Objectives:**
- ✅ Understand Nautilus architecture
- ✅ Understand CCXT capabilities
- ✅ Review historical CCXT integration
- ✅ Design adapter architecture

**Deliverables:**
- ✅ This research document
- 🔄 Detailed implementation plan (next)
- 🔄 Architecture diagrams

### Phase 2: Foundation Setup

**Objectives:**
- Create CCXT adapter directory structure
- Set up configuration classes
- Implement basic instrument provider
- Add CCXT to project dependencies

**Tasks:**
1. Create `nautilus_trader/adapters/ccxt/` directory
2. Create `crates/adapters/ccxt/` directory (if needed)
3. Add CCXT to `pyproject.toml` as optional dependency
4. Create configuration classes
5. Implement basic logging and error handling

**Estimated Time:** 2-3 days

### Phase 3: Data Client Implementation

**Objectives:**
- Implement market data fetching
- Support historical data requests
- Handle real-time data streams (if CCXT supports)

**Tasks:**
1. Implement `CCXTDataClient` class
2. Add methods for:
   - `fetch_ticker()` - Current price data
   - `fetch_order_book()` - Order book snapshots
   - `fetch_trades()` - Recent trade history
   - `fetch_ohlcv()` - Historical bar data
3. Implement data parsing and conversion
4. Add timestamp normalization (CCXT uses milliseconds, Nautilus uses nanoseconds)
5. Write unit tests

**Estimated Time:** 5-7 days

### Phase 4: Execution Client Implementation

**Objectives:**
- Implement order submission
- Handle order status updates
- Manage positions and balances

**Tasks:**
1. Implement `CCXTExecutionClient` class
2. Add methods for:
   - `submit_order()` - Place new orders
   - `cancel_order()` - Cancel existing orders
   - `modify_order()` - Modify orders (if supported)
   - `fetch_balance()` - Get account balances
   - `fetch_positions()` - Get open positions
3. Implement order state reconciliation
4. Add error handling for exchange-specific errors
5. Write unit tests

**Estimated Time:** 7-10 days

### Phase 5: Instrument Provider Implementation

**Objectives:**
- Load instrument definitions from exchanges
- Handle instrument metadata (tick size, lot size, etc.)
- Support multiple asset types

**Tasks:**
1. Implement `CCXTInstrumentProvider` class
2. Fetch market information from CCXT
3. Convert CCXT market data to Nautilus instruments
4. Handle precision and size constraints
5. Implement instrument caching
6. Write unit tests

**Estimated Time:** 3-5 days

### Phase 6: Integration Testing

**Objectives:**
- Test with multiple exchanges
- Verify data accuracy
- Test order execution flow
- Performance testing

**Tasks:**
1. Set up test accounts on 3-5 exchanges
2. Create integration test suite
3. Test market data accuracy
4. Test order execution (paper trading)
5. Test error handling and recovery
6. Performance benchmarking

**Estimated Time:** 5-7 days

### Phase 7: Documentation & Examples

**Objectives:**
- Write user documentation
- Create example strategies
- Document known limitations

**Tasks:**
1. Write `docs/integrations/ccxt.md`
2. Create example configuration files
3. Write beginner-friendly tutorial
4. Document exchange-specific quirks
5. Create troubleshooting guide

**Estimated Time:** 3-4 days

### Phase 8: Production Readiness

**Objectives:**
- Code review and refinement
- Performance optimization
- Security audit
- Release preparation

**Tasks:**
1. Code review with Nautilus maintainers
2. Address feedback and issues
3. Optimize critical paths
4. Security review (API key handling)
5. Prepare release notes
6. Submit pull request

**Estimated Time:** 3-5 days

---

## 9. Technical Challenges & Solutions

### Challenge 1: Timestamp Precision

**Problem:** CCXT uses milliseconds, Nautilus uses nanoseconds

**Solution:**
```python
def ccxt_to_nautilus_timestamp(ccxt_ms: int) -> int:
    """Convert CCXT millisecond timestamp to Nautilus nanoseconds."""
    return ccxt_ms * 1_000_000  # ms to ns
```

### Challenge 2: Instrument ID Mapping

**Problem:** CCXT uses `BTC/USDT`, Nautilus uses `InstrumentId`

**Solution:**
```python
def ccxt_symbol_to_instrument_id(symbol: str, exchange: str) -> InstrumentId:
    """Convert CCXT symbol to Nautilus InstrumentId."""
    # BTC/USDT -> BTCUSDT.BINANCE
    base, quote = symbol.split('/')
    symbol_nautilus = f"{base}{quote}"
    return InstrumentId(Symbol(symbol_nautilus), Venue(exchange.upper()))
```

### Challenge 3: Precision Handling

**Problem:** Different exchanges have different precision rules

**Solution:**
- Use CCXT's `market['precision']` data
- Implement rounding functions
- Validate order sizes before submission

### Challenge 4: Async/Await Compatibility

**Problem:** CCXT has both sync and async versions

**Solution:**
- Use `ccxt.async_support` for async operations
- Integrate with Nautilus's event loop
- Handle connection pooling properly

### Challenge 5: Error Handling

**Problem:** CCXT raises various exception types

**Solution:**
```python
# Map CCXT exceptions to Nautilus exceptions
CCXT_ERROR_MAP = {
    ccxt.NetworkError: NautilusNetworkError,
    ccxt.ExchangeError: NautilusExchangeError,
    ccxt.InvalidOrder: NautilusInvalidOrder,
    # ... etc
}
```

---

## 10. Architecture Decisions

### Decision 1: Pure Python vs Rust Core

**Options:**
A) Pure Python adapter (wraps CCXT directly)
B) Rust core with CCXT bindings

**Decision:** Start with **Pure Python (Option A)**

**Rationale:**
- CCXT is Python-native
- Faster initial development
- Easier to maintain
- Can optimize to Rust later if needed

### Decision 2: Single Adapter vs Per-Exchange Adapters

**Options:**
A) One CCXT adapter that works with all exchanges
B) Separate adapter for each CCXT exchange

**Decision:** **Single unified adapter (Option A)**

**Rationale:**
- Leverages CCXT's unified API
- Easier maintenance
- Users configure exchange via settings
- Consistent behavior across exchanges

### Decision 3: WebSocket Support

**Options:**
A) Use CCXT Pro (paid, has WebSocket support)
B) Use CCXT free (REST only)
C) Hybrid: CCXT for execution, native WebSocket for data

**Decision:** Start with **CCXT free (Option B)**, document upgrade path

**Rationale:**
- Free version accessible to all users
- REST sufficient for many strategies
- Can add CCXT Pro support later
- Document how to use native adapters for high-frequency needs

---

## 11. Configuration Design

### User-Facing Configuration

```python
# Example: nautilus_trader/adapters/ccxt/config.py

from nautilus_trader.config import LiveDataClientConfig, LiveExecClientConfig

class CCXTDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for CCXT Data Client.
    
    Parameters
    ----------
    exchange_id : str
        The CCXT exchange ID (e.g., 'binance', 'coinbase', 'kraken')
    api_key : str, optional
        Exchange API key (required for private endpoints)
    api_secret : str, optional
        Exchange API secret
    api_password : str, optional
        Exchange API password (required by some exchanges like Coinbase)
    sandbox : bool, default False
        Use exchange testnet/sandbox if available
    rate_limit : bool, default True
        Enable CCXT's built-in rate limiting
    timeout : int, default 30000
        Request timeout in milliseconds
    """
    exchange_id: str
    api_key: str | None = None
    api_secret: str | None = None
    api_password: str | None = None
    sandbox: bool = False
    rate_limit: bool = True
    timeout: int = 30000

class CCXTExecClientConfig(LiveExecClientConfig, frozen=True):
    """Configuration for CCXT Execution Client."""
    exchange_id: str
    api_key: str
    api_secret: str
    api_password: str | None = None
    sandbox: bool = False
    rate_limit: bool = True
    timeout: int = 30000
```

### Usage Example

```python
# User's strategy configuration
from nautilus_trader.adapters.ccxt.config import CCXTDataClientConfig

config = CCXTDataClientConfig(
    exchange_id='binance',
    api_key='your_api_key',
    api_secret='your_api_secret',
    sandbox=True,  # Use testnet
)
```

---

## 12. Testing Strategy

### Unit Tests
- Test each method in isolation
- Mock CCXT responses
- Test error handling
- Test data conversions

### Integration Tests
- Test with CCXT's test exchanges
- Test with real exchange testnets
- Test order lifecycle
- Test data accuracy

### Performance Tests
- Measure latency
- Test throughput
- Memory usage profiling
- Compare with native adapters

### Exchange-Specific Tests
- Test with 5-10 popular exchanges
- Document exchange-specific quirks
- Test edge cases per exchange

---

## 13. Documentation Requirements

### User Documentation

1. **Integration Guide** (`docs/integrations/ccxt.md`)
   - What is CCXT
   - Supported exchanges
   - Installation instructions
   - Configuration examples
   - Limitations and trade-offs

2. **Tutorial** (`docs/tutorials/ccxt_quickstart.md`)
   - Step-by-step setup
   - First strategy with CCXT
   - Common pitfalls
   - Troubleshooting

3. **API Reference**
   - Auto-generated from docstrings
   - Configuration options
   - Method signatures

### Developer Documentation

1. **Architecture Document**
   - Design decisions
   - Code structure
   - Extension points

2. **Contribution Guide**
   - How to add exchange support
   - Testing requirements
   - Code style

---

## 14. Success Criteria

### Minimum Viable Product (MVP)

- ✅ Supports 3+ major exchanges (Binance, Coinbase, Kraken)
- ✅ Can fetch market data (tickers, order books, trades)
- ✅ Can submit and cancel orders
- ✅ Passes all unit tests
- ✅ Has basic documentation

### Production Ready

- ✅ Supports 10+ exchanges
- ✅ Has comprehensive error handling
- ✅ Passes integration tests on real exchanges
- ✅ Has performance benchmarks
- ✅ Has complete documentation
- ✅ Code reviewed and approved

### Long-Term Goals

- ✅ Supports 50+ exchanges
- ✅ CCXT Pro integration (WebSocket support)
- ✅ Community contributions for exchange-specific features
- ✅ Regular maintenance and updates

---

## 15. Risk Assessment

### High Risk

1. **CCXT API Changes**
   - **Risk:** CCXT updates may break our adapter
   - **Mitigation:** Pin CCXT version, test before upgrading

2. **Exchange API Changes**
   - **Risk:** Exchanges change APIs, CCXT may lag
   - **Mitigation:** Document known issues, provide workarounds

### Medium Risk

1. **Performance**
   - **Risk:** Python CCXT slower than Rust adapters
   - **Mitigation:** Document performance characteristics, optimize critical paths

2. **Precision Errors**
   - **Risk:** Rounding errors in price/quantity conversions
   - **Mitigation:** Extensive testing, use Decimal types

### Low Risk

1. **Maintenance Burden**
   - **Risk:** Keeping up with CCXT updates
   - **Mitigation:** Active community, automated testing

---

## 16. Next Steps

### Immediate Actions (This Week)

1. ✅ Complete this research document
2. 🔄 Create detailed implementation plan
3. 🔄 Set up development environment
4. 🔄 Create adapter directory structure
5. 🔄 Write initial configuration classes

### Short-Term (Next 2 Weeks)

1. Implement instrument provider
2. Implement basic data client
3. Write unit tests
4. Test with 2-3 exchanges

### Medium-Term (Next Month)

1. Implement execution client
2. Integration testing
3. Write documentation
4. Code review

### Long-Term (Next Quarter)

1. Production deployment
2. Community feedback
3. Performance optimization
4. Additional exchange support

---

## 17. Resources & References

### Official Documentation

- **Nautilus Trader Docs:** https://nautilustrader.io/docs/
- **CCXT Documentation:** https://docs.ccxt.com/
- **Nautilus GitHub:** https://github.com/nautechsystems/nautilus_trader
- **CCXT GitHub:** https://github.com/ccxt/ccxt

### Key Files to Study

- `nautilus_trader/adapters/binance/` - Reference adapter implementation
- `nautilus_trader/adapters/_template/` - Adapter template
- `docs/developer_guide/adapters.md` - Adapter development guide
- `docs/integrations/index.md` - Integration guidelines

### Community Resources

- **Nautilus Discord:** https://discord.gg/NautilusTrader
- **CCXT Discord:** https://discord.gg/ccxt
- **GitHub Discussions:** For questions and feedback

---

## 18. Glossary (Beginner-Friendly)

**Adapter:** A translator that connects Nautilus to an exchange

**Instrument:** A tradable asset (e.g., BTC/USDT, AAPL stock)

**Venue:** An exchange or trading platform (e.g., Binance, Coinbase)

**Order Book:** List of buy and sell orders at different prices

**Tick:** The smallest price movement allowed for an instrument

**Lot Size:** The minimum quantity you can trade

**Execution:** The process of placing and managing orders

**Backtesting:** Testing a strategy on historical data

**Event-Driven:** System reacts to events (price changes, order fills) rather than running continuously

**Message Bus:** Internal communication system that distributes events

**Cache:** Temporary storage for current market state

**Portfolio:** Collection of your positions and balances

**Position:** An open trade (e.g., "I'm long 1 BTC")

**Precision:** Number of decimal places allowed (e.g., 0.00000001 BTC)

---

## Conclusion

This research document provides a comprehensive foundation for integrating CCXT with Nautilus Trader. The integration will:

1. **Expand Access:** Give Nautilus users access to 100+ exchanges
2. **Reduce Complexity:** One adapter instead of 100 individual adapters
3. **Leverage Expertise:** Use CCXT's battle-tested exchange integrations
4. **Maintain Quality:** Follow Nautilus's high standards for reliability

The next step is to create a detailed implementation plan and begin Phase 2: Foundation Setup.

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Author:** AI Development Agent  
**Status:** Complete - Ready for Implementation Planning
