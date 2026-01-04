# -------------------------------------------------------------------------------------------------
#  RL-Enhanced Momentum Breakout Strategy
#  Combines technical breakout signals with reinforcement learning
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.indicators import AverageTrueRange
from nautilus_trader.indicators import RelativeStrengthIndex
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


class RLMomentumBreakoutConfig(StrategyConfig, frozen=True):
    """Configuration for RL-enhanced momentum breakout strategy."""

    instrument_ids: tuple[str, ...]  # e.g., ("NVDA.MOOMOO", "AMD.MOOMOO")
    benchmark_id: str = "SPY.MOOMOO"
    breakout_lookback: int = 20
    volume_multiplier: float = 1.5
    rsi_period: int = 14
    rsi_min: float = 55.0
    rsi_max: float = 75.0
    relative_strength_min: float = 0.02
    atr_period: int = 14
    profit_target_atr: float = 2.0
    trailing_stop_atr: float = 1.5
    position_size_pct: float = 0.02  # 2% per position (conservative)
    max_holding_bars: int = 50
    max_concurrent: int = 5
    use_rl: bool = True
    rl_model_path: str | None = None


class RLMomentumBreakoutStrategy(Strategy):
    """
    Multi-timeframe momentum breakout strategy with RL enhancement.

    The RL agent learns to:
    1. Time breakout entries for optimal momentum catch
    2. Hold trending positions longer (seeing out the move)
    3. Exit early on false breakouts
    4. Adapt position sizing to volatility regimes
    """

    def __init__(
        self,
        config: RLMomentumBreakoutConfig,
        rl_agent: RLAgent | None = None,
        experience_buffer: PrioritizedReplayBuffer | None = None,
    ):
        super().__init__(config)

        # Note: self.config is already set by parent class Strategy
        self.instruments = [InstrumentId.from_str(id_) for id_ in config.instrument_ids]
        self.benchmark = InstrumentId.from_str(config.benchmark_id)

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

        # Indicators per instrument
        self.rsi_indicators: dict[InstrumentId, RelativeStrengthIndex] = {}
        self.atr_indicators: dict[InstrumentId, AverageTrueRange] = {}
        self.ema_indicators: dict[InstrumentId, ExponentialMovingAverage] = {}

        # Price/volume history per instrument
        self.highs: dict[InstrumentId, deque] = {}
        self.lows: dict[InstrumentId, deque] = {}
        self.closes: dict[InstrumentId, deque] = {}
        self.volumes: dict[InstrumentId, deque] = {}
        self.bars: dict[InstrumentId, list[Bar]] = {}
        self.benchmark_prices: deque = deque(maxlen=config.breakout_lookback * 2)

        # Position tracking per instrument
        self.entry_prices: dict[InstrumentId, float] = {}
        self.highest_highs: dict[InstrumentId, float] = {}
        self.entry_bar: dict[InstrumentId, int] = {}
        self.bars_held: dict[InstrumentId, int] = {}
        self.max_favorable_pnl: dict[InstrumentId, float] = {}
        self.max_adverse_pnl: dict[InstrumentId, float] = {}

        # Experience tracking for RL
        self._trajectories: dict[InstrumentId, list[Experience]] = {}
        self._previous_states: dict[InstrumentId, np.ndarray] = {}
        self._previous_actions: dict[InstrumentId, Action] = {}
        self._bar_count: int = 0

    def on_start(self):
        """Initialize strategy on start."""
        for instrument_id in self.instruments:
            self.subscribe_quote_ticks(instrument_id)

            # Subscribe to bars using proper BarType
            bar_type = BarType.from_str(f"{instrument_id}-1-MINUTE-LAST-EXTERNAL")
            self.subscribe_bars(bar_type)

            # Initialize indicators
            self.rsi_indicators[instrument_id] = RelativeStrengthIndex(
                self.config.rsi_period
            )
            self.atr_indicators[instrument_id] = AverageTrueRange(
                self.config.atr_period
            )
            self.ema_indicators[instrument_id] = ExponentialMovingAverage(10)

            # Initialize price tracking
            max_len = self.config.breakout_lookback * 2
            self.highs[instrument_id] = deque(maxlen=max_len)
            self.lows[instrument_id] = deque(maxlen=max_len)
            self.closes[instrument_id] = deque(maxlen=max_len)
            self.volumes[instrument_id] = deque(maxlen=max_len)
            self.bars[instrument_id] = []

            # Initialize trajectory tracking
            self._trajectories[instrument_id] = []

        # Subscribe to benchmark using proper BarType
        benchmark_bar_type = BarType.from_str(f"{self.benchmark}-1-MINUTE-LAST-EXTERNAL")
        self.subscribe_bars(benchmark_bar_type)

        self.log.info(
            f"RL Momentum Breakout started with {len(self.instruments)} instruments"
        )

    def on_quote_tick(self, tick: QuoteTick):
        """Process quote tick for real-time monitoring."""
        # Could be used for more granular entry timing
        pass

    def on_bar(self, bar: Bar):
        """Process bar and generate signals."""
        self._bar_count += 1
        instrument_id = bar.bar_type.instrument_id

        # Update benchmark prices
        if instrument_id == self.benchmark:
            self.benchmark_prices.append(float(bar.close))
            return

        # Skip if not in our universe
        if instrument_id not in self.instruments:
            return

        # Update indicators
        close_price = float(bar.close)
        high_price = float(bar.high)
        low_price = float(bar.low)

        self.rsi_indicators[instrument_id].update_raw(close_price)
        self.atr_indicators[instrument_id].update_raw(high_price, low_price, close_price)
        self.ema_indicators[instrument_id].update_raw(close_price)

        # Track price history
        self.highs[instrument_id].append(high_price)
        self.lows[instrument_id].append(low_price)
        self.closes[instrument_id].append(close_price)
        self.volumes[instrument_id].append(float(bar.volume))
        self.bars[instrument_id].append(bar)

        # Trim bars list
        if len(self.bars[instrument_id]) > self.config.breakout_lookback * 2:
            self.bars[instrument_id] = self.bars[instrument_id][-self.config.breakout_lookback * 2:]

        # Need sufficient data
        if len(self.highs[instrument_id]) < self.config.breakout_lookback:
            return

        # Build current state
        current_state = self._build_state(instrument_id)

        # Get RL action
        if self.use_rl:
            action = self.rl_agent.act(current_state, explore=True)
        else:
            action = self._rule_based_action(bar, instrument_id)

        # Execute action
        self._execute_action(action, bar, instrument_id)

        # Track position P&L for MFE/MAE
        if instrument_id in self.entry_prices:
            self.bars_held[instrument_id] = self.bars_held.get(instrument_id, 0) + 1
            current_pnl = self._calculate_unrealized_pnl(instrument_id)
            self.max_favorable_pnl[instrument_id] = max(
                self.max_favorable_pnl.get(instrument_id, 0), current_pnl
            )
            self.max_adverse_pnl[instrument_id] = min(
                self.max_adverse_pnl.get(instrument_id, 0), current_pnl
            )

        # Store experience for RL training
        self._store_experience(instrument_id, current_state, action)

    def _build_state(self, instrument_id: InstrumentId) -> np.ndarray:
        """Build state vector for RL agent."""
        bars = self.bars.get(instrument_id, [])

        state = self.state_builder.build_state(
            bars=bars,
            portfolio=self.portfolio,
            position=None,
            account_value=100000.0,
        )

        # Add momentum-specific features
        closes = list(self.closes[instrument_id])
        volumes = list(self.volumes[instrument_id])
        highs = list(self.highs[instrument_id])

        # Recent momentum features
        if len(closes) >= 5:
            momentum_1d = (closes[-1] / closes[-2] - 1) if closes[-2] != 0 else 0
            momentum_5d = (closes[-1] / closes[-5] - 1) if closes[-5] != 0 else 0
        else:
            momentum_1d = 0
            momentum_5d = 0

        # Volume features
        if len(volumes) >= 5:
            avg_volume = np.mean(list(volumes)[-5:])
            volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        else:
            volume_ratio = 1

        # Breakout distance
        if len(highs) >= self.config.breakout_lookback:
            lookback_high = max(list(highs)[-self.config.breakout_lookback:-1])
            breakout_dist = (closes[-1] / lookback_high - 1) if lookback_high > 0 else 0
        else:
            breakout_dist = 0

        # RSI and ATR (normalized)
        rsi = self.rsi_indicators[instrument_id].value / 100.0 if self.rsi_indicators[instrument_id].initialized else 0.5
        atr = self.atr_indicators[instrument_id].value
        atr_pct = atr / closes[-1] if closes and closes[-1] > 0 else 0.02

        # Position status
        in_position = float(instrument_id in self.entry_prices)
        bars_held = self.bars_held.get(instrument_id, 0) / self.config.max_holding_bars

        momentum_features = np.array([
            momentum_1d * 10,  # Scale
            momentum_5d * 5,
            volume_ratio / 3,  # Normalize
            breakout_dist * 10,
            rsi,
            atr_pct * 10,
            in_position,
            bars_held,
        ])

        return np.concatenate([state, momentum_features])

    def _rule_based_action(self, bar: Bar, instrument_id: InstrumentId) -> Action:
        """Generate action using traditional breakout rules."""
        close_price = float(bar.close)
        highs = list(self.highs[instrument_id])
        volumes = list(self.volumes[instrument_id])

        # If in position, check exits
        if instrument_id in self.entry_prices:
            entry_price = self.entry_prices[instrument_id]
            atr_value = self.atr_indicators[instrument_id].value

            if atr_value > 0:
                # Profit target
                profit_target_price = entry_price + (self.config.profit_target_atr * atr_value)
                if close_price >= profit_target_price:
                    return Action.EXIT

                # Trailing stop
                highest = self.highest_highs.get(instrument_id, entry_price)
                trailing_stop_price = highest - (self.config.trailing_stop_atr * atr_value)
                if close_price <= trailing_stop_price:
                    return Action.EXIT

            # EMA breakdown
            ema_value = self.ema_indicators[instrument_id].value
            if close_price < ema_value:
                return Action.EXIT

            # Time stop
            if self.bars_held.get(instrument_id, 0) >= self.config.max_holding_bars:
                return Action.EXIT

            return Action.HOLD

        # Check concurrent position limit
        open_positions = len([i for i in self.instruments if i in self.entry_prices])
        if open_positions >= self.config.max_concurrent:
            return Action.HOLD

        # Entry signals - breakout condition
        if len(highs) < self.config.breakout_lookback:
            return Action.HOLD

        lookback_high = max(highs[-self.config.breakout_lookback:-1])
        if close_price <= lookback_high:
            return Action.HOLD

        # Volume confirmation
        avg_volume = np.mean(volumes[-self.config.breakout_lookback:])
        if volumes[-1] < avg_volume * self.config.volume_multiplier:
            return Action.HOLD

        # RSI filter
        rsi_value = self.rsi_indicators[instrument_id].value
        if not (self.config.rsi_min <= rsi_value <= self.config.rsi_max):
            return Action.HOLD

        # Relative strength check
        if not self._check_relative_strength(instrument_id):
            return Action.HOLD

        return Action.BUY

    def _check_relative_strength(self, instrument_id: InstrumentId) -> bool:
        """Check if instrument is outperforming benchmark."""
        if len(self.benchmark_prices) < self.config.breakout_lookback:
            return True  # Allow if no benchmark data

        closes = list(self.closes[instrument_id])
        if len(closes) < self.config.breakout_lookback:
            return True

        # Calculate returns over lookback period
        instrument_return = (closes[-1] / closes[-self.config.breakout_lookback] - 1)
        benchmark_prices = list(self.benchmark_prices)
        benchmark_return = (benchmark_prices[-1] / benchmark_prices[-self.config.breakout_lookback] - 1)

        relative_strength = instrument_return - benchmark_return
        return relative_strength >= self.config.relative_strength_min

    def _execute_action(self, action: Action, bar: Bar, instrument_id: InstrumentId):
        """Execute the RL action."""
        if action == Action.BUY and instrument_id not in self.entry_prices:
            self._enter_long(bar, instrument_id)
        elif action == Action.EXIT and instrument_id in self.entry_prices:
            self._exit_position(instrument_id, "rl_decision")

    def _enter_long(self, bar: Bar, instrument_id: InstrumentId):
        """Enter long position."""
        close_price = float(bar.close)
        rsi_value = self.rsi_indicators[instrument_id].value
        volumes = list(self.volumes[instrument_id])
        avg_volume = np.mean(volumes[-self.config.breakout_lookback:]) if volumes else 1

        self.log.info(
            f"Entering LONG {instrument_id} @ {close_price:.2f} "
            f"(RSI={rsi_value:.1f}, Vol={volumes[-1]/avg_volume:.1f}x)"
        )

        # Calculate position size
        account_value = 100000.0  # Placeholder
        position_value = account_value * self.config.position_size_pct
        quantity = int(position_value / close_price)

        if quantity > 0:
            order = self.order_factory.market(
                instrument_id=instrument_id,
                order_side=OrderSide.BUY,
                quantity=Decimal(str(quantity)),
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order)

        # Track entry
        self.entry_prices[instrument_id] = close_price
        self.highest_highs[instrument_id] = close_price
        self.entry_bar[instrument_id] = self._bar_count
        self.bars_held[instrument_id] = 0
        self.max_favorable_pnl[instrument_id] = 0.0
        self.max_adverse_pnl[instrument_id] = 0.0

    def _exit_position(self, instrument_id: InstrumentId, reason: str):
        """Exit position and calculate rewards."""
        entry_price = self.entry_prices.get(instrument_id)
        if entry_price is None:
            return

        close_price = float(self.closes[instrument_id][-1]) if self.closes[instrument_id] else entry_price

        self.log.info(f"Exiting {instrument_id}: {reason} (entry={entry_price:.2f}, exit={close_price:.2f})")

        # Close position
        for position in self.cache.positions_open():
            if position.instrument_id == instrument_id:
                self.close_position(position)

        # Calculate final reward
        pnl = (close_price - entry_price) * 100  # Scaled for 100 shares

        # Create trade record
        trade = Trade(
            instrument_id=str(instrument_id),
            entry_price=entry_price,
            exit_price=close_price,
            quantity=100,
            direction="long",
            pnl=pnl,
            cost=entry_price * 100,
            max_favorable_excursion=self.max_favorable_pnl.get(instrument_id, 0),
            max_adverse_excursion=self.max_adverse_pnl.get(instrument_id, 0),
            holding_bars=self.bars_held.get(instrument_id, 0),
            exit_reason=reason,
        )

        # Store completed trade experience
        self._complete_trajectory(instrument_id, trade)

        # Clean up tracking
        self.entry_prices.pop(instrument_id, None)
        self.highest_highs.pop(instrument_id, None)
        self.entry_bar.pop(instrument_id, None)
        self.bars_held.pop(instrument_id, None)
        self.max_favorable_pnl.pop(instrument_id, None)
        self.max_adverse_pnl.pop(instrument_id, None)

    def _calculate_unrealized_pnl(self, instrument_id: InstrumentId) -> float:
        """Calculate unrealized P&L for current position."""
        entry_price = self.entry_prices.get(instrument_id)
        if entry_price is None:
            return 0.0

        closes = self.closes.get(instrument_id)
        if not closes:
            return 0.0

        current_price = closes[-1]
        return (current_price - entry_price) * 100  # Scaled for 100 shares

    def _store_experience(self, instrument_id: InstrumentId, state: np.ndarray, action: Action):
        """Store experience for RL training."""
        prev_state = self._previous_states.get(instrument_id)
        prev_action = self._previous_actions.get(instrument_id)

        if prev_state is not None and prev_action is not None:
            # Calculate step reward
            current_pnl = self._calculate_unrealized_pnl(instrument_id)
            step_reward = self.reward_calculator.calculate_step_reward(
                current_pnl=current_pnl,
                previous_pnl=0.0,  # Simplified
                portfolio_value=100000.0,
            )

            experience = Experience(
                state=prev_state.tolist(),
                action=int(prev_action),
                immediate_reward=step_reward,
                next_state=state.tolist(),
                done=False,
                timestamp=self._bar_count,
            )

            if instrument_id not in self._trajectories:
                self._trajectories[instrument_id] = []
            self._trajectories[instrument_id].append(experience)

        self._previous_states[instrument_id] = state
        self._previous_actions[instrument_id] = action

    def _complete_trajectory(self, instrument_id: InstrumentId, trade: Trade):
        """Complete trajectory with final reward and add to buffer."""
        trajectory = self._trajectories.get(instrument_id, [])
        if not trajectory or self.experience_buffer is None:
            self._trajectories[instrument_id] = []
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
        trajectory = credit_assigner.assign_rewards(trajectory, final_reward)

        # Add to experience buffer
        for exp in trajectory:
            self.experience_buffer.add(exp)

        # Clear trajectory
        self._trajectories[instrument_id] = []

        # Log trade summary
        capture_ratio = trade.pnl / max(trade.max_favorable_excursion, 0.001)
        self.log.info(
            f"Trade completed {instrument_id}: PnL={trade.pnl:.2f}, "
            f"Capture ratio={capture_ratio:.2f}, "
            f"Final reward={final_reward:.3f}"
        )

    def on_stop(self):
        """Clean up on strategy stop."""
        # Close all open positions
        for instrument_id in list(self.entry_prices.keys()):
            self._exit_position(instrument_id, "strategy_stop")

        self.log.info("RL Momentum Breakout strategy stopped")
