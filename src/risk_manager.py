"""Risk Manager — Position sizing, stop-loss/take-profit, and portfolio risk.

Provides:
- Kelly Criterion and fixed-fractional position sizing
- Stop-loss / take-profit / trailing stop checking
- Max drawdown monitoring with circuit breaker
- Portfolio-level risk metrics (VaR, Beta, correlation exposure)
"""

import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
RISK_CONFIG_PATH = MEMORY_DIR / "risk_config.json"

# ---------------------------------------------------------------------------
# Default risk configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "max_position_pct": 20.0,       # Max % of portfolio in one position
    "max_drawdown_pct": 15.0,       # Circuit breaker drawdown %
    "default_stop_loss_pct": 5.0,   # Default stop-loss %
    "default_take_profit_pct": 10.0,# Default take-profit %
    "trailing_stop_pct": 3.0,       # Default trailing stop %
    "risk_per_trade_pct": 2.0,      # Risk per trade (for sizing)
    "circuit_breaker_active": False,
}


def load_config() -> dict:
    if RISK_CONFIG_PATH.exists():
        try:
            return json.loads(RISK_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    RISK_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Position sizing
# ---------------------------------------------------------------------------

def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Calculate Kelly Criterion fraction.

    Args:
        win_rate: Historical win rate (0.0 - 1.0).
        avg_win: Average winning trade amount.
        avg_loss: Average losing trade amount (positive number).

    Returns:
        Fraction of capital to risk (0.0 - 1.0), half-Kelly for safety.
    """
    if avg_loss <= 0 or win_rate <= 0:
        return 0.0
    b = avg_win / avg_loss  # win/loss ratio
    q = 1 - win_rate
    kelly = (win_rate * b - q) / b
    # Half-Kelly for safety
    return max(0.0, min(kelly * 0.5, 0.25))


def fixed_fractional_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
) -> dict:
    """Calculate position size using fixed-fractional method.

    Args:
        capital: Total available capital.
        risk_pct: Percentage of capital willing to risk (e.g. 2.0).
        entry_price: Planned entry price.
        stop_loss_price: Planned stop-loss price.

    Returns:
        Dict with quantity, usd_amount, risk_amount.
    """
    risk_amount = capital * (risk_pct / 100)
    price_risk = abs(entry_price - stop_loss_price)
    if price_risk <= 0:
        return {"quantity": 0, "usd_amount": 0, "risk_amount": risk_amount, "error": "Stop loss equals entry."}

    quantity = risk_amount / price_risk
    usd_amount = quantity * entry_price

    # Cap at max position %
    config = load_config()
    max_usd = capital * (config["max_position_pct"] / 100)
    if usd_amount > max_usd:
        usd_amount = max_usd
        quantity = usd_amount / entry_price

    return {
        "quantity": round(quantity, 6),
        "usd_amount": round(usd_amount, 2),
        "risk_amount": round(risk_amount, 2),
        "risk_per_unit": round(price_risk, 2),
    }


def suggest_position_size(capital: float, entry_price: float, trade_history: list) -> dict:
    """Suggest position size based on trade history (Kelly) or defaults."""
    config = load_config()
    wins = [t for t in trade_history if t.get("pnl", 0) > 0]
    losses = [t for t in trade_history if t.get("pnl", 0) < 0]

    if len(wins) >= 3 and len(losses) >= 1:
        win_rate = len(wins) / (len(wins) + len(losses))
        avg_win = sum(t["pnl"] for t in wins) / len(wins)
        avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses))
        kelly_frac = kelly_criterion(win_rate, avg_win, avg_loss)
        suggested_usd = capital * kelly_frac
        method = "half_kelly"
    else:
        suggested_usd = capital * (config["risk_per_trade_pct"] / 100)
        kelly_frac = config["risk_per_trade_pct"] / 100
        method = "fixed_fractional"

    return {
        "method": method,
        "suggested_usd": round(suggested_usd, 2),
        "fraction": round(kelly_frac, 4),
        "max_usd": round(capital * config["max_position_pct"] / 100, 2),
    }


# ---------------------------------------------------------------------------
# Stop-loss / Take-profit / Trailing stop
# ---------------------------------------------------------------------------

def calculate_stop_take(
    entry_price: float,
    direction: str,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
) -> dict:
    """Calculate stop-loss and take-profit prices from percentages."""
    config = load_config()
    sl_pct = stop_loss_pct or config["default_stop_loss_pct"]
    tp_pct = take_profit_pct or config["default_take_profit_pct"]

    if direction == "long":
        sl_price = entry_price * (1 - sl_pct / 100)
        tp_price = entry_price * (1 + tp_pct / 100)
    else:
        sl_price = entry_price * (1 + sl_pct / 100)
        tp_price = entry_price * (1 - tp_pct / 100)

    risk_reward = tp_pct / sl_pct if sl_pct > 0 else 0
    return {
        "stop_loss": round(sl_price, 2),
        "take_profit": round(tp_price, 2),
        "stop_loss_pct": sl_pct,
        "take_profit_pct": tp_pct,
        "risk_reward": round(risk_reward, 2),
    }


def calculate_trailing_stop(entry_price: float, highest_price: float, trail_pct: float) -> float:
    """Calculate trailing stop price based on highest price reached."""
    return round(highest_price * (1 - trail_pct / 100), 2)


def check_exits(positions: list, live_prices: dict) -> list[dict]:
    """Check all open positions for stop-loss/take-profit/trailing stop triggers.

    Returns list of positions that should be closed with reason.
    """
    exits = []
    for pos in positions:
        price = live_prices.get(pos.get("asset"), 0)
        if not price:
            continue

        sl = pos.get("stop_loss")
        tp = pos.get("take_profit")
        trail = pos.get("trailing_stop_pct")
        direction = pos.get("direction", "long")

        # Update highest/lowest price for trailing stop tracking
        if direction == "long":
            highest = max(pos.get("highest_price", pos["entry_price"]), price)
            pos["highest_price"] = highest  # Persist for next check
        else:
            lowest = min(pos.get("lowest_price", pos["entry_price"]), price)
            pos["lowest_price"] = lowest  # Persist for next check

        if direction == "long":
            if sl and price <= sl:
                exits.append({**pos, "exit_reason": "stop_loss", "exit_price": price})
            elif tp and price >= tp:
                exits.append({**pos, "exit_reason": "take_profit", "exit_price": price})
            elif trail:
                trail_price = calculate_trailing_stop(pos["entry_price"], highest, trail)
                if price <= trail_price:
                    exits.append({**pos, "exit_reason": "trailing_stop", "exit_price": price})
        else:  # short — symmetric trailing stop
            if sl and price >= sl:
                exits.append({**pos, "exit_reason": "stop_loss", "exit_price": price})
            elif tp and price <= tp:
                exits.append({**pos, "exit_reason": "take_profit", "exit_price": price})
            elif trail:
                trail_price = lowest * (1 + trail / 100)
                if price >= trail_price:
                    exits.append({**pos, "exit_reason": "trailing_stop", "exit_price": price})

    return exits


# ---------------------------------------------------------------------------
# Portfolio risk metrics
# ---------------------------------------------------------------------------

def max_drawdown(equity_curve: list) -> dict:
    """Calculate maximum drawdown from equity curve data."""
    if not equity_curve:
        return {"max_drawdown_pct": 0, "max_drawdown_usd": 0, "peak": 0, "trough": 0}

    values = [p.get("equity", 0) for p in equity_curve]
    peak = values[0]
    max_dd = 0
    max_dd_usd = 0
    peak_val = values[0]
    trough_val = values[0]

    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            max_dd_usd = peak - v
            peak_val = peak
            trough_val = v

    return {
        "max_drawdown_pct": round(max_dd, 2),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "peak": round(peak_val, 2),
        "trough": round(trough_val, 2),
    }


def check_circuit_breaker(equity_curve: list) -> bool:
    """Return True if circuit breaker should trigger (drawdown exceeds limit)."""
    config = load_config()
    dd = max_drawdown(equity_curve)
    return dd["max_drawdown_pct"] >= config["max_drawdown_pct"]


def portfolio_var(returns: list[float], confidence: float = 0.95) -> float:
    """Calculate Value at Risk (historical method).

    Args:
        returns: List of daily return percentages.
        confidence: Confidence level (e.g. 0.95 for 95%).

    Returns:
        VaR as a percentage (negative number = loss).
    """
    if not returns or len(returns) < 5:
        return 0.0
    arr = np.array(returns)
    var = float(np.percentile(arr, (1 - confidence) * 100))
    return round(var, 4)


def correlation_matrix(price_series: dict[str, list[float]]) -> pd.DataFrame:
    """Calculate correlation matrix from dict of price series."""
    df = pd.DataFrame(price_series)
    returns = df.pct_change().dropna()
    return returns.corr().round(3)


# ---------------------------------------------------------------------------
# Portfolio exposure & charting (added 2026-02-26)
# ---------------------------------------------------------------------------

import plotly.graph_objects as go

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,11,18,0.95)",
    font={"color": "#c9d1d9", "family": "Inter, sans-serif"},
)

# Asset-class keyword mapping
_ASSET_CLASS_MAP = {
    "crypto": {"BTC", "ETH"},
    "commodity": {"GOLD", "SILVER", "OIL", "NATURAL GAS", "COPPER", "PLATINUM", "WHEAT"},
    "index": {"SP500", "NASDAQ", "S&P 500"},
    "forex": {"EUR_USD", "EURUSD"},
}


def _classify_asset(name: str) -> str:
    """Return the asset class for a given asset name."""
    upper = name.upper().strip()
    for cls, keywords in _ASSET_CLASS_MAP.items():
        if upper in keywords:
            return cls
    # Fallback heuristics
    if "USD" in upper:
        return "forex"
    return "other"


def portfolio_exposure(
    positions: list[dict],
    live_prices: dict[str, float],
    total_equity: float,
) -> dict:
    """Compute portfolio exposure breakdown.

    Args:
        positions: List of position dicts, each with at minimum:
            - "asset": str (e.g. "BTC", "Gold")
            - "quantity": float
            - "direction": "long" | "short"
        live_prices: Dict mapping asset name -> current price.
        total_equity: Total portfolio equity in USD.

    Returns:
        Dict with keys: by_asset, by_direction, by_asset_class,
        largest_position, concentration_warning.
    """
    if total_equity <= 0:
        return {
            "by_asset": {},
            "by_direction": {"long": 0.0, "short": 0.0},
            "by_asset_class": {"crypto": 0.0, "commodity": 0.0, "index": 0.0, "forex": 0.0},
            "largest_position": {"name": None, "pct": 0.0},
            "concentration_warning": False,
        }

    by_asset: dict[str, dict] = {}
    direction_totals = {"long": 0.0, "short": 0.0}
    class_totals: dict[str, float] = {}

    for pos in positions:
        asset = pos.get("asset", "Unknown")
        qty = abs(pos.get("quantity", 0))
        direction = pos.get("direction", "long")
        price = live_prices.get(asset, 0)
        usd_value = qty * price
        pct = (usd_value / total_equity * 100) if total_equity > 0 else 0.0

        by_asset[asset] = {
            "usd_value": round(usd_value, 2),
            "pct_of_portfolio": round(pct, 2),
            "direction": direction,
        }

        direction_totals[direction] = direction_totals.get(direction, 0.0) + pct

        asset_class = _classify_asset(asset)
        class_totals[asset_class] = class_totals.get(asset_class, 0.0) + pct

    # Ensure all standard classes appear
    by_asset_class = {
        "crypto": round(class_totals.get("crypto", 0.0), 2),
        "commodity": round(class_totals.get("commodity", 0.0), 2),
        "index": round(class_totals.get("index", 0.0), 2),
        "forex": round(class_totals.get("forex", 0.0), 2),
    }
    # Include "other" only if present
    if class_totals.get("other", 0) > 0:
        by_asset_class["other"] = round(class_totals["other"], 2)

    by_direction = {
        "long": round(direction_totals.get("long", 0.0), 2),
        "short": round(direction_totals.get("short", 0.0), 2),
    }

    # Largest position
    largest_name = None
    largest_pct = 0.0
    for name, info in by_asset.items():
        if info["pct_of_portfolio"] > largest_pct:
            largest_pct = info["pct_of_portfolio"]
            largest_name = name

    concentration_warning = largest_pct > 30.0

    return {
        "by_asset": by_asset,
        "by_direction": by_direction,
        "by_asset_class": by_asset_class,
        "largest_position": {"name": largest_name, "pct": round(largest_pct, 2)},
        "concentration_warning": concentration_warning,
    }


def correlation_heatmap_chart(
    price_series: dict[str, list[float]],
    height: int = 400,
) -> go.Figure:
    """Plotly annotated heatmap of asset return correlations.

    Args:
        price_series: Dict of {asset_name: [price_list]}.
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    corr = correlation_matrix(price_series)
    labels = list(corr.columns)
    z = corr.values.tolist()

    # Build annotation text
    annotations = []
    for i, row_label in enumerate(labels):
        for j, col_label in enumerate(labels):
            val = z[i][j]
            annotations.append(
                dict(
                    x=col_label,
                    y=row_label,
                    text=f"{val:.2f}",
                    showarrow=False,
                    font=dict(color="#ffffff" if abs(val) > 0.5 else "#c9d1d9", size=11),
                )
            )

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=labels,
            y=labels,
            colorscale=[
                [0.0, "#da3633"],   # strong negative - red
                [0.5, "#1a1e2e"],   # zero - dark neutral
                [1.0, "#3fb950"],   # strong positive - green
            ],
            zmin=-1,
            zmax=1,
            colorbar=dict(
                title="Corr",
                tickvals=[-1, -0.5, 0, 0.5, 1],
                ticktext=["-1", "-0.5", "0", "0.5", "1"],
            ),
        )
    )

    fig.update_layout(
        **DARK_LAYOUT,
        height=height,
        title=dict(text="Asset Correlation Matrix", font=dict(size=14)),
        xaxis=dict(side="bottom"),
        annotations=annotations,
        margin=dict(l=80, r=40, t=50, b=60),
    )

    return fig


