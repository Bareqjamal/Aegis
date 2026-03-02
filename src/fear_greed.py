"""Fear & Greed Index — aggregated market sentiment indicator.

Blends multiple sentiment sources into a single 0-100 index:
    - Crypto Fear & Greed (Alternative.me API): 30% weight
    - Social sentiment average (from social_sentiment.py cache): 30% weight
    - Macro regime score (from macro_regime.py cache): 40% weight

Caches results for 1 hour in src/data/fear_greed_cache.json.

Usage:
    from fear_greed import FearGreedIndex
    fgi = FearGreedIndex()
    result = fgi.get_index()
    # Returns: {"value": 35, "label": "Fear", "crypto_fg": 28, "components": {...}}
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
CACHE_FILE = DATA_DIR / "fear_greed_cache.json"
SOCIAL_CACHE = DATA_DIR / "social_sentiment.json"
REGIME_CACHE = DATA_DIR / "macro_regime.json"

ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/"
CACHE_TTL_SECONDS = 3600  # 1 hour

logger = logging.getLogger("aegis.fear_greed")


# ---------------------------------------------------------------------------
# Label / color mapping
# ---------------------------------------------------------------------------

def _get_label(value: int) -> str:
    """Convert a 0-100 index value to a human-readable label."""
    if value <= 20:
        return "Extreme Fear"
    elif value <= 40:
        return "Fear"
    elif value <= 60:
        return "Neutral"
    elif value <= 80:
        return "Greed"
    else:
        return "Extreme Greed"


def _get_color(label: str) -> str:
    """Return hex color for a Fear & Greed label."""
    colors = {
        "Extreme Fear": "#f85149",
        "Fear": "#fd7e14",
        "Neutral": "#8b949e",
        "Greed": "#3fb950",
        "Extreme Greed": "#3fb950",
    }
    return colors.get(label, "#8b949e")


# Macro regime name -> Fear & Greed score mapping
REGIME_SCORES = {
    "RISK_ON": 75,
    "RISK-ON": 75,
    "NEUTRAL": 50,
    "RISK_OFF": 25,
    "RISK-OFF": 25,
    "HIGH_VOLATILITY": 35,
    "VOLATILE": 35,
    "INFLATIONARY": 45,
    "DEFLATIONARY": 40,
}


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    """Safely load a JSON file, returning None on any error."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path.name, exc)
        return None


def _save_json(path: Path, data: dict) -> None:
    """Safely write a dict to a JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Failed to save %s: %s", path.name, exc)


# ---------------------------------------------------------------------------
# FearGreedIndex
# ---------------------------------------------------------------------------

class FearGreedIndex:
    """Compute an aggregated Fear & Greed index from multiple sources."""

    def _fetch_crypto_fg(self) -> int | None:
        """Fetch the crypto Fear & Greed index from Alternative.me.

        Returns an integer 0-100, or None on failure.
        """
        try:
            resp = requests.get(ALTERNATIVE_ME_URL, timeout=10)
            if resp.status_code != 200:
                logger.warning("Alternative.me returned %d", resp.status_code)
                return None
            data = resp.json()
            entries = data.get("data", [])
            if entries and isinstance(entries, list):
                value = entries[0].get("value")
                if value is not None:
                    return int(value)
            return None
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            logger.warning("Crypto F&G fetch failed: %s", exc)
            return None

    def _get_social_score(self) -> float | None:
        """Read the average social sentiment from the cached social scan.

        Returns a value in [-1.0, 1.0] or None if unavailable.
        """
        social = _load_json(SOCIAL_CACHE)
        if not social:
            return None
        asset_scores = social.get("asset_scores")
        if not asset_scores or not isinstance(asset_scores, dict):
            return None

        values = []
        for _asset, score_data in asset_scores.items():
            if isinstance(score_data, dict):
                ss = score_data.get("social_score")
                if ss is not None:
                    values.append(float(ss))

        if not values:
            return None
        return sum(values) / len(values)

    def _get_regime_score(self) -> int | None:
        """Map the cached macro regime to a Fear & Greed score.

        Returns an integer 0-100 or None if unavailable.
        """
        regime_data = _load_json(REGIME_CACHE)
        if not regime_data:
            return None
        regime_name = regime_data.get("regime", "NEUTRAL")
        return REGIME_SCORES.get(regime_name, 50)

    def get_index(self, force_refresh: bool = False) -> dict:
        """Compute the aggregated Fear & Greed index.

        Uses a 1-hour cache.  Pass ``force_refresh=True`` to bypass.

        Returns:
            {
                "value": int (0-100),
                "label": str,
                "color": str (hex),
                "crypto_fg": int | None,
                "social_score": float | None,
                "regime_score": int | None,
                "components": {
                    "crypto_fg": {"value": ..., "weight": 0.30},
                    "social": {"value": ..., "weight": 0.30},
                    "regime": {"value": ..., "weight": 0.40},
                },
                "timestamp": str (ISO-8601),
            }
        """
        # Check cache
        if not force_refresh:
            cached = _load_json(CACHE_FILE)
            if cached:
                ts = cached.get("timestamp", "")
                try:
                    cache_time = datetime.fromisoformat(ts)
                    age_s = (datetime.now(timezone.utc) - cache_time).total_seconds()
                    if age_s < CACHE_TTL_SECONDS:
                        return cached
                except (ValueError, TypeError):
                    pass

        # Gather components
        crypto_fg = self._fetch_crypto_fg()
        social_raw = self._get_social_score()
        regime_score = self._get_regime_score()

        # Convert social sentiment [-1, 1] to 0-100 scale
        if social_raw is not None:
            social_value = int(round((social_raw + 1.0) * 50))
            social_value = max(0, min(100, social_value))
        else:
            social_value = None

        # Weighted blend (only use available components)
        weights = {}
        if crypto_fg is not None:
            weights["crypto"] = (crypto_fg, 0.30)
        if social_value is not None:
            weights["social"] = (social_value, 0.30)
        if regime_score is not None:
            weights["regime"] = (regime_score, 0.40)

        if weights:
            # Normalize weights so they sum to 1.0
            total_weight = sum(w for _, w in weights.values())
            blended = sum(v * (w / total_weight) for v, w in weights.values())
            value = int(round(blended))
            value = max(0, min(100, value))
        else:
            # No data at all — default to neutral
            value = 50

        label = _get_label(value)
        color = _get_color(label)

        result = {
            "value": value,
            "label": label,
            "color": color,
            "crypto_fg": crypto_fg,
            "social_score": round(social_raw, 3) if social_raw is not None else None,
            "regime_score": regime_score,
            "components": {
                "crypto_fg": {
                    "value": crypto_fg,
                    "weight": 0.30,
                    "source": "Alternative.me",
                },
                "social": {
                    "value": social_value,
                    "weight": 0.30,
                    "source": "Social Sentiment Cache",
                },
                "regime": {
                    "value": regime_score,
                    "weight": 0.40,
                    "source": "Macro Regime Detector",
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Cache
        _save_json(CACHE_FILE, result)
        logger.info(
            "Fear & Greed Index: %d (%s) | crypto=%s social=%s regime=%s",
            value, label, crypto_fg, social_value, regime_score,
        )
        return result

    def load_cached(self) -> dict | None:
        """Load the cached Fear & Greed result without computing."""
        return _load_json(CACHE_FILE)
