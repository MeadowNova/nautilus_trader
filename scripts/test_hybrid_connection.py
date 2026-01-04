#!/usr/bin/env python3
"""
Quick connection test for hybrid trading setup.
Tests both yfinance data and Moomoo OpenD connectivity.
"""

import sys
from datetime import datetime

print("=" * 70)
print("HYBRID TRADING CONNECTION TEST")
print("=" * 70 + "\n")

# Test 1: yfinance data access
print("[Test 1] Testing yfinance data access...")
try:
    import yfinance as yf

    ticker = yf.Ticker("SPY")
    info = ticker.info
    price = info.get('currentPrice') or info.get('regularMarketPrice')

    if price:
        print(f"  SUCCESS: SPY price = ${price:.2f}")
    else:
        print("  WARNING: Could not get SPY price")

    # Test historical data
    hist = ticker.history(period="5d", interval="1h")
    if not hist.empty:
        print(f"  SUCCESS: Retrieved {len(hist)} historical bars")
        print(f"  Last close: ${hist['Close'].iloc[-1]:.2f}")
    else:
        print("  WARNING: No historical data")

except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

# Test 2: Moomoo OpenD connection
print("\n[Test 2] Testing Moomoo OpenD connection...")
try:
    from moomoo import (
        OpenQuoteContext,
        OpenSecTradeContext,
        TrdEnv,
        TrdMarket,
    )

    # Test quote context
    print("  Connecting to OpenD at localhost:11111...")
    quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

    ret, data = quote_ctx.get_global_state()
    if ret != 0:
        print(f"  FAILED: {data}")
        sys.exit(1)

    market_state = data.get('market_us', 'UNKNOWN')
    print(f"  SUCCESS: US Market state = {market_state}")

    # Test trade context (use SIMULATE for paper trading)
    trade_ctx = OpenSecTradeContext(
        host="127.0.0.1",
        port=11111,
        filter_trdmarket=TrdMarket.US
    )

    ret, acc_list = trade_ctx.get_acc_list()
    if ret != 0:
        print(f"  FAILED: {acc_list}")
        quote_ctx.close()
        trade_ctx.close()
        sys.exit(1)

    paper_accounts = acc_list[acc_list['trd_env'] == TrdEnv.SIMULATE]
    if paper_accounts.empty:
        print("  FAILED: No paper trading accounts found")
        quote_ctx.close()
        trade_ctx.close()
        sys.exit(1)

    account_id = paper_accounts.iloc[0]['acc_id']
    print(f"  SUCCESS: Paper account = {account_id}")

    # Test positions query
    ret, positions = trade_ctx.position_list_query(trd_env=TrdEnv.SIMULATE)
    if ret == 0:
        print(f"  SUCCESS: Current positions = {len(positions)}")
        if not positions.empty:
            print("\n  Current Positions:")
            print(positions[['code', 'qty', 'pl_val', 'pl_ratio']].to_string())
    else:
        print(f"  WARNING: Could not query positions: {positions}")

    quote_ctx.close()
    trade_ctx.close()

except ImportError:
    print("  FAILED: moomoo-api package not installed")
    print("  Install with: pip install moomoo-api")
    sys.exit(1)
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Options chain query
print("\n[Test 3] Testing options chain query...")
try:
    from moomoo import OpenQuoteContext

    quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

    # Test SPY options
    ret, options = quote_ctx.get_option_chain(code="US.SPY")

    if ret != 0:
        print(f"  FAILED: {options}")
        quote_ctx.close()
        sys.exit(1)

    if options.empty:
        print("  WARNING: No options available for SPY")
    else:
        print(f"  SUCCESS: Retrieved {len(options)} SPY options")

        # Show sample options
        sample = options.head(3)
        print("\n  Sample Options:")
        for _, opt in sample.iterrows():
            print(f"    {opt.get('code', 'N/A')}: strike={opt.get('strike_price', 0)}, expiry={opt.get('expiry_date', 'N/A')}")

    quote_ctx.close()

except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success!
print("\n" + "=" * 70)
print("ALL TESTS PASSED - READY FOR HYBRID TRADING")
print("=" * 70)
print("\nTo start trading, run:")
print("  python scripts/hybrid_options_trading.py")
print()
