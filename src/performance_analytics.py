"""Performance Analytics — Sharpe, Sortino, drawdown, profit factor, heatmaps.

Computes institutional-grade performance metrics from paper trading data
and presents them as summary dicts or Plotly charts.
"""

import math
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,11,18,0.95)",
    font={"color": "#c9d1d9", "family": "Inter, sans-serif"},
)

# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.04) -> float:
    """Annualized Sharpe Ratio.

    Args:
        returns: List of daily return percentages.
        risk_free_rate: Annual risk-free rate (default 4%).
    """
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns) / 100  # convert pct to decimal
    daily_rf = risk_free_rate / 252
    excess = arr - daily_rf
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return round(float(np.mean(excess) / std * math.sqrt(252)), 2)


def sortino_ratio(returns: list[float], risk_free_rate: float = 0.04) -> float:
    """Annualized Sortino Ratio (only penalizes downside volatility)."""
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns) / 100
    daily_rf = risk_free_rate / 252
    excess = arr - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 99.99 if np.mean(excess) > 0 else 0.0
    down_std = np.std(downside, ddof=1)
    if down_std == 0:
        return 0.0
    return round(float(np.mean(excess) / down_std * math.sqrt(252)), 2)


def calmar_ratio(total_return_pct: float, max_drawdown_pct: float) -> float:
    """Calmar Ratio = annualized return / max drawdown."""
    if max_drawdown_pct == 0:
        return 0.0
    return round(total_return_pct / max_drawdown_pct, 2)


def profit_factor(trades: list[dict]) -> float:
    """Profit Factor = gross profit / gross loss."""
    gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
    if gross_loss == 0:
        return 99.99 if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 2)


def expectancy(trades: list[dict]) -> float:
    """Expectancy per trade in USD.

    E = (win_rate * avg_win) - (loss_rate * avg_loss)
    """
    if not trades:
        return 0.0
    wins = [t["pnl"] for t in trades if t.get("pnl", 0) > 0]
    losses = [abs(t["pnl"]) for t in trades if t.get("pnl", 0) < 0]
    total = len(trades)
    win_rate = len(wins) / total
    loss_rate = len(losses) / total
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    return round(win_rate * avg_win - loss_rate * avg_loss, 2)


def avg_holding_time(trades: list[dict]) -> str:
    """Average time a position was held."""
    durations = []
    for t in trades:
        if t.get("opened_at") and t.get("closed_at"):
            try:
                opened = datetime.fromisoformat(t["opened_at"])
                closed = datetime.fromisoformat(t["closed_at"])
                durations.append((closed - opened).total_seconds())
            except (ValueError, TypeError):
                pass
    if not durations:
        return "N/A"
    avg_sec = sum(durations) / len(durations)
    if avg_sec < 3600:
        return f"{avg_sec / 60:.0f} min"
    elif avg_sec < 86400:
        return f"{avg_sec / 3600:.1f} hrs"
    else:
        return f"{avg_sec / 86400:.1f} days"


def consecutive_wins_losses(trades: list[dict]) -> dict:
    """Calculate max consecutive wins and losses."""
    max_wins = max_losses = current_wins = current_losses = 0
    for t in trades:
        if t.get("pnl", 0) > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif t.get("pnl", 0) < 0:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
        else:
            current_wins = current_losses = 0
    return {"max_consecutive_wins": max_wins, "max_consecutive_losses": max_losses}


# ---------------------------------------------------------------------------
# Full performance report
# ---------------------------------------------------------------------------

