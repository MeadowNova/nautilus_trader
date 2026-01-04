# Changelog

All notable changes to the Moomoo RL Paper Trading System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-09

### Added
- **Moomoo Adapter**: Complete adapter for NautilusTrader v1.221.0
  - `MoomooDataClient` for market data streaming
  - `MoomooExecClient` for order execution
  - `MoomooInstrumentProvider` for instrument metadata
  - Full reconciliation support (orders, fills, positions)

- **RL Framework**: Reinforcement learning infrastructure
  - State builder (75-dimensional state vector)
  - Reward calculator with "seeing out" bonus
  - Prioritized experience replay buffer
  - N-step TD credit assignment
  - Elastic Weight Consolidation (anti-forgetting)
  - Training orchestrator with background training loop

- **Trading Strategies**:
  - RL Pairs Trading (XLE/XLF) - Mean reversion with z-score signals
  - RL Momentum Breakout (NVDA, AMD, META) - Trend following with volume confirmation

- **Infrastructure**:
  - Docker Compose setup (PostgreSQL, Redis, Prometheus, Grafana)
  - Grafana dashboards (Live Trading Monitor, RL Training Metrics, System Health)
  - Prometheus metrics collection
  - Log aggregation and rotation

- **Documentation**:
  - Complete documentation suite (README, QUICKSTART, SETUP, CONFIGURATION, STRATEGIES, MONITORING, TROUBLESHOOTING, ARCHITECTURE, API_REFERENCE)
  - Code examples and templates
  - Troubleshooting guide with common issues

### Fixed

#### 2025-12-09: Critical Adapter Fixes

**Issue 1: Bar Subscription Type Error**
- **Problem**: Strategies were passing `InstrumentId` to `subscribe_bars()` instead of `BarType`
- **Error**: `TypeError: Argument 'bar_type' has incorrect type (expected BarType, got InstrumentId)`
- **Fix**: Updated strategies to create `BarType` objects using `BarType.from_str()`
- **Files**: `ajk_strategies/rl_strategies/pairs_trading.py`, `ajk_strategies/rl_strategies/momentum_breakout.py`

**Issue 2: Data Client Method Signatures**
- **Problem**: Moomoo data client had incorrect method signatures (raw `InstrumentId` instead of command objects)
- **Error**: `'SubscribeQuoteTicks' object has no attribute 'symbol'`
- **Fix**: Updated all subscription methods to accept command objects
  - `_subscribe_quote_ticks(command: SubscribeQuoteTicks)`
  - `_subscribe_trade_ticks(command: SubscribeTradeTicks)`
  - `_subscribe_bars(command: SubscribeBars)`
- **Files**: `nautilus_trader/adapters/moomoo/data.py`

**Issue 3: Missing Bar Subscription Method**
- **Problem**: Data client missing `_subscribe_bars()` coroutine
- **Error**: `NotImplementedError: implement the '_subscribe_bars' coroutine`
- **Fix**: Implemented `_subscribe_bars()` method that registers bar subscriptions and adds underlying instrument to quote subscriptions
- **Files**: `nautilus_trader/adapters/moomoo/data.py`

**Issue 4: Missing Reconciliation Methods**
- **Problem**: Execution client missing reconciliation methods required by NautilusTrader
- **Error**: `NotImplementedError: method 'generate_order_status_reports' must be implemented`
- **Fix**: Implemented three reconciliation methods:
  - `generate_order_status_reports()` - Queries `order_list_query()`
  - `generate_fill_reports()` - Queries `deal_list_query()`
  - `generate_position_status_reports()` - Queries `position_list_query()`
- **Files**: `nautilus_trader/adapters/moomoo/execution.py`

**Issue 5: Position Sizing**
- **Problem**: Default position sizes (8-10%) too large for conservative paper trading
- **Fix**: Reduced to 2% per position (4% total for pairs strategy)
- **Rationale**: Conservative sizing during initial validation phase
- **Files**: `scripts/start_paper_trading_moomoo.py`, strategy configs

