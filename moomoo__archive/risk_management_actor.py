# -------------------------------------------------------------------------------------------------
#  Risk Management Actor for NautilusTrader
#  Implements position and portfolio monitoring with real-time risk alerts
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from datetime import datetime, timedelta
import pandas as pd

from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.common.enums import LogColor
from nautilus_trader.core.data import Data
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model import ActorId, InstrumentId
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.events import AccountState, PositionChanged, TradeOccurred
from nautilus_trader.model.instruments import Instrument

from risk_management_framework import (
    PositionRiskConfig,
    PortfolioRiskConfig,
    GreeksConfig,
    PositionMetrics,
    PortfolioMetrics,
    RMeasurement,
    TradeEntry,
    RiskLevel,
    PositionSizer,
    RiskMonitor,
    StopLossEngine,
    TakeProfitEngine,
    RiskReporter,
    MonteCarloSimulator,
)

if TYPE_CHECKING:
    from nautilus_trader.core.fsm import FiniteStateMachine


# ===== CUSTOM DATA TYPES =====

@customdataclass
class RiskAlert(Data):
    """Alert for risk violations."""
    instrument_id: InstrumentId
    alert_level: str
    alert_message: str
    timestamp: int


@customdataclass
class PositionReport(Data):
    """Position-level risk metrics."""
    instrument_id: InstrumentId
    pnl_unrealized: float
    pnl_pct: float
    r_multiple: float
    bars_held: int
    position_notional: float
    timestamp: int


@customdataclass
class PortfolioSnapshot(Data):
    """Portfolio-level risk metrics."""
    total_pnl: float
    daily_pnl: float
    gross_exposure: float
    net_exposure: float
    drawdown_pct: float
    margin_utilization: float
    win_rate: float
    expectancy: float
    timestamp: int


# ===== RISK MANAGEMENT ACTOR CONFIGURATION =====

@dataclass
class RiskManagementActorConfig(DataActorConfig):
    """Configuration for RiskManagementActor."""

    # Inherited from DataActorConfig
    actor_id: ActorId | None = None
    log_events: bool = True
    log_commands: bool = True

    # Risk parameters
    position_max_size_usd: float = 25000.0
    position_max_pct_account: float = 0.05
    position_stop_loss_atr_multiple: float = 2.0
    position_take_profit_rr: float = 2.0
    position_max_losing_streak: int = 3
    position_min_win_rate: float = 0.35

    portfolio_max_gross_exposure: float = 1.0
    portfolio_max_net_exposure: float = 0.75
    portfolio_max_sector_exposure: float = 0.30
    portfolio_max_daily_loss_pct: float = 0.05
    portfolio_max_drawdown_pct: float = 0.10
    portfolio_margin_limit: float = 0.80

    greeks_delta_limit: float = 0.30
    greeks_gamma_limit: float = 0.05
    greeks_vega_limit: float = 0.25
    greeks_theta_daily_limit: float = 100.0

    # Monitoring
    risk_check_interval_minutes: int = 5
    rebalance_interval_minutes: int = 60
    report_interval_minutes: int = 15

    def __post_init__(self):
        """Validate and setup configuration."""
        if isinstance(self.actor_id, str):
            self.actor_id = ActorId(self.actor_id)


# ===== RISK MANAGEMENT ACTOR =====

