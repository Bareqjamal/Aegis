"""Autonomous Manager — the decision engine that makes Aegis self-improving.

Handles:
- Credit-Awareness: checks budget before every action
- Proactive Backlog: scans kanban, creates improvement tickets, auto-executes
- Self-Optimization: delegates idle tasks to sub-agents
- [AUTONOMOUS ACTION] logging for every self-initiated change

Usage:
    from autonomous_manager import AutonomousManager
    mgr = AutonomousManager()
    mgr.run_cycle()  # One autonomous decision cycle
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KANBAN_PATH = PROJECT_ROOT / "kanban_board.json"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "memory"))
from token_manager import TokenManager
from memory_manager import get_prevention_rules, get_lessons


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(message: str, autonomous: bool = False) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[AUTONOMOUS ACTION]" if autonomous else "[Manager]"
    line = f"[{ts}] {prefix} {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Budget awareness
# ---------------------------------------------------------------------------

class BudgetGuard:
    """Checks token budget before authorizing autonomous actions."""

    def __init__(self):
        self.tm = TokenManager()

    @property
    def budget_pct_remaining(self) -> float:
        remaining = self.tm.budget_remaining()
        limit = self.tm.max_daily_budget
        return (remaining / limit * 100) if limit > 0 else 0

    def can_act(self, min_pct: float = 20.0) -> bool:
        """Return True if budget has more than min_pct% remaining."""
        return self.budget_pct_remaining > min_pct

    def get_mode(self) -> str:
        """Determine operational mode based on budget."""
        pct = self.budget_pct_remaining
        if pct > 60:
            return "full_autonomy"     # Can do anything
        elif pct > 40:
            return "conservative"      # Only high-priority tasks
        elif pct > 20:
            return "minimal"           # Only critical tasks
        else:
            return "paused"            # No autonomous actions

    def report(self) -> dict:
        return {
            "remaining_pct": round(self.budget_pct_remaining, 1),
            "mode": self.get_mode(),
            "daily_cost": round(self.tm.get_daily_cost(), 6),
            "limit": self.tm.max_daily_budget,
            "can_act": self.can_act(),
        }


# ---------------------------------------------------------------------------
# Kanban management
# ---------------------------------------------------------------------------

class KanbanManager:
    """Reads, manages, and creates tickets in the kanban board."""

    def load_board(self) -> dict:
        with open(KANBAN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_board(self, data: dict) -> None:
        with open(KANBAN_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_backlog(self) -> list[dict]:
        board = self.load_board()["board"]
        return board.get("Backlog", [])

    def get_todo(self) -> list[dict]:
        board = self.load_board()["board"]
        return board.get("To Do", [])

    def get_in_progress(self) -> list[dict]:
        board = self.load_board()["board"]
        return board.get("In Progress", [])

    def get_highest_priority_ticket(self) -> dict | None:
        """Get the highest priority ticket from To Do, then Backlog."""
        for column in ["To Do", "Backlog"]:
            board = self.load_board()["board"]
            tickets = board.get(column, [])
            # Sort by priority: high > medium > low
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_tickets = sorted(
                tickets,
                key=lambda t: priority_order.get(t.get("priority", "medium"), 1),
            )
            if sorted_tickets:
                return sorted_tickets[0]
        return None

    def move_ticket(self, ticket_id: str, from_col: str, to_col: str) -> bool:
        """Move a ticket between columns."""
        data = self.load_board()
        board = data["board"]

        ticket = None
        for i, t in enumerate(board.get(from_col, [])):
            if t["id"] == ticket_id:
                ticket = board[from_col].pop(i)
                break

        if not ticket:
            return False

        board.setdefault(to_col, []).insert(0, ticket)
        self.save_board(data)
        return True

    def create_ticket(self, title: str, description: str, priority: str = "medium",
                      column: str = "Backlog") -> str:
        """Create a new kanban ticket. Returns the ticket ID."""
        data = self.load_board()

        all_ids = []
        for tickets in data["board"].values():
            for t in tickets:
                num = t["id"].replace("AEGIS-", "")
                if num.isdigit():
                    all_ids.append(int(num))
        next_id = max(all_ids) + 1 if all_ids else 20
        ticket_id = f"AEGIS-{next_id:03d}"

        ticket = {
            "id": ticket_id,
            "title": title,
            "description": description,
            "priority": priority,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "auto_created": True,
        }
        data["board"].setdefault(column, []).append(ticket)
        self.save_board(data)
        return ticket_id

    def count_by_status(self) -> dict:
        board = self.load_board()["board"]
        return {col: len(tickets) for col, tickets in board.items()}


# ---------------------------------------------------------------------------
# Self-improvement engine
# ---------------------------------------------------------------------------

IMPROVEMENT_CHECKS = [
    {
        "id": "stale_signals",
        "check": "Are any signal reports older than 6 hours?",
        "action": "run_scanner",
        "title": "AUTO: Refresh stale market signals",
        "priority": "high",
    },
    {
        "id": "discovery_scan",
        "check": "Run discovery for new market opportunities",
        "action": "run_discovery",
        "title": "AUTO: Run Market Discovery scan",
        "priority": "medium",
    },
    {
        "id": "error_reflection",
        "check": "Have there been errors since last reflection?",
        "action": "run_reflection",
        "title": "AUTO: Chief Monitor daily reflection",
        "priority": "low",
    },
    {
        "id": "prediction_validation",
        "check": "Check if past predictions were correct",
        "action": "validate_predictions",
        "title": "AUTO: Validate past market predictions",
        "priority": "medium",
    },
]


class SelfImprover:
    """Identifies improvement opportunities and executes them."""

    def __init__(self):
        self.research_dir = PROJECT_ROOT / "research_outputs"

    def check_stale_signals(self, max_age_hours: int = 6) -> bool:
        """Check if signal reports are older than max_age_hours."""
        now = time.time()
        for f in self.research_dir.glob("*_Signal_*.md"):
            age_hours = (now - f.stat().st_mtime) / 3600
            if age_hours > max_age_hours:
                return True
        return False

    def check_error_count(self) -> int:
        """Count recent errors in logs."""
        if not LOG_FILE.exists():
            return 0
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return sum(1 for l in lines if today in l and "ERROR" in l)

    def identify_improvements(self) -> list[dict]:
        """Identify what can be improved right now."""
        improvements = []

        # Stale signals?
        if self.check_stale_signals():
            improvements.append({
                "type": "refresh_signals",
                "reason": "Signal reports are older than 6 hours",
                "action": "run_scanner",
                "priority": "high",
            })

        # High error count?
        errors = self.check_error_count()
        if errors > 3:
            improvements.append({
                "type": "error_reflection",
                "reason": f"{errors} errors today — reflection needed",
                "action": "run_reflection",
                "priority": "high",
            })

        # Prediction validation due?
        pred_file = PROJECT_ROOT / "memory" / "market_predictions.json"
        if pred_file.exists():
            data = json.loads(pred_file.read_text(encoding="utf-8"))
            unvalidated = [p for p in data.get("predictions", []) if not p.get("validated")]
            if unvalidated:
                improvements.append({
                    "type": "validate_predictions",
                    "reason": f"{len(unvalidated)} unvalidated predictions",
                    "action": "validate_predictions",
                    "priority": "medium",
                })

        return improvements


# ---------------------------------------------------------------------------
# Action executor
# ---------------------------------------------------------------------------

class ActionExecutor:
    """Executes autonomous actions."""

    def run_scanner(self) -> bool:
        """Run the market scanner."""
        log("Running market scanner...", autonomous=True)
        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "src" / "market_scanner.py")],
                capture_output=True, text=True, timeout=120,
            )
            success = result.returncode == 0
            log(f"Scanner completed: {'OK' if success else 'FAILED'}", autonomous=True)
            return success
        except Exception as e:
            log(f"Scanner error: {e}", autonomous=True)
            return False

    def run_discovery(self) -> bool:
        """Run the market discovery agent."""
        log("Running market discovery...", autonomous=True)
        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "src" / "market_discovery.py")],
                capture_output=True, text=True, timeout=180,
            )
            success = result.returncode == 0
            log(f"Discovery completed: {'OK' if success else 'FAILED'}", autonomous=True)
            return success
        except Exception as e:
            log(f"Discovery error: {e}", autonomous=True)
            return False

    def validate_predictions(self) -> bool:
        """Run prediction validation."""
        log("Validating past predictions...", autonomous=True)
        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "src" / "market_learner.py"), "--validate"],
                capture_output=True, text=True, timeout=120,
            )
            success = result.returncode == 0
            log(f"Prediction validation: {'OK' if success else 'FAILED'}", autonomous=True)
            return success
        except Exception as e:
            log(f"Validation error: {e}", autonomous=True)
            return False

    def run_reflection(self) -> bool:
        """Run Chief Monitor reflection."""
        log("Running Chief Monitor reflection...", autonomous=True)
        try:
            from chief_monitor import ChiefMonitor
            monitor = ChiefMonitor()
            report = monitor.run_health_check()

            # Write reflection
            reflection = _generate_reflection(report)
            reflection_path = PROJECT_ROOT / "memory" / "daily_reflections.json"
            existing = []
            if reflection_path.exists():
                existing = json.loads(reflection_path.read_text(encoding="utf-8"))

            existing.append(reflection)
            # Keep last 30 reflections
            existing = existing[-30:]
            reflection_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log(f"Reflection complete: {reflection['summary'][:80]}", autonomous=True)
            return True
        except Exception as e:
            log(f"Reflection error: {e}", autonomous=True)
            return False


def _generate_reflection(health_report: dict) -> dict:
    """Generate a Chief Monitor efficiency reflection."""
    budget = health_report["budget"]
    errors = health_report["errors"]["total"]
    warnings = health_report["warnings"]
    agents = health_report["agents"]

    tips = []
    if budget["daily_cost"] > budget["limit"] * 0.5:
        tips.append("Budget usage over 50% — consider switching more agents to Haiku mode.")
    if errors > 3:
        tips.append(f"{errors} errors today — investigate root causes to prevent recurrence.")
    unhealthy = [a for a in agents if a["health"] == "UNHEALTHY"]
    if unhealthy:
        names = [a["name"] for a in unhealthy]
        tips.append(f"Unhealthy agents: {', '.join(names)} — needs debugging.")

    idle_agents = [a for a in agents if a["last_seen"] == "Never"]
    if idle_agents:
        names = [a["name"] for a in idle_agents]
        tips.append(f"Idle agents: {', '.join(names)} — could be used for improvement tasks.")

    if not tips:
        tips.append("System running smoothly. No efficiency improvements needed right now.")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "summary": tips[0],
        "efficiency_tips": tips,
        "budget_used_pct": round(budget["daily_cost"] / budget["limit"] * 100, 1) if budget["limit"] > 0 else 0,
        "errors_today": errors,
        "warning_count": len(warnings),
        "agent_health": {a["name"]: a["health"] for a in agents},
    }


# ---------------------------------------------------------------------------
# Main Autonomous Manager
# ---------------------------------------------------------------------------

class AutonomousManager:
    """The brain of Aegis — makes autonomous decisions."""

    def __init__(self):
        self.budget = BudgetGuard()
        self.kanban = KanbanManager()
        self.improver = SelfImprover()
        self.executor = ActionExecutor()
        self.cycle_count = 0

    def run_cycle(self) -> dict:
        """Execute one autonomous decision cycle.

        Returns a report of what happened.
        """
        self.cycle_count += 1
        report = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "budget": self.budget.report(),
            "action_taken": None,
            "reason": None,
            "success": None,
        }

        # Step 1: Budget check
        budget_info = self.budget.report()
        mode = budget_info["mode"]
        log(f"Cycle {self.cycle_count}: Budget {budget_info['remaining_pct']:.1f}% remaining, mode={mode}")

        if mode == "paused":
            log("Budget exhausted — pausing all autonomous actions.")
            report["action_taken"] = "paused"
            report["reason"] = "Budget < 20%"
            return report

        # Step 2: Pre-task memory check
        rules = get_prevention_rules()
        if rules:
            log(f"Pre-task check: {len(rules)} prevention rules loaded.")

        # Step 3: Check for improvements
        improvements = self.improver.identify_improvements()

        # Step 4: Decide what to do
        action = None

        # Priority A: High-priority improvements
        high_imps = [i for i in improvements if i["priority"] == "high"]
        if high_imps:
            action = high_imps[0]
            log(f"High-priority improvement: {action['reason']}", autonomous=True)

        # Priority B: Kanban tickets (if in full_autonomy or conservative mode)
        elif mode in ("full_autonomy", "conservative"):
            ticket = self.kanban.get_highest_priority_ticket()
            if ticket:
                # Only auto-execute TRADE ALERT or AUTO tickets
                title = ticket.get("title", "")
                if "TRADE ALERT" in title or "AUTO:" in title or "DISCOVERY:" in title:
                    action = {
                        "type": "kanban_ticket",
                        "reason": f"Processing ticket: {ticket['id']} — {title}",
                        "ticket": ticket,
                    }

        # Priority C: Medium improvements (if full autonomy)
        elif mode == "full_autonomy" and improvements:
            action = improvements[0]
            log(f"Improvement opportunity: {action['reason']}", autonomous=True)

        # Step 5: Execute
        if action:
            report["reason"] = action.get("reason", str(action.get("type", "unknown")))
            action_type = action.get("action") or action.get("type", "")

            if action_type == "run_scanner":
                report["success"] = self.executor.run_scanner()
                report["action_taken"] = "ran market scanner"

            elif action_type == "run_discovery":
                report["success"] = self.executor.run_discovery()
                report["action_taken"] = "ran market discovery"

            elif action_type == "validate_predictions":
                report["success"] = self.executor.validate_predictions()
                report["action_taken"] = "validated predictions"

            elif action_type == "run_reflection":
                report["success"] = self.executor.run_reflection()
                report["action_taken"] = "ran Chief Monitor reflection"

            else:
                log(f"Unknown action type: {action_type}")
                report["action_taken"] = "skipped_unknown"
        else:
            log("No actionable tasks found. System idle.")
            report["action_taken"] = "idle"

            # Idle-time: create improvement tickets if none exist
            if mode == "full_autonomy":
                self._idle_improvement()

        # Step 6: Kanban stats
        report["kanban_stats"] = self.kanban.count_by_status()
        return report

    def _idle_improvement(self) -> None:
        """When idle, create proactive improvement tickets."""
        board = self.kanban.load_board()["board"]
        existing_titles = set()
        for tickets in board.values():
            for t in tickets:
                existing_titles.add(t.get("title", ""))

        ideas = [
            ("AUTO: Add Google News RSS feeds for better news coverage",
             "Improve news_researcher.py to include Google News RSS for each asset.",
             "medium"),
            ("AUTO: Implement VADER sentiment for NLP-based scoring",
             "Replace keyword-based sentiment with VADER NLP model for more accurate scoring.",
             "low"),
            ("AUTO: Add multi-timeframe chart selector",
             "Add timeframe dropdown (1W/1M/3M/6M/1Y) to dashboard chart views.",
             "low"),
        ]

        for title, desc, priority in ideas:
            if title not in existing_titles:
                tid = self.kanban.create_ticket(title, desc, priority)
                log(f"Created improvement ticket: {tid} — {title}", autonomous=True)
                break  # Only one per idle cycle


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_loop(interval_minutes: int = 5) -> None:
    """Run autonomous cycles continuously with *interval_minutes* sleep."""
    mgr = AutonomousManager()
    log(f"Autonomous loop started — cycle every {interval_minutes} min. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                report = mgr.run_cycle()
                action = report.get("action_taken", "idle")
                budget_pct = report.get("budget", {}).get("remaining_pct", "?")
                log(f"Cycle {report['cycle']} done — action={action}, budget={budget_pct}%")
            except Exception as e:
                log(f"Cycle error (will retry next interval): {e}")
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        log("Autonomous loop stopped by user.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aegis Autonomous Manager")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=5,
                        help="Minutes between cycles (default: 5)")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.interval)
    else:
        mgr = AutonomousManager()
        report = mgr.run_cycle()
        print(json.dumps(report, indent=2))
