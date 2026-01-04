#!/usr/bin/env python3
"""
Quick Backtest with PostgreSQL Persistence

This script runs a fast backtest (50k bars) and persists results to PostgreSQL
for Prometheus/Grafana monitoring.

Based on the V3 GPU validation script but adds database persistence.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import pandas as pd
import pyarrow.parquet as pq

# Set environment for persistence
os.environ["NAUTILUS_PERSIST_BACKTESTS"] = "1"

# Add project to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from ajk_strategies.ai_adaptive_stragey_v3 import (
    AIAdaptiveStrategyConfigV3,
    AIAdaptiveStrategyV3,
)
from ajk_strategies.persistence import (
    BacktestMetricRecord,
    BacktestRunRecord,
    PostgresPersistenceClient,
)


def run_quick_backtest():
    print("\n" + "="*70)
    print("  QUICK BACKTEST WITH DATABASE PERSISTENCE")
    print("="*70)
    
    # Configuration
    instrument_symbol = "BTC-USDT"
    max_bars = 50_000
    venue_name = "BINANCE"
    
    print(f"\n📊 Configuration:")
    print(f"   Instrument: {instrument_symbol}")
    print(f"   Max Bars: {max_bars:,}")
    print(f"   Persistence: ENABLED")
    print(f"   Database: localhost:5435/nautilus_trader")
    
    # Create instrument
    instrument = TestInstrumentProvider.btcusdt_binance()
    
    # Load data
    print(f"\n📂 Loading data...")
    data_path = project_root / "data" / "nautilus" / f"{instrument_symbol}-1-MINUTE.parquet"
    
    table = pq.read_table(str(data_path))
    df = table.to_pandas()
    df["timestamp"] = pd.to_datetime(df["ts_event"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    
    # Filter to 2024 data
    start_date = pd.Timestamp("2024-01-01", tz="UTC")
    end_date = pd.Timestamp("2024-12-31", tz="UTC")
    df = df[(df.index >= start_date) & (df.index <= end_date)]
    
    # Limit bars
    if len(df) > max_bars:
        df = df.head(max_bars)
    
    print(f"   ✓ Loaded {len(df):,} bars from 2024")
    print(f"   ✓ Date range: {df.index[0]} to {df.index[-1]}")
    
    # Convert to bars
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    
    bar_type_str = f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"
    wrangler = BarDataWrangler(
        bar_type=BarType.from_str(bar_type_str),
        instrument=instrument,
    )
    bars = wrangler.process(df)
    
    # Create backtest engine
    config = BacktestEngineConfig(
        trader_id=TraderId(f"METRICS-TEST-{instrument_symbol}"),
        logging=LoggingConfig(log_level="ERROR"),  # Quiet mode
    )
    
    engine = BacktestEngine(config=config)
    
    # Add venue
    engine.add_venue(
        venue=Venue(venue_name),
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[
            Money(100_000, USDT),
            Money(Decimal("10.0"), BTC),
        ],
    )
    
    engine.add_instrument(instrument)
    engine.add_data(bars)
    
    # Create strategy
    strategy_config = AIAdaptiveStrategyConfigV3(
        instrument_id=str(instrument.id),
        bar_type=bar_type_str,
        venue=venue_name,
        max_bars_per_run=max_bars,
        enable_monte_carlo=False,  # Disabled for speed
        confidence_threshold=0.75,
    )
    
    strategy = AIAdaptiveStrategyV3(config=strategy_config)
    engine.add_strategy(strategy)
    
    # Run backtest
    print(f"\n⚡ Running backtest...")
    start_time = datetime.now(timezone.utc)
    engine.run()
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    print(f"   ✓ Completed in {duration:.2f} seconds")
    
    # Get results
    accounts = list(engine.cache.accounts())
    if not accounts:
        print("   ❌ No account data")
        return
    
    account = accounts[0]
    positions = list(engine.cache.positions())
    closed_positions = [p for p in positions if p.is_closed]
    
    # Calculate metrics
    starting_usdt = 100_000.0
    final_balances = {str(b.currency): float(b.total) for b in account.balances().values()}
    final_usdt = final_balances.get("USDT", 0.0)
    btc_amount = final_balances.get("BTC", 0.0)
    
    if bars:
        final_price = float(bars[-1].close)
        btc_value_usdt = btc_amount * final_price
        total_equity = final_usdt + btc_value_usdt
    else:
        total_equity = final_usdt
    
    net_pnl = total_equity - starting_usdt
    pnl_pct = (net_pnl / starting_usdt) * 100
    
    # Calculate win rate
    win_rate = 0.0
    profit_factor = 0.0
    sharpe_ratio = 0.0
    
    if closed_positions:
        winning = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0]
        losing = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) < 0]
        
        wins = len(winning)
        losses = len(losing)
        total_trades = wins + losses
        
        if total_trades > 0:
            win_rate = (wins / total_trades) * 100
            
            total_wins = sum(float(p.realized_pnl) for p in winning if p.realized_pnl)
            total_losses = abs(sum(float(p.realized_pnl) for p in losing if p.realized_pnl))
            
            if total_losses > 0:
                profit_factor = total_wins / total_losses
    
    print(f"\n📊 Results:")
    print(f"   Total Equity: ${total_equity:,.2f}")
    print(f"   Net P&L: ${net_pnl:,.2f} ({pnl_pct:+.2f}%)")
    print(f"   Total Trades: {len(closed_positions)}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    
    # Persist to database
    print(f"\n💾 Persisting to database...")
    
    try:
        client = PostgresPersistenceClient(
            host="localhost",
            port=5435,
            database="nautilus_trader",
            user="nautilus",
            password="xSr7IgOZlwgkUwtnBBZoFG7N",
        )
        
        # Create run record
        run_name = f"metrics_test_{instrument_symbol}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        backtest_record = BacktestRunRecord(
            strategy_id="ai_adaptive_v3",
            run_name=run_name,
            instrument_id=str(instrument.id),
            bar_type=bar_type_str,
            model_versions={
                "xgboost": "gpu_accelerated",
                "monte_carlo": "disabled",
            },
            parameters={
                "max_bars": max_bars,
                "confidence_threshold": 0.75,
                "enable_monte_carlo": False,
            },
            dataset_source=str(data_path),
            dataset_start=df.index[0].to_pydatetime(),
            dataset_end=df.index[-1].to_pydatetime(),
            status="completed",
            metrics={
                "bars_processed": len(df),
                "duration_seconds": duration,
                "total_equity": total_equity,
                "net_pnl": net_pnl,
                "pnl_pct": pnl_pct,
                "total_trades": len(closed_positions),
                "win_rate": win_rate,
                "profit_factor": profit_factor,
            },
            started_at=start_time,
            completed_at=end_time,
        )
        
        backtest_id = client.record_backtest_run(backtest_record)
        print(f"   ✓ Backtest run recorded: {backtest_id}")
        
        # Record individual metrics
        metrics = [
            BacktestMetricRecord(backtest_id, "bars_processed", float(len(df)), recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "duration_seconds", duration, recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "total_equity", total_equity, recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "net_pnl", net_pnl, recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "pnl_pct", pnl_pct, recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "total_trades", float(len(closed_positions)), recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "win_rate", win_rate, recorded_at=end_time),
            BacktestMetricRecord(backtest_id, "profit_factor", profit_factor, recorded_at=end_time),
        ]
        
        client.record_backtest_metrics(metrics)
        print(f"   ✓ Recorded {len(metrics)} metrics")
        
        print(f"\n✅ Database persistence complete!")
        print(f"\n📊 Next steps:")
        print(f"   1. Metrics collector will pick up data automatically")
        print(f"   2. Check Prometheus: curl http://localhost:9100/metrics | grep ai_backtest")
        print(f"   3. View in Grafana: http://localhost:3000")
        
    except Exception as e:
        print(f"   ❌ Error persisting to database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_quick_backtest()
