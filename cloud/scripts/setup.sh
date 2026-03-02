#!/bin/bash
# =============================================================================
# Project Aegis — Google Cloud Setup Script
# Run this ONCE to set up all cloud infrastructure
# Prerequisites: gcloud CLI installed and authenticated
# =============================================================================

set -e

PROJECT_ID="project-aegis"
REGION="europe-west1"              # Frankfurt — close to Germany
BUCKET_NAME="aegis-market-data"

echo "============================================="
echo "  Project Aegis — Google Cloud Setup"
echo "============================================="
echo ""

# -- Step 1: Set project --
echo "[1/7] Setting project..."
gcloud config set project $PROJECT_ID

# -- Step 2: Enable required APIs --
echo "[2/7] Enabling APIs..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    storage.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com

# -- Step 3: Create Cloud Storage bucket --
echo "[3/7] Creating storage bucket..."
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --uniform-bucket-level-access \
    2>/dev/null || echo "Bucket already exists"

# -- Step 4: Deploy price fetcher function --
echo "[4/7] Deploying fetch_prices Cloud Function..."
cd "$(dirname "$0")/../functions/fetch_prices"
gcloud functions deploy fetch-prices \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=fetch_prices \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256Mi \
    --timeout=120s \
    --max-instances=1

# Get the function URL
PRICE_URL=$(gcloud functions describe fetch-prices --region=$REGION --gen2 --format='value(serviceConfig.uri)')
echo "  Price fetcher URL: $PRICE_URL"

# -- Step 5: Create Cloud Scheduler job for prices (every 2 minutes) --
echo "[5/7] Creating price fetch scheduler (every 2 min)..."
gcloud scheduler jobs create http aegis-price-fetch \
    --location=$REGION \
    --schedule="*/2 * * * *" \
    --uri="$PRICE_URL" \
    --http-method=GET \
    --attempt-deadline=120s \
    2>/dev/null || echo "Scheduler job already exists"

# -- Step 6: Deploy brain loop function (Phase 2 — optional) --
echo "[6/7] Deploying brain_loop Cloud Function..."
cd "$(dirname "$0")/../functions/brain_loop"
gcloud functions deploy brain-loop \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=brain_loop \
    --trigger-http \
    --allow-unauthenticated \
    --memory=512Mi \
    --timeout=300s \
    --max-instances=1

BRAIN_URL=$(gcloud functions describe brain-loop --region=$REGION --gen2 --format='value(serviceConfig.uri)')
echo "  Brain loop URL: $BRAIN_URL"

# -- Step 7: Create Cloud Scheduler job for brain (every 30 min) --
echo "[7/7] Creating brain loop scheduler (every 30 min)..."
gcloud scheduler jobs create http aegis-brain-loop \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --uri="$BRAIN_URL" \
    --http-method=GET \
    --attempt-deadline=300s \
    2>/dev/null || echo "Scheduler job already exists"

# -- Done --
echo ""
echo "============================================="
echo "  Setup Complete!"
echo "============================================="
echo ""
echo "  Bucket:         gs://$BUCKET_NAME"
echo "  Price Fetcher:  $PRICE_URL (every 2 min)"
echo "  Brain Loop:     $BRAIN_URL (every 30 min)"
echo ""
echo "  Set billing alerts:"
echo "    gcloud billing budgets create --billing-account=ACCOUNT_ID \\"
echo "      --display-name='Aegis $50 alert' --budget-amount=50"
echo ""
echo "  Monitor costs:"
echo "    https://console.cloud.google.com/billing"
echo ""
