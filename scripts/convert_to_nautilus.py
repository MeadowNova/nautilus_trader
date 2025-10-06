#!/usr/bin/env python3
"""
Convert WinkingFace parquet files to Nautilus-compatible format.

This script:
1. Loads all 92 parquet files for each coin
2. Merges them into a single dataframe
3. Converts to Nautilus Bar format
4. Saves as Nautilus-compatible parquet files
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Required library not installed: {e}")
    print("Install with: pip install pandas pyarrow tqdm")
    sys.exit(1)


def load_and_merge_coin_data(coin_dir: Path, coin_name: str) -> pd.DataFrame:
    """Load and merge all parquet files for a coin."""
    
    print(f"\n📦 Loading {coin_name} data...")
    
    parquet_files = sorted(coin_dir.glob("*.parquet"))
    
    if not parquet_files:
        print(f"   ❌ No parquet files found in {coin_dir}")
        return None
    
    print(f"   Found {len(parquet_files)} files")
    
    dfs = []
    
    with tqdm(parquet_files, desc=f"   Loading {coin_name}", unit="file") as pbar:
        for file in pbar:
            try:
                df = pd.read_parquet(file)
                dfs.append(df)
            except Exception as e:
                print(f"\n   ⚠️  Error loading {file.name}: {e}")
    
    if not dfs:
        print(f"   ❌ No data loaded")
        return None
    
    # Merge all dataframes
    print(f"   Merging {len(dfs)} dataframes...")
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # Sort by timestamp
    merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
    merged_df = merged_df.sort_values('timestamp').reset_index(drop=True)
    
    # Remove duplicates
    initial_rows = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=['timestamp'], keep='first')
    final_rows = len(merged_df)
    
    if initial_rows > final_rows:
        print(f"   🧹 Removed {initial_rows - final_rows} duplicate rows")
    
    print(f"   ✅ Loaded {len(merged_df):,} total candles")
    print(f"   📅 Date range: {merged_df['timestamp'].min()} to {merged_df['timestamp'].max()}")
    
    return merged_df


def convert_to_nautilus_format(
    df: pd.DataFrame,
    instrument_id: str,
    bar_type: str = "1-MINUTE"
) -> pd.DataFrame:
    """
    Convert dataframe to Nautilus Bar format.
    
    Nautilus expects:
    - ts_event: Event timestamp (nanoseconds)
    - ts_init: Initialization timestamp (nanoseconds)
    - open: Open price
    - high: High price
    - low: Low price
    - close: Close price
    - volume: Volume
    """
    
    print(f"\n🔄 Converting to Nautilus format...")
    
    # Convert timestamp to nanoseconds
    df['ts_event'] = (df['timestamp'].astype('int64') // 1_000_000).astype('int64')  # milliseconds -> nanoseconds
    df['ts_init'] = df['ts_event']  # Use same timestamp for init
    
    # Rename columns to Nautilus format
    nautilus_df = pd.DataFrame({
        'ts_event': df['ts_event'],
        'ts_init': df['ts_init'],
        'open': df['open'].astype('float64'),
        'high': df['high'].astype('float64'),
        'low': df['low'].astype('float64'),
        'close': df['close'].astype('float64'),
        'volume': df['volume'].astype('float64'),
    })
    
    # Add metadata columns (optional but helpful)
    nautilus_df['instrument_id'] = instrument_id
    nautilus_df['bar_type'] = bar_type
    
    print(f"   ✅ Converted {len(nautilus_df):,} bars")
    print(f"   Columns: {nautilus_df.columns.tolist()}")
    
    return nautilus_df


def save_nautilus_parquet(
    df: pd.DataFrame,
    output_file: Path,
    instrument_id: str
) -> None:
    """Save dataframe as Nautilus-compatible parquet file."""
    
    print(f"\n💾 Saving to {output_file}...")
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create PyArrow schema
    schema = pa.schema([
        ('ts_event', pa.int64()),
        ('ts_init', pa.int64()),
        ('open', pa.float64()),
        ('high', pa.float64()),
        ('low', pa.float64()),
        ('close', pa.float64()),
        ('volume', pa.float64()),
        ('instrument_id', pa.string()),
        ('bar_type', pa.string()),
    ])
    
    # Convert to PyArrow Table
    table = pa.Table.from_pandas(df, schema=schema)
    
    # Write parquet with compression
    pq.write_table(
        table,
        output_file,
        compression='snappy',
        use_dictionary=True,
        write_statistics=True
    )
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"   ✅ Saved {len(df):,} rows ({file_size_mb:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(
        description="Convert WinkingFace parquet files to Nautilus format"
    )
    parser.add_argument(
        "--coins",
        nargs="+",
        choices=["BTC", "ETH"],
        default=["ETH", "BTC"],
        help="Coins to convert (default: ETH BTC)",
    )
    parser.add_argument(
        "--input",
        default="data/raw/parquet/winkingface",
        help="Input directory (default: data/raw/parquet/winkingface)",
    )
    parser.add_argument(
        "--output",
        default="data/nautilus",
        help="Output directory (default: data/nautilus)",
    )
    
    args = parser.parse_args()
    
    input_base = Path(args.input)
    output_base = Path(args.output)
    
    print("=" * 70)
    print("🔄 WinkingFace → Nautilus Converter")
    print("=" * 70)
    print(f"\nCoins: {', '.join(args.coins)}")
    print(f"Input: {input_base}")
    print(f"Output: {output_base}")
    
    results = []
    
    # Process each coin
    for coin in args.coins:
        coin_dir = input_base / coin
        
        if not coin_dir.exists():
            print(f"\n⚠️  Directory not found: {coin_dir}")
            continue
        
        # Load and merge data
        df = load_and_merge_coin_data(coin_dir, coin)
        
        if df is None or len(df) == 0:
            print(f"   ⚠️  No data to convert for {coin}")
            continue
        
        # Convert to Nautilus format
        instrument_id = f"{coin}-USDT.WINKINGFACE"
        nautilus_df = convert_to_nautilus_format(df, instrument_id)
        
        # Save to parquet
        output_file = output_base / f"{coin}-USDT-1-MINUTE.parquet"
        save_nautilus_parquet(nautilus_df, output_file, instrument_id)
        
        results.append({
            "coin": coin,
            "rows": len(nautilus_df),
            "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            "output": str(output_file)
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Conversion Summary")
    print("=" * 70)
    
    for result in results:
        print(f"\n✅ {result['coin']}")
        print(f"   Rows: {result['rows']:,}")
        print(f"   Date Range: {result['date_range']}")
        print(f"   Output: {result['output']}")
    
    print(f"\n🎯 Converted {len(results)} coins successfully!")
    print(f"📁 Nautilus data ready at: {output_base}")


if __name__ == "__main__":
    main()
