# RL-Enhanced Multi-Factor Trading Strategy

## Overview

An advanced algorithmic trading strategy that combines multi-factor alpha generation with Deep Reinforcement Learning (PPO algorithm) for adaptive decision-making. All data points are captured to PostgreSQL for offline training, analysis, and model improvement.

## Architecture

### Components

1. **Multi-Factor Alpha Model** (9 factors)
   - Traditional: Momentum, Mean Reversion, Volatility, Volume, Microstructure
   - Alternative: News Sentiment, Social Sentiment, Congressional Trading, Economic Regime

2. **Regime Detector**
   - Classifies market conditions: CHOPPY, TRENDING, MEAN_REVERTING, VOLATILE
   - HMM-like state transitions

3. **RL Agent (PPO)**
   - State Space: 52 features (market data, alpha signals, regime, position, P&L)
   - Action Space: Discrete(5) - Strong Sell, Sell, Hold, Buy, Strong Buy
   - Reward: Risk-adjusted returns with Sharpe ratio shaping

4. **PostgreSQL Data Capture**
   - Complete audit trail of all decisions
   - Experience replay buffer for offline training
   - Model checkpointing

5. **Prometheus Metrics**
   - Real-time monitoring on port 9101
   - RL-specific metrics (epsilon, reward, policy loss)
   - Trading metrics (P&L, Sharpe, positions)

## Database Schema

### Core Tables

