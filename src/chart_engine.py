"""Chart Engine — Interactive candlestick charts with pattern detection.

Provides Plotly-based interactive charts with:
- Candlestick charts with zoom/pan
- Technical indicator overlays (SMA, EMA, Bollinger Bands, RSI, MACD)
- Automated candlestick pattern detection
- Support/resistance level identification
- Multi-timeframe analysis
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Dark theme constants
# ---------------------------------------------------------------------------
DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,11,18,0.95)",
    font={"color": "#c9d1d9", "family": "Inter, sans-serif"},
    xaxis={"gridcolor": "rgba(48,54,61,0.3)", "showgrid": True},
    yaxis={"gridcolor": "rgba(48,54,61,0.3)", "showgrid": True},
)
UP_COLOR = "#3fb950"
DOWN_COLOR = "#f85149"
ACCENT = "#58a6ff"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_ohlcv(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data from yfinance. Returns DataFrame with standard columns."""
    import yfinance as yf
    # Use Ticker().history() for thread safety (yf.download uses shared global state)
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if df is None or df.empty:
        return pd.DataFrame()
    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # Guard: ensure required columns exist
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame()
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    return df


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute common technical indicators and append as columns."""
    c = df["Close"]
    # SMA
    df["SMA_20"] = c.rolling(20).mean()
    df["SMA_50"] = c.rolling(50).mean()
    df["SMA_200"] = c.rolling(200).mean()
    # EMA
    df["EMA_12"] = c.ewm(span=12, adjust=False).mean()
    df["EMA_26"] = c.ewm(span=26, adjust=False).mean()
    # Bollinger Bands
    df["BB_MID"] = df["SMA_20"]
    bb_std = c.rolling(20).std()
    df["BB_UPPER"] = df["BB_MID"] + 2 * bb_std
    df["BB_LOWER"] = df["BB_MID"] - 2 * bb_std
    # RSI-14
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    # MACD
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
    return df


# ---------------------------------------------------------------------------
# Candlestick pattern detection
# ---------------------------------------------------------------------------

def detect_patterns(df: pd.DataFrame) -> list[dict]:
    """Detect common candlestick patterns. Returns list of pattern annotations."""
    patterns = []
    o, h, l, c = df["Open"].values, df["High"].values, df["Low"].values, df["Close"].values
    body = np.abs(c - o)
    wick_upper = h - np.maximum(c, o)
    wick_lower = np.minimum(c, o) - l
    avg_body = pd.Series(body).rolling(20).mean().values

    for i in range(2, len(df)):
        idx = df.index[i]
        # Doji: body < 10% of range
        rng = h[i] - l[i]
        if rng > 0 and body[i] / rng < 0.1:
            patterns.append({"date": idx, "pattern": "Doji", "type": "neutral", "price": h[i]})

        # Hammer: small body at top, long lower wick
        if wick_lower[i] > 2 * body[i] and wick_upper[i] < body[i] * 0.5 and c[i] > o[i]:
            patterns.append({"date": idx, "pattern": "Hammer", "type": "bullish", "price": l[i]})

        # Shooting Star: small body at bottom, long upper wick
        if wick_upper[i] > 2 * body[i] and wick_lower[i] < body[i] * 0.5 and c[i] < o[i]:
            patterns.append({"date": idx, "pattern": "Shooting Star", "type": "bearish", "price": h[i]})

        # Engulfing patterns
        if i >= 1:
            # Bullish engulfing
            if c[i-1] < o[i-1] and c[i] > o[i] and o[i] <= c[i-1] and c[i] >= o[i-1]:
                patterns.append({"date": idx, "pattern": "Bullish Engulfing", "type": "bullish", "price": l[i]})
            # Bearish engulfing
            if c[i-1] > o[i-1] and c[i] < o[i] and o[i] >= c[i-1] and c[i] <= o[i-1]:
                patterns.append({"date": idx, "pattern": "Bearish Engulfing", "type": "bearish", "price": h[i]})

        # Morning Star (3-bar)
        if i >= 2:
            if (c[i-2] < o[i-2] and  # big red
                body[i-1] < avg_body[i-1] * 0.5 if avg_body[i-1] and avg_body[i-1] > 0 else False and  # small body
                c[i] > o[i] and c[i] > (o[i-2] + c[i-2]) / 2):  # big green past midpoint
                patterns.append({"date": idx, "pattern": "Morning Star", "type": "bullish", "price": l[i]})

    return patterns


# ---------------------------------------------------------------------------
# Support / Resistance
# ---------------------------------------------------------------------------

def find_support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 5) -> dict:
    """Find support and resistance levels using local extrema."""
    from scipy.signal import argrelextrema

    highs = df["High"].values
    lows = df["Low"].values

    res_idx = argrelextrema(highs, np.greater, order=window)[0]
    sup_idx = argrelextrema(lows, np.less, order=window)[0]

    resistance = sorted(set(round(float(highs[i]), 2) for i in res_idx))[-num_levels:]
    support = sorted(set(round(float(lows[i]), 2) for i in sup_idx))[:num_levels]

    return {"support": support, "resistance": resistance}


# ---------------------------------------------------------------------------
# TrendSpider-style Support/Resistance with zone clustering
# ---------------------------------------------------------------------------

def detect_support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 3) -> dict:
    """Detect support/resistance levels with zone clustering.

    Uses rolling-window local extrema, then clusters nearby levels (within
    1.5 % of each other) into zones.  Returns the *num_levels* strongest
    support and resistance levels together with their zone boundaries.

    Returns
    -------
    dict with keys:
        support  : list of {"level": float, "zone_lo": float, "zone_hi": float, "touches": int}
        resistance: list of {"level": float, "zone_lo": float, "zone_hi": float, "touches": int}
    """
    if len(df) < window * 2:
        return {"support": [], "resistance": []}

    from scipy.signal import argrelextrema

    highs = df["High"].values
    lows = df["Low"].values

    # --- find local extrema ---
    res_idx = argrelextrema(highs, np.greater, order=window)[0]
    sup_idx = argrelextrema(lows, np.less, order=window)[0]

    def _cluster_levels(prices: list[float], cluster_pct: float = 0.015) -> list[dict]:
        """Group price levels within *cluster_pct* of each other."""
        if not prices:
            return []
        prices = sorted(prices)
        clusters: list[list[float]] = [[prices[0]]]
        for p in prices[1:]:
            if abs(p - clusters[-1][-1]) / max(clusters[-1][-1], 1e-9) <= cluster_pct:
                clusters[-1].append(p)
            else:
                clusters.append([p])
        results = []
        for c in clusters:
            avg = float(np.mean(c))
            results.append({
                "level": round(avg, 2),
                "zone_lo": round(float(min(c)), 2),
                "zone_hi": round(float(max(c)), 2),
                "touches": len(c),
            })
        # Sort by most touches first (strongest zones)
        results.sort(key=lambda x: x["touches"], reverse=True)
        return results

    res_prices = [float(highs[i]) for i in res_idx]
    sup_prices = [float(lows[i]) for i in sup_idx]

    resistance = _cluster_levels(res_prices)[:num_levels]
    support = _cluster_levels(sup_prices)[:num_levels]

    return {"support": support, "resistance": resistance}


# ---------------------------------------------------------------------------
# TrendSpider-style automatic trendline detection
# ---------------------------------------------------------------------------

def detect_trendlines(df: pd.DataFrame, window: int = 20) -> list[dict]:
    """Detect uptrend and downtrend lines from swing points.

    Connects recent swing lows (uptrend) and swing highs (downtrend).
    Uses ``scipy.stats.linregress`` to fit a line through the last N swing
    points and only returns the trendline when R-squared > 0.7.

    Returns
    -------
    list of dicts, each with:
        direction   : "up" | "down"
        start_date  : datetime-like (index value)
        end_date    : datetime-like
        start_price : float
        end_price   : float
        r_squared   : float
        slope       : float
    """
    if len(df) < window * 2:
        return []

    from scipy.signal import argrelextrema
    from scipy.stats import linregress

    highs = df["High"].values
    lows = df["Low"].values

    swing_low_idx = argrelextrema(lows, np.less, order=window)[0]
    swing_high_idx = argrelextrema(highs, np.greater, order=window)[0]

    trendlines: list[dict] = []

    def _fit_trendline(indices, prices, direction: str):
        """Fit a line through the most recent swing points (min 3)."""
        if len(indices) < 3:
            # Fall back to 2-point line (no R-squared filter)
            if len(indices) == 2:
                i0, i1 = indices[0], indices[1]
                p0, p1 = float(prices[i0]), float(prices[i1])
                slope_dir = p1 - p0
                if direction == "up" and slope_dir <= 0:
                    return
                if direction == "down" and slope_dir >= 0:
                    return
                trendlines.append({
                    "direction": direction,
                    "start_date": df.index[i0],
                    "end_date": df.index[i1],
                    "start_price": round(p0, 2),
                    "end_price": round(p1, 2),
                    "r_squared": 1.0,
                    "slope": round(slope_dir / max(i1 - i0, 1), 4),
                })
            return

        # Use last 5 swing points max for a recent trendline
        recent = indices[-5:]
        x = np.array(recent, dtype=float)
        y = np.array([float(prices[i]) for i in recent])

        result = linregress(x, y)
        r_sq = result.rvalue ** 2

        if r_sq < 0.7:
            return
        # Ensure direction matches
        if direction == "up" and result.slope <= 0:
            return
        if direction == "down" and result.slope >= 0:
            return

        start_i = int(recent[0])
        end_i = int(recent[-1])
        # Extend the trendline to the current bar for visual projection
        last_i = len(df) - 1
        projected_end_price = result.intercept + result.slope * last_i

        trendlines.append({
            "direction": direction,
            "start_date": df.index[start_i],
            "end_date": df.index[last_i],
            "start_price": round(float(result.intercept + result.slope * start_i), 2),
            "end_price": round(float(projected_end_price), 2),
            "r_squared": round(r_sq, 3),
            "slope": round(float(result.slope), 4),
        })

    _fit_trendline(swing_low_idx, lows, "up")
    _fit_trendline(swing_high_idx, highs, "down")

    return trendlines


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def build_candlestick_chart(
    df: pd.DataFrame,
    title: str = "",
    show_volume: bool = True,
    show_bb: bool = True,
    show_sma: bool = True,
    show_patterns: bool = True,
    show_sr: bool = True,
    height: int = 600,
) -> go.Figure:
    """Build a full interactive candlestick chart with indicators."""
    df = add_indicators(df)

    rows = 3 if show_volume else 2
    row_heights = [0.6, 0.2, 0.2] if show_volume else [0.7, 0.3]
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=[title, "Volume", "RSI"] if show_volume else [title, "RSI"],
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing_line_color=UP_COLOR, decreasing_line_color=DOWN_COLOR,
        name="Price",
    ), row=1, col=1)

    # SMA overlays
    if show_sma:
        for col, color, name in [("SMA_20", "#ffa657", "SMA 20"), ("SMA_50", "#58a6ff", "SMA 50")]:
            if col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col], mode="lines",
                    line={"color": color, "width": 1}, name=name, opacity=0.7,
                ), row=1, col=1)

    # Bollinger Bands
    if show_bb and "BB_UPPER" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_UPPER"], mode="lines",
                                 line={"color": "rgba(136,198,255,0.3)", "width": 1},
                                 name="BB Upper", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_LOWER"], mode="lines",
                                 line={"color": "rgba(136,198,255,0.3)", "width": 1},
                                 fill="tonexty", fillcolor="rgba(88,166,255,0.05)",
                                 name="BB", showlegend=True), row=1, col=1)

    # Support / Resistance
    if show_sr and len(df) > 40:
        sr = find_support_resistance(df)
        for level in sr["resistance"]:
            fig.add_hline(y=level, line_dash="dot", line_color="rgba(248,81,73,0.4)",
                          annotation_text=f"R {level:,.2f}", annotation_font_color="#f85149",
                          row=1, col=1)
        for level in sr["support"]:
            fig.add_hline(y=level, line_dash="dot", line_color="rgba(63,185,80,0.4)",
                          annotation_text=f"S {level:,.2f}", annotation_font_color="#3fb950",
                          row=1, col=1)

    # Pattern annotations
    if show_patterns:
        pats = detect_patterns(df)
        for p in pats[-15:]:  # limit annotations
            color = UP_COLOR if p["type"] == "bullish" else DOWN_COLOR if p["type"] == "bearish" else "#ffa657"
            fig.add_annotation(
                x=p["date"], y=p["price"], text=p["pattern"],
                showarrow=True, arrowhead=2, arrowcolor=color,
                font={"size": 9, "color": color}, arrowsize=0.8,
                row=1, col=1,
            )

    # Volume
    vol_row = 2 if show_volume else None
    if show_volume:
        colors = [UP_COLOR if c >= o else DOWN_COLOR
                  for c, o in zip(df["Close"].values, df["Open"].values)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"], marker_color=colors,
            name="Volume", showlegend=False, opacity=0.6,
        ), row=2, col=1)

    # RSI
    rsi_row = 3 if show_volume else 2
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], mode="lines",
            line={"color": ACCENT, "width": 1.5}, name="RSI",
        ), row=rsi_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(248,81,73,0.5)", row=rsi_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(63,185,80,0.5)", row=rsi_row, col=1)

    # Layout
    fig.update_layout(
        **DARK_LAYOUT,
        height=height,
        margin=dict(t=40, b=30, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font={"size": 10}),
        xaxis_rangeslider_visible=False,
        showlegend=True,
    )
    # Disable all grid for subplot xaxes
    for i in range(1, rows + 1):
        fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)", row=i, col=1)
        fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)", row=i, col=1)

    return fig


def build_macd_chart(df: pd.DataFrame, height: int = 200) -> go.Figure:
    """Build standalone MACD chart."""
    df = add_indicators(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], mode="lines",
                             line={"color": ACCENT, "width": 1.5}, name="MACD"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_SIGNAL"], mode="lines",
                             line={"color": "#ffa657", "width": 1.5}, name="Signal"))
    colors = [UP_COLOR if v >= 0 else DOWN_COLOR for v in df["MACD_HIST"].values]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_HIST"], marker_color=colors,
                         name="Histogram", opacity=0.6))
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=20, b=20, l=60, r=20),
                      showlegend=True, legend=dict(orientation="h", y=1.15))
    return fig


def build_multi_timeframe(ticker: str) -> dict[str, pd.DataFrame]:
    """Fetch data for multiple timeframes."""
    frames = {}
    for label, period, interval in [
        ("1D (5m)", "1d", "5m"), ("1W (15m)", "5d", "15m"),
        ("1M", "1mo", "1d"), ("3M", "3mo", "1d"),
        ("6M", "6mo", "1d"), ("1Y", "1y", "1d"),
    ]:
        df = fetch_ohlcv(ticker, period=period, interval=interval)
        if not df.empty:
            frames[label] = df
    return frames
