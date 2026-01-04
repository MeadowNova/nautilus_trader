# API Reference and Code Examples

Comprehensive code examples for working with the Moomoo RL Trading System.

## Table of Contents

1. [Basic Trading Examples](#basic-trading-examples)
2. [Strategy Development](#strategy-development)
3. [RL Agent Usage](#rl-agent-usage)
4. [Data Access](#data-access)
5. [Risk Management](#risk-management)
6. [Configuration](#configuration)
7. [Testing](#testing)

---

## Basic Trading Examples

### Minimal Working Example

```python
#!/usr/bin/env python3
"""Minimal Moomoo paper trading example."""

from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig, LoggingConfig
from nautilus_trader.model.identifiers import TraderId

from nautilus_trader.adapters.moomoo.config import (
    MoomooGatewayConfig,
    MoomooDataClientConfig,
    MoomooExecClientConfig,
)
from nautilus_trader.adapters.moomoo.factories import (
    MoomooLiveDataClientFactory,
    MoomooLiveExecClientFactory,
)

# Configure Moomoo gateway
gateway = MoomooGatewayConfig(
    host="127.0.0.1",
    port=11111,
    trading_mode="SIMULATE",  # Paper trading
)

# Create trading node config
config = TradingNodeConfig(
    trader_id=TraderId("MOOMOO-001"),
    logging=LoggingConfig(log_level="INFO"),
    data_clients={
        "MOOMOO": MoomooDataClientConfig(gateway=gateway)
    },
    exec_clients={
        "MOOMOO": MoomooExecClientConfig(gateway=gateway)
    },
)

# Create and configure node
node = TradingNode(config=config)
node.add_data_client_factory("MOOMOO", MoomooLiveDataClientFactory)
node.add_exec_client_factory("MOOMOO", MoomooLiveExecClientFactory)

# Build and run
node.build()
node.run()
```

### Simple Buy-and-Hold Strategy

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.orders import MarketOrder


class BuyAndHoldStrategy(Strategy):
    """Simple buy-and-hold strategy."""

    def __init__(self, config):
        super().__init__(config)
        self.instrument = InstrumentId.from_str(config.instrument_id)
        self.quantity = config.quantity
        self.bought = False

    def on_start(self):
        """Subscribe to 1-minute bars."""
        bar_type = BarType.from_str(
            f"{self.instrument}-1-MINUTE-LAST-EXTERNAL"
        )
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar):
        """Buy once on first bar."""
        if not self.bought:
            self.buy()

    def buy(self):
        """Place market buy order."""
        order = self.order_factory.market(
            instrument_id=self.instrument,
            order_side=OrderSide.BUY,
            quantity=self.quantity,
        )
        self.submit_order(order)
        self.bought = True
        self._log.info(f"Submitted buy order for {self.quantity} {self.instrument}")
```

---

## Strategy Development

### Template Strategy with RL

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.indicators import AverageTrueRange, RelativeStrengthIndex

from ajk_strategies.rl_framework.agents.base_agent import RLAgent, Action
from ajk_strategies.rl_framework.state.state_builder import StateBuilder, StateConfig
from ajk_strategies.rl_framework.reward.reward_calculator import RewardCalculator


class MyRLStrategyConfig(StrategyConfig, frozen=True):
    """Configuration for custom RL strategy."""
    instrument_id: str
    lookback_period: int = 20
    position_size_pct: float = 0.02
    use_rl: bool = True


class MyRLStrategy(Strategy):
    """Custom strategy with RL enhancement."""

    def __init__(
        self,
        config: MyRLStrategyConfig,
        rl_agent: RLAgent,
        experience_buffer,
    ):
        super().__init__(config)
        self.instrument = InstrumentId.from_str(config.instrument_id)
        self.rl_agent = rl_agent
        self.experience_buffer = experience_buffer

        # State builder
        self.state_builder = StateBuilder(StateConfig(
            lookback_bars=10,
            indicators=["rsi_14", "atr_14"],
        ))

        # Reward calculator
        self.reward_calculator = RewardCalculator()

        # Technical indicators
        self.rsi = RelativeStrengthIndex(14)
        self.atr = AverageTrueRange(14)

        # Tracking
        self.position_entry_state = None
        self.position_entry_action = None
        self.bars = []

    def on_start(self):
        """Initialize strategy."""
        self._log.info(f"Starting {self.__class__.__name__}")

        # Subscribe to bars
        bar_type = BarType.from_str(
            f"{self.instrument}-1-MINUTE-LAST-EXTERNAL"
        )
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar):
        """Process new bar."""
        # Store bar
        self.bars.append(bar)
        if len(self.bars) > 100:
            self.bars.pop(0)

        # Update indicators
        self.rsi.update(bar)
        self.atr.update(bar)

        # Need enough data
        if len(self.bars) < 20:
            return

        # Build state
        state = self.state_builder.build_state(
            bar=bar,
            position=self.position,
            indicators={
                'rsi': self.rsi.value,
                'atr': self.atr.value,
            }
        )

        # Get RL action
        if self.config.use_rl:
            action = self.rl_agent.select_action(state)
        else:
            action = self._rule_based_action()

        # Execute action
        if action == Action.BUY and self.position is None:
            self.enter_long(state, action)
        elif action == Action.EXIT and self.position is not None:
            self.exit_position(state, action)

    def enter_long(self, state, action):
        """Enter long position."""
        # Calculate quantity
        account_balance = self.portfolio.account("MOOMOO").balance_total()
        position_value = account_balance * self.config.position_size_pct
        quantity = int(position_value / self.bars[-1].close.as_double())

        if quantity > 0:
            order = self.order_factory.market(
                instrument_id=self.instrument,
                order_side=OrderSide.BUY,
                quantity=quantity,
            )
            self.submit_order(order)

            # Store for RL
            self.position_entry_state = state
            self.position_entry_action = action
            self._log.info(f"Entering LONG: {quantity} shares")

    def exit_position(self, state, action):
        """Exit position."""
        if self.position:
            order = self.order_factory.market(
                instrument_id=self.instrument,
                order_side=OrderSide.SELL,
                quantity=self.position.quantity,
            )
            self.submit_order(order)
            self._log.info(f"Exiting position: {self.position.quantity} shares")

    def on_position_closed(self, position):
        """Store experience when position closes."""
        if self.config.use_rl:
            # Calculate reward
            trade = self._create_trade_summary(position)
            reward = self.reward_calculator.calculate_reward(trade)

            # Store experience
            experience = {
                'state': self.position_entry_state,
                'action': self.position_entry_action,
                'reward': reward,
                'next_state': self.state_builder.build_state(...),
            }
            self.experience_buffer.add(experience)

            self._log.info(f"Position closed: P&L=${position.realized_pnl:.2f}, Reward={reward:.4f}")

    def _rule_based_action(self) -> Action:
        """Fallback rule-based logic."""
        if self.position is None:
            # Buy when RSI < 30 (oversold)
            if self.rsi.value < 30:
                return Action.BUY
        else:
            # Sell when RSI > 70 (overbought)
            if self.rsi.value > 70:
                return Action.EXIT

        return Action.HOLD

    def _create_trade_summary(self, position):
        """Create trade summary for reward calculation."""
        return {
            'pnl': position.realized_pnl,
            'bars_held': position.duration_ns / 60_000_000_000,  # minutes
            'max_favorable_excursion': position.max_pnl,
            'max_adverse_excursion': abs(position.min_pnl),
        }
```

---

## RL Agent Usage

### Creating a Custom RL Agent

```python
import torch
import torch.nn as nn
import numpy as np

from ajk_strategies.rl_framework.agents.base_agent import RLAgent, Action


class PPOAgent(RLAgent):
    """PPO (Proximal Policy Optimization) agent."""

    def __init__(self, state_dim, action_dim, hidden_dim=128, lr=3e-4):
        super().__init__(state_dim, action_dim)

        # Actor network (policy)
        self.actor = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )

        # Critic network (value function)
        self.critic = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )

        self.optimizer = torch.optim.Adam(
            list(self.actor.parameters()) + list(self.critic.parameters()),
            lr=lr
        )

        self.epsilon = 0.1  # Exploration rate

    def select_action(self, state: np.ndarray) -> Action:
        """Select action using policy."""
        # Epsilon-greedy exploration
        if np.random.random() < self.epsilon:
            return Action(np.random.randint(0, self.action_dim))

        # Forward pass
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            action_probs = self.actor(state_tensor)

        # Sample from distribution
        action = torch.multinomial(action_probs, 1).item()
        return Action(action)

    def train(self, experiences, gamma=0.99, clip_epsilon=0.2):
        """Train using PPO algorithm."""
        states = torch.FloatTensor([e['state'] for e in experiences])
        actions = torch.LongTensor([e['action'] for e in experiences])
        rewards = torch.FloatTensor([e['reward'] for e in experiences])
        next_states = torch.FloatTensor([e['next_state'] for e in experiences])

        # Compute returns (discounted rewards)
        returns = []
        G = 0
        for r in reversed(rewards):
            G = r + gamma * G
            returns.insert(0, G)
        returns = torch.FloatTensor(returns)

        # Normalize returns
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)

        # Forward pass
        action_probs = self.actor(states)
        values = self.critic(states).squeeze()

        # Compute advantages
        advantages = returns - values.detach()

        # Policy loss (PPO clipped objective)
        action_log_probs = torch.log(action_probs.gather(1, actions.unsqueeze(1)))
        ratio = torch.exp(action_log_probs - action_log_probs.detach())
        clipped_ratio = torch.clamp(ratio, 1 - clip_epsilon, 1 + clip_epsilon)
        policy_loss = -torch.min(
            ratio * advantages.unsqueeze(1),
            clipped_ratio * advantages.unsqueeze(1)
        ).mean()

        # Value loss
        value_loss = nn.MSELoss()(values, returns)

        # Total loss
        loss = policy_loss + 0.5 * value_loss

        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return {
            'policy_loss': policy_loss.item(),
            'value_loss': value_loss.item(),
            'total_loss': loss.item(),
        }

    def save(self, path: str):
        """Save model checkpoint."""
        torch.save({
            'actor_state_dict': self.actor.state_dict(),
            'critic_state_dict': self.critic.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, path)

    def load(self, path: str):
        """Load model checkpoint."""
        checkpoint = torch.load(path)
        self.actor.load_state_dict(checkpoint['actor_state_dict'])
        self.critic.load_state_dict(checkpoint['critic_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
```

### Using the Agent in a Strategy

```python
# Create agent
agent = PPOAgent(state_dim=75, action_dim=4)

# Load pretrained model (optional)
agent.load("models/pretrained_agent.pt")

# Create strategy with agent
strategy = MyRLStrategy(
    config=config,
    rl_agent=agent,
    experience_buffer=buffer,
)

# Add to trading node
node.trader.add_strategy(strategy)
```

---

## Data Access

### Querying Market Data

```python
from moomoo import OpenQuoteContext

# Connect to OpenD
ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

# Get real-time quote
ret, data = ctx.get_market_snapshot(['US.AAPL'])
if ret == 0:
    print(f"AAPL: ${data['last_price'][0]}")

# Get historical bars
ret, data = ctx.get_history_kline(
    code='US.AAPL',
    start='2024-01-01',
    end='2024-12-01',
    ktype='K_1M',  # 1-minute bars
)

ctx.close()
```

### Accessing NautilusTrader Cache

```python
# In strategy
def on_bar(self, bar: Bar):
    # Get instrument from cache
    instrument = self.cache.instrument(self.instrument_id)

    # Get current position
    position = self.cache.position(self.instrument_id)

    # Get open orders
    orders = self.cache.orders_open(instrument_id=self.instrument_id)

    # Get account balance
    account = self.cache.account("MOOMOO")
    balance = account.balance_total()
```

---

## Risk Management

### Custom Risk Checks

```python
from nautilus_trader.risk import RiskEngine


class CustomRiskEngine(RiskEngine):
    """Custom risk management logic."""

    def check_pre_trade(self, order):
        """Pre-trade risk checks."""
        # Check daily loss limit
        daily_pnl = self.portfolio.unrealized_pnl()
        if daily_pnl < -3000:  # -$3,000 daily loss
            self.reject_order(order, "Daily loss limit exceeded")
            return False

        # Check position concentration
        position_value = order.quantity * order.price
        account_value = self.portfolio.account_value()
        if position_value / account_value > 0.10:  # 10% max
            self.reject_order(order, "Position size exceeds limit")
            return False

        return True
```

---

## Configuration

### Advanced Node Configuration

```python
from nautilus_trader.config import (
    TradingNodeConfig,
    LoggingConfig,
    CacheConfig,
    DataEngineConfig,
    ExecEngineConfig,
    RiskEngineConfig,
)

config = TradingNodeConfig(
    trader_id=TraderId("MOOMOO-RL-001"),

    # Logging
    logging=LoggingConfig(
        log_level="INFO",
        log_level_file="DEBUG",
        log_directory="logs",
        log_colors=True,
        bypass_logging=False,
    ),

    # Cache
    cache=CacheConfig(
        database=DatabaseConfig(
            type="redis",
            host="localhost",
            port=6378,
        ),
        encoding="msgpack",
        timestamps_as_iso8601=False,
    ),

    # Data engine
    data_engine=DataEngineConfig(
        time_bars_timestamp_on_close=True,
        validate_data_sequence=True,
    ),

    # Execution engine
    exec_engine=ExecEngineConfig(
        reconciliation_lookback_mins=1440,  # 24 hours
        snapshot_orders=True,
        snapshot_positions=True,
    ),

    # Risk engine
    risk_engine=RiskEngineConfig(
        bypass=False,
        max_order_rate="15/00:00:30",  # 15 per 30 seconds
        max_notional_per_order={"MOOMOO": Money(10000, USD)},
    ),

    # Moomoo clients
    data_clients={"MOOMOO": MoomooDataClientConfig(...)},
    exec_clients={"MOOMOO": MoomooExecClientConfig(...)},
)
```

---

## Testing

### Backtesting Example

```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog


# Load historical data
catalog = ParquetDataCatalog("./data")

# Configure backtest
config = BacktestEngineConfig(
    trader_id=TraderId("BACKTEST-001"),
    log_level="INFO",
)

# Create engine
engine = BacktestEngine(config=config)

# Add data
engine.add_instrument(instrument)
engine.add_data(catalog.bars(["US.AAPL-1-MINUTE-LAST-EXTERNAL"]))

# Add strategy
strategy = MyRLStrategy(config=strategy_config)
engine.add_strategy(strategy)

# Run backtest
engine.run()

# Get results
results = engine.get_result()
print(f"Total P&L: ${results.total_pnl:.2f}")
print(f"Sharpe: {results.sharpe_ratio:.2f}")
```

### Unit Testing Strategy

```python
import pytest
from nautilus_trader.test_kit.stubs import TestStubs


def test_strategy_enter_long():
    """Test strategy enters long position."""
    # Create test strategy
    config = MyRLStrategyConfig(instrument_id="US.AAPL.MOOMOO")
    strategy = MyRLStrategy(config)

    # Simulate bar
    bar = TestStubs.bar_5decimal()
    strategy.on_bar(bar)

    # Assert order was submitted
    assert len(strategy.cache.orders()) == 1
    order = strategy.cache.orders()[0]
    assert order.side == OrderSide.BUY
```

---

**For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).**
**For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).**
