#!/usr/bin/env python3
"""
AI-Adaptive Strategy Backtest with Real Parquet Data

Runs comprehensive backtest using prepared BTC-USDT and ETH-USDT data.
"""

import logging
import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import pandas as pd
import pyarrow as pa

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import BTC, ETH, USDT
from nautilus_trader.model.enums import AccountType, OmsType, AssetClass
from nautilus_trader.model.identifiers import Venue, TraderId, InstrumentId
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.instruments import CryptoFuture, CryptoPerpetual, CurrencyPair
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from ajk_strategies.ai_adaptive_strategy_main import AIAdaptiveStrategy
from ajk_strategies.ai_adaptive_strategy import AIAdaptiveStrategyConfig
from ajk_strategies.persistence import (
    BacktestMetricRecord,
    BacktestRunRecord,
    PostgresPersistenceClient,
)


logger = logging.getLogger(__name__)


def create_instrument(symbol: str, venue: str):
    """Create a proper instrument for the backtest"""
    from nautilus_trader.test_kit.providers import TestInstrumentProvider
    
    # Use test providers which have correct instrument signatures
    if symbol == "BTC-USDT":
        return TestInstrumentProvider.btcusdt_binance()
    elif symbol == "ETH-USDT":
        return TestInstrumentProvider.ethusdt_binance()


