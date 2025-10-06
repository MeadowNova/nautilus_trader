#!/usr/bin/env python3
"""
Backtest using converted WinkingFace data with proper Nautilus setup.

This example demonstrates:
1. Loading converted parquet data
2. Creating proper instruments for backtesting
3. Converting pandas data to Nautilus Bar objects
4. Running backtest with realistic venue configuration
5. Analyzing results

Based on Nautilus documentation: docs/concepts/backtesting.md
"""

import pandas as pd
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import (
    AccountType,
    AggregationSource,
    BarAggregation,
    OmsType,
    OrderSide,
    PriceType,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, TraderId, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.core.datetime import unix_nanos_to_dt

# Import strategy
from nautilus_trader.examples.strategies.ema_cross import EMACross
from nautilus_trader.config import StrategyConfig


def create_instrument(symbol: str = "BTC-USDT", venue_name: str = "WINKINGFACE") -> CryptoPerpetual:
    """
    Create a crypto perpetual instrument for backtesting.
    
    This matches the instrument format in your converted data.
    """
    instrument_id = InstrumentId(
        symbol=Symbol(symbol),
        venue=Venue(venue_name)
    )
    
    instrument = CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        base_currency=BTC,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=2,
        size_precision=8,
        price_increment=Price.from_str("0.01"),
        size_increment=Quantity.from_str("0.00000001"),
        max_quantity=Quantity.from_str("1000.00000000"),
        min_quantity=Quantity.from_str("0.00001000"),
        max_notional=None,
        min_notional=Money(10.00, USDT),
        max_price=Price.from_str("1000000.00"),
        min_price=Price.from_str("0.01"),
        margin_init=Decimal("0.0100"),  # 1% initial margin
        margin_maint=Decimal("0.0050"),  # 0.5% maintenance margin
        maker_fee=Decimal("0.0002"),  # 0.02%
        taker_fee=Decimal("0.0006"),  # 0.06%
        ts_event=0,
        ts_init=0,
    )
    
    return instrument


def load_bars_from_parquet(
    file_path: Path,
    instrument_id: InstrumentId,
    start_date: str = None,
    end_date: str = None,
    limit: int = None
) -> list[Bar]:
    """
    Load bars from parquet file and convert to Nautilus Bar objects.
    
    Args:
        file_path: Path to parquet file
        instrument_id: Nautilus instrument ID
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        limit: Optional limit on number of bars
    
    Returns:
        List of Nautilus Bar objects
    """
    
    print(f"\n📊 Loading data from {file_path.name}...")
    
    # Read parquet file
    df = pd.read_parquet(file_path)
    
    # Add datetime for filtering
    df['datetime'] = pd.to_datetime(df['ts_event'], unit='ms')
    
    # Apply date filters
    if start_date:
        df = df[df['datetime'] >= start_date]
        print(f"   Filtered from {start_date}")
    
    if end_date:
        df = df[df['datetime'] <= end_date]
        print(f"   Filtered to {end_date}")
    
    # Apply limit
    if limit:
        df = df.head(limit)
        print(f"   Limited to {limit:,} bars")
    
    print(f"   Total bars: {len(df):,}")
    print(f"   Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    # Create bar type (1-MINUTE bars)
    bar_spec = BarSpecification(
        step=1,
        aggregation=BarAggregation.MINUTE,
        price_type=PriceType.LAST,
    )
    
    bar_type = BarType(
        instrument_id=instrument_id,
        bar_spec=bar_spec,
        aggregation_source=AggregationSource.EXTERNAL,  # Data came from external source
    )
    
    print(f"\n   Converting to Nautilus bars...")
    print(f"   Bar type: {bar_type}")
    
    # Convert to Nautilus Bar objects
    bars = []
    
    for _, row in df.iterrows():
        # CRITICAL: Convert milliseconds to nanoseconds for Nautilus
        ts_event = int(row['ts_event'] * 1_000_000)
        ts_init = int(row['ts_init'] * 1_000_000)
        
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{row['open']:.2f}"),
            high=Price.from_str(f"{row['high']:.2f}"),
            low=Price.from_str(f"{row['low']:.2f}"),
            close=Price.from_str(f"{row['close']:.2f}"),
            volume=Quantity.from_str(f"{row['volume']:.8f}"),
            ts_event=ts_event,
            ts_init=ts_init,
        )
        bars.append(bar)
    
    print(f"   ✅ Converted {len(bars):,} bars")
    
    return bars


