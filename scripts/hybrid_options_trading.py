#!/usr/bin/env python3
"""
Hybrid Options Trading POC - yfinance + Moomoo
================================================

ARCHITECTURE:
- Data source: yfinance (free US stock quotes)
- Execution: Moomoo OpenD (paper trading)
- Strategy: Simple covered call / cash-secured put on SPY/AAPL/NVDA

CONNECTION DETAILS:
- Moomoo OpenD: localhost:11111
- Stock Paper Account: 1252643 (for stocks)
- Options Paper Account: 1252648 (for options - MUST use this for option orders!)
- US Options: LV1 ACCESS (available)
- US Securities: NO ACCESS (using yfinance instead)

NOTE: Moomoo has TWO separate paper trading systems:
1. Web/App Paper Trading (visible in Moomoo app UI)
2. API Paper Trading via OpenD (separate accounts, visible via API only)

STRATEGY LOGIC:
1. Poll yfinance every 30 seconds for underlying prices
2. Calculate simple technical indicators (RSI, SMA)
3. Generate signals:
   - SELL PUT: When RSI < 35 (oversold, bullish)
   - BUY CALL: When RSI > 65 (overbought, for covered calls)
4. Query available options from Moomoo
5. Submit LIMIT orders to Moomoo paper account

EXECUTION:
    python scripts/hybrid_options_trading.py

Press Ctrl+C to stop trading.
"""

import asyncio
import os
import sys
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import traceback
import time

# Third-party imports
import yfinance as yf
import pandas as pd
import numpy as np
from moomoo import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdEnv,
    TrdMarket,
    OrderType,
    TrdSide,
    ModifyOrderOp,
    OptionType,
)