### Changed
- Position sizes reduced from 8-10% to 2% for safer paper trading
- Experience buffer capacity increased to 100,000 (from 50,000)
- Epsilon decay adjusted for slower exploration reduction
- Log level defaults to INFO (was DEBUG)

### Known Issues

**Market Data Permissions** (Not a code issue)
- **Issue**: "No right to subscribe the quote for US.XLE"
- **Cause**: US market real-time quote permissions not enabled in Moomoo account
- **Solution**: Enable in Moomoo app → Settings → Quotes Permission → US Market Real-time Quotes
- **Documentation**: See [CONFIGURATION.md](CONFIGURATION.md#market-data-permissions)

**OpenD Session Timeout** (Expected behavior)
- **Issue**: Sessions expire after 24 hours
- **Solution**: Restart OpenD gateway daily or enable auto-reconnect
- **Workaround**: Run OpenD in screen/tmux session

## [0.9.0] - 2025-12-05

### Added
- Initial project setup
- Demo strategies (backtested)
- Risk management framework
- Strategy templates

### In Progress
- Moomoo adapter development
- RL framework implementation
- Infrastructure setup

## Upgrade Guide

### From 0.9.0 to 1.0.0

**Breaking Changes:**

1. **Strategy Bar Subscriptions**
   ```python
   # Old (WRONG)
   self.subscribe_bars(self.instrument_a)

   # New (CORRECT)
   bar_type_a = BarType.from_str(f"{self.instrument_a}-1-MINUTE-LAST-EXTERNAL")
   self.subscribe_bars(bar_type_a)
   ```

2. **Data Client Method Signatures**
   - If you have custom strategies using data subscriptions, update to use command objects
   - See [API_REFERENCE.md](API_REFERENCE.md#data-access) for examples

3. **Position Sizing**
   - Default position sizes reduced to 2%
   - Update configs if you want different sizing

**Non-Breaking Changes:**

- Experience buffer capacity increased (automatic)
- Reconciliation methods added (automatic)
- Logging improvements (automatic)

**Migration Steps:**

1. Update strategy bar subscriptions (see above)
2. Rebuild NautilusTrader: `make install-debug`
3. Update configs if needed
4. Test with paper trading before live

## Future Roadmap

### v1.1.0 (Planned: Q1 2026)
- [ ] Add covered call strategy
- [ ] Multi-timeframe analysis
- [ ] Advanced RL algorithms (SAC, TD3)
- [ ] Portfolio optimization
- [ ] Automated parameter tuning

### v1.2.0 (Planned: Q2 2026)
- [ ] Live trading support (after 4+ weeks paper trading validation)
- [ ] Multi-account management
- [ ] Risk dashboard improvements
- [ ] Alert system (email, SMS)
- [ ] Performance analytics dashboard

### v2.0.0 (Planned: Q3 2026)
- [ ] Multi-broker support (Interactive Brokers, Alpaca)
- [ ] Options trading support
- [ ] Advanced order types (iceberg, TWAP, VWAP)
- [ ] Backtesting framework improvements
- [ ] Cloud deployment (AWS, GCP)

## Versioning

- **Major version** (X.0.0): Breaking changes, major features
- **Minor version** (0.X.0): New features, backward compatible
- **Patch version** (0.0.X): Bug fixes, minor improvements

## Deprecation Policy

- Features marked as deprecated will be removed in the next major version
- Minimum 3 months notice before removal
- Deprecation warnings in logs and documentation

**Current Deprecations:** None

## Support

- **Issues**: https://github.com/nautechsystems/nautilus_trader/issues
- **Documentation**: See [README.md](README.md) for documentation links
- **Moomoo API**: https://www.moomoo.com/api

---

**Note:** This project is in active development. Always paper trade new releases for 30+ days before risking real capital.
