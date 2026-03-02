"""Cloud Function: Fetch live prices for all Aegis watchlist assets.

Triggered by Cloud Scheduler every 1-2 minutes.
Stores results in Google Cloud Storage as JSON.
Dashboard reads from GCS instead of calling yfinance directly.

Cost: ~$0.10/month (1,440 invocations/day)
"""

import json
import time
from datetime import datetime, timezone

import functions_framework
import yfinance as yf
from google.cloud import storage

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BUCKET_NAME = "aegis-market-data"          # GCS bucket for price data
PRICES_BLOB = "live/prices.json"           # Path in bucket
HISTORY_BLOB = "live/price_history.json"   # Rolling 24h history

# Default watchlist — same 12 assets as the main app
DEFAULT_ASSETS = {
    "Gold":        "GC=F",
    "BTC":         "BTC-USD",
    "ETH":         "ETH-USD",
    "Silver":      "SI=F",
    "Oil":         "CL=F",
    "Natural Gas": "NG=F",
    "S&P 500":     "^GSPC",
    "NASDAQ":      "^IXIC",
    "Copper":      "HG=F",
    "Platinum":    "PL=F",
    "Wheat":       "ZW=F",
    "EUR/USD":     "EURUSD=X",
}

# Price sanity bounds (same as src/config.py)
PRICE_BOUNDS = {
    "BTC-USD":   (1_000, 1_000_000),
    "ETH-USD":   (50, 25_000),
    "GC=F":      (500, 50_000),
    "SI=F":      (5, 200),
    "CL=F":      (5, 500),
    "NG=F":      (0.5, 50),
    "^GSPC":     (1_000, 50_000),
    "^IXIC":     (2_000, 100_000),
    "HG=F":      (0.5, 50),
    "PL=F":      (100, 50_000),
    "ZW=F":      (100, 5_000),
    "EURUSD=X":  (0.5, 2.0),
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_all_prices() -> dict:
    """Fetch live prices for all assets. Returns {asset_name: {price, change, ticker, ts}}."""
    results = {}

    for name, ticker in DEFAULT_ASSETS.items():
        try:
            df = yf.Ticker(ticker).history(period="5d", interval="1d")
            if df is None or df.empty:
                continue

            closes = df["Close"].dropna()
            if len(closes) < 1:
                continue

            price = round(float(closes.iloc[-1]), 2)

            # Sanity check
            bounds = PRICE_BOUNDS.get(ticker)
            if bounds and not (bounds[0] <= price <= bounds[1]):
                print(f"WARNING: {ticker} price ${price} outside bounds {bounds}, skipping")
                continue

            # Daily change
            daily_pct = 0.0
            if len(closes) >= 2:
                prev = float(closes.iloc[-2])
                if prev > 0:
                    daily_pct = round((price - prev) / prev * 100, 2)

            results[name] = {
                "price": price,
                "daily_change_pct": daily_pct,
                "ticker": ticker,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Small delay to avoid yfinance rate limiting
            time.sleep(0.3)

        except Exception as e:
            print(f"ERROR fetching {name} ({ticker}): {e}")
            continue

    return results


def upload_to_gcs(data: dict, blob_name: str) -> None:
    """Upload JSON data to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json",
    )
    print(f"Uploaded {blob_name} to gs://{BUCKET_NAME}/{blob_name}")


# ---------------------------------------------------------------------------
# Cloud Function entry point
# ---------------------------------------------------------------------------

@functions_framework.http
def fetch_prices(request):
    """HTTP-triggered Cloud Function. Called by Cloud Scheduler."""
    start = time.time()
    print(f"Starting price fetch at {datetime.now(timezone.utc).isoformat()}")

    prices = fetch_all_prices()

    if not prices:
        return json.dumps({"status": "error", "message": "No prices fetched"}), 500

    # Build the output payload
    payload = {
        "prices": prices,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "asset_count": len(prices),
        "fetch_time_s": round(time.time() - start, 2),
    }

    # Upload to Cloud Storage
    try:
        upload_to_gcs(payload, PRICES_BLOB)
    except Exception as e:
        print(f"GCS upload failed: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500

    print(f"Done: {len(prices)} assets in {payload['fetch_time_s']}s")
    return json.dumps({
        "status": "ok",
        "assets": len(prices),
        "fetch_time_s": payload["fetch_time_s"],
    })
