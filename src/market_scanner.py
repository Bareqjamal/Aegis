"""Proactive Market Scanner — scans a watchlist for buy opportunities.

Fetches live data, computes technicals, scores each asset, generates
trade alerts as kanban tickets, and writes research reports with
Execution Plans to research_outputs/.

Usage:
    python market_scanner.py              # scan all assets
    python market_scanner.py --asset Gold  # scan one asset
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KANBAN_PATH = PROJECT_ROOT / "kanban_board.json"
RESEARCH_DIR = PROJECT_ROOT / "research_outputs"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

sys.path.insert(0, str(PROJECT_ROOT / "memory"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from memory_manager import add_lesson, pre_task_check, self_debug
from news_researcher import NewsResearcher
from chart_generator import ChartGenerator
from market_learner import MarketLearner

# Apply user settings from settings_override.json so scanner uses dashboard config
try:
    from config import apply_settings_override, PRICE_SANITY_BOUNDS, SignalConfig, TechnicalParams
    apply_settings_override()
except ImportError:
    PRICE_SANITY_BOUNDS = {}
    pass

# ---------------------------------------------------------------------------
# Watchlist: loads from user_watchlist.json if available, otherwise defaults
# ---------------------------------------------------------------------------
_USER_WATCHLIST_FILE = Path(__file__).resolve().parent / "data" / "user_watchlist.json"

_DEFAULT_WATCHLIST = {
    "Gold": {
        "ticker": "GC=F",
        "support": 4405.00,
        "target": 5400.00,
        "stop_pct": 0.03,
        "macro_bias": "bullish",
        "macro_reasons": [
            "Fed holding at 3.50-3.75%, 3-4 cuts expected in 2026",
            "Persistent inflation eroding fiat purchasing power",
            "Geopolitical safe-haven demand (Powell probe, global tensions)",
            "Analyst consensus: $4,800-$6,300 by year-end 2026",
        ],
    },
    "BTC": {
        "ticker": "BTC-USD",
        "support": 62000.00,
        "target": 95000.00,
        "stop_pct": 0.05,
        "macro_bias": "bullish",
        "macro_reasons": [
            "Institutional adoption continues (ETF inflows)",
            "Halving cycle historically precedes major rallies",
            "Fed liquidity additions act as crypto tailwind",
        ],
    },
    "ETH": {
        "ticker": "ETH-USD",
        "support": 2200.00,
        "target": 4500.00,
        "stop_pct": 0.05,
        "macro_bias": "neutral",
        "macro_reasons": [
            "Layer-2 scaling improving throughput",
            "ETH ETF flows mixed",
            "Competition from Solana and other L1s",
        ],
    },
    "Silver": {
        "ticker": "SI=F",
        "support": 62.00,
        "target": 95.00,
        "stop_pct": 0.04,
        "macro_bias": "bullish",
        "macro_reasons": [
            "Industrial demand rising (solar, EVs)",
            "Gold/Silver ratio elevated — silver historically undervalued",
            "Same Fed/inflation tailwinds as gold",
        ],
    },
}


def _load_watchlist() -> dict:
    """Load watchlist from user_watchlist.json if available, otherwise use defaults."""
    if _USER_WATCHLIST_FILE.exists():
        try:
            data = json.loads(_USER_WATCHLIST_FILE.read_text(encoding="utf-8"))
            watchlist = {}
            for name, cfg in data.items():
                if not cfg.get("enabled", True):
                    continue
                entry = {
                    "ticker": cfg.get("ticker", ""),
                    "support": cfg.get("support", 0),
                    "target": cfg.get("target", 0),
                    "stop_pct": cfg.get("stop_pct", 0.05),
                    "macro_bias": cfg.get("macro_bias", "neutral"),
                    "macro_reasons": cfg.get("macro_reasons", []),
                }
                watchlist[name] = entry
            if watchlist:
                return watchlist
        except Exception as e:
            log("Manager", f"WARNING: user_watchlist.json corrupted ({e}) — using defaults")
    return _DEFAULT_WATCHLIST


WATCHLIST = _load_watchlist()

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def log(role: str, message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{role}] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Technical analysis
# ---------------------------------------------------------------------------

def _sanity_check_price(ticker: str, price: float) -> bool:
    """Validate that a fetched price is within sane bounds.

    Returns True if price passes sanity check, False if it looks like bad data.
    Catches yfinance returning garbage values (e.g., BTC at $64.97 instead of $80K).
    """
    bounds = PRICE_SANITY_BOUNDS.get(ticker)
    if not bounds:
        return True  # No bounds defined — assume ok
    low, high = bounds
    if price < low or price > high:
        return False
    return True


import threading

# Global lock to serialize ALL yfinance API calls. yfinance uses shared global
# state internally (shared._DFS, session caches, cookie jars) that corrupts data
# when called from multiple threads — even with yf.Ticker().history().
# A trading app MUST have correct prices. Speed is secondary to accuracy.
_YF_LOCK = threading.Lock()


def _yf_fetch_with_retry(ticker: str, period: str = "1y", interval: str = "1d",
                          max_retries: int = 3) -> "pd.DataFrame":
    """Fetch yfinance data with global lock + exponential backoff retry.

    All yfinance calls are serialized via _YF_LOCK to prevent price
    cross-contamination between assets when scan_all() uses thread pools.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            with _YF_LOCK:
                df = yf.Ticker(ticker).history(period=period, interval=interval)
            if not df.empty:
                return df
        except Exception as e:
            last_err = e
        if attempt < max_retries - 1:
            wait = (2 ** attempt) + 0.5  # 0.5s, 2.5s, 4.5s
            time.sleep(wait)
    # All retries exhausted
    if last_err:
        raise last_err
    return pd.DataFrame()


