#!/usr/bin/env python3
"""
Run a complete backtest using downloaded Kraken CSV data with the AIAdaptiveStrategy.
"""

import argparse
import pandas as pd
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add venv and strategy paths to allow imports
import sys
sys.path.append("/home/ajk/Nautilus/nautilus_trader/.venv/lib/python3.13/site-packages")
sys.path.append("ajk_strategies")

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.currencies import BTC, USDT, ETH
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AccountType, AggregationSource, BarAggregation, OmsType, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos

# Import the AI strategy and its config
from ai_adaptive_strategy_main import AIAdaptiveStrategy
from ai_adaptive_strategy import AIAdaptiveStrategyConfig

def create_instrument(symbol: str, venue_name: str) -> CryptoPerpetual:
    """Create a crypto perpetual instrument for backtesting."""
    base_curr, quote_curr = symbol.split("/")
    currency_map = {"BTC": BTC, "ETH": ETH, "USDT": USDT, "USD": USDT}

    instrument_id = InstrumentId(symbol=Symbol(symbol), venue=Venue(venue_name))
    
    return CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        base_currency=currency_map[base_curr],
        quote_currency=currency_map[quote_curr],
        settlement_currency=currency_map[quote_curr],
        is_inverse=False,
        price_precision=2,
        size_precision=8,
        price_increment=Price.from_str("0.01"),
        size_increment=Quantity.from_str("0.00000001"),
        max_quantity=Quantity.from_str("1000.0"),
        min_quantity=Quantity.from_str("0.00001"),
        min_notional=Money(10.00, currency_map[quote_curr]),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0006"),
        ts_event=0,
        ts_init=0,
    )

def load_bars_from_csv(file_path: Path, instrument: CryptoPerpetual) -> list[Bar]:
    """Load bars from Kraken CSV file and convert to Nautilus Bar objects."""
    print(f"\n📊 Loading data from {file_path.name}...")
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"   Total bars: {len(df):,}")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    bar_spec = BarSpecification(1, BarAggregation.HOUR, PriceType.LAST)
    bar_type = BarType(instrument.id, bar_spec, AggregationSource.EXTERNAL)

    print(f"\n   Converting to Nautilus bars (BarType: {bar_type})...")
    bars = []
    for _, row in df.iterrows():
        ts_event = dt_to_unix_nanos(row['timestamp'])
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{row['open']:.2f}"),
            high=Price.from_str(f"{row['high']:.2f}"),
            low=Price.from_str(f"{row['low']:.2f}"),
            close=Price.from_str(f"{row['close']:.2f}"),
            volume=Quantity.from_str(f"{row['volume']:.8f}"),
            ts_event=ts_event,
            ts_init=ts_event,
        )
        bars.append(bar)
    
    print(f"   ✅ Converted {len(bars):,} bars")
    return bars

def run_backtest(symbol: str, data_file: Path, start_balance: float):
    """
    Run backtest with the AIAdaptiveStrategy.
    """
    print("="*70)
    print("🚀 Nautilus Backtest - AI-Adaptive Strategy")
    print("="*70)
    print(f"Symbol: {symbol}")
    print(f"Data: {data_file}")
    print(f"Starting balance: ${start_balance:,.2f} USDT")

    venue = Venue("KRAKEN")
    instrument = create_instrument(symbol, venue.value)
    print(f"\n✅ Created instrument: {instrument.id}")

    bars = load_bars_from_csv(data_file, instrument)
    if not bars:
        print("❌ No bars loaded!")
        return

    print(f"\n⚙️  Creating backtest engine...")
    engine = BacktestEngine()

    print(f"\n⚙️  Configuring venue: {venue}")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(start_balance, USDT)],
    )

    print(f"   Adding instrument: {instrument.id}")
    engine.add_instrument(instrument)

    print(f"\n📥 Adding {len(bars):,} bars to engine...")
    engine.add_data(bars)

    print(f"\n⚙️  Creating AI strategy...")
    
    bar_spec = BarSpecification(1, BarAggregation.HOUR, PriceType.LAST)
    bar_type = BarType(instrument.id, bar_spec, AggregationSource.EXTERNAL)

    strategy_config = AIAdaptiveStrategyConfig(
        instrument_id=str(instrument.id),
        bar_type=str(bar_type),
        venue=venue.value,
        base_trade_size=Decimal("0.01"), # Set a reasonable trade size
    )

    strategy = AIAdaptiveStrategy(config=strategy_config)
    
    engine.add_strategy(strategy)

    print(f"\n🏃 Running backtest...")
    print("="*70)
    engine.run()
    print("="*70)

    print("\n📊 BACKTEST RESULTS")
    print("="*70)
    results = engine.trader.generate_order_fills_report()
    if not results.empty:
        print(results.to_string())
    else:
        print("No trades were executed.")

    # Save results
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    positions_file = output_dir / f"positions_AI_{symbol.replace('/', '_')}_{timestamp}.csv"
    engine.trader.generate_positions_report().to_csv(positions_file)
    fills_file = output_dir / f"fills_AI_{symbol.replace('/', '_')}_{timestamp}.csv"
    results.to_csv(fills_file)
    print(f"\n💾 Results saved to {positions_file} and {fills_file}")


def main():
    parser = argparse.ArgumentParser(description="Run AI backtest on Kraken CSV data.")
    parser.add_argument(
        "--symbol",
        default="BTC/USD",
        choices=["BTC/USD", "ETH/USD"],
        help="Symbol to backtest."
    )
    args = parser.parse_args()

    data_file = Path(f"data/raw/kraken_csv/kraken_{args.symbol.replace('/', '_')}_1h_20240101_20250101.csv")
    
    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        sys.exit(1)

    run_backtest(symbol=args.symbol, data_file=data_file, start_balance=100_000.0)

if __name__ == "__main__":
    main()