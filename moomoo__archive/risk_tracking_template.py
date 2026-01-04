# -------------------------------------------------------------------------------------------------
#  Risk Tracking Template & Utilities
#  CSV export and Excel generation for risk management spreadsheets
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TYPE_CHECKING
import csv
from pathlib import Path

if TYPE_CHECKING:
    from risk_management_framework import (
        PositionMetrics,
        PortfolioMetrics,
        RMeasurement,
        TradeEntry,
    )


class RiskTrackingExporter:
    """Export risk metrics to CSV and generate spreadsheet templates."""

    @staticmethod
    def export_trades_csv(
        trades: list[dict],
        filename: str = "trades.csv",
    ) -> str:
        """
        Export individual trades to CSV.

        Example columns:
        Date, Instrument, Side, Entry Price, Quantity, Stop Loss, Take Profit,
        Exit Price, P&L, R-Multiple, Bars Held, Status
        """
        if not trades:
            return ""

        fieldnames = [
            "date",
            "instrument",
            "side",
            "entry_price",
            "quantity",
            "stop_loss",
            "take_profit",
            "exit_price",
            "pnl",
            "r_multiple",
            "bars_held",
            "status",
        ]

        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trades)

        return filename

    @staticmethod
    def export_positions_csv(
        positions: dict[str, dict],
        filename: str = "positions.csv",
    ) -> str:
        """Export current positions to CSV."""
        if not positions:
            return ""

        fieldnames = [
            "instrument",
            "direction",
            "quantity",
            "entry_price",
            "current_price",
            "pnl_unrealized",
            "pnl_pct",
            "r_multiple",
            "bars_held",
            "max_favorable_move",
            "max_adverse_move",
            "account_pct",
        ]

        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for pos_data in positions.values():
                writer.writerow(pos_data)

        return filename

    @staticmethod
    def export_portfolio_csv(
        portfolio: dict,
        filename: str = "portfolio.csv",
    ) -> str:
        """Export portfolio metrics to CSV."""
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            for key, value in portfolio.items():
                writer.writerow([key, value])

        return filename

    @staticmethod
    def export_r_measurement_csv(
        r_measurement: dict,
        filename: str = "expectancy.csv",
    ) -> str:
        """Export R-multiple measurements to CSV."""
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            for key, value in r_measurement.items():
                writer.writerow([key, value])

        return filename


