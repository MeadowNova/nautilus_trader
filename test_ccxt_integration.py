#!/usr/bin/env python3
"""Quick CCXT smoke test for public market data endpoints.

The script verifies that ccxt is installed correctly, the selected
exchange is reachable from the current network, and that basic market
data endpoints (ticker, order book, OHLCV) respond without raising
exceptions. It is intentionally lightweight so it can be run before
starting paper trading or backfilling new markets.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, Tuple

import ccxt  # type: ignore

DEFAULT_EXCHANGES: Tuple[str, ...] = (
    "bybit",
    "kucoin",
    "okx",
    "bitfinex",
    "mexc",
    "gateio",
)

DEFAULT_SYMBOLS: Dict[str, str] = {
    "bybit": "BTC/USDT",
    "kucoin": "BTC/USDT",
    "okx": "BTC/USDT",
    "bitfinex": "BTC/USDT",
    "mexc": "BTC/USDT",
    "gateio": "BTC/USDT",
}


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({
        "enableRateLimit": True,
        "timeout": 10000,
    })


def format_ts(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M")


def test_exchange(exchange_id: str, symbol: str) -> bool:
    exchange = create_exchange(exchange_id)
    print(f"\n>>> Testing {exchange_id} ({symbol})")

    ticker = exchange.fetch_ticker(symbol)
    last = ticker.get("last")
    print(f"  Ticker last: {last:,.2f}" if last else "  No last price in ticker response")

    order_book = exchange.fetch_order_book(symbol, limit=20)
    best_bid = order_book["bids"][0][0] if order_book["bids"] else None
    best_ask = order_book["asks"][0][0] if order_book["asks"] else None
    print(f"  Order book best bid/ask: {best_bid}, {best_ask}")

    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=3)
    for candle in ohlcv:
        print(f"  OHLCV {format_ts(candle[0])}: O={candle[1]:,.2f} C={candle[4]:,.2f}")

    trades = exchange.fetch_trades(symbol, limit=3)
    print(f"  Recent trades: {len(trades)} records")

    print("  Supported endpoints:")
    print(f"    fetchTicker: {exchange.has.get('fetchTicker')}")
    print(f"    fetchOrderBook: {exchange.has.get('fetchOrderBook')}")
    print(f"    fetchOHLCV: {exchange.has.get('fetchOHLCV')}")
    print(f"    fetchTrades: {exchange.has.get('fetchTrades')}")

    return True


def run_suite(exchanges: Iterable[str]) -> int:
    successes = 0
    for exchange_id in exchanges:
        symbol = DEFAULT_SYMBOLS.get(exchange_id, "BTC/USDT")
        try:
            if test_exchange(exchange_id, symbol):
                successes += 1
        except Exception as exc:  # pragma: no cover - diagnostics only
            print(f"  ERROR: {exc}")
    return successes


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate CCXT connectivity")
    parser.add_argument(
        "--exchange",
        help="Single exchange id to test (defaults to a known good shortlist)",
    )
    parser.add_argument(
        "--symbol",
        help="Override the trading pair when --exchange is provided",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if args.exchange:
        exchange_id = args.exchange.lower()
        symbol = args.symbol or DEFAULT_SYMBOLS.get(exchange_id, "BTC/USDT")
        try:
            test_exchange(exchange_id, symbol)
            return 0
        except Exception as exc:  # pragma: no cover - diagnostics only
            print(f"Exchange test failed: {exc}")
            return 1

    successes = run_suite(DEFAULT_EXCHANGES)
    if successes == 0:
        print("\nNo exchanges responded successfully. Try a VPN or different venue.")
        return 2

    print(f"\nCompleted CCXT smoke test. Working exchanges: {successes}/{len(DEFAULT_EXCHANGES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
