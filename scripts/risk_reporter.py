"""
Risk Reporter for Moomoo Paper Trading

Generates detailed risk reports including R-multiple tracking, Greeks exposure,
and performance metrics for portfolio analysis.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

from config.options_risk_config import DEFAULT_RISK_LIMITS


logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a single trade with performance metrics."""

    order_id: str
    symbol: str
    option_type: str  # 'CALL' or 'PUT'
    strike_price: float
    expiration_date: str
    quantity: int
    entry_price: float  # Premium paid
    entry_time: str  # ISO timestamp
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    realized_pnl: float = 0.0
    r_multiple: float = 0.0  # R-multiple for performance tracking
    stop_loss_level: float = 0.0
    take_profit_level: float = 0.0
    status: str = "OPEN"  # 'OPEN' or 'CLOSED'
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @property
    def notional_value(self) -> float:
        """Get notional value of position."""
        return self.entry_price * self.quantity * 100.0

    @property
    def max_loss(self) -> float:
        """Get maximum possible loss (premium paid)."""
        return self.notional_value

    @property
    def duration_hours(self) -> Optional[float]:
        """Get trade duration in hours."""
        if not self.exit_time:
            entry = datetime.fromisoformat(self.entry_time)
            exit_dt = datetime.now()
        else:
            entry = datetime.fromisoformat(self.entry_time)
            exit_dt = datetime.fromisoformat(self.exit_time)

        delta = exit_dt - entry
        return delta.total_seconds() / 3600.0