def exposure_pie_chart(
    exposure_data: dict[str, float],
    height: int = 300,
) -> go.Figure:
    """Donut chart showing asset-class allocation.

    Args:
        exposure_data: The ``by_asset_class`` dict from portfolio_exposure()
            e.g. {"crypto": 40.0, "commodity": 30.0, "index": 20.0, "forex": 10.0}
        height: Chart height in pixels.

    Returns:
        Plotly Figure.
    """
    color_map = {
        "crypto": "#a371f7",
        "commodity": "#fd7e14",
        "index": "#3fb950",
        "forex": "#58a6ff",
        "other": "#6e7681",
    }

    # Filter out zero-value classes for cleaner chart
    labels = [k for k, v in exposure_data.items() if v > 0]
    values = [exposure_data[k] for k in labels]
    colors = [color_map.get(k, "#6e7681") for k in labels]

    fig = go.Figure(
        data=go.Pie(
            labels=[la.capitalize() for la in labels],
            values=values,
            hole=0.5,
            marker=dict(colors=colors, line=dict(color="#0d1117", width=2)),
            textinfo="label+percent",
            textfont=dict(size=12, color="#c9d1d9"),
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        **DARK_LAYOUT,
        height=height,
        title=dict(text="Asset Class Exposure", font=dict(size=14)),
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def calculate_portfolio_beta(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> float:
    """Calculate portfolio beta relative to a benchmark.

    Beta = Cov(portfolio, benchmark) / Var(benchmark).

    Args:
        portfolio_returns: List of portfolio daily returns (as decimals or %).
        benchmark_returns: List of benchmark daily returns (same scale).

    Returns:
        Beta as a float. Returns 0.0 if insufficient data.
    """
    if (
        not portfolio_returns
        or not benchmark_returns
        or len(portfolio_returns) < 5
        or len(benchmark_returns) < 5
    ):
        return 0.0

    # Align lengths (use the shorter of the two)
    n = min(len(portfolio_returns), len(benchmark_returns))
    p = np.array(portfolio_returns[-n:], dtype=float)
    b = np.array(benchmark_returns[-n:], dtype=float)

    var_b = float(np.var(b, ddof=1))
    if var_b == 0:
        return 0.0

    cov_pb = float(np.cov(p, b, ddof=1)[0][1])
    beta = cov_pb / var_b

    return round(beta, 4)