def generate_report(trades: list[dict], equity_curve: list[dict], starting_balance: float) -> dict:
    """Generate comprehensive performance report."""
    # Daily returns from equity curve
    daily_returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i-1].get("equity", starting_balance)
        curr = equity_curve[i].get("equity", starting_balance)
        if prev > 0:
            daily_returns.append((curr - prev) / prev * 100)

    # Trade stats
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) < 0]
    total_pnl = sum(t.get("pnl", 0) for t in trades)

    # Max drawdown from equity curve
    from risk_manager import max_drawdown
    dd = max_drawdown(equity_curve)

    total_return = (total_pnl / starting_balance * 100) if starting_balance else 0
    streaks = consecutive_wins_losses(trades)

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return, 2),
        "avg_win": round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0,
        "best_trade": round(max((t["pnl"] for t in trades), default=0), 2),
        "worst_trade": round(min((t["pnl"] for t in trades), default=0), 2),
        "profit_factor": profit_factor(trades),
        "expectancy": expectancy(trades),
        "sharpe_ratio": sharpe_ratio(daily_returns),
        "sortino_ratio": sortino_ratio(daily_returns),
        "calmar_ratio": calmar_ratio(total_return, dd["max_drawdown_pct"]),
        "max_drawdown_pct": dd["max_drawdown_pct"],
        "max_drawdown_usd": dd["max_drawdown_usd"],
        "avg_holding_time": avg_holding_time(trades),
        "max_consecutive_wins": streaks["max_consecutive_wins"],
        "max_consecutive_losses": streaks["max_consecutive_losses"],
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def equity_drawdown_chart(equity_curve: list[dict], starting_balance: float, height: int = 350) -> go.Figure:
    """Equity curve with drawdown overlay."""
    if len(equity_curve) < 2:
        return go.Figure()

    times = [p["t"] for p in equity_curve]
    equities = [p["equity"] for p in equity_curve]

    # Calculate running drawdown
    peak = equities[0]
    drawdowns = []
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        drawdowns.append(-dd)

    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.05)

    # Equity line
    fig.add_trace(go.Scatter(
        x=times, y=equities, mode="lines", fill="tozeroy",
        line={"color": "#58a6ff", "width": 2}, fillcolor="rgba(88,166,255,0.1)",
        name="Equity",
    ), row=1, col=1)
    fig.add_hline(y=starting_balance, line_dash="dash", line_color="#484f58", row=1, col=1)

    # Drawdown
    fig.add_trace(go.Scatter(
        x=times, y=drawdowns, mode="lines", fill="tozeroy",
        line={"color": "#f85149", "width": 1.5}, fillcolor="rgba(248,81,73,0.15)",
        name="Drawdown %",
    ), row=2, col=1)

    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=20, b=30, l=60, r=20),
                      showlegend=True, legend=dict(orientation="h", y=1.08))
    for r in [1, 2]:
        fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)", row=r, col=1)
        fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)", row=r, col=1)
    fig.update_yaxes(title="USD", row=1, col=1)
    fig.update_yaxes(title="DD %", row=2, col=1)

    return fig


