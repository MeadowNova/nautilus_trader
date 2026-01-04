# AI Automation & Self-Correcting Trading Systems

## 🤖 Introduction

Building an **AI-driven trading system** that adapts and self-corrects involves multiple layers of sophistication:

1. **Level 1**: Basic performance monitoring + manual switching
2. **Level 2**: Rule-based adaptive parameters
3. **Level 3**: Strategy portfolio with automatic switching
4. **Level 4**: ML-based parameter optimization
5. **Level 5**: Reinforcement Learning (RL) agents

Let's build up from simple to advanced.

---

## 📊 Level 1: Performance Monitoring & Alerting

**Concept**: Monitor strategy performance and get alerts when things go wrong.

### Implementation

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.position import Position
from nautilus_trader.model.enums import PositionSide
import numpy as np

class MonitoredStrategy(Strategy):
    """
    Strategy with performance monitoring and alerts.
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Performance tracking
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.recent_pnl = []  # Last N trades
        self.max_consecutive_losses = 0
        self.consecutive_losses = 0
        
        # Thresholds
        self.max_drawdown_threshold = 0.05  # 5%
        self.min_win_rate_threshold = 0.40  # 40%
        self.max_loss_streak = 5
        
        # State
        self.is_paused = False
        self.peak_equity = self.starting_equity
    
    def on_position_closed(self, position: Position):
        """Track performance metrics when position closes."""
        pnl = position.realized_pnl.as_double()
        self.trade_count += 1
        self.recent_pnl.append(pnl)
        
        # Keep last 20 trades
        if len(self.recent_pnl) > 20:
            self.recent_pnl.pop(0)
        
        # Update win/loss counts
        if pnl > 0:
            self.win_count += 1
            self.consecutive_losses = 0
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
            self.max_consecutive_losses = max(
                self.max_consecutive_losses,
                self.consecutive_losses
            )
        
        # Check conditions
        self._check_performance_thresholds()
    
    def _check_performance_thresholds(self):
        """Check if strategy should pause trading."""
        if self.trade_count < 10:
            return  # Need minimum trades
        
        # 1. Check win rate
        win_rate = self.win_count / self.trade_count
        if win_rate < self.min_win_rate_threshold:
            self.log.warning(
                f"Win rate below threshold: {win_rate:.2%} < {self.min_win_rate_threshold:.2%}"
            )
            self._pause_trading("Low win rate")
        
        # 2. Check loss streak
        if self.consecutive_losses >= self.max_loss_streak:
            self.log.error(
                f"Max loss streak reached: {self.consecutive_losses} losses"
            )
            self._pause_trading("Loss streak")
        
        # 3. Check drawdown
        current_equity = self.portfolio.net_position(self.instrument_id)
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        if drawdown > self.max_drawdown_threshold:
            self.log.error(f"Drawdown exceeded: {drawdown:.2%}")
            self._pause_trading("Max drawdown")
        
        # Update peak
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
    
    def _pause_trading(self, reason: str):
        """Pause trading and close positions."""
        self.log.warning(f"🚨 PAUSING TRADING: {reason}")
        self.is_paused = True
        
        # Close all positions
        self.close_all_positions(self.instrument_id)
        
        # Optional: Send alert (email, SMS, Discord)
        # self._send_alert(f"Strategy paused: {reason}")
    
    def on_bar(self, bar):
        """Your trading logic."""
        if self.is_paused:
            return  # Don't trade when paused
        
        # Your strategy logic here
        pass
```

**Key Features:**
- ✅ Tracks win rate, drawdown, loss streaks
- ✅ Pauses automatically when thresholds breached
- ✅ Closes positions when paused
- ⚠️ Requires manual restart

---

## 🔄 Level 2: Rule-Based Adaptive Parameters

**Concept**: Automatically adjust strategy parameters based on market conditions.

### Implementation

```python
from decimal import Decimal
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.indicators.atr import AverageTrueRange

class AdaptiveEMAStrategy(Strategy):
    """
    EMA crossover with adaptive periods based on volatility.
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Base parameters
        self.base_fast_period = 10
        self.base_slow_period = 20
        
        # Current adaptive parameters
        self.current_fast_period = self.base_fast_period
        self.current_slow_period = self.base_slow_period
        
        # Volatility indicator
        self.atr = None
        self.volatility_ema = None
        
        # Indicators (will be recreated)
        self.fast_ema = None
        self.slow_ema = None
        
        # Adaptation settings
        self.adaptation_interval = 100  # Check every N bars
        self.bar_count = 0
    
    def on_start(self):
        # Initialize ATR for volatility measurement
        self.atr = AverageTrueRange(14)
        self.volatility_ema = ExponentialMovingAverage(50)
        
        # Initialize EMAs
        self._recreate_emas()
        
        self.subscribe_bars(self.bar_type)
    
    def _recreate_emas(self):
        """Recreate EMAs with new periods."""
        self.fast_ema = ExponentialMovingAverage(self.current_fast_period)
        self.slow_ema = ExponentialMovingAverage(self.current_slow_period)
        
        self.log.info(
            f"EMAs updated: Fast={self.current_fast_period}, "
            f"Slow={self.current_slow_period}"
        )
    
    def on_bar(self, bar):
        # Update indicators
        self.fast_ema.update_raw(bar.close.as_double())
        self.slow_ema.update_raw(bar.close.as_double())
        self.atr.update(bar)
        
        if self.atr.initialized:
            self.volatility_ema.update_raw(self.atr.value)
        
        self.bar_count += 1
        
        # Adapt parameters periodically
        if self.bar_count % self.adaptation_interval == 0:
            self._adapt_parameters()
        
        # Trading logic
        if not (self.fast_ema.initialized and self.slow_ema.initialized):
            return
        
        if self._should_buy():
            self.buy()
        elif self._should_sell():
            self.sell()
    
    def _adapt_parameters(self):
        """Adapt EMA periods based on volatility."""
        if not self.volatility_ema.initialized:
            return
        
        current_vol = self.atr.value
        avg_vol = self.volatility_ema.value
        
        # High volatility → Use longer periods (slower)
        # Low volatility → Use shorter periods (faster)
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        if vol_ratio > 1.5:  # High volatility
            # Increase periods by 50%
            new_fast = int(self.base_fast_period * 1.5)
            new_slow = int(self.base_slow_period * 1.5)
            self.log.info("HIGH VOLATILITY: Using longer periods")
            
        elif vol_ratio < 0.7:  # Low volatility
            # Decrease periods by 30%
            new_fast = int(self.base_fast_period * 0.7)
            new_slow = int(self.base_slow_period * 0.7)
            self.log.info("LOW VOLATILITY: Using shorter periods")
            
        else:  # Normal volatility
            new_fast = self.base_fast_period
            new_slow = self.base_slow_period
        
        # Only recreate if changed significantly
        if (abs(new_fast - self.current_fast_period) > 2 or
            abs(new_slow - self.current_slow_period) > 2):
            
            self.current_fast_period = new_fast
            self.current_slow_period = new_slow
            self._recreate_emas()
    
    def _should_buy(self):
        return (
            self.fast_ema.value > self.slow_ema.value and
            self.portfolio.is_flat(self.instrument_id)
        )
    
    def _should_sell(self):
        return (
            self.fast_ema.value < self.slow_ema.value and
            not self.portfolio.is_flat(self.instrument_id)
        )
