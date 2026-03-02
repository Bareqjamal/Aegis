"""Market Learning Module — tracks predictions, validates outcomes, learns from mistakes.

Implements:
- Prediction archiving (every signal → market_predictions.json)
- Outcome validation (check if price hit target or stop-loss)
- Warum-Analyse (why was prediction wrong?)
- Strategy lessons (market_lessons.json)
- Win-rate tracking for Agent Performance dashboard

Usage:
    from market_learner import MarketLearner
    learner = MarketLearner()
    learner.record_prediction("Gold", signal_dict, tech_dict)
    learner.validate_all()
    learner.get_performance_stats()
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf
import pandas as pd

try:
    from config import ValidationConfig
except ImportError:
    class ValidationConfig:
        MIN_VALIDATION_HOURS = 1
        MAX_VALIDATION_HOURS = 48
        BUY_SUCCESS_PCT = 1.0
        BUY_FAILURE_PCT = -3.0
        SELL_SUCCESS_PCT = -1.0
        SELL_FAILURE_PCT = 3.0
        NEUTRAL_THRESHOLD_PCT = 3.0

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
PREDICTIONS_FILE = MEMORY_DIR / "market_predictions.json"
LESSONS_FILE = MEMORY_DIR / "market_lessons.json"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [MarketLearner] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_predictions() -> dict:
    default = {"predictions": [], "stats": {"total": 0, "validated": 0, "correct": 0}}
    if not PREDICTIONS_FILE.exists():
        return default
    try:
        return json.loads(PREDICTIONS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        log(f"WARNING: {PREDICTIONS_FILE} is corrupt, resetting to default")
        return default


def _save_predictions(data: dict) -> None:
    import tempfile
    content = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(PREDICTIONS_FILE.parent), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp_path).replace(PREDICTIONS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_lessons() -> dict:
    default = {"lessons": [], "rules": []}
    if not LESSONS_FILE.exists():
        return default
    try:
        return json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        log(f"WARNING: {LESSONS_FILE} is corrupt, resetting to default")
        return default


def _save_lessons(data: dict) -> None:
    import tempfile
    content = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(LESSONS_FILE.parent), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp_path).replace(LESSONS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Market Learner
# ---------------------------------------------------------------------------

class MarketLearner:

    def record_prediction(
        self,
        asset: str,
        ticker: str,
        signal: dict,
        tech: dict,
        news_sentiment: str | None = None,
    ) -> dict:
        """Record a new prediction when a signal is generated.

        Called by market_scanner after every signal scoring.
        """
        prediction = {
            "id": f"PRED-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{asset}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset": asset,
            "ticker": ticker,
            "signal_label": signal["label"],
            "signal_score": signal["score"],
            "entry_price": signal["execution"]["entry"],
            "target_price": signal["execution"]["target"],
            "stop_loss": signal["execution"]["stop_loss"],
            "risk_reward": signal["execution"]["risk_reward"],
            "rsi_at_signal": tech["rsi_14"],
            "macd_bullish": tech["macd_bullish"],
            "golden_cross": tech["golden_cross"],
            "volatility": tech["volatility_30d_pct"],
            "news_sentiment": news_sentiment,
            "validated": False,
            "outcome": None,       # "correct", "incorrect", "pending"
            "outcome_price": None,
            "outcome_date": None,
            "lesson_id": None,
        }

        data = _load_predictions()
        data["predictions"].append(prediction)
        data["stats"]["total"] = len(data["predictions"])
        _save_predictions(data)

        log(f"Prediction recorded: {prediction['id']} — {asset} {signal['label']} at ${signal['execution']['entry']:,.2f}")
        return prediction

    def validate_all(self) -> list[dict]:
        """Validate all unvalidated predictions against current prices.

        Checks if price hit target (correct) or stop-loss (incorrect),
        or if enough time has passed (48h) for a time-based assessment.
        """
        data = _load_predictions()
        validated = []

        for pred in data["predictions"]:
            if pred["validated"]:
                continue

            # Only validate predictions older than 1 hour
            pred_time = datetime.fromisoformat(pred["timestamp"])
            age_hours = (datetime.now(timezone.utc) - pred_time).total_seconds() / 3600
            if age_hours < ValidationConfig.MIN_VALIDATION_HOURS:
                continue

            try:
                current_price = self._get_current_price(pred["ticker"])
                if current_price is None:
                    continue

                result = self._evaluate_prediction(pred, current_price, age_hours)
                if result:
                    pred.update(result)
                    validated.append(pred)

                    if result["outcome"] == "incorrect":
                        self._learn_from_failure(pred, current_price)

            except Exception as e:
                log(f"Validation error for {pred['id']}: {e}")

        # Update stats
        all_validated = [p for p in data["predictions"] if p["validated"]]
        correct = [p for p in all_validated if p["outcome"] == "correct"]
        data["stats"]["validated"] = len(all_validated)
        data["stats"]["correct"] = len(correct)
        _save_predictions(data)

        if validated:
            log(f"Validated {len(validated)} predictions. "
                f"Win rate: {len(correct)}/{len(all_validated)} "
                f"({len(correct)/len(all_validated)*100:.0f}%)" if all_validated else "")

        return validated

    def _get_current_price(self, ticker: str) -> float | None:
        """Get the latest price for a ticker."""
        try:
            df = yf.download(ticker, period="1d", interval="1m", progress=False)
            if df.empty:
                df = yf.download(ticker, period="5d", interval="1d", progress=False)
            if df.empty:
                return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return float(df["Close"].iloc[-1])
        except Exception:
            return None

    def _evaluate_prediction(self, pred: dict, current_price: float, age_hours: float) -> dict | None:
        """Evaluate if a prediction was correct."""
        entry = pred["entry_price"]
        target = pred["target_price"]
        stop = pred["stop_loss"]
        label = pred["signal_label"]

        result = {
            "validated": True,
            "outcome_price": round(current_price, 4),
            "outcome_date": datetime.now(timezone.utc).isoformat(),
        }

        if label in ("BUY", "STRONG BUY"):
            # Buy signal: correct if price went toward target
            if current_price >= target:
                result["outcome"] = "correct"
                result["outcome_note"] = f"Target ${target:,.2f} reached! Price at ${current_price:,.2f}"
            elif current_price <= stop:
                result["outcome"] = "incorrect"
                result["outcome_note"] = f"Stop-loss ${stop:,.2f} hit. Price at ${current_price:,.2f}"
            elif age_hours >= ValidationConfig.MAX_VALIDATION_HOURS:
                # Time-based: did price move in the right direction?
                pct_change = (current_price - entry) / entry * 100
                if pct_change > ValidationConfig.BUY_SUCCESS_PCT:
                    result["outcome"] = "correct"
                    result["outcome_note"] = f"Price moved +{pct_change:.1f}% in {ValidationConfig.MAX_VALIDATION_HOURS}h"
                elif pct_change < ValidationConfig.BUY_FAILURE_PCT:
                    result["outcome"] = "incorrect"
                    result["outcome_note"] = f"Price dropped {pct_change:.1f}% in {ValidationConfig.MAX_VALIDATION_HOURS}h"
                else:
                    result["outcome"] = "neutral"
                    result["outcome_note"] = f"Price moved {pct_change:+.1f}% in {ValidationConfig.MAX_VALIDATION_HOURS}h (within noise)"
            else:
                return None  # Too early to judge

        elif label in ("SELL", "STRONG SELL"):
            pct_change = (current_price - entry) / entry * 100
            if age_hours >= ValidationConfig.MAX_VALIDATION_HOURS:
                if pct_change < ValidationConfig.SELL_SUCCESS_PCT:
                    result["outcome"] = "correct"
                    result["outcome_note"] = f"Price dropped {pct_change:.1f}% as predicted"
                elif pct_change > ValidationConfig.SELL_FAILURE_PCT:
                    result["outcome"] = "incorrect"
                    result["outcome_note"] = f"Price rose +{pct_change:.1f}% — sell signal was wrong"
                else:
                    result["outcome"] = "neutral"
                    result["outcome_note"] = f"Price moved {pct_change:+.1f}% (inconclusive)"
            else:
                return None

        else:  # NEUTRAL
            if age_hours >= ValidationConfig.MAX_VALIDATION_HOURS:
                pct_change = (current_price - entry) / entry * 100
                if abs(pct_change) < ValidationConfig.NEUTRAL_THRESHOLD_PCT:
                    result["outcome"] = "correct"
                    result["outcome_note"] = f"Price stayed flat ({pct_change:+.1f}%) — neutral was correct"
                else:
                    result["outcome"] = "neutral"
                    result["outcome_note"] = f"Price moved {pct_change:+.1f}% — neutral missed the move"
            else:
                return None

        return result

    def _learn_from_failure(self, pred: dict, current_price: float) -> None:
        """Analyze why a prediction failed and store the lesson.

        Deduplicates lessons: if the same cause + asset combination already
        exists in the lesson archive, the lesson is skipped to avoid spam.
        """
        lessons_data = _load_lessons()

        entry = pred["entry_price"]
        pct_move = (current_price - entry) / entry * 100

        # Diagnose potential causes
        causes = []
        if pred["volatility"] > 25:
            causes.append("High volatility environment — signals less reliable")
        if pred["rsi_at_signal"] > 65:
            causes.append("RSI was already elevated — overbought risk was underweighted")
        if pred["rsi_at_signal"] < 35:
            causes.append("RSI was low but price continued falling — trend was stronger than mean reversion")
        if not pred["macd_bullish"] and pred["signal_label"] in ("BUY", "STRONG BUY"):
            causes.append("MACD was bearish when buy signal was issued — momentum disagreed")
        if pred["risk_reward"] < 1.5:
            causes.append("Risk/Reward was below 1.5:1 — insufficient margin of safety")
        if pred.get("news_sentiment") == "BEARISH" and pred["signal_label"] in ("BUY", "STRONG BUY"):
            causes.append("News sentiment was bearish — market psychology overrode technicals")

        if not causes:
            causes.append("No obvious cause identified — may be random market noise")

        # Deduplicate: skip if this exact cause + asset already has a lesson
        primary_cause = causes[0]
        existing_keys = {
            (l["asset"], l["lesson_learned"])
            for l in lessons_data["lessons"]
        }
        if (pred["asset"], primary_cause) in existing_keys:
            log(f"Lesson deduplicated: '{primary_cause}' for {pred['asset']} already exists — skipping")
            return  # Already learned this lesson for this asset

        lesson = {
            "id": f"MKTL-{len(lessons_data['lessons']) + 1:03d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prediction_id": pred["id"],
            "asset": pred["asset"],
            "signal_was": pred["signal_label"],
            "entry_price": entry,
            "outcome_price": current_price,
            "pct_move": round(pct_move, 2),
            "what_went_wrong": pred.get("outcome_note", ""),
            "probable_causes": causes,
            "lesson_learned": primary_cause,
            "rule": f"For {pred['asset']}: {primary_cause}",
        }

        lessons_data["lessons"].append(lesson)

        # Update rules list (dedup)
        rule = lesson["rule"]
        if rule not in lessons_data["rules"]:
            lessons_data["rules"].append(rule)

        _save_lessons(lessons_data)
        log(f"Market lesson learned: {lesson['id']} — {lesson['lesson_learned'][:80]}")

    # ---------------------------------------------------------------------------
    # Strategy adaptation
    # ---------------------------------------------------------------------------

    def get_lessons_for_asset(self, asset: str) -> list[dict]:
        """Get all market lessons relevant to a specific asset."""
        data = _load_lessons()
        return [l for l in data["lessons"] if l["asset"] == asset]

    def get_all_rules(self) -> list[str]:
        """Get all learned market rules."""
        data = _load_lessons()
        return data.get("rules", [])

    def get_strategy_preamble(self, asset: str) -> str | None:
        """Generate a strategy preamble based on past lessons.

        Returns a string like:
        'Basierend auf meinen Erfahrungen vom 2026-02-07, achte ich besonders auf...'
        """
        lessons = self.get_lessons_for_asset(asset)
        if not lessons:
            return None

        latest = lessons[-1]
        date = latest["timestamp"][:10]
        causes = latest["probable_causes"]

        factors = " und ".join(causes[:2]) if len(causes) > 1 else causes[0]
        return (
            f"Basierend auf meinen Erfahrungen vom {date}, "
            f"achte ich dieses Mal besonders auf: {factors}."
        )

    # ---------------------------------------------------------------------------
    # Performance stats (for dashboard)
    # ---------------------------------------------------------------------------

    def get_performance_stats(self) -> dict:
        """Get overall and per-asset performance statistics."""
        data = _load_predictions()
        preds = data["predictions"]

        all_validated = [p for p in preds if p.get("validated")]
        correct = [p for p in all_validated if p.get("outcome") == "correct"]
        incorrect = [p for p in all_validated if p.get("outcome") == "incorrect"]
        neutral = [p for p in all_validated if p.get("outcome") == "neutral"]
        pending = [p for p in preds if not p.get("validated")]

        # Overall win rate
        total_decisions = len(correct) + len(incorrect)
        win_rate = (len(correct) / total_decisions * 100) if total_decisions > 0 else 0

        # Per-asset stats
        assets = set(p["asset"] for p in preds)
        per_asset = {}
        for asset in assets:
            asset_preds = [p for p in preds if p["asset"] == asset]
            asset_val = [p for p in asset_preds if p.get("validated")]
            asset_correct = [p for p in asset_val if p.get("outcome") == "correct"]
            asset_incorrect = [p for p in asset_val if p.get("outcome") == "incorrect"]
            asset_decisions = len(asset_correct) + len(asset_incorrect)
            per_asset[asset] = {
                "total": len(asset_preds),
                "validated": len(asset_val),
                "correct": len(asset_correct),
                "incorrect": len(asset_incorrect),
                "win_rate": round(len(asset_correct) / asset_decisions * 100, 1) if asset_decisions > 0 else 0,
                "latest_signal": asset_preds[-1]["signal_label"] if asset_preds else None,
            }

        # Per-signal-type stats
        signal_types = set(p["signal_label"] for p in preds)
        per_signal = {}
        for sig in signal_types:
            sig_preds = [p for p in all_validated if p["signal_label"] == sig]
            sig_correct = [p for p in sig_preds if p.get("outcome") == "correct"]
            sig_decisions = len([p for p in sig_preds if p.get("outcome") in ("correct", "incorrect")])
            per_signal[sig] = {
                "total": len(sig_preds),
                "correct": len(sig_correct),
                "win_rate": round(len(sig_correct) / sig_decisions * 100, 1) if sig_decisions > 0 else 0,
            }

        # Recent predictions for dashboard display
        recent = sorted(preds, key=lambda p: p["timestamp"], reverse=True)[:10]

        return {
            "total_predictions": len(preds),
            "validated": len(all_validated),
            "correct": len(correct),
            "incorrect": len(incorrect),
            "neutral": len(neutral),
            "pending": len(pending),
            "win_rate": round(win_rate, 1),
            "per_asset": per_asset,
            "per_signal": per_signal,
            "recent": recent,
            "lessons_count": len(_load_lessons()["lessons"]),
            "rules_count": len(_load_lessons()["rules"]),
        }


    # ---------------------------------------------------------------------------
    # Auto-trade intelligence: should we trade this signal?
    # ---------------------------------------------------------------------------

    def should_trade(self, asset: str, signal_label: str, tech_data: dict) -> tuple[bool, str]:
        """Consult past lessons to decide if a trade should be taken.

        Returns (True/False, reason_string).
        """
        lessons = self.get_lessons_for_asset(asset)
        if not lessons:
            return True, "No past lessons — trade allowed"

        # Check each lesson for pattern match with current conditions
        vetoes = []
        for lesson in lessons:
            cause = lesson.get("lesson_learned", "").lower()

            # Pattern: "High volatility environment" + current vol is high
            if "volatility" in cause and tech_data.get("volatility_30d_pct", 0) > 25:
                vetoes.append(f"Lesson {lesson['id']}: high volatility warning (vol={tech_data['volatility_30d_pct']}%)")

            # Pattern: "MACD was bearish when buy signal issued"
            if "macd" in cause and "bearish" in cause:
                if signal_label in ("BUY", "STRONG BUY") and not tech_data.get("macd_bullish", True):
                    vetoes.append(f"Lesson {lesson['id']}: MACD bearish on buy signal — momentum disagreed last time")

            # Pattern: "RSI was low but price continued falling"
            if "rsi" in cause and "continued falling" in cause:
                rsi = tech_data.get("rsi_14", 50)
                if signal_label in ("BUY", "STRONG BUY") and rsi < 35:
                    vetoes.append(f"Lesson {lesson['id']}: low RSI didn't hold last time (current RSI={rsi})")

            # Pattern: "Golden cross false signal"
            if "golden cross" in cause and "false" in cause:
                if tech_data.get("golden_cross") and signal_label in ("BUY", "STRONG BUY"):
                    vetoes.append(f"Lesson {lesson['id']}: golden cross was unreliable for {asset}")

            # Pattern: "News sentiment was bearish — market psychology overrode technicals"
            if "news sentiment" in cause and "overrode" in cause:
                vetoes.append(f"Lesson {lesson['id']}: news sentiment previously overrode technicals for {asset}")

        if vetoes:
            # Don't veto if we have more wins than losses overall for this asset
            stats = self.get_performance_stats()
            asset_stats = stats.get("per_asset", {}).get(asset, {})
            win_rate = asset_stats.get("win_rate", 0)
            if win_rate >= 60 and len(vetoes) <= 1:
                return True, f"Lesson warning ({vetoes[0][:60]}...) overridden by {win_rate}% win rate"
            return False, f"Blocked by {len(vetoes)} lesson(s): {vetoes[0][:100]}"

        return True, "All lesson checks passed"

    def get_indicator_reliability(self, asset: str) -> dict:
        """Analyze which indicators have been accurate for a given asset.

        Returns dict like: {"golden_cross": 0.6, "macd": 0.8, "rsi": 0.5, "news": 0.7}
        """
        data = _load_predictions()
        preds = [p for p in data["predictions"] if p["asset"] == asset and p.get("validated")]

        if len(preds) < 3:
            return {"golden_cross": 0.5, "macd": 0.5, "rsi": 0.5, "news": 0.5}

        # For each indicator, track how often it aligned with the correct outcome
        indicators = {"golden_cross": [], "macd": [], "rsi": [], "news": []}

        for pred in preds:
            is_correct = pred.get("outcome") == "correct"
            signal = pred.get("signal_label", "NEUTRAL")
            is_buy = signal in ("BUY", "STRONG BUY")

            # Golden cross: was it correct for buy signals?
            gc = pred.get("golden_cross", False)
            if is_buy:
                indicators["golden_cross"].append(1 if (gc and is_correct) or (not gc and not is_correct) else 0)

            # MACD: bullish should align with buy success
            macd_bull = pred.get("macd_bullish", False)
            if is_buy:
                indicators["macd"].append(1 if (macd_bull and is_correct) or (not macd_bull and not is_correct) else 0)

            # RSI: oversold + buy = good if correct
            rsi = pred.get("rsi_at_signal", 50)
            if is_buy:
                rsi_favorable = rsi < 50
                indicators["rsi"].append(1 if (rsi_favorable and is_correct) or (not rsi_favorable and not is_correct) else 0)

            # News sentiment
            news = pred.get("news_sentiment", "NEUTRAL")
            news_aligned = (news == "BULLISH" and is_buy) or (news == "BEARISH" and not is_buy)
            indicators["news"].append(1 if (news_aligned and is_correct) or (not news_aligned and not is_correct) else 0)

        result = {}
        for ind, outcomes in indicators.items():
            if outcomes:
                result[ind] = round(sum(outcomes) / len(outcomes), 2)
            else:
                result[ind] = 0.5  # no data = neutral

        return result

    def get_adaptive_weights(self, asset: str) -> dict:
        """Return adjusted confidence weights based on what's been accurate.

        Default: tech=0.40, news=0.20, history=0.40
        Adjusts based on indicator reliability scores.
        """
        reliability = self.get_indicator_reliability(asset)

        # Base weights
        tech_w = 0.40
        news_w = 0.20
        hist_w = 0.40

        # If technical indicators are highly reliable → boost tech weight
        tech_avg = (reliability.get("golden_cross", 0.5) + reliability.get("macd", 0.5) + reliability.get("rsi", 0.5)) / 3
        if tech_avg > 0.65:
            tech_w += 0.10
            hist_w -= 0.05
            news_w -= 0.05
        elif tech_avg < 0.35:
            tech_w -= 0.10
            hist_w += 0.05
            news_w += 0.05

        # If news has been a strong predictor → boost news weight
        news_rel = reliability.get("news", 0.5)
        if news_rel > 0.70:
            news_w += 0.10
            tech_w -= 0.05
            hist_w -= 0.05
        elif news_rel < 0.30:
            news_w = max(0.05, news_w - 0.10)
            tech_w += 0.05
            hist_w += 0.05

        # Normalize to sum to 1.0
        total = tech_w + news_w + hist_w
        return {
            "technical": round(tech_w / total, 2),
            "news": round(news_w / total, 2),
            "historical": round(hist_w / total, 2),
            # Keep short aliases for backward compat
            "tech": round(tech_w / total, 2),
            "history": round(hist_w / total, 2),
            "reliability": reliability,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Market Learning Module")
    parser.add_argument("--validate", action="store_true", help="Validate all pending predictions")
    parser.add_argument("--stats", action="store_true", help="Show performance stats")
    parser.add_argument("--lessons", action="store_true", help="Show learned lessons")
    args = parser.parse_args()

    learner = MarketLearner()

    if args.validate:
        results = learner.validate_all()
        print(f"\nValidated {len(results)} predictions.")
        for r in results:
            print(f"  {r['id']}: {r['outcome']} — {r.get('outcome_note', '')}")

    elif args.stats:
        stats = learner.get_performance_stats()
        print(json.dumps(stats, indent=2))

    elif args.lessons:
        data = _load_lessons()
        for l in data["lessons"]:
            print(f"\n{l['id']} ({l['asset']}):")
            print(f"  Signal was: {l['signal_was']}")
            print(f"  Outcome: {l['pct_move']:+.1f}%")
            print(f"  Lesson: {l['lesson_learned']}")

    else:
        print("Use --validate, --stats, or --lessons")
