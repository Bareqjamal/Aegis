# QA Signal & Data Accuracy Audit Report

**Auditor:** Signal & Data Accuracy QA Agent
**Date:** 2026-02-27
**Scope:** market_scanner.py, news_researcher.py, social_sentiment.py, market_learner.py, config.py, prediction_game.py, morning_brief.py
**Methodology:** Full code review of every function in each file, tracing data flows between modules

---

## Executive Summary

This audit uncovered **7 P0 Critical bugs**, **9 P1 High issues**, **11 P2 Medium issues**, and **6 P3 Low issues** across the signal generation pipeline. The most dangerous findings are:

1. **Adaptive confidence weights are silently ignored** due to a key name mismatch between market_learner and market_scanner, causing all assets to use hardcoded default weights.
2. **Morning Brief displays wrong signals for EVERY asset** due to field name mismatches when reading watchlist_summary.json.
3. **Prediction Game outcome validation is completely non-functional** because it reads field names that don't exist in the predictions data.
4. **Morning Brief will crash on any error path** because it calls a `log()` function that was never defined or imported.

People may trade real money based on these signals. Every P0 item can directly produce wrong information shown to users.

---

## P0 CRITICAL Findings

### P0-01: Adaptive Confidence Weights Silently Ignored (Key Name Mismatch)

**File:** `src/market_scanner.py` line 549-553, `src/market_learner.py` line 601-604
**Impact:** Confidence scores for all assets use hardcoded defaults instead of learned adaptive weights.

`market_learner.get_adaptive_weights()` returns:
```python
{"tech": 0.45, "news": 0.15, "history": 0.40, "reliability": {...}}
```

But `calculate_confidence()` in market_scanner reads:
```python
w_tech = weights.get("technical", 0.40)   # KEY IS "tech" NOT "technical"
w_news = weights.get("news", 0.20)        # This one matches
w_hist = weights.get("historical", 0.40)  # KEY IS "history" NOT "historical"
```

**Result:** `w_tech` and `w_hist` ALWAYS fall back to their defaults (0.40 each) because the keys `"technical"` and `"historical"` don't exist in the returned dict. The entire adaptive learning system for confidence weights is dead code. Users are told the system "learns and adapts" but it never actually does.

**Fix:**
```python
# In market_scanner.py calculate_confidence():
w_tech = weights.get("tech", 0.40)
w_news = weights.get("news", 0.20)
w_hist = weights.get("history", 0.40)
```

---

### P0-02: Morning Brief Displays Wrong Signal for Every Asset

**File:** `src/morning_brief.py` line 43, `src/market_scanner.py` line 1229
**Impact:** Morning Brief shows "NEUTRAL" for every asset regardless of actual signal.

The scanner writes `watchlist_summary.json` with the key `"signal_label"`:
```python
scan_summary = {
    "signal_label": signal["label"],  # e.g. "BUY", "STRONG SELL"
    ...
}
```

But `_get_watchlist_signals()` in morning_brief reads:
```python
"signal": info.get("signal", "NEUTRAL"),  # WRONG KEY: should be "signal_label"
```

Since `"signal"` doesn't exist in the JSON, every asset defaults to `"NEUTRAL"`. This means:
- The market tone is always "Mixed/Neutral"
- No asset ever shows "BUY NOW" or "AVOID" verdicts
- The key takeaway always says "No strong conviction trades"

Users see a perpetually neutral morning brief regardless of actual market conditions.

**Fix:**
```python
"signal": info.get("signal_label", "NEUTRAL"),
```

---

### P0-03: Morning Brief Shows 0% Confidence for Every Asset

**File:** `src/morning_brief.py` line 44, `src/market_scanner.py` line 1231
**Impact:** Confidence always reads as 0 because the field is a nested dict, not a number.

The scanner writes:
```python
"confidence": confidence,  # This is an ENTIRE DICT: {"confidence_pct": 73.2, "level": "MEDIUM", ...}
```

But morning_brief reads:
```python
"confidence": info.get("confidence_pct", 0),  # WRONG: "confidence_pct" is not a top-level key
```

