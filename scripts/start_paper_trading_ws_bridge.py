#!/usr/bin/env python3
"""
WebSocket -> Paper Engine bridge for NautilusTrader

This script connects to a websocket market data provider, maps incoming
messages to Nautilus model types (QuoteTick/TradeTick) for validation and
normalization, then forwards a plain JSON dict to the PAPER_ENGINE_URL.

Usage:
  - Configure environment in `infrastructure/.env.local` or export env vars:
    PAPER_ENGINE_URL, WS_URL, WS_API_KEY (optional), TRACK_SYMBOLS (comma list)

Design:
  - Minimal-change approach: import Nautilus model classes and use their
    constructors / helpers (InstrumentId.from_str, Price.from_str, Quantity.from_str)
  - Serialize to plain dict with numeric values from Price.as_double()/Quantity.as_double()
  - Skip invalid items (per AGENTS.md guidance) and log full tracebacks
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any

from pathlib import Path

# Add project root to path so we can import nautilus_trader package during local runs
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load .env.local if present
env_file = project_root / "infrastructure" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: {env_file}")

import aiohttp
import websockets

# Nautilus model imports (canonical)
from nautilus_trader.model.data import QuoteTick, TradeTick
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.functions import aggressor_side_to_str

PAPER_ENGINE_URL = os.environ.get("PAPER_ENGINE_URL", "http://localhost:8181/api/paper_engine/ingest")
WS_URL = os.environ.get("WS_URL", "wss://example.com/marketdata")
WS_API_KEY = os.environ.get("WS_API_KEY")
TRACK_SYMBOLS = os.environ.get("TRACK_SYMBOLS", "BTCUSDT").split(",")
DATA_PROVIDER = os.environ.get("DATA_PROVIDER", "BYBIT").upper()  # BYBIT | BINANCE | CCXT
SERIALIZATION_MODE = os.environ.get("SERIALIZATION_MODE", "plain").lower()  # plain | canonical

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("ws-bridge")


def quote_to_dict(q: QuoteTick) -> dict[str, Any]:
    # Build a JSON-friendly dict using canonical getters
    try:
        return {
            "type": "quote",
            "instrument_id": q.instrument_id.to_str(),
            "bid_price": q.bid_price.as_double() if q.bid_price is not None else None,
            "ask_price": q.ask_price.as_double() if q.ask_price is not None else None,
            "bid_size": q.bid_size.as_double() if q.bid_size is not None else None,
            "ask_size": q.ask_size.as_double() if q.ask_size is not None else None,
            "ts_event": int(q.ts_event),
            "ts_init": int(q.ts_init),
        }
    except Exception:
        logger.exception("Failed to convert QuoteTick to dict")
        raise


def trade_to_dict(t: TradeTick) -> dict[str, Any]:
    try:
        return {
            "type": "trade",
            "instrument_id": t.instrument_id.to_str(),
            "price": t.price.as_double(),
            "size": t.size.as_double(),
            # TradeTick uses `aggressor_side` (AggressorSide enum)
            "side": aggressor_side_to_str(t.aggressor_side) if hasattr(t, "aggressor_side") and t.aggressor_side is not None else None,
            "trade_id": t.trade_id.to_str() if hasattr(t, "trade_id") and t.trade_id is not None else None,
            "ts_event": int(t.ts_event),
            "ts_init": int(t.ts_init),
        }
    except Exception:
        logger.exception("Failed to convert TradeTick to dict")
        raise


async def forward_payload(session: aiohttp.ClientSession, payload: dict[str, Any]) -> None:
    try:
        async with session.post(PAPER_ENGINE_URL, json=payload, timeout=10) as resp:
            if resp.status >= 400:
                text = await resp.text()
                logger.error("Engine returned %s: %s", resp.status, text)
            else:
                logger.debug("Forwarded payload successfully: %s", payload.get("type"))
    except Exception:
        logger.exception("Failed to POST payload to engine")


async def handle_message(raw: str, session: aiohttp.ClientSession) -> None:
    """Parse incoming raw message (JSON), map to Nautilus models and forward."""
    try:
        msg = json.loads(raw)
    except Exception:
        logger.exception("Invalid JSON message received")
        return

    # Provider-specific mapping: supports BYBIT and BINANCE common message formats
    try:
        model_type, model_obj = map_message_to_model(msg, provider=DATA_PROVIDER)

        if model_obj is None:
            logger.debug("No model produced for message, skipping: %s", msg)
            return

        # Serialize according to selected mode
        if SERIALIZATION_MODE == "canonical":
            payload = try_canonical_serialize(model_obj)
        else:
            # plain fallback
            if model_type == "quote":
                payload = quote_to_dict(model_obj)
            else:
                payload = trade_to_dict(model_obj)

        await forward_payload(session, payload)

    except Exception:
        # Per AGENTS.md: skip failed items, log full traceback
        logger.exception("Skipping invalid message after mapping attempt")


def try_canonical_serialize(obj: Any) -> dict:
    """Attempt to call canonical serializer on object, fallback to plain dicts."""
    # Try instance method
    fn = getattr(obj, "to_dict", None)
    if callable(fn):
        try:
            return fn()
        except Exception:
            logger.exception("canonical to_dict failed on instance, falling back")

    # Try class-level to_dict(obj)
    cls_fn = getattr(type(obj), "to_dict", None)
    if callable(cls_fn):
        try:
            return cls_fn(obj)
        except Exception:
            logger.exception("canonical to_dict failed on class, falling back")

    # Last resort: fallback to plain dict helpers
    if isinstance(obj, QuoteTick):
        return quote_to_dict(obj)
    elif isinstance(obj, TradeTick):
        return trade_to_dict(obj)
    else:
        raise RuntimeError("Unknown model type for serialization")


def map_message_to_model(msg: dict, provider: str = "BYBIT") -> tuple[str, Any]:
    """Provider-aware mapping: returns (model_type, model_obj) or (None,None) if unhandled.

    Supported providers: BYBIT, BINANCE, CCXT
    """
    prov = (provider or "BYBIT").upper()
    if prov == "BYBIT":
        return map_bybit_message(msg)
    elif prov == "BINANCE":
        return map_binance_message(msg)
    else:
        # CCXT and others: attempt generic mapping
        return map_generic_message(msg)


def map_bybit_message(msg: dict) -> tuple[str, Any]:
    # Bybit public WS often sends `topic` and `data` array of dicts
    try:
        # Trades
        if msg.get("topic", "").lower().startswith("trade") or ("data" in msg and isinstance(msg["data"], list) and any("price" in d or "p" in d for d in msg["data"])):
            d = msg["data"][0] if isinstance(msg["data"], list) else msg
            symbol = d.get("symbol") or d.get("s") or msg.get("symbol")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(symbol)
            price = Price.from_str(str(d.get("price") or d.get("p") or d.get("last_price")))
            size = Quantity.from_str(str(d.get("size") or d.get("q") or d.get("trade_qty") or d.get("qty") or 0))
            # Map side/aggressor to AggressorSide enum
            side_raw = d.get("side") or d.get("S") or None
            if side_raw is None:
                aggressor = AggressorSide.NO_AGGRESSOR
            else:
                s = str(side_raw).lower()
                if s.startswith("sell"):
                    aggressor = AggressorSide.SELLER
                elif s.startswith("buy"):
                    aggressor = AggressorSide.BUYER
                else:
                    aggressor = AggressorSide.NO_AGGRESSOR

            trade_id_val = d.get("trade_time_ms") or d.get("trade_id") or d.get("i") or None
            trade_id = TradeId(str(trade_id_val)) if trade_id_val is not None else None

            # Normalize timestamps to nanoseconds (TradeTick expects ns)
            def _norm_ts(v):
                try:
                    v_int = int(v)
                except Exception:
                    return 0
                # seconds -> ns
                if v_int < 1_000_000_000_000:
                    return v_int * 1_000_000_000
                # milliseconds -> ns
                if v_int < 1_000_000_000_000_000:
                    return v_int * 1_000_000
                return v_int

            ts = _norm_ts(d.get("trade_time_ms") or d.get("ts") or d.get("T") or 0)

            # TradeTick constructor expects AggressorSide and TradeId objects
            tt = TradeTick(
                instrument_id=instrument,
                price=price,
                size=size,
                aggressor_side=aggressor,
                trade_id=trade_id,
                ts_event=ts,
                ts_init=ts,
            )
            return ("trade", tt)

        # Quotes / top-of-book
        if msg.get("topic", "").lower().startswith("books") or "bid_price" in msg or ("data" in msg and isinstance(msg["data"], list) and any("bid_price" in d or "ask_price" in d for d in msg["data"])):
            d = msg["data"][0] if isinstance(msg["data"], list) else msg
            symbol = d.get("symbol") or msg.get("symbol")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(symbol)
            bid_price = Price.from_str(str(d.get("bid_price") or d.get("bid") or d.get("b"))) if d.get("bid_price") or d.get("bid") or d.get("b") else None
            ask_price = Price.from_str(str(d.get("ask_price") or d.get("ask") or d.get("a"))) if d.get("ask_price") or d.get("ask") or d.get("a") else None
            bid_size = Quantity.from_str(str(d.get("bid_size") or d.get("B") or 0)) if d.get("bid_size") or d.get("B") else None
            ask_size = Quantity.from_str(str(d.get("ask_size") or d.get("A") or 0)) if d.get("ask_size") or d.get("A") else None
            ts = int(d.get("ts") or d.get("ts_event") or 0)

            qt = QuoteTick(
                instrument_id=instrument,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=bid_size,
                ask_size=ask_size,
                ts_event=ts,
                ts_init=ts,
            )
            return ("quote", qt)

    except Exception:
        logger.exception("Error mapping Bybit message")
    return (None, None)


def map_binance_message(msg: dict) -> tuple[str, Any]:
    # Binance streams: trade (e), bookTicker, etc.
    try:
        # Trade event
        if msg.get("e") == "trade" or msg.get("e") == "aggTrade":
            symbol = msg.get("s") or msg.get("symbol")
            instrument = InstrumentId.from_str(symbol)
            price = Price.from_str(str(msg.get("p") or msg.get("price")))
            size = Quantity.from_str(str(msg.get("q") or msg.get("qty")))
            # Derive aggressor side from maker flag `m` (True => maker)
            if "m" in msg:
                aggressor = AggressorSide.SELLER if msg.get("m") else AggressorSide.BUYER
            else:
                aggressor = AggressorSide.NO_AGGRESSOR

            trade_id_val = msg.get("t") or None
            trade_id = TradeId(str(trade_id_val)) if trade_id_val is not None else None

            def _norm_ts(v):
                try:
                    v_int = int(v)
                except Exception:
                    return 0
                if v_int < 1_000_000_000_000:
                    return v_int * 1_000_000_000
                if v_int < 1_000_000_000_000_000:
                    return v_int * 1_000_000
                return v_int

            ts = _norm_ts(msg.get("T") or msg.get("E") or 0)

            tt = TradeTick(
                instrument_id=instrument,
                price=price,
                size=size,
                aggressor_side=aggressor,
                trade_id=trade_id,
                ts_event=ts,
                ts_init=ts,
            )
            return ("trade", tt)

        # bookTicker / top-of-book
        if msg.get("e") == "bookTicker" or ("b" in msg and "a" in msg and "s" in msg):
            symbol = msg.get("s")
            instrument = InstrumentId.from_str(symbol)
            bid_price = Price.from_str(str(msg.get("b")))
            ask_price = Price.from_str(str(msg.get("a")))
            bid_size = Quantity.from_str(str(msg.get("B"))) if msg.get("B") is not None else None
            ask_size = Quantity.from_str(str(msg.get("A"))) if msg.get("A") is not None else None
            ts = int(msg.get("T") or 0)

            qt = QuoteTick(
                instrument_id=instrument,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=bid_size,
                ask_size=ask_size,
                ts_event=ts,
                ts_init=ts,
            )
            return ("quote", qt)

    except Exception:
        logger.exception("Error mapping Binance message")
    return (None, None)


def map_generic_message(msg: dict) -> tuple[str, Any]:
    # Try common fields, similar to earlier plain mapping
    try:
        if msg.get("type") == "quote" or ("bid" in msg and "ask" in msg):
            symbol = msg.get("symbol") or msg.get("s")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(symbol)
            bid_price = Price.from_str(str(msg.get("bid"))) if msg.get("bid") is not None else None
            ask_price = Price.from_str(str(msg.get("ask"))) if msg.get("ask") is not None else None
            bid_size = Quantity.from_str(str(msg.get("bid_size"))) if msg.get("bid_size") is not None else None
            ask_size = Quantity.from_str(str(msg.get("ask_size"))) if msg.get("ask_size") is not None else None
            ts = int(msg.get("ts_event", msg.get("ts", 0)))

            qt = QuoteTick(
                instrument_id=instrument,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=bid_size,
                ask_size=ask_size,
                ts_event=ts,
                ts_init=ts,
            )
            return ("quote", qt)

        if msg.get("type") == "trade" or ("price" in msg and "size" in msg):
            symbol = msg.get("symbol") or msg.get("s")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(symbol)
            price = Price.from_str(str(msg.get("price")))
            size = Quantity.from_str(str(msg.get("size")))
            tt = TradeTick(
                instrument_id=instrument,
                price=price,
                size=size,
                side=msg.get("side", None),
                trade_id=msg.get("trade_id", None),
                ts_event=int(msg.get("ts_event", msg.get("ts", 0))),
                ts_init=int(msg.get("ts_init", msg.get("ts", 0))),
            )
            return ("trade", tt)

    except Exception:
        logger.exception("Error mapping generic message")

    return (None, None)


async def run_bridge():
    reconnect_backoff = 1
    max_backoff = int(os.environ.get("RECONNECT_MAX_BACKOFF_SECONDS", "60"))

    headers = {}
    if WS_API_KEY:
        headers["Authorization"] = f"Bearer {WS_API_KEY}"

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                logger.info("Connecting to WS: %s", WS_URL)
                async with websockets.connect(WS_URL, extra_headers=headers, ping_interval=20) as ws:
                    reconnect_backoff = 1
                    logger.info("Connected to WS")

                    # Example subscribe message for provider (may need adapting)
                    subscribe = {"action": "subscribe", "symbols": TRACK_SYMBOLS}
                    await ws.send(json.dumps(subscribe))

                    async for message in ws:
                        asyncio.create_task(handle_message(message, session))

            except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
                logger.warning("WebSocket disconnected: %s", e)
            except Exception:
                logger.exception("WebSocket error")

            # Backoff
            logger.info("Reconnecting in %s seconds...", reconnect_backoff)
            await asyncio.sleep(reconnect_backoff)
            reconnect_backoff = min(max_backoff, reconnect_backoff * 2)


def _handle_exit(signum, frame):
    logger.info("Signal %s received, exiting...", signum)
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)

    logger.info("Starting WS -> Paper Engine bridge")
    asyncio.run(run_bridge())


if __name__ == "__main__":
    main()