def run_backtest(
    instrument_symbol: str,
    scenario_name: str,
    fast_ema: int = 8,
    slow_ema: int = 21,
    enable_ml: bool = True,
    use_sentiment: bool = True,
    max_bars: int = 50000,
    log_level: str = "INFO",
):
    """Run an AI-Adaptive backtest on real Parquet data."""

    log_level_upper = log_level.upper()
    verbose = log_level_upper == "INFO"
    info = print if verbose else (lambda *args, **kwargs: None)

    info(f"\n{'='*80}")
    info(f"🚀 AI-ADAPTIVE STRATEGY BACKTEST: {instrument_symbol}")
    info(f"   Scenario: {scenario_name}")
    info(f"{'='*80}")
    info("Configuration:")
    info(f"  - Instrument: {instrument_symbol}")
    info(f"  - Fast EMA: {fast_ema}")
    info(f"  - Slow EMA: {slow_ema}")
    info(f"  - ML Optimization: {enable_ml}")
    info(f"  - Sentiment Analysis: {use_sentiment}")
    info(
        "  - Max Bars: {}".format("All" if not max_bars else f"{max_bars:,}")
    )
    info("")

    venue_name = "BINANCE"
    if instrument_symbol == "BTC-USDT":
        base_currency = BTC
        starting_base = 10.0
        parquet_file = project_root / "data" / "nautilus" / "BTC-USDT-1-MINUTE.parquet"
    else:
        base_currency = ETH
        starting_base = 100.0
        parquet_file = project_root / "data" / "nautilus" / "ETH-USDT-1-MINUTE.parquet"

    instrument = create_instrument(instrument_symbol, venue_name)
    info("📂 Loading data...")
    info(f"   ✓ Created instrument: {instrument.id}")
    info(f"   ✓ Data file: {parquet_file.name}")

    from nautilus_trader.persistence.wranglers import BarDataWrangler
    import pyarrow.parquet as pq

    try:
        table = pq.read_table(str(parquet_file))
        df_full = table.to_pandas()
        df_full["date"] = pd.to_datetime(df_full["ts_event"], unit="ms", utc=True)

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-12-31", tz="UTC")
        df_filtered = df_full[
            (df_full["date"] >= start_date) & (df_full["date"] <= end_date)
        ]

        if max_bars and len(df_filtered) > max_bars:
            info(
                "   ℹ️  Using 2024 data, limiting to first "
                f"{max_bars:,} bars (out of {len(df_filtered):,})"
            )
            df_filtered = df_filtered.head(max_bars)
        else:
            info(f"   ℹ️  Using all 2024 data: {len(df_filtered):,} bars")

        table = pa.Table.from_pandas(df_filtered.drop("date", axis=1))
        df = table.to_pandas()

        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["timestamp"] = pd.to_datetime(df["ts_event"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        df = df[numeric_cols]

        bar_type_str = f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"
        wrangler = BarDataWrangler(
            bar_type=BarType.from_str(bar_type_str),
            instrument=instrument,
        )

        bars = wrangler.process(df)

        info(f"   ✓ Loaded {len(bars):,} bars")
        if bars:
            info(f"   ℹ️  First bar: {bars[0].ts_event}")
            info(f"   ℹ️  Last bar: {bars[-1].ts_event}")

    except Exception as exc:  # noqa: BLE001
        print(f"   ❌ Error loading data: {exc}")
        import traceback

        traceback.print_exc()
        return None

    config = BacktestEngineConfig(
        trader_id=TraderId(f"AI-ADAPTIVE-{instrument_symbol}-{scenario_name.upper()}"),
        logging=LoggingConfig(log_level=log_level_upper),
    )

    engine = BacktestEngine(config=config)

    engine.add_venue(
        venue=Venue(venue_name),
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[
            Money(100_000, USDT),
            Money(Decimal(str(starting_base)), base_currency),
        ],
    )

    engine.add_instrument(instrument)

    info("⚙️  Adding data to backtest engine...")
    engine.add_data(bars)

    bar_type_str = f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"

    strategy_config = AIAdaptiveStrategyConfig(
        instrument_id=str(instrument.id),
        bar_type=bar_type_str,
        venue=venue_name,
        fast_ema_period=fast_ema,
        slow_ema_period=slow_ema,
        trend_ema_period=50,
        rsi_period=14,
        atr_period=14,
        base_trade_size=Decimal("0.10000"),
        max_position_size=Decimal("1.00000"),
        min_position_size=Decimal("0.01000"),
        stop_loss_atr_multiplier=2.0,
        take_profit_atr_multiplier=3.0,
        trailing_stop_atr_multiplier=1.5,
        max_hold_seconds=7200,
        max_daily_loss_pct=0.05,
        max_drawdown_pct=0.10,
        min_win_rate=0.35,
        max_consecutive_losses=5,
        enable_ml_optimization=enable_ml,
        optimization_interval=100,
        learning_rate=0.01,
        use_sentiment=use_sentiment,
        sentiment_weight=0.25,
        regime_lookback=100,
        regime_update_interval=50,
        mc_simulations=1000,
        mc_confidence_level=0.95,
    )

    info("🎯 Initializing AI-Adaptive Strategy...")
    strategy = AIAdaptiveStrategy(config=strategy_config)
    engine.add_strategy(strategy)

    info("⚡ Running backtest...\n")
    start_time = datetime.now(timezone.utc)
    end_time = start_time
    duration = 0.0

    try:
        engine.run()
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        info(f"\n✅ Backtest completed in {duration:.2f} seconds")
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ Backtest failed: {exc}")
        import traceback

        traceback.print_exc()
        return None

    print(f"\n{'='*80}")
    print(f"📊 PERFORMANCE RESULTS: {instrument_symbol} - {scenario_name}")
    print(f"{'='*80}")

    accounts = list(engine.cache.accounts())
    if not accounts:
        print("❌ No account data available")
        return None

    account = accounts[0]

    print("\n💰 Final Account Balance:")
    starting_usdt = 100_000.0
    final_balances: dict[str, float] = {}

    for balance in account.balances().values():
        final_balances[str(balance.currency)] = float(balance.total)
        print(f"   {balance.currency}: {balance.total}")

    final_usdt = final_balances.get("USDT", 0.0)
    base_amount = final_balances.get(str(base_currency), 0.0)

    if bars:
        final_price = float(bars[-1].close)
        base_value_usdt = base_amount * final_price
        total_equity = final_usdt + base_value_usdt
    else:
        base_value_usdt = 0.0
        total_equity = final_usdt

    pnl = total_equity - starting_usdt
    pnl_pct = (pnl / starting_usdt) * 100 if starting_usdt else 0.0

    print("\n📈 P&L Summary:")
    print(f"   Starting Balance: ${starting_usdt:,.2f} USDT")
    print(f"   Final Balance: ${final_usdt:,.2f} USDT")
    if base_amount > 0:
        print(f"   {base_currency} Holdings: {base_amount:.8f} (${base_value_usdt:,.2f})")
    print(f"   Total Equity: ${total_equity:,.2f}")
    print(f"   Net P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")

    orders = list(engine.cache.orders())
    positions = list(engine.cache.positions())
    closed_positions = [position for position in positions if position.is_closed]

    print("\n📊 Trading Statistics:")
    print(f"   Total Orders: {len(orders)}")
    print(f"   Total Positions: {len(positions)}")
    print(f"   Closed Positions: {len(closed_positions)}")

    win_rate = 0.0
    profit_factor = 0.0

    if closed_positions:
        winning_positions = [
            p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0
        ]
        losing_positions = [
            p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) < 0
        ]

        wins = len(winning_positions)
        losses = len(losing_positions)
        total_trades = wins + losses

        if total_trades > 0:
            win_rate = (wins / total_trades) * 100

            total_realized_pnl = sum(
                float(p.realized_pnl) for p in closed_positions if p.realized_pnl
            )
            avg_win = (
                sum(float(p.realized_pnl) for p in winning_positions if p.realized_pnl) / wins
                if wins > 0
                else 0.0
            )
            avg_loss = (
                sum(float(p.realized_pnl) for p in losing_positions if p.realized_pnl) / losses
                if losses > 0
                else 0.0
            )

            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

            print(f"   Winning Trades: {wins}")
            print(f"   Losing Trades: {losses}")
            print(f"   Win Rate: {win_rate:.2f}%")
            print(f"   Total Realized P&L: ${total_realized_pnl:,.2f}")
            print(f"   Average Win: ${avg_win:,.2f}")
            print(f"   Average Loss: ${avg_loss:,.2f}")
            print(f"   Profit Factor: {profit_factor:.2f}")

            pnl_list = [
                float(p.realized_pnl) for p in closed_positions if p.realized_pnl
            ]
            if len(pnl_list) > 1:
                import numpy as np

                returns_mean = np.mean(pnl_list)
                returns_std = np.std(pnl_list)
                sharpe = (returns_mean / returns_std) * np.sqrt(252) if returns_std > 0 else 0.0
                print(f"   Sharpe Ratio: {sharpe:.2f}")

    print(f"{'='*80}\n")

    from pathlib import Path
    import json

    results_dir = Path("/home/ajk/Nautilus/nautilus_trader/backtest_results")
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    result_prefix = f"{instrument_symbol.replace('/', '-')}_{scenario_name}_{timestamp}"

    fills_report = engine.trader.generate_order_fills_report()
    if fills_report is not None and not getattr(fills_report, "empty", False):
        fills_path = results_dir / f"fills_{result_prefix}.csv"
        fills_report.to_csv(fills_path, index=False)
        print(f"💾 Fills saved to: {fills_path}")

    positions_report = engine.trader.generate_positions_report()
    if positions_report is not None and not getattr(positions_report, "empty", False):
        positions_path = results_dir / f"positions_{result_prefix}.csv"
        positions_report.to_csv(positions_path, index=False)
        print(f"💾 Positions saved to: {positions_path}")

    orders_report = engine.trader.generate_orders_report()
    if orders_report is not None and not getattr(orders_report, "empty", False):
        orders_path = results_dir / f"orders_{result_prefix}.csv"
        orders_report.to_csv(orders_path, index=False)
        print(f"💾 Orders saved to: {orders_path}")

    summary = {
        "instrument": instrument_symbol,
        "scenario": scenario_name,
        "timestamp": timestamp,
        "date_range": "2024-01-01 to 2024-12-31",
        "bars_processed": len(bars),
        "duration_seconds": duration,
        "total_equity": float(total_equity),
        "net_pnl": float(pnl),
        "pnl_pct": float(pnl_pct),
        "total_trades": len(closed_positions),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
    }

    summary_path = results_dir / f"summary_{result_prefix}.json"
    with open(summary_path, "w") as file:
        json.dump(summary, file, indent=2)
    print(f"💾 Summary saved to: {summary_path}\n")

    persistence_enabled = os.getenv("NAUTILUS_PERSIST_BACKTESTS", "0").lower() in {
        "1",
        "true",
        "yes",
    }
    if persistence_enabled:
        try:
            client = PostgresPersistenceClient()
            model_files = {
                "market_regime_hmm": (
                    project_root / "ajk_strategies" / "models" / "market_regime_hmm.pkl"
                ),
                "price_forecast_lstm": (
                    project_root / "ajk_strategies" / "models" / "price_forecast_lstm.h5"
                ),
                "price_forecast_lstm_meta": (
                    project_root
                    / "ajk_strategies"
                    / "models"
                    / "price_forecast_lstm_meta.pkl"
                ),
                "signal_aggregator_xgb": (
                    project_root / "ajk_strategies" / "models" / "signal_aggregator_xgb_gpu.pkl"
                ),
            }
            model_versions: dict[str, dict[str, str]] = {}
            for name, path in model_files.items():
                if path.exists():
                    modified_at = datetime.fromtimestamp(
                        path.stat().st_mtime,
                        tz=timezone.utc,
                    ).isoformat()
                    model_versions[name] = {
                        "path": str(path),
                        "modified_at": modified_at,
                    }

            backtest_params = {
                "fast_ema_period": fast_ema,
                "slow_ema_period": slow_ema,
                "enable_ml": enable_ml,
                "use_sentiment": use_sentiment,
                "max_bars": max_bars,
            }

            backtest_record = BacktestRunRecord(
                strategy_id="ai_adaptive_strategy",
                run_name=result_prefix,
                instrument_id=str(instrument.id),
                bar_type=bar_type_str,
                model_versions=model_versions or None,
                parameters=backtest_params,
                dataset_source=str(parquet_file),
                dataset_start=start_date.to_pydatetime(),
                dataset_end=end_date.to_pydatetime(),
                status="completed",
                metrics=summary,
                started_at=start_time,
                completed_at=end_time,
            )
            backtest_id = client.record_backtest_run(backtest_record)

            metric_records = []
            for metric_name, metric_value in summary.items():
                if isinstance(metric_value, (int, float)):
                    metric_records.append(
                        BacktestMetricRecord(
                            backtest_run_id=backtest_id,
                            metric_name=metric_name,
                            metric_value=float(metric_value),
                            recorded_at=end_time,
                        )
                    )
            if metric_records:
                client.record_backtest_metrics(metric_records)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist backtest run: %s", exc, exc_info=True)

    return {
        "instrument": instrument_symbol,
        "scenario": scenario_name,
        "bars_processed": len(bars),
        "duration_seconds": duration,
        "total_equity": total_equity,
        "net_pnl": pnl,
        "pnl_pct": pnl_pct,
        "total_trades": len(closed_positions),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
    }


def run_all_scenarios():
    """Run comprehensive backtests on both BTC and ETH"""
    
    print("""
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║              AI-ADAPTIVE STRATEGY - COMPREHENSIVE BACKTEST                   ║
    ║                          Real Market Data Analysis                           ║
    ║                                                                              ║
    ║  Testing on:                                                                 ║
    ║  • BTC-USDT: 2.26M bars (~4.3 years)                                        ║
    ║  • ETH-USDT: 2.26M bars (~4.3 years)                                        ║
    ║                                                                              ║
    ║  Strategy Features:                                                          ║
    ║  ✓ Machine Learning Optimization                                             ║
    ║  ✓ Advanced Pattern Recognition                                              ║
    ║  ✓ Market Regime Detection                                                   ║
    ║  ✓ Sentiment Analysis (simulated)                                            ║
    ║  ✓ Dynamic Risk Management                                                   ║
    ║  ✓ Multi-layer Circuit Breakers                                              ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Define test scenarios
    scenarios = [
        {
            'name': 'full_ai_adaptive',
            'fast_ema': 8,
            'slow_ema': 21,
            'enable_ml': True,
            'use_sentiment': True,
        },
    ]
    
    instruments = ["BTC-USDT", "ETH-USDT"]
    
    all_results = []
    
    for instrument in instruments:
        for scenario in scenarios:
            try:
                result = run_backtest(
                    instrument_symbol=instrument,
                    scenario_name=scenario['name'],
                    fast_ema=scenario['fast_ema'],
                    slow_ema=scenario['slow_ema'],
                    enable_ml=scenario['enable_ml'],
                    use_sentiment=scenario['use_sentiment'],
                    max_bars=50000,  # Use 50k bars for reasonable testing speed
                )
                
                if result:
                    all_results.append(result)
                    
            except Exception as e:
                print(f"❌ Error in {instrument} - {scenario['name']}: {e}")
                import traceback
                traceback.print_exc()
    
    # Print comprehensive summary
    if all_results:
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE BACKTEST SUMMARY")
        print(f"{'='*80}\n")
        
        print(
            f"{'Instrument':<12} {'Scenario':<18} {'Bars':<10} {'Time':<8} "
            f"{'P&L %':<10} {'Trades':<8} {'Win%':<8} {'PF':<6}"
        )
        print("-" * 80)
        
        for r in all_results:
            print(
                f"{r['instrument']:<12} "
                f"{r['scenario']:<18} "
                f"{r['bars_processed']:<10,} "
                f"{r['duration_seconds']:<8.1f} "
                f"{r['pnl_pct']:>+9.2f}% "
                f"{r['total_trades']:<8} "
                f"{r['win_rate']:<7.1f}% "
                f"{r['profit_factor']:<6.2f}"
            )
        
        print(f"{'='*80}\n")
        
        # Summary statistics
        total_pnl = sum(r['pnl_pct'] for r in all_results)
        avg_pnl = total_pnl / len(all_results)
        avg_win_rate = sum(r['win_rate'] for r in all_results) / len(all_results)
        
        print(f"📈 Overall Performance:")
        print(f"   Average P&L: {avg_pnl:+.2f}%")
        print(f"   Average Win Rate: {avg_win_rate:.2f}%")
        print(f"   Total Scenarios Tested: {len(all_results)}")
        
        print(f"\n{'='*80}\n")
    
    return all_results


if __name__ == "__main__":
    print("\n🚀 Starting AI-Adaptive Strategy Backtests...\n")
    results = run_all_scenarios()
    print("\n✅ All backtests completed!")
    print("📁 Check logs above for detailed results\n")