```

**Key Features:**
- ✅ Adapts to market volatility automatically
- ✅ Adjusts parameters in real-time
- ✅ No manual intervention needed
- ⚠️ Still rule-based, not learning

---

## 🎯 Level 3: Multi-Strategy Portfolio with Auto-Switching

**Concept**: Run multiple strategies and automatically switch based on performance.

### Architecture

```
┌─────────────────────────────────────────┐
│      Portfolio Manager (Orchestrator)   │
│  - Monitors all strategies              │
│  - Allocates capital                    │
│  - Switches active strategies           │
└────────────┬────────────────────────────┘
             │
    ┌────────┼────────┬────────┐
    │        │        │        │
┌───▼───┐ ┌─▼───┐ ┌──▼───┐ ┌──▼───┐
│Strategy│ │Strat│ │Strat │ │Strat │
│   A    │ │  B  │ │  C   │ │  D   │
│ (Trend)│ │(Mean│ │(Arb) │ │(ML)  │
└────────┘ └─────┘ └──────┘ └──────┘
```

### Implementation

```python
from nautilus_trader.common.actor import Actor
from nautilus_trader.trading.strategy import Strategy
from typing import Dict, List
import pandas as pd

class StrategyPortfolioManager(Actor):
    """
    Manages multiple strategies and switches based on performance.
    """
    
    def __init__(self, config):
        super().__init__()
        
        # Strategy registry
        self.strategies: Dict[str, Strategy] = {}
        self.strategy_performance: Dict[str, List[float]] = {}
        self.strategy_active: Dict[str, bool] = {}
        
        # Settings
        self.evaluation_window = 50  # trades
        self.min_trades_required = 20
        self.switch_threshold = 0.10  # 10% performance difference
        
    def register_strategy(self, name: str, strategy: Strategy):
        """Register a strategy with the manager."""
        self.strategies[name] = strategy
        self.strategy_performance[name] = []
        self.strategy_active[name] = False
        
        self.log.info(f"Registered strategy: {name}")
    
    def on_start(self):
        """Start with the first strategy."""
        if self.strategies:
            first_strategy = list(self.strategies.keys())[0]
            self._activate_strategy(first_strategy)
    
    def on_event(self, event):
        """Monitor all strategy events."""
        # Track position closes
        if hasattr(event, 'position_id'):
            strategy_name = self._get_strategy_from_position(event.position_id)
            if strategy_name:
                self._update_performance(strategy_name, event)
        
        # Periodic evaluation
        if self._should_evaluate():
            self._evaluate_and_switch()
    
    def _update_performance(self, strategy_name: str, event):
        """Update strategy performance metrics."""
        if hasattr(event, 'realized_pnl'):
            pnl = event.realized_pnl.as_double()
            self.strategy_performance[strategy_name].append(pnl)
            
            # Keep only recent window
            if len(self.strategy_performance[strategy_name]) > self.evaluation_window:
                self.strategy_performance[strategy_name].pop(0)
    
    def _evaluate_and_switch(self):
        """Evaluate all strategies and switch if needed."""
        # Calculate performance metrics
        performance_scores = {}
        
        for name, pnls in self.strategy_performance.items():
            if len(pnls) < self.min_trades_required:
                continue
            
            # Calculate Sharpe-like score
            returns = pd.Series(pnls)
            mean_return = returns.mean()
            std_return = returns.std()
            
            score = mean_return / std_return if std_return > 0 else 0
            performance_scores[name] = score
        
        if not performance_scores:
            return
        
        # Find best performing strategy
        best_strategy = max(performance_scores, key=performance_scores.get)
        best_score = performance_scores[best_strategy]
        
        # Get current active strategy
        current_strategy = self._get_active_strategy()
        
        if current_strategy == best_strategy:
            return  # Already running best
        
        current_score = performance_scores.get(current_strategy, 0)
        
        # Switch if significant improvement
        if best_score > current_score * (1 + self.switch_threshold):
            self.log.warning(
                f"🔄 SWITCHING STRATEGY: {current_strategy} → {best_strategy} "
                f"(Score: {current_score:.3f} → {best_score:.3f})"
            )
            self._deactivate_strategy(current_strategy)
            self._activate_strategy(best_strategy)
    
    def _activate_strategy(self, name: str):
        """Activate a strategy."""
        strategy = self.strategies[name]
        self.strategy_active[name] = True
        strategy.resume()  # Or start if not started
        self.log.info(f"✅ Activated strategy: {name}")
    
    def _deactivate_strategy(self, name: str):
        """Deactivate a strategy."""
        strategy = self.strategies[name]
        self.strategy_active[name] = False
        
        # Close all positions
        # strategy.close_all_positions()
        
        strategy.pause()
        self.log.info(f"⏸️  Deactivated strategy: {name}")
    
    def _get_active_strategy(self) -> str:
        """Get currently active strategy name."""
        for name, is_active in self.strategy_active.items():
            if is_active:
                return name
        return None
    
    def _should_evaluate(self) -> bool:
        """Check if it's time to evaluate."""
        # Could be time-based or event-based
        return True
    
    def _get_strategy_from_position(self, position_id) -> str:
        """Extract strategy name from position ID."""
        # Position IDs typically contain strategy name
        return position_id.value.split('-')[1] if '-' in position_id.value else None
```

**Usage:**

```python
# In your main script
manager = StrategyPortfolioManager(config)

# Register multiple strategies
manager.register_strategy("TrendFollower", TrendStrategy(config))
manager.register_strategy("MeanReversion", MeanReversionStrategy(config))
manager.register_strategy("Arbitrage", ArbitrageStrategy(config))

# Add to engine
engine.add_actor(manager)
```

**Key Features:**
- ✅ Multiple strategies running
- ✅ Automatic performance-based switching
- ✅ Capital reallocation
- ⚠️ Requires multiple good strategies

---

## 🧠 Level 4: ML-Based Parameter Optimization

**Concept**: Use machine learning to find optimal parameters.

### Approaches

#### A. Grid Search with Backtesting

```python
import itertools
import pandas as pd
from typing import Dict, List

class ParameterOptimizer:
    """
    Find optimal strategy parameters using grid search.
    """
    
    def __init__(self, strategy_class, data, base_config):
        self.strategy_class = strategy_class
        self.data = data
        self.base_config = base_config
    
    def optimize(self, param_grid: Dict[str, List]) -> Dict:
        """
        Grid search over parameter space.
        
        Args:
            param_grid: {"param_name": [val1, val2, val3]}
        
        Returns:
            Best parameters and their performance
        """
        results = []
        
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for combination in itertools.product(*param_values):
            params = dict(zip(param_names, combination))
            
            # Run backtest with these parameters
            performance = self._backtest_with_params(params)
            
            results.append({
                'params': params,
                'sharpe': performance['sharpe'],
                'total_return': performance['total_return'],
                'win_rate': performance['win_rate'],
                'max_drawdown': performance['max_drawdown'],
            })
        
        # Find best by Sharpe ratio
        results_df = pd.DataFrame(results)
        best_idx = results_df['sharpe'].idxmax()
        best = results_df.loc[best_idx]
        
        print(f"\n🏆 BEST PARAMETERS:")
        print(best)
        
        return best['params']
    
    def _backtest_with_params(self, params: Dict) -> Dict:
        """Run backtest with specific parameters."""
        # Update config
        config = self.base_config.copy()
        config.update(params)
        
        # Create strategy
        strategy = self.strategy_class(config)
        
        # Run backtest (simplified)
        engine = BacktestEngine(...)
        engine.add_strategy(strategy)
        engine.add_data(self.data)
        engine.run()
        
        # Extract metrics
        positions = engine.cache.positions()
        performance = self._calculate_performance(positions)
        
        engine.reset()
        engine.dispose()
        
        return performance
    
    def _calculate_performance(self, positions) -> Dict:
        """Calculate performance metrics."""
        pnls = [p.realized_pnl.as_double() for p in positions if p.is_closed]
        returns = pd.Series(pnls)
        
        return {
            'sharpe': returns.mean() / returns.std() if returns.std() > 0 else 0,
            'total_return': returns.sum(),
            'win_rate': len([p for p in pnls if p > 0]) / len(pnls) if pnls else 0,
            'max_drawdown': (returns.cumsum().cummax() - returns.cumsum()).max()
        }


# Usage
optimizer = ParameterOptimizer(
    strategy_class=EMACrossStrategy,
    data=historical_data,
    base_config=base_config
)

best_params = optimizer.optimize({
    'fast_ema_period': [5, 10, 15, 20],
    'slow_ema_period': [20, 30, 40, 50],
    'position_size': [0.05, 0.10, 0.15],
})

# Use best parameters
strategy = EMACrossStrategy(best_params)
```

#### B. Bayesian Optimization (Advanced)

```python
# Requires: pip install scikit-optimize

from skopt import gp_minimize
from skopt.space import Integer, Real

class BayesianOptimizer:
    """
    Find optimal parameters using Bayesian optimization.
    More efficient than grid search.
    """
    
    def __init__(self, strategy_class, data, base_config):
        self.strategy_class = strategy_class
        self.data = data
        self.base_config = base_config
        self.evaluation_count = 0
    
    def optimize(self, n_calls=50):
        """
        Bayesian optimization.
        
        Args:
            n_calls: Number of evaluations (much fewer than grid search)
        """
        # Define search space
        space = [
            Integer(5, 30, name='fast_ema_period'),
            Integer(20, 100, name='slow_ema_period'),
            Real(0.01, 0.20, name='position_size'),
        ]
        
        # Minimize negative Sharpe (to maximize Sharpe)
        result = gp_minimize(
            func=self._objective,
            dimensions=space,
            n_calls=n_calls,
            random_state=42,
            verbose=True
        )
        
        best_params = {
            'fast_ema_period': result.x[0],
            'slow_ema_period': result.x[1],
            'position_size': result.x[2],
        }
        
        print(f"\n🏆 BEST PARAMETERS (Bayesian):")
        print(f"Fast EMA: {best_params['fast_ema_period']}")
        print(f"Slow EMA: {best_params['slow_ema_period']}")
        print(f"Position Size: {best_params['position_size']:.3f}")
        print(f"Best Sharpe: {-result.fun:.3f}")
        
        return best_params
    
    def _objective(self, params):
        """Objective function to minimize."""
        self.evaluation_count += 1
        
        config = {
            'fast_ema_period': params[0],
            'slow_ema_period': params[1],
            'position_size': params[2],
        }
        
        performance = self._backtest_with_params(config)
        sharpe = performance['sharpe']
        
        print(f"Eval {self.evaluation_count}: Sharpe = {sharpe:.3f}")
        
        # Return negative (we're minimizing)
        return -sharpe
    
    def _backtest_with_params(self, params):
        # Same as grid search version
        pass


# Usage - finds good parameters in ~50 evaluations
# vs 1000s for grid search!
optimizer = BayesianOptimizer(...)
best_params = optimizer.optimize(n_calls=50)
```

---

## 🤖 Level 5: Reinforcement Learning Agents

**Concept**: AI agent learns optimal trading policy through trial and error.

### Overview

Reinforcement Learning for trading:
- **Agent**: Your trading strategy
- **Environment**: The market
- **State**: Current market conditions (prices, indicators, positions)
- **Actions**: Buy, Sell, Hold
- **Reward**: Profit/loss

### Popular Frameworks

1. **Stable-Baselines3** (easiest)
2. **Ray RLlib** (scalable)
3. **TensorTrade** (trading-specific)

### Basic RL Setup

```python
# Requires: pip install stable-baselines3 gym

import gym
from gym import spaces
import numpy as np
from stable_baselines3 import PPO

class TradingEnv(gym.Env):
    """
    Custom Gym environment for trading.
    Compatible with NautilusTrader.
    """
    
    def __init__(self, data, initial_balance=10000):
        super().__init__()
        
        self.data = data
        self.initial_balance = initial_balance
        self.current_step = 0
        
        # Action space: 0=Hold, 1=Buy, 2=Sell
        self.action_space = spaces.Discrete(3)
        
        # Observation space: [price, volume, position, cash, ...]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )
        
        self.reset()
    
    def reset(self):
        """Reset environment to start."""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0  # shares held
        self.entry_price = 0
        
        return self._get_observation()
    
    def step(self, action):
        """
        Execute one time step.
        
        Returns:
            observation, reward, done, info
        """
        current_price = self.data.iloc[self.current_step]['close']
        
        # Execute action
        reward = 0
        if action == 1:  # Buy
            if self.position == 0 and self.balance > current_price:
                self.position = self.balance / current_price
                self.entry_price = current_price
                self.balance = 0
                
        elif action == 2:  # Sell
            if self.position > 0:
                self.balance = self.position * current_price
                reward = (current_price - self.entry_price) / self.entry_price
                self.position = 0
        
        # Move to next step
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1
        
        observation = self._get_observation()
        info = {'balance': self.balance, 'position': self.position}
        
        return observation, reward, done, info
    
    def _get_observation(self):
        """Get current state."""
        if self.current_step >= len(self.data):
            return np.zeros(10)
        
        row = self.data.iloc[self.current_step]
        
        # Example features
        return np.array([
            row['close'],
            row['volume'],
            row['rsi'],  # Add indicators
            row['ema_fast'],
            row['ema_slow'],
            self.position,
            self.balance,
            self.entry_price,
            row['volatility'],
            row['trend_strength'],
        ])


# Train the RL agent
def train_rl_agent(training_data):
    """
    Train a reinforcement learning trading agent.
    """
    # Create environment
    env = TradingEnv(training_data)
    
    # Create RL agent (PPO algorithm)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
    )
    
    # Train
    print("Training RL agent...")
    model.learn(total_timesteps=100000)
    
    # Save
    model.save("trading_agent_ppo")
    print("Agent trained and saved!")
    
    return model


