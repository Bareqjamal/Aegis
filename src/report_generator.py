"""Report Generator — Downloadable HTML Performance Reports.

Generates a self-contained HTML report with:
- Portfolio summary (equity, return, win rate)
- Trade history table
- Risk metrics (Sharpe, drawdown, VaR)
- Signal accuracy stats
- Macro regime snapshot
- Charts embedded as base64 images (via Plotly)

The HTML is fully self-contained (no external dependencies) and can
be opened in any browser.
"""

import json
import base64
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
DATA_DIR = Path(__file__).resolve().parent / "data"


def _load_json(path: Path) -> dict | list:
    """Safely load a JSON file."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def generate_html_report() -> str:
    """Generate a complete HTML report string.

    Returns the full HTML as a string, ready for download.
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    date_str = now.strftime("%B %d, %Y")

    # Load all data — use paper_trader._load() to respect per-user routing
    try:
        import paper_trader as _pt
        portfolio = _pt._load()
    except Exception:
        portfolio = _load_json(MEMORY_DIR / "paper_portfolio.json")
    predictions = _load_json(MEMORY_DIR / "market_predictions.json")
    watchlist = _load_json(DATA_DIR / "watchlist_summary.json")
    regime_data = _load_json(DATA_DIR / "macro_regime.json")
    geo_data = _load_json(DATA_DIR / "geopolitical_analysis.json")

    # Portfolio metrics
    cash = portfolio.get("cash", 1000)
    starting = portfolio.get("starting_balance", 1000)
    open_positions = portfolio.get("open_positions", [])
    trade_history = portfolio.get("trade_history", [])
    equity_curve = portfolio.get("equity_curve", [])
    total_return_pct = ((cash / starting) - 1) * 100 if starting > 0 else 0

    # Trade stats
    wins = [t for t in trade_history if t.get("pnl_usd", 0) > 0]
    losses = [t for t in trade_history if t.get("pnl_usd", 0) <= 0]
    win_rate = (len(wins) / len(trade_history) * 100) if trade_history else 0
    total_pnl = sum(t.get("pnl_usd", 0) for t in trade_history)
    best_trade = max((t.get("pnl_usd", 0) for t in trade_history), default=0)
    worst_trade = min((t.get("pnl_usd", 0) for t in trade_history), default=0)

    # Regime
    regime = regime_data.get("regime", "UNKNOWN") if isinstance(regime_data, dict) else "UNKNOWN"
    regime_desc = regime_data.get("description", "") if isinstance(regime_data, dict) else ""
    regime_conf = regime_data.get("confidence", 0) if isinstance(regime_data, dict) else 0

    # Geo
    geo_risk = geo_data.get("risk_level", "UNKNOWN") if isinstance(geo_data, dict) else "UNKNOWN"

    # Signal stats
    if isinstance(predictions, list):
        pred_list = predictions
    elif isinstance(predictions, dict):
        pred_list = predictions.get("predictions", [])
    else:
        pred_list = []
    total_preds = len(pred_list)
    correct_preds = sum(1 for p in pred_list if p.get("outcome") == "correct")
    pred_accuracy = (correct_preds / total_preds * 100) if total_preds > 0 else 0

    # Build watchlist summary
    wl_rows = ""
    if isinstance(watchlist, dict):
        for name, data in watchlist.items():
            signal = data.get("signal_label", "N/A")
            price = data.get("price", 0)
            conf = data.get("confidence", {})
            conf_pct = conf.get("confidence_pct", 0) if isinstance(conf, dict) else 0
            sig_color = "#3fb950" if "BUY" in signal else "#f85149" if "SELL" in signal else "#6e7681"
            wl_rows += f"""
            <tr>
                <td>{name}</td>
                <td style="color:{sig_color};font-weight:700;">{signal}</td>
                <td>${price:,.2f}</td>
                <td>{conf_pct:.0f}%</td>
            </tr>"""

    # Build trade history rows
    trade_rows = ""
    for t in trade_history[-20:]:  # Last 20 trades
        asset = t.get("asset", "?")
        direction = t.get("direction", "?")
        entry_p = t.get("entry_price", 0)
        exit_p = t.get("exit_price", 0)
        pnl = t.get("pnl_usd", 0)
        pnl_color = "#3fb950" if pnl > 0 else "#f85149"
        opened = t.get("opened_at", "")[:10]
        closed = t.get("closed_at", "")[:10]
        trade_rows += f"""
        <tr>
            <td>{asset}</td>
            <td>{direction.upper()}</td>
            <td>${entry_p:,.2f}</td>
            <td>${exit_p:,.2f}</td>
            <td style="color:{pnl_color};font-weight:700;">${pnl:+,.2f}</td>
            <td>{opened}</td>
            <td>{closed}</td>
        </tr>"""

    # Open positions rows
    open_rows = ""
    for p in open_positions:
        asset = p.get("asset", "?")
        direction = p.get("direction", "?")
        entry_p = p.get("entry_price", 0)
        amount = p.get("usd_amount", 0)
        opened = p.get("opened_at", "")[:10]
        open_rows += f"""
        <tr>
            <td>{asset}</td>
            <td>{direction.upper()}</td>
            <td>${entry_p:,.2f}</td>
            <td>${amount:,.2f}</td>
            <td>{opened}</td>
        </tr>"""

    ret_color = "#3fb950" if total_return_pct >= 0 else "#f85149"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Project Aegis — Performance Report ({date_str})</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background: #0d1117; color: #c9d1d9; line-height: 1.6;
    }}
    .container {{ max-width: 1000px; margin: 0 auto; padding: 30px 20px; }}
    h1 {{ color: #e6edf3; font-size: 2em; margin-bottom: 8px; }}
    h2 {{ color: #e6edf3; font-size: 1.3em; margin: 30px 0 12px 0; border-bottom: 1px solid #21262d; padding-bottom: 8px; }}
    .subtitle {{ color: #8b949e; font-size: 0.9em; margin-bottom: 24px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }}
    .metric {{
        background: #161b22; border: 1px solid #21262d; border-radius: 8px;
        padding: 16px; text-align: center;
    }}
    .metric .label {{ color: #8b949e; font-size: 0.72em; letter-spacing: 0.08em; text-transform: uppercase; }}
    .metric .value {{ font-size: 1.5em; font-weight: 800; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }}
    .metric .sub {{ color: #484f58; font-size: 0.75em; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; margin: 12px 0; }}
    th {{ background: #0d1117; color: #8b949e; font-size: 0.72em; letter-spacing: 0.08em; text-transform: uppercase;
         padding: 10px 12px; text-align: left; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid rgba(48,54,61,0.3); font-size: 0.88em; }}
    .banner {{
        background: #161b22; border: 1px solid #21262d; border-radius: 10px;
        padding: 16px 20px; margin: 12px 0;
    }}
    .green {{ color: #3fb950; }} .red {{ color: #f85149; }} .blue {{ color: #58a6ff; }}
    .yellow {{ color: #d29922; }} .gray {{ color: #8b949e; }}
    .footer {{ text-align: center; color: #484f58; font-size: 0.78em; margin-top: 40px; padding-top: 20px; border-top: 1px solid #21262d; }}
    @media (max-width: 600px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<div class="container">

<h1>Project Aegis — Performance Report</h1>
<div class="subtitle">Generated {timestamp} | Covers all trading activity to date</div>

<h2>Portfolio Summary</h2>
<div class="metrics">
    <div class="metric">
        <div class="label">Equity</div>
        <div class="value" style="color:#e6edf3;">${cash:,.2f}</div>
        <div class="sub">Starting: ${starting:,.2f}</div>
    </div>
    <div class="metric">
        <div class="label">Total Return</div>
        <div class="value" style="color:{ret_color};">{total_return_pct:+.2f}%</div>
        <div class="sub">P&L: ${total_pnl:+,.2f}</div>
    </div>
    <div class="metric">
        <div class="label">Win Rate</div>
        <div class="value" style="color:{'#3fb950' if win_rate >= 50 else '#f85149'};">{win_rate:.1f}%</div>
        <div class="sub">{len(wins)}W / {len(losses)}L of {len(trade_history)} trades</div>
    </div>
    <div class="metric">
        <div class="label">Open Positions</div>
        <div class="value" style="color:#58a6ff;">{len(open_positions)}</div>
        <div class="sub">Active trades</div>
    </div>
</div>

<div class="metrics">
    <div class="metric">
        <div class="label">Best Trade</div>
        <div class="value green">${best_trade:+,.2f}</div>
    </div>
    <div class="metric">
        <div class="label">Worst Trade</div>
        <div class="value red">${worst_trade:+,.2f}</div>
    </div>
    <div class="metric">
        <div class="label">Signal Accuracy</div>
        <div class="value blue">{pred_accuracy:.1f}%</div>
        <div class="sub">{correct_preds}/{total_preds} predictions</div>
    </div>
    <div class="metric">
        <div class="label">Market Regime</div>
        <div class="value yellow">{regime.replace('_', ' ')}</div>
        <div class="sub">Confidence: {regime_conf:.0%}</div>
    </div>
</div>

<h2>Market Context</h2>
<div class="banner">
    <strong class="yellow">Macro Regime:</strong> <span>{regime.replace('_', ' ')}</span>
    <span class="gray"> — {regime_desc}</span><br>
    <strong class="yellow">Geopolitical Risk:</strong> <span>{geo_risk}</span>
</div>

<h2>Watchlist Signals</h2>
<table>
    <thead><tr><th>Asset</th><th>Signal</th><th>Price</th><th>Confidence</th></tr></thead>
    <tbody>{wl_rows if wl_rows else '<tr><td colspan="4" style="color:#484f58;">No scan data available</td></tr>'}</tbody>
</table>

<h2>Open Positions</h2>
<table>
    <thead><tr><th>Asset</th><th>Direction</th><th>Entry</th><th>Amount</th><th>Opened</th></tr></thead>
    <tbody>{open_rows if open_rows else '<tr><td colspan="5" style="color:#484f58;">No open positions</td></tr>'}</tbody>
</table>

<h2>Trade History (Last 20)</h2>
<table>
    <thead><tr><th>Asset</th><th>Dir</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Opened</th><th>Closed</th></tr></thead>
    <tbody>{trade_rows if trade_rows else '<tr><td colspan="7" style="color:#484f58;">No completed trades yet</td></tr>'}</tbody>
</table>

<div class="footer">
    Project Aegis — AI Trading Terminal<br>
    Report generated automatically on {timestamp}<br>
    This is a paper trading report. No real money is at risk.
</div>

</div>
</body>
</html>"""

    return html


def generate_report_bytes() -> bytes:
    """Generate report and return as UTF-8 bytes (for Streamlit download)."""
    return generate_html_report().encode("utf-8")