The confidence value is nested at `info["confidence"]["confidence_pct"]`, but the brief looks for `info["confidence_pct"]` at the top level, which doesn't exist. Every asset shows 0% confidence.

Combined with P0-02, this means the Morning Brief is essentially displaying fabricated data for every single field.

**Fix:**
```python
conf_data = info.get("confidence", {})
confidence_pct = conf_data.get("confidence_pct", 0) if isinstance(conf_data, dict) else 0
```

---

### P0-04: Morning Brief Crashes on Any Warning/Error Path (Undefined `log`)

**File:** `src/morning_brief.py` lines 31, 75, 339
**Impact:** Any JSON parse error or calendar load failure crashes the entire morning brief with `NameError: name 'log' is not defined`.

The file calls `log()` in three exception handlers but never defines or imports it:
```python
# Line 31 - inside _load_json:
log(f"WARNING: Failed to load JSON {path.name}: {e}")

# Line 75 - inside _get_calendar_events:
log(f"WARNING: Calendar events load failed: {e}")

# Line 339 - inside load_cached:
log(f"WARNING: Failed to load cached brief: {e}")
```

There is no `import` for `log` and no `def log(...)` anywhere in the file. When any of these error paths triggers, the resulting `NameError` will either crash the morning brief generation or crash the dashboard page rendering it.

**Fix:** Add at the top of the file:
```python
def log(message: str) -> None:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [MorningBrief] {message}")
```

---

### P0-05: Prediction Game Outcome Validation Is Completely Non-Functional

**File:** `src/prediction_game.py` lines 133-143
**Impact:** User votes are NEVER validated against actual outcomes. The scorecard always shows 0 correct, 0 wrong.

`_check_outcome()` searches predictions for matching entries using:
```python
pred_date = pred.get("date", "")[:10]        # WRONG: field is "timestamp", not "date"
validated = pred.get("validated", False)       # OK
correct = pred.get("correct", False)           # WRONG: field is "outcome", not "correct"
actual_move = pred.get("actual_move_pct", 0)   # WRONG: field doesn't exist
```

But `market_learner.record_prediction()` creates predictions with:
```python
{
    "timestamp": "2026-02-27T10:30:00+00:00",  # Not "date"
    "validated": True/False,
    "outcome": "correct"/"incorrect"/"neutral",  # Not boolean "correct"
    "outcome_price": 2850.50,                    # Not "actual_move_pct"
}
```

