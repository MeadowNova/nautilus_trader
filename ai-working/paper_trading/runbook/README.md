Paper Trading Runbook
=====================

This runbook contains quick, copy-pasteable commands and helper scripts to start, stop, and verify a paper trading session in this repository.

Paths and quick references
- Demo / sandbox runners:
  - `scripts/start_paper_trading_demo.py`
  - `scripts/start_paper_trading_sandbox.py`
  - `ajk_strategies/run_paper_trading.py --config configs/paper_trading_config.json`
- WS -> Paper Engine bridge:
  - `scripts/start_paper_trading_ws_bridge.py` (for forwarding third-party WS feeds)
- Logs:
  - `logs/PAPER-TRADER-001_*.log`

Environment variables (common)
- `PAPER_TRADING_ENABLED=true`
- `PAPER_TRADING_INITIAL_BALANCE=100000`
- `PAPER_TRADING_CURRENCY=USD`
- Exchange/testnet keys: `BINANCE_API_KEY`, `BINANCE_API_SECRET`, BYBIT keys, etc.
- `IB_TRADING_MODE=paper` and `IB_PORT=7497` for Interactive Brokers gateway

Quick start (recommended order)

1. Activate virtualenv and install dependencies (see repo README):

```bash
source .venv/bin/activate
uv sync --group all   # if you use uv as recommended by repo
# or: pip install -r requirements.txt
```

2. Run a quick demo (fast):

```bash
python3 scripts/start_paper_trading_demo.py
tail -f logs/PAPER-TRADER-001_*.log
```

3. Run the sandbox for extended live-data validation:

```bash
# optionally in a screen session
screen -S paper_trading
python3 scripts/start_paper_trading_sandbox.py
```

4. Forward an external WS feed to the Paper Engine (optional):

```bash
export PAPER_ENGINE_URL=http://localhost:8181/api/paper_engine/ingest
export WS_URL=wss://stream.testnet.bybit.com/realtime_public
export DATA_PROVIDER=BYBIT
python3 scripts/start_paper_trading_ws_bridge.py
```

Stop / graceful shutdown

```bash
# If running in screen: reattach and Ctrl-C
pkill -SIGTERM -f start_paper_trading_sandbox.py
# Or use the helper script in this runbook folder:
bash ai-working/paper_trading/runbook/stop_paper_trading.sh
```

Verification checklist (quick)

- Check logs for activity (trades, bars, signals):

```bash
tail -f logs/PAPER-TRADER-001_*.log | grep -E "TradeTick|on_bar|Signal probability"
```

- Confirm the bridge is forwarding (if used):
  - Watch the bridge terminal for POST responses or info logs about forwarded payloads.

- Monitoring dashboards:
  - If Prometheus/Grafana are running, open the `live-trading-monitor` dashboard (check `infrastructure/monitoring/grafana/dashboards` for the JSON). The dashboard name is `live-trading-monitor`.

- Confirm Binance instruments loaded (if using Binance):

```bash
grep "Loading instruments: BTCUSDT.BINANCE" -n logs/PAPER-TRADER-001_*.log || true
```

Notes and recommendations
- Default demo trader id: `PAPER-TRADER-001`. Change in scripts/configs if you need multiple parallel sessions.
- Use testnet API keys for exchanges (Binance testnet, Bybit testnet) and set env vars according to `infrastructure/.env.template`.
- The WS bridge validates messages with Nautilus model types before forwarding — it reduces invalid instrument issues when ingesting third-party streams.

Next steps (optional)
- I can create `configs/paper_trading_config.json` tuned to Binance testnet or Bybit testnet and run a quick smoke test in your environment. Ask me to proceed and tell me which exchange you prefer.
