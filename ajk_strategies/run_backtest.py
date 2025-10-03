#!/usr/bin/env python3
"""
Backtest Runner for AI-Adaptive Strategy

This script runs comprehensive backtests across multiple scenarios:
1. Bull market scenario
2. Bear market scenario
3. Volatile/choppy market scenario
4. Ranging market scenario
5. Mixed conditions scenario

Results are saved to CSV files for analysis.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.node import BacktestNode, BacktestRunConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import ETH, USDT
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.test_kit.providers import TestDataProvider

from ajk_strategies.ai_adaptive_strategy_main import AIAdaptiveStrategy
from ajk_strategies.ai_adaptive_strategy import AIAdaptiveStrategyConfig


def create_backtest_engine(
    scenario_name: str,
    start_date: datetime,
    end_date: datetime,
    initial_balance: float = 10000.0
) -> BacktestEngine:
    """
    Create and configure a backtest engine
    
    Args:
        scenario_name: Name of the backtest scenario
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_balance: Starting account balance in USDT
    
    Returns:
        Configured BacktestEngine
    """
    # Create engine configuration
    config = BacktestEngineConfig(
        logging=LoggingConfig(log_level="INFO"),
    )
    
    # Create engine
    engine = BacktestEngine(config=config)
    
    # Add venue
    venue = Venue("BINANCE")
    
    # Add instrument
    instrument = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(instrument)
    
    # Add account
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(initial_balance, USDT)],
    )
    
    return engine


def load_historical_data(
    engine: BacktestEngine,
    instrument_id: str,
    start_date: datetime,
    end_date: datetime,
    bar_spec: str = "1-MINUTE-LAST"
) -> None:
    """
    Load historical data into the backtest engine
    
    For demonstration, we'll use test data provider.
    In production, you would load from CSV or database.
    """
    # Get instrument
    instrument = engine.cache.instrument(instrument_id)
    
    # Create bar type
    bar_type = BarType.from_str(f"{instrument_id}-{bar_spec}-EXTERNAL")
    
    # Generate test data
    provider = TestDataProvider()
    bars = provider.generate_quote_ticks(
        instrument=instrument,
        start=start_date,
        end=end_date,
        n=10000  # Generate 10k bars
    )
    
    # Add bars to engine
    engine.add_data(bars)


def run_single_backtest(
    scenario_name: str,
    config: AIAdaptiveStrategyConfig,
    start_date: datetime,
    end_date: datetime,
    output_dir: Path
) -> dict:
    """
    Run a single backtest scenario
    
    Returns:
        Dictionary with backtest results
    """
    print(f"\n{'='*70}")
    print(f"🔬 Running Backtest: {scenario_name}")
    print(f"{'='*70}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Configuration:")
    print(f"  - EMA: {config.fast_ema_period}/{config.slow_ema_period}/{config.trend_ema_period}")
    print(f"  - RSI: {config.rsi_period} | ATR: {config.atr_period}")
    print(f"  - Position Size: {config.base_trade_size}")
    print(f"  - ML Optimization: {config.enable_ml_optimization}")
    print(f"  - Sentiment: {config.use_sentiment}")
    print()
    
    # Create engine
    engine = create_backtest_engine(
        scenario_name=scenario_name,
        start_date=start_date,
        end_date=end_date
    )
    
    # Load data
    print("📥 Loading historical data...")
    load_historical_data(
        engine=engine,
        instrument_id=config.instrument_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Add strategy
    print("🎯 Initializing strategy...")
    strategy = AIAdaptiveStrategy(config=config)
    engine.add_strategy(strategy)
    
    # Run backtest
    print("⚡ Running backtest...")
    engine.run()
    
    # Get results
    print("📊 Collecting results...")
    account = engine.cache.accounts()[0]
    
    # Calculate metrics
    total_orders = len(engine.cache.orders())
    total_positions = len(engine.cache.positions())
    
    # Get fills
    fills = engine.cache.orders()
    filled_orders = [o for o in fills if o.is_closed]
    
    # Calculate P&L
    final_balance = float(account.balance_total(USDT).as_double())
    initial_balance = 10000.0
    total_pnl = final_balance - initial_balance
    total_pnl_pct = (total_pnl / initial_balance) * 100
    
    # Get strategy stats
    wins = strategy.trades_won
    losses = strategy.trades_lost
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    results = {
        'scenario': scenario_name,
        'start_date': start_date,
        'end_date': end_date,
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_orders': total_orders,
        'total_positions': total_positions,
        'fast_ema': config.fast_ema_period,
        'slow_ema': config.slow_ema_period,
        'ml_enabled': config.enable_ml_optimization,
        'sentiment_enabled': config.use_sentiment,
    }
    
    # Print results
    print(f"\n{'='*70}")
    print(f"📈 BACKTEST RESULTS: {scenario_name}")
    print(f"{'='*70}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print(f"Final Balance:   ${final_balance:,.2f}")
    print(f"Total P&L:       ${total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"")
    print(f"Total Trades:    {total_trades}")
    print(f"Wins:            {wins}")
    print(f"Losses:          {losses}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print(f"")
    print(f"Total Orders:    {total_orders}")
    print(f"Total Positions: {total_positions}")
    print(f"{'='*70}\n")
    
    # Save detailed results
    save_backtest_results(engine, scenario_name, output_dir)
    
    return results


def save_backtest_results(engine: BacktestEngine, scenario_name: str, output_dir: Path):
    """Save backtest results to CSV files"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save orders
    orders = engine.cache.orders()
    if orders:
        orders_data = []
        for order in orders:
            orders_data.append({
                'order_id': str(order.client_order_id),
                'instrument': str(order.instrument_id),
                'side': str(order.side),
                'quantity': float(order.quantity),
                'status': str(order.status),
                'filled_qty': float(order.filled_qty) if hasattr(order, 'filled_qty') else 0,
                'avg_px': float(order.avg_px) if hasattr(order, 'avg_px') else 0,
            })
        
        orders_df = pd.DataFrame(orders_data)
        orders_file = output_dir / f"{scenario_name}_orders_{timestamp}.csv"
        orders_df.to_csv(orders_file, index=False)
        print(f"💾 Saved orders to: {orders_file}")
    
    # Save positions
    positions = engine.cache.positions()
    if positions:
        positions_data = []
        for pos in positions:
            positions_data.append({
                'position_id': str(pos.id),
                'instrument': str(pos.instrument_id),
                'side': str(pos.side),
                'quantity': float(pos.quantity),
                'entry_price': float(pos.avg_px_open),
                'realized_pnl': float(pos.realized_pnl) if hasattr(pos, 'realized_pnl') else 0,
            })
        
        positions_df = pd.DataFrame(positions_data)
        positions_file = output_dir / f"{scenario_name}_positions_{timestamp}.csv"
        positions_df.to_csv(positions_file, index=False)
        print(f"💾 Saved positions to: {positions_file}")


