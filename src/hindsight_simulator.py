"""Hindsight Learning Simulator — time-travels 48h back to test predictions.

The simulator:
1. Fetches historical data as of 48h ago (pretends it's "now")
2. Runs the full signal scoring using only past data
3. Compares prediction with actual outcome over those 48 hours
4. Stores lessons: what would we have gotten right/wrong?
5. Feeds results into the market learner for strategy improvement

Usage:
    python hindsight_simulator.py              # run for all assets
    python hindsight_simulator.py --asset Gold  # run for one asset
    python hindsight_simulator.py --days 5      # custom lookback
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
SIMULATIONS_FILE = PROJECT_ROOT / "memory" / "hindsight_simulations.json"
LESSONS_FILE = PROJECT_ROOT / "memory" / "market_lessons.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "memory"))

# Import the scanner's watchlist and scoring logic
from market_scanner import WATCHLIST, score_signal


def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [HindsightSim] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_simulations() -> dict:
    if not SIMULATIONS_FILE.exists():
        return {
            "simulations": [],
            "stats": {
                "total": 0,
                "correct": 0,
                "incorrect": 0,
                "neutral": 0,
                "accuracy": 0,
            },
        }
    return json.loads(SIMULATIONS_FILE.read_text(encoding="utf-8"))


def _save_simulations(data: dict) -> None:
    SIMULATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SIMULATIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_lessons() -> dict:
    if not LESSONS_FILE.exists():
        return {"lessons": [], "rules": []}
    return json.loads(LESSONS_FILE.read_text(encoding="utf-8"))


def _save_lessons(data: dict) -> None:
    LESSONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Time-travel analysis: analyze asset "as of" a past date
# ---------------------------------------------------------------------------

def analyze_asset_at(ticker: str, as_of_date: datetime, lookback_days: int = 250) -> dict | None:
    """Fetch historical data and compute technicals as if 'as_of_date' were today.

    Only uses data available up to as_of_date (no peeking into the future).
    """
    # Download enough history before the as_of_date
    start_date = as_of_date - timedelta(days=lookback_days + 30)
    end_date = as_of_date

    try:
        df = yf.download(
            ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
        )
    except Exception as e:
        log(f"Failed to fetch data for {ticker} as of {as_of_date.date()}: {e}")
        return None

    if df.empty or len(df) < 50:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors="coerce")

    close = df["Close"]
    current = close.iloc[-1]

    # SMAs
    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1]
    sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    # Bollinger Bands
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = (bb_sma + 2 * bb_std).iloc[-1]
    bb_lower = (bb_sma - 2 * bb_std).iloc[-1]

    # Volatility
    last_30 = df.tail(30)
    high_30 = last_30["High"].max()
    low_30 = last_30["Low"].min()
    vol_30 = (high_30 - low_30) / current * 100

    return {
        "current_price": round(float(current), 2),
        "sma_20": round(float(sma_20), 2),
        "sma_50": round(float(sma_50), 2),
        "sma_200": round(float(sma_200), 2) if sma_200 is not None else None,
        "rsi_14": round(float(rsi), 2),
        "macd": round(float(macd_line.iloc[-1]), 4),
        "macd_signal": round(float(signal_line.iloc[-1]), 4),
        "macd_bullish": bool(macd_line.iloc[-1] > signal_line.iloc[-1]),
        "bb_upper": round(float(bb_upper), 2),
        "bb_lower": round(float(bb_lower), 2),
        "high_30d": round(float(high_30), 2),
        "low_30d": round(float(low_30), 2),
        "volatility_30d_pct": round(float(vol_30), 1),
        "golden_cross": bool(sma_200 is not None and sma_50 > sma_200),
        "rows": len(df),
        "as_of_date": as_of_date.strftime("%Y-%m-%d"),
    }


def get_actual_outcome(ticker: str, from_date: datetime, to_date: datetime) -> dict | None:
    """Get what actually happened to the price between from_date and to_date."""
    try:
        df = yf.download(
            ticker,
            start=from_date.strftime("%Y-%m-%d"),
            end=(to_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
        )
    except Exception:
        return None

    if df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors="coerce")

    start_price = float(df["Close"].iloc[0])
    end_price = float(df["Close"].iloc[-1])
    high = float(df["High"].max())
    low = float(df["Low"].min())
    pct_change = (end_price - start_price) / start_price * 100

    return {
        "start_price": round(start_price, 2),
        "end_price": round(end_price, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "pct_change": round(pct_change, 2),
        "max_drawdown": round((low - start_price) / start_price * 100, 2),
        "max_upside": round((high - start_price) / start_price * 100, 2),
    }


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def simulate_asset(name: str, hours_back: int = 48) -> dict | None:
    """Run a hindsight simulation for one asset.

    1. Go back `hours_back` hours
    2. Compute technicals as of that time
    3. Score the signal (what would we have said?)
    4. Check what actually happened
    5. Grade the prediction
    """
    config = WATCHLIST[name]
    ticker = config["ticker"]

    now = datetime.now(timezone.utc)
    past_time = now - timedelta(hours=hours_back)

    log(f"Time-travel: analyzing {name} as of {past_time.strftime('%Y-%m-%d %H:%M')} ({hours_back}h ago)")

    # Step 1: Analyze with only past data
    tech = analyze_asset_at(ticker, past_time)
    if tech is None:
        log(f"Insufficient data for {name} at {past_time.date()}")
        return None

    # Step 2: Score the signal (what would we have predicted?)
    signal = score_signal(name, tech, config)
    predicted_label = signal["label"]
    predicted_score = signal["score"]
    predicted_price = tech["current_price"]

    log(f"Hindsight prediction: {name} was {predicted_label} (score {predicted_score}) at ${predicted_price:,.2f}")

    # Step 3: Get actual outcome (what really happened in those hours)
    actual = get_actual_outcome(ticker, past_time, now)
    if actual is None:
        log(f"Could not fetch actual outcome for {name}")
        return None

    actual_price = actual["end_price"]
    pct_change = actual["pct_change"]

    # Step 4: Grade — was the prediction correct?
    if predicted_label in ("BUY", "STRONG BUY"):
        if pct_change > 1.0:
            outcome = "correct"
            grade = "A" if pct_change > 3.0 else "B"
            note = f"BUY signal correct: price rose {pct_change:+.2f}%"
        elif pct_change < -2.0:
            outcome = "incorrect"
            grade = "F"
            note = f"BUY signal wrong: price dropped {pct_change:+.2f}%"
        else:
            outcome = "neutral"
            grade = "C"
            note = f"BUY signal inconclusive: price moved {pct_change:+.2f}%"

    elif predicted_label in ("SELL", "STRONG SELL"):
        if pct_change < -1.0:
            outcome = "correct"
            grade = "A" if pct_change < -3.0 else "B"
            note = f"SELL signal correct: price dropped {pct_change:+.2f}%"
        elif pct_change > 2.0:
            outcome = "incorrect"
            grade = "F"
            note = f"SELL signal wrong: price rose {pct_change:+.2f}%"
        else:
            outcome = "neutral"
            grade = "C"
            note = f"SELL signal inconclusive: price moved {pct_change:+.2f}%"

    else:  # NEUTRAL
        if abs(pct_change) < 2.0:
            outcome = "correct"
            grade = "B"
            note = f"NEUTRAL correct: price stayed flat ({pct_change:+.2f}%)"
        else:
            outcome = "incorrect"
            grade = "D"
            note = f"NEUTRAL missed move: price moved {pct_change:+.2f}%"

    log(f"Result: {outcome.upper()} ({grade}) — {note}")

    # Step 5: Build simulation record
    sim_id = f"SIM-{now.strftime('%Y%m%d%H%M%S')}-{name}"
    simulation = {
        "id": sim_id,
        "timestamp": now.isoformat(),
        "asset": name,
        "ticker": ticker,
        "hours_back": hours_back,
        "simulated_date": past_time.strftime("%Y-%m-%d %H:%M"),
        "predicted_label": predicted_label,
        "predicted_score": predicted_score,
        "predicted_price": predicted_price,
        "actual_price": actual_price,
        "pct_change": pct_change,
        "max_drawdown": actual["max_drawdown"],
        "max_upside": actual["max_upside"],
        "outcome": outcome,
        "grade": grade,
        "note": note,
        "tech_snapshot": {
            "rsi": tech["rsi_14"],
            "macd_bullish": tech["macd_bullish"],
            "golden_cross": tech["golden_cross"],
            "volatility": tech["volatility_30d_pct"],
        },
    }

    # Step 6: Save and learn from failures
    data = _load_simulations()
    data["simulations"].append(simulation)

    # Update stats
    all_sims = data["simulations"]
    correct_count = sum(1 for s in all_sims if s["outcome"] == "correct")
    incorrect_count = sum(1 for s in all_sims if s["outcome"] == "incorrect")
    neutral_count = sum(1 for s in all_sims if s["outcome"] == "neutral")
    total_decisions = correct_count + incorrect_count
    accuracy = round(correct_count / total_decisions * 100, 1) if total_decisions > 0 else 0

    data["stats"] = {
        "total": len(all_sims),
        "correct": correct_count,
        "incorrect": incorrect_count,
        "neutral": neutral_count,
        "accuracy": accuracy,
    }
    _save_simulations(data)

    # Learn from failures
    if outcome == "incorrect":
        _learn_from_hindsight(simulation, tech)

    return simulation


def _learn_from_hindsight(sim: dict, tech: dict) -> None:
    """Analyze why a hindsight prediction failed and store the lesson."""
    lessons_data = _load_lessons()

    causes = []

    # Diagnose
    if tech["volatility_30d_pct"] > 25:
        causes.append(f"High volatility ({tech['volatility_30d_pct']}%) made signals unreliable")
    if tech["rsi_14"] > 65 and sim["predicted_label"] in ("BUY", "STRONG BUY"):
        causes.append(f"RSI was already elevated ({tech['rsi_14']}) — overbought risk missed")
    if tech["rsi_14"] < 35 and sim["predicted_label"] in ("SELL", "STRONG SELL"):
        causes.append(f"RSI was already low ({tech['rsi_14']}) — oversold bounce missed")
    if not tech["macd_bullish"] and sim["predicted_label"] in ("BUY", "STRONG BUY"):
        causes.append("MACD was bearish — momentum disagreed with buy signal")
    if tech["macd_bullish"] and sim["predicted_label"] in ("SELL", "STRONG SELL"):
        causes.append("MACD was bullish — momentum disagreed with sell signal")
    if not tech["golden_cross"] and sim["predicted_label"] in ("BUY", "STRONG BUY"):
        causes.append("No Golden Cross — long-term trend was not supportive")
    if abs(sim["pct_change"]) > 5:
        causes.append(f"Large move ({sim['pct_change']:+.1f}%) suggests external catalyst (news/event)")

    if not causes:
        causes.append("No clear pattern — may be market noise or external event")

    lesson = {
        "id": f"HSIM-{len(lessons_data['lessons']) + 1:03d}",
        "timestamp": sim["timestamp"],
        "prediction_id": sim["id"],
        "asset": sim["asset"],
        "signal_was": sim["predicted_label"],
        "entry_price": sim["predicted_price"],
        "outcome_price": sim["actual_price"],
        "pct_move": sim["pct_change"],
        "what_went_wrong": sim["note"],
        "probable_causes": causes,
        "lesson_learned": causes[0],
        "rule": f"Hindsight for {sim['asset']}: {causes[0]}",
        "source": "hindsight_simulator",
    }

    lessons_data["lessons"].append(lesson)

    rule = lesson["rule"]
    if rule not in lessons_data["rules"]:
        lessons_data["rules"].append(rule)

    _save_lessons(lessons_data)
    log(f"Hindsight lesson: {lesson['id']} — {lesson['lesson_learned'][:80]}")


# ---------------------------------------------------------------------------
# Run all assets
# ---------------------------------------------------------------------------

def simulate_all(hours_back: int = 48) -> list[dict]:
    """Run hindsight simulation for all assets in the watchlist."""
    log(f"=== Hindsight Simulator starting ({hours_back}h lookback) ===")
    results = []

    for name in WATCHLIST:
        try:
            result = simulate_asset(name, hours_back)
            if result:
                results.append(result)
        except Exception as e:
            log(f"ERROR simulating {name}: {e}")

    # Summary
    if results:
        correct = sum(1 for r in results if r["outcome"] == "correct")
        total = len(results)
        log(f"=== Hindsight complete: {correct}/{total} correct ({correct/total*100:.0f}%) ===")
    else:
        log("=== Hindsight complete: no results ===")

    return results


def get_simulation_stats() -> dict:
    """Get simulation statistics for dashboard display."""
    data = _load_simulations()
    sims = data["simulations"]

    if not sims:
        return data["stats"]

    # Per-asset breakdown
    assets = set(s["asset"] for s in sims)
    per_asset = {}
    for asset in sorted(assets):
        asset_sims = [s for s in sims if s["asset"] == asset]
        ac = sum(1 for s in asset_sims if s["outcome"] == "correct")
        ai = sum(1 for s in asset_sims if s["outcome"] == "incorrect")
        ad = ac + ai
        per_asset[asset] = {
            "total": len(asset_sims),
            "correct": ac,
            "incorrect": ai,
            "accuracy": round(ac / ad * 100, 1) if ad > 0 else 0,
            "avg_grade": _avg_grade([s["grade"] for s in asset_sims]),
        }

    # Grade distribution
    grades = {}
    for s in sims:
        g = s["grade"]
        grades[g] = grades.get(g, 0) + 1

    # Recent simulations
    recent = sorted(sims, key=lambda s: s["timestamp"], reverse=True)[:10]

    return {
        **data["stats"],
        "per_asset": per_asset,
        "grade_distribution": grades,
        "recent": recent,
    }


def _avg_grade(grades: list[str]) -> str:
    """Compute average grade from a list of letter grades."""
    grade_values = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
    values = [grade_values.get(g, 2) for g in grades]
    if not values:
        return "N/A"
    avg = sum(values) / len(values)
    if avg >= 3.5:
        return "A"
    elif avg >= 2.5:
        return "B"
    elif avg >= 1.5:
        return "C"
    elif avg >= 0.5:
        return "D"
    return "F"


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*80}")
    print(f"  HINDSIGHT SIMULATOR RESULTS")
    print(f"{'='*80}")
    print(f"  {'Asset':<10} {'Predicted':<14} {'Score':>6} {'Price Then':>12} {'Price Now':>12} {'Change':>8} {'Grade':>6} {'Result'}")
    print(f"  {'-'*85}")
    for r in results:
        print(
            f"  {r['asset']:<10} {r['predicted_label']:<14} {r['predicted_score']:>5} "
            f"${r['predicted_price']:>10,.2f} ${r['actual_price']:>10,.2f} "
            f"{r['pct_change']:>+7.2f}% {r['grade']:>5}  {r['outcome'].upper()}"
        )
    print(f"{'='*80}\n")

    # Overall stats
    data = _load_simulations()
    stats = data["stats"]
    print(f"  Overall: {stats['correct']} correct, {stats['incorrect']} incorrect, "
          f"{stats['neutral']} neutral — Accuracy: {stats['accuracy']}%\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hindsight Learning Simulator")
    parser.add_argument("--asset", default=None, help="Simulate one asset (Gold, BTC, ETH, Silver)")
    parser.add_argument("--hours", type=int, default=48, help="Hours to look back (default: 48)")
    parser.add_argument("--stats", action="store_true", help="Show simulation statistics")
    args = parser.parse_args()

    if args.stats:
        stats = get_simulation_stats()
        print(json.dumps(stats, indent=2))
    elif args.asset:
        if args.asset not in WATCHLIST:
            print(f"Unknown asset '{args.asset}'. Available: {', '.join(WATCHLIST.keys())}")
            sys.exit(1)
        result = simulate_asset(args.asset, args.hours)
        if result:
            print_summary([result])
    else:
        results = simulate_all(args.hours)
        if results:
            print_summary(results)
