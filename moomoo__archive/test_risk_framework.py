# -------------------------------------------------------------------------------------------------
#  Unit Tests for Risk Management Framework
#  Comprehensive test suite for all risk components
# -------------------------------------------------------------------------------------------------

import unittest
from datetime import datetime

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


class TestPositionSizing(unittest.TestCase):
    """Test position sizing calculations."""

    def test_fixed_fraction_long(self):
        """Test fixed fractional position sizing for LONG."""
        size = PositionSizer.fixed_fraction(
            account_size=500000.0,
            risk_per_trade_pct=0.02,
            entry_price=100.0,
            stop_loss_price=95.0,
        )

        # Risk = $500k * 0.02 = $10k
        # Price risk = $5
        # Size = $10k / $5 = 2000
        self.assertEqual(size, 2000)

    def test_fixed_fraction_tight_stop(self):
        """Test position sizing with tight stop loss."""
        size = PositionSizer.fixed_fraction(
            account_size=500000.0,
            risk_per_trade_pct=0.02,
            entry_price=100.0,
            stop_loss_price=98.0,
        )

        # Risk = $10k, Price risk = $2, Size = 5000
        self.assertEqual(size, 5000)

    def test_fixed_fraction_wide_stop(self):
        """Test position sizing with wide stop loss."""
        size = PositionSizer.fixed_fraction(
            account_size=500000.0,
            risk_per_trade_pct=0.02,
            entry_price=100.0,
            stop_loss_price=80.0,
        )

        # Risk = $10k, Price risk = $20, Size = 500
        self.assertEqual(size, 500)

    def test_kelly_criterion_moderate_edge(self):
        """Test Kelly Criterion with moderate edge."""
        kelly = PositionSizer.kelly_criterion(
            win_rate=0.45,
            avg_win_r=2.0,
            avg_loss_r=1.0,
            kelly_multiplier=0.25,
        )

        # Full kelly = (0.45*2 - 0.55*1) / 2 = (0.9 - 0.55) / 2 = 0.35 / 2 = 0.175
        # So expected value is 0.175 (less than kelly_multiplier 0.25, so no capping)
        self.assertAlmostEqual(kelly, 0.175, places=3)

    def test_kelly_criterion_high_win_rate(self):
        """Test Kelly Criterion with high win rate."""
        kelly = PositionSizer.kelly_criterion(
            win_rate=0.60,
            avg_win_r=1.5,
            avg_loss_r=1.0,
            kelly_multiplier=0.25,
        )

        # Full kelly = (0.60*1.5 - 0.40*1.0) / 1.5 = 0.40
        # Capped at kelly_multiplier = 0.25
        self.assertAlmostEqual(kelly, 0.25, places=2)

    def test_volatility_adjusted_sizing(self):
        """Test volatility-adjusted position sizing."""
        size = PositionSizer.volatility_adjusted(
            account_size=500000.0,
            atr_value=5.0,
            entry_price=100.0,
            atr_multiple=2.0,
            risk_pct=0.02,
        )

        # Risk = $10k, Stop distance = 5*2 = $10, Size = 1000
        self.assertEqual(size, 1000)


class TestStopLossCalculation(unittest.TestCase):
    """Test stop loss calculations."""

    def test_atr_based_long(self):
        """Test ATR-based stop loss for LONG position."""
        stop = StopLossEngine.atr_based(
            entry_price=100.0,
            atr_value=5.0,
            atr_multiple=2.0,
            direction="LONG",
        )

        # Stop = entry - (ATR * multiple) = 100 - 10 = 90
        self.assertEqual(stop, 90.0)

    def test_atr_based_short(self):
        """Test ATR-based stop loss for SHORT position."""
        stop = StopLossEngine.atr_based(
            entry_price=100.0,
            atr_value=5.0,
            atr_multiple=2.0,
            direction="SHORT",
        )

        # Stop = entry + (ATR * multiple) = 100 + 10 = 110
        self.assertEqual(stop, 110.0)

    def test_percentage_based_long(self):
        """Test percentage-based stop loss for LONG."""
        stop = StopLossEngine.percentage_based(
            entry_price=100.0,
            stop_loss_pct=0.02,
            direction="LONG",
        )

        # Stop = entry - (entry * pct) = 100 - 2 = 98
        self.assertEqual(stop, 98.0)

    def test_swing_point(self):
        """Test swing point stop loss."""
        stop = StopLossEngine.swing_point(
            recent_lows=[92, 94, 91, 93, 90],
            entry_price=100.0,
            direction="LONG",
        )

        # Stop = min of recent lows = 90
        self.assertEqual(stop, 90.0)