class RiskDashboardTemplate:
    """Generate HTML dashboard template for risk monitoring."""

    @staticmethod
    def generate_html_dashboard(
        portfolio: dict,
        positions: dict[str, dict],
        r_measurement: dict,
        filename: str = "risk_dashboard.html",
    ) -> str:
        """Generate interactive HTML risk dashboard."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Risk Management Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        h1 {{
            color: white;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border-left: 5px solid #667eea;
        }}

        .card h2 {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        .card-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}

        .card-subtitle {{
            font-size: 0.85em;
            color: #999;
            margin-top: 10px;
        }}

        .positive {{
            color: #27ae60;
        }}

        .negative {{
            color: #e74c3c;
        }}

        .warning {{
            color: #f39c12;
        }}

        .critical {{
            color: #c0392b;
            font-weight: bold;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f5f5f5;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .risk-ok {{
            background: rgba(39, 174, 96, 0.1);
            color: #27ae60;
        }}

        .risk-warning {{
            background: rgba(243, 156, 18, 0.1);
            color: #f39c12;
        }}

        .risk-critical {{
            background: rgba(192, 57, 43, 0.1);
            color: #c0392b;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 0.9em;
        }}

        .timestamp {{
            color: white;
            text-align: center;
            margin-bottom: 20px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Risk Management Dashboard</h1>
        <div class="timestamp">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

        <!-- Portfolio Metrics -->
        <div class="grid">
            <div class="card">
                <h2>Account Size</h2>
                <div class="card-value">${portfolio.get('account_size', 0):,.0f}</div>
            </div>

            <div class="card">
                <h2>Total P&L</h2>
                <div class="card-value {('positive' if portfolio.get('pnl_total', 0) >= 0 else 'negative')}">
                    ${portfolio.get('pnl_total', 0):,.2f}
                </div>
                <div class="card-subtitle">{portfolio.get('pnl_total', 0) / portfolio.get('account_size', 1) * 100:.2f}%</div>
            </div>

            <div class="card">
                <h2>Daily P&L</h2>
                <div class="card-value {('positive' if portfolio.get('pnl_daily', 0) >= 0 else 'negative')}">
                    ${portfolio.get('pnl_daily', 0):,.2f}
                </div>
            </div>

            <div class="card">
                <h2>Gross Exposure</h2>
                <div class="card-value">${portfolio.get('gross_exposure', 0):,.0f}</div>
                <div class="card-subtitle">{portfolio.get('gross_exposure_pct', 0):.1f}% of account</div>
            </div>

            <div class="card">
                <h2>Net Exposure</h2>
                <div class="card-value">${portfolio.get('net_exposure', 0):,.0f}</div>
                <div class="card-subtitle">{portfolio.get('net_exposure_pct', 0):.1f}% of account</div>
            </div>

            <div class="card">
                <h2>Drawdown</h2>
                <div class="card-value {('warning' if portfolio.get('drawdown_pct', 0) > 5 else '')}">
                    {portfolio.get('drawdown_pct', 0):.2f}%
                </div>
                <div class="card-subtitle">${portfolio.get('current_drawdown', 0):,.0f}</div>
            </div>

            <div class="card">
                <h2>Win Rate</h2>
                <div class="card-value">{r_measurement.get('win_rate', 0):.2f}%</div>
                <div class="card-subtitle">{r_measurement.get('winning_trades', 0)}W / {r_measurement.get('losing_trades', 0)}L</div>
            </div>

            <div class="card">
                <h2>Expectancy</h2>
                <div class="card-value {('positive' if r_measurement.get('expectancy', 0) > 0 else 'negative')}">
                    {r_measurement.get('expectancy', 0):.3f}R
                </div>
                <div class="card-subtitle">Per trade</div>
            </div>

            <div class="card">
                <h2>Profit Factor</h2>
                <div class="card-value {('positive' if r_measurement.get('profit_factor', 0) > 1.5 else 'warning' if r_measurement.get('profit_factor', 0) > 1 else 'negative')}">
                    {r_measurement.get('profit_factor', 0):.2f}x
                </div>
                <div class="card-subtitle">Wins vs Losses</div>
            </div>
        </div>

        <!-- Positions Table -->
        <h2 style="color: white; margin-bottom: 15px;">Open Positions</h2>
        <table>
            <thead>
                <tr>
                    <th>Instrument</th>
                    <th>Direction</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Unrealized P&L</th>
                    <th>Return %</th>
                    <th>R Multiple</th>
                    <th>Bars Held</th>
                </tr>
            </thead>
            <tbody>
"""

        # Add positions
        if positions:
            for instrument, pos_data in positions.items():
                pnl_class = "risk-ok" if pos_data.get("pnl_unrealized", 0) >= 0 else "risk-critical"
                html_content += f"""
                <tr class="{pnl_class}">
                    <td><strong>{instrument}</strong></td>
                    <td>{pos_data.get('direction', 'N/A')}</td>
                    <td>{pos_data.get('quantity', 0)}</td>
                    <td>${pos_data.get('entry_price', 0):.2f}</td>
                    <td>${pos_data.get('current_price', 0):.2f}</td>
                    <td>${pos_data.get('pnl_unrealized', 0):,.2f}</td>
                    <td>{pos_data.get('pnl_pct', 0):.2f}%</td>
                    <td>{pos_data.get('r_multiple', 0):.2f}R</td>
                    <td>{pos_data.get('bars_held', 0)}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>

        <div class="footer">
            <p>Nautilus Trader Risk Management System</p>
            <p>Real-time monitoring of position and portfolio risk</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filename, "w") as f:
            f.write(html_content)

        return filename


class RiskTrackingSpreadsheet:
    """
    Template structure for Excel/CSV risk tracking spreadsheet.

    Recommended layout:

    Sheet 1: Daily Summary
    - Date
    - Account Size
    - Daily P&L
    - Total P&L
    - Gross Exposure
    - Win Rate (%)
    - Expectancy (R)
    - Profit Factor
    - Max Drawdown (%)

    Sheet 2: Trades Log
    - Entry Date
    - Instrument
    - Side (LONG/SHORT)
    - Entry Price
    - Stop Loss
    - Take Profit
    - Exit Date
    - Exit Price
    - Quantity
    - P&L
    - R-Multiple
    - Bars Held
    - Notes

    Sheet 3: Position Monitor
    - Instrument
    - Direction
    - Entry Price
    - Current Price
    - Quantity
    - Entry Time
    - Unrealized P&L
    - Return %
    - R-Multiple
    - Max Favorable Move
    - Max Adverse Move
    - Greeks (Delta/Gamma/Vega/Theta if options)

    Sheet 4: Risk Limits
    - Limit Type
    - Configured Value
    - Current Value
    - Status (OK/WARNING/CRITICAL)
    - Notes

    Sheet 5: Performance Analysis
    - Win Rate
    - Losing Trades
    - Average Win (R)
    - Average Loss (R)
    - Profit Factor
    - Expectancy
    - Kelly %
    - Consecutive Losses
    - Streak Analysis
    """

    @staticmethod
    def get_daily_summary_template() -> dict:
        """Get template for daily summary sheet."""
        return {
            "headers": [
                "Date",
                "Account Size",
                "Daily P&L",
                "Daily %",
                "Total P&L",
                "Total %",
                "Gross Exposure",
                "Net Exposure",
                "Drawdown %",
                "Win Rate %",
                "Expectancy (R)",
                "Profit Factor",
                "Trades Today",
                "Notes",
            ],
            "sample_row": [
                "2024-01-15",
                "500000",
                "2500",
                "0.50%",
                "15000",
                "3.00%",
                "450000",
                "300000",
                "2.50%",
                "42.5%",
                "0.22",
                "1.65",
                "3",
                "Strong day, good risk control",
            ],
        }

    @staticmethod
    def get_trades_log_template() -> dict:
        """Get template for trades log sheet."""
        return {
            "headers": [
                "Entry Date",
                "Instrument",
                "Side",
                "Entry Price",
                "Stop Loss",
                "Take Profit",
                "Exit Date",
                "Exit Price",
                "Quantity",
                "Gross P&L",
                "R-Multiple",
                "Bars Held",
                "Win/Loss",
                "Notes",
            ],
            "sample_row": [
                "2024-01-15 10:30",
                "TSLA",
                "LONG",
                "250.00",
                "245.00",
                "260.00",
                "2024-01-15 14:20",
                "258.50",
                "100",
                "850.00",
                "1.70",
                "4",
                "WIN",
                "Good entry, took profit early",
            ],
        }

    @staticmethod
    def get_position_monitor_template() -> dict:
        """Get template for position monitor sheet."""
        return {
            "headers": [
                "Instrument",
                "Direction",
                "Entry Price",
                "Current Price",
                "Quantity",
                "Entry Time",
                "Unrealized P&L",
                "Return %",
                "R-Multiple",
                "Bars Held",
                "Max Favorable",
                "Max Adverse",
                "Delta",
                "Gamma",
                "Vega",
                "Theta",
                "Status",
            ],
            "sample_row": [
                "AAPL",
                "LONG",
                "175.50",
                "178.25",
                "200",
                "2024-01-15 09:30",
                "550.00",
                "1.57%",
                "1.10",
                "6",
                "650.00",
                "-200.00",
                "0.75",
                "0.05",
                "25.5",
                "-15.2",
                "OK",
            ],
        }


# ===== EXAMPLE USAGE =====

if __name__ == "__main__":
    print("Risk Tracking Template & Utilities")
    print("\nAvailable Exports:")
    print("1. export_trades_csv() - Individual trade records")
    print("2. export_positions_csv() - Current positions snapshot")
    print("3. export_portfolio_csv() - Portfolio metrics")
    print("4. export_r_measurement_csv() - R-multiple statistics")
    print("5. generate_html_dashboard() - Interactive HTML dashboard")

    # Example: Generate templates
    print("\nSpreadsheet Templates:")
    daily = RiskTrackingSpreadsheet.get_daily_summary_template()
    trades = RiskTrackingSpreadsheet.get_trades_log_template()
    positions = RiskTrackingSpreadsheet.get_position_monitor_template()

    print(f"\nDaily Summary columns: {len(daily['headers'])}")
    print(f"Trades Log columns: {len(trades['headers'])}")
    print(f"Position Monitor columns: {len(positions['headers'])}")
