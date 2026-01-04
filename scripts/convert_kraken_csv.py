#!/usr/bin/env python3
"""
Convert Kraken CSV data to Nautilus-compatible format and register instruments.
"""

import pandas as pd
import sys
from pathlib import Path

# Add venv path to allow imports
sys.path.append("/home/ajk/Nautilus/nautilus_trader/.venv/lib/python3.13/site-packages")

try:
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
    from nautilus_trader.model.instrument import Instrument
    from nautilus_trader.model.identifiers import InstrumentId, Symbol
    from nautilus_trader.model.enums import AssetClass, InstrumentClass
    from nautilus_trader.model.objects import Currency, Price, Quantity, Venue
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    from nautilus_trader.model.data import Bar, BarType, BarSpecification
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run this script using the project venv python: .venv/bin/python scripts/convert_kraken_csv.py")
    sys.exit(1)

def create_instrument(symbol_str: str, venue: Venue) -> Instrument:
    """Creates a generic instrument definition."""
    base, quote = symbol_str.split("/")
    instrument_id = InstrumentId(Symbol(symbol_str), venue)
    
    return Instrument(
        instrument_id=instrument_id,
        native_symbol=Symbol(symbol_str),
        asset_class=AssetClass.CRYPTO,
        instrument_class=InstrumentClass.PERPETUAL,
        price_precision=2,
        price_increment=Price(1, 2),
        size_precision=8,
        size_increment=Quantity(1, 8),
        lot_size=Quantity(1, 8),
        quote_currency=Currency(quote),
        is_inverse=False,
        multiplier=Quantity(1, 0),
        margin_init=Price(1, 2),
        margin_maint=Price(1, 2),
        maker_fee=Price(0, 4),
        taker_fee=Price(0, 4),
        ts_event=0,
        ts_init=0,
    )

def convert_csv_to_nautilus(catalog: ParquetDataCatalog, csv_path: Path, instrument: Instrument):
    """Reads a CSV, converts it to Nautilus Bars, and writes to the catalog."""
    print(f"\n🔄 Processing {csv_path.name}...")
    
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"   Read {len(df):,} rows from CSV.")

    bar_spec = BarSpecification(1, "MINUTE")
    bar_type = BarType(instrument.id, bar_spec)

    bars = []
    for _, row in df.iterrows():
        ts_event = dt_to_unix_nanos(row['timestamp'])
        bar = Bar(
            bar_type=bar_type,
            open=Price(row['open'], instrument.price_precision),
            high=Price(row['high'], instrument.price_precision),
            low=Price(row['low'], instrument.price_precision),
            close=Price(row['close'], instrument.price_precision),
            volume=Quantity(row['volume'], instrument.size_precision),
            ts_event=ts_event,
            ts_init=ts_event, # Use same timestamp for init
        )
        bars.append(bar)

    print(f"   Converted {len(bars)} rows to Nautilus Bar objects.")
    
    catalog.write_data(bars)
    print(f"   ✅ Wrote {len(bars)} bars to catalog for instrument {instrument.id}")

def main():
    """Main function to run the conversion."""
    input_dir = Path("data/raw/kraken_csv")
    output_dir = Path("data/nautilus")
    venue = Venue("KRAKEN")

    print("="*70)
    print("🐙 Kraken CSV to Nautilus Converter")
    print("="*70)
    print(f"Input directory:  {input_dir}")
    print(f"Output catalog:   {output_dir}")
    print(f"Venue:            {venue}")
    print("-"*70)

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        sys.exit(1)

    # Initialize the data catalog
    catalog = ParquetDataCatalog(str(output_dir))
    print(f"✅ Initialized ParquetDataCatalog at {output_dir}")

    # Find CSV files to process
    csv_files = list(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {input_dir}")
        sys.exit(1)

    for csv_path in csv_files:
        # Infer symbol from filename, e.g., kraken_BTC_USD_1h_... -> BTC/USD
        try:
            symbol_str = csv_path.name.split("_")[1] + "/" + csv_path.name.split("_")[2]
        except IndexError:
            print(f"⚠️  Could not determine symbol from filename: {csv_path.name}. Skipping.")
            continue

        # 1. Create and register the instrument
        instrument = create_instrument(symbol_str, venue)
        print(f"\n🔧 Created instrument {instrument.id}")
        catalog.write_data([instrument])
        print(f"   ✅ Wrote instrument definition to catalog.")

        # 2. Convert the CSV bar data and write to catalog
        convert_csv_to_nautilus(catalog, csv_path, instrument)

    print("\n" + "="*70)
    print("✅ Conversion complete!")
    print("="*70)

if __name__ == "__main__":
    main()
