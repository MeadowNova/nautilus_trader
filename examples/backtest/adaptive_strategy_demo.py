#!/usr/bin/env python3
"""
Adaptive EMA Strategy Demo

Demonstrates self-correction through:
1. Performance monitoring
2. Automatic parameter adaptation
3. Trading pause on poor performance

Run: python adaptive_strategy_demo.py
"""

from decimal import Decimal

import pandas as pd

from nautilus_trader.adapters.binance import BINANCE_VENUE
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators.averages import ExponentialMovingAverage
from nautilus_trader.model.currencies import ETH
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.position import Position
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy


class AdaptiveEMAConfig(StrategyConfig, frozen=True):
    """Configuration for adaptive EMA strategy."""

    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    base_fast_period: int = 10
    base_slow_period: int = 20
    max_drawdown_threshold: float = 0.10  # 10%
    min_win_rate: float = 0.35  # 35%


class AdaptiveEMAStrategy(Strategy):
    """
    Self-correcting EMA crossover strategy.
    
    Features:
    - Adapts EMA periods based on volatility
    - Monitors performance and pauses on poor results
    - Automatically adjusts position sizing
    """

    def __init__(self, config: AdaptiveEMAConfig):
        super().__init__(config)

        # Configuration
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size

        # Adaptive parameters
        self.base_fast_period = config.base_fast_period
        self.base_slow_period = config.base_slow_period
        self.current_fast_period = self.base_fast_period
        self.current_slow_period = self.base_slow_period

        # Performance tracking
        self.trades: list[float] = []
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        self.is_paused = False

        # Thresholds
        self.max_drawdown_threshold = config.max_drawdown_threshold
        self.min_win_rate = config.min_win_rate

        # Indicators
        self.fast_ema: ExponentialMovingAverage | None = None
        self.slow_ema: ExponentialMovingAverage | None = None

        # Volatility tracking (simplified)
        self.price_changes: list[float] = []
        
        # Adaptation tracking
        self.bar_count = 0
        self.adaptation_interval = 50

    def on_start(self):
        """Actions to perform when strategy starts."""
        # Initialize indicators
        self.fast_ema = ExponentialMovingAverage(self.current_fast_period)
        self.slow_ema = ExponentialMovingAverage(self.current_slow_period)

        # Subscribe to data
        self.subscribe_bars(self.bar_type)

        self.log.info("🤖 Adaptive EMA Strategy started")
        self.log.info(f"   Fast EMA: {self.current_fast_period}")
        self.log.info(f"   Slow EMA: {self.current_slow_period}")

    def on_bar(self, bar: Bar):
        """Handle new bar."""
        # Track price changes for volatility
        if self.fast_ema.initialized:
            price_change = abs(bar.close.as_double() - bar.open.as_double()) / bar.open.as_double()
            self.price_changes.append(price_change)
            if len(self.price_changes) > 30:
                self.price_changes.pop(0)
        
        # Update indicators
        self.fast_ema.update_raw(bar.close.as_double())
        self.slow_ema.update_raw(bar.close.as_double())

        self.bar_count += 1

        # Adapt parameters periodically
        if self.bar_count % self.adaptation_interval == 0:
            self._adapt_parameters()

        # Don't trade if paused
        if self.is_paused:
            return

        # Wait for indicators to initialize
        if not (self.fast_ema.initialized and self.slow_ema.initialized):
            return

        # Trading logic
        if self._should_buy():
            self._execute_buy(bar)
        elif self._should_sell():
            self._execute_sell(bar)

    def _should_buy(self) -> bool:
        """Check if should enter long."""
        return (
            self.fast_ema.value > self.slow_ema.value
            and self.portfolio.is_flat(self.instrument_id)
        )

    def _should_sell(self) -> bool:
        """Check if should exit long."""
        return (
            self.fast_ema.value < self.slow_ema.value
            and not self.portfolio.is_flat(self.instrument_id)
        )

    def _execute_buy(self, bar: Bar):
        """Execute buy order."""
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_str(str(self.trade_size)),
        )
        self.submit_order(order)
        self.log.info(f"🟢 BUY at {bar.close}")

    def _execute_sell(self, bar: Bar):
        """Execute sell order."""
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=Quantity.from_str(str(self.trade_size)),
        )
        self.submit_order(order)
        self.log.info(f"🔴 SELL at {bar.close}")

    def on_position_closed(self, position: Position):
        """Track performance when position closes."""
        pnl = position.realized_pnl.as_double()
        self.trades.append(pnl)

        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
            self.max_consecutive_losses = max(
                self.max_consecutive_losses,
                self.consecutive_losses,
            )
        else:
            self.consecutive_losses = 0

        # Log trade
        result = "WIN" if pnl > 0 else "LOSS"
        self.log.info(f"📊 Trade closed: {result} | P&L: {pnl:.4f} USDT")

        # Check if should pause
        if len(self.trades) >= 10:
            self._check_performance()

    def _check_performance(self):
        """Check if performance warrants pausing."""
        if len(self.trades) < 10:
            return

        # Calculate win rate
        recent_trades = self.trades[-20:]
        wins = len([t for t in recent_trades if t > 0])
        win_rate = wins / len(recent_trades)

        # Check thresholds
        if win_rate < self.min_win_rate:
            self._pause_trading(f"Win rate too low: {win_rate:.1%}")

        if self.consecutive_losses >= 5:
            self._pause_trading(f"Loss streak: {self.consecutive_losses} trades")

    def _pause_trading(self, reason: str):
        """Pause trading."""
        if self.is_paused:
            return

        self.is_paused = True
        self.log.warning(f"🚨 PAUSING TRADING: {reason}")

        # Close any open positions
        if not self.portfolio.is_flat(self.instrument_id):
            self.close_all_positions(self.instrument_id)

    def _adapt_parameters(self):
        """Adapt EMA periods based on volatility."""
        if len(self.price_changes) < 10:
            return

        # Calculate volatility from price changes
        import numpy as np
        recent_vol = np.std(self.price_changes[-10:])
        avg_vol = np.std(self.price_changes)

        if avg_vol == 0:
            return

        vol_ratio = recent_vol / avg_vol

        # Adapt periods
        if vol_ratio > 1.5:  # High volatility
            new_fast = int(self.base_fast_period * 1.5)
            new_slow = int(self.base_slow_period * 1.5)
            regime = "HIGH VOLATILITY"

        elif vol_ratio < 0.7:  # Low volatility
            new_fast = int(self.base_fast_period * 0.8)
            new_slow = int(self.base_slow_period * 0.8)
            regime = "LOW VOLATILITY"

        else:  # Normal volatility
            new_fast = self.base_fast_period
            new_slow = self.base_slow_period
            regime = "NORMAL VOLATILITY"

        # Only update if significant change
        if (
            abs(new_fast - self.current_fast_period) > 2
            or abs(new_slow - self.current_slow_period) > 2
        ):
            self.current_fast_period = new_fast
            self.current_slow_period = new_slow

            # Recreate indicators
            self.fast_ema = ExponentialMovingAverage(self.current_fast_period)
            self.slow_ema = ExponentialMovingAverage(self.current_slow_period)

            self.log.info(
                f"🔄 {regime} - Adapted EMAs: "
                f"Fast={self.current_fast_period}, Slow={self.current_slow_period}",
            )

    def on_stop(self):
        """Actions to perform when strategy stops."""
        # Calculate final statistics
        if self.trades:
            total_pnl = sum(self.trades)
            wins = len([t for t in self.trades if t > 0])
            losses = len([t for t in self.trades if t < 0])
            win_rate = wins / len(self.trades) * 100 if self.trades else 0

            self.log.info("\n" + "=" * 60)
            self.log.info("📊 FINAL PERFORMANCE SUMMARY")
            self.log.info("=" * 60)
            self.log.info(f"Total Trades:      {len(self.trades)}")
            self.log.info(f"Winning Trades:    {wins}")
            self.log.info(f"Losing Trades:     {losses}")
            self.log.info(f"Win Rate:          {win_rate:.1f}%")
            self.log.info(f"Total P&L:         {total_pnl:.4f} USDT")
            self.log.info(f"Max Loss Streak:   {self.max_consecutive_losses}")
            self.log.info(f"Was Paused:        {self.is_paused}")
            self.log.info("=" * 60)


