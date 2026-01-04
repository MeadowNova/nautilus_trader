# Nautilus Trader Backtest Tutorials Guide

**Created:** January 2025  
**Purpose:** Progressive learning path from simple EMA strategies to advanced AI-adaptive trading

---

## 📚 Tutorial Overview

This tutorial series teaches you algorithmic trading with Nautilus Trader, starting from basics and progressively building to advanced AI-driven strategies.

### Tutorial Progression

```
Tutorial 1: Simple EMA Cross ←── START HERE
    ↓
Tutorial 2: Enhanced Indicators
    ↓
Tutorial 3: AI-Adaptive Strategy
    ↓
Tutorial 4: Reddit Sentiment Integration
    ↓
Tutorial 5: Full Production System
```

---

## 📖 Tutorial 1: Simple EMA Cross Backtest

**File:** `tutorial_01_simple_ema_backtest.py`  
**Difficulty:** Beginner  
**Time:** 30-45 minutes  

### What You'll Learn

1. **Data Download with CCXT**
   - Connect to Kraken exchange
   - Download historical OHLCV data
   - Handle rate limiting and errors

2. **Nautilus Setup**
   - Configure backtest engine
   - Set up trading venue
   - Create instrument definitions

3. **Simple Strategy**
   - EMA crossover logic
   - Buy/sell signal generation
   - Position sizing basics

4. **Result Analysis**
   - Calculate win rate
   - Compute profit/loss
   - Generate performance reports

### Running the Tutorial

```bash
cd /home/ajk/Nautilus/nautilus_trader/tutorials
python3 tutorial_01_simple_ema_backtest.py
```

### Expected Output

```
📥 DOWNLOADING DATA FROM KRAKEN
   ✅ Downloaded 720 bars total (30 days of hourly data)

🔧 PREPARING DATA FOR NAUTILUS
   ✅ Created 720 Nautilus bars

⚙️ SETTING UP BACKTEST ENGINE
   🏦 Venue: KRAKEN
   Starting Balance: $100,000.00

🎯 CREATING EMA CROSSOVER STRATEGY
   Fast EMA: 10 periods
   Slow EMA: 20 periods

⚡ RUNNING BACKTEST
   🚀 Starting backtest...
   ✅ Backtest complete!

📊 BACKTEST RESULTS
   Total Orders: XX
   Closed Positions: XX
   Win Rate: XX.X%
   Total P&L: $X,XXX.XX

🎉 TUTORIAL COMPLETE!
```

### Key Concepts Covered

#### 1. CCXT Integration
```python
# Download data from exchange
exchange = ccxt.kraken()
ohlcv = exchange.fetch_ohlcv('ETH/USD', '1h')
```

**Learning Points:**
- How to connect to exchanges
- OHLCV data format
- Timestamp handling (milliseconds vs nanoseconds)

#### 2. Data Wrangling
```python
# Convert to Nautilus format
wrangler = BarDataWrangler(bar_type, instrument)
bars = wrangler.process(df)
```

**Learning Points:**
- Nautilus data types (Bar, BarType)
- Data validation and cleaning
- Time series handling

#### 3. Backtest Engine
```python
# Configure and run
engine = BacktestEngine(config)
engine.add_venue(venue)
engine.add_instrument(instrument)
engine.add_data(bars)
engine.run()
```

**Learning Points:**
- Engine configuration
- Venue and account setup
- Strategy injection
- Execution flow

#### 4. Strategy Logic
```python
# EMA crossover
if fast_ema > slow_ema:
    # Bullish signal - buy
elif fast_ema < slow_ema:
    # Bearish signal - sell
```

**Learning Points:**
- Indicator calculation
- Signal generation
- Order submission
- Position management

### Exercises

After completing the tutorial, try these modifications:

**Exercise 1: Parameter Tuning**
```python
# Change EMA periods
fast_period = 5   # Try: 5, 8, 12
slow_period = 15  # Try: 15, 21, 26
```

**Exercise 2: Different Timeframes**
```python
# Change candle timeframe
timeframe = '4h'  # Try: 1h, 4h, 1d
```

**Exercise 3: Different Pairs**
```python
# Test other trading pairs
symbol = 'BTC/USD'  # Try: BTC/USD, SOL/USD
```