class YFinanceDataProvider:
    """Provides real-time US stock data via yfinance."""

    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.tickers = {sym: yf.Ticker(sym) for sym in symbols}
        self.last_prices: Dict[str, float] = {}
        self.price_history: Dict[str, pd.DataFrame] = {}

    def update_prices(self):
        """Fetch latest prices and historical data."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Updating prices from yfinance...")

        for symbol in self.symbols:
            try:
                ticker = self.tickers[symbol]

                # Get latest price
                info = ticker.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')

                if current_price:
                    self.last_prices[symbol] = current_price
                    print(f"  {symbol}: ${current_price:.2f}")

                # Get historical data for indicators (30 days, 1 hour intervals)
                hist = ticker.history(period="30d", interval="1h")
                if not hist.empty:
                    self.price_history[symbol] = hist

            except Exception as e:
                print(f"  Error fetching {symbol}: {e}")

    def calculate_rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        """Calculate RSI for a symbol."""
        if symbol not in self.price_history:
            return None

        hist = self.price_history[symbol]
        if len(hist) < period + 1:
            return None

        close = hist['Close']
        delta = close.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None

    def calculate_sma(self, symbol: str, period: int = 20) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if symbol not in self.price_history:
            return None

        hist = self.price_history[symbol]
        if len(hist) < period:
            return None

        return hist['Close'].rolling(window=period).mean().iloc[-1]


class MoomooOptionsExecutor:
    """Executes options trades via Moomoo OpenD."""

    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        self.host = host
        self.port = port
        self.quote_ctx: Optional[OpenQuoteContext] = None
        self.trade_ctx: Optional[OpenSecTradeContext] = None
        self.stock_account_id: Optional[str] = None
        self.options_account_id: Optional[str] = None

    def connect(self):
        """Connect to Moomoo OpenD."""
        print(f"\n[Moomoo] Connecting to OpenD at {self.host}:{self.port}...")

        # Quote context
        self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
        ret, data = self.quote_ctx.get_global_state()

        if ret != 0:
            raise RuntimeError(f"Quote context error: {data}")

        market_state = data.get('market_us', 'UNKNOWN')
        print(f"  US Market state: {market_state}")

        # Trade context (paper trading)
        self.trade_ctx = OpenSecTradeContext(
            host=self.host,
            port=self.port,
            filter_trdmarket=TrdMarket.US
        )

        ret, data = self.trade_ctx.get_acc_list()

        if ret != 0:
            raise RuntimeError(f"Could not get account list: {data}")

        # Find paper trading accounts - IMPORTANT: Moomoo has separate accounts for stocks vs options
        # Account 1252643: STOCK paper trading (US market)
        # Account 1252648: OPTION paper trading (US market)
        paper_accounts = data[data['trd_env'] == TrdEnv.SIMULATE]
        if paper_accounts.empty:
            raise RuntimeError("No paper trading accounts found!")

        # Find stock account (sim_acc_type != 'OPTION' or empty)
        stock_accounts = paper_accounts[paper_accounts['sim_acc_type'] != 'OPTION']
        if not stock_accounts.empty:
            self.stock_account_id = stock_accounts.iloc[0]['acc_id']
            print(f"  Stock Account: {self.stock_account_id}")

        # Find options account (sim_acc_type == 'OPTION')
        option_accounts = paper_accounts[paper_accounts['sim_acc_type'] == 'OPTION']
        if not option_accounts.empty:
            self.options_account_id = option_accounts.iloc[0]['acc_id']
            print(f"  Options Account: {self.options_account_id}")
        else:
            # Fallback: try to use first account for both
            self.options_account_id = paper_accounts.iloc[0]['acc_id']
            print(f"  Options Account (fallback): {self.options_account_id}")

        # Get account positions
        ret, positions = self.trade_ctx.position_list_query(trd_env=TrdEnv.SIMULATE)
        if ret == 0 and not positions.empty:
            print(f"  Current positions: {len(positions)}")
            print(positions[['code', 'qty', 'pl_val', 'pl_ratio']])
        else:
            print("  No current positions")

    def disconnect(self):
        """Disconnect from Moomoo OpenD."""
        if self.quote_ctx:
            self.quote_ctx.close()
        if self.trade_ctx:
            self.trade_ctx.close()
        print("\n[Moomoo] Disconnected")

    def get_options_chain(self, underlying: str, expiry_min_days: int = 7, expiry_max_days: int = 60):
        """Get available options for an underlying."""
        if not self.quote_ctx:
            raise RuntimeError("Not connected to Moomoo")

        # Convert symbol format (AAPL -> US.AAPL)
        moomoo_symbol = f"US.{underlying}"

        print(f"\n[Moomoo] Querying options chain for {moomoo_symbol}...")

        # Get option chain
        ret, data = self.quote_ctx.get_option_chain(code=moomoo_symbol)

        if ret != 0:
            print(f"  Error: {data}")
            return []

        if data.empty:
            print("  No options available")
            return []

        # Filter by expiry date
        today = datetime.now()
        min_date = today + timedelta(days=expiry_min_days)
        max_date = today + timedelta(days=expiry_max_days)

        # Convert expiry strings to dates and filter
        filtered_options = []
        for _, row in data.iterrows():
            expiry_str = row.get('expiry_date')
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
                    if min_date <= expiry_date <= max_date:
                        filtered_options.append(row)
                except:
                    continue

        print(f"  Found {len(filtered_options)} options in date range")
        return filtered_options

    def find_suitable_put(self, underlying: str, current_price: float, delta_target: float = 0.30):
        """Find a suitable out-of-the-money put to sell."""
        options = self.get_options_chain(underlying)

        if not options:
            return None

        # Filter for puts below current price
        suitable_puts = []
        for opt in options:
            if opt.get('option_type') == OptionType.PUT:
                strike = opt.get('strike_price', 0)
                if strike < current_price * 0.95:  # At least 5% OTM
                    suitable_puts.append(opt)

        if not suitable_puts:
            print(f"  No suitable puts found for {underlying}")
            return None

        # Sort by strike (closest to 0.30 delta, roughly 70% of current price)
        target_strike = current_price * 0.70
        suitable_puts.sort(key=lambda x: abs(x['strike_price'] - target_strike))

        best_put = suitable_puts[0]
        print(f"  Selected PUT: strike={best_put['strike_price']}, expiry={best_put['expiry_date']}")

        return best_put

    def find_suitable_call(self, underlying: str, current_price: float, delta_target: float = 0.30):
        """Find a suitable out-of-the-money call to buy."""
        options = self.get_options_chain(underlying)

        if not options:
            return None

        # Filter for calls above current price
        suitable_calls = []
        for opt in options:
            if opt.get('option_type') == OptionType.CALL:
                strike = opt.get('strike_price', 0)
                if strike > current_price * 1.05:  # At least 5% OTM
                    suitable_calls.append(opt)

        if not suitable_calls:
            print(f"  No suitable calls found for {underlying}")
            return None

        # Sort by strike (closest to 0.30 delta, roughly 130% of current price)
        target_strike = current_price * 1.30
        suitable_calls.sort(key=lambda x: abs(x['strike_price'] - target_strike))

        best_call = suitable_calls[0]
        print(f"  Selected CALL: strike={best_call['strike_price']}, expiry={best_call['expiry_date']}")

        return best_call

    def place_option_order(self, option_code: str, side: TrdSide, quantity: int, price: float):
        """Place a limit order for an option."""
        if not self.trade_ctx:
            raise RuntimeError("Not connected to Moomoo")

        if not self.options_account_id:
            raise RuntimeError("No options account found - options require account 1252648")

        print(f"\n[Moomoo] Placing OPTIONS order:")
        print(f"  Account: {self.options_account_id} (OPTIONS)")
        print(f"  Code: {option_code}")
        print(f"  Side: {side}")
        print(f"  Quantity: {quantity}")
        print(f"  Limit Price: ${price:.2f}")

        ret, data = self.trade_ctx.place_order(
            price=price,
            qty=quantity,
            code=option_code,
            trd_side=side,
            order_type=OrderType.NORMAL,  # Limit order
            trd_env=TrdEnv.SIMULATE,
            acc_id=self.options_account_id,  # CRITICAL: Must use OPTIONS account for options
        )

        if ret != 0:
            print(f"  ERROR: {data}")
            return None

        order_id = data.iloc[0]['order_id'] if 'order_id' in data.columns else None
        print(f"  SUCCESS: Order ID = {order_id}")

        return order_id

    def get_open_orders(self):
        """Get list of open orders."""
        if not self.trade_ctx:
            return pd.DataFrame()

        ret, data = self.trade_ctx.order_list_query(trd_env=TrdEnv.SIMULATE)

        if ret != 0:
            print(f"  Error querying orders: {data}")
            return pd.DataFrame()

        return data


class HybridTradingBot:
    """Main trading bot orchestrator."""

    def __init__(self, symbols: List[str], poll_interval: int = 30):
        self.symbols = symbols
        self.poll_interval = poll_interval
        self.data_provider = YFinanceDataProvider(symbols)
        self.executor = MoomooOptionsExecutor()
        self.running = False

        # Trading parameters
        self.rsi_oversold = 35
        self.rsi_overbought = 65
        self.max_positions = 3
        self.order_cooldown = {}  # Track last order time per symbol
        self.cooldown_minutes = 30

    def start(self):
        """Start the trading bot."""
        print("\n" + "=" * 70)
        print("HYBRID OPTIONS TRADING BOT")
        print("=" * 70)
        print(f"Data Source: yfinance (free US stock quotes)")
        print(f"Execution: Moomoo OpenD (paper trading)")
        print(f"Strategy: Options based on RSI signals")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Poll Interval: {self.poll_interval} seconds")
        print("=" * 70 + "\n")

        # Connect to Moomoo
        self.executor.connect()

        # Initial data fetch
        self.data_provider.update_prices()

        self.running = True
        print("\n[Bot] Trading bot started. Press Ctrl+C to stop.\n")

    def stop(self):
        """Stop the trading bot."""
        print("\n[Bot] Stopping trading bot...")
        self.running = False
        self.executor.disconnect()
        print("[Bot] Trading bot stopped.\n")

    def is_on_cooldown(self, symbol: str) -> bool:
        """Check if symbol is on cooldown."""
        if symbol not in self.order_cooldown:
            return False

        last_order_time = self.order_cooldown[symbol]
        elapsed_minutes = (datetime.now() - last_order_time).total_seconds() / 60

        return elapsed_minutes < self.cooldown_minutes

    def generate_signals(self):
        """Generate trading signals based on indicators."""
        signals = []

        for symbol in self.symbols:
            if symbol not in self.data_provider.last_prices:
                continue

            price = self.data_provider.last_prices[symbol]
            rsi = self.data_provider.calculate_rsi(symbol)
            sma20 = self.data_provider.calculate_sma(symbol, period=20)

            if rsi is None:
                continue

            print(f"\n[Signal] {symbol}: price=${price:.2f}, RSI={rsi:.1f}, SMA20=${sma20 if sma20 else 0:.2f}")

            # Skip if on cooldown
            if self.is_on_cooldown(symbol):
                remaining = self.cooldown_minutes - (datetime.now() - self.order_cooldown[symbol]).total_seconds() / 60
                print(f"  On cooldown: {remaining:.1f} minutes remaining")
                continue

            # Signal: SELL PUT when oversold (bullish)
            if rsi < self.rsi_oversold and price > sma20:
                signals.append({
                    'symbol': symbol,
                    'action': 'SELL_PUT',
                    'price': price,
                    'rsi': rsi,
                    'reason': f'RSI {rsi:.1f} < {self.rsi_oversold} (oversold, bullish)'
                })

            # Signal: BUY CALL when overbought (for covered calls)
            elif rsi > self.rsi_overbought and price < sma20:
                signals.append({
                    'symbol': symbol,
                    'action': 'BUY_CALL',
                    'price': price,
                    'rsi': rsi,
                    'reason': f'RSI {rsi:.1f} > {self.rsi_overbought} (overbought, bearish)'
                })

        return signals

    def execute_signal(self, signal: Dict):
        """Execute a trading signal."""
        symbol = signal['symbol']
        action = signal['action']
        price = signal['price']
        reason = signal['reason']

        print(f"\n[Execute] {action} on {symbol}")
        print(f"  Reason: {reason}")

        try:
            if action == 'SELL_PUT':
                # Find suitable put option
                option = self.executor.find_suitable_put(symbol, price)

                if option:
                    # Calculate premium (rough estimate: 2-3% of underlying)
                    premium = price * 0.025

                    # Place order to SELL put
                    order_id = self.executor.place_option_order(
                        option_code=option['code'],
                        side=TrdSide.SELL,
                        quantity=1,
                        price=premium
                    )

                    if order_id:
                        self.order_cooldown[symbol] = datetime.now()

            elif action == 'BUY_CALL':
                # Find suitable call option
                option = self.executor.find_suitable_call(symbol, price)

                if option:
                    # Calculate premium (rough estimate: 2-3% of underlying)
                    premium = price * 0.025

                    # Place order to BUY call
                    order_id = self.executor.place_option_order(
                        option_code=option['code'],
                        side=TrdSide.BUY,
                        quantity=1,
                        price=premium
                    )

                    if order_id:
                        self.order_cooldown[symbol] = datetime.now()

        except Exception as e:
            print(f"  Error executing signal: {e}")
            traceback.print_exc()

    def trading_loop(self):
        """Main trading loop."""
        iteration = 0

        while self.running:
            try:
                iteration += 1
                print(f"\n{'=' * 70}")
                print(f"Iteration {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print('=' * 70)

                # Update prices
                self.data_provider.update_prices()

                # Generate signals
                signals = self.generate_signals()

                # Check open orders
                open_orders = self.executor.get_open_orders()
                if not open_orders.empty:
                    print(f"\n[Orders] {len(open_orders)} open orders:")
                    print(open_orders[['code', 'trd_side', 'qty', 'price', 'order_status']])

                # Execute signals
                if signals:
                    print(f"\n[Signals] Generated {len(signals)} signals")
                    for signal in signals:
                        # Check position limits
                        if len(open_orders) < self.max_positions:
                            self.execute_signal(signal)
                        else:
                            print(f"  Skipping signal (max positions reached)")
                else:
                    print("\n[Signals] No trading signals generated")

                # Sleep until next iteration
                print(f"\n[Bot] Sleeping for {self.poll_interval} seconds...\n")
                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n[Error] Trading loop error: {e}")
                traceback.print_exc()
                time.sleep(self.poll_interval)


def main():
    """Main entry point."""

    # Trading symbols (user has US Options LV1 access)
    symbols = ["SPY", "AAPL", "NVDA"]

    # Create bot
    bot = HybridTradingBot(symbols=symbols, poll_interval=30)

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nShutdown signal received...")
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        bot.start()
        bot.trading_loop()
    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt received...")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        traceback.print_exc()
    finally:
        bot.stop()


if __name__ == "__main__":
    main()
