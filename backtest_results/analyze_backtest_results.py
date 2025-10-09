import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json

def analyze_backtest_results(results_dir="/home/ajk/Nautilus/nautilus_trader/backtest_results"):
    results_path = Path(results_dir)
    summaries = sorted(results_path.glob("summary_*.json"))

    if not summaries:
        print("No summary files found. Run a backtest first.")
        return

    # Load summaries
    records = []
    for file in summaries:
        with open(file) as f:
            records.append(json.load(f))

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    print("\n📊 SUMMARY TABLE")
    print(df[[
        "instrument", "scenario", "pnl_pct", "win_rate", "profit_factor",
        "total_trades", "duration_seconds"
    ]].round(2))

    # Plot total equity progression if you have CSVs
    fills = sorted(results_path.glob("fills_*.csv"))
    positions = sorted(results_path.glob("positions_*.csv"))

    if not positions:
        print("\nNo positions CSV found, skipping equity curve.")
        return

    for pos_file in positions:
        df_pos = pd.read_csv(pos_file)
        if "realized_pnl" not in df_pos.columns:
            continue

        df_pos["timestamp"] = pd.to_datetime(df_pos["closed_time"], errors="coerce")
        df_pos = df_pos.sort_values("timestamp")

        # Equity curve
        df_pos["cumulative_pnl"] = df_pos["realized_pnl"].cumsum()
        plt.figure(figsize=(12, 6))
        plt.plot(df_pos["timestamp"], df_pos["cumulative_pnl"], label=pos_file.name)
        plt.title("Equity Curve")
        plt.xlabel("Time")
        plt.ylabel("Cumulative P&L (USDT)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        # Drawdown curve
        running_max = df_pos["cumulative_pnl"].cummax()
        drawdown = df_pos["cumulative_pnl"] - running_max
        plt.figure(figsize=(12, 4))
        plt.plot(df_pos["timestamp"], drawdown, color="red", label="Drawdown")
        plt.title("Drawdown Over Time")
        plt.xlabel("Time")
        plt.ylabel("Drawdown (USDT)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    print("\n✅ Analysis complete.")
