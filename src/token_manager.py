"""Token Usage & Budget Manager.

Tracks API token consumption per agent, calculates costs,
enforces daily budget limits, and manages efficiency mode.

Usage:
    from token_manager import TokenManager

    tm = TokenManager()

    # Check budget before making a call
    if not tm.check_budget():
        print("Budget exceeded!")
        return

    # Log usage after an API call
    tm.log_usage(
        agent="Scanner",
        model="claude-sonnet-4-5-20250929",
        prompt_tokens=1200,
        completion_tokens=350,
    )

    # Get cost summary
    print(tm.daily_summary())
"""

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
USAGE_FILE = PROJECT_ROOT / "token_usage.json"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

# ---------------------------------------------------------------------------
# Pricing per 1M tokens (USD) — updated Feb 2026
# ---------------------------------------------------------------------------
MODEL_PRICING = {
    # Claude 4.6 Opus
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    # Claude 4.5 Sonnet
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    # Claude 4.5 Haiku
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
}

# Mode-to-model mapping
MODE_MODELS = {
    "deep_research": "claude-sonnet-4-5-20250929",
    "fast_scan": "claude-haiku-4-5-20251001",
}


def _log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [CostGuard] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


class TokenManager:
    def __init__(self) -> None:
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not USAGE_FILE.exists():
            data = {"config": {"max_daily_budget_usd": 5.00, "mode": "fast_scan"}, "entries": []}
            self._save(data)

    def _load(self) -> dict:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- Config ---

    @property
    def mode(self) -> str:
        return self._load()["config"].get("mode", "fast_scan")

    @mode.setter
    def mode(self, value: str) -> None:
        data = self._load()
        data["config"]["mode"] = value
        self._save(data)
        _log(f"Mode changed to: {value}")

    @property
    def max_daily_budget(self) -> float:
        return self._load()["config"].get("max_daily_budget_usd", 5.00)

    @max_daily_budget.setter
    def max_daily_budget(self, value: float) -> None:
        data = self._load()
        data["config"]["max_daily_budget_usd"] = value
        self._save(data)

    def get_model_for_mode(self) -> str:
        return MODE_MODELS.get(self.mode, MODE_MODELS["fast_scan"])

    # --- Logging ---

    def log_usage(
        self,
        agent: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        task: str = "",
    ) -> dict:
        """Record a single API call's token usage."""
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "agent": agent,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": round(cost, 6),
            "task": task,
        }
        data = self._load()
        data["entries"].append(entry)
        self._save(data)
        return entry

    # --- Cost calculation ---

    @staticmethod
    def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # Default to Sonnet pricing if model unknown
            pricing = MODEL_PRICING["claude-sonnet-4-5-20250929"]
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    # --- Budget checks ---

    def get_daily_cost(self, date: str | None = None) -> float:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = self._load()
        return sum(e["cost_usd"] for e in data["entries"] if e["date"] == date)

    def get_monthly_cost(self, month: str | None = None) -> float:
        if month is None:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        data = self._load()
        return sum(e["cost_usd"] for e in data["entries"] if e["date"].startswith(month))

    def check_budget(self) -> bool:
        """Return True if daily budget is NOT exceeded."""
        daily = self.get_daily_cost()
        limit = self.max_daily_budget
        if daily >= limit:
            _log(f"BUDGET EXCEEDED! ${daily:.4f} >= ${limit:.2f}. All agents paused.")
            return False
        return True

    def budget_remaining(self) -> float:
        return max(0, self.max_daily_budget - self.get_daily_cost())

    # --- Summaries ---

    def daily_summary(self, date: str | None = None) -> dict:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = self._load()
        day_entries = [e for e in data["entries"] if e["date"] == date]
        return {
            "date": date,
            "total_cost": round(sum(e["cost_usd"] for e in day_entries), 6),
            "total_tokens": sum(e["total_tokens"] for e in day_entries),
            "prompt_tokens": sum(e["prompt_tokens"] for e in day_entries),
            "completion_tokens": sum(e["completion_tokens"] for e in day_entries),
            "api_calls": len(day_entries),
        }

    def cost_by_agent(self, date: str | None = None) -> dict[str, float]:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = self._load()
        agents: dict[str, float] = {}
        for e in data["entries"]:
            if e["date"] == date:
                agents[e["agent"]] = agents.get(e["agent"], 0) + e["cost_usd"]
        return {k: round(v, 6) for k, v in agents.items()}

    def cost_by_model(self, date: str | None = None) -> dict[str, float]:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = self._load()
        models: dict[str, float] = {}
        for e in data["entries"]:
            if e["date"] == date:
                models[e["model"]] = models.get(e["model"], 0) + e["cost_usd"]
        return {k: round(v, 6) for k, v in models.items()}


if __name__ == "__main__":
    tm = TokenManager()

    # Seed with simulated usage from today's session
    calls = [
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "Gold scan"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "BTC scan"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "ETH scan"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "Silver scan"),
        ("Analyst", "claude-sonnet-4-5-20250929", 2400, 800, "Signal scoring"),
        ("Researcher", "claude-sonnet-4-5-20250929", 3200, 1500, "Gold macro research"),
        ("Researcher", "claude-sonnet-4-5-20250929", 3200, 1500, "BTC strategy research"),
        ("Coder", "claude-sonnet-4-5-20250929", 1800, 2200, "Build market_scanner.py"),
        ("Coder", "claude-sonnet-4-5-20250929", 1500, 1800, "Build backtester.py"),
        ("Analyst", "claude-sonnet-4-5-20250929", 2000, 600, "Backtest analysis"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "Scheduled scan 1"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "Scheduled scan 1"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "Scheduled scan 1"),
        ("Scanner", "claude-haiku-4-5-20251001", 850, 200, "Scheduled scan 1"),
    ]
    for agent, model, pt, ct, task in calls:
        entry = tm.log_usage(agent, model, pt, ct, task)
        print(f"  {agent:12} | {model:35} | {pt:>5} in {ct:>5} out | ${entry['cost_usd']:.6f}")

    print(f"\nDaily summary: {tm.daily_summary()}")
    print(f"By agent: {tm.cost_by_agent()}")
    print(f"By model: {tm.cost_by_model()}")
    print(f"Budget remaining: ${tm.budget_remaining():.4f}")
    print(f"Budget OK: {tm.check_budget()}")
    print(f"Mode: {tm.mode}")
