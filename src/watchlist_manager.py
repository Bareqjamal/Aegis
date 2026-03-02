"""Watchlist Manager — Multiple Named Watchlists with Presets.

Provides:
- Multiple named watchlist configurations
- Save / load / switch between watchlists
- Preset templates (Crypto, Commodities, Indices, etc.)
- Duplicate, rename, delete watchlists
- Add / remove individual assets
- Backward compatible with existing user_watchlist.json

Storage format:
    src/data/watchlists/
        _active.json          # {"active": "Default"}
        Default.json          # the default watchlist
        Crypto Focus.json     # user-created
        Commodities.json      # preset or user-created
"""

import json
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
WATCHLISTS_DIR = DATA_DIR / "watchlists"
ACTIVE_FILE = WATCHLISTS_DIR / "_active.json"
LEGACY_FILE = DATA_DIR / "user_watchlist.json"

# ---------------------------------------------------------------------------
# Preset templates
# ---------------------------------------------------------------------------
PRESETS = {
    "All Assets": {
        "Gold": {"ticker": "GC=F", "support": 4405.00, "target": 5400.00, "stop_pct": 0.03, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "BTC": {"ticker": "BTC-USD", "support": 62000.00, "target": 95000.00, "stop_pct": 0.05, "macro_bias": "bullish", "category": "crypto", "enabled": True},
        "ETH": {"ticker": "ETH-USD", "support": 2200.00, "target": 4500.00, "stop_pct": 0.05, "macro_bias": "neutral", "category": "crypto", "enabled": True},
        "Silver": {"ticker": "SI=F", "support": 62.00, "target": 95.00, "stop_pct": 0.04, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "Oil": {"ticker": "CL=F", "support": 65.00, "target": 85.00, "stop_pct": 0.05, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "Natural Gas": {"ticker": "NG=F", "support": 2.80, "target": 4.50, "stop_pct": 0.06, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "S&P 500": {"ticker": "^GSPC", "support": 5200.00, "target": 6500.00, "stop_pct": 0.03, "macro_bias": "bullish", "category": "index", "enabled": True},
        "NASDAQ": {"ticker": "^IXIC", "support": 16000.00, "target": 20000.00, "stop_pct": 0.04, "macro_bias": "bullish", "category": "index", "enabled": True},
        "Copper": {"ticker": "HG=F", "support": 5.10, "target": 7.50, "stop_pct": 0.05, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "Platinum": {"ticker": "PL=F", "support": 900.00, "target": 1200.00, "stop_pct": 0.04, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "Wheat": {"ticker": "ZW=F", "support": 520.00, "target": 700.00, "stop_pct": 0.05, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "EUR/USD": {"ticker": "EURUSD=X", "support": 1.05, "target": 1.15, "stop_pct": 0.02, "macro_bias": "neutral", "category": "forex", "enabled": True},
    },
    "Crypto Focus": {
        "BTC": {"ticker": "BTC-USD", "support": 62000.00, "target": 95000.00, "stop_pct": 0.05, "macro_bias": "bullish", "category": "crypto", "enabled": True},
        "ETH": {"ticker": "ETH-USD", "support": 2200.00, "target": 4500.00, "stop_pct": 0.05, "macro_bias": "neutral", "category": "crypto", "enabled": True},
        "Gold": {"ticker": "GC=F", "support": 4405.00, "target": 5400.00, "stop_pct": 0.03, "macro_bias": "bullish", "category": "commodity", "enabled": True},
    },
    "Commodities": {
        "Gold": {"ticker": "GC=F", "support": 4405.00, "target": 5400.00, "stop_pct": 0.03, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "Silver": {"ticker": "SI=F", "support": 62.00, "target": 95.00, "stop_pct": 0.04, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "Oil": {"ticker": "CL=F", "support": 65.00, "target": 85.00, "stop_pct": 0.05, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "Natural Gas": {"ticker": "NG=F", "support": 2.80, "target": 4.50, "stop_pct": 0.06, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "Copper": {"ticker": "HG=F", "support": 5.10, "target": 7.50, "stop_pct": 0.05, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "Platinum": {"ticker": "PL=F", "support": 900.00, "target": 1200.00, "stop_pct": 0.04, "macro_bias": "neutral", "category": "commodity", "enabled": True},
        "Wheat": {"ticker": "ZW=F", "support": 520.00, "target": 700.00, "stop_pct": 0.05, "macro_bias": "neutral", "category": "commodity", "enabled": True},
    },
    "Indices Only": {
        "S&P 500": {"ticker": "^GSPC", "support": 5200.00, "target": 6500.00, "stop_pct": 0.03, "macro_bias": "bullish", "category": "index", "enabled": True},
        "NASDAQ": {"ticker": "^IXIC", "support": 16000.00, "target": 20000.00, "stop_pct": 0.04, "macro_bias": "bullish", "category": "index", "enabled": True},
    },
    "Safe Haven": {
        "Gold": {"ticker": "GC=F", "support": 4405.00, "target": 5400.00, "stop_pct": 0.03, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "Silver": {"ticker": "SI=F", "support": 62.00, "target": 95.00, "stop_pct": 0.04, "macro_bias": "bullish", "category": "commodity", "enabled": True},
        "BTC": {"ticker": "BTC-USD", "support": 62000.00, "target": 95000.00, "stop_pct": 0.05, "macro_bias": "bullish", "category": "crypto", "enabled": True},
        "EUR/USD": {"ticker": "EURUSD=X", "support": 1.05, "target": 1.15, "stop_pct": 0.02, "macro_bias": "neutral", "category": "forex", "enabled": True},
    },
}


# ---------------------------------------------------------------------------
# WatchlistManager
# ---------------------------------------------------------------------------

class WatchlistManager:
    """Manages multiple named watchlists stored as JSON files."""

    def __init__(self):
        """Initialize and ensure storage directory exists."""
        WATCHLISTS_DIR.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy()

    def _migrate_legacy(self):
        """One-time migration: copy legacy user_watchlist.json -> Default.json."""
        default_path = WATCHLISTS_DIR / "Default.json"
        if not default_path.exists() and LEGACY_FILE.exists():
            try:
                data = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
                default_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                # Set Default as active
                ACTIVE_FILE.write_text(json.dumps({"active": "Default"}, indent=2), encoding="utf-8")
            except Exception:
                pass

        # Ensure there's always a Default if nothing exists
        if not default_path.exists():
            default_path.write_text(
                json.dumps(PRESETS["All Assets"], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Ensure active file exists
        if not ACTIVE_FILE.exists():
            ACTIVE_FILE.write_text(json.dumps({"active": "Default"}, indent=2), encoding="utf-8")

    # --- Core operations ---

    def list_watchlists(self) -> list:
        """Return sorted list of watchlist names."""
        names = []
        for f in WATCHLISTS_DIR.glob("*.json"):
            if f.name.startswith("_"):
                continue
            names.append(f.stem)
        return sorted(names)

    def get_active_name(self) -> str:
        """Return the currently active watchlist name."""
        try:
            data = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
            return data.get("active", "Default")
        except Exception:
            return "Default"

    def load_watchlist(self, name=None) -> dict:
        """Load a named watchlist. If name is None, load active watchlist."""
        if name is None:
            name = self.get_active_name()
        path = WATCHLISTS_DIR / f"{name}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def load_active(self) -> dict:
        """Load the currently active watchlist."""
        return self.load_watchlist(None)

    def save_watchlist(self, name: str, data: dict) -> bool:
        """Save watchlist data to a named file. Also syncs to legacy file if active."""
        try:
            path = WATCHLISTS_DIR / f"{name}.json"
            tmp_path = path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(path)  # atomic rename
            # Keep legacy file in sync if this is the active watchlist
            if name == self.get_active_name():
                self._sync_to_legacy(data)
            return True
        except Exception:
            return False

    def _sync_to_legacy(self, data: dict):
        """Keep user_watchlist.json in sync for backward compatibility."""
        try:
            tmp = LEGACY_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(LEGACY_FILE)  # atomic rename
        except Exception:
            pass

    def set_active(self, name: str) -> bool:
        """Switch the active watchlist. Also syncs to legacy file."""
        path = WATCHLISTS_DIR / f"{name}.json"
        if not path.exists():
            return False
        try:
            ACTIVE_FILE.write_text(json.dumps({"active": name}, indent=2), encoding="utf-8")
            # Sync to legacy
            data = self.load_watchlist(name)
            self._sync_to_legacy(data)
            return True
        except Exception:
            return False

    def create_watchlist(self, name: str, data=None) -> bool:
        """Create a new empty or pre-filled watchlist."""
        path = WATCHLISTS_DIR / f"{name}.json"
        if path.exists():
            return False  # already exists
        return self.save_watchlist(name, data or {})

    def create_from_preset(self, preset_name: str, watchlist_name=None) -> bool:
        """Create a watchlist from a preset template."""
        if preset_name not in PRESETS:
            return False
        wl_name = watchlist_name or preset_name
        return self.create_watchlist(wl_name, PRESETS[preset_name])

    def delete_watchlist(self, name: str) -> bool:
        """Delete a watchlist. Cannot delete the active one unless it's the only one."""
        if name == self.get_active_name():
            others = [n for n in self.list_watchlists() if n != name]
            if not others:
                return False  # can't delete last watchlist
            # Switch to first available before deleting
            self.set_active(others[0])
        try:
            path = WATCHLISTS_DIR / f"{name}.json"
            if path.exists():
                path.unlink()
            return True
        except Exception:
            return False

    def rename_watchlist(self, old_name: str, new_name: str) -> bool:
        """Rename a watchlist."""
        old_path = WATCHLISTS_DIR / f"{old_name}.json"
        new_path = WATCHLISTS_DIR / f"{new_name}.json"
        if not old_path.exists() or new_path.exists():
            return False
        try:
            old_path.rename(new_path)
            # Update active reference if needed
            if self.get_active_name() == old_name:
                ACTIVE_FILE.write_text(json.dumps({"active": new_name}, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def duplicate_watchlist(self, source_name: str, new_name: str) -> bool:
        """Duplicate an existing watchlist under a new name."""
        data = self.load_watchlist(source_name)
        if not data:
            return False
        return self.create_watchlist(new_name, data)

    # --- Asset operations ---

    def add_asset(self, asset_name: str, asset_data: dict, watchlist_name=None) -> bool:
        """Add an asset to a watchlist (active by default)."""
        name = watchlist_name or self.get_active_name()
        wl = self.load_watchlist(name)
        wl[asset_name] = asset_data
        return self.save_watchlist(name, wl)

    def remove_asset(self, asset_name: str, watchlist_name=None) -> bool:
        """Remove an asset from a watchlist (active by default)."""
        name = watchlist_name or self.get_active_name()
        wl = self.load_watchlist(name)
        if asset_name not in wl:
            return False
        del wl[asset_name]
        return self.save_watchlist(name, wl)

    def update_asset(self, asset_name: str, updates: dict, watchlist_name=None) -> bool:
        """Update fields on an existing asset."""
        name = watchlist_name or self.get_active_name()
        wl = self.load_watchlist(name)
        if asset_name not in wl:
            return False
        wl[asset_name].update(updates)
        return self.save_watchlist(name, wl)

    # --- Info ---

    def get_presets(self) -> dict:
        """Return preset names -> list of asset names."""
        return {name: list(assets.keys()) for name, assets in PRESETS.items()}

    def get_watchlist_info(self, name=None) -> dict:
        """Get summary info about a watchlist."""
        if name is None:
            name = self.get_active_name()
        wl = self.load_watchlist(name)
        categories = {}
        for asset_data in wl.values():
            cat = asset_data.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "name": name,
            "asset_count": len(wl),
            "categories": categories,
            "assets": list(wl.keys()),
        }
