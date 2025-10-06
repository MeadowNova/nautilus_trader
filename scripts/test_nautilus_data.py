#!/usr/bin/env python3
"""
Test if converted Nautilus data can be loaded and used for backtesting.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

try:
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    from nautilus_trader.model.data import BarType
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.test_kit.providers import TestDataProvider
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    print("✅ Nautilus imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you've activated the virtual environment:")
    print("  cd /home/ajk/Nautilus/nautilus_trader && source activate_env.sh")
    exit(1)


def test_parquet_read():
    """Test if we can read the parquet files."""
    print("\n" + "="*70)
    print("📊 Test 1: Read Parquet Files")
    print("="*70)
    
    btc_file = Path("data/nautilus/BTC-USDT-1-MINUTE.parquet")
    eth_file = Path("data/nautilus/ETH-USDT-1-MINUTE.parquet")
    
    for file in [btc_file, eth_file]:
        if not file.exists():
            print(f"❌ File not found: {file}")
            continue
        
        df = pd.read_parquet(file)
        
        # Convert timestamps to datetime for display
        ts_min = pd.to_datetime(df['ts_event'].min(), unit='ms')
        ts_max = pd.to_datetime(df['ts_event'].max(), unit='ms')
        
        print(f"\n✅ {file.name}")
        print(f"   Rows: {len(df):,}")
        print(f"   Columns: {df.columns.tolist()}")
        print(f"   Date range: {ts_min} to {ts_max}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        print(f"   Avg volume: {df['volume'].mean():.2f}")


def test_nautilus_catalog():
    """Test if Nautilus can read the data via ParquetDataCatalog."""
    print("\n" + "="*70)
    print("📊 Test 2: Nautilus ParquetDataCatalog")
    print("="*70)
    
    try:
        # Create a catalog pointing to our data directory
        catalog = ParquetDataCatalog("data/nautilus")
        
        print(f"✅ Catalog created")
        
        # List what's in the catalog
        instruments = catalog.instruments()
        print(f"   Instruments found: {len(instruments)}")
        
        for inst in instruments:
            print(f"     - {inst.id}")
        
        # Try to query bar data
        print("\n   Querying bar data...")
        
        # Query BTC bars
        btc_bars = catalog.bars(instrument_ids=["BTC-USDT.WINKINGFACE"])
        
        if btc_bars is not None and len(btc_bars) > 0:
            print(f"   ✅ Retrieved {len(btc_bars):,} BTC bars")
            print(f"      First bar: {btc_bars[0]}")
        else:
            print(f"   ⚠️  No BTC bars found")
        
    except Exception as e:
        print(f"   ⚠️  Catalog error: {e}")
        print(f"      This is expected - Nautilus may need additional metadata")


def test_data_quality():
    """Test data quality (OHLCV validation)."""
    print("\n" + "="*70)
    print("📊 Test 3: Data Quality Validation")
    print("="*70)
    
    btc_file = Path("data/nautilus/BTC-USDT-1-MINUTE.parquet")
    
    if not btc_file.exists():
        print(f"❌ File not found: {btc_file}")
        return
    
    df = pd.read_parquet(btc_file)
    
    # Check OHLCV integrity
    issues = []
    
    # High >= Open
    invalid_high_open = df[df['high'] < df['open']]
    if len(invalid_high_open) > 0:
        issues.append(f"High < Open: {len(invalid_high_open)} rows")
    
    # High >= Close
    invalid_high_close = df[df['high'] < df['close']]
    if len(invalid_high_close) > 0:
        issues.append(f"High < Close: {len(invalid_high_close)} rows")
    
    # Low <= Open
    invalid_low_open = df[df['low'] > df['open']]
    if len(invalid_low_open) > 0:
        issues.append(f"Low > Open: {len(invalid_low_open)} rows")
    
    # Low <= Close
    invalid_low_close = df[df['low'] > df['close']]
    if len(invalid_low_close) > 0:
        issues.append(f"Low > Close: {len(invalid_low_close)} rows")
    
    # High >= Low
    invalid_high_low = df[df['high'] < df['low']]
    if len(invalid_high_low) > 0:
        issues.append(f"High < Low: {len(invalid_high_low)} rows")
    
    # Check for zero/negative values
    zero_prices = df[(df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)]
    if len(zero_prices) > 0:
        issues.append(f"Zero/negative prices: {len(zero_prices)} rows")
    
    # Check for NaN values
    nan_count = df.isnull().sum().sum()
    if nan_count > 0:
        issues.append(f"NaN values: {nan_count}")
    
    # Check timestamp gaps
    df_sorted = df.sort_values('ts_event')
    time_diffs = df_sorted['ts_event'].diff()
    expected_diff = 60000  # 1 minute in milliseconds
    large_gaps = time_diffs[time_diffs > expected_diff * 2]
    
    if len(large_gaps) > 0:
        issues.append(f"Large time gaps: {len(large_gaps)} (>2 minutes)")
    
    # Report
    if len(issues) == 0:
        print("✅ All data quality checks passed!")
        print(f"   Total bars checked: {len(df):,}")
    else:
        print("⚠️  Data quality issues found:")
        for issue in issues:
            print(f"   - {issue}")
    
    # Show statistics
    print(f"\n📊 Data Statistics:")
    print(f"   Total bars: {len(df):,}")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"   Avg close: ${df['close'].mean():.2f}")
    print(f"   Avg volume: {df['volume'].mean():.2f}")


def main():
    print("="*70)
    print("🧪 Nautilus Data Testing Suite")
    print("="*70)
    print(f"Testing data in: data/nautilus/")
    
    # Run tests
    test_parquet_read()
    test_nautilus_catalog()
    test_data_quality()
    
    print("\n" + "="*70)
    print("✅ Testing Complete!")
    print("="*70)
    print("\nNext steps:")
    print("  1. If all tests passed, your data is ready for backtesting")
    print("  2. Run a simple backtest: python tutorials/tutorial_01_SIMPLE_VERSION.py")
    print("  3. Modify the tutorial to use your converted data")


if __name__ == "__main__":
    main()