Three field name mismatches mean:
1. `pred_date` is always `""` -- no prediction ever matches a vote date
2. Even if dates matched, `correct` is always `False` (field doesn't exist)
3. `actual_move_pct` is always 0 (field doesn't exist)

The prediction game scorecards, streaks, and the "regret engine" (`get_signals_you_ignored`) are all non-functional.

**Fix:** Rewrite `_check_outcome()` to use the correct field names and data structure:
```python
pred_date = pred.get("timestamp", "")[:10]
if pred_asset == asset and pred_date == vote_date and validated:
    outcome = pred.get("outcome", "")
    signal_correct = outcome == "correct"
    # Calculate actual_move_pct from entry_price and outcome_price
    entry = pred.get("entry_price", 0)
    outcome_price = pred.get("outcome_price", 0)
    actual_move = ((outcome_price - entry) / entry * 100) if entry else 0
```

---

### P0-06: Morning Brief Never Loads Predictions (Data Structure Mismatch)

**File:** `src/morning_brief.py` lines 61-66
**Impact:** The `_get_predictions()` method always returns an empty list.

```python
def _get_predictions(self) -> list[dict]:
    data = self._load_json(MEMORY_DIR / "market_predictions.json")
    if not data or not isinstance(data, list):  # data is a DICT, not a list!
        return []
    return data[-10:]
```

`market_predictions.json` has the structure `{"predictions": [...], "stats": {...}}`. It's a dict, not a list. The `isinstance(data, list)` check always fails, so predictions are never loaded.

**Fix:**
```python
def _get_predictions(self) -> list[dict]:
    data = self._load_json(MEMORY_DIR / "market_predictions.json")
    if not data:
        return []
    if isinstance(data, dict):
        return data.get("predictions", [])[-10:]
    if isinstance(data, list):
        return data[-10:]
    return []
```

---

### P0-07: Confidence Score Formula Can Produce Misleadingly High Values for Weak Signals

**File:** `src/market_scanner.py` lines 556-577
**Impact:** A signal with score +10 (barely above NEUTRAL threshold) can receive confidence of 70%+ due to the formula design.

The technical confidence calculation:
```python
if signal["label"] in ("BUY", "STRONG BUY"):
    tech_conf = max(0, min(100, (raw_score + 10) * 1.1))  # score 10 -> (20)*1.1 = 22
```

A score of 35 (minimum for "BUY" label) produces: `(35+10)*1.1 = 49.5`. Then with alignment bonus (up to +20), tech_conf can reach 69.5. If history_conf is 50 (default) and news_conf is 50 (default), the weighted average is `69.5*0.4 + 50*0.2 + 50*0.4 = 27.8 + 10 + 20 = 57.8%`. With social boost (+10) and MTF bonus (+10), this reaches **77.8%** -- labeled "HIGH" confidence for a barely-qualifying BUY signal.

A STRONG BUY at score 60: `(60+10)*1.1 = 77` + alignment bonus 20 = 97 tech_conf. With defaults: `97*0.4 + 50*0.2 + 50*0.4 = 38.8 + 10 + 20 = 68.8%`. Add social+MTF = **88.8%** HIGH confidence. The floor is too high for the formula.

The problem: the `(raw_score + 10) * 1.1` shift inflates every BUY signal's technical component by a fixed +11 points, and the alignment bonus stacks independently of signal strength.

**Fix:** Remove the artificial +10 shift and scale alignment bonus proportionally to signal strength:
```python
tech_conf = max(0, min(100, raw_score * 1.0))
alignment_bonus = aligned * 3  # Reduced from 5 to 3
```

---

## P1 HIGH Findings

### P1-01: Settings Override Weights Not Validated (Sum Can Exceed 1.0)

**File:** `src/config.py` lines 317-322
**Impact:** A user can set confidence weights to any value via the Settings page. No validation ensures they sum to 1.0.

If a user sets `confidence_weight_technical=0.9, confidence_weight_news=0.9, confidence_weight_historical=0.9`, the weights sum to 2.7. The `calculate_confidence` function would produce confidence values up to 270%, which gets clamped to 100% -- meaning every signal appears "HIGH confidence."

Conversely, weights of 0.1 each (sum=0.3) would produce artificially low confidence scores.

**Fix:** Normalize weights after loading:
```python
total = tech_w + news_w + hist_w
if total > 0:
    tech_w, news_w, hist_w = tech_w/total, news_w/total, hist_w/total
```

---

### P1-02: RSI Can Produce NaN in Flat Markets (Division by Zero)

**File:** `src/market_scanner.py` lines 196-199
**Impact:** If a ticker has zero price movement over any 14-day period, both gain and loss rolling averages are 0, producing `rs = 0/0 = NaN`, which propagates `NaN` through the entire signal scoring pipeline.

```python
rs = gain / loss  # No guard against loss == 0 or both == 0
rsi = (100 - (100 / (1 + rs))).iloc[-1]  # NaN if rs is NaN
```

With NaN RSI, the score_signal function would still run but produce incorrect results: all RSI-based score adjustments would be skipped (NaN comparisons are False), and the RSI value stored would be NaN.

This same pattern appears at lines 295 and 687.

**Fix:**
```python
rs = gain / loss.replace(0, np.nan)
rsi_series = 100 - (100 / (1 + rs))
rsi_series = rsi_series.fillna(50)  # Default to neutral RSI if uncalculable
```

---

### P1-03: Social Sentiment Scoring Lacks Word Boundary Checks

**File:** `src/social_sentiment.py` lines 218-236
**Impact:** The `_score_social_text()` function uses simple substring matching (`word in text_lower`) instead of word boundary matching. This creates false positives.

Examples of false matches:
- "up" matches in "s**up**ply chain", "**up**date", "s**up**port"
- "red" matches in "favo**red**", "featu**red**", "cove**red**"
- "hold" matches in "wit**hhold**ing", "s**hold**er"
- "long" matches in "a**long**", "be**long**s"
- "bull" matches in "**bull**et", "**bull**ying"
- "gain" matches in "a**gain**st", "bar**gain**"
- "calls" matches in "re**calls**"
- "green" matches in "**green**house", "ever**green**"
- "dead" matches in "**dead**line"

Compare to `news_researcher.py` which correctly uses `_keyword_match()` with `re.search(r'\b' + re.escape(keyword) + r'\b', ...)`.

**Fix:** Add word boundary matching like the news researcher:
```python
def _score_social_text(text: str) -> float:
    text_lower = text.lower()
    bull_score = 0.0
    bear_score = 0.0
    for word, weight in SOCIAL_BULLISH:
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            bull_score += weight
    # ... same for SOCIAL_BEARISH
```

---

### P1-04: Market Learner Prediction ID Collision Under High Throughput

**File:** `src/market_learner.py` line 137
**Impact:** Prediction IDs are generated using seconds-precision timestamps:

```python
"id": f"PRED-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{asset}"
```

If the parallel scanner (4 threads) processes two different assets within the same second, they'll have unique IDs due to the asset suffix. But if the same asset is scanned twice within one second (e.g., retry logic), the IDs will collide.

More importantly, the market_learner deduplication for lessons uses prediction_id references, so collisions could link lessons to wrong predictions.

**Fix:** Add milliseconds or a UUID:
```python
import uuid
"id": f"PRED-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{asset}-{uuid.uuid4().hex[:6]}"
```

---

### P1-05: Sell Signal Validation Ignores Target/Stop-Loss for 48 Hours

**File:** `src/market_learner.py` lines 266-279
**Impact:** For SELL signals, the code ONLY checks time-based validation after 48 hours. Unlike BUY signals which check target and stop-loss hit at every validation cycle, SELL signals always wait the full 48 hours.

```python
elif label in ("SELL", "STRONG SELL"):
    pct_change = (current_price - entry) / entry * 100
    if age_hours >= ValidationConfig.MAX_VALIDATION_HOURS:  # Only checks at 48h
        if pct_change < ValidationConfig.SELL_SUCCESS_PCT:
            result["outcome"] = "correct"
        ...
    else:
        return None  # No early validation for sells!
```

But for BUY signals:
```python
if label in ("BUY", "STRONG BUY"):
    if current_price >= target:        # Checked at every cycle
        result["outcome"] = "correct"
    elif current_price <= stop:         # Checked at every cycle
        result["outcome"] = "incorrect"
    elif age_hours >= MAX:              # Fallback at 48h
```

This means a SELL signal where price rallies 20% within the first hour won't be marked as incorrect until 48 hours later. The win rate statistics will be delayed and inaccurate for sell signals.

**Fix:** Add target/stop-loss checks for SELL signals:
```python
elif label in ("SELL", "STRONG SELL"):
    if current_price <= stop:  # For sells, stop is the target (price dropped to target)
        result["outcome"] = "correct"
    elif current_price >= target:  # For sells, price going up is bad
        result["outcome"] = "incorrect"
    elif age_hours >= ValidationConfig.MAX_VALIDATION_HOURS:
        ...
```

---

### P1-06: Watchlist Summary File Writes Are Not Atomic

**File:** `src/market_scanner.py` lines 1247-1255
**Impact:** The scan_all function uses parallel threads (4 workers), and each thread writes to the same `watchlist_summary.json` file. The write pattern is:

```python
# Thread 1 reads, modifies, writes
summaries = json.loads(summary_file.read_text())
summaries[name] = scan_summary
summary_file.write_text(json.dumps(summaries))

# Thread 2 reads, modifies, writes (possibly between Thread 1's read and write)
```

This is a classic TOCTOU race condition. Two threads reading simultaneously will each get the old state, then each overwrite the file -- the last writer wins and the first writer's data is lost. With 4 parallel workers, up to 3 assets could be silently dropped from the summary.

Note: `_save_predictions()` and `_save_lessons()` in market_learner.py correctly use atomic writes (tempfile + rename), but the scanner does not.

**Fix:** Use a thread lock or atomic write pattern:
```python
import threading
_summary_lock = threading.Lock()

# In scan_asset:
with _summary_lock:
    summaries = json.loads(summary_file.read_text())
    summaries[name] = scan_summary
    summary_file.write_text(json.dumps(summaries))
```

---

### P1-07: Score-to-Label Mapping Has Asymmetric Ranges

**File:** `src/market_scanner.py` lines 443-452
**Impact:** The signal label thresholds are not symmetric, creating a bullish bias:

| Range | Label |
|-------|-------|
| 60 to 100 | STRONG BUY |
| 35 to 59 | BUY |
| -10 to 34 | NEUTRAL |
| -35 to -11 | SELL |
| -100 to -36 | STRONG SELL |

The NEUTRAL zone spans 45 points (-10 to +34) but is heavily shifted to the positive side. A score of +30 is "NEUTRAL" but a score of -30 is "SELL". The BUY zone is 25 points wide (35-59) but the SELL zone is also 25 points (-11 to -35). The STRONG BUY zone is 41 points (60-100) but STRONG SELL is 65 points (-36 to -100).

This means the system is structurally biased toward emitting fewer BUY signals than SELL signals, but the NEUTRAL zone captures many moderately positive signals that would be actionable.

**Recommendation:** Make thresholds symmetric or document the intentional bias:
```python
if score >= 60: "STRONG BUY"
elif score >= 30: "BUY"
elif score >= -30: "NEUTRAL"
elif score >= -60: "SELL"
else: "STRONG SELL"
```

---

### P1-08: No Staleness Check on Cached Data

**File:** `src/morning_brief.py`, `src/market_scanner.py` (social cache), `src/news_researcher.py` (social overlay)
**Impact:** The morning brief, market scanner, and news researcher all read cached JSON files (social_sentiment.json, macro_regime.json, geopolitical_analysis.json, watchlist_summary.json) without checking how old the data is. A morning brief generated today could display social sentiment data from a week ago with no staleness indicator.

The social cache at `src/data/social_sentiment.json` includes a `"timestamp"` field, but none of the consumers check it. If the social scan hasn't run in days, the confidence boost calculations in market_scanner.py and the blended sentiment in news_researcher.py will use arbitrarily old data.

**Fix:** Add staleness checks:
```python
cache_ts = datetime.fromisoformat(data.get("timestamp", "2020-01-01"))
age_hours = (datetime.now(timezone.utc) - cache_ts).total_seconds() / 3600
if age_hours > 24:
    log(f"WARNING: Social data is {age_hours:.0f}h old, treating as unavailable")
    return None
```

---

### P1-09: Backtest Strategy Uses Oversimplified Criteria

**File:** `src/market_scanner.py` lines 698-727
**Impact:** The backtest function uses a stripped-down signal logic (golden cross + RSI < 60 + MACD) that differs from the actual `score_signal()` function which uses 8 factors. This means the backtest success rate doesn't reflect the actual strategy's performance.

The backtest omits: support proximity, Bollinger Bands, macro bias, volume confirmation, and risk/reward checks. A backtest might show 80% success rate when the actual strategy (which includes macro bias at +15 or volume at +10) would have different entry/exit points.

Users see "Strategy backtested: 80% success rate" and think that reflects the signal they're about to act on. It doesn't.

**Fix:** Either use the actual `score_signal()` function in the backtest loop (generating a synthetic config for each historical point), or clearly label the backtest as "simplified technical-only backtest" in the UI.

---

## P2 MEDIUM Findings

### P2-01: News Relevance Filter Too Loose for Generic Assets

**File:** `src/news_researcher.py` lines 170-183
**Impact:** The keyword "support" is in the BULLISH_WORDS list and also in the Gold ASSET_KEYWORDS ("safe haven"). The word "euro" matches EUR_USD but also appears in thousands of non-forex European news articles. "stock market" matches SP500 but captures articles about any stock market globally.

"green" (1.0 bullish) will match "green energy", "greenhouse gas", etc.
"growth" (1.0 bullish) matches any article about GDP, population, or business growth.

These generic keywords inflate article counts and dilute sentiment accuracy for specific assets.

---

### P2-02: Negation Detection Only Checks Before the Keyword

**File:** `src/news_researcher.py` lines 116-127
**Impact:** `_has_negation_before()` only checks for negation words in the 30 characters BEFORE a keyword. Post-keyword negation is missed:

- "Gold rally not expected" -- "rally" is detected as bullish, but "not" comes after it (missed)
- "Markets surge, then not" -- "surge" counted as bullish (the negation is after, not before)

However: "not rally" and "no surge" are correctly caught. The fix priority is medium because pre-keyword negation is the most common English pattern.

---

### P2-03: Social Sentiment `_score_social_text` Uses Same Normalization as News

**File:** `src/social_sentiment.py` lines 218-236
**Impact:** The formula `raw = (bull_score - bear_score) / total` normalizes by the sum of both scores. This means a post with one strong bullish keyword (3.0) and one strong bearish keyword (3.0) gets score 0.0 (neutral), which is reasonable. But a post with 10 mild bullish keywords (total 10.0) and one strong bearish (3.0) gets `(10-3)/13 = 0.54`, which is "VERY_BULLISH" -- even though a crash keyword should carry more weight than 10 mild bullish mentions.

---

### P2-04: NatGas Asset Name Inconsistency

**File:** `src/social_sentiment.py` line 191
**Impact:** The ASSET_MENTION_PATTERNS dict uses key `"Natural Gas"` but the watchlist uses `"NatGas"`. This means Reddit/influencer social sentiment for Natural Gas will never be computed or matched.

```python
# social_sentiment.py
ASSET_MENTION_PATTERNS = {
    "Natural Gas": [r"\bnatural\s*gas\b", r"\blng\b"],  # Key is "Natural Gas"
}

# market_scanner.py watchlist
"NatGas": {"ticker": "NG=F", ...}  # Key is "NatGas"
```

---

### P2-05: Confidence Report Table Shows Hardcoded Weight Percentages

**File:** `src/market_scanner.py` lines 954-958
**Impact:** The research report always displays "40% | 20% | 40%" for component weights, even when adaptive weights have changed them:

```python
f"| Technical Analysis | {confidence['tech_component']}% | 40% |",
f"| News Alignment | {confidence['news_component']}% | 20% |",
f"| Historical Win-Rate | {confidence['history_component']}% | 40% |",
```

This is cosmetically misleading if adaptive weights are ever fixed (see P0-01). The weights dict is available in `confidence['weights']` but not used in the report template.

---

### P2-06: Market Learner `validate_all` Has Potential f-string Syntax Error

**File:** `src/market_learner.py` lines 211-213
**Impact:** The log statement has a conditional expression that may not produce the intended output:

```python
log(f"Validated {len(validated)} predictions. "
    f"Win rate: {len(correct)}/{len(all_validated)} "
    f"({len(correct)/len(all_validated)*100:.0f}%)" if all_validated else "")
```

The `if all_validated else ""` applies to the entire f-string expression, not just the division. If `all_validated` is empty and `validated` is non-empty (shouldn't happen but defensive coding), the log call becomes `log("")` which is a no-op. More concerning: this ternary means if there ARE validated predictions but the list is truthy, it works, but the intent seems to be guarding against ZeroDivisionError -- the guard should be inside the format string.

---

### P2-07: Backtest Forward-Looking Bias

**File:** `src/market_scanner.py` lines 682-683
**Impact:** The backtest computes SMA-200 using the FULL dataset including future data:

```python
sma_200 = close.rolling(200).mean() if sma_200_available else None
# Then for each day in test_range:
sma_200_val = float(sma_200.iloc[pos])  # This uses rolling mean up to `pos`
```

The rolling(200).mean() correctly only looks at the 200 points before `pos`, so there's no actual look-ahead in the SMA. However, the data download itself uses `period="3mo"` which may be less than 200 trading days, meaning the SMA-200 at the start of the test range will be NaN. This is handled by the `sma_200_available` check, but the check uses `len(close) < 200` while the rolling window needs 200 *non-NaN* values.

---

### P2-08: Influencer Impact Score Unbounded Before Clamping

**File:** `src/social_sentiment.py` lines 372-383
**Impact:** The influencer impact formula can accumulate unbounded keyword hits:

```python
impact = avg_sent * base_weight * article_factor  # Can be up to 1.0 * 3.0 * 2.0 = 6.0
if bull_kw_hits > 0:
    impact += 0.2 * bull_kw_hits * base_weight    # 10 hits * 0.2 * 3.0 = +6.0
if bear_kw_hits > 0:
    impact -= 0.2 * bear_kw_hits * base_weight    # 10 hits * 0.2 * 3.0 = -6.0
asset_impacts[asset] = round(max(-5.0, min(5.0, impact)), 2)
```

The clamping at [-5, 5] catches extreme values, but the keyword hits are not capped. A single influencer with many articles mentioning many keywords can dominate the score.

---

### P2-09: `daily_change_pct` Never Written to Watchlist Summary

**File:** `src/morning_brief.py` line 47, `src/market_scanner.py` lines 1225-1243
**Impact:** Morning brief reads `info.get("daily_change_pct", 0)` but market_scanner never writes this field to the summary. All assets show 0% daily change in the brief. This is a lesser version of P0-02/P0-03 -- the brief's data model doesn't match the scanner's output.

---

### P2-10: Prediction Game `get_signals_you_ignored` Uses Wrong Field Names

**File:** `src/prediction_game.py` lines 440-463
**Impact:** Same field mismatch as P0-05. The "regret engine" searches for `pred.get("date")` (doesn't exist, field is `"timestamp"`), `pred.get("correct")` (doesn't exist, field is `"outcome"`), and `pred.get("signal")` (doesn't exist, field is `"signal_label"`). This feature never produces results.

---

### P2-11: Social Sentiment ETH Pattern Matches Non-Crypto Content

**File:** `src/social_sentiment.py` line 181
**Impact:** The regex pattern `r"\beth\b"` for Ethereum will match the common English word "eth" which appears in names like "Seth", "Beth", etc. However, the `\b` boundary helps somewhat. More critically, `r"\bdefi\b"` will match non-crypto "defi" words like "definitely" (though `\b` prevents this specific case). The pattern `r"\bether\b"` could match chemistry/science discussions about diethyl ether.

---

## P3 LOW Findings

### P3-01: Emoji Characters in Social Scoring

**File:** `src/social_sentiment.py` line 202
**Impact:** The rocket emoji ("rocket", 3.0) in SOCIAL_BULLISH is the string "rocket", not the actual emoji character. This will match the word "rocket" in text but not the actual emoji character that Reddit users commonly use. Separately, the entry for the emoji character itself is present but may not reliably match across different Unicode normalizations.

---

### P3-02: Chart Generator Import May Fail Silently

**File:** `src/market_scanner.py` line 32
**Impact:** `from chart_generator import ChartGenerator` is imported at module level. If chart_generator.py has an import error (e.g., missing plotly), it will crash the entire market scanner even though chart generation is an optional enhancement.

---

### P3-03: MarketLearner Lesson ID Is Sequential, Not Unique

**File:** `src/market_learner.py` line 335
**Impact:** Lesson IDs are `f"MKTL-{len(lessons_data['lessons']) + 1:03d}"`. If lessons are ever deleted or the file is reset, IDs will be reused, creating ambiguous references in prediction records.

---

### P3-04: RSS Feed Redundancy

**File:** `src/news_researcher.py` lines 198-199
**Impact:** "CNBC Markets" and "CNBC Economy" use the same URL (`id=20910258`). This fetches the same feed twice, doubling processing time for identical content. The dedup by title handles the articles, but network bandwidth and latency are wasted.

---

### P3-05: Hardcoded Technical Parameters Not Respected

**File:** `src/market_scanner.py` lines 190-213
**Impact:** The `analyze_asset()` function hardcodes SMA periods (20, 50, 200), RSI period (14), MACD periods (12, 26, 9), and BB period (20) instead of reading from `TechnicalParams`. The Settings page allows changing `sma_short`, `rsi_period`, etc. via `config.py`, but the scanner ignores these settings.

```python
# Hardcoded values in analyze_asset():
sma_20 = close.rolling(20).mean()
sma_50 = close.rolling(50).mean()           # Should be TechnicalParams.SMA_SHORT
sma_200 = close.rolling(200).mean()         # Should be TechnicalParams.SMA_LONG
gain = delta.clip(lower=0).rolling(14).mean()  # Should be TechnicalParams.RSI_PERIOD
```

The `TechnicalParams` class is imported but never used in the actual calculations.

---

### P3-06: `volume_ratio` Can Be Misleading for Crypto/Forex

**File:** `src/market_scanner.py` lines 222-231, 428-437
**Impact:** Crypto trades 24/7 and forex trades across sessions. Volume patterns differ fundamentally from equities. A "low volume" reading on a Sunday for BTC doesn't mean the same thing as low volume on a Tuesday for S&P 500. The volume ratio scoring applies the same thresholds (1.5x = strong, 0.5x = weak) to all asset classes without adjustment.

---

## Cross-Module Data Flow Issues

### Data Contract Violations Summary

| Producer | Consumer | Field Expected | Field Actual | Impact |
|----------|----------|---------------|--------------|--------|
| market_scanner | morning_brief | `signal` | `signal_label` | Wrong signal displayed |
| market_scanner | morning_brief | `confidence_pct` (top-level) | `confidence` (dict) | 0% confidence shown |
| market_scanner | morning_brief | `daily_change_pct` | (not written) | 0% change shown |
| market_learner (adaptive weights) | market_scanner | `technical`, `historical` | `tech`, `history` | Adaptive weights ignored |
| market_learner (predictions) | prediction_game | `date`, `correct`, `actual_move_pct` | `timestamp`, `outcome`, `outcome_price` | Validation broken |
| social_sentiment (asset keys) | market_scanner | `NatGas` | `Natural Gas` | NatGas social score missing |

---

## Recommendations (Priority Order)

1. **Establish a shared data contract** -- create a `src/schemas.py` with TypedDict or dataclass definitions for `WatchlistSummary`, `Prediction`, `SocialScore`, etc. All producers and consumers should use the same types.

2. **Fix all P0 field name mismatches immediately** -- these are one-line fixes that will make the morning brief, prediction game, and adaptive weights functional.

3. **Add integration tests** -- test that market_scanner's output can be correctly read by morning_brief, prediction_game, and the dashboard. These are simple JSON round-trip tests.

4. **Add data validation at module boundaries** -- when morning_brief reads watchlist_summary.json, validate the structure matches expectations. Fail loudly rather than showing default values silently.

5. **Add staleness checks on all cached data** -- timestamp all cached files and refuse to use data older than a configured threshold.

6. **Fix social sentiment word boundary matching** -- port the `_keyword_match()` approach from news_researcher to social_sentiment.

7. **Make backtest use actual signal logic** -- or clearly label it as a simplified technical-only check.

8. **Add atomic writes everywhere parallel threads write** -- the watchlist_summary.json race condition can lose scan data silently.

---

## Appendix: Files Audited

| File | Lines | Findings |
|------|-------|----------|
| `src/market_scanner.py` | ~1358 | P0-01, P0-07, P1-02, P1-06, P1-07, P1-09, P2-05, P2-07, P3-02, P3-05, P3-06 |
| `src/news_researcher.py` | ~531 | P2-01, P2-02, P3-04 |
| `src/social_sentiment.py` | ~675 | P1-03, P2-03, P2-04, P2-08, P2-11, P3-01 |
| `src/market_learner.py` | ~643 | P0-01 (counterpart), P1-04, P1-05, P2-06, P3-03 |
| `src/config.py` | ~389 | P1-01 |
| `src/prediction_game.py` | ~464 | P0-05, P2-10 |
| `src/morning_brief.py` | ~341 | P0-02, P0-03, P0-04, P0-06, P1-08, P2-09 |

**Total findings: 33** (7 P0 Critical, 9 P1 High, 11 P2 Medium, 6 P3 Low)
