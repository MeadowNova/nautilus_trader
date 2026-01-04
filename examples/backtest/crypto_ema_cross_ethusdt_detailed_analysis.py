#!/usr/bin/env python3
"""
Enhanced backtest example with comprehensive performance analytics.
Includes detailed reports, statistics, and performance metrics.
"""

import time
from decimal import Decimal
from pathlib import Path

import pandas as pd

from nautilus_trader.adapters.binance import BINANCE_VENUE
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm
from nautilus_trader.examples.strategies.ema_cross_twap import EMACrossTWAP
from nautilus_trader.examples.strategies.ema_cross_twap import EMACrossTWAPConfig
from nautilus_trader.model.currencies import ETH
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider
from nautilus_trader.test_kit.providers import TestInstrumentProvider


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 100)
    print(f" {title}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    # Configure backtest engine
    config = BacktestEngineConfig(
        trader_id=TraderId("BACKTESTER-001"),
        logging=LoggingConfig(
            log_level="ERROR",  # Set to ERROR to reduce output noise
            log_colors=True,
            use_pyo3=False,
        ),
    )

    # Build the backtest engine
    engine = BacktestEngine(config=config)

    # Add a trading venue
    engine.add_venue(
        venue=BINANCE_VENUE,
        oms_type=OmsType.NETTING,
        book_type=BookType.L1_MBP,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(1_000_000.0, USDT), Money(10.0, ETH)],
        trade_execution=True,
    )

    # Add instruments
    ETHUSDT_BINANCE = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(ETHUSDT_BINANCE)

    # Add data
    provider = TestDataProvider()
    wrangler = TradeTickDataWrangler(instrument=ETHUSDT_BINANCE)
    ticks = wrangler.process(provider.read_csv_ticks("binance/ethusdt-trades.csv"))
    engine.add_data(ticks)

    # Configure strategy
    strategy_config = EMACrossTWAPConfig(
        instrument_id=ETHUSDT_BINANCE.id,
        bar_type=BarType.from_str("ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL"),
        trade_size=Decimal("0.10"),
        fast_ema_period=10,
        slow_ema_period=20,
        twap_horizon_secs=10.0,
        twap_interval_secs=2.5,
    )

    # Instantiate and add strategy
    strategy = EMACrossTWAP(config=strategy_config)
    engine.add_strategy(strategy=strategy)

    # Instantiate and add execution algorithm
    exec_algorithm = TWAPExecAlgorithm()
    engine.add_exec_algorithm(exec_algorithm)

    # Run the backtest
    print_section("RUNNING BACKTEST")
    start_time = time.time()
    engine.run()
    elapsed = time.time() - start_time
    print(f"Backtest completed in {elapsed:.2f} seconds")

    # Set pandas display options for better output
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 300)
    pd.set_option('display.precision', 8)
    pd.set_option('display.float_format', lambda x: f'{x:.8f}')

    # ========== COMPREHENSIVE ANALYTICS ==========

    # 1. Account Report
    print_section("ACCOUNT REPORT")
    account_report = engine.trader.generate_account_report(BINANCE_VENUE)
    print(account_report)

    # 2. Orders Report
    print_section("ORDERS REPORT")
    orders_report = engine.trader.generate_orders_report()
    print(orders_report)

    # 3. Order Fills Report
    print_section("ORDER FILLS REPORT")
    fills_report = engine.trader.generate_order_fills_report()
    print(fills_report)

    # 4. Positions Report (most important for P&L)
    print_section("POSITIONS REPORT")
    positions_report = engine.trader.generate_positions_report()
    print(positions_report)

    # 5. Extract detailed statistics
    print_section("PERFORMANCE STATISTICS")
    
    # Get all positions
    positions = engine.cache.positions()
    if positions:
        total_positions = len(positions)
        closed_positions = [p for p in positions if p.is_closed]
        
        # Calculate win/loss statistics
        winning_trades = [p for p in closed_positions if p.realized_pnl.as_double() > 0]
        losing_trades = [p for p in closed_positions if p.realized_pnl.as_double() < 0]
        
        total_pnl = sum(p.realized_pnl.as_double() for p in closed_positions)
        total_wins = len(winning_trades)
        total_losses = len(losing_trades)
        
        win_rate = (total_wins / len(closed_positions) * 100) if closed_positions else 0
        
        avg_win = sum(p.realized_pnl.as_double() for p in winning_trades) / total_wins if winning_trades else 0
        avg_loss = sum(p.realized_pnl.as_double() for p in losing_trades) / total_losses if losing_trades else 0
        
        profit_factor = abs(sum(p.realized_pnl.as_double() for p in winning_trades) / 
                           sum(p.realized_pnl.as_double() for p in losing_trades)) if losing_trades and sum(p.realized_pnl.as_double() for p in losing_trades) != 0 else 0
        
        print(f"{'Total Positions:':<30} {total_positions}")
        print(f"{'Closed Positions:':<30} {len(closed_positions)}")
        print(f"{'Winning Trades:':<30} {total_wins}")
        print(f"{'Losing Trades:':<30} {total_losses}")
        print(f"{'Win Rate:':<30} {win_rate:.2f}%")
        print(f"{'Total P&L:':<30} {total_pnl:.8f} USDT")
        print(f"{'Average Win:':<30} {avg_win:.8f} USDT")
        print(f"{'Average Loss:':<30} {avg_loss:.8f} USDT")
        print(f"{'Profit Factor:':<30} {profit_factor:.4f}")
        
        if winning_trades:
            best_trade = max(winning_trades, key=lambda p: p.realized_pnl.as_double())
            print(f"{'Best Trade:':<30} {best_trade.realized_pnl.as_double():.8f} USDT")
        
        if losing_trades:
            worst_trade = min(losing_trades, key=lambda p: p.realized_pnl.as_double())
            print(f"{'Worst Trade:':<30} {worst_trade.realized_pnl.as_double():.8f} USDT")

    # 6. Trade durations
    print_section("TRADE DURATION ANALYSIS")
    if closed_positions:
        durations_seconds = [(p.ts_closed - p.ts_opened) / 1e9 for p in closed_positions]
        durations_minutes = [d / 60 for d in durations_seconds]
        
        print(f"{'Average Duration:':<30} {sum(durations_minutes) / len(durations_minutes):.2f} minutes")
        print(f"{'Min Duration:':<30} {min(durations_minutes):.2f} minutes")
        print(f"{'Max Duration:':<30} {max(durations_minutes):.2f} minutes")

    # 7. Commission Analysis
    print_section("COMMISSION ANALYSIS")
    total_commissions = sum(
        sum(c.as_double() for c in p.commissions()) 
        for p in closed_positions
    )
    print(f"{'Total Commissions Paid:':<30} {total_commissions:.8f} USDT")
    print(f"{'Avg Commission per Trade:':<30} {total_commissions / len(closed_positions):.8f} USDT" if closed_positions else "N/A")

    # 8. Account Summary
    print_section("ACCOUNT SUMMARY")
    account = engine.cache.account_for_venue(BINANCE_VENUE)
    if account:
        print(f"{'Account ID:':<30} {account.id}")
        print(f"\nFinal Balances:")
        # Get last state from account report
        acct_report = engine.trader.generate_account_report(BINANCE_VENUE)
        if isinstance(acct_report, pd.DataFrame) and not acct_report.empty:
            final_balances = acct_report[acct_report['reported'] == False].tail(10)
            if not final_balances.empty:
                for _, row in final_balances.iterrows():
                    print(f"  {row['currency']}: {row['total']} (Free: {row['free']}, Locked: {row['locked']})")
        else:
            print("  (Balance information not available)")

    # 9. Data Summary
    print_section("DATA SUMMARY")
    print(f"{'Total Ticks Processed:':<30} {len(ticks)}")
    print(f"{'Data Start Time:':<30} {ticks[0].ts_init}")
    print(f"{'Data End Time:':<30} {ticks[-1].ts_init}")

    # Optional: Save results to file
    print_section("SAVING RESULTS")
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    
    # Save positions report
    positions_df = positions_report
    if isinstance(positions_df, pd.DataFrame) and not positions_df.empty:
        positions_file = output_dir / f"positions_{timestamp}.csv"
        positions_df.to_csv(positions_file)
        print(f"Positions saved to: {positions_file}")
    
    # Save fills report
    fills_df = fills_report
    if isinstance(fills_df, pd.DataFrame) and not fills_df.empty:
        fills_file = output_dir / f"fills_{timestamp}.csv"
        fills_df.to_csv(fills_file)
        print(f"Order fills saved to: {fills_file}")

    print("\n" + "=" * 100)
    print(" ANALYSIS COMPLETE")
    print("=" * 100 + "\n")

    # Reset and dispose
    engine.reset()
    engine.dispose()
