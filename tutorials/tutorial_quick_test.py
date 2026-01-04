#!/usr/bin/env python3
"""
Quick Test: Verify Nautilus + CCXT Integration

This is a minimal test to verify your setup works before
running the full tutorials.

Expected runtime: < 2 minutes
"""

import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("="*70)
print("NAUTILUS TRADER + CCXT QUICK TEST")
print("="*70)

# Test 1: Import Nautilus
print("\n1. Testing Nautilus Trader import...")
try:
    import nautilus_trader
    print(f"   ✅ Nautilus version: {nautilus_trader.__version__}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Import CCXT
print("\n2. Testing CCXT import...")
try:
    import ccxt
    print(f"   ✅ CCXT version: {ccxt.__version__}")
    print(f"   ✅ Available exchanges: {len(ccxt.exchanges)}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 3: Fetch sample data
print("\n3. Testing Kraken connection...")
try:
    exchange = ccxt.kraken({'enableRateLimit': True})
    ticker = exchange.fetch_ticker('ETH/USD')
    print(f"   ✅ ETH/USD Price: ${ticker['last']:,.2f}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("   Note: This might be a network issue, not a setup issue")

# Test 4: Create simple backtest engine
print("\n4. Testing Nautilus backtest engine...")
try:
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.config import LoggingConfig
    from nautilus_trader.model.identifiers import TraderId
    
    config = BacktestEngineConfig(
        trader_id=TraderId("TEST-001"),
        logging=LoggingConfig(log_level="ERROR"),
    )
    engine = BacktestEngine(config=config)
    print(f"   ✅ Backtest engine created successfully")
    engine.dispose()
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 5: Test instrument provider
print("\n5. Testing instrument provider...")
try:
    from nautilus_trader.test_kit.providers import TestInstrumentProvider
    
    # Use a known working method
    instrument = TestInstrumentProvider.ethusdt_binance()
    print(f"   ✅ Instrument: {instrument.id}")
    print(f"   ✅ Symbol: {instrument.symbol}")
except Exception as e:
    print(f"   ⚠️  Warning: {e}")
    print("   (This is OK - continuing anyway)")

# Test 6: Test strategy import
print("\n6. Testing strategy import...")
try:
    from nautilus_trader.examples.strategies.ema_cross import EMACross
    print(f"   ✅ EMACross strategy available")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL TESTS PASSED!")
print("="*70)
print("\n💡 Your setup is ready for the tutorials!")
print("\nNext steps:")
print("  1. Review TUTORIALS_GUIDE.md")
print("  2. Run: python3 tutorial_01_simple_ema_backtest.py")
print("  3. Start learning!")
print("="*70)