class RMultipleTracker:
    """Tracks all trades using R-multiple analysis for consistent performance measurement."""

    def __init__(self, account_size: float = 100_000.00):
        """Initialize R-multiple tracker.

        Args:
            account_size: Starting account size
        """
        self.account_size = account_size
        self.trades: List[TradeRecord] = []
        self.initial_balance = account_size

    def add_trade(self, trade: TradeRecord) -> None:
        """Add a trade to tracking.

        Args:
            trade: TradeRecord to add
        """
        self.trades.append(trade)

    def calculate_r_multiple(
        self,
        entry_price: float,
        exit_price: float,
        stop_loss_price: float,
        quantity: int,
    ) -> float:
        """Calculate R-multiple for a trade.

        R-multiple = (Profit or Loss) / Risk Per Trade
        where Risk Per Trade = (Entry Price - Stop Loss) * Quantity * 100

        Args:
            entry_price: Entry premium
            exit_price: Exit premium
            stop_loss_price: Stop loss level
            quantity: Number of contracts

        Returns:
            R-multiple value
        """
        risk_per_trade = (entry_price - stop_loss_price) * quantity * 100.0
        if risk_per_trade <= 0:
            return 0.0

        profit = (exit_price - entry_price) * quantity * 100.0
        return profit / risk_per_trade

    def get_trade_statistics(self) -> Dict[str, float]:
        """Calculate trade statistics across all trades.

        Returns:
            Dictionary with trade statistics
        """
        if not self.trades:
            return {}

        closed_trades = [t for t in self.trades if t.status == "CLOSED"]
        if not closed_trades:
            return {}

        r_multiples = [t.r_multiple for t in closed_trades if t.r_multiple != 0]
        pnls = [t.realized_pnl for t in closed_trades]

        wins = [pnl for pnl in pnls if pnl > 0]
        losses = [pnl for pnl in pnls if pnl < 0]

        win_count = len(wins)
        loss_count = len(losses)
        total_trades = win_count + loss_count

        return {
            "total_trades": float(total_trades),
            "winning_trades": float(win_count),
            "losing_trades": float(loss_count),
            "win_rate_percent": (win_count / total_trades * 100.0) if total_trades > 0 else 0.0,
            "total_pnl": float(sum(pnls)),
            "average_pnl": float(statistics.mean(pnls)) if pnls else 0.0,
            "max_win": float(max(wins)) if wins else 0.0,
            "max_loss": float(min(losses)) if losses else 0.0,
            "avg_win": float(statistics.mean(wins)) if wins else 0.0,
            "avg_loss": float(statistics.mean(losses)) if losses else 0.0,
            "avg_r_multiple": float(statistics.mean(r_multiples)) if r_multiples else 0.0,
            "expectancy": self._calculate_expectancy(pnls, total_trades),
            "profit_factor": (sum(wins) / abs(sum(losses)))
            if losses and sum(losses) != 0
            else 0.0,
        }

    def _calculate_expectancy(self, pnls: List[float], total_trades: int) -> float:
        """Calculate expectancy per trade.

        Expectancy = (Win% * Avg Win) - (Loss% * Avg Loss)

        Args:
            pnls: List of trade P&Ls
            total_trades: Total number of trades

        Returns:
            Expectancy value
        """
        if not pnls or total_trades == 0:
            return 0.0

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        loss_rate = len(losses) / total_trades if total_trades > 0 else 0

        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0

        return (win_rate * avg_win) - (loss_rate * abs(avg_loss))

    def get_consecutive_stats(self) -> Dict[str, int]:
        """Calculate consecutive win/loss streaks.

        Returns:
            Dictionary with streak statistics
        """
        if not self.trades:
            return {"max_consecutive_wins": 0, "max_consecutive_losses": 0}

        closed_trades = [t for t in self.trades if t.status == "CLOSED"]
        if not closed_trades:
            return {"max_consecutive_wins": 0, "max_consecutive_losses": 0}

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in closed_trades:
            if trade.realized_pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return {
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
        }

    def calculate_position_sizing(
        self,
        account_balance: float,
        risk_percent: float = 1.0,
        premium: float = 2.50,
    ) -> int:
        """Calculate recommended position size using Kelly criterion variant.

        Args:
            account_balance: Current account balance
            risk_percent: Risk per trade as % of account
            premium: Option premium per contract

        Returns:
            Recommended number of contracts
        """
        risk_amount = account_balance * (risk_percent / 100.0)
        contracts = int(risk_amount / (premium * 100.0))
        return max(1, contracts)

    def export_trades_csv(self, filepath: Path) -> None:
        """Export all trades to CSV file.

        Args:
            filepath: Path to CSV file
        """
        import csv

        if not self.trades:
            logger.warning("No trades to export")
            return

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.trades[0]).keys())
            writer.writeheader()
            for trade in self.trades:
                writer.writerow(asdict(trade))

        logger.info(f"Trades exported to {filepath}")

    def export_trades_json(self, filepath: Path) -> None:
        """Export all trades to JSON file.

        Args:
            filepath: Path to JSON file
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "export_timestamp": datetime.now().isoformat(),
            "account_size": self.account_size,
            "trades": [asdict(t) for t in self.trades],
            "statistics": self.get_trade_statistics(),
            "streaks": self.get_consecutive_stats(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Trades exported to {filepath}")


class GreeksCalculator:
    """Calculates and tracks Greeks exposure for options portfolio."""

    @staticmethod
    def estimate_delta(
        option_type: str,
        strike: float,
        spot: float,
        dte: int,
        volatility: float = 0.25,
    ) -> float:
        """Estimate delta using simplified Black-Scholes approximation.

        Args:
            option_type: 'CALL' or 'PUT'
            strike: Strike price
            spot: Current spot price
            dte: Days to expiration
            volatility: Implied volatility (0.25 = 25%)

        Returns:
            Delta value (-1 to 1)
        """
        import math

        # Simplified calculation
        moneyness = spot / strike
        sqrtT = math.sqrt(dte / 365.0)
        d = math.log(moneyness) / (volatility * sqrtT) if sqrtT > 0 else 0

        if option_type == "CALL":
            delta = 0.5 + 0.5 * math.tanh(d)
        else:  # PUT
            delta = -0.5 + 0.5 * math.tanh(d)

        return delta

    @staticmethod
    def estimate_gamma(
        strike: float,
        spot: float,
        dte: int,
        volatility: float = 0.25,
    ) -> float:
        """Estimate gamma using simplified approximation.

        Args:
            strike: Strike price
            spot: Current spot price
            dte: Days to expiration
            volatility: Implied volatility

        Returns:
            Gamma value
        """
        import math

        sqrtT = math.sqrt(dte / 365.0)
        if sqrtT == 0:
            return 0.0

        # Simplified gamma calculation
        moneyness = spot / strike
        d = math.log(moneyness) / (volatility * sqrtT)
        gamma = math.exp(-d * d / 2) / (spot * volatility * sqrtT * math.sqrt(2 * math.pi))

        return max(0, gamma)

    @staticmethod
    def estimate_theta(
        option_type: str,
        strike: float,
        spot: float,
        dte: int,
        premium: float,
        volatility: float = 0.25,
    ) -> float:
        """Estimate theta (time decay) per day.

        Args:
            option_type: 'CALL' or 'PUT'
            strike: Strike price
            spot: Current spot price
            dte: Days to expiration
            premium: Current option premium
            volatility: Implied volatility

        Returns:
            Theta per day (time value decay)
        """
        if dte <= 0:
            return 0.0

        # Simplified: assume theta accelerates as expiration approaches
        days_factor = min(dte / 30.0, 1.0)
        base_theta = premium * (0.01 + days_factor * 0.05)

        return base_theta

    @staticmethod
    def calculate_portfolio_delta(positions: Dict[str, Dict]) -> float:
        """Calculate net delta for portfolio.

        Args:
            positions: Dict of positions with quantity and delta

        Returns:
            Net portfolio delta
        """
        net_delta = 0.0

        for symbol, pos in positions.items():
            if "delta" in pos:
                quantity = pos.get("quantity", 0)
                delta = pos.get("delta", 0.0)
                net_delta += quantity * delta * 100.0  # Contract multiplier

        return net_delta


class DailyPnLTracker:
    """Tracks daily P&L with detailed breakdown."""

    def __init__(self):
        """Initialize daily P&L tracker."""
        self.daily_records: List[Dict] = []
        self.current_date = datetime.now().date()

    def record_pnl(
        self,
        realized_pnl: float,
        unrealized_pnl: float,
        positions_count: int,
        notes: str = "",
    ) -> None:
        """Record daily P&L data.

        Args:
            realized_pnl: Realized profit/loss
            unrealized_pnl: Unrealized profit/loss
            positions_count: Number of open positions
            notes: Optional notes
        """
        record = {
            "date": self.current_date.isoformat(),
            "timestamp": datetime.now().isoformat(),
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": realized_pnl + unrealized_pnl,
            "positions_count": positions_count,
            "notes": notes,
        }

        self.daily_records.append(record)

    def get_daily_summary(self) -> Dict:
        """Get summary for current day.

        Returns:
            Dictionary with daily summary
        """
        today_records = [
            r for r in self.daily_records
            if r["date"] == self.current_date.isoformat()
        ]

        if not today_records:
            return {
                "date": self.current_date.isoformat(),
                "total_realized": 0.0,
                "total_unrealized": 0.0,
                "total_pnl": 0.0,
                "record_count": 0,
            }

        return {
            "date": self.current_date.isoformat(),
            "total_realized": sum(r["realized_pnl"] for r in today_records),
            "total_unrealized": sum(r["unrealized_pnl"] for r in today_records),
            "total_pnl": sum(r["total_pnl"] for r in today_records),
            "record_count": len(today_records),
        }

    def export_daily_pnl_csv(self, filepath: Path) -> None:
        """Export daily P&L to CSV.

        Args:
            filepath: Path to CSV file
        """
        import csv

        if not self.daily_records:
            logger.warning("No daily P&L records to export")
            return

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "date",
                    "timestamp",
                    "realized_pnl",
                    "unrealized_pnl",
                    "total_pnl",
                    "positions_count",
                    "notes",
                ],
            )
            writer.writeheader()
            for record in self.daily_records:
                writer.writerow(record)

        logger.info(f"Daily P&L exported to {filepath}")


def generate_performance_report(
    r_tracker: RMultipleTracker,
    daily_tracker: DailyPnLTracker,
) -> str:
    """Generate comprehensive performance report.

    Args:
        r_tracker: RMultipleTracker instance
        daily_tracker: DailyPnLTracker instance

    Returns:
        Formatted report string
    """
    stats = r_tracker.get_trade_statistics()
    streaks = r_tracker.get_consecutive_stats()
    daily = daily_tracker.get_daily_summary()

    report = f"""
{'='*70}
PERFORMANCE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

