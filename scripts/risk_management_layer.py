"""
COMPREHENSIVE RISK MANAGEMENT LAYER FOR MULTI-FACTOR STRATEGY
==============================================================

This module provides institutional-grade risk management for the advanced
multi-factor strategy deployment. It integrates position limits, R-multiple
tracking, hedging strategies, and real-time risk monitoring.

Architecture:
- Portfolio-level position limits and correlations
- Trade-level R-multiple tracking and expectancy
- Dynamic hedging based on delta and correlation
- Circuit breakers for drawdown and daily losses
- Prometheus integration for real-time alerts
- Monte Carlo stress testing

Author: Risk Management Framework
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class AlertLevel(Enum):
    """Alert severity levels for Prometheus"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ALERT = "alert"


class HedgeType(Enum):
    """Types of hedging strategies"""
    DELTA_HEDGE = "delta_hedge"
    CORRELATION_HEDGE = "correlation_hedge"
    VIX_HEDGE = "vix_hedge"
    TAIL_RISK_HEDGE = "tail_risk_hedge"
    NONE = "none"


@dataclass
class RiskMetrics:
    """Real-time risk metrics for portfolio"""
    portfolio_value: float
    cash_available: float
    total_exposure: float
    leverage_ratio: float
    daily_pnl: float
    daily_loss_pct: float
    drawdown: float
    max_drawdown: float
    portfolio_volatility: float
    portfolio_beta: float
    var_95: float
    cvar_95: float
    num_open_positions: int
    heat_used: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RMultiple:
    """R-multiple tracking for a closed trade"""
    trade_id: str
    entry_price: float
    exit_price: float
    stop_loss: float
    initial_risk: float  # R value in dollars
    pnl: float
    r_multiple: float  # PnL / R
    win: bool
    entry_time: datetime
    exit_time: datetime
    symbol: str
    direction: int  # 1 = long, -1 = short


@dataclass
class PositionLimits:
    """Position size limits per symbol"""
    symbol: str
    max_position_pct: float  # % of portfolio
    max_notional: float
    current_notional: float = 0.0
    num_positions: int = 0
    concentration_warning: float = 0.7  # Alert at 70% of max


@dataclass
class CorrelationRisk:
    """Correlation monitoring between positions"""
    symbol_pair: Tuple[str, str]
    correlation: float
    lookback_bars: int
    alert_threshold: float = 0.85  # Alert if correlation too high


class MarketRegimeAlert(Enum):
    """Market regime for alert rules"""
    LOW_VOLATILITY = "low_vol"
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_vol"
    CRISIS = "crisis"


# ============================================================================
# POSITION LIMITS & CONCENTRATION CONTROL
# ============================================================================

