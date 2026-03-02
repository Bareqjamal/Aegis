"""Scheduler — runs the market scanner every 30 minutes."""

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
SCANNER_SCRIPT = Path(__file__).resolve().parent / "market_scanner.py"
INTERVAL_SECONDS = 30 * 60  # 30 minutes

sys.path.insert(0, str(Path(__file__).resolve().parent))
from token_manager import TokenManager


def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [Scheduler] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def run_scan() -> None:
    log("Triggering scheduled market scan...")
    result = subprocess.run(
        [sys.executable, str(SCANNER_SCRIPT)],
        cwd=str(SCANNER_SCRIPT.parent),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode == 0:
        # Extract the summary table from stdout
        lines = result.stdout.strip().splitlines()
        summary = [l for l in lines if l.startswith("  ") and "$" in l]
        log(f"Scan complete. {len(summary)} assets processed.")
    else:
        log(f"Scan FAILED (exit {result.returncode}): {result.stderr[:200]}")


if __name__ == "__main__":
    log(f"Scheduler started. Interval: {INTERVAL_SECONDS // 60} minutes.")
    log(f"Scanner: {SCANNER_SCRIPT}")

    tm = TokenManager()

    # Run immediately on start, then loop
    while True:
        if not tm.check_budget():
            remaining = tm.budget_remaining()
            log(f"BUDGET EXCEEDED — daily limit ${tm.max_daily_budget:.2f} reached. Remaining: ${remaining:.4f}. Agents PAUSED.")
            log(f"Waiting {INTERVAL_SECONDS // 60} minutes before re-checking budget...")
        else:
            remaining = tm.budget_remaining()
            log(f"Budget OK (${remaining:.4f} remaining of ${tm.max_daily_budget:.2f}). Mode: {tm.mode}")
            try:
                run_scan()
            except Exception as e:
                log(f"Scheduler error: {e}")
        log(f"Next scan in {INTERVAL_SECONDS // 60} minutes.")
        time.sleep(INTERVAL_SECONDS)