TRADE STATISTICS
{'-'*70}
Total Trades:                 {stats.get('total_trades', 0):>8.0f}
Winning Trades:               {stats.get('winning_trades', 0):>8.0f}
Losing Trades:                {stats.get('losing_trades', 0):>8.0f}
Win Rate:                     {stats.get('win_rate_percent', 0):>7.1f}%

PROFIT & LOSS
{'-'*70}
Total P&L:                    ${stats.get('total_pnl', 0):>12,.2f}
Average P&L per Trade:        ${stats.get('average_pnl', 0):>12,.2f}
Best Trade (Win):             ${stats.get('max_win', 0):>12,.2f}
Worst Trade (Loss):           ${stats.get('max_loss', 0):>12,.2f}
Average Win:                  ${stats.get('avg_win', 0):>12,.2f}
Average Loss:                 ${stats.get('avg_loss', 0):>12,.2f}

PERFORMANCE METRICS
{'-'*70}
Expectancy per Trade:         ${stats.get('expectancy', 0):>12,.2f}
Profit Factor:                {stats.get('profit_factor', 0):>14.2f}x
Average R-Multiple:           {stats.get('avg_r_multiple', 0):>14.2f}R
Max Consecutive Wins:         {streaks.get('max_consecutive_wins', 0):>14}
Max Consecutive Losses:       {streaks.get('max_consecutive_losses', 0):>14}

