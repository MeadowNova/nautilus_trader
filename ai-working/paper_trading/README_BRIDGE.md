WS Bridge quick usage
=====================

We added a lightweight WebSocket → Paper Engine bridge script to validate and forward live ticks using Nautilus model types.

Files:
- `scripts/start_paper_trading_ws_bridge.py` - main bridge (supports BYBIT and BINANCE message formats). Set env vars and run.
- `scripts/test_ws_bridge.py` - local test harness that simulates Bybit/Binance messages and prints mapping results.

Environment variables (recommended):
```bash
PAPER_ENGINE_URL=http://localhost:8181/api/paper_engine/ingest
WS_URL=wss://your-provider.example/stream
WS_API_KEY=your_key_here            # optional
TRACK_SYMBOLS=BTCUSDT,ETHUSDT
DATA_PROVIDER=BYBIT                 # BYBIT | BINANCE | CCXT
SERIALIZATION_MODE=plain            # plain | canonical
LOG_LEVEL=INFO
```

Run the bridge:
```bash
python scripts/start_paper_trading_ws_bridge.py
```

Run the local test harness (no network required):
```bash
python scripts/test_ws_bridge.py
```

Notes:
- The bridge validates messages by constructing Nautilus model objects (QuoteTick/TradeTick) and then forwards a plain JSON dict to `PAPER_ENGINE_URL` by default.
- `SERIALIZATION_MODE=canonical` will attempt to call any available `.to_dict()` helper on model instances and fall back to plain dicts if unavailable.
- If you want additional provider mappings (other exchanges or custom envelopes), paste a sample incoming WS message and we'll extend `map_bybit_message` / `map_binance_message` accordingly.
