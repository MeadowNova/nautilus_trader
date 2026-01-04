# RL Multi-Factor Trading System - Active State

## Last Updated: 2025-12-09 20:00 UTC

## System Overview
Production-ready RL-enhanced multi-factor trading strategy deployed on Moomoo paper trading with comprehensive PostgreSQL data capture.

## Running Processes

### 1. RL Multi-Factor Strategy
- **Script**: `/home/ajk/Nautilus/nautilus_trader/scripts/rl_multi_factor_strategy.py`
- **Mode**: Live monitoring (data capture)
- **Session ID**: `85ae8607-b7e9-4810-857b-0f5e8de3e040`
- **Symbols**: SPY, AAPL, NVDA
- **Update Interval**: 30 seconds
- **Virtual Environment**: `/home/ajk/Nautilus/nautilus_trader/.venv`

### 2. Infrastructure Services
- **PostgreSQL**: localhost:5435 (nautilus_trader database)
- **Prometheus**: localhost:9090
- **Grafana**: localhost:3000
- **Moomoo OpenD**: localhost:11111

## Moomoo Paper Trading Accounts
- **Stock Account**: 1252643 (US market)
- **Options Account**: 1252648 (US market)
- **Environment**: TrdEnv.SIMULATE (paper trading)

## PostgreSQL Schema (11 Tables)

### Data Capture Tables
| Table | Purpose | Columns |
|-------|---------|---------|
| `rl_market_data` | OHLCV + technical indicators | open, high, low, close, volume, returns, volatility_20, atr_14, rsi_14, macd, bb_* |
| `rl_alpha_signals` | 9 alpha factors | momentum, mean_reversion, volatility, volume, microstructure, news_sentiment, social_sentiment, congressional, economic_regime |
| `rl_regime_states` | Market regime classification | regime (0-3), confidence, trend_strength, volatility_percentile |
| `rl_states` | RL state vectors (52-dim) | state_vector, portfolio_value, position, unrealized_pnl |
| `rl_actions` | Agent decisions | action (0-4), action_name, epsilon, was_exploration |
| `rl_rewards` | Reward calculations | reward, pnl_component, risk_component, sharpe_component |
| `rl_experience_replay` | (S,A,R,S',done) tuples | For offline training |
| `rl_model_checkpoints` | Model weights | Serialized PPO model |
| `rl_performance_metrics` | Episode metrics | sharpe, win_rate, max_drawdown |
| `rl_trades` | Trade log | symbol, side, quantity, price, commission |
| `rl_training_sessions` | Session metadata | start_time, mode, config |

### Current Data Volume
- `rl_market_data`: 66+ records (growing)
- `rl_alpha_signals`: 66+ records (growing)
- `rl_regime_states`: 66+ records (growing)

## RL Architecture

### PPO Agent (Stable-Baselines3)
- **State Space**: 52 dimensions
  - Market features (20): OHLCV, returns, volatility, RSI, MACD, Bollinger Bands
  - Alpha signals (9): momentum, mean_reversion, volatility, volume, microstructure, sentiment (3), economic
  - Regime (5): one-hot encoded regime + confidence
  - Portfolio (18): position, unrealized P&L, cash ratio per symbol
  
- **Action Space**: 5 discrete actions
  - 0: STRONG_SELL (-100% position)
  - 1: SELL (-50% position)
  - 2: HOLD (no change)
  - 3: BUY (+50% position)
  - 4: STRONG_BUY (+100% position)

- **Reward Function**: Risk-adjusted returns
  - PnL component (realized + unrealized)
  - Risk penalty (drawdown)
  - Sharpe shaping bonus
  - Transaction cost penalty

- **Exploration**: Epsilon-greedy with exponential decay
  - Start: 1.0
  - End: 0.05
  - Decay: 0.995 per episode

## Alpha Factors (9 Total)

### Traditional (5)
1. **Momentum**: ROC + acceleration + MA crossover (weight: 0.15)
2. **Mean Reversion**: Bollinger Bands + RSI + z-score (weight: 0.15)
3. **Volatility**: Vol ratio regime filter (weight: 0.12)
4. **Volume**: OBV + volume momentum + VWAP deviation (weight: 0.12)
5. **Microstructure**: Price-volume correlation + spread proxy (weight: 0.06)

### Alternative (4)
6. **News Sentiment**: Finnhub news API (weight: 0.10)
7. **Social Sentiment**: Reddit/Twitter sentiment (weight: 0.10)
8. **Congressional**: Congressional trading signals (weight: 0.10)
9. **Economic Regime**: Fed rates, GDP, inflation (weight: 0.10)

## Market Regime Detection

| Regime | Code | Characteristics |
|--------|------|-----------------|
| CHOPPY | 0 | Low trend strength, random walk |
| TRENDING | 1 | High trend strength, momentum works |
| MEAN_REVERTING | 2 | High mean reversion, Bollinger works |
| VOLATILE | 3 | High volatility, reduce position size |

## Key Files

### Strategy Scripts
- `/home/ajk/Nautilus/nautilus_trader/scripts/rl_multi_factor_strategy.py` (2,007 lines) - Main RL strategy
- `/home/ajk/Nautilus/nautilus_trader/scripts/live_multi_factor_strategy.py` (2,327 lines) - Non-RL version

### Documentation
- `RL_STRATEGY_ANALYSIS.md` - Technical documentation
- `RL_DEPLOYMENT_SUMMARY.md` - Quick reference
- `rl_queries.sql` - SQL query library

### Monitoring
- `/home/ajk/Nautilus/nautilus_trader/infrastructure/monitoring/grafana/dashboards/multi_factor_strategy.json`

## Database Connection
```python
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5435,
    "database": "nautilus_trader",
    "user": "nautilus",
    "password": "xSr7IgOZlwgkUwtnBBZoFG7N"
}
```

## Commands

### Start Strategy
```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate
python scripts/rl_multi_factor_strategy.py --mode live
```

### Train RL Model
```bash
python scripts/rl_multi_factor_strategy.py --mode train --episodes 100
```

### Query Database
```bash
PGPASSWORD='xSr7IgOZlwgkUwtnBBZoFG7N' psql -h localhost -p 5435 -U nautilus -d nautilus_trader
```

## Known Issues

1. **Alpha signals showing 0.0**: Need historical data warmup (60+ days lookback)
2. **Prometheus port conflict**: Using 9101 instead of 9100
3. **Moomoo execution not enabled**: Currently in monitoring-only mode

## Next Steps

1. Fix alpha signal calculations (add historical warmup)
2. Enable Moomoo paper trading execution
3. Integrate Finnhub/Alpha Vantage for alternative data
4. Start RL training after data accumulation
5. Backtest with experience replay data

## Data Sources

| Source | Type | Status | Rate Limit |
|--------|------|--------|------------|
| yfinance | Price data | Active | None (free) |
| Finnhub | Sentiment | Not integrated | 60/min free |
| Alpha Vantage | Economic | Not integrated | 5/min free |
| Moomoo | Execution | Connected | N/A |
