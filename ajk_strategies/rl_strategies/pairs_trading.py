# -------------------------------------------------------------------------------------------------
#  RL-Enhanced Pairs Trading Strategy
#  Combines statistical arbitrage with reinforcement learning
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType, QuoteTick
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from ajk_strategies.rl_framework.agents.base_agent import RLAgent, Action, SimpleRuleAgent
from ajk_strategies.rl_framework.state.state_builder import StateBuilder, StateConfig
from ajk_strategies.rl_framework.reward.reward_calculator import RewardCalculator, Trade
from ajk_strategies.rl_framework.reward.credit_assignment import Experience

if TYPE_CHECKING:
    from ajk_strategies.rl_framework.training.experience_buffer import PrioritizedReplayBuffer


class RLPairsTradingConfig(StrategyConfig, frozen=True):
    """Configuration for RL-enhanced pairs trading strategy."""

    instrument_id_a: str  # e.g., "XLE.MOOMOO"
    instrument_id_b: str  # e.g., "XLF.MOOMOO"
    lookback_period: int = 60
    zscore_entry: float = 2.0
    zscore_exit: float = 0.5
    zscore_stop: float = 3.0
    position_size_pct: float = 0.02  # 2% per position (conservative)
    max_holding_bars: int = 100
    use_rl: bool = True
    rl_model_path: str | None = None


