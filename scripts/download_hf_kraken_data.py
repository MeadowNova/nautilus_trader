#!/usr/bin/env python3
"""
Download Kraken trading data from Hugging Face.

Dataset: GotThatData/kraken-trading-data
URL: https://huggingface.co/datasets/GotThatData/kraken-trading-data

This script downloads historical OHLCV data for specified trading pairs.
"""

import argparse
import sys
from pathlib import Path

try:
    from datasets import load_dataset
    import pandas as pd
except ImportError as e:
    print(f"Error: Required library not installed: {e}")
    print("Install with: pip install datasets pandas")
    sys.exit(1)


def download_kraken_data(
    symbols: list[str],
    output_dir: str,
    timeframe: str = "1h",
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01",
):
    """
    Download Kraken trading data from Hugging Face.
    
    Args:
        symbols: List of trading pairs (e.g., ['ETH/USD', 'BTC/USD'])
        output_dir: Directory to save the data
        timeframe: Timeframe for OHLCV data (1m, 5m, 1h, 1d)
        start_date: Start date for data (YYYY-MM-DD)
        end_date: End date for data (YYYY-MM-DD)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Downloading Kraken data from Hugging Face...")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Date range: {start_date} to {end_date}")
    print(f"   Output: {output_path}")
    print()
    
    try:
        # Load the dataset
        print("📦 Loading dataset from Hugging Face...")
        dataset = load_dataset("GotThatData/kraken-trading-data", split="train")
        
        print(f"✅ Dataset loaded successfully!")
        print(f"   Total records: {len(dataset)}")
        print(f"   Columns: {dataset.column_names}")
        print()
        
        # Convert to pandas DataFrame for easier filtering
        df = dataset.to_pandas()
        
        # Display sample of available data
        print("📊 Dataset preview:")
        print(df.head())
        print()
        
        # Save dataset info
        info_file = output_path / "dataset_info.txt"
        with open(info_file, "w") as f:
            f.write(f"Dataset: GotThatData/kraken-trading-data\n")
            f.write(f"Total records: {len(df)}\n")
            f.write(f"Columns: {df.columns.tolist()}\n")
            f.write(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}\n")
            f.write(f"\nSample data:\n{df.head()}\n")
        
        print(f"✅ Dataset info saved to {info_file}")
        
        # Filter and save data for each symbol
        for symbol in symbols:
            print(f"\n🔍 Processing {symbol}...")
            
            # Kraken formats: ETH/USD -> XETHZUSD, BTC/USD -> XXBTZUSD
            # Try different symbol formats
            base, quote = symbol.split('/')
            symbol_slash = symbol.upper()  # ETH/USD
            symbol_normalized = symbol.replace("/", "").upper()  # ETHUSD
            symbol_kraken_single = f"X{base}Z{quote}".upper()  # XETHZUSD
            symbol_kraken_double = f"XX{base}Z{quote}".upper()  # XXETHZUSD
            
            # Special case: BTC is XBT in Kraken
            if base.upper() == 'BTC':
                symbol_kraken_btc = f"XXBTZ{quote}".upper()  # XXBTZUSD
            else:
                symbol_kraken_btc = None
            
            formats_to_try = [symbol_slash, symbol_normalized, symbol_kraken_single, symbol_kraken_double]
            if symbol_kraken_btc:
                formats_to_try.append(symbol_kraken_btc)
            
            print(f"   Trying formats: {formats_to_try}")
            
            # Filter by pair (Kraken uses 'pair' column)
            mask = (df['pair'] == symbol_slash) | (df['pair'] == symbol_normalized) | (df['pair'] == symbol_kraken_single) | (df['pair'] == symbol_kraken_double)
            if symbol_kraken_btc:
                mask = mask | (df['pair'] == symbol_kraken_btc)
            symbol_df = df[mask].copy()
            
            if len(symbol_df) == 0:
                print(f"   ⚠️  No data found for {symbol}")
                print(f"   Available pairs: {df['pair'].unique()[:20]}")
                continue
            
            # Filter by date range
            if 'timestamp' in symbol_df.columns:
                symbol_df.loc[:, 'timestamp'] = pd.to_datetime(symbol_df['timestamp'])
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                symbol_df = symbol_df[
                    (symbol_df['timestamp'] >= start_dt) & 
                    (symbol_df['timestamp'] <= end_dt)
                ].copy()
            
            # Save to CSV
            output_file = output_path / f"{symbol.replace('/', '_')}_{timeframe}.csv"
            symbol_df.to_csv(output_file, index=False)
            
            print(f"   ✅ Saved {len(symbol_df)} records to {output_file}")
            print(f"   Date range: {symbol_df['timestamp'].min()} to {symbol_df['timestamp'].max()}")
            print(f"   Columns: {symbol_df.columns.tolist()}")
        
        print("\n✅ All data downloaded successfully!")
        print(f"📁 Data saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download Kraken trading data from Hugging Face")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["ETH/USD", "BTC/USD"],
        help="Trading pairs to download (default: ETH/USD BTC/USD)",
    )
    parser.add_argument(
        "--output",
        default="data/raw/huggingface",
        help="Output directory (default: data/raw/huggingface)",
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        help="Timeframe for OHLCV data (default: 1h)",
    )
    parser.add_argument(
        "--start",
        default="2024-01-01",
        help="Start date YYYY-MM-DD (default: 2024-01-01)",
    )
    parser.add_argument(
        "--end",
        default="2025-01-01",
        help="End date YYYY-MM-DD (default: 2025-01-01)",
    )
    
    args = parser.parse_args()
    
    download_kraken_data(
        symbols=args.symbols,
        output_dir=args.output,
        timeframe=args.timeframe,
        start_date=args.start,
        end_date=args.end,
    )


if __name__ == "__main__":
    main()
