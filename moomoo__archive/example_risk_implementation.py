# -------------------------------------------------------------------------------------------------
#  Example Risk Management Implementation for NautilusTrader
#  Demonstrates all risk management features in a working strategy context
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import InstrumentId
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.trading.strategy import Strategy

from risk_management_framework import (
    PositionRiskConfig,
    PortfolioRiskConfig,
    GreeksConfig,
    PositionMetrics,
    PortfolioMetrics,
    TradeEntry,
    RMeasurement,
    RiskLevel,
    PositionSizer,
    RiskMonitor,
    StopLossEngine,
    TakeProfitEngine,
    RiskReporter,
    MonteCarloSimulator,
)


@dataclass
class ExampleStrategyConfig(StrategyConfig, frozen=True):
    """Configuration for example strategy with risk management."""
    bar_type: BarType
    instrument: InstrumentId
    risk_per_trade_pct: float = 0.02  # Risk 2% per trade
    atr_period: int = 14


class ExampleRiskManagedStrategy(Strategy):
    """
    Example strategy implementing comprehensive risk management.

    Features:
    - Automatic position sizing based on ATR
    - R-multiple tracking
    - Real-time risk monitoring
    - Expectancy calculation
    - Monte Carlo stress testing
    """

    def __init__(self, config: ExampleStrategyConfig):
        super().__init__(config)
        self.config = config

        # Risk management configuration
        self.position_risk_config = PositionRiskConfig(
            max_position_size_usd=25000.0,
            max_position_size_pct_account=0.05,
            stop_loss_atr_multiple=2.0,
            take_profit_rr_ratio=2.0,
            max_losing_streak=3,
            min_win_rate=0.35,
        )

        self.portfolio_risk_config = PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=0.75,
            max_single_sector_exposure=0.30,
            max_daily_loss_pct=0.05,
            max_drawdown_pct=0.10,
            margin_utilization_limit=0.80,
        )

        self.greeks_config = GreeksConfig(
            portfolio_delta_limit=0.30,
            portfolio_gamma_limit=0.05,
            portfolio_vega_limit=0.25,
            portfolio_theta_daily_limit=100.0,
        )

        # Initialize monitoring components
        self.risk_monitor = RiskMonitor(
            self.position_risk_config,
            self.portfolio_risk_config,
            self.greeks_config,
        )

        self.reporter = RiskReporter()
        self.position_sizer = PositionSizer()

        # Portfolio and position tracking
        self.portfolio = PortfolioMetrics(account_size=0.0)
        self.positions: dict[str, PositionMetrics] = {}
        self.r_measurement = RMeasurement()

        # Current market state
        self.atr_value: float = 0.0
        self.current_price: float = 0.0

    def on_start(self):
        """Initialize strategy on startup."""
        self.log.info(f"Strategy starting: {self.config.instrument}")
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        """Process bar updates."""
        # Update market state
        self.current_price = float(bar.close)
        self._update_atr(bar)
        self._update_portfolio()
        self._check_risk_limits()

        # Strategy logic
        if self.portfolio.account_size > 0:
            self._generate_signals()

    def on_stop(self):
        """Cleanup on strategy stop."""
        self.log.info("Strategy stopping")

        # Print final statistics
        self._print_performance_summary()

    # ===== SIGNAL GENERATION =====

    def _generate_signals(self):
        """Generate trading signals with risk management."""
        # Simple example: Buy on close above moving average
        # (In production, use more sophisticated logic)

        if not self.portfolio.positions or len(self.portfolio.positions) < 2:
            # Example: Long signal
            if self.current_price > 100.0:  # Placeholder condition
                self._enter_long_position()

    def _enter_long_position(self):
        """Enter a long position with automatic risk management."""
        if not self._can_trade():
            self.log.warning("Cannot trade: Risk limits approaching")
            return

        # Calculate stop loss
        stop_price = StopLossEngine.atr_based(
            entry_price=self.current_price,
            atr_value=self.atr_value,
            atr_multiple=self.position_risk_config.stop_loss_atr_multiple,
            direction="LONG",
        )

        # Calculate take profit
        tp_price = TakeProfitEngine.risk_reward_based(
            entry_price=self.current_price,
            stop_loss_price=stop_price,
            rr_ratio=self.position_risk_config.take_profit_rr_ratio,
            direction="LONG",
        )

        # Calculate position size
        position_size = self.position_sizer.fixed_fraction(
            account_size=self.portfolio.account_size,
            risk_per_trade_pct=self.config.risk_per_trade_pct,
            entry_price=self.current_price,
            stop_loss_price=stop_price,
        )

        # Calculate R value
        r_value = abs(self.current_price - stop_price) * position_size

        # Verify position size against limits
        position_notional = position_size * self.current_price
        if position_notional > self.position_risk_config.max_position_size_usd:
            self.log.warning(
                f"Position size ${position_notional:,.0f} exceeds limit "
                f"${self.position_risk_config.max_position_size_usd:,.0f}"
            )
            return

        self.log.info(
            f"ENTRY: Price={self.current_price:.2f}, "
            f"Stop={stop_price:.2f}, TP={tp_price:.2f}, "
            f"Size={position_size}, Risk=${r_value:,.0f}"
        )

        # Execute order (in real strategy)
        # self.buy(
        #     instrument_id=self.config.instrument,
        #     quantity=position_size,
        #     time_in_force=TimeInForce.GTC,
        # )

        # Record trade entry
        trade_entry = TradeEntry(
            instrument_id=str(self.config.instrument),
            entry_price=self.current_price,
            entry_size=position_size,
            entry_time=datetime.now(),
            r_value=r_value,
            stop_loss_price=stop_price,
            take_profit_price=tp_price,
        )

        # Initialize position
        position = PositionMetrics(
            instrument_id=str(self.config.instrument),
            entry_price=self.current_price,
            current_price=self.current_price,
            quantity=position_size,
            entry_time=datetime.now(),
            direction="LONG",
            trades=[trade_entry],
        )

        self.positions[str(self.config.instrument)] = position
        self.portfolio.positions[str(self.config.instrument)] = position

    # ===== RISK MONITORING =====

    def _can_trade(self) -> bool:
        """Check if new trades are allowed given risk limits."""
        # Check daily loss limit
        if self.portfolio.pnl_daily < 0:
            daily_loss_pct = abs(self.portfolio.pnl_daily) / self.portfolio.account_size
            if daily_loss_pct > self.portfolio_risk_config.max_daily_loss_pct:
                return False

        # Check max consecutive losses
        if (
            self.r_measurement.consecutive_losses
            > self.position_risk_config.max_losing_streak
        ):
            return False

        return True

    def _check_risk_limits(self):
        """Perform comprehensive risk checks."""
        # Check position risks
        for instrument_id, position in self.positions.items():
            risk_level, issues = self.risk_monitor.check_position_risk(
                position, self.portfolio.account_size
            )

            if risk_level == RiskLevel.BREACH:
                self.log.error(f"POSITION BREACH: {instrument_id}")
                for issue in issues:
                    self.log.error(f"  {issue}")
                # Close position immediately
                # self.close_position(instrument_id)

            elif risk_level == RiskLevel.CRITICAL:
                self.log.warning(f"POSITION CRITICAL: {instrument_id}")
                for issue in issues:
                    self.log.warning(f"  {issue}")

        # Check portfolio risks
        risk_level, issues = self.risk_monitor.check_portfolio_risk(self.portfolio)

        if risk_level == RiskLevel.BREACH:
            self.log.error("PORTFOLIO BREACH")
            for issue in issues:
                self.log.error(f"  {issue}")

        elif risk_level == RiskLevel.CRITICAL:
            self.log.warning("PORTFOLIO CRITICAL")
            for issue in issues:
                self.log.warning(f"  {issue}")

    # ===== PORTFOLIO UPDATES =====

    def _update_atr(self, bar: Bar):
        """Update ATR value from bar data."""
        # In production, use indicator cache
        # For now, simple placeholder
        self.atr_value = float(bar.high - bar.low)

    def _update_portfolio(self):
        """Update portfolio metrics."""
        # Get account balance
        account_state = self.get_account()
        if account_state:
            self.portfolio.account_size = account_state.balance()
            self.portfolio.peak_equity = max(
                self.portfolio.peak_equity, account_state.balance()
            )

        # Update all positions
        self.portfolio.gross_exposure = 0.0
        self.portfolio.net_exposure = 0.0

        for position in self.positions.values():
            # Update current price
            position.current_price = self.current_price

            # Calculate unrealized P&L
            move = self.current_price - position.entry_price
            if position.direction == "SHORT":
                move = -move
            position.pnl_unrealized = move * position.quantity

            # Track favorable/adverse moves
            if move > position.max_favorable_move:
                position.max_favorable_move = move
            if move < position.max_adverse_move:
                position.max_adverse_move = move

            # Update gross/net exposure
            notional = position.quantity * position.current_price
            signed_notional = notional if position.direction == "LONG" else -notional
            self.portfolio.gross_exposure += abs(notional)
            self.portfolio.net_exposure += signed_notional

            # Update R-multiple
            if position.trades:
                avg_risk = sum(t.r_value for t in position.trades) / len(
                    position.trades
                )
                if avg_risk > 0:
                    position.r_multiple = position.pnl_unrealized / avg_risk

        # Calculate drawdown
        self.portfolio.current_drawdown = (
            self.portfolio.peak_equity - self.portfolio.account_size
        )

    def _record_closed_trade(self, position: PositionMetrics):
        """Record closed trade and update statistics."""
        # Calculate total risk for position
        if position.trades:
            total_risk = sum(t.r_value for t in position.trades)

            if position.pnl_unrealized > 0:
                self.r_measurement.winning_trades += 1
                r_gain = position.pnl_unrealized / total_risk if total_risk > 0 else 0
                self.r_measurement.total_r_gained += r_gain
                self.r_measurement.consecutive_losses = 0
            else:
                self.r_measurement.losing_trades += 1
                r_loss = abs(position.pnl_unrealized) / total_risk if total_risk > 0 else 0
                self.r_measurement.total_r_lost += r_loss
                self.r_measurement.consecutive_losses += 1
                self.r_measurement.max_consecutive_losses = max(
                    self.r_measurement.max_consecutive_losses,
                    self.r_measurement.consecutive_losses,
                )

    # ===== REPORTING =====

    def _print_performance_summary(self):
        """Print final performance statistics."""
        self.log.info("=" * 60, color="MAGENTA")
        self.log.info("PERFORMANCE SUMMARY", color="MAGENTA")
        self.log.info("=" * 60, color="MAGENTA")

        # Portfolio metrics
        port_report = self.reporter.generate_portfolio_report(self.portfolio)
        self.log.info(f"Total P&L: ${port_report['pnl_total']:,.2f}")
        self.log.info(f"Daily P&L: ${port_report['pnl_daily']:,.2f}")
        self.log.info(f"Drawdown: {port_report['drawdown_pct']:.2f}%")

        # R-multiple metrics
        exp_report = self.reporter.generate_expectancy_report(self.r_measurement)
        self.log.info(
            f"Trades: {exp_report['winning_trades']}W / {exp_report['losing_trades']}L "
            f"({exp_report['win_rate']:.2f}%)"
        )
        self.log.info(f"Expectancy: {exp_report['expectancy']:.3f}R")
        self.log.info(f"Profit Factor: {exp_report['profit_factor']:.2f}")
        self.log.info(f"Kelly %: {exp_report['kelly_percentage']:.2f}%")

        self.log.info("=" * 60, color="MAGENTA")

        # Monte Carlo stress test
        if self.r_measurement.winning_trades + self.r_measurement.losing_trades > 20:
            self.log.info("MONTE CARLO STRESS TEST (1000 simulations)", color="CYAN")

            avg_win = self.r_measurement.total_r_gained / max(
                self.r_measurement.winning_trades, 1
            )
            avg_loss = self.r_measurement.total_r_lost / max(
                self.r_measurement.losing_trades, 1
            )

            sim_results = MonteCarloSimulator.simulate_drawdown(
                win_rate=self.r_measurement.win_rate,
                avg_win_r=avg_win,
                avg_loss_r=avg_loss,
                num_trades=100,
                num_simulations=1000,
                starting_capital=self.portfolio.account_size,
            )

            self.log.info(
                f"Expected final: ${sim_results['expected_final_capital']:,.0f}"
            )
            self.log.info(f"Worst case (5th %ile): ${sim_results['worst_case_capital']:,.0f}")
            self.log.info(f"Best case (95th %ile): ${sim_results['best_case_capital']:,.0f}")
            self.log.info(f"Avg max drawdown: {sim_results['avg_max_drawdown_pct']:.2f}%")


# ===== EXAMPLE USAGE =====

if __name__ == "__main__":
    print("Example Risk-Managed Strategy Module")
    print("\nKey Features:")
    print("1. Position sizing based on account risk")
    print("2. Automatic stop-loss calculation (ATR-based)")
    print("3. Automatic take-profit calculation (2:1 RR)")
    print("4. Real-time risk monitoring")
    print("5. R-multiple tracking")
    print("6. Expectancy calculation")
    print("7. Monte Carlo stress testing")
    print("\nConfiguration Parameters:")
    print(f"  - Max position size: ${25000:,}")
    print(f"  - Max position %: 5% of account")
    print(f"  - Risk per trade: 2% of account")
    print(f"  - Stop loss: 2.0x ATR")
    print(f"  - Take profit: 2:1 risk/reward")
    print(f"  - Max daily loss: 5%")
    print(f"  - Max drawdown: 10%")