class PositionLimitManager:
    """
    Manages position-level and portfolio-level limits.

    Controls:
    - Max position size per symbol (% of portfolio)
    - Max notional exposure per symbol
    - Portfolio heat (total risk at stake)
    - Sector/asset class limits
    """

    def __init__(self, portfolio_value: float, config: Dict = None):
        """
        Initialize position limit manager.

        Args:
            portfolio_value: Current total portfolio value
            config: Configuration dictionary with limit parameters
        """
        self.portfolio_value = portfolio_value
        self.config = config or {}

        # Default limits
        self.max_position_size_pct = self.config.get('max_position_size_pct', 0.05)
        self.max_sector_exposure_pct = self.config.get('max_sector_exposure_pct', 0.25)
        self.max_portfolio_heat = self.config.get('max_portfolio_heat', 0.02)
        self.max_correlation_sum = self.config.get('max_correlation_sum', 3.0)
        self.max_beta_exposure = self.config.get('max_beta_exposure', 2.0)

        # Track positions
        self.positions: Dict[str, Dict] = {}
        self.sector_exposures: Dict[str, float] = defaultdict(float)
        self.portfolio_heat_used = 0.0

        logger.info(f"Position limits initialized: max_position={self.max_position_size_pct:.1%}, "
                   f"max_heat={self.max_portfolio_heat:.1%}")

    def check_position_limit(self, symbol: str, notional: float,
                            current_notional: float = 0.0) -> Tuple[bool, str]:
        """
        Check if new position respects limits.

        Returns:
            (allowed, reason)
        """
        max_notional = self.portfolio_value * self.max_position_size_pct
        proposed_notional = current_notional + notional

        if proposed_notional > max_notional:
            reason = (f"Position {symbol} would exceed limit: "
                     f"{proposed_notional:,.0f} > {max_notional:,.0f}")
            logger.warning(reason)
            return False, reason

        return True, "Position size OK"

    def check_portfolio_heat(self, required_risk: float) -> Tuple[bool, str]:
        """
        Check if additional risk exceeds portfolio heat limit.
        """
        max_risk = self.portfolio_value * self.max_portfolio_heat
        available_heat = max_risk - self.portfolio_heat_used

        if required_risk > available_heat:
            reason = (f"Insufficient heat: {required_risk:,.0f} > "
                     f"{available_heat:,.0f} available")
            logger.warning(reason)
            return False, reason

        return True, "Heat available"

    def check_correlation_limit(self, symbol: str, position_beta: float,
                               correlations: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check portfolio correlation constraints.
        """
        # Sum of absolute correlations
        corr_sum = sum(abs(c) for c in correlations.values())

        if corr_sum > self.max_correlation_sum:
            reason = (f"Correlation constraint violated: {corr_sum:.2f} > "
                     f"{self.max_correlation_sum:.2f}")
            logger.warning(reason)
            return False, reason

        return True, "Correlation OK"

    def add_position(self, symbol: str, notional: float, risk: float,
                    sector: str, beta: float):
        """Record new position in manager"""
        self.positions[symbol] = {
            'notional': notional,
            'risk': risk,
            'sector': sector,
            'beta': beta,
            'timestamp': datetime.now()
        }
        self.portfolio_heat_used += risk
        self.sector_exposures[sector] += notional

        logger.info(f"Added position {symbol}: {notional:,.0f} notional, "
                   f"{risk:,.0f} risk, {sector} sector")

    def remove_position(self, symbol: str, realized_pnl: float = 0.0):
        """Remove closed position"""
        if symbol in self.positions:
            pos = self.positions.pop(symbol)
            self.portfolio_heat_used -= pos['risk']
            self.sector_exposures[pos['sector']] -= pos['notional']

            logger.info(f"Closed position {symbol}: realized PnL ${realized_pnl:,.2f}")

    def get_available_capital(self) -> float:
        """Get capital available for new positions"""
        total_risk = self.portfolio_value * self.max_portfolio_heat
        available_risk = total_risk - self.portfolio_heat_used
        return available_risk

    def get_concentration_report(self) -> Dict:
        """Generate position concentration report"""
        total_notional = sum(p['notional'] for p in self.positions.values())

        report = {
            'total_positions': len(self.positions),
            'total_notional': total_notional,
            'portfolio_leverage': total_notional / self.portfolio_value if self.portfolio_value > 0 else 0,
            'heat_used_pct': self.portfolio_heat_used / (self.portfolio_value * self.max_portfolio_heat),
            'positions_by_size': sorted(
                [(s, p['notional']) for s, p in self.positions.items()],
                key=lambda x: x[1],
                reverse=True
            ),
            'sector_exposures': dict(self.sector_exposures)
        }

        return report


# ============================================================================
# R-MULTIPLE TRACKING & EXPECTANCY
# ============================================================================

class RMultipleTracker:
    """
    Tracks all trades in R-multiples for objective performance analysis.

    R = Initial Risk (max loss from entry to stop)
    R-multiple = (Profit) / R

    Expectancy = (Win% * Avg_Win) - (Loss% * Avg_Loss)
    """

    def __init__(self, lookback_trades: int = 50):
        """
        Initialize R-multiple tracker.

        Args:
            lookback_trades: Number of recent trades to track for metrics
        """
        self.all_trades: List[RMultiple] = []
        self.lookback_trades = lookback_trades
        self.rolling_trades = deque(maxlen=lookback_trades)

        logger.info(f"R-multiple tracker initialized with {lookback_trades} trade lookback")

    def record_trade(self, trade_id: str, entry_price: float, exit_price: float,
                    stop_loss: float, shares: int, exit_time: datetime,
                    symbol: str, entry_time: datetime, direction: int) -> RMultiple:
        """
        Record a completed trade and calculate R-multiple.

        Args:
            trade_id: Unique trade identifier
            entry_price: Price at entry
            exit_price: Price at exit
            stop_loss: Stop loss price (defines R)
            shares: Position size
            exit_time: Exit timestamp
            symbol: Trading symbol
            entry_time: Entry timestamp
            direction: 1 for long, -1 for short

        Returns:
            RMultiple object with metrics
        """
        # Calculate initial risk (1R)
        initial_risk_pct = abs(entry_price - stop_loss) / entry_price
        initial_risk_dollars = initial_risk_pct * entry_price * shares

        # Calculate P&L
        if direction > 0:  # Long
            pnl = (exit_price - entry_price) * shares
        else:  # Short
            pnl = (entry_price - exit_price) * shares

        # Calculate R-multiple
        if initial_risk_dollars > 0:
            r_multiple = pnl / initial_risk_dollars
        else:
            r_multiple = 0.0

        trade = RMultiple(
            trade_id=trade_id,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss=stop_loss,
            initial_risk=initial_risk_dollars,
            pnl=pnl,
            r_multiple=r_multiple,
            win=pnl > 0,
            entry_time=entry_time,
            exit_time=exit_time,
            symbol=symbol,
            direction=direction
        )

        self.all_trades.append(trade)
        self.rolling_trades.append(trade)

        logger.info(f"Trade {trade_id} recorded: R-multiple={r_multiple:.2f}, "
                   f"PnL=${pnl:,.2f}, initial_risk=${initial_risk_dollars:,.2f}")

        return trade

    def calculate_expectancy(self) -> Dict[str, float]:
        """
        Calculate expectancy: (Win% * Avg Win in R) - (Loss% * Avg Loss in R)
        """
        if len(self.rolling_trades) < 1:
            return {
                'expectancy': 0.0,
                'win_rate': 0.0,
                'avg_win_r': 0.0,
                'avg_loss_r': 0.0,
                'num_trades': 0
            }

        trades = list(self.rolling_trades)
        winning_trades = [t for t in trades if t.win]
        losing_trades = [t for t in trades if not t.win]

        win_rate = len(winning_trades) / len(trades) if trades else 0
        loss_rate = len(losing_trades) / len(trades) if trades else 0

        # Average R-multiples
        avg_win_r = np.mean([t.r_multiple for t in winning_trades]) if winning_trades else 0
        avg_loss_r = abs(np.mean([t.r_multiple for t in losing_trades])) if losing_trades else 0

        expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

        return {
            'expectancy': expectancy,
            'win_rate': win_rate,
            'avg_win_r': avg_win_r,
            'avg_loss_r': avg_loss_r,
            'num_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_pnl': sum(t.pnl for t in trades),
            'total_risk': sum(t.initial_risk for t in trades)
        }

    def get_rolling_metrics(self) -> Dict:
        """Get performance metrics for rolling window"""
        expectancy = self.calculate_expectancy()

        if len(self.rolling_trades) < 1:
            return expectancy

        trades = list(self.rolling_trades)

        return {
            **expectancy,
            'consecutive_wins': self._count_consecutive_wins(),
            'consecutive_losses': self._count_consecutive_losses(),
            'max_win_streak': self._get_max_win_streak(),
            'max_loss_streak': self._get_max_loss_streak(),
            'profit_factor': self._calculate_profit_factor(trades)
        }

    def _count_consecutive_wins(self) -> int:
        """Count current consecutive winning trades"""
        count = 0
        for trade in reversed(list(self.rolling_trades)):
            if trade.win:
                count += 1
            else:
                break
        return count

    def _count_consecutive_losses(self) -> int:
        """Count current consecutive losing trades"""
        count = 0
        for trade in reversed(list(self.rolling_trades)):
            if not trade.win:
                count += 1
            else:
                break
        return count

    def _get_max_win_streak(self) -> int:
        """Get maximum consecutive wins in rolling window"""
        trades = list(self.rolling_trades)
        max_streak = 0
        current_streak = 0

        for trade in trades:
            if trade.win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _get_max_loss_streak(self) -> int:
        """Get maximum consecutive losses in rolling window"""
        trades = list(self.rolling_trades)
        max_streak = 0
        current_streak = 0

        for trade in trades:
            if not trade.win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _calculate_profit_factor(self, trades: List[RMultiple]) -> float:
        """Calculate profit factor: gross wins / abs(gross losses)"""
        gross_wins = sum(t.pnl for t in trades if t.pnl > 0)
        gross_losses = abs(sum(t.pnl for t in trades if t.pnl < 0))

        if gross_losses == 0:
            return float('inf') if gross_wins > 0 else 1.0

        return gross_wins / gross_losses

    def export_trades(self, filepath: str):
        """Export all trades to CSV for analysis"""
        df = pd.DataFrame([
            {
                'trade_id': t.trade_id,
                'symbol': t.symbol,
                'entry_time': t.entry_time.isoformat(),
                'exit_time': t.exit_time.isoformat(),
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'stop_loss': t.stop_loss,
                'initial_risk': t.initial_risk,
                'pnl': t.pnl,
                'r_multiple': t.r_multiple,
                'win': t.win,
                'direction': 'LONG' if t.direction > 0 else 'SHORT'
            }
            for t in self.all_trades
        ])

        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(self.all_trades)} trades to {filepath}")


# ============================================================================
# HEDGING STRATEGIES
# ============================================================================

class HedgingEngine:
    """
    Manages hedging strategies for portfolio protection.

    Strategies:
    - Delta hedging: Use options to hedge directional exposure
    - Correlation hedging: Add negatively correlated assets
    - Tail risk hedging: Buy OTM puts as insurance
    - Beta management: Reduce systematic risk exposure
    """

    def __init__(self, config: Dict = None):
        """Initialize hedging engine"""
        self.config = config or {}
        self.active_hedges: Dict[str, Dict] = {}

        # Hedging parameters
        self.target_delta = self.config.get('target_delta', 0.0)
        self.max_hedge_cost_pct = self.config.get('max_hedge_cost_pct', 0.02)
        self.rebalance_threshold = self.config.get('rebalance_threshold', 0.15)

        logger.info("Hedging engine initialized")

    def calculate_portfolio_delta(self, positions: Dict[str, Dict],
                                 option_deltas: Dict[str, float] = None) -> float:
        """
        Calculate total portfolio delta exposure.

        Args:
            positions: Dict of {symbol: {'notional': float, 'beta': float}}
            option_deltas: Dict of {option_id: delta}

        Returns:
            Portfolio delta (% of total value)
        """
        equity_delta = sum(p.get('beta', 1.0) * p.get('notional', 0)
                          for p in positions.values())

        option_delta = 0.0
        if option_deltas:
            option_delta = sum(option_deltas.values())

        total_notional = sum(p.get('notional', 0) for p in positions.values())

        if total_notional == 0:
            return 0.0

        return (equity_delta + option_delta) / total_notional

    def recommend_delta_hedge(self, current_delta: float,
                             available_capital: float) -> Optional[Dict]:
        """
        Recommend hedge positions to neutralize delta.

        Returns:
            {'type': 'hedge', 'position': ..., 'cost': ...} or None
        """
        delta_gap = current_delta - self.target_delta

        if abs(delta_gap) < self.rebalance_threshold:
            return None  # No rehedge needed

        # Simple hedge: buy put options or short SPY to reduce delta
        if delta_gap > 0:  # Long bias, need to hedge down
            hedge_type = 'short_etf'
            hedge_notional = abs(delta_gap) * available_capital
            cost_estimate = hedge_notional * 0.001  # ~10bps for short

            return {
                'type': HedgeType.DELTA_HEDGE.value,
                'action': 'hedge_long_bias',
                'notional': hedge_notional,
                'estimated_cost': cost_estimate,
                'delta_impact': -delta_gap
            }
        else:
            # Short bias, need to hedge up
            hedge_notional = abs(delta_gap) * available_capital
            return {
                'type': HedgeType.DELTA_HEDGE.value,
                'action': 'hedge_short_bias',
                'notional': hedge_notional,
                'estimated_cost': hedge_notional * 0.001,
                'delta_impact': -delta_gap
            }

    def recommend_tail_risk_hedge(self, portfolio_value: float,
                                 current_var_95: float) -> Optional[Dict]:
        """
        Recommend tail risk hedging (buy OTM puts).

        VaR-based approach: buy protection if downside risk exceeds threshold.
        """
        var_threshold = portfolio_value * 0.05  # Protect against 5% move

        if current_var_95 > var_threshold:
            # Recommend put options
            notional_to_protect = current_var_95

            return {
                'type': HedgeType.TAIL_RISK_HEDGE.value,
                'action': 'buy_otm_puts',
                'protection_notional': notional_to_protect,
                'strike_offset': 0.02,  # 2% OTM
                'duration_days': 30,
                'estimated_cost_pct': 0.01  # 1% of notional
            }

        return None

    def recommend_correlation_hedge(self, high_correlation_pairs: List[Tuple[str, float]]
                                   ) -> Optional[Dict]:
        """
        Recommend adding negatively correlated assets if concentration too high.

        If multiple longs are all correlated, diversify or reduce.
        """
        if not high_correlation_pairs:
            return None

        avg_corr = np.mean([c for _, c in high_correlation_pairs])

        if avg_corr > 0.85:
            return {
                'type': HedgeType.CORRELATION_HEDGE.value,
                'action': 'reduce_concentration',
                'avg_correlation': avg_corr,
                'recommendation': 'Consider long VIX hedge or reduce position sizes',
                'affected_pairs': high_correlation_pairs
            }

        return None

    def get_hedge_summary(self) -> Dict:
        """Get summary of all active hedges"""
        return {
            'num_active_hedges': len(self.active_hedges),
            'total_hedge_notional': sum(h.get('notional', 0)
                                       for h in self.active_hedges.values()),
            'hedges': self.active_hedges
        }


# ============================================================================
# VALUE AT RISK (VaR) & STRESS TESTING
# ============================================================================

class RiskAnalyzer:
    """
    Advanced risk analysis: VaR, CVaR, correlation, beta, stress testing.
    """

    def __init__(self, lookback_days: int = 252):
        """Initialize risk analyzer"""
        self.lookback_days = lookback_days
        self.returns_history: Dict[str, List[float]] = defaultdict(list)
        self.correlation_matrix = None

        logger.info(f"Risk analyzer initialized with {lookback_days} day lookback")

    def update_returns(self, symbol: str, returns: List[float]):
        """Update historical returns for a symbol"""
        self.returns_history[symbol] = returns[-self.lookback_days:]

    def calculate_var_95(self, portfolio_returns: np.ndarray) -> float:
        """
        Calculate Value at Risk at 95% confidence.

        VaR = -percentile(returns, 5)
        """
        if len(portfolio_returns) < 20:
            return 0.0

        return -np.percentile(portfolio_returns, 5)

    def calculate_cvar_95(self, portfolio_returns: np.ndarray) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall) at 95%.

        CVaR = mean of returns worse than VaR
        """
        if len(portfolio_returns) < 20:
            return 0.0

        var_95 = self.calculate_var_95(portfolio_returns)
        return -np.mean(portfolio_returns[portfolio_returns <= -var_95])

    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate correlation matrix between all positions"""
        if not self.returns_history:
            return pd.DataFrame()

        df = pd.DataFrame(self.returns_history)
        self.correlation_matrix = df.corr()
        return self.correlation_matrix

    def get_high_correlation_pairs(self, threshold: float = 0.8) -> List[Tuple[str, str, float]]:
        """Find position pairs with correlation above threshold"""
        if self.correlation_matrix is None:
            self.calculate_correlation_matrix()

        pairs = []
        if self.correlation_matrix is not None:
            for i, col1 in enumerate(self.correlation_matrix.columns):
                for col2 in self.correlation_matrix.columns[i+1:]:
                    corr = self.correlation_matrix.loc[col1, col2]
                    if corr > threshold:
                        pairs.append((col1, col2, corr))

        return sorted(pairs, key=lambda x: x[2], reverse=True)

    def monte_carlo_simulation(self, initial_value: float, daily_returns: np.ndarray,
                              num_simulations: int = 10000,
                              horizon_days: int = 20) -> Dict:
        """
        Monte Carlo simulation for portfolio value distribution.

        Returns:
            Dict with quantiles, max drawdown, etc.
        """
        if len(daily_returns) < 20:
            return {'error': 'Insufficient data for simulation'}

        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)

        # Generate simulated paths
        simulations = np.zeros((num_simulations, horizon_days))
        simulations[:, 0] = initial_value

        for t in range(1, horizon_days):
            shocks = np.random.normal(mean_return, std_return, num_simulations)
            simulations[:, t] = simulations[:, t-1] * (1 + shocks)

        final_values = simulations[:, -1]

        return {
            'mean_final_value': np.mean(final_values),
            'std_final_value': np.std(final_values),
            'percentile_5': np.percentile(final_values, 5),
            'percentile_25': np.percentile(final_values, 25),
            'percentile_50': np.percentile(final_values, 50),
            'percentile_75': np.percentile(final_values, 75),
            'percentile_95': np.percentile(final_values, 95),
            'max_drawdown_mean': np.mean([
                (np.max(sim) - np.min(sim)) / np.max(sim) if np.max(sim) > 0 else 0
                for sim in simulations
            ]),
            'probability_loss': np.sum(final_values < initial_value) / num_simulations,
            'probability_5pct_loss': np.sum(final_values < initial_value * 0.95) / num_simulations
        }

    def stress_test_scenarios(self, positions: Dict[str, float],
                             market_moves: Dict[str, float]) -> Dict:
        """
        Stress test portfolio against specified market moves.

        Args:
            positions: {symbol: notional}
            market_moves: {symbol: pct_change} e.g., {'SPY': -0.10}

        Returns:
            Portfolio PnL under scenario
        """
        scenario_pnl = 0.0

        for symbol, notional in positions.items():
            if symbol in market_moves:
                move = market_moves[symbol]
                pnl = notional * move
                scenario_pnl += pnl

        return {
            'scenario_pnl': scenario_pnl,
            'pnl_pct': scenario_pnl / sum(positions.values()) if sum(positions.values()) > 0 else 0,
            'details': {symbol: positions[symbol] * market_moves.get(symbol, 0)
                       for symbol in positions}
        }


# ============================================================================
# CIRCUIT BREAKER & DAILY LOSS LIMITS
# ============================================================================

class CircuitBreaker:
    """
    Trading circuit breaker: pause or stop trading on excessive losses.

    Rules:
    - Daily loss > 2%: Reduce position size
    - Daily loss > 5%: Stop trading for remainder of day
    - Max drawdown > 10%: Alert and reduce size
    - Max drawdown > 20%: Circuit breaker - pause trading
    """

    def __init__(self, portfolio_value: float, config: Dict = None):
        """Initialize circuit breaker"""
        self.portfolio_value = portfolio_value
        self.config = config or {}

        # Daily limits
        self.daily_loss_limit_pct = self.config.get('daily_loss_limit_pct', 0.05)  # 5%
        self.daily_loss_warning_pct = self.config.get('daily_loss_warning_pct', 0.02)  # 2%

        # Drawdown limits
        self.max_drawdown_limit = self.config.get('max_drawdown_limit', 0.20)  # 20%
        self.max_drawdown_warning = self.config.get('max_drawdown_warning', 0.10)  # 10%

        # Tracking
        self.daily_start_value = portfolio_value
        self.peak_value = portfolio_value
        self.circuit_breaker_active = False
        self.trading_paused = False
        self.current_drawdown = 0.0
        self.current_daily_loss = 0.0

        logger.info("Circuit breaker initialized")

    def update_portfolio(self, current_value: float) -> Dict:
        """
        Update circuit breaker status with current portfolio value.

        Returns:
            Dict with status and alerts
        """
        self.peak_value = max(self.peak_value, current_value)

        # Calculate daily loss
        daily_loss = (self.daily_start_value - current_value) / self.daily_start_value
        self.current_daily_loss = daily_loss

        # Calculate drawdown
        drawdown = (self.peak_value - current_value) / self.peak_value
        self.current_drawdown = drawdown

        status = {
            'timestamp': datetime.now(),
            'current_value': current_value,
            'daily_loss_pct': daily_loss,
            'drawdown_pct': drawdown,
            'alerts': [],
            'circuit_breaker_active': self.circuit_breaker_active,
            'trading_paused': self.trading_paused
        }

        # Check alerts
        if daily_loss > self.daily_loss_limit_pct:
            self.circuit_breaker_active = True
            self.trading_paused = True
            status['alerts'].append({
                'level': AlertLevel.CRITICAL.value,
                'message': f'Daily loss limit exceeded: {daily_loss:.2%} > {self.daily_loss_limit_pct:.2%}',
                'action': 'TRADING_HALTED'
            })
            logger.critical(status['alerts'][-1]['message'])

        elif daily_loss > self.daily_loss_warning_pct:
            status['alerts'].append({
                'level': AlertLevel.WARNING.value,
                'message': f'Daily loss warning: {daily_loss:.2%} > {self.daily_loss_warning_pct:.2%}',
                'action': 'REDUCE_POSITION_SIZE'
            })
            logger.warning(status['alerts'][-1]['message'])

        if drawdown > self.max_drawdown_limit:
            self.circuit_breaker_active = True
            status['alerts'].append({
                'level': AlertLevel.CRITICAL.value,
                'message': f'Max drawdown exceeded: {drawdown:.2%} > {self.max_drawdown_limit:.2%}',
                'action': 'CIRCUIT_BREAKER_ACTIVE'
            })
            logger.critical(status['alerts'][-1]['message'])

        elif drawdown > self.max_drawdown_warning:
            status['alerts'].append({
                'level': AlertLevel.WARNING.value,
                'message': f'Drawdown warning: {drawdown:.2%} > {self.max_drawdown_warning:.2%}',
                'action': 'REDUCE_POSITION_SIZE'
            })
            logger.warning(status['alerts'][-1]['message'])

        return status

    def reset_daily(self):
        """Reset daily counters at market close/open"""
        self.daily_start_value = self.peak_value
        self.trading_paused = False
        logger.info(f"Daily counters reset. New daily reference: ${self.daily_start_value:,.2f}")


# ============================================================================
# MAIN RISK MANAGER ORCHESTRATOR
# ============================================================================

class PortfolioRiskManager:
    """
    Main orchestrator for all risk management components.

    Integrates:
    - Position limits
    - R-multiple tracking
    - Hedging strategies
    - Risk metrics calculation
    - Circuit breakers
    - Alert generation
    """

    def __init__(self, portfolio_value: float, config: Dict = None):
        """Initialize portfolio risk manager"""
        self.portfolio_value = portfolio_value
        self.config = config or self._default_config()

        # Initialize components
        self.position_limits = PositionLimitManager(portfolio_value, self.config)
        self.r_tracker = RMultipleTracker(self.config.get('lookback_trades', 50))
        self.hedging = HedgingEngine(self.config)
        self.risk_analyzer = RiskAnalyzer(self.config.get('lookback_days', 252))
        self.circuit_breaker = CircuitBreaker(portfolio_value, self.config)

        # Portfolio state
        self.positions: Dict[str, Dict] = {}
        self.daily_returns: List[float] = []
        self.alerts: List[Dict] = []

        logger.info(f"Portfolio Risk Manager initialized for ${portfolio_value:,.2f}")

    @staticmethod
    def _default_config() -> Dict:
        """Default configuration parameters"""
        return {
            # Position limits
            'max_position_size_pct': 0.05,
            'max_sector_exposure_pct': 0.25,
            'max_portfolio_heat': 0.02,
            'max_correlation_sum': 3.0,

            # Circuit breaker
            'daily_loss_limit_pct': 0.05,
            'daily_loss_warning_pct': 0.02,
            'max_drawdown_limit': 0.20,
            'max_drawdown_warning': 0.10,

            # Hedging
            'target_delta': 0.0,
            'max_hedge_cost_pct': 0.02,
            'rebalance_threshold': 0.15,

            # Tracking
            'lookback_trades': 50,
            'lookback_days': 252
        }

    def check_pre_trade_limits(self, symbol: str, notional: float,
                              required_risk: float) -> Tuple[bool, List[str]]:
        """
        Check all limits before allowing a trade.

        Returns:
            (allowed, reasons)
        """
        reasons = []

        # Circuit breaker
        if self.circuit_breaker.circuit_breaker_active:
            reasons.append(f"Circuit breaker active - trading halted")
            return False, reasons

        # Position size
        allowed, msg = self.position_limits.check_position_limit(
            symbol, notional, self.positions.get(symbol, {}).get('notional', 0)
        )
        if not allowed:
            reasons.append(msg)

        # Portfolio heat
        allowed, msg = self.position_limits.check_portfolio_heat(required_risk)
        if not allowed:
            reasons.append(msg)

        return len(reasons) == 0, reasons

    def add_position(self, symbol: str, notional: float, risk: float,
                    sector: str = 'unknown', beta: float = 1.0):
        """Record new position"""
        self.position_limits.add_position(symbol, notional, risk, sector, beta)
        self.positions[symbol] = {
            'notional': notional,
            'risk': risk,
            'sector': sector,
            'beta': beta,
            'entry_time': datetime.now()
        }

    def close_position(self, symbol: str, pnl: float):
        """Close position and update trackers"""
        if symbol in self.positions:
            self.position_limits.remove_position(symbol, pnl)
            del self.positions[symbol]

    def record_trade(self, trade_id: str, symbol: str, entry_price: float,
                    exit_price: float, stop_loss: float, shares: int,
                    entry_time: datetime, exit_time: datetime,
                    direction: int) -> RMultiple:
        """Record closed trade for R-multiple analysis"""
        return self.r_tracker.record_trade(
            trade_id, entry_price, exit_price, stop_loss, shares, exit_time,
            symbol, entry_time, direction
        )

    def calculate_risk_metrics(self, cash: float,
                              daily_return: float = 0.0) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        total_notional = sum(p['notional'] for p in self.positions.values())
        total_exposure = total_notional + cash
        leverage = total_notional / total_exposure if total_exposure > 0 else 0

        # Update portfolio value
        self.portfolio_value = total_exposure

        # Record daily return
        if daily_return != 0.0:
            self.daily_returns.append(daily_return)

        # Calculate VaR and CVaR
        if len(self.daily_returns) > 20:
            returns_array = np.array(self.daily_returns[-252:])
            var_95 = self.risk_analyzer.calculate_var_95(returns_array)
            cvar_95 = self.risk_analyzer.calculate_cvar_95(returns_array)
            portfolio_vol = np.std(returns_array) * np.sqrt(252)
        else:
            var_95 = 0.0
            cvar_95 = 0.0
            portfolio_vol = 0.15

        # Calculate drawdown
        circuit_status = self.circuit_breaker.update_portfolio(self.portfolio_value)

        metrics = RiskMetrics(
            portfolio_value=self.portfolio_value,
            cash_available=cash,
            total_exposure=total_exposure,
            leverage_ratio=leverage,
            daily_pnl=daily_return * self.portfolio_value,
            daily_loss_pct=circuit_status['daily_loss_pct'],
            drawdown=circuit_status['drawdown_pct'],
            max_drawdown=circuit_status['drawdown_pct'],
            portfolio_volatility=portfolio_vol,
            portfolio_beta=np.mean([p.get('beta', 1.0) for p in self.positions.values()]) if self.positions else 1.0,
            var_95=var_95,
            cvar_95=cvar_95,
            num_open_positions=len(self.positions),
            heat_used=self.position_limits.portfolio_heat_used / (self.portfolio_value * self.position_limits.max_portfolio_heat) if self.portfolio_value > 0 else 0
        )

        return metrics

    def get_risk_report(self) -> Dict:
        """Generate comprehensive risk report"""
        expectancy = self.r_tracker.calculate_expectancy()
        hedge_summary = self.hedging.get_hedge_summary()
        concentration = self.position_limits.get_concentration_report()
        correlations = self.risk_analyzer.get_high_correlation_pairs()

        return {
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': self.portfolio_value,
            'expectancy_metrics': expectancy,
            'hedge_summary': hedge_summary,
            'concentration': concentration,
            'high_correlations': [(p[0], p[1], f"{p[2]:.3f}") for p in correlations],
            'circuit_breaker_status': {
                'active': self.circuit_breaker.circuit_breaker_active,
                'trading_paused': self.circuit_breaker.trading_paused,
                'daily_loss_pct': self.circuit_breaker.current_daily_loss,
                'drawdown_pct': self.circuit_breaker.current_drawdown
            },
            'num_open_positions': len(self.positions),
            'heat_used_pct': self.position_limits.portfolio_heat_used / (self.portfolio_value * self.position_limits.max_portfolio_heat) if self.portfolio_value > 0 else 0
        }


# ============================================================================
# PROMETHEUS ALERT RULES GENERATOR
# ============================================================================

class PrometheusAlertGenerator:
    """
    Generates Prometheus alert rules YAML from risk metrics.
    """

    @staticmethod
    def generate_alert_rules(output_path: str):
        """Generate Prometheus alert rules YAML file"""

        rules = """groups:
  - name: multi_factor_strategy_alerts
    interval: 30s
    rules:

      # Daily Loss Alerts
      - alert: DailyLossWarning
        expr: daily_loss_pct > 0.02
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Daily loss warning - {{ $value | humanizePercentage }}"
          description: "Daily loss has exceeded 2% threshold. Current: {{ $value | humanizePercentage }}"

      - alert: DailyLossCritical
        expr: daily_loss_pct > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Daily loss critical - {{ $value | humanizePercentage }}"
          description: "Daily loss has exceeded 5% limit. STOP TRADING. Current: {{ $value | humanizePercentage }}"

      # Drawdown Alerts
      - alert: DrawdownWarning
        expr: drawdown_pct > 0.10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Drawdown warning - {{ $value | humanizePercentage }}"
          description: "Portfolio drawdown has exceeded 10% threshold. Current: {{ $value | humanizePercentage }}"

      - alert: DrawdownCritical
        expr: drawdown_pct > 0.20
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Drawdown critical - {{ $value | humanizePercentage }}"
          description: "Portfolio drawdown has exceeded 20% limit. Circuit breaker active. Current: {{ $value | humanizePercentage }}"

      # Win Rate Alerts
      - alert: LowWinRate
        expr: win_rate_20trades < 0.35
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Win rate low - {{ $value | humanizePercentage }}"
          description: "Win rate over last 20 trades below 35%. Current: {{ $value | humanizePercentage }}"

      # Position Concentration Alerts
      - alert: HighPositionConcentration
        expr: max_position_pct > 0.075
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Position concentration high"
          description: "Single position exceeds 7.5% of portfolio. Current: {{ $value | humanizePercentage }}"

      # Correlation Alerts
      - alert: HighCorrelation
        expr: max_correlation_pairs > 0.85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High correlation detected"
          description: "Position correlation pairs > 0.85. Insufficient diversification. Pairs: {{ $labels.symbols }}"

      # Leverage Alerts
      - alert: HighLeverage
        expr: leverage_ratio > 2.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Leverage elevated"
          description: "Portfolio leverage has exceeded 2.5x. Current: {{ $value }}"

      # Expectancy Alerts
      - alert: NegativeExpectancy
        expr: expectancy < 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Negative expectancy detected"
          description: "Trade expectancy is negative: {{ $value | humanize }}. Strategy not profitable."

      # Heat Usage Alerts
      - alert: HighHeatUsage
        expr: heat_used_pct > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Portfolio heat nearly exhausted"
          description: "Heat usage exceeds 85%. Limited capacity for new trades. Current: {{ $value | humanizePercentage }}"

      # Volatility Alerts
      - alert: HighVolatility
        expr: portfolio_volatility > 0.30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Portfolio volatility elevated"
          description: "Annualized volatility exceeded 30%. Current: {{ $value | humanizePercentage }}"

      # VaR Alerts
      - alert: HighValueAtRisk
        expr: var_95_pct > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Value at Risk elevated"
          description: "95% VaR exceeds 5% of portfolio. Current: {{ $value | humanizePercentage }}"
"""

        with open(output_path, 'w') as f:
            f.write(rules)

        logger.info(f"Prometheus alert rules written to {output_path}")

    @staticmethod
    def generate_grafana_dashboard_json(output_path: str):
        """Generate Grafana dashboard JSON for visualization"""

        dashboard = {
            "dashboard": {
                "title": "Multi-Factor Strategy Risk Dashboard",
                "panels": [
                    {
                        "title": "Portfolio Value",
                        "targets": [
                            {"expr": "portfolio_value", "legendFormat": "Portfolio"}
                        ],
                        "type": "graph"
                    },
                    {
                        "title": "Daily P&L",
                        "targets": [
                            {"expr": "daily_pnl", "legendFormat": "Daily PnL"}
                        ],
                        "type": "graph"
                    },
                    {
                        "title": "Drawdown %",
                        "targets": [
                            {"expr": "drawdown_pct * 100", "legendFormat": "Drawdown"}
                        ],
                        "type": "gauge",
                        "fieldConfig": {
                            "defaults": {
                                "max": 30,
                                "min": 0,
                                "color": {"mode": "thresholds"}
                            }
                        }
                    },
                    {
                        "title": "Win Rate (20 trades)",
                        "targets": [
                            {"expr": "win_rate_20trades * 100", "legendFormat": "Win Rate"}
                        ],
                        "type": "gauge"
                    },
                    {
                        "title": "Trade Expectancy",
                        "targets": [
                            {"expr": "expectancy", "legendFormat": "Expectancy"}
                        ],
                        "type": "graph"
                    },
                    {
                        "title": "Position Concentration",
                        "targets": [
                            {"expr": "max_position_pct * 100", "legendFormat": "Max Position"}
                        ],
                        "type": "graph"
                    },
                    {
                        "title": "Portfolio Leverage",
                        "targets": [
                            {"expr": "leverage_ratio", "legendFormat": "Leverage"}
                        ],
                        "type": "gauge"
                    },
                    {
                        "title": "Heat Usage",
                        "targets": [
                            {"expr": "heat_used_pct * 100", "legendFormat": "Heat %"}
                        ],
                        "type": "gauge"
                    },
                    {
                        "title": "Portfolio Beta",
                        "targets": [
                            {"expr": "portfolio_beta", "legendFormat": "Beta"}
                        ],
                        "type": "graph"
                    },
                    {
                        "title": "Value at Risk (95%)",
                        "targets": [
                            {"expr": "var_95_pct * 100", "legendFormat": "VaR 95%"}
                        ],
                        "type": "graph"
                    },
                    {
                        "title": "Volatility (annualized)",
                        "targets": [
                            {"expr": "portfolio_volatility * 100", "legendFormat": "Volatility"}
                        ],
                        "type": "graph"
                    }
                ]
            }
        }

        with open(output_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

        logger.info(f"Grafana dashboard written to {output_path}")


# ============================================================================
# EXAMPLE USAGE & TESTING
# ============================================================================

def example_usage():
    """Demonstrate risk management layer functionality"""

    print("\n" + "=" * 80)
    print("MULTI-FACTOR STRATEGY RISK MANAGEMENT LAYER DEMONSTRATION")
    print("=" * 80)

    # Initialize risk manager
    portfolio_value = 1000000  # 1M portfolio
    config = {
        'max_position_size_pct': 0.05,
        'max_portfolio_heat': 0.02,
        'daily_loss_warning_pct': 0.02,
        'daily_loss_limit_pct': 0.05,
        'max_drawdown_warning': 0.10,
        'max_drawdown_limit': 0.20,
        'lookback_trades': 50
    }

    risk_mgr = PortfolioRiskManager(portfolio_value, config)

    print(f"\nInitial Portfolio Value: ${portfolio_value:,.2f}")
    print(f"Max Portfolio Heat: {config['max_portfolio_heat']:.1%}")
    print(f"Max Position Size: {config['max_position_size_pct']:.1%}")

    # Simulate adding positions
    print("\n" + "-" * 80)
    print("Adding positions...")

    # Position 1: SPY
    risk_mgr.add_position(
        symbol='SPY',
        notional=50000,
        risk=1000,
        sector='equities',
        beta=1.0
    )
    print(f"Added SPY: $50,000 notional, $1,000 risk")

    # Position 2: QQQ
    risk_mgr.add_position(
        symbol='QQQ',
        notional=40000,
        risk=1200,
        sector='equities',
        beta=1.3
    )
    print(f"Added QQQ: $40,000 notional, $1,200 risk")

    # Check limits
    print("\n" + "-" * 80)
    print("Risk Metrics:")

    metrics = risk_mgr.calculate_risk_metrics(
        cash=portfolio_value - 90000,
        daily_return=0.002
    )

    print(f"Total Exposure: ${metrics.total_exposure:,.2f}")
    print(f"Leverage: {metrics.leverage_ratio:.2f}x")
    print(f"Heat Used: {metrics.heat_used:.1%}")
    print(f"Daily PnL: ${metrics.daily_pnl:,.2f}")
    print(f"Positions: {metrics.num_open_positions}")

    # Simulate trades
    print("\n" + "-" * 80)
    print("Simulating closed trades...")

    trade1 = risk_mgr.record_trade(
        trade_id='T001',
        symbol='SPY',
        entry_price=450.00,
        exit_price=455.00,
        stop_loss=448.00,
        shares=100,
        entry_time=datetime.now() - timedelta(hours=2),
        exit_time=datetime.now(),
        direction=1
    )

    print(f"Trade 1 (SPY Long): Entry $450, Exit $455, Stop $448")
    print(f"  PnL: ${trade1.pnl:.2f}, R-multiple: {trade1.r_multiple:.2f}R")

    trade2 = risk_mgr.record_trade(
        trade_id='T002',
        symbol='QQQ',
        entry_price=380.00,
        exit_price=375.00,
        stop_loss=382.00,
        shares=100,
        entry_time=datetime.now() - timedelta(hours=1),
        exit_time=datetime.now(),
        direction=1
    )

    print(f"Trade 2 (QQQ Long): Entry $380, Exit $375, Stop $382")
    print(f"  PnL: ${trade2.pnl:.2f}, R-multiple: {trade2.r_multiple:.2f}R")

    # Expectancy calculation
    print("\n" + "-" * 80)
    print("Trade Expectancy Analysis:")

    expectancy = risk_mgr.r_tracker.calculate_expectancy()
    print(f"Win Rate: {expectancy['win_rate']:.1%}")
    print(f"Avg Win (R): {expectancy['avg_win_r']:.2f}R")
    print(f"Avg Loss (R): {expectancy['avg_loss_r']:.2f}R")
    print(f"Expectancy: {expectancy['expectancy']:.2f}R")

    # Risk report
    print("\n" + "-" * 80)
    print("Comprehensive Risk Report:")

    risk_report = risk_mgr.get_risk_report()
    print(f"Expectancy: {risk_report['expectancy_metrics']['expectancy']:.2f}R")
    print(f"Heat Used: {risk_report['heat_used_pct']:.1%}")
    print(f"Circuit Breaker Active: {risk_report['circuit_breaker_status']['active']}")
    print(f"Open Positions: {risk_report['num_open_positions']}")

    # Generate alert rules
    print("\n" + "-" * 80)
    print("Generating Prometheus alert rules...")

    PrometheusAlertGenerator.generate_alert_rules(
        '/tmp/alert_rules.yml'
    )
    print("Alert rules generated: /tmp/alert_rules.yml")

    PrometheusAlertGenerator.generate_grafana_dashboard_json(
        '/tmp/grafana_dashboard.json'
    )
    print("Grafana dashboard generated: /tmp/grafana_dashboard.json")

    # Export trades
    print("\n" + "-" * 80)
    print("Exporting trade data...")

    risk_mgr.r_tracker.export_trades('/tmp/trades.csv')
    print("Trades exported to: /tmp/trades.csv")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    example_usage()
