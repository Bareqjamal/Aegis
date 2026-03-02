"""Fetch BTC-USD historical OHLCV data using yfinance."""

from pathlib import Path

import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SYMBOL = "BTC-USD"
OUTPUT_FILE = DATA_DIR / "btc_usd_daily.csv"


def fetch_btc_data(period: str = "5y") -> Path:
    """Download BTC-USD daily OHLCV data and save to CSV.

    Args:
        period: yfinance period string (e.g. "1y", "5y", "max").

    Returns:
        Path to the saved CSV file.
    """
    print(f"Fetching {SYMBOL} data for period={period}...")
    df = yf.download(SYMBOL, period=period, interval="1d")
    df.to_csv(OUTPUT_FILE)
    print(f"Saved {len(df)} rows to {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    fetch_btc_data()
