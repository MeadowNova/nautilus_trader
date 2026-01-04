# from repo root
uv sync --group all     # if you use uv package manager (recommended by repo)
# or regular pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # if repo has requirements.txt

# Run the included demo paper trader which uses TraderId PAPER-TRADER-001
python3 scripts/start_paper_trading_demo.py
# Logs are written to logs/PAPER-TRADER-001_*.log — tail them:
tail -f logs/PAPER-TRADER-001_*.log
# Grep useful lines:
tail -f logs/PAPER-TRADER-001_*.log | grep -E "Bar|Trade|Signal probability"

# Start in a screen session so it keeps running
screen -S paper_trading
# Inside the screen
python3 scripts/start_paper_trading_sandbox.py
# Detach: Ctrl-A D ; Reattach with: screen -r paper_trading
# To run in background (nohup)
nohup python3 scripts/start_paper_trading_sandbox.py > /tmp/paper_trading.out 2>&1 &

# Create or edit a config at configs/paper_trading_config.json (see infra/OPERATIONS_GUIDE.md for expected keys)
python3 ajk_strategies/run_paper_trading.py --config configs/paper_trading_config.json
# Run inside screen:
screen -S paper_trading
python3 ajk_strategies/run_paper_trading.py --config configs/paper_trading_config.json

# Set the PAPER_ENGINE_URL (defaults to http://localhost:8181/api/paper_engine/ingest)
export PAPER_ENGINE_URL=http://localhost:8181/api/paper_engine/ingest
export WS_URL=wss://stream.testnet.bybit.com/realtime_public   # example
export DATA_PROVIDER=BYBIT    # or BINANCE
python3 scripts/start_paper_trading_ws_bridge.py

# If started in screen: reattach and Ctrl-C
# If running as background nohup: find the PID and kill gracefully:
ps aux | grep start_paper_trading_sandbox.py
pkill -SIGTERM -f start_paper_trading_sandbox.py
# Or use the repo helper if present:
bash scripts/stop_paper_trading.sh

# Check demo/sandbox logs for trades, bars, signals:
tail -f logs/PAPER-TRADER-001_*.log | grep -E "TradeTick|on_bar|Signal probability"

# Confirm the WS bridge is forwarding:
# - Watch the bridge terminal for POST responses
# - Or inspect PAPER engine logs / endpoints to confirm ingestion

# Check Grafana dashboard (if set up):
# - Open the `live-trading-monitor` dashboard JSON found in:
ls infrastructure/monitoring/grafana/dashboards

# Confirm Binance instruments loaded:
grep "Loading instruments: BTCUSDT.BINANCE" -n logs/PAPER-TRADER-001_*.log || true