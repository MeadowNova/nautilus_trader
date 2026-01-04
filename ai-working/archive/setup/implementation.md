# Implementation Guide: Nautilus Trader Setup & Learning

## Context
- **Plan Reference**: `/home/ajk/Nautilus/nautilus_trader/ai-working/setup/plan.md`
- **Research Notes**: `/home/ajk/Nautilus/nautilus_trader/ai-working/setup/research/nautilus_ccxt_research.md`
- **Objective**: Master Nautilus Trader for algorithmic trading with AI-driven adaptive strategies

**Last Updated**: October 2, 2025  
**Current Phase**: Phase 3 - Learning & Strategy Development

---

## Phase 1: Research & Understanding ✅ COMPLETE
- [x] Read Nautilus Trader documentation
- [x] Understand architecture (Rust core + Python interface)
- [x] Study existing adapter patterns
- [x] Review CCXT integration history
- [x] Create comprehensive research document

**Completion Date**: October 2, 2025

---

## Phase 2: Environment Setup ✅ COMPLETE
- [x] Install Rust toolchain (1.90.0)
- [x] Install Clang compiler (18.1.3)
- [x] Install uv package manager (already present)
- [x] Build NautilusTrader from source
- [x] Create environment activation script
- [x] Verify installation with first backtest

**Completion Date**: October 2, 2025

---

## Phase 3: Learning & Strategy Development 🔄 IN PROGRESS
### Step 1: Initial Backtesting (✅ Complete)
- **Action**: Run first backtest to understand workflow
- **Files**: `examples/backtest/crypto_ema_cross_ethusdt_trade_ticks.py`
- **Expected Outcome**: Successfully execute backtest and view results
- **Status**: Complete - 15 trades executed on ETH/USDT
- **Learnings**: 
  - Mostly losses, strategy needs optimization
  - Understanding of backtest workflow achieved
  - Results saved to `backtest_results/`

### Step 2: Enhanced Analytics (✅ Complete)
- **Action**: Create detailed performance analysis script
- **Files**: `examples/backtest/crypto_ema_cross_ethusdt_detailed_analysis.py`
- **Expected Outcome**: Comprehensive metrics (win rate, Sharpe, drawdown, P&L)
- **Status**: Complete with fixes
- **Issues Resolved**:
  - ATR indicator import path corrected
  - Balance object attribute access fixed (`.total.currency`)
  - Multiple import adjustments for NautilusTrader API
- **Learnings**: Full performance metrics for strategy evaluation

### Step 3: AI Adaptive Strategy Demo (✅ Complete)
- **Action**: Build self-correcting strategy with adaptive parameters
- **Files**: `examples/backtest/adaptive_strategy_demo.py`
- **Expected Outcome**: Strategy that adjusts EMA periods based on volatility
- **Status**: Complete with multiple fixes
- **Issues Resolved**:
  1. Import paths: `nautilus_trader.indicators.averages` (not `.average.ema`)
  2. Removed ATR indicator complexity, replaced with price change volatility
  3. Fixed `OrderSide` enum usage (must use `OrderSide.BUY`, not `"BUY"`)
  4. Fixed `Quantity` type (must use `Quantity.from_str(str(value))`)
- **Results**: 
  - 139 orders generated
  - 0 closed positions (no exit signals during uptrend)
  - Successfully demonstrates adaptive parameter adjustment
- **Key Learning**: Pure EMA crossover needs additional exit conditions:
  - Time-based stops
  - Profit targets
  - Trailing stops

### Step 4: Reddit Sentiment Analysis (✅ Complete)
- **Action**: Test Reddit scraper for crypto sentiment analysis
- **Files**: 
  - `docs/algorithms/reddit.py` (existing)
  - `test_reddit_sentiment.py` (created)
- **Expected Outcome**: Gather sentiment from crypto subreddits
- **Status**: Complete - Successfully tested with 3 subreddits
- **Dependencies**: Installed `httpx` library
- **Results**:
  - **r/CryptoCurrency**: 25 posts, avg 141.6 score, NEUTRAL, BTC most mentioned
  - **r/Bitcoin**: 25 posts, avg 384.2 score, NEUTRAL, high engagement
  - **r/ethereum**: 25 posts, avg 45.3 score, slightly BULLISH (0.11)
- **Capabilities**:
  - Multi-subreddit analysis
  - Sentiment scoring (bullish/bearish keywords)
  - Coin mention tracking (BTC, ETH, SOL, etc.)
  - Engagement metrics (scores, upvote ratios)
  - Trading signal generation
- **Limitations**:
  - Rate limits (~60 requests/minute)
  - No historical data
  - Basic keyword sentiment (not NLP)
  - Lags price action
- **Best Use**: Supplementary signal for position sizing, not primary strategy

### Step 5: Exit Condition Implementation (📋 Planned)
- **Action**: Add proper exit logic to adaptive strategy
- **Files**: `examples/backtest/adaptive_strategy_demo.py`
- **Expected Outcome**: Strategy generates closed positions and complete statistics
- **Planned Changes**:
  1. Time-based exits (max 30-minute hold)
  2. Profit target exits (1-2% gain)
  3. Trailing stop losses
  4. Test with shorter EMA periods (5/10 vs 10/20)
- **Success Criteria**:
  - At least 10 closed positions
  - Statistics calculated (no more "nan")
  - Positive or breakeven results

### Step 6: Sentiment Integration (📋 Planned)
- **Action**: Integrate Reddit sentiment into trading strategy
- **Files**: New Actor component + modified strategy
- **Expected Outcome**: Position sizing adjusts based on sentiment
- **Planned Components**:
  1. `RedditSentimentActor` - Polls Reddit every 5-10 minutes
  2. Custom `SentimentData` message type
  3. Strategy subscribes to sentiment updates
  4. Position size = base_size × sentiment_multiplier
- **Example Logic**:
  - Bullish (>0.3): 1.2x position size
  - Neutral (±0.2): 1.0x position size
  - Bearish (<-0.3): 0.5x position size or skip trade

---

## Phase 3: Verification
- [ ] Runs tests
- [ ] Confirm criteria from plan.md are satisfied
- [ ] Cross-reference with AGENTS.md or system prompts

---

## Status Compaction (running log)
- **Progress**:  
  - Done: Step 4 Celery awaitable integration implemented with eager-mode validation.  
  - In Progress: Step 5 telemetry settings centralized and Alembic wiring validated via `alembic heads`.  
  - Issues: Offline migration generation fails due to data-dependent scripts; full worker runtime validation deferred until broker available; need decision on ScoreImprovement endpoint revival timing.  
- **Next Steps**:  
  1. Capture follow-up plan for handling migrations requiring live Supabase data before executing dry-run (likely seed fixtures or run against staging Supabase where `reconstruction_jobs` exists).  
  2. Enumerate prerequisites for Step 6 verification (pytest, Celery worker, telemetry toggle) and queue execution once environment access is confirmed.

---

## Notes
- If mismatches arise, log them here in the format:

