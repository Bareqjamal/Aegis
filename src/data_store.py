"""Project Aegis — DataStore Abstraction Layer.

Centralizes all JSON file read/write operations behind a clean interface.
Phase 1: JSON files on disk (current).
Phase 2: Swap internals to PostgreSQL/Redis without changing callers.

Usage:
    from data_store import data_store
    data_store.save_user_data("portfolio", user_id, portfolio_dict)
    portfolio = data_store.load_user_data("portfolio", user_id)
"""

import json
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR, MEMORY_DIR, PROJECT_ROOT

# ---------------------------------------------------------------------------
# File locks — prevent concurrent write corruption
# ---------------------------------------------------------------------------
_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_lock(path: str) -> threading.Lock:
    with _locks_lock:
        if path not in _locks:
            _locks[path] = threading.Lock()
        return _locks[path]


# ---------------------------------------------------------------------------
# Shared (market) data paths — same for all users
# ---------------------------------------------------------------------------
SHARED_PATHS = {
    "watchlist_summary": DATA_DIR / "watchlist_summary.json",
    "social_sentiment": DATA_DIR / "social_sentiment.json",
    "geopolitical": DATA_DIR / "geopolitical_analysis.json",
    "macro_regime": DATA_DIR / "macro_regime.json",
    "morning_brief": DATA_DIR / "morning_brief.json",
    "brain_report": DATA_DIR / "brain_cycle_report.json",
    "monitor_status": DATA_DIR / "monitor_status.json",
}

# News cache files follow pattern: news_{asset}.json
# Chart files follow pattern: charts/{asset}_*.json

# ---------------------------------------------------------------------------
# Per-user data keys (isolated per user)
# ---------------------------------------------------------------------------
USER_DATA_KEYS = {
    "portfolio": "paper_portfolio.json",
    "predictions": "market_predictions.json",
    "market_lessons": "market_lessons.json",
    "error_lessons": "error_lessons.json",
    "reflections": "daily_reflections.json",
    "hindsight": "hindsight_simulations.json",
    "bot_activity": "bot_activity.json",
    "bot_schedule": "bot_schedule.json",
    "settings": "settings_override.json",
    "alerts": "alerts.json",
}

# Default user ID for backward compatibility (single-user mode)
DEFAULT_USER = "default"


