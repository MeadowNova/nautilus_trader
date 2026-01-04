# Moomoo RL Paper Trading System

**A production-grade algorithmic trading system combining NautilusTrader, Moomoo OpenD API, and Reinforcement Learning**

## Overview

This system enables institutional-quality paper trading with real-time market data from Moomoo, powered by NautilusTrader's high-performance Rust/Python engine and enhanced with reinforcement learning that learns to "see out" winning trades.

### Key Features

- **Real Market Data**: Live US equity data via Moomoo OpenD API
- **Event-Driven Architecture**: Nanosecond precision Rust core with Python strategies
- **RL Enhancement**: Learns optimal entry/exit timing and captures more profitable moves
- **Production Infrastructure**: PostgreSQL, Prometheus, Grafana monitoring
- **Multiple Strategies**: Pairs trading, momentum breakout, with RL adaptations
- **Paper Trading**: Risk-free validation before live deployment

### System Status

**Version**: 1.0.0
**NautilusTrader**: v1.221.0
**Python**: 3.11-3.13
**Last Updated**: 2025-12-09

**Current Blocker**: US market data subscription permissions must be enabled in Moomoo app before trading. See [CONFIGURATION.md](CONFIGURATION.md#market-data-permissions).

## Quick Navigation

| Document | Purpose | Time to Read |
|----------|---------|--------------|
| [QUICKSTART.md](QUICKSTART.md) | Get trading in 10 minutes | 5 min |
| [SETUP.md](SETUP.md) | Detailed installation guide | 15 min |
| [CONFIGURATION.md](CONFIGURATION.md) | Moomoo account & permissions setup | 10 min |
| [STRATEGIES.md](STRATEGIES.md) | Trading strategies documentation | 20 min |
| [MONITORING.md](MONITORING.md) | Dashboards and debugging | 10 min |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions | As needed |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design deep-dive | 30 min |
| [API_REFERENCE.md](API_REFERENCE.md) | Code examples and API docs | As needed |
| [CHANGELOG.md](CHANGELOG.md) | Version history and fixes | As needed |

## Getting Started

### Prerequisites Checklist

- [ ] Moomoo trading account with paper trading enabled
- [ ] US market data permissions enabled (see [CONFIGURATION.md](CONFIGURATION.md))
- [ ] OpenD gateway downloaded and installed
- [ ] Python 3.11+ installed
- [ ] Docker installed (for infrastructure services)
- [ ] 8GB+ RAM available

### Quick Start (5 Minutes)

```bash
# 1. Start OpenD gateway (separate terminal)
./OpenD

# 2. Navigate to project
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

# 3. Verify OpenD connection
python -c "from moomoo import OpenQuoteContext; ctx = OpenQuoteContext(); print(ctx.get_global_state())"

# 4. Start infrastructure
cd infrastructure/docker
docker compose --env-file ../.env.local up -d

# 5. Start trading
cd ../..
python scripts/start_paper_trading_moomoo.py
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.**

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MOOMOO RL TRADING SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐      ┌──────────────┐      ┌───────────────────┐     │
│  │  Moomoo  │      │ NautilusTrader│     │  RL Framework     │     │
│  │  OpenD   │◄────►│    Engine     │◄───►│  (PPO/SAC)        │     │
│  │ Gateway  │      │  (Rust Core)  │     │                   │     │
│  └──────────┘      └──────────────┘      └───────────────────┘     │
│       │                   │                       │                 │
│       ▼                   ▼                       ▼                 │
│  Market Data        Strategies            Experience Buffer         │
│  + Execution      (Pairs/Momentum)       + Reward Shaping           │
│                         │                       │                   │
│                         ▼                       ▼                   │
│                  Risk Management          Model Checkpoints         │
│                  + Position Limits       + Training Metrics         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Trading Strategies

### 1. RL Pairs Trading (XLE/XLF)
Statistical arbitrage on energy/financial sector ETFs with RL-enhanced timing.

**Key Parameters:**
- Entry: 2.25 sigma z-score
- Exit: 0.25 sigma mean reversion
- Position size: 2% per leg

### 2. RL Momentum Breakout (NVDA, AMD, META)
Trend following with volume confirmation and RL-optimized holding periods.

**Key Parameters:**
- Breakout: 15-day high with 1.75x volume
- RSI: 50-70 range
- Position size: 2% per instrument

**See [STRATEGIES.md](STRATEGIES.md) for full parameter details and backtesting results.**

## Monitoring & Dashboards

Access real-time monitoring at:

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Trading dashboards |
| Prometheus | http://localhost:9090 | Metrics and alerts |
| Logs | `logs/MOOMOO-RL-PAPER-001_*.log` | System logs |

## RL "Seeing Out" Innovation

The key innovation is reward shaping that encourages holding winning trades longer:

```python
# Bonus for capturing 80%+ of favorable moves
if capture_ratio >= 0.8:
    seeing_out_bonus = 1.0
elif capture_ratio >= 0.5:
    seeing_out_bonus = 0.5
```

This addresses the common trader problem of exiting winners too early while cutting losers appropriately.

## Risk Management

Default risk parameters for $100,000 account:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Position Size | 2% ($2,000) | Per instrument |
| Max Concurrent Positions | 8 | Total across strategies |
| Daily Loss Limit | 3% ($3,000) | Halts new trades |
| Max Drawdown | 10% ($10,000) | Emergency liquidation |
| Stop Loss (1R) | 1% ($1,000) | Per trade risk |

## Project Structure

```
nautilus_trader/
├── scripts/
│   └── start_paper_trading_moomoo.py    # Main entry point
├── nautilus_trader/adapters/moomoo/     # Moomoo adapter
│   ├── data.py                          # Market data client
│   ├── execution.py                     # Order execution client
│   ├── config.py                        # Configuration
│   └── providers.py                     # Instrument provider
├── ajk_strategies/
│   ├── rl_strategies/                   # Trading strategies
│   │   ├── pairs_trading.py            # Pairs strategy
│   │   └── momentum_breakout.py        # Momentum strategy
│   └── rl_framework/                    # RL components
│       ├── agents/                      # RL agents
│       ├── state/                       # State builder
│       ├── reward/                      # Reward calculator
│       └── training/                    # Trainer & buffer
├── logs/                                # Trading logs
├── models/                              # RL model checkpoints
└── docs/moomoo-trading-system/         # This documentation
```

## Support & Resources

### Documentation
- [NautilusTrader Docs](https://nautilustrader.io)
- [Moomoo OpenD API](https://www.moomoo.com/api)
- [This Guide's Troubleshooting](TROUBLESHOOTING.md)

### Common Issues
1. **"No right to subscribe to US.XLE"** → Enable US market data in Moomoo app
2. **OpenD connection failed** → Verify OpenD is running on port 11111
3. **Strategies not trading** → Check market hours (9:30 AM - 4:00 PM ET)

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive solutions.

## Contributing

This is a personal trading system. For Nautilus core contributions, see the main [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Disclaimer

This system is for paper trading and educational purposes. Live trading involves substantial risk of loss. Always start with paper trading and thoroughly validate strategies before risking real capital.

## License

Follows NautilusTrader license. See [LICENSE](../../LICENSE) for details.

---

**Ready to trade?** → Start with [QUICKSTART.md](QUICKSTART.md)
