#!/usr/bin/env python3
"""
Simple backtest using converted WinkingFace data.

This demonstrates how to:
1. Load converted parquet data directly
2. Create synthetic instruments
3. Run a simple EMA cross strategy
4. Analyze results
"""

import pandas as pd
from pathlib import Path
from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.model.currencies import BTC, USD, USDT
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, BarAggregation, OmsType, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# Import the strategy from tutorials
import sys
sys.path.append("tutorials")
try:
    from tutorial_01_SIMPLE_VERSION import EMACrossStrategy
    print("✅ Strategy imported from tutorials")
except ImportError:
    print("❌ Could not import strategy - make sure tutorial_01_SIMPLE_VERSION.py exists")
    exit(1)


def create_crypto_instrument(symbol: str, venue: str = "WINKINGFACE") -> CryptoPerpetual:
    """Create a synthetic crypto instrument for backtesting."""
    
    # Parse symbol (e.g., "BTC-USDT" -> "BTC", "USDT")
    base, quote = symbol.split("-")
    
    instrument_id = InstrumentId(
        symbol=Symbol(symbol),
        venue=Venue(venue)
    )
    
    # Create a synthetic perpetual contract
    instrument = CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        base_currency=BTC if base == "BTC" else USDT,  # Simplified
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=2,
        size_precision=8,
        price_increment=Price(0.01, precision=2),
        size_increment=Quantity(0.00000001, precision=8),
        max_quantity=Quantity(1000, precision=8),
        min_quantity=Quantity(0.00001, precision=8),
        max_notional=None,
        min_notional=Money(10.00, USDT),
        max_price=Price(1000000, precision=2),
        min_price=Price(0.01, precision=2),
        margin_init=Decimal("0.0100"),
        margin_maint=Decimal("0.0050"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0006"),
        ts_event=0,
        ts_init=0,
    )
    
    return instrument


def load_bars_from_parquet(file_path: Path, instrument_id: InstrumentId, limit: int = None) -> list:
    """
    Load bars from parquet file and convert to Nautilus Bar objects.
    
    Args:
        file_path: Path to parquet file
        instrument_id: Nautilus instrument ID
        limit: Maximum number of bars to load (None = all)
    
    Returns:
        List of Nautilus Bar objects
    """
    
    print(f"\n📊 Loading bars from {file_path.name}...")
    
    # Read parquet file
    df = pd.read_parquet(file_path)
    
    if limit:
        df = df.head(limit)
    
    print(f"   Loaded {len(df):,} bars")
    print(f"   Date range: {pd.to_datetime(df['ts_event'].min(), unit='ms')} to {pd.to_datetime(df['ts_event'].max(), unit='ms')}")
    
    # Convert to Nautilus Bar objects
    bars = []
    
    # Create bar type (1-MINUTE bars)
    bar_type = BarType(
        instrument_id=instrument_id,
        bar_spec=BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
    )
    
    print(f"   Converting to Nautilus bars...")
    
    from nautilus_trader.model.data import Bar
    from nautilus_trader.model.objects import Price, Quantity
    
    for _, row in df.iterrows():
        bar = Bar(
            bar_type=bar_type,
            open=Price(row['open'], precision=2),
            high=Price(row['high'], precision=2),
            low=Price(row['low'], precision=2),
            close=Price(row['close'], precision=2),
            volume=Quantity(row['volume'], precision=8),
            ts_event=int(row['ts_event'] * 1_000_000),  # milliseconds to nanoseconds
            ts_init=int(row['ts_init'] * 1_000_000),
        )
        bars.append(bar)
    
    print(f"   ✅ Converted {len(bars):,} bars")
    
    return bars


