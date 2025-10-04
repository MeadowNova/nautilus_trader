#!/usr/bin/env python3
"""
Tutorial 1 - SIMPLE VERSION: Learn Nautilus Backtesting Basics

This simplified version uses built-in test data to avoid data format issues.
Perfect for learning the backtest workflow without CCXT complications.

Runtime: < 1 minute
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue, TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler
import pandas as pd

print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    NAUTILUS TRADER TUTORIAL 1: SIMPLE BACKTEST                  ║
║                     (Using Built-In Test Data)                   ║
║                                                                  ║
║  Learn:                                                          ║
║  • Backtest engine setup                                         ║
║  • Strategy configuration                                        ║
║  • Results analysis                                              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

# Step 1: Setup
print("="*70)
print("STEP 1: CONFIGURATION")
print("="*70)

# Create engine
config = BacktestEngineConfig(
    trader_id=TraderId("TUTORIAL-001"),
    logging=LoggingConfig(log_level="INFO"),
)
engine = BacktestEngine(config=config)
print("✅ Backtest engine created")

# Step 2: Add venue and instrument
print("\n" + "="*70)
print("STEP 2: VENUE & INSTRUMENT SETUP")
print("="*70)

BINANCE = Venue("BINANCE")
instrument = TestInstrumentProvider.ethusdt_binance()

engine.add_venue(
    venue=BINANCE,
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=None,
    starting_balances=[Money(100_000, USDT)],
)
print(f"✅ Venue: {BINANCE}")
print(f"✅ Starting Balance: $100,000 USDT")

engine.add_instrument(instrument)
print(f"✅ Instrument: {instrument.id}")

# Step 3: Load data
print("\n" + "="*70)
print("STEP 3: LOADING TEST DATA")
print("="*70)

provider = TestDataProvider()
bar_type_str = f"{instrument.id}-250-TICK-LAST-INTERNAL"
bar_type = BarType.from_str(bar_type_str)

# Use QuoteTick data and convert to bars
wrangler = QuoteTickDataWrangler(instrument=instrument)
ticks = wrangler.process_bar_data(
    bid_data=provider.read_csv_bars("btc-perp-20211231-20220201_1m.csv"),
    ask_data=provider.read_csv_bars("btc-perp-20211231-20220201_1m.csv"),
)

engine.add_data(ticks)
print(f"✅ Loaded {len(ticks)} ticks")
print(f"✅ Bar Type: {bar_type}")

# Step 4: Create strategy
print("\n" + "="*70)
print("STEP 4: STRATEGY CONFIGURATION")
print("="*70)

strategy_config = EMACrossConfig(
    instrument_id=instrument.id,
    bar_type=bar_type,
    fast_ema_period=10,
    slow_ema_period=20,
    trade_size=Decimal("0.10"),
)

strategy = EMACross(config=strategy_config)
engine.add_strategy(strategy)

print(f"✅ Strategy: EMA Cross")
print(f"   Fast EMA: 10 periods")
print(f"   Slow EMA: 20 periods")
print(f"   Trade Size: 0.1 ETH")

# Step 5: Run backtest
print("\n" + "="*70)
print("STEP 5: RUNNING BACKTEST")
print("="*70)

engine.run()

print("✅ Backtest complete!")

# Step 6: Analyze results
print("\n" + "="*70)
print("STEP 6: RESULTS ANALYSIS")
print("="*70)

# Get account
account = list(engine.cache.accounts())[0]

print("\n💰 Final Balances:")
for balance in account.balances().values():
    print(f"   {balance.currency}: {balance.total}")

# Get orders and positions
orders = engine.cache.orders()
positions = engine.cache.positions()

print(f"\n📊 Trading Statistics:")
print(f"   Total Orders: {len(orders)}")
print(f"   Total Positions: {len(positions)}")

# Analyze closed positions
closed_positions = [p for p in positions if p.is_closed]

if closed_positions:
    print(f"   Closed Positions: {len(closed_positions)}")
    
    profitable = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0]
    losing = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) < 0]
    
    total_pnl = sum(float(p.realized_pnl) for p in closed_positions if p.realized_pnl)
    
    print(f"   Winning Trades: {len(profitable)}")
    print(f"   Losing Trades: {len(losing)}")
    
    if len(closed_positions) > 0:
        win_rate = len(profitable) / len(closed_positions) * 100
        print(f"   Win Rate: {win_rate:.2f}%")
    
    print(f"   Total P&L: {total_pnl:.2f}")
else:
    print("\n⚠️  No closed positions")
    print("   This is normal for this test data - not enough bars for signals")

# Generate reports
print("\n" + "="*70)
print("DETAILED REPORTS")
print("="*70)

try:
    print("\n" + "-"*70)
    print("ACCOUNT REPORT")
    print("-"*70)
    print(engine.trader.generate_account_report(BINANCE))
except Exception as e:
    print(f"Could not generate account report: {e}")

try:
    print("\n" + "-"*70)
    print("FILLS REPORT")
    print("-"*70)
    print(engine.trader.generate_order_fills_report())
except Exception as e:
    print(f"Could not generate fills report: {e}")

# Cleanup
engine.dispose()

print("\n" + "="*70)
print("🎉 TUTORIAL COMPLETE!")
print("="*70)

print("\n📚 What You Learned:")
print("   ✅ How to create a backtest engine")
print("   ✅ How to configure venues and instruments")
print("   ✅ How to load data into the engine")
print("   ✅ How to create and add strategies")
print("   ✅ How to run a backtest")
print("   ✅ How to analyze results")

print("\n💡 Next Steps:")
print("   1. Modify the EMA periods (lines with fast_ema_period, slow_ema_period)")
print("   2. Change trade size")
print("   3. Try different instruments")
print("   4. Move to Tutorial 2 for advanced features")

print("\n📖 For CCXT data integration:")
print("   See: tutorial_01_simple_ema_backtest.py (work in progress)")

print("="*70)
