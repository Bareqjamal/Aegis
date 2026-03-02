@echo off
:: ============================================================================
:: Project Aegis — Quick Launcher
:: ============================================================================
:: Usage:
::   run.bat              — Install deps + launch dashboard + brain (FULL)
::   run.bat dashboard    — Launch dashboard only
::   run.bat brain        — Run one brain cycle (scan + auto-trade + learn)
::   run.bat autopilot    — Start autopilot (brain loop every 30 min)
::   run.bat server       — Start brain API server (FastAPI + scheduler)
::   run.bat full         — Dashboard + Brain Server together
::   run.bat scan         — Run market scanner (CLI)
::   run.bat install      — Install dependencies only
:: ============================================================================

cd /d "%~dp0"

if "%1"=="" goto :fullstart
if "%1"=="dashboard" goto :dashboard
if "%1"=="full" goto :fullstart
if "%1"=="server" goto :server
if "%1"=="scan" goto :scan
if "%1"=="brain" goto :brain
if "%1"=="autopilot" goto :autopilot
if "%1"=="install" goto :install
if "%1"=="stop" goto :stop
if "%1"=="status" goto :status
if "%1"=="help" goto :help
echo Unknown command: %1
goto :help

:fullstart
echo.
echo  ============================================
echo   Project Aegis — Full Startup
echo  ============================================
echo.
echo  [1/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  ERROR: pip install failed. Make sure Python and pip are on your PATH.
    pause
    exit /b 1
)
echo  [2/3] Starting Brain Server (background)...
start "Aegis Brain" /min cmd /c "python src/brain_entrypoint.py > brain_logs.txt 2>&1"
echo        Brain API running at http://localhost:8502
echo        Brain logs: brain_logs.txt
echo.
echo  [3/3] Starting Dashboard...
echo.
echo  ============================================
echo   Dashboard:  http://localhost:8501
echo   Brain API:  http://localhost:8502/health
echo   Press Ctrl+C to stop the dashboard
echo   (Brain runs in background — use "run stop" to kill it)
echo  ============================================
echo.
python -m streamlit run dashboard/app.py --server.headless true
goto :eof

:dashboard
echo.
echo  Launching Aegis Dashboard...
echo.
echo  ============================================
echo   Dashboard starting at http://localhost:8501
echo   Press Ctrl+C to stop
echo  ============================================
echo.
python -m streamlit run dashboard/app.py --server.headless true
goto :eof

:server
echo.
echo  ============================================
echo   Aegis Brain Server — FastAPI + Scheduler
echo   API:      http://localhost:8502
echo   Health:   http://localhost:8502/health
echo   Status:   http://localhost:8502/api/brain/status
echo   Press Ctrl+C to stop
echo  ============================================
echo.
python src/brain_entrypoint.py
goto :eof

:scan
echo.
echo  Running Market Scanner...
echo.
python src/market_scanner.py %2 %3
goto :eof

:brain
echo.
echo  ============================================
echo   Running ONE brain cycle (scan + trade + learn)
echo  ============================================
echo.
python src/aegis_brain.py
goto :eof

:autopilot
echo.
echo  ============================================
echo   AUTOPILOT MODE — Aegis Brain Loop
echo   Scanning + Trading every 30 minutes
echo   Press Ctrl+C to stop
echo  ============================================
echo.
python src/aegis_brain.py --loop --interval 30
goto :eof

:stop
echo.
echo  Stopping Aegis Brain Server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8502" ^| findstr "LISTENING"') do (
    echo  Killing process %%a on port 8502...
    taskkill /PID %%a /F >nul 2>&1
)
echo  Brain server stopped.
echo.
goto :eof

:status
echo.
echo  Checking Aegis services...
echo.
echo  Brain API (port 8502):
curl -s http://localhost:8502/health 2>nul
if errorlevel 1 (
    echo  OFFLINE — Brain server is not running
) else (
    echo.
    echo  Brain Status:
    curl -s http://localhost:8502/api/brain/status 2>nul
    echo.
)
echo.
echo  Dashboard (port 8501):
curl -s -o nul -w "  HTTP %%{http_code}" http://localhost:8501/_stcore/health 2>nul
if errorlevel 1 (
    echo  OFFLINE — Dashboard is not running
) else (
    echo  — ONLINE
)
echo.
goto :eof

:install
echo.
echo  Installing dependencies...
pip install -r requirements.txt
echo  Done!
goto :eof

:help
echo.
echo  Project Aegis Launcher
echo  ----------------------
echo  run.bat              Install deps + launch dashboard + brain (FULL START)
echo  run.bat dashboard    Launch dashboard only
echo  run.bat server       Start brain API server only (FastAPI + scheduler)
echo  run.bat full         Same as no arguments (dashboard + brain)
echo  run.bat brain        Run one brain cycle (scan + auto-trade + learn)
echo  run.bat autopilot    Start brain loop (scan every 30 min, no API)
echo  run.bat scan         Run market scanner (CLI)
echo  run.bat scan --asset Gold   Scan a single asset
echo  run.bat status       Check if services are running
echo  run.bat stop         Stop the brain server
echo  run.bat install      Install dependencies only
echo  run.bat help         Show this help
echo.
echo  Docker (for server deployment):
echo    docker compose up -d        Start both services
echo    docker compose logs -f      View logs
echo    docker compose down         Stop everything
echo.
goto :eof