def run_backtest(
    symbol: str = "BTC-USDT",
    data_file: str = "data/nautilus/BTC-USDT-1-MINUTE.parquet",
    start_balance: float = 100000.0,
    fast_ema: int = 8,
    slow_ema: int = 21,
    limit_bars: int = None,  # Limit for testing (None = all data)
):
    """
    Run backtest with converted data.
    
    Args:
        symbol: Trading symbol (e.g., "BTC-USDT")
        data_file: Path to parquet file
        start_balance: Starting account balance in USDT
        fast_ema: Fast EMA period
        slow_ema: Slow EMA period
        limit_bars: Limit number of bars (for testing)
    """
    
    print("="*70)
    print("🚀 Nautilus Backtest with Converted Data")
    print("="*70)
    print(f"Symbol: {symbol}")
    print(f"Data: {data_file}")
    print(f"Starting Balance: ${start_balance:,.2f}")
    print(f"Strategy: EMA Cross ({fast_ema}/{slow_ema})")
    if limit_bars:
        print(f"⚠️  Testing mode: Limited to {limit_bars:,} bars")
    
    # Create instrument
    venue = "WINKINGFACE"
    instrument = create_crypto_instrument(symbol, venue)
    instrument_id = instrument.id
    
    print(f"\n✅ Created instrument: {instrument_id}")
    
    # Load bars from parquet
    data_path = Path(data_file)
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return
    
    bars = load_bars_from_parquet(data_path, instrument_id, limit_bars)
    
    # Configure backtest engine
    config = BacktestEngineConfig(
        trader_id="BACKTESTER-001",
        log_level="INFO",
    )
    
    # Create engine
    engine = BacktestEngine(config=config)
    
    # Add venue
    engine.add_venue(
        venue=Venue(venue),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(start_balance, USDT)],
    )
    
    # Add instrument
    engine.add_instrument(instrument)
    
    # Add bars
    print(f"\n📥 Adding {len(bars):,} bars to engine...")
    engine.add_bars(bars)
    
    # Add strategy
    print(f"\n⚙️  Adding strategy...")
    strategy = EMACrossStrategy(
        instrument_id=instrument_id,
        fast_ema_period=fast_ema,
        slow_ema_period=slow_ema,
        trade_size=Decimal("0.01"),  # 0.01 BTC per trade
    )
    
    engine.add_strategy(strategy)
    
    # Run backtest
    print(f"\n🏃 Running backtest...")
    engine.run()
    
    # Get results
    print(f"\n📊 Results:")
    print("="*70)
    
    # Account statistics
    account = engine.trader.generate_account_report(Venue(venue))
    print(f"\n💰 Account:")
    print(account)
    
    # Position statistics  
    positions = engine.trader.generate_positions_report()
    print(f"\n📍 Positions:")
    print(positions)
    
    # Order statistics
    orders = engine.trader.generate_order_fills_report()
    print(f"\n📋 Orders:")
    print(orders)
    
    # Save results
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    positions_file = output_dir / f"positions_{symbol}_{timestamp}.csv"
    orders_file = output_dir / f"orders_{symbol}_{timestamp}.csv"
    
    positions.to_csv(positions_file)
    orders.to_csv(orders_file)
    
    print(f"\n💾 Results saved:")
    print(f"   {positions_file}")
    print(f"   {orders_file}")
    
    print(f"\n✅ Backtest complete!")


def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest with converted data")
    parser.add_argument("--symbol", default="BTC-USDT", help="Trading symbol")
    parser.add_argument("--data", default="data/nautilus/BTC-USDT-1-MINUTE.parquet", help="Data file")
    parser.add_argument("--balance", type=float, default=100000.0, help="Starting balance")
    parser.add_argument("--fast", type=int, default=8, help="Fast EMA period")
    parser.add_argument("--slow", type=int, default=21, help="Slow EMA period")
    parser.add_argument("--limit", type=int, default=None, help="Limit bars (for testing)")
    
    args = parser.parse_args()
    
    # Import required classes here to avoid issues
    from nautilus_trader.model.data import BarSpecification
    globals()['BarSpecification'] = BarSpecification
    
    run_backtest(
        symbol=args.symbol,
        data_file=args.data,
        start_balance=args.balance,
        fast_ema=args.fast,
        slow_ema=args.slow,
        limit_bars=args.limit,
    )


if __name__ == "__main__":
    main()
