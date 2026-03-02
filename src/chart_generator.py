"""Chart Generator Agent — creates interactive plotly charts for the dashboard.

Produces price charts with SMA overlays, RSI, MACD, Bollinger Bands,
and a signal score gauge. All charts are returned as plotly Figure objects
that Streamlit can render directly with st.plotly_chart().

Usage:
    from chart_generator import ChartGenerator
    gen = ChartGenerator()
    figures = gen.generate_all(ticker="BTC-USD", asset_name="BTC", tech=tech_dict, signal=signal_dict)
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

# ---------------------------------------------------------------------------
# Color palette (matches dashboard dark theme)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0d1117",
    "paper": "#161b22",
    "grid": "rgba(48, 54, 61, 0.3)",
    "text": "#c9d1d9",
    "text_dim": "#6e7681",
    "blue": "#58a6ff",
    "green": "#3fb950",
    "red": "#f85149",
    "orange": "#d29922",
    "purple": "#bc8cff",
    "cyan": "#39d2c0",
    "white": "#e6edf3",
    "sma20": "#58a6ff",
    "sma50": "#d29922",
    "sma200": "#bc8cff",
    "candle_up": "#3fb950",
    "candle_down": "#f85149",
    "bb_fill": "rgba(88, 166, 255, 0.06)",
    "bb_line": "rgba(88, 166, 255, 0.3)",
    "volume": "rgba(88, 166, 255, 0.25)",
}

def _base_layout(title: str = "", height: int = 400) -> dict:
    """Shared layout config for all charts."""
    return dict(
        title=dict(text=title, font=dict(size=14, color=COLORS["white"], family="Inter")),
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], size=11, family="Inter"),
        margin=dict(l=50, r=20, t=40, b=30),
        height=height,
        xaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            showgrid=True,
            rangeslider=dict(visible=False),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            showgrid=True,
            side="right",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color=COLORS["text_dim"]),
            orientation="h",
            y=1.02,
            x=0,
        ),
        hovermode="x unified",
    )


def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [ChartGenerator] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch OHLCV data from yfinance."""
    df = yf.download(ticker, period=period, interval="1d")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors="coerce")
    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to the dataframe."""
    close = df["Close"]

    # SMAs
    df["SMA_20"] = close.rolling(20).mean()
    df["SMA_50"] = close.rolling(50).mean()
    df["SMA_200"] = close.rolling(200).mean()

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Bollinger Bands
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["BB_Upper"] = bb_sma + 2 * bb_std
    df["BB_Lower"] = bb_sma - 2 * bb_std
    df["BB_Mid"] = bb_sma

    return df


# ---------------------------------------------------------------------------
# Chart: Price + SMA + Bollinger Bands
# ---------------------------------------------------------------------------

def chart_price(df: pd.DataFrame, asset_name: str, support: float = None, target: float = None) -> go.Figure:
    """Candlestick chart with SMA overlays and Bollinger Bands."""
    fig = go.Figure()

    # Bollinger Band fill
    if "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"],
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"],
            line=dict(width=0), fill="tonexty",
            fillcolor=COLORS["bb_fill"],
            name="Bollinger Bands",
            hoverinfo="skip",
        ))

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color=COLORS["candle_up"]), fillcolor=COLORS["candle_up"]),
        decreasing=dict(line=dict(color=COLORS["candle_down"]), fillcolor=COLORS["candle_down"]),
        name="Price",
        showlegend=False,
    ))

    # SMAs
    for col, color, label in [
        ("SMA_20", COLORS["sma20"], "SMA 20"),
        ("SMA_50", COLORS["sma50"], "SMA 50"),
        ("SMA_200", COLORS["sma200"], "SMA 200"),
    ]:
        if col in df.columns and df[col].notna().any():
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col],
                line=dict(color=color, width=1.5),
                name=label,
            ))

    # Support / Target lines
    if support:
        fig.add_hline(
            y=support, line_dash="dash", line_color=COLORS["red"],
            annotation_text=f"Support ${support:,.0f}",
            annotation_font_color=COLORS["red"],
            annotation_font_size=10,
        )
    if target:
        fig.add_hline(
            y=target, line_dash="dash", line_color=COLORS["green"],
            annotation_text=f"Target ${target:,.0f}",
            annotation_font_color=COLORS["green"],
            annotation_font_size=10,
        )

    layout = _base_layout(f"{asset_name} — Price & Indicators", height=450)
    layout["yaxis"]["title"] = "Price (USD)"
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Chart: RSI
# ---------------------------------------------------------------------------

def chart_rsi(df: pd.DataFrame, asset_name: str) -> go.Figure:
    """RSI chart with overbought/oversold zones."""
    fig = go.Figure()

    # RSI line
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        line=dict(color=COLORS["cyan"], width=2),
        name="RSI-14",
        fill="tozeroy",
        fillcolor="rgba(57, 210, 192, 0.05)",
    ))

    # Overbought / oversold zones
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["red"],
                  annotation_text="Overbought (70)", annotation_font_size=9,
                  annotation_font_color=COLORS["red"])
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["green"],
                  annotation_text="Oversold (30)", annotation_font_size=9,
                  annotation_font_color=COLORS["green"])
    fig.add_hline(y=50, line_dash="dot", line_color=COLORS["grid"])

    # Zone fills
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248, 81, 73, 0.05)",
                  line_width=0, layer="below")
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(63, 185, 80, 0.05)",
                  line_width=0, layer="below")

    layout = _base_layout(f"{asset_name} — RSI (14)", height=220)
    layout["yaxis"]["range"] = [0, 100]
    layout["yaxis"]["title"] = "RSI"
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Chart: MACD
# ---------------------------------------------------------------------------

def chart_macd(df: pd.DataFrame, asset_name: str) -> go.Figure:
    """MACD chart with signal line and histogram."""
    fig = go.Figure()

    # Histogram
    colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in df["MACD_Hist"].fillna(0)]
    fig.add_trace(go.Bar(
        x=df.index, y=df["MACD_Hist"],
        marker_color=colors,
        name="Histogram",
        opacity=0.6,
    ))

    # MACD line
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"],
        line=dict(color=COLORS["blue"], width=2),
        name="MACD",
    ))

    # Signal line
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD_Signal"],
        line=dict(color=COLORS["orange"], width=1.5, dash="dot"),
        name="Signal",
    ))

    fig.add_hline(y=0, line_color=COLORS["grid"])

    layout = _base_layout(f"{asset_name} — MACD (12, 26, 9)", height=220)
    layout["yaxis"]["title"] = "MACD"
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Chart: Signal Score Gauge
# ---------------------------------------------------------------------------

def chart_signal_gauge(score: int, label: str, asset_name: str) -> go.Figure:
    """Gauge chart showing the signal score from -100 to +100."""
    if score >= 60:
        bar_color = COLORS["green"]
    elif score >= 35:
        bar_color = "#20c997"
    elif score >= -10:
        bar_color = COLORS["text_dim"]
    elif score >= -35:
        bar_color = COLORS["orange"]
    else:
        bar_color = COLORS["red"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        title=dict(text=f"{asset_name} Signal", font=dict(size=16, color=COLORS["white"])),
        number=dict(font=dict(size=36, color=bar_color, family="JetBrains Mono"), suffix="/100"),
        gauge=dict(
            axis=dict(range=[-100, 100], tickcolor=COLORS["text_dim"],
                      tickfont=dict(size=10, color=COLORS["text_dim"])),
            bar=dict(color=bar_color, thickness=0.75),
            bgcolor=COLORS["bg"],
            bordercolor=COLORS["grid"],
            steps=[
                dict(range=[-100, -35], color="rgba(248, 81, 73, 0.1)"),
                dict(range=[-35, -10], color="rgba(210, 153, 34, 0.08)"),
                dict(range=[-10, 35], color="rgba(110, 118, 129, 0.08)"),
                dict(range=[35, 60], color="rgba(32, 201, 151, 0.08)"),
                dict(range=[60, 100], color="rgba(63, 185, 80, 0.1)"),
            ],
            threshold=dict(
                line=dict(color=COLORS["white"], width=2),
                thickness=0.8,
                value=score,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"]),
        height=250,
        margin=dict(l=30, r=30, t=60, b=10),
    )

    # Add label annotation
    fig.add_annotation(
        text=f"<b>{label}</b>",
        x=0.5, y=-0.05,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(size=18, color=bar_color, family="JetBrains Mono"),
    )

    return fig


# ---------------------------------------------------------------------------
# Chart: Volume
# ---------------------------------------------------------------------------

def chart_volume(df: pd.DataFrame, asset_name: str) -> go.Figure:
    """Volume bar chart."""
    colors = [
        COLORS["candle_up"] if df["Close"].iloc[i] >= df["Open"].iloc[i]
        else COLORS["candle_down"]
        for i in range(len(df))
    ]

    fig = go.Figure(go.Bar(
        x=df.index, y=df["Volume"],
        marker_color=colors,
        opacity=0.5,
        name="Volume",
    ))

    layout = _base_layout(f"{asset_name} — Volume", height=180)
    layout["yaxis"]["title"] = "Volume"
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Chart: News Sentiment Bar
# ---------------------------------------------------------------------------

def chart_news_sentiment(news_data: dict) -> go.Figure:
    """Horizontal bar showing news sentiment breakdown."""
    articles = news_data.get("articles", [])
    relevant = [a for a in articles if a.get("relevant")]

    bull = sum(1 for a in relevant if a["sentiment"] > 0)
    neutral = sum(1 for a in relevant if a["sentiment"] == 0)
    bear = sum(1 for a in relevant if a["sentiment"] < 0)
    total = bull + neutral + bear or 1

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=["Sentiment"],
        x=[bull / total * 100],
        orientation="h",
        marker_color=COLORS["green"],
        name=f"Bullish ({bull})",
        text=f"{bull}", textposition="inside",
        textfont=dict(color="white", size=11),
    ))
    fig.add_trace(go.Bar(
        y=["Sentiment"],
        x=[neutral / total * 100],
        orientation="h",
        marker_color=COLORS["text_dim"],
        name=f"Neutral ({neutral})",
        text=f"{neutral}", textposition="inside",
        textfont=dict(color="white", size=11),
    ))
    fig.add_trace(go.Bar(
        y=["Sentiment"],
        x=[bear / total * 100],
        orientation="h",
        marker_color=COLORS["red"],
        name=f"Bearish ({bear})",
        text=f"{bear}", textposition="inside",
        textfont=dict(color="white", size=11),
    ))

    fig.update_layout(
        barmode="stack",
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], size=11),
        height=100,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]),
        yaxis=dict(showgrid=False, showticklabels=False),
        legend=dict(
            orientation="h", y=-0.3,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color=COLORS["text_dim"]),
        ),
        showlegend=True,
    )
    return fig


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class ChartGenerator:
    """Generates all charts for a given asset."""

    def generate_all(
        self,
        ticker: str,
        asset_name: str,
        config: dict | None = None,
        signal: dict | None = None,
        news_data: dict | None = None,
        period: str = "6mo",
    ) -> dict[str, go.Figure]:
        """Generate all chart figures for an asset.

        Returns dict mapping chart name to plotly Figure.
        """
        log(f"Generating charts for {asset_name} ({ticker})...")

        df = fetch_ohlcv(ticker, period)
        if df.empty:
            log(f"ERROR: No data for {ticker}")
            return {}

        df = compute_indicators(df)

        support = config.get("support") if config else None
        target = config.get("target") if config else None

        figures = {}

        # Price chart
        figures["price"] = chart_price(df, asset_name, support=support, target=target)

        # RSI
        figures["rsi"] = chart_rsi(df, asset_name)

        # MACD
        figures["macd"] = chart_macd(df, asset_name)

        # Volume
        if "Volume" in df.columns and df["Volume"].sum() > 0:
            figures["volume"] = chart_volume(df, asset_name)

        # Signal gauge
        if signal:
            figures["gauge"] = chart_signal_gauge(
                signal["score"], signal["label"], asset_name
            )

        # News sentiment
        if news_data and news_data.get("articles"):
            figures["news_sentiment"] = chart_news_sentiment(news_data)

        log(f"Generated {len(figures)} charts for {asset_name}.")
        return figures


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = ChartGenerator()
    figs = gen.generate_all(
        ticker="BTC-USD",
        asset_name="BTC",
        config={"support": 62000, "target": 95000},
        signal={"score": 45, "label": "BUY"},
    )
    print(f"\nGenerated {len(figs)} charts: {', '.join(figs.keys())}")
    # Save as HTML for preview
    for name, fig in figs.items():
        fig.write_html(str(PROJECT_ROOT / f"src/data/chart_{name}.html"))
        print(f"  Saved: chart_{name}.html")