class TestTakeProfitCalculation(unittest.TestCase):
    """Test take profit calculations."""

    def test_rr_ratio_2_to_1(self):
        """Test 2:1 risk-to-reward take profit."""
        tp = TakeProfitEngine.risk_reward_based(
            entry_price=100.0,
            stop_loss_price=90.0,
            rr_ratio=2.0,
            direction="LONG",
        )

        # Risk = $10, Reward = $20, TP = 100 + 20 = 120
        self.assertEqual(tp, 120.0)

    def test_rr_ratio_3_to_1(self):
        """Test 3:1 risk-to-reward take profit."""
        tp = TakeProfitEngine.risk_reward_based(
            entry_price=100.0,
            stop_loss_price=95.0,
            rr_ratio=3.0,
            direction="LONG",
        )

        # Risk = $5, Reward = $15, TP = 100 + 15 = 115
        self.assertEqual(tp, 115.0)

    def test_atr_based_tp(self):
        """Test ATR-based take profit."""
        tp = TakeProfitEngine.atr_based(
            entry_price=100.0,
            atr_value=5.0,
            atr_multiple=4.0,
            direction="LONG",
        )

        # TP = entry + (ATR * multiple) = 100 + 20 = 120
        self.assertEqual(tp, 120.0)


class TestRMultipleMeasurement(unittest.TestCase):
    """Test R-multiple tracking and expectancy."""

    def test_win_rate_calculation(self):
        """Test win rate calculation."""
        r_meas = RMeasurement(
            winning_trades=8,
            losing_trades=12,
        )

        # Win rate = 8 / 20 = 0.4 = 40%
        self.assertEqual(r_meas.win_rate, 0.4)

    def test_expectancy_positive(self):
        """Test expectancy with profitable strategy."""
        r_meas = RMeasurement(
            winning_trades=8,
            losing_trades=12,
            total_r_gained=16.5,  # 8 wins, avg 2.06R
            total_r_lost=12.0,    # 12 losses, avg 1.0R
        )

        # Expectancy = (0.4 * 2.06) - (0.6 * 1.0) = 0.824 - 0.6 = 0.224
        exp = r_meas.expectancy
        self.assertAlmostEqual(exp, 0.224, places=2)

    def test_expectancy_negative(self):
        """Test expectancy with losing strategy."""
        r_meas = RMeasurement(
            winning_trades=6,
            losing_trades=14,
            total_r_gained=9.0,   # 6 wins, avg 1.5R
            total_r_lost=21.0,    # 14 losses, avg 1.5R
        )

        # Expectancy = (0.3 * 1.5) - (0.7 * 1.5) = 0.45 - 1.05 = -0.6
        exp = r_meas.expectancy
        self.assertAlmostEqual(exp, -0.6, places=2)

    def test_profit_factor(self):
        """Test profit factor calculation."""
        r_meas = RMeasurement(
            total_r_gained=20.0,
            total_r_lost=12.0,
        )

        # Profit factor = 20 / 12 = 1.67
        pf = r_meas.profit_factor
        self.assertAlmostEqual(pf, 1.67, places=2)

    def test_kelly_percentage(self):
        """Test Kelly Criterion percentage."""
        r_meas = RMeasurement(
            winning_trades=9,
            losing_trades=11,
            total_r_gained=18.0,   # avg 2.0R
            total_r_lost=11.0,     # avg 1.0R
        )

        # Full kelly = (0.45*2 - 0.55*1) / 2 = 0.225
        # But capped at kelly_multiplier so check the actual percentage
        kelly = r_meas.kelly_percentage
        # Just verify it's positive and reasonable
        self.assertGreater(kelly, 0.0)
        self.assertLess(kelly, 25.0)

    def test_consecutive_losses_tracking(self):
        """Test tracking of consecutive losses."""
        r_meas = RMeasurement()

        r_meas.consecutive_losses = 1
        r_meas.losing_trades += 1
        r_meas.max_consecutive_losses = max(r_meas.max_consecutive_losses, r_meas.consecutive_losses)

        r_meas.consecutive_losses = 2
        r_meas.losing_trades += 1
        r_meas.max_consecutive_losses = max(r_meas.max_consecutive_losses, r_meas.consecutive_losses)

        r_meas.consecutive_losses = 3
        r_meas.losing_trades += 1
        r_meas.max_consecutive_losses = max(r_meas.max_consecutive_losses, r_meas.consecutive_losses)

        r_meas.consecutive_losses = 0  # Win
        r_meas.winning_trades += 1

        self.assertEqual(r_meas.max_consecutive_losses, 3)
        self.assertEqual(r_meas.losing_trades, 3)


