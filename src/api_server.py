"""API Server — FastAPI health/status/trigger endpoints for Aegis Brain.

Lightweight REST API that exposes brain status and allows manual triggering
of brain cycles and morning emails. Intended for Docker healthcheck and
dashboard communication.

This module is imported by brain_entrypoint.py — not run directly.

Endpoints:
    GET  /health              → {"status": "ok"}
    GET  /api/brain/status    → brain_status.json contents
    GET  /api/brain/report    → last brain_cycle_report.json
    POST /api/brain/trigger   → trigger immediate brain cycle
    POST /api/email/trigger   → trigger immediate morning email
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("aegis.api_server")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
STATUS_FILE = DATA_DIR / "brain_status.json"
REPORT_FILE = DATA_DIR / "brain_cycle_report.json"

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Aegis Brain API",
    description="Health, status, and trigger endpoints for the Aegis background brain.",
    version="1.0.0",
)

# Rate limiting for trigger endpoints
_last_trigger_time: float = 0.0
TRIGGER_COOLDOWN_SECONDS = 300  # 5 minutes between manual triggers

# Reference to the BrainScheduler — set by brain_entrypoint.py
_scheduler = None


def set_scheduler(scheduler) -> None:
    """Set the BrainScheduler instance (called by entrypoint)."""
    global _scheduler
    _scheduler = scheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json_file(path: Path) -> dict:
    """Safely load a JSON file."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Docker healthcheck endpoint."""
    return {"status": "ok", "service": "aegis-brain", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/brain/status")
async def brain_status():
    """Return current brain status from brain_status.json."""
    status = _load_json_file(STATUS_FILE)
    if not status:
        return JSONResponse(
            content={
                "status": "unknown",
                "message": "No brain status file found. Brain may not have run yet.",
            },
            status_code=200,
        )

    # Add scheduler info if available
    if _scheduler:
        status["scheduler_running"] = _scheduler.is_running
        status["next_cycle"] = _scheduler.get_next_run_time()

    return status


@app.get("/api/brain/report")
async def brain_report():
    """Return the last brain cycle report."""
    report = _load_json_file(REPORT_FILE)
    if not report:
        return JSONResponse(
            content={"message": "No brain cycle report found. Run a cycle first."},
            status_code=200,
        )
    return report


@app.post("/api/brain/trigger")
async def trigger_brain_cycle():
    """Manually trigger an immediate brain cycle.

    Rate limited: 1 trigger per 5 minutes.
    """
    global _last_trigger_time

    if not _scheduler or not _scheduler.is_running:
        raise HTTPException(status_code=503, detail="Brain scheduler is not running.")

    now = time.monotonic()
    if now - _last_trigger_time < TRIGGER_COOLDOWN_SECONDS:
        remaining = int(TRIGGER_COOLDOWN_SECONDS - (now - _last_trigger_time))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Try again in {remaining} seconds.",
        )

    success = _scheduler.trigger_cycle_now()
    if success:
        _last_trigger_time = now
        return {
            "message": "Brain cycle triggered. It will start momentarily.",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to trigger brain cycle.")


@app.post("/api/email/trigger")
async def trigger_morning_email():
    """Manually trigger morning email broadcast.

    Rate limited: 1 trigger per 5 minutes.
    """
    global _last_trigger_time

    if not _scheduler or not _scheduler.is_running:
        raise HTTPException(status_code=503, detail="Brain scheduler is not running.")

    now = time.monotonic()
    if now - _last_trigger_time < TRIGGER_COOLDOWN_SECONDS:
        remaining = int(TRIGGER_COOLDOWN_SECONDS - (now - _last_trigger_time))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Try again in {remaining} seconds.",
        )

    success = _scheduler.trigger_email_now()
    if success:
        _last_trigger_time = now
        return {
            "message": "Morning email triggered. Emails will be sent momentarily.",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to trigger morning email.")


@app.get("/api/brain/config")
async def brain_config():
    """Return current brain configuration."""
    from brain_runner import BRAIN_INTERVAL_MIN, MORNING_EMAIL_HOUR, MORNING_EMAIL_MIN
    return {
        "brain_interval_min": BRAIN_INTERVAL_MIN,
        "morning_email_hour": MORNING_EMAIL_HOUR,
        "morning_email_min": MORNING_EMAIL_MIN,
        "scheduler_running": _scheduler.is_running if _scheduler else False,
    }