# Use trained agent in NautilusTrader
class RLTradingStrategy(Strategy):
    """
    Strategy that uses trained RL agent for decisions.
    """
    
    def __init__(self, config, model_path="trading_agent_ppo"):
        super().__init__(config)
        
        # Load trained model
        self.model = PPO.load(model_path)
        
        # State tracking
        self.observation_window = []
    
    def on_bar(self, bar):
        """Use RL agent to make trading decisions."""
        # Prepare observation
        observation = self._prepare_observation(bar)
        
        # Get action from agent
        action, _states = self.model.predict(observation, deterministic=True)
        
        # Execute action
        if action == 1:  # Buy signal
            if self.portfolio.is_flat(self.instrument_id):
                self.buy()
        elif action == 2:  # Sell signal
            if not self.portfolio.is_flat(self.instrument_id):
                self.sell()
        # action == 0: Hold (do nothing)
    
    def _prepare_observation(self, bar):
        """Convert current state to observation for RL agent."""
        # Calculate indicators
        # Return numpy array matching training format
        pass
```

---

## 🎯 Practical Roadmap

### Phase 1: Start Simple (Week 1-2)
```python
# Implement Level 1: Monitoring
- Add performance tracking
- Set thresholds
- Implement pause mechanism
```

### Phase 2: Add Adaptation (Week 3-4)
```python
# Implement Level 2: Rule-based adaptation
- Adjust parameters based on volatility
- Adapt to market regime
```

### Phase 3: Multiple Strategies (Month 2)
```python
# Implement Level 3: Portfolio management
- Run 2-3 strategies
- Automatic switching
- Performance comparison
```

### Phase 4: Optimization (Month 3)
```python
# Implement Level 4: ML optimization
- Grid search for parameters
- Bayesian optimization
- Walk-forward testing
```

### Phase 5: RL (Month 4+)
```python
# Implement Level 5: RL agents
- Build custom environment
- Train agent
- Integrate with NautilusTrader
```

---

## ⚠️ Important Warnings

### 1. Overfitting Risk
- **Problem**: Strategy works perfectly on historical data but fails live
- **Solution**: 
  - Use walk-forward testing
  - Out-of-sample validation
  - Keep parameters simple

### 2. Data Snooping
- **Problem**: Testing many strategies until one works (by luck)
- **Solution**:
  - Have clear hypothesis before testing
  - Use separate validation data
  - Statistical significance tests

### 3. Transaction Costs
- **Problem**: Ignoring slippage and commissions
- **Solution**:
  - Include realistic costs in backtest
  - Account for market impact
  - Test with conservative estimates

### 4. Black Swan Events
- **Problem**: AI hasn't seen extreme events
- **Solution**:
  - Always have risk limits
  - Maximum position size
  - Circuit breakers
  - Human oversight

---

## 📚 Learning Resources

### Books
- "Advances in Financial Machine Learning" by Marcos López de Prado
- "Machine Learning for Algorithmic Trading" by Stefan Jansen
- "Reinforcement Learning" by Sutton & Barto

### Courses
- Coursera: "Machine Learning for Trading" (Georgia Tech)
- Udacity: "AI for Trading"
- Fast.ai: Practical Deep Learning

### Libraries
- **stable-baselines3**: Easy RL
- **scikit-learn**: ML basics
- **optuna**: Hyperparameter optimization
- **gym**: RL environments

---

## 🎯 Quick Start Template

```python
# Start with this template
from nautilus_trader.trading.strategy import Strategy

