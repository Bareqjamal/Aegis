"""Prediction Game Engine — Agree/Disagree engagement mechanic + daily scorecard.

Users can agree or disagree with each AI signal. The system tracks outcomes,
calculates accuracy streaks, and generates daily scorecards showing who was
right — the user or the AI.

Usage:
    from prediction_game import PredictionGame
    game = PredictionGame(user_id="default")
    game.record_vote("Gold", "BUY", agrees=True, ai_confidence=73)
    scorecard = game.get_yesterday_scorecard()
    streak = game.get_streak()
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
USERS_DIR = PROJECT_ROOT / "users"
PREDICTIONS_FILE = MEMORY_DIR / "market_predictions.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _yesterday_str() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _get_game_path(user_id: str = "default") -> Path:
    """Get the prediction game file path for a user."""
    if user_id and user_id != "default":
        user_dir = USERS_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "prediction_game.json"
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / "prediction_game.json"


def _load_game(user_id: str = "default") -> dict:
    """Load prediction game data."""
    path = _get_game_path(user_id)
    default = {
        "votes": [],
        "stats": {
            "total_votes": 0,
            "correct_agrees": 0,
            "correct_disagrees": 0,
            "current_streak": 0,
            "best_streak": 0,
            "last_vote_date": None,
        },
    }
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if "votes" not in data:
            data["votes"] = []
        if "stats" not in data:
            data["stats"] = default["stats"]
        return data
    except (json.JSONDecodeError, ValueError, OSError) as e:
        logger.warning("Prediction game data corrupt for %s: %s", user_id, e)
        return default


def _save_game(data: dict, user_id: str = "default") -> None:
    """Save prediction game data atomically."""
    path = _get_game_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp_path).replace(path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Outcome validation
# ---------------------------------------------------------------------------


def _load_ai_predictions() -> list:
    """Load AI market predictions for outcome checking."""
    if not PREDICTIONS_FILE.exists():
        return []
    try:
        data = json.loads(PREDICTIONS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("predictions", [])
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, ValueError, OSError):
        return []


def _check_outcome(asset: str, signal: str, vote_date: str) -> dict | None:
    """Check if a prediction was correct based on AI validation data.

    Returns dict with outcome info or None if not yet validated.
    The market_learner stores predictions with:
      - "timestamp" (ISO format, not "date")
      - "outcome": "correct" | "incorrect" | None (not a boolean "correct")
      - "outcome_price" (not "actual_move_pct")
    """
    ai_preds = _load_ai_predictions()
    for pred in reversed(ai_preds):
        if not isinstance(pred, dict):
            continue
        pred_asset = pred.get("asset", "")
        # Handle both "timestamp" (actual) and "date" (legacy) fields
        pred_timestamp = pred.get("timestamp", pred.get("date", ""))
        pred_date = pred_timestamp[:10] if pred_timestamp else ""
        validated = pred.get("validated", False)

        if pred_asset == asset and pred_date == vote_date and validated:
            # "outcome" is a string ("correct"/"incorrect"), not a boolean
            outcome_str = pred.get("outcome", "")
            correct = outcome_str == "correct"
            # Calculate actual move % from entry and outcome prices
            entry_price = pred.get("entry_price", 0)
            outcome_price = pred.get("outcome_price", 0)
            actual_move = 0
            if entry_price and outcome_price:
                actual_move = round(
                    (outcome_price - entry_price) / entry_price * 100, 2
                )
            return {
                "validated": True,
                "signal_correct": correct,
                "actual_move_pct": actual_move,
            }
    return None


# ---------------------------------------------------------------------------
# PredictionGame class
# ---------------------------------------------------------------------------


class PredictionGame:
    """Manages the Agree/Disagree prediction game for a user."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id

    def record_vote(
        self,
        asset: str,
        signal: str,
        agrees: bool,
        ai_confidence: float = 0,
    ) -> dict:
        """Record a user's agree/disagree vote on a signal.

        Args:
            asset: Asset name (e.g. "Gold")
            signal: AI signal label (e.g. "BUY", "STRONG SELL")
            agrees: True if user agrees, False if disagrees
            ai_confidence: AI confidence % for this signal

        Returns:
            The vote dict that was recorded.
        """
        data = _load_game(self.user_id)
        today = _today_str()

        # Check if already voted on this asset today
        for vote in data["votes"]:
            if vote.get("asset") == asset and vote.get("date") == today:
                # Update existing vote
                vote["agrees"] = agrees
                vote["signal"] = signal
                vote["ai_confidence"] = ai_confidence
                vote["updated_at"] = datetime.now(timezone.utc).isoformat()
                _save_game(data, self.user_id)
                return vote

        # New vote
        vote = {
            "date": today,
            "asset": asset,
            "signal": signal,
            "agrees": agrees,
            "ai_confidence": ai_confidence,
            "outcome": None,
            "signal_correct": None,
            "actual_move_pct": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data["votes"].append(vote)
        data["stats"]["total_votes"] = data["stats"].get("total_votes", 0) + 1
        data["stats"]["last_vote_date"] = today

        # Keep last 500 votes
        if len(data["votes"]) > 500:
            data["votes"] = data["votes"][-500:]

        _save_game(data, self.user_id)
        return vote

    def get_today_votes(self) -> list[dict]:
        """Get all votes placed today."""
        data = _load_game(self.user_id)
        today = _today_str()
        return [v for v in data["votes"] if v.get("date") == today]

    def has_voted(self, asset: str) -> bool:
        """Check if user already voted on this asset today."""
        today = _today_str()
        data = _load_game(self.user_id)
        return any(
            v.get("asset") == asset and v.get("date") == today
            for v in data["votes"]
        )

    def get_vote(self, asset: str) -> dict | None:
        """Get today's vote for a specific asset."""
        today = _today_str()
        data = _load_game(self.user_id)
        for v in data["votes"]:
            if v.get("asset") == asset and v.get("date") == today:
                return v
        return None

    def validate_outcomes(self) -> int:
        """Validate pending votes against real market outcomes.

        Returns number of newly validated votes.
        """
        data = _load_game(self.user_id)
        validated_count = 0

        for vote in data["votes"]:
            if vote.get("outcome") is not None:
                continue  # Already validated

            outcome = _check_outcome(
                vote["asset"], vote["signal"], vote["date"]
            )
            if outcome and outcome.get("validated"):
                signal_correct = outcome["signal_correct"]
                user_agreed = vote["agrees"]

                # User is "correct" if:
                # - They agreed AND the signal was right
                # - They disagreed AND the signal was wrong
                user_correct = (user_agreed and signal_correct) or (
                    not user_agreed and not signal_correct
                )

                vote["outcome"] = "correct" if user_correct else "wrong"
                vote["signal_correct"] = signal_correct
                vote["actual_move_pct"] = outcome.get("actual_move_pct", 0)
                validated_count += 1

                # Update stats
                if user_correct:
                    if user_agreed:
                        data["stats"]["correct_agrees"] = (
                            data["stats"].get("correct_agrees", 0) + 1
                        )
                    else:
                        data["stats"]["correct_disagrees"] = (
                            data["stats"].get("correct_disagrees", 0) + 1
                        )

        if validated_count > 0:
            self._update_streak(data)
            _save_game(data, self.user_id)

        return validated_count

    def _update_streak(self, data: dict) -> None:
        """Recalculate the current accuracy streak."""
        # Look at most recent validated votes in reverse order
        validated = [
            v for v in data["votes"] if v.get("outcome") is not None
        ]
        validated.sort(key=lambda v: v.get("created_at", ""), reverse=True)

        streak = 0
        for v in validated:
            if v["outcome"] == "correct":
                streak += 1
            else:
                break

        data["stats"]["current_streak"] = streak
        data["stats"]["best_streak"] = max(
            streak, data["stats"].get("best_streak", 0)
        )

    def get_yesterday_scorecard(self) -> dict:
        """Get yesterday's scorecard showing AI vs User accuracy.

        Returns:
            {
                "date": "2026-02-26",
                "votes": [...],
                "user_correct": 3,
                "user_wrong": 1,
                "user_pending": 0,
                "user_accuracy": 75.0,
                "ai_correct": 2,
                "ai_wrong": 2,
                "ai_accuracy": 50.0,
                "user_beat_ai": True,
            }
        """
        data = _load_game(self.user_id)
        yesterday = _yesterday_str()

        yesterday_votes = [
            v for v in data["votes"] if v.get("date") == yesterday
        ]

        # Validate any pending outcomes
        self.validate_outcomes()
        # Reload after validation
        data = _load_game(self.user_id)
        yesterday_votes = [
            v for v in data["votes"] if v.get("date") == yesterday
        ]

        user_correct = sum(
            1 for v in yesterday_votes if v.get("outcome") == "correct"
        )
        user_wrong = sum(
            1 for v in yesterday_votes if v.get("outcome") == "wrong"
        )
        user_pending = sum(
            1 for v in yesterday_votes if v.get("outcome") is None
        )

        ai_correct = sum(
            1 for v in yesterday_votes if v.get("signal_correct") is True
        )
        ai_wrong = sum(
            1 for v in yesterday_votes if v.get("signal_correct") is False
        )

        total_validated = user_correct + user_wrong
        user_accuracy = (
            round(user_correct / total_validated * 100, 1)
            if total_validated > 0
            else 0
        )

        ai_total = ai_correct + ai_wrong
        ai_accuracy = (
            round(ai_correct / ai_total * 100, 1) if ai_total > 0 else 0
        )

        return {
            "date": yesterday,
            "votes": yesterday_votes,
            "user_correct": user_correct,
            "user_wrong": user_wrong,
            "user_pending": user_pending,
            "user_accuracy": user_accuracy,
            "ai_correct": ai_correct,
            "ai_wrong": ai_wrong,
            "ai_accuracy": ai_accuracy,
            "user_beat_ai": user_accuracy > ai_accuracy
            if total_validated > 0 and ai_total > 0
            else None,
            "total_votes": len(yesterday_votes),
        }

    def get_streak(self) -> dict:
        """Get current and best accuracy streaks."""
        data = _load_game(self.user_id)
        stats = data.get("stats", {})
        return {
            "current": stats.get("current_streak", 0),
            "best": stats.get("best_streak", 0),
            "total_votes": stats.get("total_votes", 0),
            "correct_agrees": stats.get("correct_agrees", 0),
            "correct_disagrees": stats.get("correct_disagrees", 0),
        }

    def get_all_time_stats(self) -> dict:
        """Get all-time prediction game statistics."""
        data = _load_game(self.user_id)
        votes = data.get("votes", [])
        stats = data.get("stats", {})

        validated = [v for v in votes if v.get("outcome") is not None]
        correct = sum(1 for v in validated if v["outcome"] == "correct")
        wrong = sum(1 for v in validated if v["outcome"] == "wrong")
        total = correct + wrong

        # Per-asset breakdown
        asset_stats = {}
        for v in validated:
            asset = v["asset"]
            if asset not in asset_stats:
                asset_stats[asset] = {"correct": 0, "wrong": 0}
            if v["outcome"] == "correct":
                asset_stats[asset]["correct"] += 1
            else:
                asset_stats[asset]["wrong"] += 1

        # Add accuracy to each asset
        for asset, s in asset_stats.items():
            t = s["correct"] + s["wrong"]
            s["accuracy"] = round(s["correct"] / t * 100, 1) if t > 0 else 0
            s["total"] = t

        return {
            "total_votes": stats.get("total_votes", 0),
            "validated": total,
            "correct": correct,
            "wrong": wrong,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
            "current_streak": stats.get("current_streak", 0),
            "best_streak": stats.get("best_streak", 0),
            "per_asset": asset_stats,
            "correct_agrees": stats.get("correct_agrees", 0),
            "correct_disagrees": stats.get("correct_disagrees", 0),
        }

    # Per-asset-class max move sanity bounds (percentage).
    # Anything beyond these in a validation window is price contamination.
    _INDEX_TICKERS = {"^GSPC", "^IXIC", "^DJI", "^RUT"}
    _CRYPTO_TICKERS = {"BTC-USD", "ETH-USD", "BTC", "ETH", "Bitcoin", "Ethereum"}
    _FOREX_TICKERS = {"EURUSD=X", "EUR/USD", "GBPUSD=X", "GBP/USD", "USDJPY=X",
                      "USD/JPY", "AUDUSD=X", "AUD/USD"}
    _COMMODITY_NAMES = {"Gold", "Silver", "Oil", "Copper", "Platinum", "Wheat",
                        "Natural Gas", "Palladium"}

    @classmethod
    def _max_move_for_asset(cls, asset: str, ticker: str = "") -> float:
        """Return the sanity-bound max % move for an asset class."""
        t = ticker.upper()
        a = asset.strip()
        # Indices
        if t in cls._INDEX_TICKERS or a in cls._INDEX_TICKERS:
            return 10.0
        # Crypto
        if a in cls._CRYPTO_TICKERS or t in cls._CRYPTO_TICKERS:
            return 50.0
        # Forex
        if a in cls._FOREX_TICKERS or t in cls._FOREX_TICKERS:
            return 5.0
        # Commodities (by name)
        if a in cls._COMMODITY_NAMES:
            return 20.0
        # Default: treat as individual stock
        return 25.0

    # Minimum absolute move (%) to count as a real "hit"
    _MIN_HIT_MOVE = 1.0
    # Moves below this are effectively zero and never count
    _NEAR_ZERO_THRESHOLD = 0.1

    def get_signals_you_ignored(self, limit: int = 5) -> list[dict]:
        """Get recent signals user didn't vote on that turned out correct.

        This is the 'regret engine' — shows missed opportunities.
        """
        data = _load_game(self.user_id)
        ai_preds = _load_ai_predictions()
        voted_keys = set()
        for v in data["votes"]:
            voted_keys.add(f"{v.get('date')}_{v.get('asset')}")

        ignored_hits = []
        for pred in reversed(ai_preds):
            if not isinstance(pred, dict):
                continue
            if not pred.get("validated"):
                continue
            # "outcome" is a string "correct"/"incorrect", not a boolean "correct"
            if pred.get("outcome") != "correct":
                continue
            # "timestamp" is the actual field, not "date"
            pred_ts = pred.get("timestamp", pred.get("date", ""))
            pred_date = pred_ts[:10] if pred_ts else ""
            key = f"{pred_date}_{pred.get('asset', '')}"
            if key not in voted_keys:
                entry_price = pred.get("entry_price", 0)
                outcome_price = pred.get("outcome_price", 0)
                actual_move = 0
                if entry_price and outcome_price:
                    actual_move = round(
                        (outcome_price - entry_price) / entry_price * 100, 2
                    )

                # --- Filter: effectively-zero moves are never hits ---
                if abs(actual_move) < self._NEAR_ZERO_THRESHOLD:
                    continue  # ±0.0% or ±0.09% is not a meaningful move

                # --- Filter: per-asset-class sanity bounds ---
                asset_name = pred.get("asset", "")
                ticker = pred.get("ticker", "")
                max_move = self._max_move_for_asset(asset_name, ticker)
                if abs(actual_move) > max_move:
                    continue  # Exceeds realistic move for this asset class

                # --- Filter: direction validation ---
                signal_label = pred.get("signal_label", pred.get("signal", ""))
                if signal_label in ("BUY", "STRONG BUY") and actual_move < 0:
                    continue  # BUY signal moved down — not a real hit
                if signal_label in ("SELL", "STRONG SELL") and actual_move > 0:
                    continue  # SELL signal moved up — not a real hit

                # --- Filter: minimum move threshold for a "hit" ---
                if signal_label in ("BUY", "STRONG BUY") and actual_move < self._MIN_HIT_MOVE:
                    continue  # Need at least +1% to count as a BUY hit
                if signal_label in ("SELL", "STRONG SELL") and actual_move > -self._MIN_HIT_MOVE:
                    continue  # Need at least -1% to count as a SELL hit

                ignored_hits.append({
                    "date": pred_date,
                    "asset": asset_name,
                    "signal": signal_label,
                    "actual_move_pct": actual_move,
                })
            if len(ignored_hits) >= limit:
                break

        return ignored_hits
