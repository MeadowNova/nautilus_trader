#!/usr/bin/env python3
"""
Analyze merged parquet data for time gaps.
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from tqdm import tqdm

def load_and_merge_coin_data(coin_dir: Path, coin_name: str) -> pd.DataFrame:
    """Load and merge all parquet files for a coin."""
    print(f"\n📦 Loading {coin_name} data from {coin_dir}...")
    parquet_files = sorted(coin_dir.glob("*.parquet"))
    if not parquet_files:
        print(f"   ❌ No parquet files found in {coin_dir}")
        return None

    print(f"   Found {len(parquet_files)} files")
    dfs = [pd.read_parquet(file) for file in tqdm(parquet_files, desc=f"   Loading {coin_name}", unit="file")]
    
    if not dfs:
        print(f"   ❌ No data loaded")
        return None

    print(f"   Merging {len(dfs)} dataframes...")
    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
    merged_df = merged_df.sort_values('timestamp').reset_index(drop=True)
    
    initial_rows = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=['timestamp'], keep='first')
    final_rows = len(merged_df)
    if initial_rows > final_rows:
        print(f"   🧹 Removed {initial_rows - final_rows} duplicate rows")

    print(f"   ✅ Loaded {len(merged_df):,} total candles")
    return merged_df

def analyze_gaps(df: pd.DataFrame, max_gap_minutes: int = 2):
    """Analyze the dataframe for time gaps."""
    print(f"\n🔬 Analyzing for time gaps larger than {max_gap_minutes} minutes...")
    
    df_sorted = df.sort_values('timestamp')
    df_sorted['time_diff'] = df_sorted['timestamp'].diff()
    
    # Identify gaps larger than the threshold
    large_gaps = df_sorted[df_sorted['time_diff'] > pd.Timedelta(minutes=max_gap_minutes)]
    
    if large_gaps.empty:
        print("✅ No significant time gaps found!")
        return

    print(f"⚠️  Found {len(large_gaps)} gaps larger than {max_gap_minutes} minutes.")
    
    print("\n--- First 20 Gaps ---")
    for index, row in large_gaps.head(20).iterrows():
        gap_end = row['timestamp']
        time_diff = row['time_diff']
        gap_start = gap_end - time_diff
        print(f"  - Gap of {str(time_diff):>25} found between {gap_start} and {gap_end}")

    print("\n--- Gap Summary ---")
    print(f"Total gaps found: {len(large_gaps)}")
    print(f"Largest gap:      {large_gaps['time_diff'].max()}")
    print(f"Smallest gap:     {large_gaps['time_diff'].min()}")
    print(f"Average gap:      {large_gaps['time_diff'].mean()}")

def main():
    parser = argparse.ArgumentParser(description="Analyze data for time gaps.")
    parser.add_argument(
        "coin",
        choices=["BTC", "ETH"],
        help="Coin to analyze.",
    )
    parser.add_argument(
        "--input",
        default="data/raw/parquet/winkingface",
        help="Input directory (default: data/raw/parquet/winkingface)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input) / args.coin
    
    df = load_and_merge_coin_data(input_dir, args.coin)
    
    if df is not None and not df.empty:
        analyze_gaps(df)

if __name__ == "__main__":
    main()