def run_backtest(
    symbol: str = "BTC-USDT",
    data_file: str = "data/nautilus/BTC-USDT-1-MINUTE.parquet",
    start_date: str = "2024-01-01",
    end_date: str = None,
    start_balance: float = 100_000.0,
    fast_ema: int = 10,
    slow_ema: int = 20,
    trade_size: float = 0.01,
):
    """
    Run backtest with converted data following Nautilus best practices.
    
    This follows the low-level API approach from docs/concepts/backtesting.md
    """
    
    print("="*70)
    print("🚀 Nautilus Backtest - Converted Data")
    print("="*70)
    print(f"Symbol: {symbol}")
    print(f"Data: {data_file}")
    print(f"Date range: {start_date} to {end_date or 'latest'}")
    print(f"Starting balance: ${start_balance:,.2f} USDT")
    print(f"Strategy: EMA Cross ({fast_ema}/{slow_ema})")
    print(f"Trade size: {trade_size} BTC")
    
    # Create instrument
    venue = Venue("WINKINGFACE")
    instrument = create_instrument(symbol, venue.value)
    instrument_id = instrument.id
    
    print(f"\n✅ Created instrument: {instrument_id}")
    
    # Load bars
    data_path = Path(data_file)
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return
    
    bars = load_bars_from_parquet(
        data_path,
        instrument_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    if len(bars) == 0:
        print("❌ No bars loaded!")
        return
    
    # Configure backtest engine
    print(f"\n⚙️  Creating backtest engine...")
    engine = BacktestEngine()
    
    # Add venue with proper configuration for bar execution
    # Per docs: bar_execution=True by default, book_type=L1_MBP for bars
    print(f"\n⚙️  Configuring venue: {venue}")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,  # Crypto perpetuals use margin
        base_currency=USDT,
        starting_balances=[Money(start_balance, USDT)],
        bar_execution=True,  # Enable bar-based execution (default)
        bar_adaptive_high_low_ordering=True,  # Use adaptive H/L ordering (more realistic)
    )
    
    # Add instrument
    print(f"   Adding instrument: {instrument_id}")
    engine.add_instrument(instrument)
    
    # Add bars to engine
    print(f"\n📥 Adding {len(bars):,} bars to engine...")
    engine.add_data(bars)
    
    # Create and add strategy
    print(f"\n⚙️  Creating strategy...")
    
    # Create strategy config
    strategy_config = StrategyConfig(
        order_id_tag="001",
        oms_type=OmsType.NETTING,
    )
    
    strategy = EMACross(
        config=strategy_config,
        fast_ema_period=fast_ema,
        slow_ema_period=slow_ema,
        trade_size=Decimal(str(trade_size)),
        instrument_id=instrument_id,
    )
    
    engine.add_strategy(strategy)
    
    # Run backtest
    print(f"\n🏃 Running backtest...")
    print("="*70)
    
    engine.run()
    
    # Get and display results
    print(f"\n" + "="*70)
    print("📊 BACKTEST RESULTS")
    print("="*70)
    
    # Get account state
    account = list(engine.trader.generate_accounts())[0]
    print(f"\n💰 Account: {account.id}")
    print(f"   Balance: {account.balance_total(USDT)}")
    print(f"   Equity: {account.calculated_balance(USDT)}")
    print(f"   Available: {account.balance(USDT)}")
    print(f"   Locked: {account.balance_locked(USDT)}")
    
    # Get positions
    positions = engine.trader.generate_positions()
    print(f"\n📍 Positions: {len(positions)}")
    
    for position in positions[:5]:  # Show first 5
        print(f"   {position.id}: {position.quantity} @ {position.avg_px_open} "
              f"(PnL: {position.realized_pnl})")
    
    # Get orders
    orders = engine.trader.generate_orders()
    print(f"\n📋 Orders: {len(orders)}")
    print(f"   Filled: {len([o for o in orders if o.is_closed])}")
    print(f"   Open: {len([o for o in orders if o.is_open])}")
    
    # Statistics
    stats = engine.trader.generate_order_fills_report()
    print(f"\n📈 Statistics:")
    if len(stats) > 0:
        print(f"   Total trades: {len(stats)}")
        print(stats.describe())
    else:
        print("   No completed trades")
    
    # Save results
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed reports
    account_report = engine.trader.generate_account_report(venue)
    positions_report = engine.trader.generate_positions_report()
    orders_report = engine.trader.generate_order_fills_report()
    
    account_file = output_dir / f"account_{symbol}_{timestamp}.csv"
    positions_file = output_dir / f"positions_{symbol}_{timestamp}.csv"
    orders_file = output_dir / f"orders_{symbol}_{timestamp}.csv"
    
    account_report.to_csv(account_file)
    positions_report.to_csv(positions_file)
    orders_report.to_csv(orders_file)
    
    print(f"\n💾 Results saved:")
    print(f"   {account_file}")
    print(f"   {positions_file}")
    print(f"   {orders_file}")
    
    print(f"\n✅ Backtest complete!")


def main():
    """Main entry point with argument parsing."""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Backtest with converted WinkingFace data"
    )
    parser.add_argument(
        "--symbol",
        default="BTC-USDT",
        help="Trading symbol (default: BTC-USDT)"
    )
    parser.add_argument(
        "--data",
        default="data/nautilus/BTC-USDT-1-MINUTE.parquet",
        help="Path to parquet data file"
    )
    parser.add_argument(
        "--start",
        default="2024-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        default=None,
        help="End date (YYYY-MM-DD, optional)"
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=100000.0,
        help="Starting balance in USDT"
    )
    parser.add_argument(
        "--fast",
        type=int,
        default=10,
        help="Fast EMA period"
    )
    parser.add_argument(
        "--slow",
        type=int,
        default=20,
        help="Slow EMA period"
    )
    parser.add_argument(
        "--size",
        type=float,
        default=0.01,
        help="Trade size in BTC"
    )
    
    args = parser.parse_args()
    
    run_backtest(
        symbol=args.symbol,
        data_file=args.data,
        start_date=args.start,
        end_date=args.end,
        start_balance=args.balance,
        fast_ema=args.fast,
        slow_ema=args.slow,
        trade_size=args.size,
    )


if __name__ == "__main__":
    main()
