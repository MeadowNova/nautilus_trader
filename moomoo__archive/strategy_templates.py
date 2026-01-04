"""
Trading Strategy Templates for NautilusTrader + Moomoo
======================================================

This module provides implementation templates for three systematic trading strategies:
1. Statistical Arbitrage Pairs Trading
2. Momentum Breakout Trading
3. Covered Call Income Strategy

Each template includes:
- Strategy class skeleton
- Parameter configuration
- Risk management logic
- Position sizing
- Entry/exit signal generation

Author: Quantitative Strategy Team
Date: 2025-12-05
"""

from decimal import Decimal
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.message import Event
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.indicators.atr import AverageTrueRange
from nautilus_trader.indicators.rsi import RelativeStrengthIndex
from nautilus_trader.model.data import Bar, QuoteTick
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy
from scipy import stats


# ============================================================================
# STRATEGY 1: STATISTICAL ARBITRAGE PAIRS TRADING
# ============================================================================


class PairsTradingConfig(StrategyConfig):
    """Configuration for pairs trading strategy."""

    instrument_id_long: str  # e.g., "XLE.ARCA"
    instrument_id_short: str  # e.g., "XOP.ARCA"
    lookback_period: int = 60  # days
    zscore_entry: float = 2.0  # standard deviations
    zscore_exit: float = 0.5  # mean reversion threshold
    zscore_stop: float = 3.0  # stop loss threshold
    position_size_pct: float = 0.10  # 10% per leg
    max_holding_days: int = 5
    min_correlation: float = 0.85
    cointegration_pvalue: float = 0.05
    slippage_bps: float = 5.0
    spread_cost_bps: float = 2.0


