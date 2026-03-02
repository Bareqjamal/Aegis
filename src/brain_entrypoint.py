"""Brain Entrypoint — launches APScheduler + FastAPI together.

This is the main entry point for the aegis-brain Docker container.
It starts the BrainScheduler in a background thread and runs the
FastAPI/uvicorn server in the main thread.

Usage:
    python src/brain_entrypoint.py
    # or with custom port:
    BRAIN_API_PORT=8502 python src/brain_entrypoint.py
"""

import logging
import os
import signal
import sys
from pathlib import Path

# Ensure src/ and memory/ are on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "memory"))

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "brain_logs.txt", encoding="utf-8"),
    ],
)

logger = logging.getLogger("aegis.entrypoint")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BRAIN_API_PORT = int(os.environ.get("BRAIN_API_PORT", "8502"))


def main() -> None:
    """Start the brain scheduler and API server."""
    import uvicorn
    from brain_runner import BrainScheduler
    from api_server import app, set_scheduler

    logger.info("=" * 60)
    logger.info("AEGIS BRAIN — Starting background service")
    logger.info("=" * 60)

    # Create and start the scheduler
    scheduler = BrainScheduler()
    scheduler.start()

    # Wire the scheduler into the API server
    set_scheduler(scheduler)

    # Graceful shutdown handler
    def _shutdown(signum, frame):
        logger.info("Received signal %s — shutting down...", signum)
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Starting API server on port %d...", BRAIN_API_PORT)

    # Run uvicorn (blocking) — this keeps the process alive
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=BRAIN_API_PORT,
        log_level="info",
        access_log=False,  # reduce noise — health checks are frequent
    )


if __name__ == "__main__":
    main()
