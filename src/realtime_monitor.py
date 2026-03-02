"""Real-Time Monitor — watches logs for live changes and tracks system health.

Continuously monitors agent_logs.txt for new entries, detects errors
in real-time, and writes a live status file for the dashboard.

Usage:
    python realtime_monitor.py              # Run in foreground
    python realtime_monitor.py --interval 3 # Custom check interval
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import deque

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
STATUS_FILE = PROJECT_ROOT / "src" / "data" / "monitor_status.json"

STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


class RealtimeMonitor:
    """Watches agent_logs.txt and maintains a live status file."""

    def __init__(self, interval: int = 3):
        self.interval = interval
        self.last_size = 0
        self.last_mtime = 0
        self.recent_entries = deque(maxlen=100)
        self.error_count = 0
        self.warning_count = 0
        self.agent_activity: dict[str, str] = {}  # agent -> last timestamp
        self.alerts: list[dict] = []
        self.start_time = datetime.now(timezone.utc)

    def _parse_log_line(self, line: str) -> dict | None:
        """Parse a log line into structured data.

        Handles formats:
          [2026-02-08 21:48:03] [Scanner] message
          [2026-02-08 21:48:03] [AUTONOMOUS ACTION] message
          [2026-02-08 21:48:03] [MarketLearner] message
          [2026-02-08 21:48:03] [AegisBrain] message
        """
        m = re.match(
            r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+)",
            line.strip(),
        )
        if not m:
            return None
        msg = m.group(3)
        msg_upper = msg.upper()
        # Detect real errors: "ERROR: ...", "...error: ...", "CRITICAL: ..."
        # Avoid false positives like "0 errors" or "error lesson tracking"
        is_error = bool(
            re.search(r'\bERROR\s*:', msg, re.IGNORECASE)
            or re.search(r'\bCRITICAL\b', msg, re.IGNORECASE)
            or re.search(r'\bFAILED\b', msg_upper)
            or re.search(r'\bEXCEPTION\b', msg_upper)
        )
        is_warning = bool(
            re.search(r'\bWARNING\s*:', msg, re.IGNORECASE)
            or re.search(r'\bWARN\b:', msg, re.IGNORECASE)
        )
        return {
            "timestamp": m.group(1),
            "agent": m.group(2),
            "message": msg,
            "is_error": is_error,
            "is_warning": is_warning,
            "is_autonomous": "AUTONOMOUS" in m.group(2).upper(),
        }

    def check_for_updates(self) -> list[dict]:
        """Check if the log file has new content. Returns new entries."""
        if not LOG_FILE.exists():
            return []

        stat = LOG_FILE.stat()
        current_size = stat.st_size
        current_mtime = stat.st_mtime

        # No changes
        if current_size == self.last_size and current_mtime == self.last_mtime:
            return []

        new_entries = []
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                # Seek to where we left off
                if self.last_size > 0 and current_size > self.last_size:
                    f.seek(self.last_size)
                elif current_size < self.last_size:
                    # File was truncated/rewritten — read from start
                    f.seek(0)
                else:
                    f.seek(self.last_size)

                for line in f:
                    parsed = self._parse_log_line(line)
                    if parsed:
                        new_entries.append(parsed)
                        self.recent_entries.append(parsed)

                        # Track agent activity
                        self.agent_activity[parsed["agent"]] = parsed["timestamp"]

                        # Count errors/warnings
                        if parsed["is_error"]:
                            self.error_count += 1
                            self.alerts.append({
                                "type": "error",
                                "agent": parsed["agent"],
                                "message": parsed["message"][:100],
                                "timestamp": parsed["timestamp"],
                            })
                        if parsed["is_warning"]:
                            self.warning_count += 1

        except Exception as e:
            print(f"[Monitor] Error reading log: {e}")

        self.last_size = current_size
        self.last_mtime = current_mtime
        return new_entries

    def get_status(self) -> dict:
        """Build current monitoring status."""
        now = datetime.now(timezone.utc)
        uptime = (now - self.start_time).total_seconds()

        # Determine active agents (seen in last 5 minutes)
        active_agents = []
        for agent, ts_str in self.agent_activity.items():
            try:
                ts = datetime.fromisoformat(ts_str.replace(" ", "T") + "+00:00")
                age = (now - ts).total_seconds()
                active_agents.append({
                    "agent": agent,
                    "last_seen": ts_str,
                    "seconds_ago": int(age),
                    "active": age < 300,  # active if seen in last 5 min
                })
            except ValueError:
                continue

        active_agents.sort(key=lambda a: a["seconds_ago"])

        return {
            "timestamp": now.isoformat(),
            "uptime_seconds": int(uptime),
            "log_file_size": self.last_size,
            "total_entries_seen": len(self.recent_entries),
            "errors_total": self.error_count,
            "warnings_total": self.warning_count,
            "active_agents": active_agents,
            "recent_alerts": self.alerts[-10:],  # last 10 alerts
            "last_entries": [
                {
                    "timestamp": e["timestamp"],
                    "agent": e["agent"],
                    "message": e["message"][:120],
                    "is_error": e["is_error"],
                }
                for e in list(self.recent_entries)[-20:]
            ],
            "status": "ERROR" if self.error_count > 10 else (
                "WARNING" if self.warning_count > 5 else "OK"
            ),
        }

    def write_status(self) -> None:
        """Write current status to the status file for dashboard consumption."""
        status = self.get_status()
        STATUS_FILE.write_text(
            json.dumps(status, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def run(self) -> None:
        """Main monitoring loop."""
        print(f"[Monitor] Starting real-time monitor (interval: {self.interval}s)")
        print(f"[Monitor] Watching: {LOG_FILE}")
        print(f"[Monitor] Status file: {STATUS_FILE}")

        # Initial read of entire file
        if LOG_FILE.exists():
            self.last_size = 0  # Read everything on first pass
            initial = self.check_for_updates()
            print(f"[Monitor] Loaded {len(initial)} existing log entries")

        while True:
            try:
                new = self.check_for_updates()
                if new:
                    for entry in new:
                        prefix = "!!" if entry["is_error"] else ">>"
                        print(f"  {prefix} [{entry['agent']}] {entry['message'][:80]}")

                self.write_status()
                time.sleep(self.interval)

            except KeyboardInterrupt:
                print("\n[Monitor] Stopped.")
                break
            except Exception as e:
                print(f"[Monitor] Error: {e}")
                time.sleep(self.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time log monitor")
    parser.add_argument("--interval", type=int, default=3, help="Check interval in seconds")
    args = parser.parse_args()

    monitor = RealtimeMonitor(interval=args.interval)
    monitor.run()
