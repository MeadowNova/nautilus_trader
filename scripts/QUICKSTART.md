# Hybrid Options Trading - Quick Start

## 30-Second Start

```bash
cd /home/ajk/Nautilus/nautilus_trader

# 1. Test connection (1 minute)
python scripts/test_hybrid_connection.py

# 2. Start trading (if tests pass)
python scripts/hybrid_options_trading.py
```

## What It Does

- Polls yfinance every 30 seconds for SPY/AAPL/NVDA prices
- Calculates RSI and SMA indicators
- Generates signals:
  - RSI < 35 → SELL PUT (bullish)
  - RSI > 65 → BUY CALL (bearish)
- Submits REAL orders to Moomoo paper account
- You'll see activity on your Moomoo dashboard!

## Stop Trading

Press `Ctrl+C` in the terminal.

## See Activity

1. Watch console output for signals and orders
2. Check Moomoo app → Orders tab
3. Check Moomoo app → Positions tab

## Key Parameters (edit in script)

```python
# Line ~469-472 in hybrid_options_trading.py
symbols = ["SPY", "AAPL", "NVDA"]  # Add/remove symbols
poll_interval = 30                  # Seconds between updates

# Line ~473-476
rsi_oversold = 35                   # Lower = more conservative
rsi_overbought = 65                 # Higher = more conservative
max_positions = 3                   # Max concurrent positions
cooldown_minutes = 30               # Minutes between orders per symbol
```

## Requirements

- Moomoo OpenD running on localhost:11111
- Paper trading account active
- US Options LV1 access
- Internet connection (for yfinance)

## Troubleshooting

### "OpenD connection failed"
→ Start Moomoo OpenD (check desktop app)

### "No paper trading accounts found"
→ Enable paper trading in Moomoo settings

### "No options available"
→ Check market hours (9:30 AM - 4:00 PM ET)

### "Could not get SPY price"
→ Check internet connection

## Full Documentation

See `/home/ajk/Nautilus/nautilus_trader/docs/HYBRID_OPTIONS_TRADING.md` for complete details.
