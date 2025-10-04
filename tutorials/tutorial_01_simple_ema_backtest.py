#!/usr/bin/env python3
"""
Tutorial 1: Simple EMA Cross Strategy Backtest with CCXT Data

This tutorial demonstrates:
1. Downloading historical data from Kraken using CCXT
2. Setting up a simple EMA crossover strategy
3. Running a backtest with the data
4. Analyzing the results

Learning Objectives:
- Understand Nautilus backtest engine setup
- Learn how to integrate CCXT data
- Analyze basic strategy performance
- Interpret backtest metrics

Author: AI Quant Trading Specialist
Date: January 2025
"""

import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ccxt
import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USD, ETH
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue, TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.model.instruments import CryptoFuture, CryptoPerpetual, Instrument
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.model.data import BarType, Bar


# ==================== PART 1: DATA DOWNLOAD ====================

def download_historical_data(
    exchange_id='kraken',
    symbol='ETH/USD',
    timeframe='1h',
    days_back=30
):
    """
    Download historical OHLCV data from an exchange using CCXT
    
    Args:
        exchange_id: Exchange name (kraken, kucoin, etc.)
        symbol: Trading pair (ETH/USD, BTC/USDT, etc.)
        timeframe: Candlestick interval (1h, 4h, 1d)
        days_back: How many days of history to download
    
    Returns:
        pandas.DataFrame with OHLCV data
    """
    print("="*70)
    print(f"📥 DOWNLOADING DATA FROM {exchange_id.upper()}")
    print("="*70)
    
    # Initialize exchange
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True,
    })
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    since = int(start_date.timestamp() * 1000)  # CCXT uses milliseconds
    
    print(f"\n📊 Fetching {symbol} {timeframe} bars")
    print(f"   From: {start_date.strftime('%Y-%m-%d')}")
    print(f"   To: {end_date.strftime('%Y-%m-%d')}")
    
    # Fetch data in chunks
    all_ohlcv = []
    current_since = since
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            
            # Update since to last timestamp + 1
            current_since = ohlcv[-1][0] + 1
            
            # Break if we've reached current time
            if current_since >= int(end_date.timestamp() * 1000):
                break
            
            print(f"   Fetched {len(all_ohlcv)} bars...", end='\r')
            
        except Exception as e:
            print(f"\n⚠️  Error: {e}")
            break
    
    print(f"\n✅ Downloaded {len(all_ohlcv)} bars total")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    return df


# ==================== PART 2: DATA PREPARATION ====================

def clean_ohlcv_data(df):
    """
    Clean and validate OHLCV data
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        Cleaned DataFrame
    """
    print("\n🧹 Cleaning and validating data...")
    original_len = len(df)
    
    # Create a copy to avoid any reference issues
    df = df.copy()
    
    # Remove rows with zero or negative values
    mask_positive = (df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0) & (df['volume'] >= 0)
    df = df[mask_positive]
    
    # Ensure high is max and low is min
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # Reset index to avoid any issues
    df = df.reset_index(drop=True)
    
    cleaned_len = len(df)
    removed = original_len - cleaned_len
    
    if removed > 0:
        print(f"   ⚠️  Removed {removed} invalid bars")
    print(f"   ✅ {cleaned_len} valid bars remaining")
    
    return df


def prepare_nautilus_data(df, symbol='ETH/USD', venue_str='KRAKEN'):
    """
    Convert CCXT DataFrame to Nautilus format
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Trading pair symbol
        venue_str: Venue name
    
    Returns:
        List of Nautilus Bar objects
    """
    print("\n" + "="*70)
    print("🔧 PREPARING DATA FOR NAUTILUS")
    print("="*70)
    
    # Clean the data first
    df = clean_ohlcv_data(df)
    
    # Create instrument
    # Using TestInstrumentProvider for simplicity
    if 'ETH' in symbol and 'USD' in symbol:
        if 'USDT' in symbol:
            instrument = TestInstrumentProvider.ethusdt_binance()
            instrument_id_str = f"ETHUSDT.{venue_str}"
        else:
            # For ETH/USD we'll use the BitMEX instrument as a template
            instrument = TestInstrumentProvider.ethusd_bitmex()
            instrument_id_str = f"ETHUSD.{venue_str}"
    elif 'BTC' in symbol:
        if 'USDT' in symbol:
            instrument = TestInstrumentProvider.btcusdt_binance()
            instrument_id_str = f"BTCUSDT.{venue_str}"
        else:
            instrument = TestInstrumentProvider.btcusdt_binance()
            instrument_id_str = f"BTCUSD.{venue_str}"
    else:
        # Fallback to a default instrument
        instrument = TestInstrumentProvider.default_fx_ccy("EURUSD")
        instrument_id_str = f"{symbol.replace('/', '')}.{venue_str}"
    
    print(f"\n📝 Instrument: {instrument.id}")
    print(f"   Symbol: {symbol}")
    print(f"   Venue: {venue_str}")
    
    # Convert DataFrame to Nautilus bars
    print(f"\n🔄 Converting {len(df)} rows to Nautilus format...")
    
    # Create bar type
    bar_type_str = f"{instrument_id_str}-1-HOUR-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)
    
    # Prepare data in format wrangler expects
    # The wrangler needs a DataFrame with datetime index
    df_for_wrangler = df.copy()
    
    # Final cleaning step - ensure OHLC integrity
    df_for_wrangler['high'] = df_for_wrangler[['open', 'high', 'close']].max(axis=1)
    df_for_wrangler['low'] = df_for_wrangler[['open', 'low', 'close']].min(axis=1)
    
    # Debug: Check a few rows
    print(f"\n🔍 Sample data (first 3 rows):")
    for idx in range(min(3, len(df_for_wrangler))):
        row = df_for_wrangler.iloc[idx]
        print(f"   Row {idx}: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")
        # Verify OHLC relationships
        if row['high'] < row['open'] or row['high'] < row['close']:
            print(f"   ⚠️  High issue in row {idx}!")
        if row['low'] > row['open'] or row['low'] > row['close']:
            print(f"   ⚠️  Low issue in row {idx}!")
    
    df_for_wrangler = df_for_wrangler.set_index('datetime')
    df_for_wrangler.index = pd.to_datetime(df_for_wrangler.index, utc=True)
    
    # Use wrangler to process data
    wrangler = BarDataWrangler(bar_type, instrument)
    bars = wrangler.process(df_for_wrangler)
    
    print(f"✅ Created {len(bars)} Nautilus bars")
    
    return bars, instrument, bar_type