DAILY P&L
{'-'*70}
Date:                         {daily.get('date', 'N/A')}
Realized P&L:                 ${daily.get('total_realized', 0):>12,.2f}
Unrealized P&L:               ${daily.get('total_unrealized', 0):>12,.2f}
Total Daily P&L:              ${daily.get('total_pnl', 0):>12,.2f}
Records:                      {daily.get('record_count', 0):>14}

{'='*70}
"""

    return report


if __name__ == "__main__":
    # Test the reporter
    tracker = RMultipleTracker(account_size=100_000.0)

    # Add test trades
    trade1 = TradeRecord(
        order_id="ORD-001",
        symbol="SPY",
        option_type="CALL",
        strike_price=500.0,
        expiration_date="2025-12-19",
        quantity=2,
        entry_price=2.50,
        entry_time=datetime.now().isoformat(),
        exit_price=3.50,
        exit_time=datetime.now().isoformat(),
        realized_pnl=200.0,
        r_multiple=2.0,
        status="CLOSED",
    )

    trade2 = TradeRecord(
        order_id="ORD-002",
        symbol="QQQ",
        option_type="PUT",
        strike_price=380.0,
        expiration_date="2025-12-26",
        quantity=1,
        entry_price=1.75,
        entry_time=datetime.now().isoformat(),
        exit_price=1.25,
        exit_time=datetime.now().isoformat(),
        realized_pnl=-50.0,
        r_multiple=-1.0,
        status="CLOSED",
    )

    tracker.add_trade(trade1)
    tracker.add_trade(trade2)

    daily_tracker = DailyPnLTracker()
    daily_tracker.record_pnl(150.0, 100.0, 0)

    report = generate_performance_report(tracker, daily_tracker)
    print(report)

    print("\nTest completed successfully.")
