#!/usr/bin/env python3
"""
Test placing a single option order on Moomoo paper trading account.
This script will BUY 1 SPY call option.
"""

from datetime import datetime, timedelta
from moomoo import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdEnv,
    TrdMarket,
    TrdSide,
    OrderType,
)

print("=" * 70)
print("TEST OPTION ORDER PLACEMENT")
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

paper_accounts = acc_list[acc_list['trd_env'] == TrdEnv.SIMULATE]
if paper_accounts.empty:
    print("FAILED: No paper trading accounts found")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

account_id = paper_accounts.iloc[0]['acc_id']
print(f"  Paper Account: {account_id}")

# Get SPY option chain
print("\n[2] Getting SPY option chain...")
ret, options = quote_ctx.get_option_chain(code="US.SPY")

if ret != 0:
    print(f"FAILED: {options}")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

print(f"  Found {len(options)} SPY options")

# Find a cheap call option expiring soon
# Filter for CALL options, near the money, expiring within 30 days
current_price = 684.65  # SPY price from earlier

# Parse the option chain
calls = options[options['option_type'] == 'CALL'].copy()
print(f"  Found {len(calls)} call options")

# Find an option close to current price
if 'strike_price' in calls.columns:
    calls['atm_distance'] = abs(calls['strike_price'] - current_price)
    calls_sorted = calls.sort_values('atm_distance')

    # Get the nearest ATM call
    if not calls_sorted.empty:
        selected_option = calls_sorted.iloc[0]
        option_code = selected_option['code']
        strike = selected_option['strike_price']
        expiry = selected_option.get('expiry_date', 'N/A')

        print(f"\n[3] Selected option: {option_code}")
        print(f"  Strike: ${strike}")
        print(f"  Expiry: {expiry}")

        # Get option quote
        print(f"\n[4] Getting option quote...")
        ret, quote = quote_ctx.get_market_snapshot([option_code])
        if ret == 0 and not quote.empty:
            ask_price = quote.iloc[0].get('ask_price', 5.0)
            print(f"  Ask price: ${ask_price}")
        else:
            ask_price = 5.0  # Default price
            print(f"  Using default price: ${ask_price}")

        # Place order
        print(f"\n[5] Placing PAPER TRADING order...")
        print(f"  Action: BUY")
        print(f"  Quantity: 1 contract")
        print(f"  Price: ${ask_price} (LIMIT)")
        print(f"  Environment: PAPER TRADING")

        # Confirm
        print("\n" + "=" * 50)
        print("THIS IS A PAPER TRADE - NO REAL MONEY INVOLVED")
        print("=" * 50)

        ret, data = trade_ctx.place_order(
            price=ask_price,
            qty=1,
            code=option_code,
            trd_side=TrdSide.BUY,
            order_type=OrderType.NORMAL,
            trd_env=TrdEnv.SIMULATE,  # Paper trading
            acc_id=account_id,
        )

        if ret == 0:
            order_id = data.iloc[0]['order_id'] if 'order_id' in data.columns else 'N/A'
            print(f"\n  ORDER PLACED SUCCESSFULLY!")
            print(f"  Order ID: {order_id}")
            print(f"\n  CHECK YOUR MOOMOO APP TO VERIFY THE ORDER!")
        else:
            print(f"\n  ORDER FAILED: {data}")
    else:
        print("No call options found!")
else:
    print("Option chain format unexpected, columns:", list(options.columns))

# Clean up
quote_ctx.close()
trade_ctx.close()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
