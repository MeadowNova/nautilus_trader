#!/usr/bin/env python3
"""
Quick test harness for `start_paper_trading_ws_bridge.py` mapping/serialization.

Run locally to validate mapping logic without opening real websockets.
"""
import json
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import importlib.util
import types


def _load_bridge_module():
    # Import the bridge module without executing top-level websocket connect.
    spec = importlib.util.spec_from_file_location("ws_bridge", "./scripts/start_paper_trading_ws_bridge.py")
    module = importlib.util.module_from_spec(spec)
    # Execute module in its own namespace
    spec.loader.exec_module(module)  # type: ignore
    return module


from ws_bridge_core import (
    map_bybit_message,
    map_binance_message,
    map_generic_message,
    try_canonical_serialize,
    quote_to_dict,
    trade_to_dict,
)


def run_sample_bybit_trade():
    sample = {
        "topic": "trade.BTCUSDT",
        "data": [
            {
                "symbol": "BTCUSDT-LINEAR.BYBIT",
                "price": "42000.5",
                "size": "0.001",
                "side": "BUY",
                "trade_time_ms": 1697110400000,
            }
        ],
    }

    model_type, obj = map_bybit_message(sample)
    print('BYBIT MAPPED:', model_type)
    if obj is not None:
        print('PLAIN:', trade_to_dict(obj))
    else:
        print('BYBIT mapping returned None')


def run_sample_binance_trade():
    sample = {
        "e": "trade",
        "s": "BTCUSDT",
        "p": "42001.0",
        "q": "0.002",
        "T": 1697110401000,
        "m": False,
    }
    model_type, obj = map_binance_message(sample)
    print('BINANCE MAPPED:', model_type)
    if obj is not None:
        print('PLAIN:', trade_to_dict(obj))
    else:
        print('BINANCE mapping returned None')


def run_generic():
    sample = {"type": "quote", "symbol": "BTCUSDT", "bid": "41999.5", "ask": "42001.5", "bid_size": "0.5", "ask_size": "0.6", "ts": 1697110402000}
    model_type, obj = map_generic_message(sample)
    print('GENERIC MAPPED:', model_type)
    if obj is not None:
        print('PLAIN:', quote_to_dict(obj))
    else:
        print('GENERIC mapping returned None')


if __name__ == '__main__':
    run_sample_bybit_trade()
    run_sample_binance_trade()
    run_generic()