**Exercise 4: Position Sizing**
```python
# Adjust trade size
trade_size = Decimal("0.5")  # Try: 0.05, 0.1, 0.5
```

### Common Issues and Solutions

**Issue 1: "No closed positions"**
```
Cause: EMA periods too slow or insufficient data
Solution: Use faster EMAs (5/10) or download more data
```

**Issue 2: "CCXT rate limit exceeded"**
```
Cause: Too many API requests too quickly
Solution: Enable rate limiting: enableRateLimit=True
```

**Issue 3: "Instrument not found"**
```
Cause: Symbol format mismatch
Solution: Use exchange-specific format (ETH/USD for Kraken)
```

**Issue 4: "Data alignment errors"**
```
Cause: Timestamp inconsistencies
Solution: Sort data by timestamp before processing
```

### Success Criteria

By the end of Tutorial 1, you should be able to:

- ✅ Download data from any CCXT exchange
- ✅ Convert data to Nautilus format
- ✅ Set up and run a backtest
- ✅ Analyze basic performance metrics
- ✅ Modify strategy parameters
- ✅ Interpret backtest results

---

## 📖 Tutorial 2: Enhanced Indicators (Coming Soon)

**File:** `tutorial_02_enhanced_indicators.py`  
**Difficulty:** Intermediate  
**Time:** 45-60 minutes

### What You'll Learn

1. Multiple indicators (EMA, RSI, ATR)
2. Combined signal logic
3. Risk management (stop loss, take profit)
4. Performance optimization
5. Parameter sensitivity analysis

### Preview

```python
# Multiple indicators
fast_ema = ExponentialMovingAverage(10)
slow_ema = ExponentialMovingAverage(20)
rsi = RelativeStrengthIndex(14)
atr = AverageTrueRange(14)

# Combined logic
if (fast_ema > slow_ema and 
    rsi < 70 and 
    rsi > 30):
    # Enter trade with ATR-based stop
```

---

## 📖 Tutorial 3: AI-Adaptive Strategy (Coming Soon)

**File:** `tutorial_03_ai_adaptive_strategy.py`  
**Difficulty:** Advanced  
**Time:** 60-90 minutes

### What You'll Learn

1. ML-based parameter optimization
2. Pattern recognition
3. Market regime detection
4. Adaptive position sizing
5. Walk-forward optimization

### Preview

```python
# AI components
optimizer = MultiLayerOptimizer(learning_rate=0.01)
pattern_detector = AdvancedPatternDetector()
regime_detector = MarketRegimeDetector()

# Adaptive strategy
strategy = AIAdaptiveStrategy(
    optimizer=optimizer,
    pattern_detector=pattern_detector,
    regime_detector=regime_detector,
)
```

---

## 📖 Tutorial 4: Sentiment Integration (Coming Soon)

**File:** `tutorial_04_reddit_sentiment.py`  
**Difficulty:** Advanced  
**Time:** 60-90 minutes

### What You'll Learn

1. Reddit API integration
2. Sentiment analysis
3. Multi-source signal aggregation
4. Sentiment-based position sizing
5. Backtesting with external data

---

## 📖 Tutorial 5: Production System (Coming Soon)

**File:** `tutorial_05_production_system.py`  
**Difficulty:** Expert  
**Time:** 2-3 hours

### What You'll Learn

1. Live trading setup
2. Risk management systems
3. Monitoring and alerting
4. Performance tracking
5. Production deployment

---

## 🛠️ Quick Reference

### Essential Commands

```bash
# Run a tutorial
python3 tutorial_01_simple_ema_backtest.py

# Run with custom parameters (edit the file first)
python3 tutorial_01_simple_ema_backtest.py

# View results
cd tutorial_results
ls -lh
```

### Data Locations

```
tutorials/
├── tutorial_01_simple_ema_backtest.py
├── tutorial_02_enhanced_indicators.py
├── tutorial_03_ai_adaptive_strategy.py
├── tutorial_04_reddit_sentiment.py
├── tutorial_05_production_system.py
├── TUTORIALS_GUIDE.md (this file)
└── tutorial_results/
    ├── orders_20250104_120000.csv
    └── positions_20250104_120000.csv
```

### Performance Metrics Explained

**Win Rate**
```
Win Rate = (Winning Trades / Total Trades) × 100%

Good: > 50%
Excellent: > 60%
```

