#!/usr/bin/env python3
"""
Core mapping and serialization helpers for the WS -> Paper Engine bridge.

This file contains pure functions that import only the Nautilus model types and
do not depend on network libraries. It's safe to import from unit tests.
"""
from typing import Any
import logging

from nautilus_trader.model.data import QuoteTick, TradeTick
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.functions import aggressor_side_to_str


def _ensure_venue_suffix(symbol: str | None, default_venue: str = "BINANCE") -> str | None:
    """If symbol is a bare symbol (no '.'), append a default venue suffix.

    This keeps behaviour minimal and predictable for live feeds that only
    provide exchange symbols like "BTCUSDT". We default to ".BINANCE"
    because many test samples and existing loaders use the BINANCE venue
    naming convention (e.g. "BTCUSDT.BINANCE"). If symbol is already
    canonical (contains a '.'), return unchanged.
    """
    if not symbol:
        return None
    if "." in symbol:
        return symbol
    return f"{symbol}.{default_venue}"

def quote_to_dict(q: QuoteTick) -> dict[str, Any]:
    try:
        return {
            "type": "quote",
            "instrument_id": q.instrument_id.to_str() if hasattr(q.instrument_id, "to_str") else str(q.instrument_id),
            "bid_price": q.bid_price.as_double() if q.bid_price is not None else None,
            "ask_price": q.ask_price.as_double() if q.ask_price is not None else None,
            "bid_size": q.bid_size.as_double() if q.bid_size is not None else None,
            "ask_size": q.ask_size.as_double() if q.ask_size is not None else None,
            "ts_event": int(q.ts_event),
            "ts_init": int(q.ts_init),
        }
    except Exception:
        logging.getLogger("ws-bridge-core").exception("quote_to_dict failed")
        raise


def trade_to_dict(t: TradeTick) -> dict[str, Any]:
    try:
        return {
            "type": "trade",
            "instrument_id": t.instrument_id.to_str() if hasattr(t.instrument_id, "to_str") else str(t.instrument_id),
            "price": t.price.as_double(),
            "size": t.size.as_double(),
            "side": aggressor_side_to_str(t.aggressor_side) if hasattr(t, "aggressor_side") and t.aggressor_side is not None else None,
            "trade_id": t.trade_id.to_str() if hasattr(t, "trade_id") and t.trade_id is not None and hasattr(t.trade_id, "to_str") else (str(t.trade_id) if getattr(t, "trade_id", None) is not None else None),
            "ts_event": int(t.ts_event),
            "ts_init": int(t.ts_init),
        }
    except Exception:
        logging.getLogger("ws-bridge-core").exception("trade_to_dict failed")
        raise


def try_canonical_serialize(obj: Any) -> dict:
    fn = getattr(obj, "to_dict", None)
    if callable(fn):
        try:
            return fn()
        except Exception:
            pass

    cls_fn = getattr(type(obj), "to_dict", None)
    if callable(cls_fn):
        try:
            return cls_fn(obj)
        except Exception:
            pass

    if isinstance(obj, QuoteTick):
        return quote_to_dict(obj)
    elif isinstance(obj, TradeTick):
        return trade_to_dict(obj)
    else:
        raise RuntimeError("Unknown model type for serialization")


def map_message_to_model(msg: dict, provider: str = "BYBIT") -> tuple[str, Any]:
    prov = (provider or "BYBIT").upper()
    if prov == "BYBIT":
        return map_bybit_message(msg)
    elif prov == "BINANCE":
        return map_binance_message(msg)
    else:
        return map_generic_message(msg)


def map_bybit_message(msg: dict) -> tuple[str, Any]:
    try:
        if msg.get("topic", "").lower().startswith("trade") or ("data" in msg and isinstance(msg["data"], list) and any("price" in d or "p" in d for d in msg["data"])):
            d = msg["data"][0] if isinstance(msg["data"], list) else msg
            symbol = d.get("symbol") or d.get("s") or msg.get("symbol")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(_ensure_venue_suffix(symbol, "BYBIT") or symbol)
            price = Price.from_str(str(d.get("price") or d.get("p") or d.get("last_price")))
            size = Quantity.from_str(str(d.get("size") or d.get("q") or d.get("trade_qty") or d.get("qty") or 0))
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

            ts = _norm_ts(d.get("trade_time_ms") or d.get("ts") or d.get("T") or 0)

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

        if msg.get("topic", "").lower().startswith("books") or "bid_price" in msg or ("data" in msg and isinstance(msg["data"], list) and any("bid_price" in d or "ask_price" in d for d in msg["data"])):
            d = msg["data"][0] if isinstance(msg["data"], list) else msg
            symbol = d.get("symbol") or msg.get("symbol")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(_ensure_venue_suffix(symbol, "BYBIT") or symbol)
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
        logging.getLogger("ws-bridge-core").exception("map_bybit_message failed")
    return (None, None)


def map_binance_message(msg: dict) -> tuple[str, Any]:
    try:
        if msg.get("e") == "trade" or msg.get("e") == "aggTrade":
            symbol = msg.get("s") or msg.get("symbol")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(_ensure_venue_suffix(symbol, "BINANCE") or symbol)
            price = Price.from_str(str(msg.get("p") or msg.get("price")))
            size = Quantity.from_str(str(msg.get("q") or msg.get("qty")))
            if "m" in msg:
                aggressor = AggressorSide.SELLER if msg.get("m") else AggressorSide.BUYER
            else:
                aggressor = AggressorSide.NO_AGGRESSOR

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

            trade_id_val = msg.get("t") or None
            # TradeTick requires a TradeId; fallback to ts-based id when venue id missing
            if trade_id_val is not None:
                trade_id = TradeId(str(trade_id_val))
            else:
                trade_id = TradeId(str(ts))

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

        if msg.get("e") == "bookTicker" or ("b" in msg and "a" in msg and "s" in msg):
            symbol = msg.get("s")
            instrument = InstrumentId.from_str(_ensure_venue_suffix(symbol, "BINANCE") or symbol)
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
        logging.getLogger("ws-bridge-core").exception("map_binance_message failed")
    return (None, None)


def map_generic_message(msg: dict) -> tuple[str, Any]:
    try:
        if msg.get("type") == "quote" or ("bid" in msg and "ask" in msg):
            symbol = msg.get("symbol") or msg.get("s")
            if not symbol:
                return (None, None)
            instrument = InstrumentId.from_str(_ensure_venue_suffix(symbol, "BINANCE") or symbol)
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
            instrument = InstrumentId.from_str(_ensure_venue_suffix(symbol, "BINANCE") or symbol)
            price = Price.from_str(str(msg.get("price")))
            size = Quantity.from_str(str(msg.get("size")))
            aggressor = AggressorSide.NO_AGGRESSOR
            trade_id_val = msg.get("trade_id", None)
            trade_id = TradeId(str(trade_id_val)) if trade_id_val is not None else None
            tt = TradeTick(
                instrument_id=instrument,
                price=price,
                size=size,
                aggressor_side=aggressor,
                trade_id=trade_id,
                ts_event=int(msg.get("ts_event", msg.get("ts", 0))),
                ts_init=int(msg.get("ts_init", msg.get("ts", 0))),
            )
            return ("trade", tt)

    except Exception:
        logging.getLogger("ws-bridge-core").exception("map_generic_message failed")
    return (None, None)
