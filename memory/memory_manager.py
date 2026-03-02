"""Memory manager for tracking error lessons, pre-task checks, and self-debugging.

Enhanced capabilities:
- Error lesson recording (post-mortems)
- Pre-task memory check (every agent reads lessons before acting)
- Self-debugging (match errors to known causes)
- Daily reflections by Chief Monitor
"""

import json
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent
LESSONS_PATH = MEMORY_DIR / "error_lessons.json"
REFLECTIONS_PATH = MEMORY_DIR / "daily_reflections.json"


def _load() -> dict:
    if not LESSONS_PATH.exists():
        return {"lessons": []}
    with open(LESSONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(LESSONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_lesson(
    category: str,
    what_happened: str,
    root_cause: str,
    prevention_rule: str,
    related_ticket: str | None = None,
) -> dict:
    """Record a new lesson learned from a failure or sub-optimal outcome.

    Args:
        category: e.g. "coding", "logic", "data", "infra"
        what_happened: Description of the failure.
        root_cause: Why it happened.
        prevention_rule: Concrete rule to avoid recurrence.
        related_ticket: Optional kanban ticket ID.

    Returns:
        The created lesson entry.
    """
    data = _load()
    lesson = {
        "id": len(data["lessons"]) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "what_happened": what_happened,
        "root_cause": root_cause,
        "prevention_rule": prevention_rule,
        "related_ticket": related_ticket,
    }
    data["lessons"].append(lesson)
    _save(data)
    return lesson


def get_lessons(category: str | None = None) -> list[dict]:
    """Retrieve lessons, optionally filtered by category."""
    data = _load()
    lessons = data["lessons"]
    if category:
        lessons = [l for l in lessons if l["category"] == category]
    return lessons


def get_prevention_rules() -> list[str]:
    """Return all prevention rules as a flat list for quick reference."""
    return [l["prevention_rule"] for l in _load()["lessons"]]


# ---------------------------------------------------------------------------
# Pre-task memory check
# ---------------------------------------------------------------------------

def pre_task_check(agent_name: str, task_context: str = "") -> dict:
    """Called BEFORE any agent starts a task. Reads error_lessons.json and
    returns relevant rules and warnings.

    Args:
        agent_name: Which agent is about to act (e.g. "Scanner", "Analyst").
        task_context: Optional description of what the agent is about to do.

    Returns:
        Dict with rules, warnings, and relevant_lessons.
    """
    lessons = _load()["lessons"]
    rules = [l["prevention_rule"] for l in lessons]

    # Find relevant lessons by matching keywords from task_context
    relevant = []
    if task_context:
        ctx_lower = task_context.lower()
        for lesson in lessons:
            fields = f"{lesson['what_happened']} {lesson['root_cause']} {lesson['category']}".lower()
            if any(word in fields for word in ctx_lower.split() if len(word) > 3):
                relevant.append(lesson)

    # Category-based relevance
    agent_categories = {
        "Scanner": ["data", "infra"],
        "Analyst": ["logic", "data"],
        "Coder": ["coding"],
        "Researcher": ["data", "infra"],
        "ChartGenerator": ["coding", "data"],
        "NewsResearcher": ["data", "infra"],
        "Discovery": ["data", "infra"],
    }
    cats = agent_categories.get(agent_name, [])
    for lesson in lessons:
        if lesson["category"] in cats and lesson not in relevant:
            relevant.append(lesson)

    return {
        "agent": agent_name,
        "total_rules": len(rules),
        "relevant_lessons": relevant,
        "rules": rules,
        "warning": f"Bevor du loslegst: {len(rules)} Regeln beachten!" if rules else None,
    }


# ---------------------------------------------------------------------------
# Self-debugging
# ---------------------------------------------------------------------------

def self_debug(error_message: str, context: str = "") -> dict:
    """Analyze an error against known lessons to suggest a fix.

    Args:
        error_message: The error string to diagnose.
        context: Additional context (file, function, etc.).

    Returns:
        Dict with matched_lessons, suggested_fix, and is_known_issue flag.
    """
    lessons = _load()["lessons"]
    error_lower = error_message.lower()
    ctx_lower = context.lower()

    matches = []
    for lesson in lessons:
        score = 0
        fields = f"{lesson['what_happened']} {lesson['root_cause']}".lower()
        # Check for keyword overlap
        error_words = [w for w in error_lower.split() if len(w) > 3]
        for word in error_words:
            if word in fields:
                score += 1
        if ctx_lower:
            ctx_words = [w for w in ctx_lower.split() if len(w) > 3]
            for word in ctx_words:
                if word in fields:
                    score += 1
        if score > 0:
            matches.append({"lesson": lesson, "relevance_score": score})

    matches.sort(key=lambda m: m["relevance_score"], reverse=True)
    top_matches = matches[:3]

    if top_matches:
        best = top_matches[0]["lesson"]
        return {
            "is_known_issue": True,
            "matched_lessons": [m["lesson"] for m in top_matches],
            "suggested_fix": best["prevention_rule"],
            "root_cause_hint": best["root_cause"],
            "confidence": "high" if top_matches[0]["relevance_score"] >= 3 else "medium",
        }
    else:
        return {
            "is_known_issue": False,
            "matched_lessons": [],
            "suggested_fix": "No matching lesson found — this is a NEW error type. Record a lesson after fixing.",
            "root_cause_hint": None,
            "confidence": "none",
        }


# ---------------------------------------------------------------------------
# Daily reflections
# ---------------------------------------------------------------------------

def load_reflections() -> list[dict]:
    """Load all daily reflections."""
    if not REFLECTIONS_PATH.exists():
        return []
    return json.loads(REFLECTIONS_PATH.read_text(encoding="utf-8"))


def save_reflection(reflection: dict) -> None:
    """Append a daily reflection and keep the last 30."""
    existing = load_reflections()
    existing.append(reflection)
    existing = existing[-30:]
    REFLECTIONS_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_todays_reflection() -> dict | None:
    """Get today's reflection if it exists."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for r in reversed(load_reflections()):
        if r.get("date") == today:
            return r
    return None


def get_evolution_stats() -> dict:
    """Get system evolution statistics for the dashboard."""
    lessons = _load()["lessons"]
    reflections = load_reflections()

    # Lessons by category
    by_category = {}
    for l in lessons:
        cat = l["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    # Lessons over time (last 7 days)
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    lessons_per_day = {}
    for l in lessons:
        day = l["timestamp"][:10]
        lessons_per_day[day] = lessons_per_day.get(day, 0) + 1

    return {
        "total_lessons": len(lessons),
        "by_category": by_category,
        "lessons_per_day": lessons_per_day,
        "total_reflections": len(reflections),
        "latest_reflection": reflections[-1] if reflections else None,
        "all_rules": get_prevention_rules(),
    }


if __name__ == "__main__":
    # Quick self-test
    lesson = add_lesson(
        category="coding",
        what_happened="Self-test: memory manager initialized.",
        root_cause="N/A - initial setup.",
        prevention_rule="Always verify memory_manager loads before using it.",
        related_ticket="AEGIS-003",
    )
    print(f"Lesson recorded: {lesson}")
    print(f"All rules: {get_prevention_rules()}")
    print(f"\nPre-task check for Scanner:")
    print(json.dumps(pre_task_check("Scanner", "fetch market data"), indent=2))
    print(f"\nSelf-debug test:")
    print(json.dumps(self_debug("yfinance CSV header error"), indent=2))