class DataStore:
    """Abstraction over JSON file storage with user isolation."""

    def __init__(self):
        self._users_dir = PROJECT_ROOT / "users"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create required directories."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._users_dir.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: str) -> Path:
        """Get or create a user's data directory."""
        if user_id == DEFAULT_USER:
            return MEMORY_DIR  # backward compat: default user uses memory/
        d = self._users_dir / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ----- Low-level atomic JSON I/O -----

    def _read_json(self, path: Path, default=None):
        """Read JSON file, return default if missing or corrupt."""
        if not path.exists():
            return default if default is not None else {}
        try:
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                return default if default is not None else {}
            return json.loads(text)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: DataStore read failed ({path.name}): {e}")
            return default if default is not None else {}

    def _write_json(self, path: Path, data):
        """Atomic write: write to temp file, then rename."""
        lock = _get_lock(str(path))
        with lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd, tmp = tempfile.mkstemp(
                    dir=str(path.parent), suffix=".tmp"
                )
                with open(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                tmp_path = Path(tmp)
                tmp_path.replace(path)
            except OSError as e:
                print(f"WARNING: DataStore write failed ({path.name}): {e}")
                # Clean up temp file if it exists
                try:
                    Path(tmp).unlink(missing_ok=True)
                except Exception:
                    pass

    # ----- Shared (market) data -----

    def load_shared(self, key: str, default=None):
        """Load shared market data by key."""
        path = SHARED_PATHS.get(key)
        if path is None:
            raise KeyError(f"Unknown shared data key: {key}")
        return self._read_json(path, default)

    def save_shared(self, key: str, data):
        """Save shared market data by key."""
        path = SHARED_PATHS.get(key)
        if path is None:
            raise KeyError(f"Unknown shared data key: {key}")
        self._write_json(path, data)

    def load_news(self, asset_name: str) -> list:
        """Load cached news for an asset."""
        safe = asset_name.lower().replace(" ", "_").replace("/", "_")
        path = DATA_DIR / f"news_{safe}.json"
        return self._read_json(path, [])

    def save_news(self, asset_name: str, articles: list):
        """Save cached news for an asset."""
        safe = asset_name.lower().replace(" ", "_").replace("/", "_")
        path = DATA_DIR / f"news_{safe}.json"
        self._write_json(path, articles)

    # ----- Per-user data -----

    def load_user_data(self, key: str, user_id: str = DEFAULT_USER, default=None):
        """Load user-specific data by key."""
        filename = USER_DATA_KEYS.get(key)
        if filename is None:
            raise KeyError(f"Unknown user data key: {key}")
        path = self._user_dir(user_id) / filename
        return self._read_json(path, default)

    def save_user_data(self, key: str, data, user_id: str = DEFAULT_USER):
        """Save user-specific data by key."""
        filename = USER_DATA_KEYS.get(key)
        if filename is None:
            raise KeyError(f"Unknown user data key: {key}")
        path = self._user_dir(user_id) / filename
        self._write_json(path, data)

    # ----- User watchlists -----

    def load_user_watchlist(self, user_id: str = DEFAULT_USER) -> dict:
        """Load user's active watchlist."""
        if user_id == DEFAULT_USER:
            return self._read_json(DATA_DIR / "user_watchlist.json", {"assets": {}})
        return self._read_json(
            self._user_dir(user_id) / "user_watchlist.json", {"assets": {}}
        )

    def save_user_watchlist(self, data: dict, user_id: str = DEFAULT_USER):
        """Save user's active watchlist."""
        if user_id == DEFAULT_USER:
            self._write_json(DATA_DIR / "user_watchlist.json", data)
        else:
            self._write_json(self._user_dir(user_id) / "user_watchlist.json", data)

    # ----- User profiles (auth) -----

    def _profiles_path(self) -> Path:
        return self._users_dir / "_profiles.json"

    def load_profiles(self) -> dict:
        """Load all user profiles. Returns {user_id: profile_dict}."""
        return self._read_json(self._profiles_path(), {})

    def save_profiles(self, profiles: dict):
        """Save all user profiles."""
        self._write_json(self._profiles_path(), profiles)

    def get_profile(self, user_id: str) -> dict | None:
        """Get a single user's profile."""
        profiles = self.load_profiles()
        return profiles.get(user_id)

    def save_profile(self, user_id: str, profile: dict):
        """Save/update a single user's profile."""
        profiles = self.load_profiles()
        profiles[user_id] = profile
        self.save_profiles(profiles)

    # ----- Migration helper -----

    def migrate_default_to_user(self, user_id: str):
        """Copy default user data to a new user (first-time setup after auth)."""
        if user_id == DEFAULT_USER:
            return
        user_dir = self._user_dir(user_id)
        for key, filename in USER_DATA_KEYS.items():
            src = MEMORY_DIR / filename
            dst = user_dir / filename
            if src.exists() and not dst.exists():
                try:
                    data = self._read_json(src)
                    if data:
                        self._write_json(dst, data)
                except Exception as e:
                    print(f"WARNING: Migration of {key} failed for {user_id}: {e}")

    # ----- Utility -----

    def data_age_seconds(self, key: str) -> float | None:
        """How old is the shared data file (in seconds)? None if missing."""
        path = SHARED_PATHS.get(key)
        if path is None or not path.exists():
            return None
        mtime = path.stat().st_mtime
        return (datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, tz=timezone.utc)).total_seconds()

    def list_users(self) -> list[str]:
        """List all registered user IDs."""
        profiles = self.load_profiles()
        return list(profiles.keys())


# ---------------------------------------------------------------------------
# Singleton instance — import this
# ---------------------------------------------------------------------------
data_store = DataStore()