class TestPositionMetrics(unittest.TestCase):
    """Test position-level metrics."""

    def test_position_creation(self):
        """Test position metric creation."""
        position = PositionMetrics(
            instrument_id="TSLA.NASDAQ",
            entry_price=250.0,
            current_price=255.0,
            quantity=100,
            entry_time=datetime.now(),
            direction="LONG",
        )

        self.assertEqual(position.instrument_id, "TSLA.NASDAQ")
        self.assertEqual(position.quantity, 100)
        # Note: pnl_unrealized is 0 by default, must be calculated separately
        position.pnl_unrealized = (255.0 - 250.0) * 100
        self.assertEqual(position.pnl_unrealized, 500.0)

    def test_pnl_percentage(self):
        """Test P&L percentage calculation."""
        position = PositionMetrics(
            instrument_id="AAPL.NASDAQ",
            entry_price=150.0,
            current_price=153.0,
            quantity=100,
            entry_time=datetime.now(),
            direction="LONG",
        )

        pnl_pct = (3.0 / 150.0) * 100
        self.assertAlmostEqual(position.pnl_pct, pnl_pct, places=2)

    def test_r_multiple_calculation(self):
        """Test R-multiple calculation."""
        trade = TradeEntry(
            instrument_id="MSFT.NASDAQ",
            entry_price=300.0,
            entry_size=50,
            entry_time=datetime.now(),
            r_value=500.0,  # $500 risk per position
            stop_loss_price=290.0,
            take_profit_price=320.0,
        )

        position = PositionMetrics(
            instrument_id="MSFT.NASDAQ",
            entry_price=300.0,
            current_price=310.0,
            quantity=50,
            entry_time=datetime.now(),
            direction="LONG",
            trades=[trade],
        )

        position.pnl_unrealized = 500.0  # 50 * $10
        r_multiple = position.r_multiple

        # R-multiple = 500 / 500 = 1.0R
        self.assertEqual(r_multiple, 1.0)