class RLPairsTradingStrategy(Strategy):
    """
    Mean reversion pairs trading strategy with RL enhancement.

    The RL agent learns to:
    1. Time entries more precisely around z-score signals
    2. Hold winning trades longer (seeing out the move)
    3. Exit losing trades faster
    4. Adapt to changing correlation regimes
    """

    def __init__(
        self,
        config: RLPairsTradingConfig,
        rl_agent: RLAgent | None = None,
        experience_buffer: PrioritizedReplayBuffer | None = None,
    ):
        super().__init__(config)

        # Note: self.config is already set by parent class Strategy
        self.instrument_a = InstrumentId.from_str(config.instrument_id_a)
        self.instrument_b = InstrumentId.from_str(config.instrument_id_b)

        # RL components
        self.use_rl = config.use_rl
        self.rl_agent = rl_agent or SimpleRuleAgent()
        self.experience_buffer = experience_buffer

        # State builder
        self.state_builder = StateBuilder(StateConfig(
            lookback_bars=10,
            indicators=["ema_20", "rsi_14", "atr_14"],
        ))

        # Reward calculator
        self.reward_calculator = RewardCalculator()

        # Price tracking
        self.prices_a: deque = deque(maxlen=config.lookback_period)
        self.prices_b: deque = deque(maxlen=config.lookback_period)
        self.bars_a: list[Bar] = []
        self.bars_b: list[Bar] = []

        # Spread statistics
        self.spread_mean: float = 0.0
        self.spread_std: float = 0.0
        self.current_zscore: float = 0.0

        # Position tracking
        self.position_type: str | None = None  # "long_spread" or "short_spread"
        self.entry_zscore: float = 0.0
        self.entry_bar: int = 0
        self.bars_held: int = 0
        self.max_favorable_pnl: float = 0.0
        self.max_adverse_pnl: float = 0.0

        # Experience tracking for RL
        self._current_trajectory: list[Experience] = []
        self._previous_state: np.ndarray | None = None
        self._previous_action: Action | None = None
        self._bar_count: int = 0

    def on_start(self):
        """Initialize strategy on start."""
        self.subscribe_quote_ticks(self.instrument_a)
        self.subscribe_quote_ticks(self.instrument_b)

        # Subscribe to bars using proper BarType objects
        bar_type_a = BarType.from_str(f"{self.instrument_a}-1-MINUTE-LAST-EXTERNAL")
        bar_type_b = BarType.from_str(f"{self.instrument_b}-1-MINUTE-LAST-EXTERNAL")
        self.subscribe_bars(bar_type_a)
        self.subscribe_bars(bar_type_b)

        self.log.info(
            f"RL Pairs Trading started: {self.instrument_a} vs {self.instrument_b}"
        )

    def on_quote_tick(self, tick: QuoteTick):
        """Process quote tick."""
        mid_price = (float(tick.bid_price) + float(tick.ask_price)) / 2

        if tick.instrument_id == self.instrument_a:
            self.prices_a.append(mid_price)
        elif tick.instrument_id == self.instrument_b:
            self.prices_b.append(mid_price)

    def on_bar(self, bar: Bar):
        """Process bar and generate signals."""
        self._bar_count += 1

        # Store bars
        if bar.bar_type.instrument_id == self.instrument_a:
            self.bars_a.append(bar)
            if len(self.bars_a) > self.config.lookback_period:
                self.bars_a = self.bars_a[-self.config.lookback_period:]
        elif bar.bar_type.instrument_id == self.instrument_b:
            self.bars_b.append(bar)
            if len(self.bars_b) > self.config.lookback_period:
                self.bars_b = self.bars_b[-self.config.lookback_period:]

        # Need both instruments
        if len(self.bars_a) < 20 or len(self.bars_b) < 20:
            return

        # Update spread statistics
        self._update_spread_statistics()

        # Build current state
        current_state = self._build_state()

        # Get RL action
        if self.use_rl:
            action = self.rl_agent.act(current_state, explore=True)
        else:
            action = self._rule_based_action()

        # Execute action
        self._execute_action(action)

        # Track position P&L for MFE/MAE
        if self.position_type is not None:
            self.bars_held += 1
            current_pnl = self._calculate_unrealized_pnl()
            self.max_favorable_pnl = max(self.max_favorable_pnl, current_pnl)
            self.max_adverse_pnl = min(self.max_adverse_pnl, current_pnl)

        # Store experience for RL training
        self._store_experience(current_state, action)

    def _update_spread_statistics(self):
        """Calculate spread mean, std, and z-score."""
        if len(self.prices_a) < 20 or len(self.prices_b) < 20:
            return

        prices_a = np.array(list(self.prices_a))
        prices_b = np.array(list(self.prices_b))

        min_len = min(len(prices_a), len(prices_b))
        prices_a = prices_a[-min_len:]
        prices_b = prices_b[-min_len:]

        # Calculate spread as ratio
        spread = prices_a / prices_b

        self.spread_mean = np.mean(spread)
        self.spread_std = np.std(spread)

        if self.spread_std > 0:
            current_spread = prices_a[-1] / prices_b[-1]
            self.current_zscore = (current_spread - self.spread_mean) / self.spread_std
        else:
            self.current_zscore = 0.0

    def _build_state(self) -> np.ndarray:
        """Build state vector for RL agent."""
        # Use bars from instrument A as primary
        bars = self.bars_a if self.bars_a else []

        state = self.state_builder.build_state(
            bars=bars,
            portfolio=self.portfolio,
            position=None,  # TODO: get position
            account_value=100000.0,
        )

        # Add spread-specific features
        spread_features = np.array([
            self.current_zscore / 3.0,  # Normalized z-score
            self.spread_std / 0.1,  # Normalized volatility
            float(self.position_type is not None),  # Has position
            self.bars_held / self.config.max_holding_bars,  # Holding time
        ])

        return np.concatenate([state, spread_features])

    def _rule_based_action(self) -> Action:
        """Generate action using traditional rules."""
        # If in position, check exits
        if self.position_type is not None:
            # Profit target
            if abs(self.current_zscore) < self.config.zscore_exit:
                return Action.EXIT

            # Stop loss
            if abs(self.current_zscore) > self.config.zscore_stop:
                return Action.EXIT

            # Time stop
            if self.bars_held >= self.config.max_holding_bars:
                return Action.EXIT

            return Action.HOLD

        # Entry signals
        if self.current_zscore < -self.config.zscore_entry:
            return Action.BUY  # Long spread
        elif self.current_zscore > self.config.zscore_entry:
            return Action.SELL  # Short spread

        return Action.HOLD

    def _execute_action(self, action: Action):
        """Execute the RL action."""
        if action == Action.BUY and self.position_type is None:
            self._enter_long_spread()
        elif action == Action.SELL and self.position_type is None:
            self._enter_short_spread()
        elif action == Action.EXIT and self.position_type is not None:
            self._exit_position("rl_decision")

    def _enter_long_spread(self):
        """Enter long spread position."""
        self.log.info(f"Entering LONG spread at z-score={self.current_zscore:.2f}")

        # Calculate position sizes
        account_value = 100000.0  # Placeholder
        position_value = account_value * self.config.position_size_pct

        # Buy A, Sell B
        price_a = float(self.bars_a[-1].close) if self.bars_a else 100.0
        price_b = float(self.bars_b[-1].close) if self.bars_b else 100.0

        qty_a = int(position_value / price_a)
        qty_b = int(position_value / price_b)

        if qty_a > 0:
            order_a = self.order_factory.market(
                instrument_id=self.instrument_a,
                order_side=OrderSide.BUY,
                quantity=Decimal(str(qty_a)),
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order_a)

        if qty_b > 0:
            order_b = self.order_factory.market(
                instrument_id=self.instrument_b,
                order_side=OrderSide.SELL,
                quantity=Decimal(str(qty_b)),
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order_b)

        self.position_type = "long_spread"
        self.entry_zscore = self.current_zscore
        self.entry_bar = self._bar_count
        self.bars_held = 0
        self.max_favorable_pnl = 0.0
        self.max_adverse_pnl = 0.0

    def _enter_short_spread(self):
        """Enter short spread position."""
        self.log.info(f"Entering SHORT spread at z-score={self.current_zscore:.2f}")

        account_value = 100000.0
        position_value = account_value * self.config.position_size_pct

        price_a = float(self.bars_a[-1].close) if self.bars_a else 100.0
        price_b = float(self.bars_b[-1].close) if self.bars_b else 100.0

        qty_a = int(position_value / price_a)
        qty_b = int(position_value / price_b)

        if qty_a > 0:
            order_a = self.order_factory.market(
                instrument_id=self.instrument_a,
                order_side=OrderSide.SELL,
                quantity=Decimal(str(qty_a)),
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order_a)

        if qty_b > 0:
            order_b = self.order_factory.market(
                instrument_id=self.instrument_b,
                order_side=OrderSide.BUY,
                quantity=Decimal(str(qty_b)),
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order_b)

        self.position_type = "short_spread"
        self.entry_zscore = self.current_zscore
        self.entry_bar = self._bar_count
        self.bars_held = 0
        self.max_favorable_pnl = 0.0
        self.max_adverse_pnl = 0.0

    def _exit_position(self, reason: str):
        """Exit current position and calculate rewards."""
        self.log.info(f"Exiting position: {reason} (z-score={self.current_zscore:.2f})")

        # Close all positions
        for position in self.cache.positions_open():
            self.close_position(position)

        # Calculate final reward
        pnl = self._calculate_unrealized_pnl()

        # Create trade record for reward calculation
        trade = Trade(
            instrument_id=f"{self.instrument_a}-{self.instrument_b}",
            entry_price=self.entry_zscore,
            exit_price=self.current_zscore,
            quantity=1,
            direction=self.position_type or "unknown",
            pnl=pnl,
            cost=10000.0,  # Placeholder
            max_favorable_excursion=self.max_favorable_pnl,
            max_adverse_excursion=self.max_adverse_pnl,
            holding_bars=self.bars_held,
            exit_reason=reason,
        )

        # Store completed trade experience
        self._complete_trajectory(trade)

        # Reset position state
        self.position_type = None
        self.entry_zscore = 0.0
        self.bars_held = 0
        self.max_favorable_pnl = 0.0
        self.max_adverse_pnl = 0.0

    def _calculate_unrealized_pnl(self) -> float:
        """Calculate unrealized P&L for current position."""
        # Simplified: use z-score change as proxy for P&L
        if self.position_type == "long_spread":
            return (self.entry_zscore - self.current_zscore) * 100
        elif self.position_type == "short_spread":
            return (self.current_zscore - self.entry_zscore) * 100
        return 0.0

    def _store_experience(self, state: np.ndarray, action: Action):
        """Store experience for RL training."""
        if self._previous_state is not None and self._previous_action is not None:
            # Calculate step reward
            current_pnl = self._calculate_unrealized_pnl()
            previous_pnl = 0.0  # Simplified

            step_reward = self.reward_calculator.calculate_step_reward(
                current_pnl=current_pnl,
                previous_pnl=previous_pnl,
                portfolio_value=100000.0,
            )

            experience = Experience(
                state=self._previous_state.tolist(),
                action=int(self._previous_action),
                immediate_reward=step_reward,
                next_state=state.tolist(),
                done=False,
                timestamp=self._bar_count,
            )

            self._current_trajectory.append(experience)

        self._previous_state = state
        self._previous_action = action

    def _complete_trajectory(self, trade: Trade):
        """Complete trajectory with final reward and add to buffer."""
        if not self._current_trajectory or self.experience_buffer is None:
            self._current_trajectory = []
            return

        # Calculate seeing-out bonus
        from ajk_strategies.rl_framework.reward.reward_calculator import PortfolioSnapshot

        portfolio_before = PortfolioSnapshot(
            total_value=100000.0,
            cash=50000.0,
            unrealized_pnl=0.0,
            returns=[],
            current_drawdown=0.0,
            peak_value=100000.0,
        )

        portfolio_after = PortfolioSnapshot(
            total_value=100000.0 + trade.pnl,
            cash=50000.0 + trade.pnl,
            unrealized_pnl=0.0,
            returns=[trade.pnl / 100000.0],
            current_drawdown=0.0,
            peak_value=max(100000.0, 100000.0 + trade.pnl),
        )

        final_reward = self.reward_calculator.calculate_trade_reward(
            trade=trade,
            portfolio_before=portfolio_before,
            portfolio_after=portfolio_after,
        )

        # Assign credit through trajectory
        from ajk_strategies.rl_framework.reward.credit_assignment import NStepCreditAssignment

        credit_assigner = NStepCreditAssignment(n=10, gamma=0.99)
        self._current_trajectory = credit_assigner.assign_rewards(
            self._current_trajectory,
            final_reward,
        )

        # Add to experience buffer
        for exp in self._current_trajectory:
            self.experience_buffer.add(exp)

        # Clear trajectory
        self._current_trajectory = []

        self.log.info(
            f"Trade completed: PnL={trade.pnl:.2f}, "
            f"Capture ratio={trade.pnl/max(trade.max_favorable_excursion, 0.001):.2f}, "
            f"Final reward={final_reward:.3f}"
        )

    def on_stop(self):
        """Clean up on strategy stop."""
        # Close any open positions
        if self.position_type is not None:
            self._exit_position("strategy_stop")

        self.log.info("RL Pairs Trading strategy stopped")