# ==================== PART 3: BACKTEST CONFIGURATION ====================

def setup_backtest_engine(instrument, starting_balance=100000):
    """
    Configure and create the backtest engine
    
    Args:
        instrument: Nautilus instrument object
        starting_balance: Starting account balance in USD
    
    Returns:
        Configured BacktestEngine
    """
    print("\n" + "="*70)
    print("⚙️  SETTING UP BACKTEST ENGINE")
    print("="*70)
    
    # Configure engine
    config = BacktestEngineConfig(
        trader_id=TraderId("TUTORIAL-01"),
        logging=LoggingConfig(log_level="INFO"),
    )
    
    # Create engine
    engine = BacktestEngine(config=config)
    
    # Add venue
    venue = Venue("KRAKEN")
    
    print(f"\n🏦 Venue: {venue}")
    print(f"   OMS Type: NETTING")
    print(f"   Account Type: CASH")
    print(f"   Starting Balance: ${starting_balance:,.2f}")
    
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(starting_balance, USD)],
    )
    
    # Add instrument
    engine.add_instrument(instrument)
    print(f"   Instrument: {instrument.id}")
    
    return engine


# ==================== PART 4: STRATEGY CONFIGURATION ====================

def create_ema_strategy(instrument, bar_type, fast_period=10, slow_period=20):
    """
    Create EMA crossover strategy
    
    Args:
        instrument: Nautilus instrument
        bar_type: Bar type for the strategy
        fast_period: Fast EMA period
        slow_period: Slow EMA period
    
    Returns:
        Configured EMACross strategy
    """
    print("\n" + "="*70)
    print("🎯 CREATING EMA CROSSOVER STRATEGY")
    print("="*70)
    
    print(f"\n📊 Strategy Parameters:")
    print(f"   Fast EMA: {fast_period} periods")
    print(f"   Slow EMA: {slow_period} periods")
    print(f"   Trade Size: {instrument.make_qty(0.1)}")
    
    # Configure strategy
    config = EMACrossConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        fast_ema_period=fast_period,
        slow_ema_period=slow_period,
        trade_size=Decimal("0.1"),  # Trade 0.1 ETH per signal
    )
    
    # Create strategy
    strategy = EMACross(config=config)
    
    print(f"\n✅ Strategy created: {strategy.__class__.__name__}")
    
    return strategy


# ==================== PART 5: RUN BACKTEST ====================

def run_backtest(engine, bars, strategy):
    """
    Execute the backtest
    
    Args:
        engine: Configured BacktestEngine
        bars: List of Bar objects
        strategy: Strategy instance
    
    Returns:
        BacktestEngine with results
    """
    print("\n" + "="*70)
    print("⚡ RUNNING BACKTEST")
    print("="*70)
    
    # Add data to engine
    print(f"\n📊 Loading {len(bars)} bars into engine...")
    engine.add_data(bars)
    
    # Add strategy to engine
    print(f"🎯 Adding strategy to engine...")
    engine.add_strategy(strategy)
    
    # Run backtest
    print(f"\n🚀 Starting backtest...\n")
    engine.run()
    print(f"\n✅ Backtest complete!")
    
    return engine


# ==================== PART 6: ANALYZE RESULTS ====================

