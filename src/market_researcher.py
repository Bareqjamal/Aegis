"""Market Researcher — fetch asset data and compute technical indicators.

Usage:
    python market_researcher.py [--symbol GC=F] [--period 1y]
"""

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def fetch_and_analyze(symbol: str = "GC=F", period: str = "1y") -> dict:
    """Fetch OHLCV data for a symbol and compute key technicals.

    Args:
        symbol: yfinance ticker (GC=F for Gold futures).
        period: yfinance period string.

    Returns:
        Dict with dataframe, current price, SMA values, and signal.
    """
    print(f"Fetching {symbol} data (period={period})...")
    df = yf.download(symbol, period=period, interval="1d")

    if df.empty:
        raise ValueError(f"No data returned for {symbol}. Check the ticker.")

    # Flatten multi-level columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.apply(pd.to_numeric, errors="coerce")

    csv_path = DATA_DIR / f"{symbol.replace('=', '_').lower()}_daily.csv"
    df.to_csv(csv_path)
    print(f"Saved {len(df)} rows to {csv_path}")

    close = df["Close"]
    current_price = close.iloc[-1]

    # Compute SMAs on full history (need >= 200 rows for SMA-200)
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    sma_50_latest = sma_50.iloc[-1] if len(sma_50.dropna()) > 0 else None
    sma_200_latest = sma_200.iloc[-1] if len(sma_200.dropna()) > 0 else None

    # Determine trend signal
    if sma_50_latest and sma_200_latest:
        if sma_50_latest > sma_200_latest:
            trend = "BULLISH (Golden Cross — SMA-50 above SMA-200)"
        else:
            trend = "BEARISH (Death Cross — SMA-50 below SMA-200)"
    else:
        trend = "INSUFFICIENT DATA for SMA-200 (need >= 200 trading days)"

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_latest = rsi.iloc[-1] if len(rsi.dropna()) > 0 else None

    # Last 30 days subset
    last_30 = df.tail(30)
    high_30 = last_30["High"].max()
    low_30 = last_30["Low"].min()
    avg_volume_30 = last_30["Volume"].mean()

    result = {
        "symbol": symbol,
        "rows_fetched": len(df),
        "current_price": round(current_price, 2),
        "sma_50": round(sma_50_latest, 2) if sma_50_latest else None,
        "sma_200": round(sma_200_latest, 2) if sma_200_latest else None,
        "trend_signal": trend,
        "rsi_14": round(rsi_latest, 2) if rsi_latest else None,
        "last_30d_high": round(high_30, 2),
        "last_30d_low": round(low_30, 2),
        "last_30d_avg_volume": int(avg_volume_30) if pd.notna(avg_volume_30) else 0,
        "csv_path": str(csv_path),
    }

    return result


def print_report(r: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  MARKET RESEARCH REPORT: {r['symbol']}")
    print(f"{'='*60}")
    print(f"  Data points:       {r['rows_fetched']} daily rows")
    print(f"  Current Price:     ${r['current_price']:,.2f}")
    print(f"  SMA-50:            ${r['sma_50']:,.2f}" if r["sma_50"] else "  SMA-50:            N/A")
    print(f"  SMA-200:           ${r['sma_200']:,.2f}" if r["sma_200"] else "  SMA-200:            N/A")
    print(f"  Trend Signal:      {r['trend_signal']}")
    print(f"  RSI-14:            {r['rsi_14']}" if r["rsi_14"] else "  RSI-14:            N/A")
    print(f"  30-Day High:       ${r['last_30d_high']:,.2f}")
    print(f"  30-Day Low:        ${r['last_30d_low']:,.2f}")
    print(f"  30-Day Avg Volume: {r['last_30d_avg_volume']:,}")
    print(f"  Data saved to:     {r['csv_path']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and analyze market data")
    parser.add_argument("--symbol", default="GC=F", help="yfinance ticker (default: GC=F for Gold)")
    parser.add_argument("--period", default="1y", help="Data period (default: 1y)")
    args = parser.parse_args()

    try:
        result = fetch_and_analyze(symbol=args.symbol, period=args.period)
        print_report(result)
    except Exception as e:
        print(f"ERROR: {e}")
        # Log to error memory
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory"))
        from memory_manager import add_lesson
        add_lesson(
            category="data",
            what_happened=f"market_researcher.py failed for {args.symbol}: {e}",
            root_cause=str(type(e).__name__),
            prevention_rule=f"Verify ticker '{args.symbol}' is valid on yfinance before use.",
            related_ticket="AEGIS-009",
        )
        print("Error lesson logged to memory.")
        raise