**Profit Factor**
```
Profit Factor = Total Profits / Total Losses

Break-even: 1.0
Good: > 1.5
Excellent: > 2.0
```

**Sharpe Ratio**
```
Sharpe = (Returns - Risk-Free Rate) / Volatility

Good: > 1.0
Excellent: > 2.0
Outstanding: > 3.0
```

**Max Drawdown**
```
Max Drawdown = Largest peak-to-trough decline

Good: < 20%
Excellent: < 10%
```

---

## 🎯 Learning Path Recommendations

### Week 1: Fundamentals
- Day 1-2: Tutorial 1 (EMA Cross)
- Day 3-4: Exercises and parameter tuning
- Day 5: Different markets and timeframes
- Day 6-7: Review and documentation

### Week 2: Enhancement
- Day 8-10: Tutorial 2 (Enhanced Indicators)
- Day 11-12: Risk management implementation
- Day 13-14: Performance optimization

### Week 3: Advanced AI
- Day 15-17: Tutorial 3 (AI-Adaptive)
- Day 18-19: ML optimization testing
- Day 20-21: Pattern recognition validation

### Week 4: Integration & Production
- Day 22-24: Tutorial 4 (Sentiment)
- Day 25-27: Tutorial 5 (Production)
- Day 28: Final review and deployment

---

## 📊 Expected Learning Outcomes

### After Tutorial 1
- Basic backtest proficiency
- Understanding of EMA strategies
- Ability to analyze results
- Confidence with Nautilus basics

### After Tutorial 2
- Multi-indicator strategies
- Advanced risk management
- Performance optimization skills
- Statistical analysis ability

### After Tutorial 3
- ML-based trading systems
- Adaptive strategies
- Advanced pattern recognition
- Regime-based trading

### After Tutorial 4
- External data integration
- Sentiment analysis
- Multi-source strategies
- Real-world data handling

### After Tutorial 5
- Production-ready systems
- Live trading capability
- Risk monitoring
- Professional deployment

---

## 🆘 Getting Help

### Documentation
- Nautilus Docs: https://nautilustrader.io/docs/
- CCXT Docs: https://docs.ccxt.com/
- Tutorial Support: Check AGENTS.md

### Common Resources
- Example strategies: `/examples/strategies/`
- Test data: `/tests/test_kit/`
- Adapters: `/nautilus_trader/adapters/`

### Debugging Tips

1. **Enable detailed logging**
   ```python
   LoggingConfig(log_level="DEBUG")
   ```

2. **Check data integrity**
   ```python
   print(f"Bars: {len(bars)}")
   print(f"First: {bars[0]}")
   print(f"Last: {bars[-1]}")
   ```

3. **Validate strategy logic**
   ```python
   # Add print statements in strategy
   def on_bar(self, bar):
       print(f"Bar: {bar.close}")
       # ... strategy logic
   ```

4. **Review engine state**
   ```python
   print(engine.cache.orders())
   print(engine.cache.positions())
   ```

---

## ✅ Tutorial Completion Checklist

### Tutorial 1: Simple EMA Cross
- [ ] Downloaded CCXT data successfully
- [ ] Created Nautilus bars
- [ ] Set up backtest engine
- [ ] Ran complete backtest
- [ ] Analyzed results
- [ ] Saved results to CSV
- [ ] Completed all exercises
- [ ] Understood all metrics

### Tutorial 2: Enhanced Indicators
- [ ] TBD

### Tutorial 3: AI-Adaptive Strategy
- [ ] TBD

### Tutorial 4: Sentiment Integration
- [ ] TBD

### Tutorial 5: Production System
- [ ] TBD

---

## 🎓 Certification Criteria

To be considered proficient in Nautilus Trader algorithmic trading:

1. ✅ Complete all 5 tutorials
2. ✅ Build a custom strategy from scratch
3. ✅ Achieve Sharpe > 1.5 in backtest
4. ✅ Pass walk-forward validation
5. ✅ Deploy to paper trading successfully

---

**Happy Trading! 🚀📊💰**

**Remember:** Past performance doesn't guarantee future results. Always test thoroughly before live trading!

---

**End of Tutorials Guide**

For questions or issues, refer to the main analysis document:
`/ai-working/learning path/research/analysis.md`