def pnl_distribution_chart(trades: list[dict], height: int = 250) -> go.Figure:
    """P&L distribution histogram."""
    if not trades:
        return go.Figure()
    pnls = [t.get("pnl", 0) for t in trades]
    colors = ["#3fb950" if p >= 0 else "#f85149" for p in pnls]

    fig = go.Figure(go.Histogram(
        x=pnls, nbinsx=20,
        marker_color="#58a6ff", opacity=0.7,
        name="P&L Distribution",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="#ffa657")
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=20, b=30, l=50, r=20),
                      xaxis_title="P&L ($)", yaxis_title="Count")
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def performance_by_day_chart(trades: list[dict], height: int = 250) -> go.Figure:
    """P&L heatmap by day of week."""
    if not trades:
        return go.Figure()

    day_pnl = {d: 0 for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
    day_count = {d: 0 for d in day_pnl}
    day_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for t in trades:
        try:
            dt = datetime.fromisoformat(t["closed_at"])
            day = day_map[dt.weekday()]
            day_pnl[day] += t.get("pnl", 0)
            day_count[day] += 1
        except (ValueError, KeyError):
            pass

    days = list(day_pnl.keys())
    values = [round(day_pnl[d], 2) for d in days]
    counts = [day_count[d] for d in days]
    colors = ["#3fb950" if v >= 0 else "#f85149" for v in values]

    fig = go.Figure(go.Bar(
        x=days, y=values, marker_color=colors, opacity=0.8,
        text=[f"${v:+.2f}<br>{c} trades" for v, c in zip(values, counts)],
        textposition="outside",
    ))
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=20, b=30, l=50, r=20),
                      yaxis_title="P&L ($)")
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def rolling_win_rate_chart(trades: list[dict], window: int = 5, height: int = 280) -> go.Figure:
    """Rolling win rate chart (last N trades window)."""
    if len(trades) < 2:
        return go.Figure()

    # Sort by close time
    sorted_trades = sorted(trades, key=lambda t: t.get("closed_at", ""))
    wins = [1 if t.get("pnl", 0) >= 0 else 0 for t in sorted_trades]

    # Rolling win rate
    rolling_wr = []
    dates = []
    for i in range(window - 1, len(wins)):
        wr = sum(wins[i - window + 1:i + 1]) / window * 100
        rolling_wr.append(wr)
        try:
            dt = datetime.fromisoformat(sorted_trades[i].get("closed_at", ""))
            dates.append(dt)
        except (ValueError, KeyError):
            dates.append(None)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=rolling_wr,
        mode="lines+markers",
        line=dict(color="#58a6ff", width=2),
        marker=dict(size=5, color=["#3fb950" if wr >= 50 else "#f85149" for wr in rolling_wr]),
        name=f"Rolling {window}-Trade Win Rate",
        hovertemplate="Win Rate: %{y:.0f}%<br>%{x}<extra></extra>",
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="#ffa657", annotation_text="50% Breakeven",
                  annotation_position="top left")
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=20, b=30, l=50, r=20),
                      yaxis_title="Win Rate %", yaxis=dict(range=[0, 100]))
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def cumulative_pnl_chart(trades: list[dict], height: int = 280) -> go.Figure:
    """Cumulative P&L over time — the money curve."""
    if not trades:
        return go.Figure()

    sorted_trades = sorted(trades, key=lambda t: t.get("closed_at", ""))
    cumulative = []
    dates = []
    running = 0.0

    for t in sorted_trades:
        running += t.get("pnl", 0)
        cumulative.append(running)
        try:
            dt = datetime.fromisoformat(t.get("closed_at", ""))
            dates.append(dt)
        except (ValueError, KeyError):
            dates.append(None)

    colors = ["#3fb950" if c >= 0 else "#f85149" for c in cumulative]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=cumulative,
        mode="lines",
        fill="tozeroy",
        line=dict(color="#3fb950" if cumulative[-1] >= 0 else "#f85149", width=2),
        fillcolor="rgba(63,185,80,0.1)" if cumulative[-1] >= 0 else "rgba(248,81,73,0.1)",
        name="Cumulative P&L",
        hovertemplate="P&L: $%{y:+,.2f}<br>%{x}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#6e7681")
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=20, b=30, l=50, r=20),
                      yaxis_title="Cumulative P&L ($)")
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def pnl_by_asset_chart(trades: list[dict], height: int = 280) -> go.Figure:
    """P&L breakdown by asset — which assets are making/losing money."""
    if not trades:
        return go.Figure()

    asset_pnl = {}
    asset_count = {}
    for t in trades:
        asset = t.get("asset", "Unknown")
        asset_pnl[asset] = asset_pnl.get(asset, 0) + t.get("pnl", 0)
        asset_count[asset] = asset_count.get(asset, 0) + 1

    # Sort by P&L
    sorted_assets = sorted(asset_pnl.items(), key=lambda x: x[1])
    names = [a[0] for a in sorted_assets]
    pnls = [round(a[1], 2) for a in sorted_assets]
    counts = [asset_count.get(n, 0) for n in names]
    colors = ["#3fb950" if p >= 0 else "#f85149" for p in pnls]

    fig = go.Figure(go.Bar(
        x=pnls, y=names, orientation="h",
        marker_color=colors, opacity=0.85,
        text=[f"${p:+.2f} ({c} trades)" for p, c in zip(pnls, counts)],
        textposition="outside",
    ))
    fig.update_layout(**DARK_LAYOUT, height=max(height, len(names) * 35),
                      margin=dict(t=20, b=30, l=80, r=80),
                      xaxis_title="P&L ($)")
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def trade_timeline_chart(trades: list[dict], height: int = 350) -> go.Figure:
    """Timeline scatter chart showing all trades over time.

    X axis: date (closed_at), Y axis: P&L per trade.
    Green dots for wins, red for losses, sized by abs(pnl).
    Hover shows asset, direction, entry/exit price, P&L, hold time.
    """
    if not trades:
        return go.Figure()

    sorted_trades = sorted(trades, key=lambda t: t.get("closed_at", ""))

    dates = []
    pnls = []
    colors = []
    sizes = []
    hover_texts = []

    for t in sorted_trades:
        try:
            closed_dt = datetime.fromisoformat(t.get("closed_at", ""))
        except (ValueError, TypeError):
            continue

        pnl = t.get("pnl", 0)
        dates.append(closed_dt)
        pnls.append(pnl)
        colors.append("#3fb950" if pnl >= 0 else "#f85149")

        # Size proportional to abs(pnl), clamped to [6, 30]
        raw_size = abs(pnl)
        size = max(6, min(30, 6 + raw_size * 0.5))
        sizes.append(size)

        # Hold time
        hold_str = "N/A"
        if t.get("opened_at"):
            try:
                opened_dt = datetime.fromisoformat(t["opened_at"])
                delta_sec = (closed_dt - opened_dt).total_seconds()
                if delta_sec < 3600:
                    hold_str = f"{delta_sec / 60:.0f} min"
                elif delta_sec < 86400:
                    hold_str = f"{delta_sec / 3600:.1f} hrs"
                else:
                    hold_str = f"{delta_sec / 86400:.1f} days"
            except (ValueError, TypeError):
                pass

        asset = t.get("asset", "Unknown")
        direction = t.get("direction", "N/A")
        entry = t.get("entry_price", 0)
        exit_p = t.get("exit_price", 0)
        hover = (
            f"<b>{asset}</b><br>"
            f"Direction: {direction}<br>"
            f"Entry: ${entry:,.2f}<br>"
            f"Exit: ${exit_p:,.2f}<br>"
            f"P&L: ${pnl:+,.2f}<br>"
            f"Hold: {hold_str}"
        )
        hover_texts.append(hover)

    fig = go.Figure(go.Scatter(
        x=dates,
        y=pnls,
        mode="markers",
        marker=dict(color=colors, size=sizes, opacity=0.8,
                    line=dict(width=1, color="rgba(200,200,200,0.3)")),
        hovertext=hover_texts,
        hoverinfo="text",
        name="Trades",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#6e7681")
    fig.update_layout(**DARK_LAYOUT, height=height,
                      margin=dict(t=20, b=30, l=60, r=20),
                      yaxis_title="P&L ($)", xaxis_title="Date")
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def win_loss_streak_chart(trades: list[dict], height: int = 250) -> go.Figure:
    """Bar chart showing consecutive win/loss streaks.

    Positive bars for win streaks, negative for loss streaks.
    Color: green for wins, red for losses. Labels show streak count.
    """
    if not trades:
        return go.Figure()

    sorted_trades = sorted(trades, key=lambda t: t.get("closed_at", ""))

    # Build streaks: list of (streak_length, is_win)
    streaks = []
    current_count = 0
    current_is_win = None

    for t in sorted_trades:
        pnl = t.get("pnl", 0)
        is_win = pnl >= 0

        if current_is_win is None:
            current_is_win = is_win
            current_count = 1
        elif is_win == current_is_win:
            current_count += 1
        else:
            streaks.append((current_count, current_is_win))
            current_is_win = is_win
            current_count = 1

    # Don't forget the last streak
    if current_count > 0:
        streaks.append((current_count, current_is_win))

    if not streaks:
        return go.Figure()

    x_labels = [f"#{i+1}" for i in range(len(streaks))]
    heights = [s[0] if s[1] else -s[0] for s in streaks]
    colors = ["#3fb950" if s[1] else "#f85149" for s in streaks]
    labels = [f"{s[0]}W" if s[1] else f"{s[0]}L" for s in streaks]

    fig = go.Figure(go.Bar(
        x=x_labels,
        y=heights,
        marker_color=colors,
        opacity=0.85,
        text=labels,
        textposition="outside",
        name="Streaks",
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="#6e7681", line_width=1)
    fig.update_layout(**DARK_LAYOUT, height=height,
                      margin=dict(t=20, b=30, l=50, r=20),
                      xaxis_title="Streak #", yaxis_title="Streak Length",
                      showlegend=False)
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def hourly_performance_chart(trades: list[dict], height: int = 250) -> go.Figure:
    """P&L grouped by hour of day (when trade was opened).

    Bar chart showing total P&L per hour. Green for positive, red for negative.
    Useful for finding best trading hours.
    """
    if not trades:
        return go.Figure()

    hour_pnl = {h: 0.0 for h in range(24)}
    hour_count = {h: 0 for h in range(24)}

    for t in trades:
        try:
            dt = datetime.fromisoformat(t.get("opened_at", ""))
            hour = dt.hour
            hour_pnl[hour] += t.get("pnl", 0)
            hour_count[hour] += 1
        except (ValueError, TypeError, KeyError):
            continue

    # Only show hours that had trades
    hours = [h for h in range(24) if hour_count[h] > 0]
    if not hours:
        return go.Figure()

    pnls = [round(hour_pnl[h], 2) for h in hours]
    counts = [hour_count[h] for h in hours]
    colors = ["#3fb950" if p >= 0 else "#f85149" for p in pnls]
    labels = [f"{h:02d}:00" for h in hours]

    fig = go.Figure(go.Bar(
        x=labels,
        y=pnls,
        marker_color=colors,
        opacity=0.85,
        text=[f"${p:+.2f}<br>{c} trades" for p, c in zip(pnls, counts)],
        textposition="outside",
        name="Hourly P&L",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#6e7681")
    fig.update_layout(**DARK_LAYOUT, height=height,
                      margin=dict(t=20, b=30, l=50, r=20),
                      xaxis_title="Hour of Day", yaxis_title="P&L ($)",
                      showlegend=False)
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig
