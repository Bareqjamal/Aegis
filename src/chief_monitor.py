"""Chief Monitor — supervises all agents, detects errors, enforces budgets.

Produces a health report dict consumable by the dashboard's Monitor tab.

Usage:
    from chief_monitor import ChiefMonitor
    report = ChiefMonitor().run_health_check()
"""

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

import sys
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from token_manager import TokenManager
from agents import AGENT_PROFILES


class ChiefMonitor:
    def __init__(self) -> None:
        self.tm = TokenManager()
        self.log_lines = self._load_logs()

    def _load_logs(self) -> list[str]:
        if not LOG_FILE.exists():
            return []
        return LOG_FILE.read_text(encoding="utf-8").splitlines()

    # --- Error detection ---

    def count_errors(self) -> dict:
        """Count ERROR entries per agent in the logs."""
        error_counts: dict[str, int] = {}
        for line in self.log_lines:
            if "ERROR" in line:
                match = re.search(r"\[(\w+)\]", line)
                if match:
                    agent = match.group(1)
                    # skip timestamp bracket
                    agents_in_line = re.findall(r"\] \[(\w+)\]", line)
                    if agents_in_line:
                        agent = agents_in_line[0]
                        error_counts[agent] = error_counts.get(agent, 0) + 1
        return error_counts

    def recent_errors(self, n: int = 10) -> list[str]:
        """Return the last n error lines."""
        errors = [l for l in self.log_lines if "ERROR" in l]
        return errors[-n:]

    # --- Loop detection ---

    def detect_loops(self, threshold: int = 10) -> list[dict]:
        """Detect if any agent logged >threshold identical actions in last hour."""
        now = datetime.now(timezone.utc)
        recent: list[str] = []

        for line in self.log_lines:
            ts_match = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
            if ts_match:
                try:
                    ts = datetime.fromisoformat(ts_match.group(1).replace(" ", "T") + "+00:00")
                    if (now - ts).total_seconds() <= 3600:
                        recent.append(line)
                except ValueError:
                    continue

        # Count identical messages (strip timestamp)
        stripped = [re.sub(r"^\[.*?\] ", "", l) for l in recent]
        counts = Counter(stripped)

        alerts = []
        for msg, count in counts.items():
            if count >= threshold:
                alerts.append({
                    "message": msg,
                    "count": count,
                    "severity": "critical" if count >= threshold * 2 else "warning",
                })
        return alerts

    # --- Agent cost analysis ---

    def agent_cost_breakdown(self) -> list[dict]:
        """Cost per agent with percentage of daily budget."""
        costs = self.tm.cost_by_agent()
        budget = self.tm.max_daily_budget
        breakdown = []
        for agent, cost in sorted(costs.items(), key=lambda x: -x[1]):
            pct = (cost / budget * 100) if budget > 0 else 0
            profile = AGENT_PROFILES.get(agent, {})
            breakdown.append({
                "agent": agent,
                "icon": profile.get("icon", "?"),
                "role": profile.get("role", "Unknown"),
                "cost_usd": round(cost, 6),
                "budget_pct": round(pct, 1),
                "status": "ALERT" if pct > 40 else "OK",
            })
        return breakdown

    # --- Agent status ---

    def agent_statuses(self) -> list[dict]:
        """Determine agent health: last seen, error count, cost."""
        errors = self.count_errors()
        costs = self.tm.cost_by_agent()
        statuses = []

        for name, profile in AGENT_PROFILES.items():
            # Find last log entry for this agent
            last_seen = None
            for line in reversed(self.log_lines):
                if f"[{name}]" in line:
                    ts_match = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
                    if ts_match:
                        last_seen = ts_match.group(1)
                    break

            agent_errors = errors.get(name, 0)
            agent_cost = costs.get(name, 0)

            if agent_errors > 3:
                health = "UNHEALTHY"
            elif agent_errors > 0:
                health = "DEGRADED"
            else:
                health = "HEALTHY"

            statuses.append({
                "agent": name,
                "icon": profile["icon"],
                "name": profile["name"],
                "role": profile["role"],
                "health": health,
                "last_seen": last_seen or "Never",
                "errors_today": agent_errors,
                "cost_today": round(agent_cost, 6),
            })
        return statuses

    # --- Full health report ---

    def run_health_check(self) -> dict:
        """Produce a complete health report."""
        budget_ok = self.tm.check_budget()
        daily_cost = self.tm.get_daily_cost()
        budget_limit = self.tm.max_daily_budget
        remaining = self.tm.budget_remaining()
        mode = self.tm.mode

        loop_alerts = self.detect_loops()
        errors = self.count_errors()
        total_errors = sum(errors.values())

        # Compile warnings
        warnings = []
        if not budget_ok:
            warnings.append("CRITICAL: Daily budget exceeded. All agents should be paused.")
        if daily_cost / budget_limit > 0.8 and budget_ok:
            warnings.append(f"WARNING: Budget usage at {daily_cost/budget_limit*100:.0f}%.")
        for alert in loop_alerts:
            warnings.append(f"LOOP DETECTED: '{alert['message'][:60]}...' repeated {alert['count']}x in last hour.")
        if total_errors > 5:
            warnings.append(f"HIGH ERROR RATE: {total_errors} errors across agents today.")

        # Cost hog detection
        breakdown = self.agent_cost_breakdown()
        for b in breakdown:
            if b["status"] == "ALERT":
                warnings.append(f"COST ALERT: {b['agent']} using {b['budget_pct']}% of daily budget.")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "budget": {
                "ok": budget_ok,
                "daily_cost": round(daily_cost, 6),
                "limit": budget_limit,
                "remaining": round(remaining, 6),
                "mode": mode,
            },
            "agents": self.agent_statuses(),
            "cost_breakdown": breakdown,
            "errors": {
                "total": total_errors,
                "by_agent": errors,
                "recent": self.recent_errors(5),
            },
            "loop_alerts": loop_alerts,
            "warnings": warnings,
            "overall_status": "CRITICAL" if not budget_ok or loop_alerts else ("WARNING" if warnings else "ALL CLEAR"),
        }


if __name__ == "__main__":
    import json
    report = ChiefMonitor().run_health_check()
    print(json.dumps(report, indent=2))
