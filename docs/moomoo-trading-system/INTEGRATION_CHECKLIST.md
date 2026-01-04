# Risk Management System - Integration Checklist

Use this checklist to integrate the risk management system with your Moomoo trading platform.

---

## Phase 1: Setup & Initialization

### A. File Structure Verification

- [ ] Verify all files created in correct locations:
  - [ ] `/home/ajk/Nautilus/nautilus_trader/config/options_risk_config.py` (7.3 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/scripts/pre_trade_checks.py` (14 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/scripts/risk_monitor.py` (19 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/scripts/risk_reporter.py` (18 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/scripts/integration_example.py` (12 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/scripts/test_risk_system.py` (17 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/docs/RISK_MANAGEMENT.md` (15 KB)
  - [ ] `/home/ajk/Nautilus/nautilus_trader/docs/QUICK_START_RISK.md` (11 KB)

### B. Test Suite Execution

- [ ] Run test suite: `python /home/ajk/Nautilus/nautilus_trader/scripts/test_risk_system.py`
- [ ] Verify all 30+ tests pass (0 failures)
- [ ] Review test output for any warnings
- [ ] Note any custom configuration needs

### C. Configuration Review

- [ ] Review default risk limits in `options_risk_config.py`
- [ ] Verify account size: $100,000 (update if different)
- [ ] Confirm max position size: 5 contracts
- [ ] Confirm daily loss limit: $1,000
- [ ] Confirm max notional exposure: $10,000
- [ ] Review min/max expiration constraints
- [ ] Check stop loss % and take profit %

---

## Phase 2: Moomoo API Integration

### A. Position Data Structure

- [ ] Confirm Moomoo API returns positions in expected format:
  ```python
  {
      "positions": {
          "symbol_key": {
              "type": "CALL" | "PUT",
              "strike": float,
              "expiration": "YYYY-MM-DD",
              "quantity": int,
              "entry_price": float,
              "mark_price": float,
              "notional": float,
              "unrealized_pnl": float,
              "unrealized_pnl_pct": float,
              "dte": int
          }
      },
      "balance": float
  }
  ```
- [ ] Map actual API response to this structure if needed
- [ ] Test API connection and data retrieval
- [ ] Verify data accuracy against Moomoo web interface

### B. Create Moomoo API Wrapper

- [ ] Create function to get current positions:
  ```python
  def get_moomoo_positions():
      # Your Moomoo API call here
      return {
          "positions": {...},
          "balance": float
      }
  ```
- [ ] Create function to submit orders:
  ```python
  def submit_moomoo_order(order: OrderRequest) -> str:
      # Your Moomoo API call here
      return order_id
  ```
- [ ] Test both functions independently
- [ ] Handle API errors gracefully
- [ ] Add retry logic for network failures

### C. Account Verification

- [ ] Confirm account ID: `MOOMOO-1252643`
- [ ] Verify account type: Paper trading
- [ ] Check current balance (should be ~$100k)
- [ ] Confirm options trading enabled
- [ ] Verify account day trading power

---

## Phase 3: Pre-Trade Integration

### A. Order Validation Integration

- [ ] Create order submission wrapper:
  ```python
  def place_option_order(symbol, option_type, quantity,
                        price, strike, expiration):
      # Create OrderRequest
      order = OrderRequest(
          symbol=symbol,
          option_type=option_type,
          quantity=quantity,
          price=price,
          strike_price=strike,
          expiration_date=expiration
      )

      # Validate with risk system
      is_valid, errors = pre_trade_checker.check_order(order)
      if not is_valid:
          return False, errors

      # Submit to Moomoo
      order_id = submit_moomoo_order(order)
      return True, order_id
  ```

- [ ] Test order validation with valid orders
- [ ] Test order rejection with invalid orders
- [ ] Verify error messages are clear
- [ ] Add logging for all order attempts

### B. Position Sizing Integration

- [ ] Add position sizing recommendation to order flow:
  ```python
  def get_recommended_position_size(option_premium):
      return pre_trade_checker.get_position_sizing_recommendation(
          option_premium
      )
  ```
- [ ] Test sizing calculations for different premiums
- [ ] Display recommendation to trader
- [ ] Log sizing decisions

### C. Rate Limiting Integration

- [ ] Confirm rate limiter active: 15 orders per 30 seconds
- [ ] Test rate limiting behavior
- [ ] Display wait time when rate limited
- [ ] Add notification when approaching rate limit

---

## Phase 4: Position Monitoring Integration

### A. Position Update Loop

- [ ] Create periodic position update function:
  ```python
  async def monitor_positions():
      while True:
          positions = get_moomoo_positions()
          monitor.update_positions(
              positions["positions"],
              positions["balance"]
          )

          # Check for alerts
          alerts = monitor.check_risk_limits()
          if alerts:
              handle_alerts(alerts)

          await asyncio.sleep(30)  # Every 30 seconds
  ```

- [ ] Run position monitor in background/separate thread
- [ ] Test position updates every 30 seconds
- [ ] Verify data updates correctly

### B. Alert Handling

- [ ] Create alert handler:
  ```python
  def handle_alerts(alerts):
      for alert in alerts:
          if alert.alert_type == "CRITICAL":
              # Notify immediately
              send_notification(alert)
              if "daily loss" in alert.metric.lower():
                  stop_trading()
          elif alert.alert_type == "WARNING":
              log_warning(alert)
  ```

- [ ] Implement notification method (email, Slack, SMS, etc.)
- [ ] Test CRITICAL alert notifications
- [ ] Test WARNING alert logging
- [ ] Implement emergency stop for daily loss limit

### C. Daily Reconciliation

- [ ] Create daily reconciliation function:
  ```python
  def daily_reconciliation():
      report = monitor.generate_risk_report()
      risk_manager.save_daily_report(report)
      csv_path, json_path = risk_manager.export_trade_data()
  ```

- [ ] Schedule to run at end of market day
- [ ] Verify report generation
- [ ] Check file outputs

---

## Phase 5: Trade Logging Integration

### A. Trade Entry Logging

- [ ] When order fills, log the trade:
  ```python
  def on_order_filled(order_id, symbol, option_type, strike,
                     expiration, quantity, price, entry_time):
      # Log for tracking
      risk_manager.risk_monitor.log_trade(
          symbol=symbol,
          option_type=option_type,
          strike=strike,
          expiration=expiration,
          quantity=quantity,
          price=price,
          trade_type="BUY",
          order_id=order_id
      )
  ```

- [ ] Test trade logging for buys
- [ ] Verify entries in trade.log

### B. Trade Exit Logging

- [ ] When position closes, log complete trade:
  ```python
  def on_position_closed(entry_order_id, exit_order_id, symbol,
                        option_type, strike, expiration, quantity,
                        entry_price, exit_price, entry_time, exit_time):
      risk_manager.log_trade_close(
          order_id=entry_order_id,
          symbol=symbol,
          option_type=option_type,
          strike=strike,
          expiration=expiration,
          quantity=quantity,
          entry_price=entry_price,
          exit_price=exit_price,
          entry_time=entry_time,
          exit_time=exit_time
      )
  ```

- [ ] Test trade closing and logging
- [ ] Verify R-multiple calculation
- [ ] Check trade statistics update

### C. Trade Data Export

- [ ] Verify automatic export at end of day
- [ ] Test CSV generation
- [ ] Test JSON generation with statistics
- [ ] Confirm both formats readable

---

## Phase 6: Reporting Integration

### A. Daily Report Generation

- [ ] Verify daily report generated at end of market:
  ```python
  report = risk_manager.generate_daily_report()
  risk_manager.save_daily_report(report)
  print(report)  # Display to user
  ```

- [ ] Test report content
- [ ] Verify file saved correctly
- [ ] Check log location

### B. Performance Tracking

- [ ] Daily P&L tracker active:
  ```python
  daily_tracker.record_pnl(
      realized_pnl=realized,
      unrealized_pnl=unrealized,
      positions_count=len(positions)
  )
  ```

- [ ] Test P&L recording
- [ ] Verify daily summary calculation
- [ ] Check CSV export

### C. Weekly Review

- [ ] Schedule weekly review process:
  ```python
  stats = risk_manager.r_tracker.get_trade_statistics()
  print(f"Win Rate: {stats['win_rate_percent']:.1f}%")
  print(f"Expectancy: ${stats['expectancy']:.2f}")
  print(f"Profit Factor: {stats['profit_factor']:.2f}x")
  ```

- [ ] Review win rate (target: 45%+)
- [ ] Check expectancy (must be positive)
- [ ] Analyze profit factor (target: 1.5x+)
- [ ] Review largest losses

---

## Phase 7: Live Trading Validation

### A. Pre-Market Checklist

- [ ] Verify system components loaded:
  - [ ] Risk configuration loaded
  - [ ] Pre-trade checker initialized
  - [ ] Risk monitor ready
  - [ ] Position tracker active

- [ ] Check position monitor running
- [ ] Verify alert system armed
- [ ] Confirm logging active
- [ ] Test Moomoo connection

### B. First Trade Validation

- [ ] Place first test order:
  - [ ] Validate with pre-trade checker
  - [ ] Get position sizing recommendation
  - [ ] Submit to Moomoo
  - [ ] Log entry in system

- [ ] Monitor position:
  - [ ] Position appears in monitor
  - [ ] Greeks calculated
  - [ ] P&L tracked

- [ ] Close first position:
  - [ ] Exit and log trade
  - [ ] Verify R-multiple calculated
  - [ ] Check statistics updated

### C. Limit Testing

- [ ] Test daily loss limit:
  - [ ] Simulate loss approaching $1,000
  - [ ] Verify WARNING alert at $800+
  - [ ] Verify CRITICAL at $950+
  - [ ] Verify trading stops at $1,000+

- [ ] Test notional exposure:
  - [ ] Add positions to approach $10,000
  - [ ] Verify alerts at 80%, 95%
  - [ ] Verify orders blocked at limit

- [ ] Test position count limit:
  - [ ] Open 5 positions
  - [ ] Verify 6th is blocked
  - [ ] Verify alert generation

### D. Emergency Procedures

- [ ] Test emergency stop:
  - [ ] Trigger daily loss limit
  - [ ] Verify new orders blocked
  - [ ] Verify can close existing positions
  - [ ] Verify can cancel pending orders

- [ ] Test alert notifications:
  - [ ] Verify CRITICAL alerts send
  - [ ] Verify WARNING alerts log
  - [ ] Verify notification system works

---

## Phase 8: Documentation & Procedures

### A. Create Trading Procedure Document

Create `/home/ajk/Nautilus/nautilus_trader/TRADING_PROCEDURES.md`:

- [ ] Pre-market checklist
- [ ] Order submission procedure
- [ ] Position management rules
- [ ] Stop/profit taking rules
- [ ] Daily review procedure
- [ ] Emergency procedures
- [ ] Troubleshooting guide

### B. Create Risk Log Template

Create `/home/ajk/Nautilus/nautilus_trader/logs/DAILY_LOG_TEMPLATE.md`:

- [ ] Opening balance
- [ ] Trades executed
- [ ] Daily P&L
- [ ] Risk alerts
- [ ] Notes/observations
- [ ] Closing balance

### C. Create Weekly Review Template

Create `/home/ajk/Nautilus/nautilus_trader/WEEKLY_REVIEW_TEMPLATE.md`:

- [ ] Period: [dates]
- [ ] Total trades: [n]
- [ ] Win rate: [%]
- [ ] P&L: [$]
- [ ] Expectancy: [$]
- [ ] Profit factor: [x]
- [ ] Largest win: [$]
- [ ] Largest loss: [$]
- [ ] Observations
- [ ] Adjustments for next week

---

## Phase 9: Performance & Optimization

### A. Monitor System Performance

- [ ] Position update latency < 5 seconds
- [ ] Alert generation < 2 seconds
- [ ] Report generation < 10 seconds
- [ ] Log file sizes reasonable
- [ ] No memory leaks

### B. Optimize Thresholds

After 1 week of trading:
- [ ] Review alert thresholds
- [ ] Adjust if too many false alerts
- [ ] Confirm alert sensitivity appropriate

After 1 month of trading:
- [ ] Review risk limits performance
- [ ] Adjust if consistently hitting limits
- [ ] Consider increasing limits if consistently profitable

### C. Backup Strategy

- [ ] Daily backup of logs
- [ ] Weekly backup of trade data
- [ ] Monthly backup of full system
- [ ] Test backup restoration

---

## Phase 10: Go-Live Checklist

### Final Verification

- [ ] All 30+ tests passing
- [ ] First test trade completed successfully
- [ ] All limits tested and working
- [ ] Alerts verified and working
- [ ] Reports generating correctly
- [ ] Data exporting successfully
- [ ] Moomoo API integration complete
- [ ] Position monitoring running
- [ ] Emergency procedures tested
- [ ] Documentation complete
- [ ] Team trained on procedures
- [ ] Backups configured

### Launch Approval

- [ ] Risk Officer approval
- [ ] Trading Officer approval
- [ ] Compliance review (if applicable)
- [ ] System test certificate

**Go-live authorized by**: _________________ Date: _________

---

## Post-Launch Support

### Week 1

- [ ] Daily system health checks
- [ ] Monitor all alerts
- [ ] Verify trading procedures followed
- [ ] Adjust any thresholds as needed
- [ ] Daily team briefing

### Month 1

- [ ] Weekly performance review
- [ ] Check for any system issues
- [ ] Validate risk limits appropriate
- [ ] Optimize alert sensitivity
- [ ] Train team on findings

### Month 3

- [ ] Full system audit
- [ ] Performance analysis
- [ ] Risk limit adjustment
- [ ] Backup verification
- [ ] Optimization review

---

## Sign-Off

System Implemented By: _________________ Date: _________

Integration Completed By: _________________ Date: _________

Tested By: _________________ Date: _________

Approved By: _________________ Date: _________

---

## Quick Reference Commands

### Run Tests
```bash
cd /home/ajk/Nautilus/nautilus_trader
python scripts/test_risk_system.py
```

### Generate Daily Report
```bash
python -c "from integration_example import IntegratedRiskManager; \
m = IntegratedRiskManager(); \
print(m.generate_daily_report())"
```

### View Logs
```bash
tail -f /home/ajk/Nautilus/nautilus_trader/logs/risk_monitor.log
tail -f /home/ajk/Nautilus/nautilus_trader/logs/trades.log
```

### Export Trade Data
```bash
python -c "from integration_example import IntegratedRiskManager; \
m = IntegratedRiskManager(); \
m.export_trade_data()"
```

---

## Notes

Use this section for notes on integration progress, issues encountered, and resolutions:

```
Date: ________
Issue: ________
Resolution: ________

Date: ________
Issue: ________
Resolution: ________
```
