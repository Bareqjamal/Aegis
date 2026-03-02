"""Sector Analysis — Sector heatmaps, correlation matrices, market breadth.

Provides:
- Sector ETF performance for treemap visualization
- Correlation matrix across watchlist assets
- Market breadth indicators
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,11,18,0.95)",
    font={"color": "#c9d1d9", "family": "Inter, sans-serif"},
)

# Standard sector ETFs
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Consumer Disc.": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication": "XLC",
}


def get_sector_performance(period: str = "1mo") -> list[dict]:
    """Fetch sector ETF performance for the given period."""
    import yfinance as yf
    tickers_str = " ".join(SECTOR_ETFS.values())
    try:
        df = yf.download(tickers_str, period=period, progress=False)
        if df.empty:
            return []
    except Exception:
        return []

    results = []
    for name, ticker in SECTOR_ETFS.items():
        try:
            if isinstance(df.columns, pd.MultiIndex):
                close = df["Close"][ticker].dropna()
            else:
                close = df["Close"].dropna()
            if len(close) >= 2:
                change_pct = round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2)
                results.append({
                    "sector": name,
                    "ticker": ticker,
                    "change_pct": float(change_pct),
                    "price": round(float(close.iloc[-1]), 2),
                })
        except Exception:
            pass
    return results


def build_sector_treemap(sector_data: list[dict], height: int = 400) -> go.Figure:
    """Build a sector performance treemap."""
    if not sector_data:
        return go.Figure()

    sectors = [d["sector"] for d in sector_data]
    changes = [d["change_pct"] for d in sector_data]
    abs_changes = [abs(c) + 0.5 for c in changes]  # sizing
    labels = [f"{s}<br>{c:+.2f}%" for s, c in zip(sectors, changes)]

    fig = px.treemap(
        names=labels,
        parents=["" for _ in sectors],
        values=abs_changes,
        color=changes,
        color_continuous_scale=["#f85149", "#161b22", "#3fb950"],
        color_continuous_midpoint=0,
    )
    fig.update_layout(
        **DARK_LAYOUT,
        height=height,
        margin=dict(t=30, b=10, l=10, r=10),
        coloraxis_colorbar=dict(title="Change %", ticksuffix="%"),
    )
    fig.update_traces(textfont=dict(size=14, color="white"))
    return fig


def get_correlation_matrix(tickers: dict[str, str], period: str = "3mo") -> pd.DataFrame:
    """Calculate correlation matrix for given assets.

    Args:
        tickers: {asset_name: yahoo_ticker}
        period: yfinance period string.

    Returns:
        Correlation DataFrame with asset names as index/columns.
    """
    import yfinance as yf
    if not tickers:
        return pd.DataFrame()

    ticker_str = " ".join(tickers.values())
    try:
        df = yf.download(ticker_str, period=period, progress=False)
        if df.empty:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    prices = pd.DataFrame()
    for name, tick in tickers.items():
        try:
            if isinstance(df.columns, pd.MultiIndex):
                prices[name] = df["Close"][tick]
            else:
                prices[name] = df["Close"]
        except Exception:
            pass

    if prices.empty or prices.shape[1] < 2:
        return pd.DataFrame()

    returns = prices.pct_change().dropna()
    return returns.corr().round(3)


def build_correlation_heatmap(corr_df: pd.DataFrame, height: int = 400) -> go.Figure:
    """Build correlation heatmap from correlation DataFrame."""
    if corr_df.empty:
        return go.Figure()

    fig = go.Figure(go.Heatmap(
        z=corr_df.values,
        x=corr_df.columns.tolist(),
        y=corr_df.index.tolist(),
        colorscale=[[0, "#f85149"], [0.5, "#161b22"], [1, "#3fb950"]],
        zmid=0,
        text=corr_df.values.round(2),
        texttemplate="%{text}",
        textfont={"size": 12, "color": "#c9d1d9"},
        colorbar=dict(title="Corr"),
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        height=height,
        margin=dict(t=30, b=30, l=80, r=20),
        xaxis=dict(side="bottom"),
    )
    return fig


def get_market_breadth() -> dict:
    """Calculate basic market breadth from major index components.

    Uses S&P 500 ETF (SPY) and a sample of large-cap stocks.
    """
    import yfinance as yf
    # Sample breadth using top 30 S&P stocks
    sample_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
        "UNH", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX",
        "MRK", "ABBV", "PEP", "KO", "COST", "AVGO", "LLY", "WMT",
        "MCD", "CSCO", "ACN", "TMO", "DHR", "ABT",
    ]
    try:
        df = yf.download(" ".join(sample_tickers), period="6mo", progress=False)
        if df.empty:
            return {}
    except Exception:
        return {}

    above_sma200 = 0
    above_sma50 = 0
    advancing = 0
    declining = 0
    total = 0

    for tick in sample_tickers:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                close = df["Close"][tick].dropna()
            else:
                close = df["Close"].dropna()
            if len(close) < 50:
                continue
            total += 1
            sma50 = close.rolling(50).mean().iloc[-1]
            current = close.iloc[-1]
            prev = close.iloc[-2]

            if current > sma50:
                above_sma50 += 1
            if len(close) >= 200:
                sma200 = close.rolling(200).mean().iloc[-1]
                if current > sma200:
                    above_sma200 += 1
            if current > prev:
                advancing += 1
            else:
                declining += 1
        except Exception:
            pass

    return {
        "total_stocks": total,
        "above_sma50": above_sma50,
        "above_sma50_pct": round(above_sma50 / total * 100, 1) if total else 0,
        "above_sma200": above_sma200,
        "above_sma200_pct": round(above_sma200 / total * 100, 1) if total else 0,
        "advancing": advancing,
        "declining": declining,
        "adv_dec_ratio": round(advancing / declining, 2) if declining > 0 else advancing,
    }
