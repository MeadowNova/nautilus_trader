#!/usr/bin/env python3
"""
Test placing a single option order using the OPTIONS paper trading account.
Account 1252648 is for options, Account 1252643 is for stocks.
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
print("TEST OPTION ORDER PLACEMENT (v2)")
print("=" * 70 + "\n")

# Connect to Moomoo OpenD
print("[1] Connecting to Moomoo OpenD...")
quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
trade_ctx = OpenSecTradeContext(
    host="127.0.0.1",
    port=11111,
    filter_trdmarket=TrdMarket.US
)

# Get paper trading accounts
ret, acc_list = trade_ctx.get_acc_list()
if ret != 0:
    print(f"FAILED: {acc_list}")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

print("Account list:")
print(acc_list[['acc_id', 'trd_env', 'acc_type', 'sim_acc_type', 'acc_status']])

# Find OPTIONS paper trading account
paper_accounts = acc_list[acc_list['trd_env'] == TrdEnv.SIMULATE]
option_accounts = paper_accounts[paper_accounts['sim_acc_type'] == 'OPTION']

if option_accounts.empty:
    print("FAILED: No OPTIONS paper trading account found")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

options_account_id = option_accounts.iloc[0]['acc_id']
print(f"\n  Using OPTIONS Account: {options_account_id}")

# Get SPY option chain
print("\n[2] Getting SPY option chain...")
ret, options = quote_ctx.get_option_chain(code="US.SPY")

if ret != 0:
    print(f"FAILED: {options}")
    quote_ctx.close()
    trade_ctx.close()
    exit(1)

print(f"  Found {len(options)} SPY options")

# Find a cheap call option
calls = options[options['option_type'] == 'CALL'].copy()
current_price = 684.65

if 'strike_price' in calls.columns:
    calls['atm_distance'] = abs(calls['strike_price'] - current_price)
    calls_sorted = calls.sort_values('atm_distance')

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
            ask_price = 7.5  # Default
            print(f"  Using default price: ${ask_price}")

        # Place order
        print(f"\n[5] Placing PAPER TRADING option order...")
        print(f"  Account: {options_account_id} (OPTIONS)")
        print(f"  Action: BUY")
        print(f"  Option: {option_code}")
        print(f"  Quantity: 1 contract")
        print(f"  Price: ${ask_price} (LIMIT)")

        print("\n" + "=" * 50)
        print("THIS IS A PAPER TRADE - NO REAL MONEY INVOLVED")
        print("=" * 50)

        ret, data = trade_ctx.place_order(
            price=ask_price,
            qty=1,
            code=option_code,
            trd_side=TrdSide.BUY,
            order_type=OrderType.NORMAL,
            trd_env=TrdEnv.SIMULATE,
            acc_id=options_account_id,
        )

        if ret == 0:
            order_id = data.iloc[0]['order_id'] if 'order_id' in data.columns else 'N/A'
            print(f"\n  OPTION ORDER PLACED SUCCESSFULLY!")
            print(f"  Order ID: {order_id}")
            print(f"\n  CHECK YOUR MOOMOO APP TO VERIFY THE ORDER!")
        else:
            print(f"\n  ORDER FAILED: {data}")

# Clean up
quote_ctx.close()
trade_ctx.close()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