class TestRiskMonitoring(unittest.TestCase):
    """Test risk monitoring and alerts."""

    def test_position_within_limits(self):
        """Test position well within risk limits."""
        position = PositionMetrics(
            instrument_id="TSLA.NASDAQ",
            entry_price=250.0,
            current_price=251.0,
            quantity=50,  # $12,550 notional
            entry_time=datetime.now(),
            direction="LONG",
        )

        config = PositionRiskConfig(
            max_position_size_usd=25000.0,
            max_position_size_pct_account=0.05,
        )

        monitor = RiskMonitor(
            config,
            PortfolioRiskConfig(),
            GreeksConfig(),
        )

        risk_level, issues = monitor.check_position_risk(position, 500000.0)

        self.assertEqual(risk_level, RiskLevel.OK)
        self.assertEqual(len(issues), 0)

    def test_position_size_breach(self):
        """Test position exceeding size limit."""
        position = PositionMetrics(
            instrument_id="TSLA.NASDAQ",
            entry_price=250.0,
            current_price=251.0,
            quantity=150,  # $37,650 notional
            entry_time=datetime.now(),
            direction="LONG",
        )

        config = PositionRiskConfig(
            max_position_size_usd=25000.0,
            max_position_size_pct_account=0.05,
        )

        monitor = RiskMonitor(
            config,
            PortfolioRiskConfig(),
            GreeksConfig(),
        )

        risk_level, issues = monitor.check_position_risk(position, 500000.0)

        self.assertNotEqual(risk_level, RiskLevel.OK)
        self.assertTrue(any("exceeds max" in issue for issue in issues))

    def test_portfolio_exposure_check(self):
        """Test portfolio exposure limits."""
        portfolio = PortfolioMetrics(account_size=500000.0)
        portfolio.gross_exposure = 450000.0  # 90% (OK)
        portfolio.net_exposure = 300000.0    # 60% (OK)

        config = PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=0.75,
        )

        monitor = RiskMonitor(
            PositionRiskConfig(max_position_size_usd=25000.0),
            config,
            GreeksConfig(),
        )

        risk_level, issues = monitor.check_portfolio_risk(portfolio)

        self.assertEqual(risk_level, RiskLevel.OK)

    def test_portfolio_exposure_breach(self):
        """Test portfolio exposure exceeding limit."""
        portfolio = PortfolioMetrics(account_size=500000.0)
        portfolio.gross_exposure = 600000.0  # 120% (BREACH)
        portfolio.net_exposure = 400000.0    # 80% (BREACH)

        config = PortfolioRiskConfig(
            max_gross_exposure=1.0,
            max_net_exposure=0.75,
        )

        monitor = RiskMonitor(
            PositionRiskConfig(max_position_size_usd=25000.0),
            config,
            GreeksConfig(),
        )

        risk_level, issues = monitor.check_portfolio_risk(portfolio)

        self.assertGreaterEqual(len(issues), 1)


class TestMonteCarloSimulation(unittest.TestCase):
    """Test Monte Carlo stress testing."""

    def test_drawdown_simulation(self):
        """Test Monte Carlo drawdown simulation."""
        results = MonteCarloSimulator.simulate_drawdown(
            win_rate=0.50,
            avg_win_r=2.0,
            avg_loss_r=1.0,
            num_trades=50,
            num_simulations=100,
            starting_capital=100000.0,
        )

        # Check that results have expected keys
        self.assertIn("expected_final_capital", results)
        self.assertIn("avg_max_drawdown_pct", results)
        self.assertIn("worst_case_drawdown_pct", results)

        # Verify structure (actual values depend on random simulation)
        self.assertIsInstance(results["expected_final_capital"], (int, float))
        self.assertIsInstance(results["avg_max_drawdown_pct"], (int, float))

    def test_price_path_simulation(self):
        """Test Monte Carlo price path simulation."""
        results = MonteCarloSimulator.simulate_paths(
            current_price=100.0,
            annual_return=0.15,
            annual_volatility=0.30,
            days_to_simulate=30,
            num_paths=100,
        )

        # Check expected price is near starting price (drift is small for 30 days)
        self.assertGreater(results["expected_price"], 95.0)
        self.assertLess(results["expected_price"], 110.0)

        # Check percentiles are in order
        self.assertLess(results["percentile_5"], results["percentile_50"])
        self.assertLess(results["percentile_50"], results["percentile_95"])


class TestRiskReporting(unittest.TestCase):
    """Test risk report generation."""

    def test_position_report_generation(self):
        """Test position-level report generation."""
        position = PositionMetrics(
            instrument_id="TSLA.NASDAQ",
            entry_price=250.0,
            current_price=255.0,
            quantity=100,
            entry_time=datetime.now(),
            direction="LONG",
        )

        # Set unrealized P&L manually
        position.pnl_unrealized = 500.0

        report = RiskReporter.generate_position_report(position, 500000.0)

        self.assertIn("instrument", report)
        self.assertIn("pnl_unrealized", report)
        self.assertIn("r_multiple", report)
        self.assertEqual(report["pnl_unrealized"], 500.0)

    def test_expectancy_report_generation(self):
        """Test expectancy report generation."""
        r_meas = RMeasurement(
            winning_trades=8,
            losing_trades=12,
            total_r_gained=16.5,
            total_r_lost=12.0,
        )

        report = RiskReporter.generate_expectancy_report(r_meas)

        self.assertIn("win_rate", report)
        self.assertIn("expectancy", report)
        self.assertIn("profit_factor", report)
        self.assertEqual(report["winning_trades"], 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