def run_adaptive_demo():
    """Run the adaptive strategy demonstration."""
    # Configure backtest
    config = BacktestEngineConfig(
        trader_id=TraderId("ADAPTIVE-001"),
        logging=LoggingConfig(log_level="INFO", use_pyo3=False),
    )

    # Build engine
    engine = BacktestEngine(config=config)

    # Add venue
    engine.add_venue(
        venue=BINANCE_VENUE,
        oms_type=OmsType.NETTING,
        book_type=BookType.L1_MBP,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(1_000_000.0, USDT), Money(10.0, ETH)],
        trade_execution=True,
    )

    # Add instrument
    ETHUSDT_BINANCE = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(ETHUSDT_BINANCE)

    # Load data
    provider = TestDataProvider()
    wrangler = TradeTickDataWrangler(instrument=ETHUSDT_BINANCE)
    ticks = wrangler.process(provider.read_csv_ticks("binance/ethusdt-trades.csv"))
    engine.add_data(ticks)

    # Configure adaptive strategy
    strategy_config = AdaptiveEMAConfig(
        instrument_id=ETHUSDT_BINANCE.id,
        bar_type=BarType.from_str("ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL"),
        trade_size=Decimal("0.10"),
        base_fast_period=10,
        base_slow_period=20,
        max_drawdown_threshold=0.10,
        min_win_rate=0.35,
    )

    # Add strategy
    strategy = AdaptiveEMAStrategy(strategy_config)
    engine.add_strategy(strategy)

    # Run backtest
    print("\n🚀 Running Adaptive Strategy Demo...")
    print("=" * 60)
    engine.run()

    # Generate reports
    print("\n📊 Generating reports...")
    positions_df = engine.trader.generate_positions_report()

    # Display summary
    if not positions_df.empty:
        print("\n" + "=" * 60)
        print("POSITION SUMMARY")
        print("=" * 60)
        print(positions_df[["entry", "avg_px_open", "avg_px_close", "realized_pnl"]])

    # Cleanup
    engine.reset()
    engine.dispose()

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    run_adaptive_demo()
