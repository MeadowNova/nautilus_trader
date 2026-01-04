# Moomoo Paper Trading Account Discovery

## Date: 2025-12-09

## Key Finding: Two Separate Paper Trading Systems

Moomoo has **TWO SEPARATE** paper trading environments that do NOT share data:

### 1. Web/App Paper Trading (Manual)
- Visible in Moomoo mobile app and web interface
- User's existing positions: NVDA (50 shares), GME (530 shares)
- This is for manual paper trading through the app UI
- NOT accessible via OpenD API

### 2. API Paper Trading (via OpenD)
- Accessible only through OpenD API
- Separate accounts with separate balances
- Used for algorithmic trading

## API Paper Trading Accounts (User ID: 73774895)

### Account 1252643 - US STOCKS
- Type: MARGIN, sim_acc_type: STOCK
- Market: US
- Starting Balance: ~$1,000,000
- Current Positions:
  - 2 shares SPY @ $684.61 = $1,368.40
- Total Assets: $999,995.20

### Account 1252648 - US OPTIONS
- Type: MARGIN, sim_acc_type: OPTION
- Market: US
- Starting Balance: ~$1,000,000
- Current Positions:
  - 1 SPY Call option (US.SPY251223C685000) @ $7.20 = $664.00
- Total Assets: $999,941.68

### Account 1252642 - HK STOCKS
- Type: CASH, sim_acc_type: STOCK
- Market: HK
- No positions

## Critical Implementation Details

### Using Correct Account for Security Type
```python
# For STOCKS - use account 1252643
trade_ctx.place_order(
    code="US.SPY",
    acc_id=1252643,  # STOCK account
    trd_env=TrdEnv.SIMULATE,
    ...
)

# For OPTIONS - use account 1252648
trade_ctx.place_order(
    code="US.SPY251223C685000",
    acc_id=1252648,  # OPTION account
    trd_env=TrdEnv.SIMULATE,
    ...
)
```

### Error: "This acc_id does not support this type of security"
- Occurs when placing option orders on stock account (1252643)
- Solution: Use account 1252648 for options

### Successful Orders Placed
| Order ID | Account | Type | Symbol | Side | Qty | Price | Status |
|----------|---------|------|--------|------|-----|-------|--------|
| 528807 | 1252643 | Stock | US.SPY | BUY | 1 | $685.00 | FILLED |
| 528868 | 1252643 | Stock | US.SPY | BUY | 1 | $684.21 | FILLED |
| 528811 | 1252648 | Option | US.SPY251223C685000 | BUY | 1 | $7.20 | FILLED |

## Code to Check API Paper Trading Status

```python
from moomoo import OpenSecTradeContext, TrdEnv, TrdMarket

trade_ctx = OpenSecTradeContext(
    host='127.0.0.1', 
    port=11111, 
    filter_trdmarket=TrdMarket.US
)

# Get accounts
ret, acc_list = trade_ctx.get_acc_list()
print(acc_list[['acc_id', 'sim_acc_type', 'trdmarket_auth']])

# Check positions for stock account
ret, positions = trade_ctx.position_list_query(
    trd_env=TrdEnv.SIMULATE, 
    acc_id=1252643
)

# Check positions for options account
ret, positions = trade_ctx.position_list_query(
    trd_env=TrdEnv.SIMULATE, 
    acc_id=1252648
)

trade_ctx.close()
```

## User's Quote Rights (from OpenD)
- US Securities: **No Authority** (blocked - cannot subscribe to market data)
- US Options: **LV1** (available)
- HK Securities: **LV1** (available)
- HK Options: **LV1** (available)

## Hybrid Architecture Solution
Due to US Securities data being blocked:
1. Use **yfinance** for US stock price data (free, no subscription needed)
2. Use **Moomoo OpenD** for order execution only
3. Strategy: RSI-based options trading on SPY, AAPL, NVDA

## Scripts Created
- `scripts/test_hybrid_connection.py` - Tests yfinance + Moomoo connectivity
- `scripts/hybrid_options_trading.py` - Main trading bot (needs account fix for options)
- `scripts/test_place_stock_order.py` - Tests stock order placement
- `scripts/test_place_option_order_v2.py` - Tests option order placement with correct account