class SelfCorrectingStrategy(Strategy):
    """
    Template for self-correcting strategy.
    Combines monitoring + adaptation.
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Performance tracking
        self.trades = []
        self.is_paused = False
        
        # Adaptive parameters
        self.current_position_size = config.position_size
        self.volatility_window = []
    
    def on_position_closed(self, position):
        """Track and adapt."""
        pnl = position.realized_pnl.as_double()
        self.trades.append(pnl)
        
        # Check if should pause
        if self._should_pause():
            self.pause_trading()
        
        # Adapt parameters
        if len(self.trades) % 10 == 0:
            self._adapt_parameters()
    
    def _should_pause(self) -> bool:
        """Check stop conditions."""
        if len(self.trades) < 10:
            return False
        
        recent = self.trades[-10:]
        losses = [t for t in recent if t < 0]
        
        return len(losses) > 7  # 70% loss rate
    
    def _adapt_parameters(self):
        """Adjust based on performance."""
        if len(self.trades) < 20:
            return
        
        recent_performance = sum(self.trades[-20:])
        
        if recent_performance < 0:
            # Reduce size when losing
            self.current_position_size *= 0.8
            self.log.info("Reducing position size")
        else:
            # Increase when winning
            self.current_position_size *= 1.1
            self.log.info("Increasing position size")
    
    def on_bar(self, bar):
        """Your trading logic with adaptive sizing."""
        if self.is_paused:
            return
        
        # Your signals here
        if self.should_buy():
            self.buy(quantity=self.current_position_size)
```

---

## 🚀 Next Steps

1. **Read**: LEARNING_PATH.md for basics
2. **Build**: Start with Level 1 monitoring
3. **Test**: Backtest thoroughly
4. **Iterate**: Add complexity gradually
5. **Paper Trade**: Before live money!

**Remember**: AI is a tool, not magic. Start simple, validate thoroughly, and always have risk controls!
