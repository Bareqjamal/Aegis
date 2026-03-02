"""Brain Runner — APScheduler-based background service for Project Aegis.

Runs the brain cycle on a configurable interval and sends morning emails
on schedule. Writes brain_status.json for the dashboard to read.

This module is imported by brain_entrypoint.py — not run directly.

Usage:
    from brain_runner import BrainScheduler
    scheduler = BrainScheduler()
    scheduler.start()   # non-blocking — runs in background thread
    scheduler.stop()    # graceful shutdown
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "memory"))

DATA_DIR = PROJECT_ROOT / "src" / "data"
STATUS_FILE = DATA_DIR / "brain_status.json"
REPORT_FILE = DATA_DIR / "brain_cycle_report.json"
USERS_DIR = PROJECT_ROOT / "users"
PROFILES_FILE = USERS_DIR / "_profiles.json"

# ---------------------------------------------------------------------------
# Config (from environment)
# ---------------------------------------------------------------------------
BRAIN_INTERVAL_MIN = int(os.environ.get("BRAIN_INTERVAL_MIN", "30"))
MORNING_EMAIL_HOUR = int(os.environ.get("MORNING_EMAIL_HOUR", "7"))
MORNING_EMAIL_MIN = int(os.environ.get("MORNING_EMAIL_MIN", "0"))

logger = logging.getLogger("aegis.brain_runner")


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def _write_status(status: str, error: str | None = None,
                  cycles_today: int = 0, next_cycle: str = "") -> None:
    """Write brain_status.json atomically."""
    data = {
        "last_cycle": datetime.now(timezone.utc).isoformat(),
        "next_cycle": next_cycle,
        "status": status,
        "last_error": error,
        "cycles_today": cycles_today,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "interval_min": BRAIN_INTERVAL_MIN,
        "morning_email_hour": MORNING_EMAIL_HOUR,
    }
    tmp = STATUS_FILE.with_suffix(".tmp")
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(STATUS_FILE)
    except OSError as exc:
        logger.error("Failed to write brain status: %s", exc)


def _get_email_subscribers() -> list[str]:
    """Get list of email addresses that have opted into morning emails.

    Reads from users/_profiles.json. Users with verified emails and
    morning_email_enabled=True get the email.
    """
    if not PROFILES_FILE.exists():
        return []
    try:
        profiles = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        emails = []
        for uid, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            email = profile.get("email", "")
            verified = profile.get("email_verified", False)
            # Default: send to all verified emails (opt-out model)
            # Users can set morning_email_enabled=False to opt out
            opted_out = profile.get("morning_email_enabled") is False
            if email and "@" in email and verified and not opted_out:
                emails.append(email)
        return emails
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read profiles for email list: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Brain Scheduler
# ---------------------------------------------------------------------------

_start_time = time.monotonic()
_cycles_today = 0
_last_cycle_date = ""


class BrainScheduler:
    """APScheduler-based brain cycle runner.

    Schedules:
        - Brain cycle: every BRAIN_INTERVAL_MIN minutes
        - Morning email: daily at MORNING_EMAIL_HOUR:00 UTC
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,       # if missed, run once not N times
                "max_instances": 1,     # never overlap cycles
                "misfire_grace_time": 300,  # 5 min grace for missed jobs
            },
            timezone="UTC",
        )
        self._running = False

    def start(self) -> None:
        """Start the scheduler (non-blocking)."""
        if self._running:
            logger.warning("Brain scheduler already running.")
            return

        # Schedule brain cycle
        self.scheduler.add_job(
            self._run_brain_cycle,
            trigger=IntervalTrigger(minutes=BRAIN_INTERVAL_MIN),
            id="brain_cycle",
            name="Aegis Brain Cycle",
            next_run_time=datetime.now(timezone.utc) + timedelta(seconds=10),  # first run in 10s
        )

        # Schedule morning email
        self.scheduler.add_job(
            self._send_morning_emails,
            trigger=CronTrigger(hour=MORNING_EMAIL_HOUR, minute=MORNING_EMAIL_MIN),
            id="morning_email",
            name="Morning Email Broadcast",
        )

        self.scheduler.start()
        self._running = True

        _write_status("idle", cycles_today=0)
        logger.info(
            "Brain scheduler started: cycle every %d min, "
            "morning email at %02d:%02d UTC",
            BRAIN_INTERVAL_MIN, MORNING_EMAIL_HOUR, MORNING_EMAIL_MIN,
        )

    def stop(self) -> None:
        """Gracefully stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            _write_status("stopped")
            logger.info("Brain scheduler stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    def get_next_run_time(self) -> str:
        """Get the next scheduled brain cycle time as ISO string."""
        job = self.scheduler.get_job("brain_cycle")
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return ""

    # -- Job callbacks -------------------------------------------------------

    def _run_brain_cycle(self) -> None:
        """Execute one brain cycle (called by scheduler)."""
        global _cycles_today, _last_cycle_date

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != _last_cycle_date:
            _cycles_today = 0
            _last_cycle_date = today

        logger.info("Starting brain cycle #%d for today...", _cycles_today + 1)
        _write_status("running", cycles_today=_cycles_today,
                       next_cycle=self.get_next_run_time())

        try:
            from aegis_brain import run_brain_cycle
            report = run_brain_cycle()

            _cycles_today += 1
            errors = report.get("errors", [])

            if errors:
                logger.warning(
                    "Brain cycle completed with %d errors: %s",
                    len(errors), errors,
                )
                _write_status("idle", error=str(errors[0]),
                              cycles_today=_cycles_today,
                              next_cycle=self.get_next_run_time())
            else:
                steps = report.get("steps_completed", [])
                logger.info(
                    "Brain cycle #%d complete: %d steps, %.1fs",
                    _cycles_today, len(steps),
                    report.get("elapsed_seconds", 0),
                )
                _write_status("idle", cycles_today=_cycles_today,
                              next_cycle=self.get_next_run_time())

        except Exception as exc:
            logger.exception("Brain cycle CRASHED: %s", exc)
            _write_status("error", error=str(exc),
                          cycles_today=_cycles_today,
                          next_cycle=self.get_next_run_time())

    def _send_morning_emails(self) -> None:
        """Send morning emails to all subscribed users."""
        logger.info("Morning email job triggered...")

        subscribers = _get_email_subscribers()
        if not subscribers:
            logger.info("No email subscribers found. Skipping morning email.")
            return

        try:
            from morning_email import MorningEmailSender
            sender = MorningEmailSender()

            sent = 0
            failed = 0
            for email in subscribers:
                try:
                    ok = sender.send(email)
                    if ok:
                        sent += 1
                    else:
                        failed += 1
                except Exception as exc:
                    logger.error("Failed to send morning email to %s: %s", email, exc)
                    failed += 1

            logger.info(
                "Morning email broadcast: %d sent, %d failed, %d total subscribers",
                sent, failed, len(subscribers),
            )

        except Exception as exc:
            logger.exception("Morning email job CRASHED: %s", exc)

    def trigger_cycle_now(self) -> bool:
        """Manually trigger a brain cycle (for API endpoint)."""
        if not self._running:
            return False
        try:
            job = self.scheduler.get_job("brain_cycle")
            if job:
                job.modify(next_run_time=datetime.now(timezone.utc))
                return True
        except Exception as exc:
            logger.error("Failed to trigger manual cycle: %s", exc)
        return False

    def trigger_email_now(self) -> bool:
        """Manually trigger morning email (for API endpoint)."""
        if not self._running:
            return False
        try:
            job = self.scheduler.get_job("morning_email")
            if job:
                job.modify(next_run_time=datetime.now(timezone.utc))
                return True
        except Exception as exc:
            logger.error("Failed to trigger manual email: %s", exc)
        return False
