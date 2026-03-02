# Aegis Cloud Deployment Guide

## Prerequisites

1. **Google Cloud Account** with $300 free trial activated
2. **Google Cloud CLI** installed: https://cloud.google.com/sdk/docs/install
3. **Authenticated**: `gcloud auth login`

## Quick Start (Windows)

```batch
REM 1. Login and set project
gcloud auth login
gcloud config set project project-aegis

REM 2. Run the setup script (deploys everything)
cd cloud\scripts
setup.bat
```

## What Gets Deployed

| Component | Service | Schedule | Cost/month |
|-----------|---------|----------|------------|
| **Price Fetcher** | Cloud Function (256MB) | Every 2 minutes | ~$0.50 |
| **Brain Loop** | Cloud Function (512MB) | Every 30 minutes | ~$8 |
| **Data Storage** | Cloud Storage bucket | Always-on | ~$0.10 |
| **Schedulers** | Cloud Scheduler (2 jobs) | N/A | ~$0.20 |
| **TOTAL** | | | **~$9/month** |

## Architecture

```
Cloud Scheduler (every 2 min)
    |
    v
Cloud Function: fetch_prices
    |
    v
Cloud Storage: gs://aegis-market-data/live/prices.json
    |
    v
Streamlit Dashboard (reads prices instantly, no yfinance blocking)
```

## Enable Cloud Prices in Dashboard

Set the environment variable before running Streamlit:

```batch
REM Windows
set AEGIS_CLOUD_PRICES=true
streamlit run dashboard/app.py

REM Or add to .env file:
AEGIS_CLOUD_PRICES=true
AEGIS_GCS_BUCKET=aegis-market-data
```

When enabled, the dashboard reads prices from Cloud Storage (updated every 2 min)
instead of calling yfinance directly. This eliminates all UI freezes from yfinance timeouts.

**Fallback:** If Cloud Storage is unavailable, automatically falls back to yfinance → disk cache → scan data.

## Install Cloud Dependencies (Local)

Only needed if you want to test cloud integration locally:

```batch
pip install google-cloud-storage
```

## Monitoring

```batch
REM Check function logs
gcloud functions logs read fetch-prices --region=europe-west1 --limit=20
gcloud functions logs read brain-loop --region=europe-west1 --limit=20

REM Check scheduler status
gcloud scheduler jobs list --location=europe-west1

REM View costs
start https://console.cloud.google.com/billing
```

## Set Billing Alerts

```batch
REM Create alerts at $50, $100, $200
gcloud billing budgets create --billing-account=YOUR_ACCOUNT_ID ^
    --display-name="Aegis $50 alert" --budget-amount=50
gcloud billing budgets create --billing-account=YOUR_ACCOUNT_ID ^
    --display-name="Aegis $100 alert" --budget-amount=100
```

## File Structure

```
cloud/
    functions/
        fetch_prices/          # Price fetcher Cloud Function
            main.py            # Entry point
            requirements.txt   # Python dependencies
        brain_loop/            # Brain scanner Cloud Function
            main.py            # Entry point
            requirements.txt   # Python dependencies
    scripts/
        setup.sh               # Linux/Mac setup script
        setup.bat              # Windows setup script
    README.md                  # This file
```

## Troubleshooting

**"Permission denied" on deploy:**
```
gcloud auth login
gcloud config set project project-aegis
```

**Function fails with import error:**
Check that `requirements.txt` includes all needed packages.

**Prices not updating:**
```
gcloud scheduler jobs run aegis-price-fetch --location=europe-west1
gcloud functions logs read fetch-prices --region=europe-west1 --limit=5
```

**Want to disable cloud and go back to local:**
Remove or unset the environment variable:
```
set AEGIS_CLOUD_PRICES=
```