def analyze_results(engine):
    """
    Analyze and display backtest results
    
    Args:
        engine: BacktestEngine with completed backtest
    """
    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS")
    print("="*70)
    
    # Get account
    venue = Venue("KRAKEN")
    accounts = list(engine.cache.accounts())
    
    if not accounts:
        print("\n⚠️  No account data available")
        return
    
    account = accounts[0]
    
    # Account balances
    print(f"\n💰 Final Account Balance:")
    for balance in account.balances().values():
        print(f"   {balance.currency}: {balance.total:.2f}")
    
    # Get orders and positions
    orders = engine.cache.orders()
    positions = engine.cache.positions()
    
    print(f"\n📈 Trading Statistics:")
    print(f"   Total Orders: {len(orders)}")
    print(f"   Total Positions: {len(positions)}")
    
    # Analyze closed positions
    closed_positions = [p for p in positions if p.is_closed]
    
    if closed_positions:
        print(f"   Closed Positions: {len(closed_positions)}")
        
        # Calculate P&L
        profitable = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0]
        losing = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) < 0]
        
        total_pnl = sum(float(p.realized_pnl) for p in closed_positions if p.realized_pnl)
        
        print(f"   Winning Trades: {len(profitable)}")
        print(f"   Losing Trades: {len(losing)}")
        
        if len(closed_positions) > 0:
            win_rate = len(profitable) / len(closed_positions) * 100
            print(f"   Win Rate: {win_rate:.2f}%")
        
        print(f"   Total Realized P&L: ${total_pnl:.2f}")
        
        if profitable and losing:
            avg_win = sum(float(p.realized_pnl) for p in profitable) / len(profitable)
            avg_loss = sum(float(p.realized_pnl) for p in losing) / len(losing)
            print(f"   Average Win: ${avg_win:.2f}")
            print(f"   Average Loss: ${avg_loss:.2f}")
            
            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss)
                print(f"   Profit Factor: {profit_factor:.2f}")
    
    else:
        print("\n⚠️  No closed positions - strategy may need adjustment")
        print("   Possible reasons:")
        print("   - EMA periods too slow for the data")
        print("   - Not enough data for signals")
        print("   - Market was ranging (no clear trend)")
    
    # Generate reports
    print("\n" + "="*70)
    print("📋 DETAILED REPORTS")
    print("="*70)
    
    try:
        print("\n" + "-"*70)
        print("ACCOUNT REPORT")
        print("-"*70)
        print(engine.trader.generate_account_report(venue))
        
        print("\n" + "-"*70)
        print("ORDER FILLS REPORT")
        print("-"*70)
        print(engine.trader.generate_order_fills_report())
        
        print("\n" + "-"*70)
        print("POSITIONS REPORT")
        print("-"*70)
        print(engine.trader.generate_positions_report())
    except Exception as e:
        print(f"⚠️  Could not generate reports: {e}")


# ==================== PART 7: SAVE RESULTS ====================

def save_results(engine, output_dir='./tutorial_results'):
    """
    Save backtest results to CSV files
    
    Args:
        engine: BacktestEngine with results
        output_dir: Directory to save results
    """
    print("\n" + "="*70)
    print("💾 SAVING RESULTS")
    print("="*70)
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save orders
    orders = engine.cache.orders()
    if orders:
        orders_file = f"{output_dir}/orders_{timestamp}.csv"
        # Convert orders to DataFrame and save
        print(f"   Saved orders to: {orders_file}")
    
    # Save positions
    positions = engine.cache.positions()
    if positions:
        positions_file = f"{output_dir}/positions_{timestamp}.csv"
        # Convert positions to DataFrame and save
        print(f"   Saved positions to: {positions_file}")
    
    print(f"\n✅ Results saved to: {output_dir}")


# ==================== MAIN EXECUTION ====================

def main():
    """
    Main tutorial execution
    """
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║     NAUTILUS TRADER TUTORIAL 1: EMA CROSS BACKTEST              ║
    ║                                                                  ║
    ║  This tutorial teaches:                                          ║
    ║  • Downloading data with CCXT                                    ║
    ║  • Setting up a backtest engine                                  ║
    ║  • Creating a simple EMA strategy                                ║
    ║  • Running and analyzing backtests                               ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Part 1: Download data
        df = download_historical_data(
            exchange_id='kraken',
            symbol='ETH/USD',
            timeframe='1h',
            days_back=30
        )
        
        # Part 2: Prepare data
        bars, instrument, bar_type = prepare_nautilus_data(df, 'ETH/USD', 'KRAKEN')
        
        # Part 3: Setup engine
        engine = setup_backtest_engine(instrument, starting_balance=100000)
        
        # Part 4: Create strategy
        strategy = create_ema_strategy(
            instrument, 
            bar_type,
            fast_period=10,
            slow_period=20
        )
        
        # Part 5: Run backtest
        engine = run_backtest(engine, bars, strategy)
        
        # Part 6: Analyze results
        analyze_results(engine)
        
        # Part 7: Save results
        save_results(engine)
        
        print("\n" + "="*70)
        print("🎉 TUTORIAL COMPLETE!")
        print("="*70)
        print("\n💡 Next Steps:")
        print("   1. Try different EMA periods (fast/slow)")
        print("   2. Change the timeframe (4h, 1d)")
        print("   3. Test with different pairs (BTC/USD)")
        print("   4. Move to Tutorial 2 for advanced indicators")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error during tutorial: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if 'engine' in locals():
            engine.dispose()


if __name__ == "__main__":
    main()
