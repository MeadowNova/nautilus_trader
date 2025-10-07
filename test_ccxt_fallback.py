#!/usr/bin/env python3
"""Cycle through a shortlist of exchanges until one responds."""

from __future__ import annotations

import sys
from typing import Iterable, Tuple

from test_ccxt_integration import DEFAULT_EXCHANGES, DEFAULT_SYMBOLS, create_exchange


def try_exchange(exchange_id: str, symbol: str) -> bool:
    exchange = create_exchange(exchange_id)
    print(f"Testing {exchange_id} ({symbol})...", end=" ")
    try:
        exchange.fetch_ticker(symbol)
        print("OK")
        return True
    except Exception as exc:  # pragma: no cover - network diagnostic helper
        print(f"FAILED ({exc})")
        return False


def main(exchanges: Iterable[str]) -> int:
    for exchange_id in exchanges:
        symbol = DEFAULT_SYMBOLS.get(exchange_id, "BTC/USDT")
        if try_exchange(exchange_id, symbol):
            print(f"\nRecommendation: use {exchange_id} with symbol {symbol}")
            return 0
    print("\nNo exchanges available. Try again later or with a VPN.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(DEFAULT_EXCHANGES))
