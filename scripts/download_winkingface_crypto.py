#!/usr/bin/env python3
"""
Download WinkingFace CryptoLM datasets (BTC-USDT and ETH-USDT).

This script downloads all parquet files for Bitcoin and Ethereum
with 1-minute OHLCV candles + technical indicators.
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Required library not installed: {e}")
    print("Install with: pip install requests tqdm")
    sys.exit(1)


def download_file(url: str, output_path: Path) -> tuple[str, bool, str]:
    """Download a single parquet file."""
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        return str(output_path), True, ""
    except Exception as e:
        return str(output_path), False, str(e)


def download_coin_dataset(
    coin_name: str,
    dataset_path: str,
    output_dir: Path,
    max_workers: int = 8
) -> dict:
    """Download all parquet files for a coin."""
    
    print(f"\n🚀 Downloading {coin_name} dataset...")
    print(f"   Dataset: {dataset_path}")
    print(f"   Output: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of parquet files
    api_url = f"https://huggingface.co/api/datasets/{dataset_path}/parquet/default/train"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        file_urls = response.json()
        
        print(f"   Found {len(file_urls)} parquet files")
        
        # Download files in parallel
        downloaded = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for i, url in enumerate(file_urls):
                output_file = output_dir / f"{i:03d}.parquet"
                
                # Skip if already exists
                if output_file.exists():
                    print(f"   ⏭️  Skipping {i:03d}.parquet (already exists)")
                    downloaded += 1
                    continue
                
                future = executor.submit(download_file, url, output_file)
                futures[future] = (i, url)
            
            # Progress bar
            with tqdm(total=len(futures), desc=f"   {coin_name}", unit="file") as pbar:
                for future in as_completed(futures):
                    file_idx, url = futures[future]
                    output_path, success, error = future.result()
                    
                    if success:
                        downloaded += 1
                        pbar.update(1)
                    else:
                        failed += 1
                        print(f"\n   ❌ Failed {file_idx:03d}.parquet: {error}")
                        pbar.update(1)
        
        print(f"\n   ✅ {coin_name}: Downloaded {downloaded}/{len(file_urls)} files")
        if failed > 0:
            print(f"   ⚠️  Failed: {failed} files")
        
        return {
            "coin": coin_name,
            "total": len(file_urls),
            "downloaded": downloaded,
            "failed": failed,
            "output_dir": str(output_dir)
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "coin": coin_name,
            "total": 0,
            "downloaded": 0,
            "failed": 1,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Download WinkingFace CryptoLM datasets"
    )
    parser.add_argument(
        "--coins",
        nargs="+",
        choices=["BTC", "ETH", "SOL", "XRP"],
        default=["ETH", "BTC"],
        help="Coins to download (default: ETH BTC)",
    )
    parser.add_argument(
        "--output",
        default="data/raw/parquet/winkingface",
        help="Output directory (default: data/raw/parquet/winkingface)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel downloads (default: 8)",
    )
    
    args = parser.parse_args()
    
    # Coin dataset mapping
    datasets = {
        "BTC": "WinkingFace/CryptoLM-Bitcoin-BTC-USDT",
        "ETH": "WinkingFace/CryptoLM-Ethereum-ETH-USDT",
        "SOL": "WinkingFace/CryptoLM-Solana-SOL-USDT",
        "XRP": "WinkingFace/CryptoLM-Ripple-XRP-USDT",
    }
    
    output_base = Path(args.output)
    
    print("=" * 70)
    print("📦 WinkingFace CryptoLM Dataset Downloader")
    print("=" * 70)
    print(f"\nCoins: {', '.join(args.coins)}")
    print(f"Workers: {args.workers}")
    print(f"Output: {output_base}")
    
    results = []
    
    # Download each coin
    for coin in args.coins:
        if coin not in datasets:
            print(f"\n⚠️  Unknown coin: {coin}")
            continue
        
        dataset_path = datasets[coin]
        output_dir = output_base / coin
        
        result = download_coin_dataset(
            coin_name=coin,
            dataset_path=dataset_path,
            output_dir=output_dir,
            max_workers=args.workers
        )
        results.append(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Download Summary")
    print("=" * 70)
    
    total_downloaded = 0
    total_failed = 0
    
    for result in results:
        coin = result["coin"]
        downloaded = result.get("downloaded", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)
        
        total_downloaded += downloaded
        total_failed += failed
        
        status = "✅" if failed == 0 else "⚠️"
        print(f"{status} {coin}: {downloaded}/{total} files downloaded")
        if "output_dir" in result:
            print(f"   📁 {result['output_dir']}")
    
    print(f"\n🎯 Total: {total_downloaded} files downloaded")
    if total_failed > 0:
        print(f"⚠️  Failed: {total_failed} files")
        sys.exit(1)
    else:
        print("✅ All downloads completed successfully!")


if __name__ == "__main__":
    main()