class PairsTradingStrategy(Strategy):
    """
    Mean reversion pairs trading strategy.

    Trades statistical deviations in correlated ETF pairs.
    Maintains market neutrality with long/short positions.
    """

    def __init__(self, config: PairsTradingConfig):
        super().__init__(config)

        # Configuration
        self.instrument_long = InstrumentId.from_str(config.instrument_id_long)
        self.instrument_short = InstrumentId.from_str(config.instrument_id_short)
        self.lookback = config.lookback_period
        self.zscore_entry = config.zscore_entry
        self.zscore_exit = config.zscore_exit
        self.zscore_stop = config.zscore_stop
        self.position_size_pct = config.position_size_pct
        self.max_holding_days = config.max_holding_days

        # State tracking
        self.prices_long: List[float] = []
        self.prices_short: List[float] = []
        self.spread_mean: Optional[float] = None
        self.spread_std: Optional[float] = None
        self.current_zscore: float = 0.0
        self.entry_time: Optional[pd.Timestamp] = None
        self.position_type: Optional[str] = None  # "long_spread" or "short_spread"

        # Risk metrics
        self.max_drawdown: float = 0.0
        self.peak_equity: float = 0.0

    def on_start(self):
        """Initialize strategy on start."""
        # Subscribe to quote data for both instruments
        self.subscribe_quote_ticks(self.instrument_long)
        self.subscribe_quote_ticks(self.instrument_short)

        # Subscribe to daily bars for spread calculation
        self.subscribe_bars(self.instrument_long)
        self.subscribe_bars(self.instrument_short)

        self.log.info(
            f"Pairs trading started: {self.instrument_long} vs {self.instrument_short}"
        )

    def on_quote_tick(self, tick: QuoteTick):
        """Process quote tick for spread monitoring."""
        # Update price series
        if tick.instrument_id == self.instrument_long:
            self.prices_long.append(float(tick.bid_price))
        elif tick.instrument_id == self.instrument_short:
            self.prices_short.append(float(tick.ask_price))

        # Trim to lookback window
        if len(self.prices_long) > self.lookback * 390:  # 390 minutes per day
            self.prices_long = self.prices_long[-self.lookback * 390 :]
            self.prices_short = self.prices_short[-self.lookback * 390 :]

        # Need sufficient data for both
        if len(self.prices_long) < 100 or len(self.prices_short) < 100:
            return

        # Calculate spread and z-score
        self._update_spread_statistics()
        self._check_signals()

    def on_bar(self, bar: Bar):
        """Process bar for spread calculation."""
        # Daily recalibration of spread statistics
        if bar.is_single_price():
            return

        self._update_spread_statistics()
        self._check_risk_limits()

    def _update_spread_statistics(self):
        """Calculate spread mean, std, and z-score."""
        if len(self.prices_long) < self.lookback or len(self.prices_short) < self.lookback:
            return

        # Align series
        min_len = min(len(self.prices_long), len(self.prices_short))
        prices_long = np.array(self.prices_long[-min_len:])
        prices_short = np.array(self.prices_short[-min_len:])

        # Calculate spread (price ratio)
        spread = prices_long / prices_short

        # Rolling statistics
        self.spread_mean = np.mean(spread)
        self.spread_std = np.std(spread)

        # Current z-score
        current_spread = prices_long[-1] / prices_short[-1]
        if self.spread_std > 0:
            self.current_zscore = (current_spread - self.spread_mean) / self.spread_std
        else:
            self.current_zscore = 0.0

    def _check_cointegration(self) -> bool:
        """Test for cointegration using Augmented Dickey-Fuller test."""
        if len(self.prices_long) < self.lookback or len(self.prices_short) < self.lookback:
            return False

        min_len = min(len(self.prices_long), len(self.prices_short))
        prices_long = np.array(self.prices_long[-min_len:])
        prices_short = np.array(self.prices_short[-min_len:])

        # Run cointegration test (simplified)
        spread = prices_long - prices_short
        # In production, use statsmodels.tsa.stattools.adfuller
        # adf_result = adfuller(spread)
        # return adf_result[1] < self.config.cointegration_pvalue

        # Placeholder: assume cointegrated if correlation > threshold
        correlation = np.corrcoef(prices_long, prices_short)[0, 1]
        return correlation > self.config.min_correlation

    def _check_signals(self):
        """Check for entry and exit signals."""
        # Skip if insufficient data
        if self.spread_mean is None or self.spread_std is None:
            return

        # Check cointegration
        if not self._check_cointegration():
            self.log.warning("Pair not cointegrated, skipping signals")
            return

        # Exit signals (if in position)
        if self.position_type is not None:
            self._check_exit_signals()
            return

        # Entry signals (if flat)
        self._check_entry_signals()

    def _check_entry_signals(self):
        """Check for entry signals."""
        # Long spread signal (spread compressed)
        if self.current_zscore < -self.zscore_entry:
            self.log.info(
                f"Entry signal: LONG spread (z-score={self.current_zscore:.2f})"
            )
            self._enter_long_spread()

        # Short spread signal (spread extended)
        elif self.current_zscore > self.zscore_entry:
            self.log.info(
                f"Entry signal: SHORT spread (z-score={self.current_zscore:.2f})"
            )
            self._enter_short_spread()

    def _check_exit_signals(self):
        """Check for exit signals."""
        # Profit target: z-score reverts to mean
        if abs(self.current_zscore) < self.zscore_exit:
            self.log.info(
                f"Exit signal: PROFIT TARGET (z-score={self.current_zscore:.2f})"
            )
            self._exit_position("profit_target")
            return

        # Stop loss: z-score extends further
        if abs(self.current_zscore) > self.zscore_stop:
            self.log.warning(
                f"Exit signal: STOP LOSS (z-score={self.current_zscore:.2f})"
            )
            self._exit_position("stop_loss")
            return

        # Time stop: max holding period exceeded
        if self.entry_time is not None:
            days_held = (self.clock.utc_now() - self.entry_time).days
            if days_held >= self.max_holding_days:
                self.log.info(
                    f"Exit signal: TIME STOP (held {days_held} days)"
                )
                self._exit_position("time_stop")
                return

    def _enter_long_spread(self):
        """Enter long spread position (buy underperformer, sell outperformer)."""
        # Calculate position sizes
        account_balance = self.portfolio.account(self.venue).balance_total(self.currency).as_double()
        position_value = account_balance * self.position_size_pct

        # Buy long instrument
        instrument_long = self.cache.instrument(self.instrument_long)
        quantity_long = self._calculate_quantity(position_value, instrument_long)
        self._submit_market_order(self.instrument_long, OrderSide.BUY, quantity_long)

        # Sell short instrument
        instrument_short = self.cache.instrument(self.instrument_short)
        quantity_short = self._calculate_quantity(position_value, instrument_short)
        self._submit_market_order(self.instrument_short, OrderSide.SELL, quantity_short)

        # Update state
        self.position_type = "long_spread"
        self.entry_time = self.clock.utc_now()

    def _enter_short_spread(self):
        """Enter short spread position (sell underperformer, buy outperformer)."""
        account_balance = self.portfolio.account(self.venue).balance_total(self.currency).as_double()
        position_value = account_balance * self.position_size_pct

        # Sell long instrument
        instrument_long = self.cache.instrument(self.instrument_long)
        quantity_long = self._calculate_quantity(position_value, instrument_long)
        self._submit_market_order(self.instrument_long, OrderSide.SELL, quantity_long)

        # Buy short instrument
        instrument_short = self.cache.instrument(self.instrument_short)
        quantity_short = self._calculate_quantity(position_value, instrument_short)
        self._submit_market_order(self.instrument_short, OrderSide.BUY, quantity_short)

        # Update state
        self.position_type = "short_spread"
        self.entry_time = self.clock.utc_now()

    def _exit_position(self, reason: str):
        """Exit current spread position."""
        # Close both legs
        position_long = self.cache.position(self.instrument_long)
        position_short = self.cache.position(self.instrument_short)

        if position_long is not None and position_long.is_open:
            self._close_position(position_long)

        if position_short is not None and position_short.is_open:
            self._close_position(position_short)

        # Reset state
        self.position_type = None
        self.entry_time = None

        self.log.info(f"Position closed: {reason}")

    def _submit_market_order(
        self, instrument_id: InstrumentId, side: OrderSide, quantity: Decimal
    ):
        """Submit market order with risk checks."""
        order = self.order_factory.market(
            instrument_id=instrument_id,
            order_side=side,
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)

    def _calculate_quantity(self, position_value: float, instrument: Instrument) -> Decimal:
        """Calculate order quantity based on position value."""
        # Simplified: position_value / current_price
        # In production, use latest quote
        price = 100.0  # Placeholder
        quantity = position_value / price
        return Decimal(str(int(quantity)))  # Round to whole shares

    def _check_risk_limits(self):
        """Check portfolio-level risk limits."""
        # Calculate current equity
        equity = self.portfolio.account(self.venue).balance_total(self.currency).as_double()

        # Track peak and drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity

        current_drawdown = (self.peak_equity - equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown

        # Emergency stop if drawdown exceeds 15%
        if current_drawdown > 0.15:
            self.log.error(f"Max drawdown exceeded: {current_drawdown:.2%}")
            self._exit_position("emergency_stop")
            self.stop()


# ============================================================================
# STRATEGY 2: MOMENTUM BREAKOUT TRADING
# ============================================================================


class MomentumBreakoutConfig(StrategyConfig):
    """Configuration for momentum breakout strategy."""

    instrument_ids: List[str]  # e.g., ["NVDA.NASDAQ", "AMD.NASDAQ"]
    benchmark_id: str = "SPY.ARCA"  # For relative strength
    breakout_lookback: int = 20
    volume_multiplier: float = 1.5
    rsi_period: int = 14
    rsi_min: float = 55.0
    rsi_max: float = 75.0
    relative_strength_min: float = 0.02  # 2% outperformance
    atr_period: int = 14
    profit_target_atr: float = 2.0
    trailing_stop_atr: float = 1.5
    position_size_pct: float = 0.08
    max_holding_days: int = 10
    max_concurrent: int = 5
    slippage_bps: float = 10.0


class MomentumBreakoutStrategy(Strategy):
    """
    Multi-timeframe momentum breakout strategy.

    Trades price breakouts with volume and RSI confirmation.
    Uses trailing stops and profit targets based on ATR.
    """

    def __init__(self, config: MomentumBreakoutConfig):
        super().__init__(config)

        # Configuration
        self.instruments = [InstrumentId.from_str(id) for id in config.instrument_ids]
        self.benchmark = InstrumentId.from_str(config.benchmark_id)
        self.breakout_lookback = config.breakout_lookback
        self.volume_multiplier = config.volume_multiplier
        self.rsi_min = config.rsi_min
        self.rsi_max = config.rsi_max
        self.rs_min = config.relative_strength_min
        self.profit_target_atr = config.profit_target_atr
        self.trailing_stop_atr = config.trailing_stop_atr
        self.position_size_pct = config.position_size_pct
        self.max_concurrent = config.max_concurrent

        # Indicators (per instrument)
        self.rsi_indicators: Dict[InstrumentId, RelativeStrengthIndex] = {}
        self.atr_indicators: Dict[InstrumentId, AverageTrueRange] = {}
        self.ema_indicators: Dict[InstrumentId, ExponentialMovingAverage] = {}

        # Price history
        self.highs: Dict[InstrumentId, List[float]] = {}
        self.volumes: Dict[InstrumentId, List[float]] = {}
        self.benchmark_prices: List[float] = []

        # Position tracking
        self.entry_prices: Dict[InstrumentId, float] = {}
        self.highest_highs: Dict[InstrumentId, float] = {}
        self.entry_times: Dict[InstrumentId, pd.Timestamp] = {}

    def on_start(self):
        """Initialize strategy on start."""
        # Subscribe to data for all instruments
        for instrument_id in self.instruments:
            self.subscribe_quote_ticks(instrument_id)
            self.subscribe_bars(instrument_id)

            # Initialize indicators
            self.rsi_indicators[instrument_id] = RelativeStrengthIndex(
                self.config.rsi_period
            )
            self.atr_indicators[instrument_id] = AverageTrueRange(
                self.config.atr_period
            )
            self.ema_indicators[instrument_id] = ExponentialMovingAverage(10)

            # Initialize price tracking
            self.highs[instrument_id] = []
            self.volumes[instrument_id] = []

        # Subscribe to benchmark
        self.subscribe_bars(self.benchmark)

        self.log.info(
            f"Momentum breakout started with {len(self.instruments)} instruments"
        )

    def on_bar(self, bar: Bar):
        """Process bar for breakout detection."""
        instrument_id = bar.bar_type.instrument_id

        # Update benchmark prices
        if instrument_id == self.benchmark:
            self.benchmark_prices.append(float(bar.close))
            return

        # Skip if not in our universe
        if instrument_id not in self.instruments:
            return

        # Update indicators
        self.rsi_indicators[instrument_id].update_raw(
            float(bar.close.as_double())
        )
        self.atr_indicators[instrument_id].update_raw(
            float(bar.high.as_double()),
            float(bar.low.as_double()),
            float(bar.close.as_double()),
        )
        self.ema_indicators[instrument_id].update_raw(
            float(bar.close.as_double())
        )

        # Track highs and volumes
        self.highs[instrument_id].append(float(bar.high.as_double()))
        self.volumes[instrument_id].append(float(bar.volume))

        # Trim to lookback
        if len(self.highs[instrument_id]) > self.breakout_lookback:
            self.highs[instrument_id] = self.highs[instrument_id][-self.breakout_lookback :]
            self.volumes[instrument_id] = self.volumes[instrument_id][-self.breakout_lookback :]

        # Check signals
        position = self.cache.position(instrument_id)
        if position is not None and position.is_open:
            self._check_exit_signals(bar, instrument_id)
        else:
            self._check_entry_signals(bar, instrument_id)

    def _check_entry_signals(self, bar: Bar, instrument_id: InstrumentId):
        """Check for breakout entry signals."""
        # Need sufficient data
        if len(self.highs[instrument_id]) < self.breakout_lookback:
            return

        # Check concurrent position limit
        open_positions = len([p for p in self.cache.positions() if p.is_open])
        if open_positions >= self.max_concurrent:
            return

        # Breakout condition: close above N-day high
        close_price = float(bar.close.as_double())
        lookback_high = max(self.highs[instrument_id][:-1])  # Exclude current bar

        if close_price <= lookback_high:
            return

        # Volume confirmation
        current_volume = float(bar.volume)
        avg_volume = np.mean(self.volumes[instrument_id])
        if current_volume < avg_volume * self.volume_multiplier:
            return

        # RSI filter
        rsi_value = self.rsi_indicators[instrument_id].value
        if not (self.rsi_min <= rsi_value <= self.rsi_max):
            return

        # Relative strength vs benchmark
        if not self._check_relative_strength(instrument_id):
            return

        # ATR filter (sufficient volatility)
        atr_value = self.atr_indicators[instrument_id].value
        if atr_value <= 0:
            return

        # All conditions met - enter position
        self.log.info(
            f"Breakout signal: {instrument_id} @ {close_price:.2f} "
            f"(RSI={rsi_value:.1f}, Vol={current_volume/avg_volume:.1f}x)"
        )
        self._enter_long(bar, instrument_id)

    def _check_exit_signals(self, bar: Bar, instrument_id: InstrumentId):
        """Check for exit signals on open position."""
        close_price = float(bar.close.as_double())
        entry_price = self.entry_prices.get(instrument_id)
        atr_value = self.atr_indicators[instrument_id].value

        if entry_price is None or atr_value <= 0:
            return

        # Update highest high for trailing stop
        if close_price > self.highest_highs.get(instrument_id, 0):
            self.highest_highs[instrument_id] = close_price

        # Profit target: 2x ATR or 5% gain
        profit_pct = (close_price - entry_price) / entry_price
        profit_target_price = entry_price + (self.profit_target_atr * atr_value)

        if close_price >= profit_target_price or profit_pct >= 0.05:
            self.log.info(
                f"Exit signal: PROFIT TARGET {instrument_id} "
                f"(gain={profit_pct:.2%})"
            )
            self._exit_position(instrument_id, "profit_target")
            return

        # Trailing stop: 1.5x ATR from highest high
        trailing_stop_price = self.highest_highs[instrument_id] - (
            self.trailing_stop_atr * atr_value
        )
        if close_price <= trailing_stop_price:
            self.log.info(
                f"Exit signal: TRAILING STOP {instrument_id} "
                f"(price={close_price:.2f}, stop={trailing_stop_price:.2f})"
            )
            self._exit_position(instrument_id, "trailing_stop")
            return

        # Breakdown: close below 10-EMA
        ema_value = self.ema_indicators[instrument_id].value
        if close_price < ema_value:
            self.log.info(
                f"Exit signal: BREAKDOWN {instrument_id} "
                f"(price={close_price:.2f}, EMA={ema_value:.2f})"
            )
            self._exit_position(instrument_id, "breakdown")
            return

        # Time stop
        entry_time = self.entry_times.get(instrument_id)
        if entry_time is not None:
            days_held = (self.clock.utc_now() - entry_time).days
            if days_held >= self.config.max_holding_days:
                self.log.info(
                    f"Exit signal: TIME STOP {instrument_id} (held {days_held} days)"
                )
                self._exit_position(instrument_id, "time_stop")
                return

    def _check_relative_strength(self, instrument_id: InstrumentId) -> bool:
        """Check if instrument is outperforming benchmark."""
        if len(self.benchmark_prices) < self.breakout_lookback:
            return False
        if len(self.highs[instrument_id]) < self.breakout_lookback:
            return False

        # Calculate returns over lookback period
        instrument_return = (
            self.highs[instrument_id][-1] / self.highs[instrument_id][0]
        ) - 1.0
        benchmark_return = (
            self.benchmark_prices[-1] / self.benchmark_prices[-self.breakout_lookback]
        ) - 1.0

        relative_strength = instrument_return - benchmark_return
        return relative_strength >= self.rs_min

    def _enter_long(self, bar: Bar, instrument_id: InstrumentId):
        """Enter long position."""
        # Calculate position size
        account_balance = self.portfolio.account(self.venue).balance_total(self.currency).as_double()
        position_value = account_balance * self.position_size_pct
        price = float(bar.close.as_double())
        quantity = Decimal(str(int(position_value / price)))

        # Submit order
        order = self.order_factory.market(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)

        # Track entry
        self.entry_prices[instrument_id] = price
        self.highest_highs[instrument_id] = price
        self.entry_times[instrument_id] = self.clock.utc_now()

    def _exit_position(self, instrument_id: InstrumentId, reason: str):
        """Exit position."""
        position = self.cache.position(instrument_id)
        if position is not None and position.is_open:
            self._close_position(position)

        # Clean up tracking
        self.entry_prices.pop(instrument_id, None)
        self.highest_highs.pop(instrument_id, None)
        self.entry_times.pop(instrument_id, None)

        self.log.info(f"Position closed: {instrument_id} ({reason})")


# ============================================================================
# STRATEGY 3: COVERED CALL INCOME STRATEGY
# ============================================================================


class CoveredCallConfig(StrategyConfig):
    """Configuration for covered call strategy."""

    stock_symbols: List[str]  # e.g., ["JNJ", "PG", "KO"]
    dte_min: int = 30
    dte_max: int = 45
    delta_target: float = 0.30
    delta_max: float = 0.35
    min_premium_pct: float = 0.01  # 1% of stock price
    profit_target_pct: float = 0.50  # 50% of max profit
    roll_threshold_dte: int = 7
    roll_delta_threshold: float = 0.95
    min_iv_rank: float = 40.0
    shares_per_position: int = 100
    max_positions: int = 5


class CoveredCallStrategy(Strategy):
    """
    Covered call income strategy on dividend stocks.

    Sells out-of-the-money calls against stock positions
    to generate income while maintaining upside participation.
    """

    def __init__(self, config: CoveredCallConfig):
        super().__init__(config)

        # Configuration
        self.stock_symbols = config.stock_symbols
        self.dte_min = config.dte_min
        self.dte_max = config.dte_max
        self.delta_target = config.delta_target
        self.min_premium_pct = config.min_premium_pct
        self.profit_target_pct = config.profit_target_pct
        self.shares_per_position = config.shares_per_position

        # Position tracking
        self.stock_positions: Dict[str, int] = {}  # symbol -> shares
        self.option_positions: Dict[str, Dict] = {}  # symbol -> option details
        self.entry_premiums: Dict[str, float] = {}  # symbol -> premium received

    def on_start(self):
        """Initialize strategy on start."""
        # Subscribe to stock quotes
        for symbol in self.stock_symbols:
            instrument_id = InstrumentId.from_str(f"{symbol}.NASDAQ")
            self.subscribe_quote_ticks(instrument_id)

            # In production, subscribe to option chains
            # self.subscribe_option_chain(instrument_id)

        self.log.info(
            f"Covered call strategy started with {len(self.stock_symbols)} stocks"
        )

    def on_quote_tick(self, tick: QuoteTick):
        """Monitor option positions and check profit targets."""
        symbol = tick.instrument_id.symbol.value

        # Check if we have an option position
        if symbol not in self.option_positions:
            return

        # Calculate current option value (simplified)
        # In production, get actual option quote
        option_details = self.option_positions[symbol]
        entry_premium = self.entry_premiums.get(symbol, 0)

        # Placeholder: assume option value = $0.25 (check actual market)
        current_option_value = 0.25

        # Profit taking: close at 50% profit
        profit_pct = (entry_premium - current_option_value) / entry_premium
        if profit_pct >= self.profit_target_pct:
            self.log.info(
                f"Profit target reached for {symbol}: {profit_pct:.1%}"
            )
            self._close_call_option(symbol)

    def on_option_chain(self, chain):
        """
        Process option chain data to select and sell calls.

        This is a placeholder - in production, implement:
        1. Filter by DTE (30-45 days)
        2. Select strike with delta ~0.30
        3. Check premium > 1% of stock price
        4. Submit sell-to-open order
        """
        # Example logic:
        # for option in chain.options:
        #     if self.dte_min <= option.dte <= self.dte_max:
        #         if abs(option.delta - self.delta_target) < 0.05:
        #             if option.premium / stock_price > self.min_premium_pct:
        #                 self._sell_call_option(option)
        pass

    def _sell_call_option(self, symbol: str, strike: float, expiration: str, premium: float):
        """Sell covered call option."""
        # Check if we own stock
        if symbol not in self.stock_positions:
            self.log.warning(f"No stock position for {symbol}, cannot sell call")
            return

        # Submit sell-to-open order
        # In production: self.submit_option_order(...)
        self.log.info(
            f"Sold call: {symbol} ${strike} exp {expiration} @ ${premium}"
        )

        # Track position
        self.option_positions[symbol] = {
            "strike": strike,
            "expiration": expiration,
            "premium": premium,
        }
        self.entry_premiums[symbol] = premium

    def _close_call_option(self, symbol: str):
        """Buy back (close) call option."""
        if symbol not in self.option_positions:
            return

        # Submit buy-to-close order
        # In production: self.submit_option_order(...)
        self.log.info(f"Closed call: {symbol}")

        # Clean up tracking
        self.option_positions.pop(symbol, None)
        self.entry_premiums.pop(symbol, None)

    def _check_dividend_calendar(self, symbol: str) -> bool:
        """
        Check if stock has upcoming ex-dividend date.

        Returns True if safe to sell calls, False if too close to ex-date.
        """
        # In production, query dividend calendar
        # Avoid selling calls within 5 days of ex-dividend
        return True


# ============================================================================
# RISK MANAGEMENT UTILITIES
# ============================================================================


class PositionSizer:
    """Position sizing utilities using Kelly criterion and fixed fractional."""

    @staticmethod
    def kelly_position_size(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fractional: float = 0.5,
    ) -> float:
        """
        Calculate position size using Kelly criterion.

        Parameters:
        - win_rate: probability of winning trade (0-1)
        - avg_win: average win as ratio (e.g., 0.04 = 4%)
        - avg_loss: average loss as ratio (e.g., 0.02 = 2%, positive value)
        - fractional: fraction of Kelly to use (0.25-0.5 recommended)

        Returns:
        - Position size as fraction of capital (0-1)
        """
        if avg_win <= 0:
            return 0.0

        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        return max(0.0, kelly_fraction * fractional)

    @staticmethod
    def fixed_fractional_size(
        capital: float,
        risk_per_trade: float,
        entry_price: float,
        stop_price: float,
    ) -> int:
        """
        Calculate position size using fixed fractional method.

        Parameters:
        - capital: total account capital
        - risk_per_trade: fraction of capital to risk (e.g., 0.02 = 2%)
        - entry_price: entry price per share
        - stop_price: stop loss price per share

        Returns:
        - Number of shares to trade
        """
        risk_amount = capital * risk_per_trade
        risk_per_share = abs(entry_price - stop_price)

        if risk_per_share <= 0:
            return 0

        shares = int(risk_amount / risk_per_share)
        return shares


class RiskMetrics:
    """Calculate portfolio risk metrics."""

    @staticmethod
    def calculate_var(returns: np.ndarray, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk using historical simulation.

        Parameters:
        - returns: array of historical returns
        - confidence: confidence level (e.g., 0.95 = 95%)

        Returns:
        - VaR as decimal (e.g., 0.03 = 3% potential loss)
        """
        if len(returns) == 0:
            return 0.0
        return abs(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.04,
        periods: int = 252,
    ) -> float:
        """
        Calculate annualized Sharpe ratio.

        Parameters:
        - returns: array of returns (daily)
        - risk_free_rate: annual risk-free rate (e.g., 0.04 = 4%)
        - periods: trading periods per year (252 for daily)

        Returns:
        - Sharpe ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (risk_free_rate / periods)
        if np.std(returns) == 0:
            return 0.0

        sharpe = np.mean(excess_returns) / np.std(returns) * np.sqrt(periods)
        return sharpe

    @staticmethod
    def calculate_max_drawdown(equity_curve: np.ndarray) -> tuple:
        """
        Calculate maximum drawdown from equity curve.

        Parameters:
        - equity_curve: array of portfolio values over time

        Returns:
        - (max_drawdown, max_dd_duration_days)
        """
        if len(equity_curve) == 0:
            return 0.0, 0

        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax

        max_drawdown = abs(np.min(drawdown))

        # Duration calculation
        dd_end = np.argmin(drawdown)
        dd_start = np.argmax(cummax[:dd_end]) if dd_end > 0 else 0
        max_dd_duration = dd_end - dd_start

        return max_drawdown, max_dd_duration

    @staticmethod
    def calculate_sortino_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.04,
        periods: int = 252,
    ) -> float:
        """
        Calculate Sortino ratio (only penalizes downside volatility).

        Parameters:
        - returns: array of returns (daily)
        - risk_free_rate: annual risk-free rate
        - periods: trading periods per year

        Returns:
        - Sortino ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (risk_free_rate / periods)
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return float('inf')

        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0.0

        sortino = np.mean(excess_returns) / downside_std * np.sqrt(periods)
        return sortino


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Trading Strategy Templates for NautilusTrader + Moomoo")
    print("=" * 70)

    # Example 1: Kelly Position Sizing
    print("\nExample 1: Kelly Position Sizing for Momentum Strategy")
    print("-" * 70)
    win_rate = 0.45
    avg_win = 0.04  # 4% average win
    avg_loss = 0.02  # 2% average loss
    position_size = PositionSizer.kelly_position_size(win_rate, avg_win, avg_loss)
    print(f"Win Rate: {win_rate:.1%}")
    print(f"Avg Win: {avg_win:.1%}")
    print(f"Avg Loss: {avg_loss:.1%}")
    print(f"Recommended Position Size: {position_size:.1%}")

    # Example 2: Risk Metrics
    print("\nExample 2: Risk Metrics Calculation")
    print("-" * 70)
    # Simulate returns
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.015, 252)  # Mean=0.1%, Std=1.5% daily

    var_95 = RiskMetrics.calculate_var(returns, confidence=0.95)
    sharpe = RiskMetrics.calculate_sharpe_ratio(returns)
    sortino = RiskMetrics.calculate_sortino_ratio(returns)

    # Simulate equity curve
    equity_curve = np.cumprod(1 + returns) * 100000
    max_dd, dd_duration = RiskMetrics.calculate_max_drawdown(equity_curve)

    print(f"VaR (95%): {var_95:.2%}")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Sortino Ratio: {sortino:.2f}")
    print(f"Max Drawdown: {max_dd:.2%}")
    print(f"Max DD Duration: {dd_duration} days")

    # Example 3: Fixed Fractional Position Sizing
    print("\nExample 3: Fixed Fractional Position Sizing")
    print("-" * 70)
    capital = 100000  # $100k account
    risk_per_trade = 0.02  # 2% risk
    entry_price = 150.0
    stop_price = 145.0  # $5 stop

    shares = PositionSizer.fixed_fractional_size(
        capital, risk_per_trade, entry_price, stop_price
    )
    position_value = shares * entry_price
    risk_amount = shares * (entry_price - stop_price)

    print(f"Account Capital: ${capital:,.0f}")
    print(f"Risk Per Trade: {risk_per_trade:.1%}")
    print(f"Entry Price: ${entry_price:.2f}")
    print(f"Stop Price: ${stop_price:.2f}")
    print(f"Position Size: {shares} shares")
    print(f"Position Value: ${position_value:,.0f}")
    print(f"Risk Amount: ${risk_amount:,.0f}")
    print(f"Risk %: {risk_amount/capital:.2%}")

    print("\n" + "=" * 70)
    print("Templates Ready for Implementation")
    print("=" * 70)
