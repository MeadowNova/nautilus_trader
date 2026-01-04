# NautilusTrader Analytics & Reporting Guide

## Available Reports (engine.trader methods)

### 1. Account Report
```python
engine.trader.generate_account_report(VENUE)
```
Shows all account balance changes throughout the backtest with timestamps.

### 2. Orders Report  
```python
engine.trader.generate_orders_report()
```
Complete details of every order: type, side, quantity, fills, timestamps, execution prices.

### 3. Order Fills Report
```python
engine.trader.generate_order_fills_report()
```
Individual fill details including slippage, liquidity side (maker/taker), commissions.

### 4. Positions Report
```python
engine.trader.generate_positions_report()
```
**Most important for P&L analysis:**
- Entry/exit prices
- Position duration
- Realized P&L per position
- Commissions per position
- Win/loss classification

## Cache Access for Custom Analytics

### Get All Positions
```python
positions = engine.cache.positions()
closed_positions = [p for p in positions if p.is_closed]
open_positions = [p for p in positions if p.is_open]
```

### Get All Orders
```python
orders = engine.cache.orders()
filled_orders = [o for o in orders if o.is_filled]
```

### Get Account State
```python
account = engine.cache.account_for_venue(VENUE)
balances = account.balances()
```

## Custom Performance Metrics

### Win Rate
```python
winners = [p for p in closed_positions if p.realized_pnl.as_double() > 0]
losers = [p for p in closed_positions if p.realized_pnl.as_double() < 0]
win_rate = len(winners) / len(closed_positions) * 100
```

### Profit Factor
```python
gross_profit = sum(p.realized_pnl.as_double() for p in winners)
gross_loss = abs(sum(p.realized_pnl.as_double() for p in losers))
profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
```

### Average Win/Loss
```python
avg_win = sum(p.realized_pnl.as_double() for p in winners) / len(winners)
avg_loss = sum(p.realized_pnl.as_double() for p in losers) / len(losers)
```

### Total P&L
```python
total_pnl = sum(p.realized_pnl.as_double() for p in closed_positions)
```

### Maximum Drawdown (simplified)
```python
equity_curve = []
running_pnl = starting_balance
for position in sorted(closed_positions, key=lambda p: p.ts_closed):
    running_pnl += position.realized_pnl.as_double()
    equity_curve.append(running_pnl)

peak = equity_curve[0]
max_dd = 0
for equity in equity_curve:
    if equity > peak:
        peak = equity
    dd = (peak - equity) / peak
    max_dd = max(max_dd, dd)
```

### Sharpe Ratio (requires returns series)
```python
import numpy as np
returns = [p.realized_return for p in closed_positions]
sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # annualized
```

## Exporting Results

### Save to CSV
```python
from pathlib import Path
import pandas as pd

output_dir = Path("backtest_results")
output_dir.mkdir(exist_ok=True)

# Save positions
positions_df = engine.trader.generate_positions_report()
positions_df.to_csv(output_dir / "positions.csv")

# Save fills  
fills_df = engine.trader.generate_order_fills_report()
fills_df.to_csv(output_dir / "fills.csv")
```

### Save to Parquet (more efficient for large datasets)
```python
positions_df.to_parquet(output_dir / "positions.parquet")
```

## Visualization (Optional - requires matplotlib)

### Equity Curve
```python
import matplotlib.pyplot as plt

equity = []
timestamps = []
running_pnl = starting_balance

for pos in sorted(closed_positions, key=lambda p: p.ts_closed):
    running_pnl += pos.realized_pnl.as_double()
    equity.append(running_pnl)
    timestamps.append(pd.Timestamp(pos.ts_closed, unit='ns'))

plt.figure(figsize=(12, 6))
plt.plot(timestamps, equity)
plt.title('Equity Curve')
plt.xlabel('Time')
plt.ylabel('Account Value (USDT)')
plt.grid(True)
plt.savefig('equity_curve.png')
```

### P&L Distribution
```python
pnls = [p.realized_pnl.as_double() for p in closed_positions]

plt.figure(figsize=(10, 6))
plt.hist(pnls, bins=20, edgecolor='black')
plt.title('P&L Distribution')
plt.xlabel('P&L (USDT)')
plt.ylabel('Frequency')
plt.axvline(x=0, color='r', linestyle='--', label='Break-even')
plt.legend()
plt.savefig('pnl_distribution.png')
```

## Running the Enhanced Analysis

```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh
python examples/backtest/crypto_ema_cross_ethusdt_detailed_analysis.py
```

Results will be saved to `backtest_results/` directory with timestamps.

## Quick Analysis Script Template

```python
# Minimal backtest with analytics
engine.run()

# Get key metrics
positions = [p for p in engine.cache.positions() if p.is_closed]
total_pnl = sum(p.realized_pnl.as_double() for p in positions)
win_rate = len([p for p in positions if p.realized_pnl.as_double() > 0]) / len(positions) * 100

print(f"Total P&L: {total_pnl:.2f} USDT")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Total Trades: {len(positions)}")

# Save full reports
engine.trader.generate_positions_report().to_csv("results.csv")
```

## Next Steps

1. Run the detailed analysis script
2. Examine the CSV files in `backtest_results/`
3. Modify strategy parameters and compare results
4. Build custom analytics for your specific needs

For more advanced analytics, check out:
- [NautilusTrader Docs - Backtesting](https://nautilustrader.io/docs/latest/concepts/backtesting)
- [Performance Analysis Examples](https://nautilustrader.io/docs/latest/integrations/)