def analyze_asset(ticker: str, period: str = "1y") -> dict:
    """Fetch data and compute full technical profile."""
    df = _yf_fetch_with_retry(ticker, period=period, interval="1d")
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    # Flatten MultiIndex columns if present (shouldn't happen with .history() but be safe)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors="coerce")

    close = df["Close"]
    current = close.iloc[-1]

    # Price sanity check — catch yfinance garbage data
    if not _sanity_check_price(ticker, current):
        # Try using the median of last 5 days as a fallback
        median_price = close.tail(5).median()
        if _sanity_check_price(ticker, median_price):
            log("Scanner", f"WARNING: {ticker} price ${current:,.2f} failed sanity check. Using 5-day median ${median_price:,.2f}")
            current = median_price
            # Also fix the last row so downstream calcs use the corrected price
            df.iloc[-1, df.columns.get_loc("Close")] = current
        else:
            raise ValueError(
                f"Price sanity check FAILED for {ticker}: ${current:,.2f} "
                f"(bounds: ${PRICE_SANITY_BOUNDS[ticker][0]:,.2f}-${PRICE_SANITY_BOUNDS[ticker][1]:,.2f}). "
                f"yfinance may have returned bad data."
            )

    # SMAs — using configurable TechnicalParams
    _sma_short = getattr(TechnicalParams, 'SMA_SHORT', 50)
    _sma_long = getattr(TechnicalParams, 'SMA_LONG', 200)
    _rsi_period = getattr(TechnicalParams, 'RSI_PERIOD', 14)
    _macd_fast = getattr(TechnicalParams, 'MACD_FAST', 12)
    _macd_slow = getattr(TechnicalParams, 'MACD_SLOW', 26)
    _macd_signal = getattr(TechnicalParams, 'MACD_SIGNAL', 9)
    _bb_period = getattr(TechnicalParams, 'BB_PERIOD', 20)
    _bb_std = getattr(TechnicalParams, 'BB_STD', 2.0)

    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(_sma_short).mean().iloc[-1]
    sma_200 = close.rolling(_sma_long).mean().iloc[-1] if len(close) >= _sma_long else None

    # RSI — configurable period
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(_rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(_rsi_period).mean()
    # Guard against division by zero: when loss=0 (all gains), RSI=100
    loss_safe = loss.replace(0, float("nan"))
    rs = gain / loss_safe
    rsi_series = 100 - (100 / (1 + rs))
    rsi_series = rsi_series.fillna(100.0)  # loss=0 → RSI=100 (standard convention)
    rsi = rsi_series.iloc[-1]

    # MACD — configurable spans
    ema_fast = close.ewm(span=_macd_fast, adjust=False).mean()
    ema_slow = close.ewm(span=_macd_slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=_macd_signal, adjust=False).mean()
    macd_val = macd_line.iloc[-1]
    macd_sig = signal_line.iloc[-1]

    # Bollinger Bands — configurable period and std
    bb_sma = close.rolling(_bb_period).mean()
    bb_std_series = close.rolling(_bb_period).std()
    bb_upper = (bb_sma + _bb_std * bb_std_series).iloc[-1]
    bb_lower = (bb_sma - _bb_std * bb_std_series).iloc[-1]

    # Volatility (30-day)
    last_30 = df.tail(30)
    high_30 = last_30["High"].max()
    low_30 = last_30["Low"].min()
    vol_30 = (high_30 - low_30) / current * 100

    # ATR-14 (Average True Range) — used for dynamic targets/stops
    atr_14 = 0.0
    if len(df) >= 15 and "High" in df.columns and "Low" in df.columns:
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift(1)).abs(),
            (df["Low"] - df["Close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr_14 = float(tr.rolling(14).mean().iloc[-1])

    # Volume analysis
    volume_today = 0
    volume_avg_20 = 0
    volume_ratio = 1.0
    if "Volume" in df.columns:
        vol_series = df["Volume"].dropna()
        if len(vol_series) >= 20:
            volume_today = float(vol_series.iloc[-1].item() if hasattr(vol_series.iloc[-1], 'item') else vol_series.iloc[-1])
            avg_val = vol_series.tail(20).mean()
            volume_avg_20 = float(avg_val.item() if hasattr(avg_val, 'item') else avg_val)
            volume_ratio = round(volume_today / volume_avg_20, 2) if volume_avg_20 > 0 else 1.0

    # Golden cross: guard against None and NaN for both SMAs
    if sma_200 is not None and not pd.isna(sma_200) and sma_50 is not None and not pd.isna(sma_50):
        golden_cross = bool(sma_50 > sma_200)
    else:
        golden_cross = False

    return {
        "current_price": round(current, 2),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2) if sma_200 is not None and not pd.isna(sma_200) else None,
        "rsi_14": round(rsi, 2),
        "macd": round(macd_val, 4),
        "macd_signal": round(macd_sig, 4),
        "macd_bullish": bool(macd_val > macd_sig),
        "bb_upper": round(bb_upper, 2),
        "bb_lower": round(bb_lower, 2),
        "high_30d": round(high_30, 2),
        "low_30d": round(low_30, 2),
        "volatility_30d_pct": round(vol_30, 1),
        "atr_14": round(atr_14, 4),
        "volume_today": volume_today,
        "volume_avg_20": round(volume_avg_20, 0),
        "volume_ratio": volume_ratio,
        "golden_cross": golden_cross,
        "rows": len(df),
    }


# ---------------------------------------------------------------------------
# Multi-Timeframe Confirmation (4h data for entry timing)
# ---------------------------------------------------------------------------

def analyze_multi_timeframe(ticker: str) -> dict:
    """Fetch 4-hour data and compute short-term indicators for entry timing.

    Returns a dict with 4h RSI, MACD direction, and a confirmation score.
    Used as a confidence modifier: if 4h confirms daily → +10% confidence.
    """
    try:
        df_4h = _yf_fetch_with_retry(ticker, period="60d", interval="1h")
        if df_4h.empty or len(df_4h) < 50:
            return {"available": False, "reason": "Insufficient 4h data"}

        # Flatten MultiIndex if present
        if isinstance(df_4h.columns, pd.MultiIndex):
            df_4h.columns = df_4h.columns.get_level_values(0)
        df_4h = df_4h.apply(pd.to_numeric, errors="coerce")

        # Resample to 4h candles
        df_4h = df_4h.resample("4h").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()

        if len(df_4h) < 30:
            return {"available": False, "reason": "Not enough 4h candles after resample"}

        close = df_4h["Close"]

        # 4h RSI-14
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi_4h = (100 - (100 / (1 + rs))).iloc[-1]
        rsi_4h = float(rsi_4h.item() if hasattr(rsi_4h, 'item') else rsi_4h)

        # 4h MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_4h_bullish = bool(macd_line.iloc[-1] > signal_line.iloc[-1])

        # 4h SMA-20 trend
        sma_20_4h = close.rolling(20).mean().iloc[-1]
        price_above_sma20 = bool(close.iloc[-1] > sma_20_4h)

        # Confirmation score: how many 4h indicators agree with a bullish view
        bullish_confirms = 0
        bearish_confirms = 0

        # RSI zones: only count clear directional signals, NOT neutral (40-60)
        if rsi_4h < 40:
            bullish_confirms += 1  # oversold = buy confirmation
        if rsi_4h > 60:
            bearish_confirms += 1  # overbought = sell confirmation
        if rsi_4h < 30:
            bullish_confirms += 1  # strongly oversold = strong buy confirm
        if rsi_4h > 70:
            bearish_confirms += 1  # strongly overbought = strong sell confirm

        if macd_4h_bullish:
            bullish_confirms += 1
        else:
            bearish_confirms += 1

        if price_above_sma20:
            bullish_confirms += 1
        else:
            bearish_confirms += 1

        return {
            "available": True,
            "rsi_4h": round(rsi_4h, 1),
            "macd_4h_bullish": macd_4h_bullish,
            "price_above_sma20_4h": price_above_sma20,
            "bullish_confirms": bullish_confirms,
            "bearish_confirms": bearish_confirms,
        }

    except Exception as e:
        return {"available": False, "reason": str(e)}


# ---------------------------------------------------------------------------
# Signal scoring
# ---------------------------------------------------------------------------

def score_signal(name: str, tech: dict, config: dict) -> dict:
    """Score an asset from -100 (strong sell) to +100 (strong buy).

    Returns dict with score, label, and reasoning.
    """
    score = 0
    reasons = []

    price = tech["current_price"]
    support = config["support"]
    target = config["target"]

    # =========================================================================
    # SYMMETRIC SCORING: max bullish = +100, max bearish = -100
    # Each factor scores symmetrically for both bull and bear cases.
    # =========================================================================

    _rsi_os = getattr(TechnicalParams, 'RSI_OVERSOLD', 30)
    _rsi_ob = getattr(TechnicalParams, 'RSI_OVERBOUGHT', 70)

    # 1. Proximity to support/resistance (±20)
    distance_to_support = (price - support) / support if support > 0 else 1.0
    distance_to_target = (target - price) / price if price > 0 else 1.0
    if distance_to_support <= 0.02:  # within 2% of support — bullish
        score += 20
        reasons.append(f"Price ${price:,.2f} is within 2% of support ${support:,.2f}")
    elif distance_to_support <= 0.05:
        score += 10
        reasons.append(f"Price ${price:,.2f} is within 5% of support ${support:,.2f}")
    elif distance_to_support > 0.30:  # far above support — less bullish support
        score -= 5
        reasons.append(f"Price is >30% above support — elevated risk")

    if distance_to_target <= 0.02:  # near target/resistance — bearish
        score -= 15
        reasons.append(f"Price near target/resistance ${target:,.2f} — upside limited")
    elif distance_to_target <= 0.05:
        score -= 8
        reasons.append(f"Price within 5% of target ${target:,.2f}")

    # 2. Moving average cross (±20)
    if tech["golden_cross"]:
        score += 20
        reasons.append(f"Golden Cross active (SMA-{getattr(TechnicalParams, 'SMA_SHORT', 50)} > SMA-{getattr(TechnicalParams, 'SMA_LONG', 200)})")
    elif tech.get("sma_200") and tech["sma_50"] < tech["sma_200"]:
        score -= 20
        reasons.append(f"Death Cross active (SMA-{getattr(TechnicalParams, 'SMA_SHORT', 50)} < SMA-{getattr(TechnicalParams, 'SMA_LONG', 200)})")

    # 3. RSI zone (±15) — symmetric using configurable thresholds
    rsi = tech["rsi_14"]
    if rsi < _rsi_os:
        score += 15
        reasons.append(f"RSI {rsi:.0f} — oversold (<{_rsi_os}), mean reversion likely")
    elif rsi < 45:
        score += 5
        reasons.append(f"RSI {rsi:.0f} — low, room for upside")
    elif rsi > _rsi_ob:
        score -= 15
        reasons.append(f"RSI {rsi:.0f} — overbought (>{_rsi_ob}), pullback risk")
    elif rsi > 55:
        score -= 5
        reasons.append(f"RSI {rsi:.0f} — elevated, limited upside")

    # 4. MACD momentum (±10) — symmetric
    if tech["macd_bullish"]:
        score += 10
        reasons.append("MACD above signal line (bullish momentum)")
    else:
        score -= 10
        reasons.append("MACD below signal line (bearish momentum)")

    # 5. Bollinger Band position (±10) — symmetric
    if price <= tech["bb_lower"] * 1.01:
        score += 10
        reasons.append(f"Price near Bollinger lower band ${tech['bb_lower']:,.2f}")
    elif price >= tech["bb_upper"] * 0.99:
        score -= 10
        reasons.append(f"Price near Bollinger upper band ${tech['bb_upper']:,.2f}")

    # 6. Macro bias (±15) — symmetric
    bias = config["macro_bias"]
    if bias == "bullish":
        score += 15
        reasons.append("Macro environment is bullish")
    elif bias == "bearish":
        score -= 15
        reasons.append("Macro environment is bearish")

    # 7. Risk/reward ratio (±5)
    risk = price - (support * (1 - config["stop_pct"]))
    reward = target - price
    rr_ratio = reward / risk if risk > 0 else 0
    if rr_ratio >= 2:
        score += 5
        reasons.append(f"Risk/Reward ratio {rr_ratio:.1f}:1 (favorable)")
    elif rr_ratio < 0.5 and rr_ratio >= 0:
        score -= 5
        reasons.append(f"Risk/Reward ratio {rr_ratio:.1f}:1 (unfavorable)")

    # 8. Volume confirmation (±10) — symmetric
    vol_ratio = tech.get("volume_ratio", 1.0)
    if vol_ratio > 1.5:
        score += 10
        reasons.append(f"Volume {vol_ratio:.1f}x above average (strong conviction)")
    elif vol_ratio > 1.0:
        score += 3
        reasons.append(f"Volume slightly above average ({vol_ratio:.1f}x)")
    elif vol_ratio < 0.5 and vol_ratio > 0:
        score -= 10
        reasons.append(f"Volume only {vol_ratio:.1f}x of average (weak conviction)")
    elif vol_ratio < 0.8 and vol_ratio > 0:
        score -= 3
        reasons.append(f"Volume below average ({vol_ratio:.1f}x)")

    # Clamp
    score = max(-100, min(100, score))

    # Label
    if score >= 60:
        label = "STRONG BUY"
    elif score >= 35:
        label = "BUY"
    elif score >= -10:
        label = "NEUTRAL"
    elif score >= -35:
        label = "SELL"
    else:
        label = "STRONG SELL"

    # Execution plan — dynamic targets/stops using ATR when static levels are stale
    atr = tech.get("atr_14", 0)
    static_target = config["target"]
    static_support = support
    stop_pct = config["stop_pct"]

    is_buy = label in ("BUY", "STRONG BUY")
    is_sell = label in ("SELL", "STRONG SELL")

    # Dynamic target: use static if sensible, otherwise ATR-based
    if is_buy and static_target <= price:
        # Static target is stale (below current price for a BUY)
        target_final = round(price + max(atr * 3, price * 0.08), 2) if atr > 0 else round(price * 1.08, 2)
    elif is_sell and static_target >= price:
        # Static target is stale (above current price for a SELL)
        target_final = round(price - max(atr * 3, price * 0.08), 2) if atr > 0 else round(price * 0.92, 2)
    else:
        target_final = static_target

    # Dynamic stop-loss: use ATR-based if static support is stale
    static_stop = round(static_support * (1 - stop_pct), 2)
    if is_buy and static_stop >= price:
        # Static stop is above entry (nonsensical for a long position)
        stop_loss = round(price - max(atr * 2, price * 0.05), 2) if atr > 0 else round(price * 0.95, 2)
    elif is_buy and static_stop < price * 0.5:
        # Static stop is unreasonably far away (>50% drawdown)
        stop_loss = round(price - max(atr * 2, price * 0.05), 2) if atr > 0 else round(price * 0.95, 2)
    else:
        stop_loss = static_stop

    # Recalculate risk/reward with final values
    risk_final = price - stop_loss if is_buy else stop_loss - price
    reward_final = target_final - price if is_buy else price - target_final
    rr_final = round(reward_final / risk_final, 1) if risk_final > 0 else 0

    execution = {
        "entry": price,
        "target": target_final,
        "stop_loss": stop_loss,
        "risk_reward": rr_final,
    }

    return {
        "score": score,
        "label": label,
        "reasons": reasons,
        "execution": execution,
    }


# ---------------------------------------------------------------------------
# Kanban ticket creation
# ---------------------------------------------------------------------------

def create_trade_alert(name: str, signal: dict, tech: dict) -> str | None:
    """Create a TRADE ALERT ticket in the kanban To Do column.

    Returns the ticket ID if created, None if alert already exists.
    """
    ex = signal["execution"]
    title = f"TRADE ALERT: Buy {name} - Target ${ex['target']:,.2f}"

    with open(KANBAN_PATH, "r", encoding="utf-8") as f:
        board_data = json.load(f)

    # Check if alert already exists (avoid duplicates)
    for status_tickets in board_data["board"].values():
        for t in status_tickets:
            if t["title"] == title:
                return None

    # Find next ticket ID
    all_ids = []
    for status_tickets in board_data["board"].values():
        for t in status_tickets:
            num = t["id"].replace("AEGIS-", "")
            if num.isdigit():
                all_ids.append(int(num))
    next_id = max(all_ids) + 1 if all_ids else 11

    ticket_id = f"AEGIS-{next_id:03d}"
    ticket = {
        "id": ticket_id,
        "title": title,
        "description": (
            f"Signal: {signal['label']} (score {signal['score']}/100) | "
            f"Entry: ${ex['entry']:,.2f} | Target: ${ex['target']:,.2f} | "
            f"Stop-Loss: ${ex['stop_loss']:,.2f} | R:R {ex['risk_reward']}:1"
        ),
        "priority": "high",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    board_data["board"]["To Do"].insert(0, ticket)

    with open(KANBAN_PATH, "w", encoding="utf-8") as f:
        json.dump(board_data, f, indent=2, ensure_ascii=False)

    return ticket_id


# ---------------------------------------------------------------------------
# Research report writer
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Confidence Score (0-100%) — Tickeron-style probability index
# ---------------------------------------------------------------------------

def calculate_confidence(
    name: str,
    signal: dict,
    tech: dict,
    news_data: dict | None,
    learner: MarketLearner,
) -> dict:
    """Calculate a confidence score from 0-100%.

    Combines:
    - Technical signal strength (default 40% weight)
    - News/macro sentiment alignment (default 20% weight)
    - Historical win-rate for this asset (default 40% weight)

    Weights are ADAPTIVE: adjusted per-asset based on which component
    has been most accurate historically (via learner.get_adaptive_weights).
    """
    # Get adaptive weights for this asset (falls back to defaults if no history)
    try:
        weights = learner.get_adaptive_weights(name)
        w_tech = weights.get("technical", 0.40)
        w_news = weights.get("news", 0.20)
        w_hist = weights.get("historical", 0.40)
    except Exception:
        w_tech, w_news, w_hist = 0.40, 0.20, 0.40
    # Normalize weights to sum to 1.0 (prevents inflated/deflated confidence)
    w_total = w_tech + w_news + w_hist
    if w_total > 0 and abs(w_total - 1.0) > 0.001:
        w_tech /= w_total
        w_news /= w_total
        w_hist /= w_total

    # 1. Technical component: normalize signal score (-100..+100) → (0..100)
    raw_score = signal["score"]
    # For BUY signals, higher is better; for SELL, more negative is "more confident"
    if signal["label"] in ("BUY", "STRONG BUY"):
        tech_conf = max(0, min(100, raw_score))
    elif signal["label"] in ("SELL", "STRONG SELL"):
        tech_conf = max(0, min(100, abs(raw_score)))
    else:
        tech_conf = max(0, min(100, 50 - abs(raw_score) * 0.5))  # neutral = low confidence

    # Indicator alignment bonus — symmetric for BUY and SELL
    aligned = 0
    if signal["label"] in ("BUY", "STRONG BUY"):
        if tech["golden_cross"]:
            aligned += 1
        if tech["macd_bullish"]:
            aligned += 1
        if tech["rsi_14"] < 60:
            aligned += 1
        if signal["execution"]["risk_reward"] >= 2.0:
            aligned += 1
    elif signal["label"] in ("SELL", "STRONG SELL"):
        if not tech["golden_cross"] and tech.get("sma_200") is not None:
            aligned += 1  # death cross (SMA50 < SMA200)
        if not tech["macd_bullish"]:  # bearish MACD
            aligned += 1
        if tech["rsi_14"] > 60:
            aligned += 1  # overbought territory aligns with SELL thesis
        if signal["execution"]["risk_reward"] >= 2.0:
            aligned += 1
    alignment_bonus = aligned * 5  # up to +20
    tech_conf = min(100, tech_conf + alignment_bonus)

    # 2. News component: sentiment alignment with signal direction
    news_conf = 50  # default neutral
    if news_data:
        sent = news_data.get("sentiment_score", 0)
        if signal["label"] in ("BUY", "STRONG BUY"):
            news_conf = max(0, min(100, 50 + sent * 50))  # bullish news = higher
        elif signal["label"] in ("SELL", "STRONG SELL"):
            news_conf = max(0, min(100, 50 - sent * 50))  # bearish news = higher for sell
        else:
            news_conf = max(0, min(100, 50 - abs(sent) * 30))

    # 3. Historical win-rate component
    stats = learner.get_performance_stats()
    asset_stats = stats.get("per_asset", {}).get(name, {})
    history_conf = 50  # default if no history
    if asset_stats.get("validated", 0) >= 2:
        history_conf = asset_stats.get("win_rate", 50)

    # 4. News Impact component (geopolitical/macro causal reasoning)
    impact_conf = 50  # default neutral
    impact_data_for_return = None
    try:
        from news_impact import NewsImpactEngine
        _impact_engine = NewsImpactEngine()
        _impact_result = _impact_engine.analyze(name, news_data=news_data)
        impact_data_for_return = _impact_result

        # Map impact_score (-100..+100) to confidence component (0..100)
        imp_score = _impact_result.get("impact_score", 0)
        imp_direction = _impact_result.get("direction", "NEUTRAL")

        # Impact boosts confidence when it ALIGNS with signal direction
        is_buy = signal["label"] in ("BUY", "STRONG BUY")
        is_sell = signal["label"] in ("SELL", "STRONG SELL")

        if (is_buy and imp_direction == "BULLISH") or (is_sell and imp_direction == "BEARISH"):
            # Aligned — impact supports the signal
            impact_conf = 50 + abs(imp_score) / 2  # 50..100
        elif (is_buy and imp_direction == "BEARISH") or (is_sell and imp_direction == "BULLISH"):
            # Contradicts — impact warns against the signal
            impact_conf = 50 - abs(imp_score) / 2  # 0..50
        else:
            impact_conf = 50  # neutral impact
        impact_conf = max(0, min(100, impact_conf))
    except Exception:
        pass  # silently fall back to neutral

    # Adaptive weighted average (weights adjust based on what's been working)
    # When impact data exists, give it 10% weight (taken proportionally from others)
    if impact_data_for_return and impact_data_for_return.get("total_geo_articles", 0) > 0:
        # Geo-driven: tech 30%, news 15%, history 35%, impact 20%
        w_impact = 0.20
        scale = (1.0 - w_impact) / (w_tech + w_news + w_hist) if (w_tech + w_news + w_hist) > 0 else 1.0
        confidence = (tech_conf * w_tech * scale) + (news_conf * w_news * scale) + (history_conf * w_hist * scale) + (impact_conf * w_impact)
    else:
        w_impact = 0.0
        confidence = (tech_conf * w_tech) + (news_conf * w_news) + (history_conf * w_hist)
    confidence = round(max(0, min(100, confidence)), 1)

    # 5. Social sentiment overlay (if available) — up to +/-10 boost
    social_boost = 0.0
    social_score = 0.0
    social_label = "N/A"
    try:
        import json as _json
        _social_cache = Path(__file__).resolve().parent / "data" / "social_sentiment.json"
        if _social_cache.exists():
            _social_data = _json.loads(_social_cache.read_text(encoding="utf-8"))
            _asset_social = _social_data.get("asset_scores", {}).get(name, {})
            social_score = _asset_social.get("social_score", 0.0)
            social_label = _asset_social.get("social_label", "N/A")
            buzz = _asset_social.get("buzz_level", "LOW")

            # Social boost: aligned with signal direction = +, against = -
            if signal["label"] in ("BUY", "STRONG BUY"):
                social_boost = social_score * 10  # +1.0 score = +10 boost
            elif signal["label"] in ("SELL", "STRONG SELL"):
                social_boost = -social_score * 10  # bearish social = boost for sells
            # Amplify if buzz is high
            if buzz == "HIGH":
                social_boost *= 1.5
            social_boost = max(-10, min(10, social_boost))
            confidence = round(max(0, min(100, confidence + social_boost)), 1)
    except Exception as e:
        log(name, f"WARNING: Social sentiment boost failed: {e}")

    # Level label
    if confidence >= 80:
        level = "HIGH"
    elif confidence >= 60:
        level = "MEDIUM"
    elif confidence >= 40:
        level = "LOW"
    else:
        level = "VERY LOW"

    return {
        "confidence_pct": confidence,
        "level": level,
        "tech_component": round(tech_conf, 1),
        "news_component": round(news_conf, 1),
        "history_component": round(history_conf, 1),
        "impact_component": round(impact_conf, 1),
        "social_component": round(social_boost, 1),
        "social_score": social_score,
        "social_label": social_label,
        "indicators_aligned": aligned,
        "history_trades": asset_stats.get("validated", 0),
        "history_win_rate": asset_stats.get("win_rate", 0),
        "weights": {"technical": w_tech, "news": w_news, "historical": w_hist, "impact": w_impact},
        "news_impact": impact_data_for_return,
    }


# ---------------------------------------------------------------------------
# Mini-Backtest — "Would this strategy have worked in the last 30 days?"
# ---------------------------------------------------------------------------

def backtest_strategy(ticker: str, config: dict, days: int = 30) -> dict:
    """Simulate signal scoring over the last N days to check strategy viability.

    Returns success rate and P&L summary.
    """
    try:
        df = _yf_fetch_with_retry(ticker, period="3mo", interval="1d")
        if df.empty or len(df) < days + 50:
            return {"success": False, "reason": "Insufficient data for backtest"}

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.apply(pd.to_numeric, errors="coerce")

        close = df["Close"]

        # Need at least 200 rows for SMA-200
        if len(close) < 200:
            sma_200_available = False
        else:
            sma_200_available = True

        # Compute indicators over full range
        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean() if sma_200_available else None
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()

        # Simulate over last N trading days
        test_range = df.iloc[-days:]
        trades = []

        for i, (idx, row) in enumerate(test_range.iterrows()):
            pos = df.index.get_loc(idx)
            price = float(close.iloc[pos])
            r = float(rsi.iloc[pos]) if not pd.isna(rsi.iloc[pos]) else 50

            # Simplified signal check: golden cross + RSI < 60 + MACD bullish
            if sma_200_available and sma_200 is not None:
                sma_50_val = float(sma_50.iloc[pos])
                sma_200_val = float(sma_200.iloc[pos])
                gc = bool(
                    not pd.isna(sma_50_val) and not pd.isna(sma_200_val)
                    and sma_50_val > sma_200_val
                )
            else:
                gc = False
            macd_bull = bool(float(macd_line.iloc[pos]) > float(macd_signal.iloc[pos]))

            buy_signal = gc and r < 60 and macd_bull

            if buy_signal and i + 5 < len(test_range):
                # Check 5-day forward return
                future_price = float(test_range.iloc[i + 5]["Close"])
                pct_return = (future_price - price) / price * 100
                trades.append({
                    "date": str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    "entry": round(price, 2),
                    "exit": round(future_price, 2),
                    "return_pct": round(pct_return, 2),
                    "profitable": pct_return > 0,
                })

        if not trades:
            return {
                "success": True,
                "total_signals": 0,
                "profitable": 0,
                "success_rate": 0,
                "avg_return": 0,
                "summary": "No buy signals generated in the last 30 days with current strategy.",
            }

        profitable = sum(1 for t in trades if t["profitable"])
        rate = round(profitable / len(trades) * 100, 1)
        avg_ret = round(sum(t["return_pct"] for t in trades) / len(trades), 2)

        return {
            "success": True,
            "total_signals": len(trades),
            "profitable": profitable,
            "success_rate": rate,
            "avg_return": avg_ret,
            "trades": trades[-5:],  # Last 5 for display
            "summary": f"Strategy backtested: {rate}% success rate over {len(trades)} signals in the last {days} days (avg return: {avg_ret:+.2f}%).",
        }

    except Exception as e:
        return {"success": False, "reason": str(e)}


def generate_reasoning(name: str, config: dict, tech: dict, signal: dict) -> list[str]:
    """Reasoning Agent: produce a plain-language 'Warum?' section.

    No jargon. Explains the decision as if to a non-finance audience.
    """
    label = signal["label"]
    score = signal["score"]
    price = tech["current_price"]
    ex = signal["execution"]
    lines = []

    # 1) One-sentence conclusion
    if score >= 35:
        lines.append(f"**Fazit:** {name} sieht nach einer Kaufgelegenheit aus (Score {score}/100).")
    elif score >= -10:
        lines.append(f"**Fazit:** {name} zeigt aktuell kein klares Signal — abwarten ist sinnvoll (Score {score}/100).")
    else:
        lines.append(f"**Fazit:** {name} steht unter Druck — kein guter Zeitpunkt zum Kaufen (Score {score}/100).")
    lines.append("")

    # 2) Top factors explained simply
    lines.append("**Die wichtigsten Gruende fuer diese Einschaetzung:**")
    lines.append("")

    # Support proximity
    dist = (price - config["support"]) / config["support"] * 100
    if dist <= 5:
        lines.append(
            f"1. **Nahe am Sicherheitsnetz:** Der Preis (${price:,.2f}) ist nur {dist:.1f}% "
            f"ueber der wichtigen Unterstuetzungslinie bei ${config['support']:,.2f}. "
            f"Das ist wie ein Ball, der nahe am Boden ist — er hat mehr Platz nach oben als nach unten."
        )
    else:
        lines.append(
            f"1. **Abstand zum Sicherheitsnetz:** Der Preis (${price:,.2f}) liegt {dist:.1f}% "
            f"ueber der Unterstuetzung bei ${config['support']:,.2f}. "
            f"Es gibt noch Raum nach unten, bevor das Sicherheitsnetz greift."
        )

    # Trend
    if tech["golden_cross"]:
        lines.append(
            f"2. **Langfristiger Aufwaertstrend:** Der kurzfristige Durchschnitt (${tech['sma_50']:,.2f}) "
            f"liegt ueber dem langfristigen (${tech['sma_200']:,.2f}). "
            f"Das nennt man 'Goldenes Kreuz' — historisch ein Zeichen, dass die Preise weiter steigen."
        )
    elif tech["sma_200"]:
        lines.append(
            f"2. **Langfristiger Abwaertstrend:** Der kurzfristige Durchschnitt liegt unter dem langfristigen. "
            f"Das bedeutet, der Markt hat in letzter Zeit an Schwung verloren."
        )
    else:
        lines.append(
            f"2. **Trend unklar:** Nicht genug historische Daten fuer eine Langzeit-Trendanalyse."
        )

    # Macro
    bias = config["macro_bias"]
    if bias == "bullish":
        top_reason = config["macro_reasons"][0] if config["macro_reasons"] else "positive wirtschaftliche Signale"
        lines.append(
            f"3. **Wirtschaftliches Umfeld spricht dafuer:** {top_reason}. "
            f"Die grosse Geldpolitik arbeitet aktuell fuer dieses Asset, nicht dagegen."
        )
    elif bias == "bearish":
        lines.append(
            f"3. **Wirtschaftliches Umfeld ist schwierig:** Die Rahmenbedingungen "
            f"(Zinsen, Inflation, Geopolitik) drücken aktuell auf den Preis."
        )
    else:
        lines.append(
            f"3. **Wirtschaftlich gemischt:** Es gibt sowohl positive als auch negative Signale "
            f"im Umfeld — keiner hat die Oberhand."
        )
    lines.append("")

    # 3) Risks
    lines.append("**Was schief gehen koennte:**")
    lines.append("")
    vol = tech["volatility_30d_pct"]
    lines.append(
        f"- Die Schwankungsbreite der letzten 30 Tage betraegt {vol}%. "
        f"{'Das ist sehr hoch — der Preis kann schnell in beide Richtungen ausschlagen.' if vol > 20 else 'Das ist moderat.'}"
    )
    if ex["risk_reward"] < 1.5:
        lines.append(
            f"- Das Verhaeltnis von Chance zu Risiko ({ex['risk_reward']}:1) ist nicht ideal. "
            f"Idealerweise sollte man mindestens 2:1 anstreben."
        )
    lines.append(
        f"- Wenn der Preis unter ${ex['stop_loss']:,.2f} faellt, sollte man aussteigen um Verluste zu begrenzen."
    )
    lines.append("")

    # 4) Confidence
    if score >= 60:
        conf = "Hoch"
        conf_reason = "Mehrere Indikatoren und das Marktumfeld zeigen in die gleiche Richtung."
    elif score >= 35:
        conf = "Mittel"
        conf_reason = "Einige positive Signale, aber nicht alle Faktoren sind eindeutig."
    elif score >= 0:
        conf = "Niedrig"
        conf_reason = "Die Signale sind gemischt — es gibt keinen klaren Vorteil."
    else:
        conf = "Niedrig (negativ)"
        conf_reason = "Die Mehrheit der Indikatoren spricht gegen einen Kauf."
    lines.append(f"**Konfidenz:** {conf} — {conf_reason}")

    return lines


def write_report(
    name: str, config: dict, tech: dict, signal: dict,
    news: dict | None = None,
    confidence: dict | None = None,
    backtest: dict | None = None,
) -> Path:
    """Write a full research report with Execution Plan, Reasoning, News, Confidence, and Backtest."""
    ex = signal["execution"]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    safe_name = name.replace("/", "_").replace(" ", "_")
    filename = f"{safe_name}_Signal_{signal['label'].replace(' ', '_')}.md"
    filepath = RESEARCH_DIR / filename

    lines = [
        f"# {signal['label']}: {name} ({config['ticker']})",
        f"",
        f"**Generated:** {ts} UTC",
        f"**Signal Score:** {signal['score']}/100",
        f"**Signal Label:** {signal['label']}",
    ]

    # Confidence score
    if confidence:
        lines.append(f"**Confidence:** {confidence['confidence_pct']}% ({confidence['level']})")

    # Add news sentiment if available
    if news:
        lines.append(f"**News Sentiment:** {news['sentiment_label']} ({news['sentiment_score']:+.2f})")

    lines += [
        f"",
        f"---",
        f"",
        f"## Warum diese Einschaetzung? (Reasoning Agent)",
        f"",
    ]
    lines += generate_reasoning(name, config, tech, signal)

    # News-backed reasoning section
    if news and (news.get("top_bullish") or news.get("top_bearish")):
        lines += [
            f"",
            f"---",
            f"",
            f"## Was sagen die Nachrichten? (News Research Agent)",
            f"",
            f"**Gesamtstimmung:** {news['sentiment_label']} ({news['sentiment_score']:+.2f}) "
            f"aus {news['relevant_count']} relevanten Artikeln",
            f"",
        ]
        if news.get("top_bullish"):
            lines.append("**Positive Nachrichten:**")
            lines.append("")
            for art in news["top_bullish"]:
                source = art.get("source", "Unknown")
                pub = art.get("published", "")
                link = art.get("link", "")
                title = art["title"]
                if link:
                    lines.append(f"- [{title}]({link}) — *{source}* {pub}")
                else:
                    lines.append(f"- {title} — *{source}* {pub}")
            lines.append("")
        if news.get("top_bearish"):
            lines.append("**Negative Nachrichten:**")
            lines.append("")
            for art in news["top_bearish"]:
                source = art.get("source", "Unknown")
                pub = art.get("published", "")
                link = art.get("link", "")
                title = art["title"]
                if link:
                    lines.append(f"- [{title}]({link}) — *{source}* {pub}")
                else:
                    lines.append(f"- {title} — *{source}* {pub}")
            lines.append("")

    # Confidence breakdown
    if confidence:
        lines += [
            f"",
            f"---",
            f"",
            f"## Confidence Score: {confidence['confidence_pct']}% ({confidence['level']})",
            f"",
            f"| Component | Score | Weight |",
            f"|-----------|-------|--------|",
            f"| Technical Analysis | {confidence['tech_component']}% | {confidence.get('weights', {}).get('technical', 0.4):.0%} |",
            f"| News Alignment | {confidence['news_component']}% | {confidence.get('weights', {}).get('news', 0.2):.0%} |",
            f"| News Impact (Causal) | {confidence.get('impact_component', 50)}% | {confidence.get('weights', {}).get('impact', 0):.0%} |",
            f"| Historical Win-Rate | {confidence['history_component']}% | {confidence.get('weights', {}).get('historical', 0.4):.0%} |",
            f"",
            f"Indicators aligned: {confidence['indicators_aligned']}/4 | "
            f"Historical trades: {confidence['history_trades']} | "
            f"Win-rate: {confidence['history_win_rate']}%",
        ]

    # Backtest results
    if backtest and backtest.get("success"):
        lines += [
            f"",
            f"---",
            f"",
            f"## Strategy Backtest (Last 30 Days)",
            f"",
            f"**{backtest['summary']}**",
            f"",
        ]
        if backtest.get("trades"):
            lines += [
                f"| Date | Entry | Exit | Return |",
                f"|------|-------|------|--------|",
            ]
            for t in backtest["trades"]:
                ret_str = f"{t['return_pct']:+.2f}%"
                lines.append(f"| {t['date']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | {ret_str} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Execution Plan",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| **Entry** | ${ex['entry']:,.2f} |",
        f"| **Target** | ${ex['target']:,.2f} |",
        f"| **Stop-Loss** | ${ex['stop_loss']:,.2f} |",
        f"| **Risk/Reward** | {ex['risk_reward']}:1 |",
        f"",
        f"---",
        f"",
        f"## Technical Analysis",
        f"",
        f"| Indicator | Value |",
        f"|-----------|-------|",
        f"| Current Price | ${tech['current_price']:,.2f} |",
        f"| SMA-20 | ${tech['sma_20']:,.2f} |",
        f"| SMA-50 | ${tech['sma_50']:,.2f} |",
        f"| SMA-200 | ${tech['sma_200']:,.2f} |" if tech["sma_200"] else f"| SMA-200 | N/A (insufficient data) |",
        f"| RSI-14 | {tech['rsi_14']} |",
        f"| MACD | {tech['macd']} ({'above' if tech['macd_bullish'] else 'below'} signal) |",
        f"| Bollinger Upper | ${tech['bb_upper']:,.2f} |",
        f"| Bollinger Lower | ${tech['bb_lower']:,.2f} |",
        f"| Golden Cross | {'Yes' if tech['golden_cross'] else 'No'} |",
        f"| 30-Day High | ${tech['high_30d']:,.2f} |",
        f"| 30-Day Low | ${tech['low_30d']:,.2f} |",
        f"| 30-Day Volatility | {tech['volatility_30d_pct']}% |",
        f"| Key Support | ${config['support']:,.2f} |",
        f"",
        f"---",
        f"",
        f"## Signal Reasoning (Technical)",
        f"",
    ]
    for r in signal["reasons"]:
        lines.append(f"- {r}")

    lines += [
        f"",
        f"---",
        f"",
        f"## Macro Environment ({config['macro_bias'].upper()})",
        f"",
    ]
    for r in config["macro_reasons"]:
        lines.append(f"- {r}")

    lines += [
        f"",
        f"---",
        f"",
        f"*Generated by Aegis Market Scanner | News by News Research Agent | Reasoning by Reasoning Agent*",
    ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Main scan loop
# ---------------------------------------------------------------------------

def scan_asset(name: str) -> dict:
    """Scan a single asset end-to-end. Returns the signal dict."""
    config = WATCHLIST[name]
    learner = MarketLearner()

    # Pre-task memory check — read lessons before acting
    memory_check = pre_task_check("Scanner", f"scan {name} {config['ticker']}")
    if memory_check["relevant_lessons"]:
        log("Scanner", f"Pre-task: {len(memory_check['relevant_lessons'])} relevant lessons loaded for {name}")

    log("Scanner", f"Scanning {name} ({config['ticker']})...")

    try:
        tech = analyze_asset(config["ticker"])
    except Exception as e:
        # Self-debug: check if this is a known error
        debug = self_debug(str(e), f"Scanner {name} {config['ticker']}")
        if debug["is_known_issue"]:
            log("Scanner", f"KNOWN ERROR for {name}: {debug['suggested_fix']}")
        else:
            log("Scanner", f"NEW ERROR fetching {name}: {e}")
            add_lesson(
                category="data",
                what_happened=f"Scanner failed to fetch {name} ({config['ticker']}): {e}",
                root_cause=str(type(e).__name__),
                prevention_rule=f"Check yfinance connectivity and ticker validity for {config['ticker']}.",
                related_ticket="AEGIS-011",
            )
        raise

    signal = score_signal(name, tech, config)
    log("Analyst", f"{name}: {signal['label']} (score {signal['score']}) — Price ${tech['current_price']:,.2f}")

    # News research
    news_data = None
    try:
        researcher = NewsResearcher()
        news_data = researcher.research(name, config["ticker"])
        log("NewsResearcher", f"{name}: {news_data['sentiment_label']} ({news_data['sentiment_score']:+.2f}), {news_data['relevant_count']} relevant articles")
    except Exception as e:
        log("NewsResearcher", f"WARNING: News research failed for {name}: {e}")

    # Confidence Score calculation — wrapped in try/except to prevent cascade failures
    confidence = None
    try:
        confidence = calculate_confidence(name, signal, tech, news_data, learner)
        log("Analyst", f"{name}: Confidence {confidence['confidence_pct']}% ({confidence['level']})")
    except Exception as e:
        log("Analyst", f"WARNING: Confidence calculation failed for {name}: {e} — using defaults")
        confidence = {
            "confidence_pct": 50.0,
            "level": "LOW",
            "tech_component": 50.0,
            "news_component": 50.0,
            "history_component": 50.0,
            "indicators_aligned": 0,
            "history_trades": 0,
            "history_win_rate": 0,
        }

    # Multi-Timeframe Confirmation (4h data) — adjusts confidence
    mtf_data = None
    try:
        mtf_data = analyze_multi_timeframe(config["ticker"])
        if mtf_data.get("available"):
            # Apply confidence modifier based on 4h confirmation
            is_buy = signal["label"] in ("BUY", "STRONG BUY")
            is_sell = signal["label"] in ("SELL", "STRONG SELL")

            if is_buy and mtf_data["bullish_confirms"] >= 2:
                bonus = min(10, mtf_data["bullish_confirms"] * 3)
                confidence["confidence_pct"] = round(min(100, confidence["confidence_pct"] + bonus), 1)
                log("Analyst", f"{name}: 4h confirms BUY (+{bonus}% conf) RSI4h={mtf_data['rsi_4h']}")
            elif is_buy and mtf_data["bearish_confirms"] >= 3:
                penalty = -5
                confidence["confidence_pct"] = round(max(0, confidence["confidence_pct"] + penalty), 1)
                log("Analyst", f"{name}: 4h DIVERGES from daily BUY ({penalty}% conf) RSI4h={mtf_data['rsi_4h']}")
            elif is_sell and mtf_data["bearish_confirms"] >= 2:
                bonus = min(10, mtf_data["bearish_confirms"] * 3)
                confidence["confidence_pct"] = round(min(100, confidence["confidence_pct"] + bonus), 1)
                log("Analyst", f"{name}: 4h confirms SELL (+{bonus}% conf) RSI4h={mtf_data['rsi_4h']}")
            elif is_sell and mtf_data["bullish_confirms"] >= 3:
                penalty = -5
                confidence["confidence_pct"] = round(max(0, confidence["confidence_pct"] + penalty), 1)
                log("Analyst", f"{name}: 4h DIVERGES from daily SELL ({penalty}% conf) RSI4h={mtf_data['rsi_4h']}")
            else:
                log("Analyst", f"{name}: 4h data neutral — no confidence adjustment. RSI4h={mtf_data['rsi_4h']}")

            # Update level label after adjustment
            c = confidence["confidence_pct"]
            confidence["level"] = "HIGH" if c >= 80 else ("MEDIUM" if c >= 60 else ("LOW" if c >= 40 else "VERY LOW"))
            confidence["mtf_data"] = mtf_data
        else:
            log("Analyst", f"{name}: 4h data unavailable — {mtf_data.get('reason', 'unknown')}")
    except Exception as e:
        log("Analyst", f"WARNING: Multi-timeframe analysis failed for {name}: {e}")

    # Mini-Backtest (30-day simulation)
    backtest = None
    if confidence["confidence_pct"] >= 40:  # Only backtest if there's some signal
        try:
            backtest = backtest_strategy(config["ticker"], config)
            if backtest.get("success") and backtest.get("total_signals", 0) > 0:
                log("Analyst", f"{name}: Backtest — {backtest['summary']}")
            elif not backtest.get("success"):
                log("Analyst", f"{name}: Backtest skipped — {backtest.get('reason', 'unknown reason')}")
        except Exception as e:
            log("Analyst", f"WARNING: Backtest failed for {name}: {e} — continuing without backtest")
    else:
        log("Analyst", f"{name}: Backtest skipped — confidence {confidence['confidence_pct']}% below 40% threshold")

    # Auto-Adaptive Report Depth
    if confidence["confidence_pct"] >= 80:
        report_mode = "deep_dive"
    elif confidence["confidence_pct"] >= 50:
        report_mode = "standard"
    else:
        report_mode = "brief"
    log("Manager", f"{name}: Report mode = {report_mode} (confidence {confidence['confidence_pct']}%)")

    # Chart generation (skip for brief mode to save cost)
    if report_mode != "brief":
        try:
            chart_gen = ChartGenerator()
            figures = chart_gen.generate_all(
                ticker=config["ticker"],
                asset_name=name,
                config=config,
                signal=signal,
                news_data=news_data,
            )
            chart_data_dir = PROJECT_ROOT / "src" / "data" / "charts"
            chart_data_dir.mkdir(parents=True, exist_ok=True)
            for chart_name, fig in figures.items():
                fig.write_json(str(chart_data_dir / f"{name.lower()}_{chart_name}.json"))
            log("ChartGenerator", f"{name}: {len(figures)} charts generated and saved")
        except Exception as e:
            log("ChartGenerator", f"WARNING: Chart generation failed for {name}: {e}")
    else:
        log("ChartGenerator", f"{name}: Chart generation skipped — report mode is 'brief'")

    # Write research report (depth varies by confidence)
    report_path = write_report(
        name, config, tech, signal,
        news=news_data,
        confidence=confidence,
        backtest=backtest,
    )
    log("Researcher", f"Report written: {report_path.name} ({report_mode})")

    # Record prediction in market learner
    news_sentiment = news_data.get("sentiment_label") if news_data else None
    try:
        learner.record_prediction(name, config["ticker"], signal, tech, news_sentiment)
    except Exception as e:
        log("MarketLearner", f"WARNING: Failed to record prediction for {name}: {e}")

    # Create kanban trade alert if signal is BUY or STRONG BUY
    if signal["score"] >= 35:
        ticket_id = create_trade_alert(name, signal, tech)
        if ticket_id:
            log("Manager", f"TRADE ALERT created: {ticket_id} — Buy {name}")
        else:
            log("Manager", f"Trade alert for {name} already exists, skipping.")

    # Backtest rate: None if not run, None if 0 signals (no data), otherwise the %
    bt_rate = None
    bt_signals = 0
    if backtest and backtest.get("success"):
        bt_signals = backtest.get("total_signals", 0)
        bt_rate = backtest["success_rate"] if bt_signals > 0 else None

    # Save scan summary for dashboard watchlist consumption
    # Extract news impact from confidence dict (computed during calculate_confidence)
    news_impact = confidence.get("news_impact") if confidence else None

    ex = signal["execution"]
    scan_summary = {
        "name": name,
        "ticker": config["ticker"],
        "price": tech["current_price"],
        "signal_label": signal["label"],
        "signal_score": signal["score"],
        "confidence": confidence,
        "backtest_rate": bt_rate,
        "backtest_signals": bt_signals,
        "news_sentiment": news_data.get("sentiment_label") if news_data else None,
        "news_score": news_data.get("sentiment_score", 0) if news_data else 0,
        "news_impact": news_impact,
        "rsi": tech["rsi_14"],
        "report_mode": report_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reasoning_short": _short_reasoning(signal, tech, config, confidence),
        "target": ex["target"],
        "stop_loss": ex["stop_loss"],
        "entry": ex["entry"],
        "risk_reward": ex["risk_reward"],
    }

    # Append to watchlist summary file
    summary_file = PROJECT_ROOT / "src" / "data" / "watchlist_summary.json"
    summaries = {}
    if summary_file.exists():
        try:
            summaries = json.loads(summary_file.read_text(encoding="utf-8"))
        except Exception:
            summaries = {}
    summaries[name] = scan_summary
    summary_file.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"name": name, "signal": signal, "tech": tech, "news": news_data, "confidence": confidence, "backtest": backtest}


def _short_reasoning(signal: dict, tech: dict, config: dict, confidence: dict) -> str:
    """Generate a one-line reasoning for the signal card."""
    label = signal["label"]
    price = tech["current_price"]
    rsi = tech["rsi_14"]

    if label in ("BUY", "STRONG BUY"):
        if tech["golden_cross"]:
            reason = "Golden Cross aktiv + Aufwaertstrend"
        elif config["macro_bias"] == "bullish":
            reason = f"Bullish wegen Makro-Umfeld"
        elif rsi < 40:
            reason = f"RSI {rsi} — ueberverkauft, Erholung erwartet"
        else:
            reason = "Mehrere technische Indikatoren positiv"
    elif label in ("SELL", "STRONG SELL"):
        if rsi > 70:
            reason = f"RSI {rsi} — ueberkauft, Korrektur wahrscheinlich"
        else:
            reason = "Technische Schwaeche, Abwaertsdruck"
    else:
        reason = "Gemischte Signale — abwarten empfohlen"

    return f"{reason} (Conf: {confidence['confidence_pct']}%)"


def _scan_asset_safe(name: str) -> dict | None:
    """Wrapper for scan_asset that catches exceptions (for parallel execution)."""
    try:
        return scan_asset(name)
    except Exception as e:
        log("Manager", f"SKIPPED {name}: scan failed with {type(e).__name__}: {e}")
        return None


def scan_all(progress_callback=None) -> list[dict]:
    """Scan all assets in the watchlist sequentially for data accuracy.

    Uses sequential scanning with the global yfinance lock to guarantee
    every asset gets its own correct price. News research is the only
    part that can happen in the scan pipeline — yfinance calls are serialized.

    Args:
        progress_callback: Optional callable(asset_name, index, total, success).
            Called after each asset completes.
    """
    log("Manager", "=== Starting proactive market scan ===")
    results = []
    total = len(WATCHLIST)
    completed_count = 0

    for name in WATCHLIST:
        result = _scan_asset_safe(name)
        completed_count += 1
        success = result is not None
        if success:
            results.append(result)
        if progress_callback is not None:
            try:
                progress_callback(name, completed_count, total, success)
            except Exception:
                pass  # Never let callback errors break the scan

    log("Manager", f"=== Scan complete: {len(results)}/{total} assets processed ===")
    return results


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*80}")
    print(f"  MARKET SCANNER SUMMARY")
    print(f"{'='*80}")
    print(f"  {'Asset':<10} {'Price':>12} {'Signal':<14} {'Score':>6} {'Entry':>12} {'Target':>12} {'Stop':>12} {'R:R':>6}")
    print(f"  {'-'*74}")
    for r in results:
        s = r["signal"]
        ex = s["execution"]
        print(
            f"  {r['name']:<10} ${r['tech']['current_price']:>10,.2f} "
            f"{s['label']:<14} {s['score']:>5} "
            f"${ex['entry']:>10,.2f} ${ex['target']:>10,.2f} "
            f"${ex['stop_loss']:>10,.2f} {ex['risk_reward']:>4.1f}:1"
        )
    print(f"{'='*80}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proactive Market Scanner")
    parser.add_argument("--asset", default=None, help="Scan a single asset (Gold, BTC, ETH, Silver)")
    args = parser.parse_args()

    if args.asset:
        if args.asset not in WATCHLIST:
            print(f"Unknown asset '{args.asset}'. Available: {', '.join(WATCHLIST.keys())}")
            sys.exit(1)
        results = [scan_asset(args.asset)]
    else:
        results = scan_all()

    print_summary(results)