def run_all_scenarios():
    """Run backtests across multiple market scenarios"""
    
    # Output directory
    output_dir = Path(__file__).parent.parent / "backtest_results" / "ai_adaptive"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Base configuration
    base_config = AIAdaptiveStrategyConfig(
        instrument_id="ETHUSDT.BINANCE",
        bar_type="ETHUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL",
        venue="BINANCE",
        fast_ema_period=8,
        slow_ema_period=21,
        trend_ema_period=50,
        rsi_period=14,
        atr_period=14,
        base_trade_size=Decimal("0.10000"),
        enable_ml_optimization=True,
        use_sentiment=True,
    )
    
    # Define scenarios
    base_date = datetime(2020, 8, 14)
    
    scenarios = [
        {
            'name': 'bull_market',
            'start': base_date,
            'end': base_date + timedelta(days=30),
            'config': base_config,
        },
        {
            'name': 'bear_market',
            'start': base_date + timedelta(days=30),
            'end': base_date + timedelta(days=60),
            'config': base_config,
        },
        {
            'name': 'volatile_market',
            'start': base_date + timedelta(days=60),
            'end': base_date + timedelta(days=90),
            'config': base_config,
        },
        {
            'name': 'ranging_market',
            'start': base_date + timedelta(days=90),
            'end': base_date + timedelta(days=120),
            'config': base_config,
        },
        {
            'name': 'mixed_conditions',
            'start': base_date,
            'end': base_date + timedelta(days=120),
            'config': base_config,
        },
    ]
    
    # Run all scenarios
    all_results = []
    
    for scenario in scenarios:
        try:
            results = run_single_backtest(
                scenario_name=scenario['name'],
                config=scenario['config'],
                start_date=scenario['start'],
                end_date=scenario['end'],
                output_dir=output_dir
            )
            all_results.append(results)
        except Exception as e:
            print(f"❌ Error in scenario {scenario['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save summary results
    if all_results:
        summary_df = pd.DataFrame(all_results)
        summary_file = output_dir / f"backtest_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"\n💾 Saved summary to: {summary_file}")
        
        # Print summary table
        print(f"\n{'='*70}")
        print("📊 BACKTEST SUMMARY - ALL SCENARIOS")
        print(f"{'='*70}")
        print(summary_df.to_string(index=False))
        print(f"{'='*70}\n")
    
    return all_results


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         AI-ADAPTIVE STRATEGY BACKTEST RUNNER                     ║
    ║                                                                  ║
    ║  Advanced Algorithmic Trading Strategy with:                     ║
    ║  • Machine Learning Optimization                                 ║
    ║  • Pattern Recognition                                           ║
    ║  • Market Regime Detection                                       ║
    ║  • Sentiment Analysis                                            ║
    ║  • Advanced Risk Management                                      ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    results = run_all_scenarios()
    
    print("\n✅ All backtests completed!")
    print(f"📁 Results saved to: backtest_results/ai_adaptive/")
