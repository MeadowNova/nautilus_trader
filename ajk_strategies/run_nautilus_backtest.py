#!/usr/bin/env python3
"""
NautilusTrader Backtest Runner for AI-Adaptive Strategy

This script properly uses NautilusTrader's backtest engine to test
the AI-adaptive strategy with real market data.
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import ETH, USDT
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue, TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider

from ajk_strategies.ai_adaptive_strategy_main import AIAdaptiveStrategy
from ajk_strategies.ai_adaptive_strategy import AIAdaptiveStrategyConfig


def run_backtest_scenario(
    scenario_name: str,
    fast_ema: int = 8,
    slow_ema: int = 21,
    enable_ml: bool = True,
    use_sentiment: bool = True
):
    """
    Run a single backtest scenario
    
    Args:
        scenario_name: Name of the scenario
        fast_ema: Fast EMA period
        slow_ema: Slow EMA period
        enable_ml: Enable ML optimization
        use_sentiment: Use sentiment analysis
    """
    print(f"\n{'='*70}")
    print(f"🔬 BACKTEST SCENARIO: {scenario_name}")
    print(f"{'='*70}")
    print(f"Configuration:")
    print(f"  - Fast EMA: {fast_ema}")
    print(f"  - Slow EMA: {slow_ema}")
    print(f"  - ML Optimization: {enable_ml}")
    print(f"  - Sentiment Analysis: {use_sentiment}")
    print()
    
    # Configure backtest engine
    config = BacktestEngineConfig(
        trader_id=TraderId(f"AI-ADAPTIVE-{scenario_name.upper()}"),
        logging=LoggingConfig(log_level="INFO"),
    )
    
    # Create engine
    engine = BacktestEngine(config=config)
    
    # Add venue
    BINANCE = Venue("BINANCE")
    engine.add_venue(
        venue=BINANCE,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(1_000_000, USDT), Money(10, ETH)],
    )
    
    # Load instrument
    ETHUSDT_BINANCE = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(ETHUSDT_BINANCE)
    
    # Load data
    print("📥 Loading market data...")
    provider = TestDataProvider()
    wrangler = TradeTickDataWrangler(instrument=ETHUSDT_BINANCE)
    
    try:
        ticks = wrangler.process(provider.read_csv_ticks("binance/ethusdt-trades.csv"))
        engine.add_data(ticks)
        print(f"   ✓ Loaded {len(ticks)} trade ticks")
    except Exception as e:
        print(f"   ⚠️  Could not load CSV data: {e}")
        print("   ℹ️  Using synthetic data instead...")
        # Generate synthetic data if CSV not available
        from nautilus_trader.test_kit.providers import TestDataProvider
        provider = TestDataProvider()
        bars = provider.generate_quote_ticks(
            instrument=ETHUSDT_BINANCE,
            n=10000
        )
        engine.add_data(bars)
        print(f"   ✓ Generated {len(bars)} synthetic ticks")
    
    # Configure strategy
    strategy_config = AIAdaptiveStrategyConfig(
        instrument_id=str(ETHUSDT_BINANCE.id),
        bar_type="ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL",
        venue="BINANCE",
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
        max_hold_seconds=3600,
        max_daily_loss_pct=0.05,
        max_drawdown_pct=0.10,
        min_win_rate=0.35,
        max_consecutive_losses=5,
        enable_ml_optimization=enable_ml,
        optimization_interval=50,
        learning_rate=0.01,
        use_sentiment=use_sentiment,
        sentiment_weight=0.25,
        regime_lookback=100,
        regime_update_interval=20,
        mc_simulations=1000,
        mc_confidence_level=0.95,
    )
    
    # Add strategy
    print("🎯 Initializing AI-Adaptive Strategy...")
    strategy = AIAdaptiveStrategy(config=strategy_config)
    engine.add_strategy(strategy)
    
    # Run backtest
    print("⚡ Running backtest...\n")
    engine.run()
    
    # Get results
    print(f"\n{'='*70}")
    print(f"📊 RESULTS: {scenario_name}")
    print(f"{'='*70}")
    
    # Get account info
    account = list(engine.cache.accounts())[0]
    print(f"\n💰 Account Balance:")
    for balance in account.balances().values():
        print(f"   {balance.currency}: {balance.total}")
    
    # Get order stats
    orders = engine.cache.orders()
    positions = engine.cache.positions()
    
    print(f"\n📈 Trading Statistics:")
    print(f"   Total Orders: {len(orders)}")
    print(f"   Total Positions: {len(positions)}")
    
    # Calculate P&L
    closed_positions = [p for p in positions if p.is_closed]
    if closed_positions:
        total_pnl = sum(float(p.realized_pnl) for p in closed_positions if p.realized_pnl)
        winning_positions = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0]
        win_rate = len(winning_positions) / len(closed_positions) * 100
        
        print(f"   Closed Positions: {len(closed_positions)}")
        print(f"   Winning Positions: {len(winning_positions)}")
        print(f"   Win Rate: {win_rate:.2f}%")
        print(f"   Total Realized P&L: {total_pnl:.2f}")
    
    print(f"{'='*70}\n")
    
    return {
        'scenario': scenario_name,
        'orders': len(orders),
        'positions': len(positions),
        'closed_positions': len(closed_positions) if closed_positions else 0,
        'win_rate': win_rate if closed_positions else 0,
    }


def run_all_scenarios():
    """Run multiple backtest scenarios"""
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         AI-ADAPTIVE STRATEGY - NAUTILUS BACKTEST                 ║
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
    
    scenarios = [
        {
            'name': 'baseline',
            'fast_ema': 8,
            'slow_ema': 21,
            'enable_ml': False,
            'use_sentiment': False,
        },
        {
            'name': 'with_ml',
            'fast_ema': 8,
            'slow_ema': 21,
            'enable_ml': True,
            'use_sentiment': False,
        },
        {
            'name': 'with_sentiment',
            'fast_ema': 8,
            'slow_ema': 21,
            'enable_ml': False,
            'use_sentiment': True,
        },
        {
            'name': 'full_ai_adaptive',
            'fast_ema': 8,
            'slow_ema': 21,
            'enable_ml': True,
            'use_sentiment': True,
        },
        {
            'name': 'aggressive',
            'fast_ema': 5,
            'slow_ema': 15,
            'enable_ml': True,
            'use_sentiment': True,
        },
        {
            'name': 'conservative',
            'fast_ema': 12,
            'slow_ema': 26,
            'enable_ml': True,
            'use_sentiment': True,
        },
    ]
    
    results = []
    
    for scenario in scenarios:
        try:
            result = run_backtest_scenario(
                scenario_name=scenario['name'],
                fast_ema=scenario['fast_ema'],
                slow_ema=scenario['slow_ema'],
                enable_ml=scenario['enable_ml'],
                use_sentiment=scenario['use_sentiment'],
            )
            results.append(result)
        except Exception as e:
            print(f"❌ Error in scenario {scenario['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    if results:
        print(f"\n{'='*70}")
        print("📊 BACKTEST SUMMARY - ALL SCENARIOS")
        print(f"{'='*70}")
        
        print(f"\n{'Scenario':<20} {'Orders':<10} {'Positions':<12} {'Closed':<10} {'Win Rate':<10}")
        print("-" * 70)
        for r in results:
            print(f"{r['scenario']:<20} {r['orders']:<10} {r['positions']:<12} {r['closed_positions']:<10} {r['win_rate']:<10.2f}%")
        
        print(f"{'='*70}\n")
    
    return results


if __name__ == "__main__":
    results = run_all_scenarios()
    
    print("\n✅ All backtests completed!")
    print(f"📁 Check NautilusTrader logs for detailed results")