class RiskManagementActor(DataActor):
    """
    Risk Management Actor for NautilusTrader.

    Monitors positions and portfolio against configured risk limits.
    Publishes risk alerts and metrics as custom data types.

    Features:
    - Real-time position risk monitoring
    - Portfolio-level exposure tracking
    - R-multiple performance measurement
    - Options Greeks aggregation
    - Monte Carlo stress testing
    - Risk alerts and notifications
    """

    def __init__(self, config: RiskManagementActorConfig | None = None):
        """
        Initialize RiskManagementActor.

        Parameters:
        -----------
        config : RiskManagementActorConfig, optional
            Configuration for the actor
        """
        if config is None:
            config = RiskManagementActorConfig(actor_id=ActorId("RISK-MGR-001"))

        super().__init__(config)
        self.config = config

        # Setup risk configurations
        self.position_risk_config = PositionRiskConfig(
            max_position_size_usd=config.position_max_size_usd,
            max_position_size_pct_account=config.position_max_pct_account,
            stop_loss_atr_multiple=config.position_stop_loss_atr_multiple,
            take_profit_rr_ratio=config.position_take_profit_rr,
            max_losing_streak=config.position_max_losing_streak,
            min_win_rate=config.position_min_win_rate,
        )

        self.portfolio_risk_config = PortfolioRiskConfig(
            max_gross_exposure=config.portfolio_max_gross_exposure,
            max_net_exposure=config.portfolio_max_net_exposure,
            max_single_sector_exposure=config.portfolio_max_sector_exposure,
            max_daily_loss_pct=config.portfolio_max_daily_loss_pct,
            max_drawdown_pct=config.portfolio_max_drawdown_pct,
            margin_utilization_limit=config.portfolio_margin_limit,
        )

        self.greeks_config = GreeksConfig(
            portfolio_delta_limit=config.greeks_delta_limit,
            portfolio_gamma_limit=config.greeks_gamma_limit,
            portfolio_vega_limit=config.greeks_vega_limit,
            portfolio_theta_daily_limit=config.greeks_theta_daily_limit,
        )

        # Initialize monitoring components
        self.risk_monitor = RiskMonitor(
            self.position_risk_config,
            self.portfolio_risk_config,
            self.greeks_config,
        )

        self.reporter = RiskReporter()

        # Portfolio state tracking
        self.portfolio = PortfolioMetrics(account_size=0.0)
        self.positions: dict[str, PositionMetrics] = {}
        self.daily_trades: list[dict] = []
        self.daily_start_time: datetime | None = None

        # Timers
        self.risk_check_timer_name = "RISK-CHECK-TIMER"
        self.report_timer_name = "REPORT-TIMER"
        self.rebalance_timer_name = "REBALANCE-TIMER"

    def on_start(self) -> None:
        """Actions to perform on actor startup."""
        self.log.info("Risk Management Actor Starting...", LogColor.CYAN)

        # Setup monitoring timers
        self.clock.set_timer(
            self.risk_check_timer_name,
            pd.Timedelta(minutes=self.config.risk_check_interval_minutes),
        )
        self.clock.set_timer(
            self.report_timer_name,
            pd.Timedelta(minutes=self.config.report_interval_minutes),
        )
        self.clock.set_timer(
            self.rebalance_timer_name,
            pd.Timedelta(minutes=self.config.rebalance_interval_minutes),
        )

        self.daily_start_time = datetime.now()

        self.log.info("Risk monitoring timers configured", LogColor.BLUE)

    def on_stop(self) -> None:
        """Actions to perform on actor shutdown."""
        self.log.info("Risk Management Actor Stopping...", LogColor.CYAN)

    def on_time_event(self, event) -> None:
        """Handle timer events."""
        if event.name == self.risk_check_timer_name:
            self._perform_risk_check()
        elif event.name == self.report_timer_name:
            self._generate_reports()
        elif event.name == self.rebalance_timer_name:
            self._check_rebalance_needs()

    # ===== EVENT HANDLERS =====

    def on_account_state(self, event: AccountState) -> None:
        """Handle account state updates."""
        self.portfolio.account_size = event.balance()
        self.portfolio.peak_equity = max(self.portfolio.peak_equity, event.balance())

        # Update drawdown
        self.portfolio.current_drawdown = (
            self.portfolio.peak_equity - event.balance()
        )

        self.log.info(
            f"Account Updated: Balance ${event.balance():,.2f}",
            LogColor.BLUE,
        )

    def on_position_changed(self, event: PositionChanged) -> None:
        """Handle position changes."""
        instrument_id = str(event.instrument_id)

        if event.quantity == 0:
            # Position closed
            if instrument_id in self.positions:
                closed_position = self.positions.pop(instrument_id)
                self._record_closed_trade(closed_position, event)
                self.log.info(
                    f"Position Closed: {instrument_id}",
                    LogColor.YELLOW,
                )
        else:
            # Position opened or modified
            if instrument_id not in self.positions:
                self.positions[instrument_id] = PositionMetrics(
                    instrument_id=instrument_id,
                    entry_price=event.avg_price,
                    current_price=event.avg_price,
                    quantity=event.quantity,
                    entry_time=unix_nanos_to_dt(event.ts_event),
                    direction="LONG" if event.quantity > 0 else "SHORT",
                )

            self.log.info(
                f"Position Changed: {instrument_id} | "
                f"Qty: {event.quantity} | Price: ${event.avg_price:.2f}",
                LogColor.GREEN,
            )

    def on_trade_occurred(self, event: TradeOccurred) -> None:
        """Handle executed trades."""
        instrument_id = str(event.instrument_id)

        # Create trade entry record
        trade_entry = TradeEntry(
            instrument_id=instrument_id,
            entry_price=float(event.price),
            entry_size=int(event.quantity),
            entry_time=unix_nanos_to_dt(event.ts_event),
            r_value=0.0,  # Will be set by strategy
            stop_loss_price=0.0,
            take_profit_price=0.0,
        )

        # Add to current position or daily trades
        if instrument_id in self.positions:
            self.positions[instrument_id].trades.append(trade_entry)

        self.daily_trades.append({
            "instrument": instrument_id,
            "price": float(event.price),
            "quantity": int(event.quantity),
            "timestamp": unix_nanos_to_dt(event.ts_event),
            "side": "BUY" if event.quantity > 0 else "SELL",
        })

        self.log.info(
            f"Trade Executed: {instrument_id} | "
            f"{'BUY' if event.quantity > 0 else 'SELL'} {event.quantity} @ ${event.price}",
            LogColor.CYAN,
        )

    # ===== RISK MONITORING =====

    def _perform_risk_check(self) -> None:
        """Check all positions and portfolio against risk limits."""
        self.log.info("Performing Risk Check...", LogColor.YELLOW)

        # Check each position
        for instrument_id, position in self.positions.items():
            risk_level, issues = self.risk_monitor.check_position_risk(
                position, self.portfolio.account_size
            )

            if risk_level != RiskLevel.OK:
                self._publish_risk_alert(instrument_id, risk_level, issues)

                self.log.info(
                    f"Position Risk [{risk_level.value}]: {instrument_id}",
                    LogColor.RED if risk_level == RiskLevel.BREACH else LogColor.YELLOW,
                )
                for issue in issues:
                    self.log.info(f"  - {issue}", LogColor.RED)

        # Check portfolio
        risk_level, issues = self.risk_monitor.check_portfolio_risk(self.portfolio)

        if risk_level != RiskLevel.OK:
            self.log.info(
                f"Portfolio Risk [{risk_level.value}]",
                LogColor.RED if risk_level == RiskLevel.BREACH else LogColor.YELLOW,
            )
            for issue in issues:
                self.log.info(f"  - {issue}", LogColor.RED)

            # Take action on critical breaches
            if risk_level == RiskLevel.BREACH:
                self._handle_risk_breach()

    def _publish_risk_alert(
        self,
        instrument_id: str,
        risk_level: RiskLevel,
        issues: list[str],
    ) -> None:
        """Publish a risk alert as custom data."""
        alert = RiskAlert(
            instrument_id=InstrumentId.from_str(instrument_id),
            alert_level=risk_level.value,
            alert_message=" | ".join(issues),
            ts_event=self.clock.timestamp_ns(),
            ts_init=self.clock.timestamp_ns(),
        )

        self.publish_data(type(alert), alert)

    def _handle_risk_breach(self) -> None:
        """Handle critical risk breach."""
        self.log.error(
            "CRITICAL RISK BREACH - Manual intervention required",
            LogColor.RED,
        )

        # In production, this would trigger:
        # - Automated position reductions
        # - Strategy halts
        # - Executive notifications

    def _generate_reports(self) -> None:
        """Generate and publish risk reports."""
        # Update portfolio metrics
        self._update_portfolio_metrics()

        # Position reports
        for instrument_id, position in self.positions.items():
            report_dict = self.reporter.generate_position_report(
                position, self.portfolio.account_size
            )

            position_report = PositionReport(
                instrument_id=InstrumentId.from_str(instrument_id),
                pnl_unrealized=report_dict["pnl_unrealized"],
                pnl_pct=report_dict["pnl_pct"],
                r_multiple=report_dict["r_multiple"],
                bars_held=report_dict["bars_held"],
                position_notional=report_dict["account_pct"] * self.portfolio.account_size / 100,
                ts_event=self.clock.timestamp_ns(),
                ts_init=self.clock.timestamp_ns(),
            )

            self.publish_data(type(position_report), position_report)

        # Portfolio report
        portfolio_report_dict = self.reporter.generate_portfolio_report(self.portfolio)

        portfolio_snapshot = PortfolioSnapshot(
            total_pnl=portfolio_report_dict["pnl_total"],
            daily_pnl=portfolio_report_dict["pnl_daily"],
            gross_exposure=portfolio_report_dict["gross_exposure"],
            net_exposure=portfolio_report_dict["net_exposure"],
            drawdown_pct=portfolio_report_dict["drawdown_pct"],
            margin_utilization=portfolio_report_dict["margin_utilization_pct"],
            win_rate=portfolio_report_dict["win_rate"],
            expectancy=portfolio_report_dict["expectancy"],
            ts_event=self.clock.timestamp_ns(),
            ts_init=self.clock.timestamp_ns(),
        )

        self.publish_data(type(portfolio_snapshot), portfolio_snapshot)

        self.log.info("Risk Reports Published", LogColor.BLUE)

    def _check_rebalance_needs(self) -> None:
        """Check if portfolio rebalancing is needed."""
        self._update_portfolio_metrics()

        # Check sector concentration
        for sector, exposure in self.portfolio.sector_exposure.items():
            sector_pct = exposure.exposure_pct(self.portfolio.account_size)
            if sector_pct > self.portfolio_risk_config.max_single_sector_exposure * 100:
                self.log.warning(
                    f"Sector {sector} over-concentrated at {sector_pct:.1f}%",
                    LogColor.YELLOW,
                )

        # Check gross exposure
        if (
            self.portfolio.gross_exposure_pct
            > self.portfolio_risk_config.max_gross_exposure * 100
        ):
            self.log.warning(
                f"Portfolio over-leveraged: {self.portfolio.gross_exposure_pct:.1f}%",
                LogColor.YELLOW,
            )

    def _update_portfolio_metrics(self) -> None:
        """Update portfolio-level metrics from all positions."""
        self.portfolio.positions = self.positions
        self.portfolio.gross_exposure = 0.0
        self.portfolio.net_exposure = 0.0
        self.portfolio.pnl_total = 0.0
        self.portfolio.portfolio_delta = 0.0
        self.portfolio.portfolio_gamma = 0.0
        self.portfolio.portfolio_vega = 0.0
        self.portfolio.portfolio_theta = 0.0

        for position in self.positions.values():
            notional = position.quantity * position.current_price
            signed_notional = notional if position.direction == "LONG" else -notional

            self.portfolio.gross_exposure += abs(notional)
            self.portfolio.net_exposure += signed_notional
            self.portfolio.pnl_total += position.pnl_unrealized + position.pnl_realized

            # Aggregate Greeks
            self.portfolio.portfolio_delta += position.delta
            self.portfolio.portfolio_gamma += position.gamma
            self.portfolio.portfolio_vega += position.vega
            self.portfolio.portfolio_theta += position.theta

    def _record_closed_trade(
        self,
        position: PositionMetrics,
        event,
    ) -> None:
        """Record closed trade and update R-multiple measurements."""
        # Calculate realized P&L
        pnl_realized = position.pnl_unrealized

        # Update R-measurement
        if position.trades:
            avg_risk = sum(t.risk_amount for t in position.trades) / len(position.trades)

            if pnl_realized > 0:
                self.portfolio.r_measurement.winning_trades += 1
                r_gain = pnl_realized / avg_risk if avg_risk > 0 else 0
                self.portfolio.r_measurement.total_r_gained += r_gain
                self.portfolio.r_measurement.consecutive_losses = 0
            else:
                self.portfolio.r_measurement.losing_trades += 1
                r_loss = abs(pnl_realized) / avg_risk if avg_risk > 0 else 0
                self.portfolio.r_measurement.total_r_lost += r_loss
                self.portfolio.r_measurement.consecutive_losses += 1
                self.portfolio.r_measurement.max_consecutive_losses = max(
                    self.portfolio.r_measurement.max_consecutive_losses,
                    self.portfolio.r_measurement.consecutive_losses,
                )


# ===== DEMONSTRATION =====

if __name__ == "__main__":
    print("Risk Management Actor Module Loaded")
    print("\nFeatures:")
    print("- Real-time position risk monitoring")
    print("- Portfolio exposure tracking")
    print("- R-multiple performance measurement")
    print("- Options Greeks aggregation")
    print("- Risk alert publishing")
    print("- Risk report generation")
    print("\nCustom Data Types:")
    print("- RiskAlert: Position and portfolio risk violations")
    print("- PositionReport: Per-position risk metrics")
    print("- PortfolioSnapshot: Portfolio-level statistics")
