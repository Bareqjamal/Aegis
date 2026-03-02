@echo off
REM =============================================================================
REM Project Aegis — Google Cloud Setup Script (Windows)
REM Run this ONCE to set up all cloud infrastructure
REM Prerequisites: gcloud CLI installed and authenticated
REM =============================================================================

set PROJECT_ID=project-aegis
set REGION=europe-west1
set BUCKET_NAME=aegis-market-data

echo =============================================
echo   Project Aegis — Google Cloud Setup
echo =============================================
echo.

REM -- Step 1: Set project --
echo [1/7] Setting project...
call gcloud config set project %PROJECT_ID%

REM -- Step 2: Enable required APIs --
echo [2/7] Enabling APIs (this may take a minute)...
call gcloud services enable cloudfunctions.googleapis.com cloudscheduler.googleapis.com storage.googleapis.com cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

REM -- Step 3: Create Cloud Storage bucket --
echo [3/7] Creating storage bucket...
call gcloud storage buckets create gs://%BUCKET_NAME% --location=%REGION% --uniform-bucket-level-access 2>nul
if errorlevel 1 echo   Bucket already exists, continuing...

REM -- Step 4: Deploy price fetcher function --
echo [4/7] Deploying fetch_prices Cloud Function...
cd /d "%~dp0..\functions\fetch_prices"
call gcloud functions deploy fetch-prices --gen2 --runtime=python311 --region=%REGION% --source=. --entry-point=fetch_prices --trigger-http --allow-unauthenticated --memory=256Mi --timeout=120s --max-instances=1

REM -- Step 5: Create scheduler for prices --
echo [5/7] Creating price fetch scheduler (every 2 min)...
for /f "tokens=*" %%i in ('gcloud functions describe fetch-prices --region=%REGION% --gen2 --format="value(serviceConfig.uri)"') do set PRICE_URL=%%i
echo   Price fetcher URL: %PRICE_URL%
call gcloud scheduler jobs create http aegis-price-fetch --location=%REGION% --schedule="*/2 * * * *" --uri="%PRICE_URL%" --http-method=GET --attempt-deadline=120s 2>nul
if errorlevel 1 echo   Scheduler job already exists, continuing...

REM -- Step 6: Deploy brain loop function --
echo [6/7] Deploying brain_loop Cloud Function...
cd /d "%~dp0..\functions\brain_loop"
call gcloud functions deploy brain-loop --gen2 --runtime=python311 --region=%REGION% --source=. --entry-point=brain_loop --trigger-http --allow-unauthenticated --memory=512Mi --timeout=300s --max-instances=1

REM -- Step 7: Create scheduler for brain --
echo [7/7] Creating brain loop scheduler (every 30 min)...
for /f "tokens=*" %%i in ('gcloud functions describe brain-loop --region=%REGION% --gen2 --format="value(serviceConfig.uri)"') do set BRAIN_URL=%%i
echo   Brain loop URL: %BRAIN_URL%
call gcloud scheduler jobs create http aegis-brain-loop --location=%REGION% --schedule="*/30 * * * *" --uri="%BRAIN_URL%" --http-method=GET --attempt-deadline=300s 2>nul
if errorlevel 1 echo   Scheduler job already exists, continuing...

echo.
echo =============================================
echo   Setup Complete!
echo =============================================
echo.
echo   Bucket:         gs://%BUCKET_NAME%
echo   Price Fetcher:  %PRICE_URL% (every 2 min)
echo   Brain Loop:     %BRAIN_URL% (every 30 min)
echo.
echo   Monitor costs: https://console.cloud.google.com/billing
echo.
pause
