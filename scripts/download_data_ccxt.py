#!/usr/bin/env python3
"""
Download historical data using the CCXTDataFeed class.
"""

import sys
from datetime import datetime

# Add strategy directory to path to allow import
sys.path.append('ajk_strategies')

try:
    from ccxt_live_data import CCXTDataFeed
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Ensure ajk_strategies/ccxt_live_data.py exists.")
    sys.exit(1)

def download_all_data():
    """Download all required historical data."""
    
    exchange = 'kraken'
    symbols = ['BTC/USD', 'ETH/USD']
    timeframe = '1h'
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 1, 1)

    print("="*70)
    print("🚀 Starting CCXT Historical Data Download")
    print("="*70)
    print(f"Exchange: {exchange}")
    print(f"Symbols: {symbols}")
    print(f"Timeframe: {timeframe}")
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print("-"*70)

    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        try:
            feed = CCXTDataFeed(
                exchange_id=exchange,
                symbol=symbol,
                timeframe=timeframe,
            )
            
            df = feed.fetch_historical_data(
                start_date=start_date,
                end_date=end_date,
                save_to_csv=True
            )
            
            if df is not None and not df.empty:
                print(f"✅ Successfully downloaded and saved data for {symbol}")
            else:
                print(f"⚠️ No data returned for {symbol}")

        except Exception as e:
            print(f"❌ An error occurred while processing {symbol}: {e}")

    print("\n" + "="*70)
    print("✅ All downloads complete!")
    print("="*70)

if __name__ == "__main__":
    download_all_data()
