#!/usr/bin/env python3
"""
Test placing a single stock order on Moomoo paper trading account.
This script will BUY 1 share of SPY.
"""

from moomoo import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdEnv,
    TrdMarket,
    TrdSide,
    OrderType,
)

print("=" * 70)
print("TEST STOCK ORDER PLACEMENT")
print("=" * 70 + "\n")

# Connect to Moomoo OpenD
print("[1] Connecting to Moomoo OpenD...")
quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
trade_ctx = OpenSecTradeContext(
    host="127.0.0.1",
    port=11111,
    filter_trdmarket=TrdMarket.US
)

# Get paper trading account
ret, acc_list = trade_ctx.get_acc_list()
if ret != 0:
    print(f"FAILED: {acc_list}")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

print("Account list:")
print(acc_list)

paper_accounts = acc_list[acc_list['trd_env'] == TrdEnv.SIMULATE]
if paper_accounts.empty:
    print("FAILED: No paper trading accounts found")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

account_id = paper_accounts.iloc[0]['acc_id']
print(f"\n  Using Paper Account: {account_id}")

# Get SPY quote
print("\n[2] Getting SPY quote...")
ret, quote = quote_ctx.get_market_snapshot(["US.SPY"])
if ret == 0 and not quote.empty:
    ask_price = quote.iloc[0].get('ask_price', 685.0)
    print(f"  SPY ask price: ${ask_price}")
else:
    ask_price = 685.0  # Default
    print(f"  Using default price: ${ask_price}")

# Place order
print(f"\n[3] Placing PAPER TRADING order...")
print(f"  Action: BUY")
print(f"  Symbol: US.SPY")
print(f"  Quantity: 1 share")
print(f"  Price: ${ask_price} (LIMIT)")
print(f"  Environment: PAPER TRADING")

print("\n" + "=" * 50)
print("THIS IS A PAPER TRADE - NO REAL MONEY INVOLVED")
print("=" * 50)

ret, data = trade_ctx.place_order(
    price=ask_price,
    qty=1,
    code="US.SPY",
    trd_side=TrdSide.BUY,
    order_type=OrderType.NORMAL,
    trd_env=TrdEnv.SIMULATE,
    acc_id=account_id,
)

if ret == 0:
    order_id = data.iloc[0]['order_id'] if 'order_id' in data.columns else 'N/A'
    print(f"\n  ORDER PLACED SUCCESSFULLY!")
    print(f"  Order ID: {order_id}")
    print(f"\n  CHECK YOUR MOOMOO APP TO VERIFY THE ORDER!")
else:
    print(f"\n  ORDER FAILED: {data}")

# Also try to get order history
print("\n[4] Getting order history...")
ret, order_history = trade_ctx.order_list_query(trd_env=TrdEnv.SIMULATE)
if ret == 0 and not order_history.empty:
    print(f"  Found {len(order_history)} orders:")
    print(order_history[['order_id', 'code', 'trd_side', 'qty', 'price', 'order_status']].tail(5))
else:
    print(f"  No orders found or error: {order_history}")

# Clean up
quote_ctx.close()
trade_ctx.close()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
