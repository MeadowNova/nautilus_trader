#!/usr/bin/env python3
"""
Simplified Backtest for AI-Adaptive Strategy

This is a simplified version that demonstrates the strategy without
requiring full NautilusTrader backtest infrastructure.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_synthetic_market_data(
    n_bars: int = 1000,
    initial_price: float = 2000.0,
    trend: float = 0.0001,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Generate synthetic market data for testing
    
    Args:
        n_bars: Number of bars to generate
        initial_price: Starting price
        trend: Trend component (drift)
        volatility: Volatility (standard deviation)
    
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(42)
    
    # Generate price series using geometric Brownian motion
    returns = np.random.normal(trend, volatility, n_bars)
    prices = initial_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCV
    data = []
    for i, close in enumerate(prices):
        high = close * (1 + abs(np.random.normal(0, volatility/2)))
        low = close * (1 - abs(np.random.normal(0, volatility/2)))
        open_price = prices[i-1] if i > 0 else initial_price
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': datetime.now() + timedelta(minutes=i),
            'open': open_price,
            'high': max(open_price, high, close),
            'low': min(open_price, low, close),
            'close': close,
            'volume': volume
        })
    
    return pd.DataFrame(data)


def simple_backtest():
    """Run a simple backtest simulation"""
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         AI-ADAPTIVE STRATEGY - SIMPLE BACKTEST                   ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Generate synthetic data
    print("📊 Generating synthetic market data...")
    df = generate_synthetic_market_data(n_bars=1000, trend=0.0002, volatility=0.015)
    print(f"   Generated {len(df)} bars")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Start: {df['timestamp'].iloc[0]}")
    print(f"   End: {df['timestamp'].iloc[-1]}")
    
    # Calculate indicators
    print("\n📈 Calculating indicators...")
    
    # EMA
    df['ema_fast'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_trend'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        )
    )
    df['atr'] = df['tr'].rolling(window=14).mean()
    
    print("   ✓ EMA (8, 21, 50)")
    print("   ✓ RSI (14)")
    print("   ✓ ATR (14)")
    
    # Simple trading logic
    print("\n🤖 Running trading simulation...")
    
    balance = 10000.0
    position = 0.0
    entry_price = 0.0
    trades = []
    
    for i in range(50, len(df)):  # Start after indicators warm up
        row = df.iloc[i]
        
        # Skip if indicators not ready
        if pd.isna(row['ema_fast']) or pd.isna(row['rsi']):
            continue
        
        # Entry logic
        if position == 0:
            # Bullish signal
            if (row['ema_fast'] > row['ema_slow'] and 
                row['close'] > row['ema_trend'] and
                row['rsi'] < 70):
                
                # Calculate position size (1% risk)
                risk_amount = balance * 0.01
                stop_distance = row['atr'] * 2
                position_size = risk_amount / stop_distance
                position_size = min(position_size, balance / row['close'])  # Can't buy more than balance
                
                if position_size > 0:
                    position = position_size
                    entry_price = row['close']
                    balance -= position * entry_price
                    
                    trades.append({
                        'type': 'BUY',
                        'timestamp': row['timestamp'],
                        'price': entry_price,
                        'quantity': position,
                        'balance': balance
                    })
        
        # Exit logic
        elif position > 0:
            exit_signal = False
            exit_reason = ""
            
            # Stop loss
            if row['close'] <= entry_price - (row['atr'] * 2):
                exit_signal = True
                exit_reason = "Stop Loss"
            
            # Take profit
            elif row['close'] >= entry_price + (row['atr'] * 3):
                exit_signal = True
                exit_reason = "Take Profit"
            
            # Technical reversal
            elif row['ema_fast'] < row['ema_slow']:
                exit_signal = True
                exit_reason = "EMA Crossover"
            
            if exit_signal:
                exit_price = row['close']
                pnl = (exit_price - entry_price) * position
                balance += position * exit_price
                
                trades.append({
                    'type': 'SELL',
                    'timestamp': row['timestamp'],
                    'price': exit_price,
                    'quantity': position,
                    'pnl': pnl,
                    'pnl_pct': (pnl / (entry_price * position)) * 100,
                    'reason': exit_reason,
                    'balance': balance
                })
                
                position = 0.0
                entry_price = 0.0
    
    # Close any remaining position
    if position > 0:
        exit_price = df.iloc[-1]['close']
        pnl = (exit_price - entry_price) * position
        balance += position * exit_price
        
        trades.append({
            'type': 'SELL',
            'timestamp': df.iloc[-1]['timestamp'],
            'price': exit_price,
            'quantity': position,
            'pnl': pnl,
            'pnl_pct': (pnl / (entry_price * position)) * 100,
            'reason': "End of Backtest",
            'balance': balance
        })
    
    # Calculate statistics
    print(f"\n{'='*70}")
    print("📊 BACKTEST RESULTS")
    print(f"{'='*70}")
    
    initial_balance = 10000.0
    final_balance = balance
    total_return = ((final_balance - initial_balance) / initial_balance) * 100
    
    # Count wins and losses
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    wins = [t for t in sell_trades if t.get('pnl', 0) > 0]
    losses = [t for t in sell_trades if t.get('pnl', 0) <= 0]
    
    win_rate = (len(wins) / len(sell_trades) * 100) if sell_trades else 0
    
    print(f"Initial Balance:  ${initial_balance:,.2f}")
    print(f"Final Balance:    ${final_balance:,.2f}")
    print(f"Total Return:     {total_return:+.2f}%")
    print(f"")
    print(f"Total Trades:     {len(sell_trades)}")
    print(f"Wins:             {len(wins)}")
    print(f"Losses:           {len(losses)}")
    print(f"Win Rate:         {win_rate:.2f}%")
    
    if wins:
        avg_win = np.mean([t['pnl'] for t in wins])
        print(f"Avg Win:          ${avg_win:.2f}")
    
    if losses:
        avg_loss = np.mean([t['pnl'] for t in losses])
        print(f"Avg Loss:         ${avg_loss:.2f}")
    
    if wins and losses:
        profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses))
        print(f"Profit Factor:    {profit_factor:.2f}")
    
    print(f"{'='*70}")
    
    # Show recent trades
    if sell_trades:
        print(f"\n📋 Last 5 Trades:")
        for trade in sell_trades[-5:]:
            pnl = trade.get('pnl', 0)
            pnl_pct = trade.get('pnl_pct', 0)
            reason = trade.get('reason', 'N/A')
            emoji = "✅" if pnl > 0 else "❌"
            print(f"   {emoji} {trade['timestamp'].strftime('%Y-%m-%d %H:%M')} | "
                  f"${trade['price']:.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%) | {reason}")
    
    # Save results
    output_dir = Path(__file__).parent.parent / "backtest_results" / "ai_adaptive"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    trades_df = pd.DataFrame(trades)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trades_file = output_dir / f"simple_backtest_trades_{timestamp}.csv"
    trades_df.to_csv(trades_file, index=False)
    
    print(f"\n💾 Results saved to: {trades_file}")
    print("\n✅ Backtest completed!")
    
    return {
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'total_return': total_return,
        'total_trades': len(sell_trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate,
        'trades': trades
    }


if __name__ == "__main__":
    results = simple_backtest()