- `rl_market_data`: OHLCV + technical indicators (RSI, MACD, Bollinger Bands, etc.)
- `rl_alpha_signals`: All 9 factor signals with ensemble weighting
- `rl_regime_states`: Market regime classifications with confidence
- `rl_states`: Complete RL state vectors (52 features)
- `rl_actions`: Actions taken with position sizing
- `rl_rewards`: Reward calculations with components (PnL, Sharpe, drawdown)
- `rl_experience_replay`: (S, A, R, S', done) tuples for training
- `rl_model_checkpoints`: Serialized model weights
- `rl_performance_metrics`: Episode-level performance
- `rl_training_sessions`: Training run metadata

## Installation

```bash
# Navigate to nautilus_trader directory
cd /home/ajk/Nautilus/nautilus_trader

# Install additional dependencies
uv pip install -r scripts/rl_requirements.txt

# Verify PostgreSQL is running
docker ps | grep postgres

# Initialize database schema (automatic on first run)
```

## Usage

### 1. Training Mode (Offline Learning)

Train the RL agent on historical data:

```bash
python scripts/rl_multi_factor_strategy.py --mode train --episodes 1000
```

This will:
- Download 1 year of historical data for SPY, AAPL, NVDA
- Run 1000 episodes of simulated trading
- Update model weights via PPO algorithm
- Save checkpoints every 100 episodes to PostgreSQL
- Export metrics to Prometheus

### 2. Live Trading Mode (Online Learning)

Run live paper trading with continuous learning:

```bash
python scripts/rl_multi_factor_strategy.py --mode live
```

This will:
- Connect to Moomoo OpenD for execution
- Poll market data every 30 seconds
- Make trading decisions using RL agent
- Continue learning from live experience
- Store all data to PostgreSQL

### 3. Inference Mode (Frozen Model)

Run paper trading with a trained model (no learning):

```bash
python scripts/rl_multi_factor_strategy.py --mode inference
```

This will:
- Load latest checkpoint from PostgreSQL
- Set epsilon=0 (no exploration)
- Make deterministic trading decisions
- Continue data capture for analysis

## Configuration

Edit `RLStrategyConfig` in the script:

```python
@dataclass
class RLStrategyConfig:
    # Symbols to trade
    symbols: List[str] = ['SPY', 'AAPL', 'NVDA']

    # Capital
    initial_capital: float = 100000.0
    max_position_pct: float = 0.02  # 2% max per position

    # RL Hyperparameters
    learning_rate: float = 3e-4
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995

    # Risk Management
    max_drawdown_threshold: float = 0.10
    volatility_target: float = 0.15

    # Update Frequency
    poll_interval_seconds: int = 30
    checkpoint_frequency: int = 100
```

## Monitoring

### Prometheus Metrics (Port 9101)

Access metrics at: http://localhost:9101/metrics

Key metrics:
- `rl_epsilon`: Current exploration rate
- `rl_avg_reward`: Average reward per episode
- `rl_state_pnl`: Current P&L
- `rl_action_distribution`: Action frequency by type
- `nautilus_multifactor_sharpe_ratio`: Current Sharpe ratio
- `nautilus_multifactor_portfolio_value`: Portfolio value

### Grafana Dashboard

1. Add Prometheus data source: http://localhost:9090
2. Import dashboard or create custom panels
3. Monitor in real-time

### PostgreSQL Queries

```sql
-- Recent performance
SELECT episode, symbol, total_reward, sharpe_ratio, win_rate, num_trades
FROM rl_performance_metrics
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY episode DESC
LIMIT 10;

-- Action distribution
SELECT action, COUNT(*) as count, AVG(action_prob) as avg_prob
FROM rl_actions
WHERE session_id = 'YOUR_SESSION_ID' AND symbol = 'SPY'
GROUP BY action
ORDER BY action;

-- Reward components
SELECT
    AVG(pnl_reward) as avg_pnl_reward,
    AVG(sharpe_reward) as avg_sharpe_reward,
    AVG(drawdown_penalty) as avg_drawdown_penalty,
    AVG(total_reward) as avg_total_reward
FROM rl_rewards
WHERE session_id = 'YOUR_SESSION_ID';

-- Model checkpoints
SELECT checkpoint_name, episode, step, avg_sharpe, win_rate, timestamp
FROM rl_model_checkpoints
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY timestamp DESC;

-- Experience replay buffer size
SELECT COUNT(*) as replay_size
FROM rl_experience_replay
WHERE session_id = 'YOUR_SESSION_ID';
```

## Reward Function

The reward function combines multiple components:

```
Total Reward = PnL Reward + 0.5 * Sharpe Reward + Drawdown Penalty + Transaction Cost Penalty

Where:
- PnL Reward: Normalized step P&L * 100
- Sharpe Reward: Recent Sharpe ratio / Target Sharpe (2.0)
- Drawdown Penalty: -10 * max_drawdown (if > 5%)
- Transaction Cost: -(cost / capital) * 1000
```

This encourages:
- Positive returns
- Risk-adjusted performance
- Avoiding large drawdowns
- Minimizing transaction costs

## State Space (52 features)

1. **Market Features (5)**: returns, volatility, RSI, MACD, BB width
2. **Alpha Signals (6)**: 4 traditional factors + ensemble + confidence
3. **Regime (5)**: one-hot encoded regime + confidence
4. **Position & P&L (4)**: position, position value, cash, portfolio value
5. **Recent P&L (5)**: last 5 step P&Ls
6. **Recent Returns (5)**: last 5 step returns
7. **Risk Metrics (2)**: Sharpe ratio, max drawdown
8. **Time Features (2)**: step in episode, position in 20-day cycle

## Action Space (5 discrete actions)

- **STRONG_SELL (0)**: Target -50% of max position
- **SELL (1)**: Target -25% of max position
- **HOLD (2)**: No change
- **BUY (3)**: Target +25% of max position
- **STRONG_BUY (4)**: Target +50% of max position

Position sizing respects `max_position_pct` (2% of capital per symbol).

## Training Strategy

### Exploration vs Exploitation

- Epsilon-greedy strategy
- Start: epsilon = 1.0 (100% random actions)
- End: epsilon = 0.05 (5% random actions)
- Decay: 0.995 per episode

### PPO Hyperparameters

- Learning rate: 3e-4 (adaptive)
- Batch size: 64 experiences
- N-steps: 2048 steps per update
- Epochs: 10 epochs per update
- Clip range: 0.2
- Entropy coefficient: 0.01 (for exploration)
- Gamma: 0.99 (discount factor)

### Checkpointing

- Automatic every 100 episodes
- Stores model weights, hyperparameters, and performance metrics
- Can resume training from any checkpoint

## Offline Training from Historical Data

The experience replay buffer enables offline training:

```python
# Sample 10,000 random experiences from database
experiences = await persistence.sample_experiences(10000, symbol='SPY')

# Train model on sampled experiences
for experience in experiences:
    agent.train_step(experience)
```

This allows:
- Training from market crashes/unusual events
- Balancing dataset with rare scenarios
- Improving model without live trading risk

## Performance Analysis

### Episode Metrics

- Total reward
- Total P&L
- Sharpe ratio
- Max drawdown
- Win rate
- Profit factor
- Number of trades
- Exploration rate

### Trade Analysis

```sql
-- Best and worst trades
SELECT
    symbol,
    action,
    shares_traded,
    target_position,
    timestamp
FROM rl_actions
JOIN rl_rewards ON rl_actions.id = rl_rewards.action_id
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY total_reward DESC
LIMIT 10;

-- Regime performance
SELECT
    r.regime,
    COUNT(*) as actions,
    AVG(rw.total_reward) as avg_reward,
    AVG(rw.sharpe_ratio) as avg_sharpe
FROM rl_regime_states r
JOIN rl_actions a ON a.timestamp BETWEEN r.timestamp AND r.timestamp + INTERVAL '30 seconds'
JOIN rl_rewards rw ON rw.action_id = a.id
WHERE r.session_id = 'YOUR_SESSION_ID'
GROUP BY r.regime;
```

## Troubleshooting

### No Prometheus Metrics

- Check port 9101 is not in use: `lsof -i :9101`
- Verify Prometheus is configured to scrape localhost:9101

### PostgreSQL Connection Failed

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -p 5435 -U nautilus -d nautilus_trader

# Verify schema
\dt rl_*
```

### Moomoo Connection Failed

```bash
# Check OpenD is running
lsof -i :11111

# Check account IDs in Moomoo desktop app
# Stock: 1252643 (paper)
# Options: 1252648 (paper)
```

### Low Performance

- Increase `poll_interval_seconds` to reduce overhead
- Use fewer symbols initially
- Check `n_steps` and `batch_size` for memory issues
- Monitor CPU/GPU usage

## Advanced Usage

### Custom Reward Function

Edit `TradingEnvironment._calculate_reward()`:

```python
def _calculate_reward(self, step_pnl: float, transaction_cost: float) -> float:
    # Add custom reward components
    custom_reward = ...

    return pnl_reward + sharpe_reward + custom_reward
```

### Custom Alpha Factors

Edit `AlphaFactorModel.calculate_signals()`:

```python
# Add new factor
signals.custom_factor_signal = calculate_custom_factor(df)

# Update factor weights
self.factor_weights['custom_factor'] = 0.10
```

### Prioritized Experience Replay

The database supports priority field for prioritized sampling:

```sql
-- Sample high-priority experiences
SELECT * FROM rl_experience_replay
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY priority DESC
LIMIT 1000;
```

## Risk Management

### Position Limits

- Max 2% of capital per symbol
- Max 1x leverage overall
- Automatic stop on 10% drawdown

### Transaction Costs

- 5 bps transaction costs
- 2 bps slippage
- Costs are factored into reward calculation

### Market Hours

Currently runs 24/7 (crypto-style). For equity hours:

```python
def is_market_open() -> bool:
    now = datetime.now(timezone('US/Eastern'))
    return (now.time() >= dt_time(9, 30) and
            now.time() <= dt_time(16, 0) and
            now.weekday() < 5)
```

## Future Enhancements

1. **Multi-Symbol Coordination**: Portfolio-level optimization
2. **Hierarchical RL**: High-level strategy selection, low-level execution
3. **Meta-Learning**: Fast adaptation to new market regimes
4. **Options Overlay**: Hedging with options (account 1252648)
5. **Transfer Learning**: Pre-train on one symbol, fine-tune on others
6. **Prioritized Replay**: Sample important experiences more frequently
7. **Curiosity-Driven Exploration**: Intrinsic reward for novel states

## References

- Stable-Baselines3: https://stable-baselines3.readthedocs.io/
- PPO Paper: https://arxiv.org/abs/1707.06347
- Gymnasium: https://gymnasium.farama.org/
- NautilusTrader: https://nautilustrader.io/

## License

Same as NautilusTrader parent project.

## Support

For issues or questions:
1. Check logs in console output
2. Query PostgreSQL for data issues
3. Monitor Prometheus metrics
4. Review episode performance metrics
