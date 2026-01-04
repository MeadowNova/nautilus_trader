#!/usr/bin/env python3
"""
View API Paper Trading Positions
================================
Shows positions and orders from the Moomoo API paper trading accounts.
NOTE: These are SEPARATE from the Web/App paper trading you see in the Moomoo UI.

API Paper Trading Accounts:
- Account 1252643: STOCK paper trading (US market)
- Account 1252648: OPTION paper trading (US market)
"""

from moomoo import (
    OpenSecTradeContext,
    TrdEnv,
    TrdMarket,
)

print("=" * 70)
print("MOOMOO API PAPER TRADING DASHBOARD")
print("=" * 70)
print("\nNOTE: This shows API paper trading positions, NOT web/app positions!")
print("      Your NVDA/GME positions are in the WEB paper trading system.\n")

# Connect to Moomoo OpenD
trade_ctx = OpenSecTradeContext(
    host="127.0.0.1",
    port=11111,
    filter_trdmarket=TrdMarket.US
)

# Get all accounts
ret, acc_list = trade_ctx.get_acc_list()
if ret != 0:
    print(f"FAILED: {acc_list}")
    trade_ctx.close()
    exit(1)

# Show all accounts
print("[ALL ACCOUNTS]")
print(acc_list[['acc_id', 'trd_env', 'acc_type', 'sim_acc_type', 'acc_status']])

# Filter paper trading accounts
paper_accounts = acc_list[acc_list['trd_env'] == TrdEnv.SIMULATE]

print("\n" + "=" * 70)
print("PAPER TRADING ACCOUNTS DETAILS")
print("=" * 70)

for _, account in paper_accounts.iterrows():
    acc_id = account['acc_id']
    acc_type = account.get('sim_acc_type', 'STOCK')

    print(f"\n--- Account {acc_id} ({acc_type}) ---")

    # Get positions for this account
    ret, positions = trade_ctx.position_list_query(
        trd_env=TrdEnv.SIMULATE,
        acc_id=acc_id
    )

    if ret == 0 and not positions.empty:
        print(f"\nPositions ({len(positions)}):")
        cols = ['code', 'qty', 'cost_price', 'market_val', 'pl_val', 'pl_ratio']
        available_cols = [c for c in cols if c in positions.columns]
        print(positions[available_cols].to_string())
    else:
        print("\nNo positions")

    # Get orders for this account
    ret, orders = trade_ctx.order_list_query(
        trd_env=TrdEnv.SIMULATE,
        acc_id=acc_id
    )

    if ret == 0 and not orders.empty:
        print(f"\nOrders ({len(orders)}):")
        cols = ['order_id', 'code', 'trd_side', 'qty', 'price', 'order_status', 'create_time']
        available_cols = [c for c in cols if c in orders.columns]
        print(orders[available_cols].tail(10).to_string())
    else:
        print("\nNo orders")

    # Get account funds
    ret, funds = trade_ctx.accinfo_query(
        trd_env=TrdEnv.SIMULATE,
        acc_id=acc_id
    )

    if ret == 0 and not funds.empty:
        print(f"\nAccount Balance:")
        cols = ['total_assets', 'cash', 'market_val', 'available']
        available_cols = [c for c in cols if c in funds.columns]
        for col in available_cols:
            value = funds.iloc[0].get(col, 'N/A')
            if isinstance(value, (int, float)):
                print(f"  {col}: ${value:,.2f}")
            else:
                print(f"  {col}: {value}")

trade_ctx.close()

print("\n" + "=" * 70)
print("DASHBOARD COMPLETE")
print("=" * 70)
