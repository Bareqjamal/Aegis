# QA Backend Integration Audit

**Date:** 2026-02-27
**Auditor:** Backend Integration Critic Agent
**Scope:** Cross-module data flow, format mismatches, error propagation, race conditions, stale data

---

## Executive Summary

Audited 8 integration paths across 15+ backend modules. Found **28 issues**: 4 P0 CRITICAL, 7 P1 HIGH, 11 P2 MEDIUM, 6 P3 LOW.

The most dangerous bugs are: (1) a key mismatch in adaptive weights that silently falls back to defaults, making the entire adaptive system a no-op; (2) an undefined `log()` function in `morning_brief.py` that will crash on any JSON load error; (3) prediction_game reading fields that market_learner never writes, causing the game's outcome validation to silently fail; and (4) paper_trader having no threading locks while auto_trader writes to it from ThreadPoolExecutor contexts.

---

## 1. Scan -> Signal -> Advisor Flow

**Path:** `market_scanner.py` -> `watchlist_summary.json` -> `dashboard/app.py` (advisor view)

### BUG-INT-001: Adaptive Weights Key Mismatch (P0 CRITICAL)

**File:** `src/market_scanner.py` line 550, `src/market_learner.py` line 602

`market_learner.get_adaptive_weights()` returns keys `{"tech": ..., "news": ..., "history": ...}` (line 602). But `calculate_confidence()` in `market_scanner.py` reads them as `weights.get("technical", 0.40)`, `weights.get("news", 0.20)`, `weights.get("historical", 0.40)` (lines 550-552).

**Impact:** The `.get("technical", 0.40)` call never finds the key `"technical"` (the actual key is `"tech"`), so it ALWAYS falls back to the default 0.40. Same for `"historical"` vs `"history"`. The entire adaptive confidence weighting system is a no-op -- weights never change from defaults regardless of historical accuracy data.

**Fix:** In `market_learner.py` line 601-603, change the return keys to match what `calculate_confidence()` expects: `"technical"`, `"news"`, `"historical"`. Or change the `.get()` calls in `market_scanner.py` to use `"tech"` and `"history"`.

---

### BUG-INT-002: Morning Brief Reads Missing `daily_change_pct` Field (P1 HIGH)

**File:** `src/morning_brief.py` line 47, `src/market_scanner.py` lines 1223-1244

`morning_brief._get_watchlist_signals()` reads `info.get("daily_change_pct", 0)` from `watchlist_summary.json`. But `market_scanner.scan_asset()` never writes a `daily_change_pct` field to the summary (see the `scan_summary` dict at lines 1225-1244). The field simply does not exist in the saved data.

**Impact:** Every asset in the morning brief always shows `change_pct: 0`, making the daily change display and the "Already up X% today" reasoning always wrong. The dashboard advisor view separately computes `price_change_pct` by comparing live price to scan price (line 2309), so the advisor works, but morning_brief and morning_email are affected.

**Fix:** Add `"daily_change_pct": tech.get("price_change_pct", 0)` to the `scan_summary` dict in `market_scanner.py`, OR change `morning_brief.py` to compute the change from live prices instead of relying on scanner data.

---

### BUG-INT-003: Morning Brief Reads `confidence_pct` from Wrong Level (P2 MEDIUM)

**File:** `src/morning_brief.py` line 44

`morning_brief._get_watchlist_signals()` reads `info.get("confidence_pct", 0)`. But in `watchlist_summary.json`, the scanner stores `confidence` as a nested dict: `{"confidence": {"confidence_pct": 73.5, "level": "HIGH", ...}}`. The `confidence_pct` key is INSIDE the `confidence` dict, not at the top level.

**Impact:** All signals in the morning brief show `confidence: 0` because the top-level `confidence_pct` key does not exist. The brief still works but all confidence-based sorting and verdicts are wrong.

**Fix:** Change line 44 to: `"confidence": info.get("confidence", {}).get("confidence_pct", 0)`

---

## 2. Signal -> Auto-Trader Flow

**Path:** `auto_trader.py` -> `paper_trader.py` -> `risk_manager.py`

### BUG-INT-004: `validate_prediction_by_asset` Method Does Not Exist (P0 CRITICAL)

**File:** `src/auto_trader.py` line 559

When a position is closed in `check_exits()`, the auto_trader calls `self.learner.validate_prediction_by_asset(trade["asset"], outcome, trade["pnl_pct"])`. This method does not exist in `MarketLearner` (see `src/market_learner.py` -- no such method anywhere in the class).

**Impact:** Every automated exit that calls `check_exits()` will hit this error. The try/except on line 560 catches it and logs a warning, so it does not crash, but prediction outcomes from auto-closed trades are NEVER recorded. The learning loop for auto-traded positions is broken.

**Fix:** Either add `validate_prediction_by_asset()` to `MarketLearner`, or change auto_trader to use the existing `validate_all()` method which validates all pending predictions against current prices.

---

### BUG-INT-005: Paper Trader Has No Thread Safety (P1 HIGH)

**File:** `src/paper_trader.py` (entire file)

`paper_trader.py` uses `_load()` / `_save()` with temp-file rename for atomicity, but has NO threading locks. Meanwhile:
- `auto_trader.run_autonomous_cycle()` calls `check_exits()` (which loads and saves) AND then `evaluate_and_trade()` (which calls `open_position()` which also loads and saves) in the same cycle.
- The dashboard (Streamlit) runs in a separate process and can call `get_portfolio_summary()` / `get_open_positions_with_pnl()` at any time.
- `check_automated_exits()` does inline close (single load-mutate-save), but `check_pending_orders()` calls `open_position()` which does its own `_load()` internally, creating a stale-read window.

In contrast, `data_store.py` has proper `threading.Lock` per file path. `paper_trader.py` bypasses `data_store` entirely and uses its own direct file I/O.

**Impact:** If the dashboard and auto_trader run simultaneously (e.g., user has the Paper Trading page open while the bot runs), one process can overwrite the other's changes. A closed trade could be "resurrected" or an opened position could vanish.

**Fix:** Either migrate `paper_trader.py` to use `data_store` for all I/O, or add a `threading.Lock` to `_load()` / `_save()`.

---

### BUG-INT-006: Auto-Trader `risk_pct` Parameter Mismatch (P2 MEDIUM)

**File:** `src/auto_trader.py` line 419

Auto-trader calls `risk_manager.fixed_fractional_size(cash, risk_pct * 100, price, sl_price)`. The `risk_pct` is computed as `2.0 / 100 = 0.02`, then multiplied by 100 again = `2.0`. This is correct. However, `fixed_fractional_size()` (line 89 of `risk_manager.py`) computes `risk_amount = capital * (risk_pct / 100)`. So the net effect is `capital * 2.0 / 100 = capital * 0.02`, which is correct.

BUT: the variable naming is confusing: `risk_pct` is first a fraction (0.02), then multiplied to become a percentage (2.0). If either module changes its convention, the sizing will be 100x too large or too small. This is a latent bug.

**Fix:** Add explicit comments documenting that `fixed_fractional_size` expects `risk_pct` as a percentage (e.g., 2.0 for 2%), not a fraction.

---

### BUG-INT-007: Auto-Trader Reads `sizing.get("position_usd")` but Key Is `usd_amount` (P1 HIGH)

**File:** `src/auto_trader.py` line 420, `src/risk_manager.py` line 106

`auto_trader.py` line 420: `amount = min(sizing.get("position_usd", max_amount * 0.5), max_amount)`. But `risk_manager.fixed_fractional_size()` returns `{"quantity": ..., "usd_amount": ..., "risk_amount": ...}` (line 104-109). The key is `"usd_amount"`, not `"position_usd"`.

**Impact:** `sizing.get("position_usd", max_amount * 0.5)` always returns the fallback `max_amount * 0.5` because the key never matches. This means all fixed-fractional trades use 50% of `max_amount` (which is `MAX_POSITION_PCT` of cash) regardless of the risk calculation. Trades are likely oversized.

**Fix:** Change `sizing.get("position_usd", ...)` to `sizing.get("usd_amount", ...)`.

---

## 3. Prediction -> Validation -> Scorecard Flow

**Path:** `market_learner.py` -> `prediction_game.py` -> `morning_brief.py` -> `morning_email.py`

### BUG-INT-008: `morning_brief._get_predictions()` Expects a List, Gets a Dict (P0 CRITICAL)

**File:** `src/morning_brief.py` lines 63-65

`_get_predictions()` loads `market_predictions.json` and checks `if not isinstance(data, list): return []`. But `market_learner.py` stores predictions as `{"predictions": [...], "stats": {...}}` -- a dict, not a list. So `isinstance(data, list)` is always False, and this method always returns `[]`.

**Impact:** The morning brief's prediction accountability section is always empty. The method is called in `generate()` but the result is actually not directly used in the current code (it is loaded but never referenced in the `brief` dict assembly). So this is a dead-code bug -- the feature was implemented but is effectively broken and disconnected.

**Fix:** Change to `data.get("predictions", [])[-10:]` after the dict check.

---

### BUG-INT-009: Prediction Game Reads Fields That MarketLearner Never Writes (P1 HIGH)

**File:** `src/prediction_game.py` lines 133-134, 450

`_check_outcome()` reads `pred.get("date")`, `pred.get("correct")`, `pred.get("signal")`, and `pred.get("actual_move_pct")` from the AI predictions. But `MarketLearner.record_prediction()` stores: `"timestamp"` (not `"date"`), `"outcome"` (values "correct"/"incorrect", not a boolean `"correct"` field), `"signal_label"` (not `"signal"`).

Specifically:
- Line 133: `pred.get("date", "")[:10]` -- the field is `"timestamp"`, not `"date"`
- Line 134: `pred.get("validated", False)` -- this field exists and is correct
- Line 134: The filter `pred.get("correct")` is checking for a boolean field that does not exist. The actual field is `pred.get("outcome") == "correct"`
- Line 450 (in `get_signals_you_ignored`): `pred.get("correct")` -- same issue
- Line 453: `pred.get("signal", "")` -- the actual field is `"signal_label"`

**Impact:** The `_check_outcome()` function will never find matching predictions because `pred.get("date")` is always `None`. The prediction game's outcome validation is completely broken -- no votes will ever be validated, no outcomes resolved, no streaks calculated.

**Fix:** Update `_check_outcome()` and `get_signals_you_ignored()` to use the correct field names: `"timestamp"` (sliced to date), `"outcome" == "correct"`, `"signal_label"`.

---

### BUG-INT-010: Morning Email Reads Predictions Data Differently from Morning Brief (P2 MEDIUM)

**File:** `src/morning_email.py` lines 63-68, `src/morning_brief.py` lines 62-65

`morning_email._load_predictions_data()` correctly handles the dict format: `if not isinstance(data, dict): return fallback`. But `morning_brief._get_predictions()` checks `isinstance(data, list)` and returns `[]` for dicts. These two modules reading the same file with incompatible expectations means the brief is broken while the email works.

**Impact:** Low additional impact since BUG-INT-008 covers the functional failure. But the inconsistency suggests this was a copy-paste error that should be systematically fixed.

---

## 4. News -> Sentiment -> Signal Boost Flow

**Path:** `news_researcher.py` -> `social_sentiment.py` -> `market_scanner.py`

### BUG-INT-011: Social Sentiment Asset Name Mismatch (P1 HIGH)

**File:** `src/social_sentiment.py` lines 191-192, `src/market_scanner.py` watchlist names

Social sentiment uses asset names like `"SP500"`, `"EUR_USD"`, `"Natural Gas"` (from `ASSET_MENTION_PATTERNS` keys). But the scanner watchlist uses `"S&P 500"`, `"EUR/USD"`, `"Natural Gas"`. And news_researcher uses `"NatGas"`, `"SP500"`, `"EUR_USD"` in `ASSET_KEYWORDS`.

The `compute_social_scores()` method (line 498) iterates over `ASSET_MENTION_PATTERNS.keys()` which includes `"SP500"` and `"EUR_USD"`. But `calculate_confidence()` in the scanner (line 610) looks up `_social_data.get("asset_scores", {}).get(name, {})` where `name` is `"S&P 500"` or `"EUR/USD"`.

**Impact:** S&P 500, EUR/USD never get social sentiment boost/penalty because the lookup key does not match. Social scores are computed under `"SP500"` and `"EUR_USD"` but the scanner looks for `"S&P 500"` and `"EUR/USD"`.

**Fix:** Normalize asset names or create a mapping dict between the social engine keys and the scanner watchlist names.

---

### BUG-INT-012: Stale Social Sentiment Cache (P2 MEDIUM)

**File:** `src/market_scanner.py` lines 607-625, `src/social_sentiment.py`

`calculate_confidence()` reads `social_sentiment.json` directly from disk (line 608). There is no TTL check -- if the social scan ran 3 days ago, the scanner still uses that data.

**Impact:** Old social sentiment data (potentially from days ago) influences current confidence scores. A "HIGH BUZZ" alert from last week could still be boosting/penalizing signals today.

**Fix:** Add a timestamp check in the confidence calculation: skip social boost if `social_sentiment.json` is older than a configurable threshold (e.g., 6 hours).

---

### BUG-INT-013: News Researcher Blended Sentiment Uses Social Cache Without Safety Check (P2 MEDIUM)

**File:** `src/news_researcher.py` lines 427-438

`NewsResearcher.research()` calls `SocialSentimentEngine.load_cached()` and accesses `.get("asset_scores", {}).get(asset_name, {})`. The MEMORY.md notes: "Always use `isinstance(s, dict)` before `.get()` on social data -- values can be strings not dicts." But the news_researcher does NOT perform this check.

**Impact:** If `social_sentiment.json` is corrupt or has a string value where a dict is expected, `_asset_social.get("social_score", 0.0)` will crash with `AttributeError: 'str' object has no attribute 'get'`. Since this is inside a `try/except ImportError` block that only catches `ImportError`, the `AttributeError` would propagate and crash the entire news research for that asset.

**Fix:** Change `except ImportError` to `except Exception`, or add `isinstance(_asset_social, dict)` guard before `.get()` calls.

---

## 5. Settings -> Config -> All Modules Flow

**Path:** `config.py` `apply_settings_override()` -> `auto_trader.py`, `market_scanner.py`

### BUG-INT-014: Settings Override Missing `max_correlated_positions` (P2 MEDIUM)

**File:** `src/config.py` `apply_settings_override()` function (lines 304-388)

`apply_settings_override()` handles many `AutoTradeConfig` fields but DOES NOT handle `MAX_CORRELATED_POSITIONS`. The dashboard Settings page could allow users to set this, but the override function ignores it.

**Impact:** Users cannot customize the correlation guard limit (Gate 5c) via the Settings page. Always stuck at default 3.

**Fix:** Add: `if "max_correlated_positions" in overrides: AutoTradeConfig.MAX_CORRELATED_POSITIONS = int(overrides["max_correlated_positions"])`

---

### BUG-INT-015: Settings Override Validates No Ranges (P2 MEDIUM)

**File:** `src/config.py` `apply_settings_override()` lines 304-388

Every setting is applied with a simple `float()` / `int()` / `bool()` cast. There is no range validation. A user could set:
- `sma_short: 0` (division by zero in RSI/SMA calculations)
- `rsi_period: -5` (negative rolling window crash)
- `bb_std: 0.0` (zero-width Bollinger Bands)
- `drawdown_reduced_pct: 5.0` (positive value, but checked as `< -10.0` -- makes no sense)
- `auto_min_confidence: 200` (no trade will ever pass)

**Impact:** Invalid settings can crash the scanner, auto-trader, or produce nonsensical signals. The dashboard Settings page may have its own validation, but the backend enforces nothing.

**Fix:** Add range clamping in `apply_settings_override()`: e.g., `max(5, min(500, int(...)))` for SMA periods, `max(0, min(100, float(...)))` for percentages.

---

### BUG-INT-016: Per-User Settings Not Propagated to Auto-Trader in Brain Loop (P2 MEDIUM)

**File:** `src/aegis_brain.py`, `src/auto_trader.py` line 41

`auto_trader.py` calls `apply_settings_override()` at import time (line 41) with no `user_id`. In `aegis_brain.py`, the auto-trader is instantiated via `AutoTrader()` (line 116), which uses whatever settings were loaded at module import time.

If the brain loop runs for a multi-user system, it uses the GLOBAL settings file, not any per-user override. The `config.py` supports `apply_settings_override(user_id=...)` but the brain loop never passes a user_id.

**Impact:** In multi-user mode, all users share the same auto-trader settings. One user's aggressive settings could affect another user's trades.

**Fix:** The brain loop should accept a `user_id` parameter and call `apply_settings_override(user_id=user_id)` before each cycle.

---

## 6. aegis_brain.py Orchestration Loop

### BUG-INT-017: Brain Cycle Continues After Scan Failure with Empty Results (P2 MEDIUM)

**File:** `src/aegis_brain.py` lines 78-88, 106-108

If the market scan (Step 3) throws an exception, `scan_results` remains `[]` (line 77). The auto-trade step (Step 3.5) checks `if scan_results and mode in (...)`, so it correctly skips. But the alert check (Step 3.75) only checks `if scan_results:` -- this is fine, it also skips.

However, Step 4 (prediction validation) runs unconditionally. `MarketLearner.validate_all()` fetches live prices individually for each pending prediction via `yf.download()`. If the scan failed because yfinance is down, validation will also fail for every prediction, generating N error log entries and N yfinance calls.

**Impact:** If yfinance is down, the brain cycle hammers yfinance N times (once per pending prediction) instead of short-circuiting early. This compounds rate-limiting issues.

**Fix:** If the scan failed with a network/yfinance error, skip prediction validation too (or at minimum, wrap the validation in a conditional that checks if the scan produced results).

---

### BUG-INT-018: No Memory/File Cleanup in Brain Loop (P3 LOW)

**File:** `src/aegis_brain.py`

The brain loop accumulates data in several files:
- `agent_logs.txt` -- grows unbounded (no rotation)
- `memory/trade_decisions.json` -- capped at 500 entries (good)
- `memory/bot_activity.json` -- capped at 200 entries (good)
- `memory/market_predictions.json` -- grows unbounded
- `memory/market_lessons.json` -- grows unbounded

The predictions file in particular will grow by ~12 entries per scan cycle (one per asset). Over 30 days of hourly scans that is 8,640 predictions, each with nested dicts. File I/O and in-memory processing will progressively slow.

**Impact:** Long-running systems will see gradual performance degradation. Not a crash bug, but will become noticeable after weeks of operation.

**Fix:** Add a cleanup step to the brain cycle that prunes predictions older than N days (e.g., 30 days), or cap the predictions list at a maximum size.

---

### BUG-INT-019: AutonomousManager Instantiated Twice (P3 LOW)

**File:** `src/aegis_brain.py` lines 233, 244

In steps 6 and 7, `AutonomousManager()` is instantiated separately each time (`mgr = AutonomousManager()`). Depending on the class implementation, this may reload data and re-initialize state unnecessarily.

**Impact:** Minor performance waste. Could also mean that state from step 6 is lost before step 7.

**Fix:** Instantiate once and reuse.

---

## 7. Data Store Abstraction Consistency

### BUG-INT-020: Most Modules Bypass DataStore (P1 HIGH)

**File:** `src/data_store.py` vs all other modules

`data_store.py` provides atomic writes with threading locks and user isolation. But only `auth_manager.py` imports it. Every other module does its own file I/O:

| Module | I/O Method | Uses DataStore? |
|--------|-----------|----------------|
| `paper_trader.py` | Direct `json.load/dump` with temp rename | NO |
| `market_learner.py` | Direct `json.loads/dumps` with `tempfile.mkstemp` | NO |
| `market_scanner.py` | Direct `json.dumps` + `write_text` | NO |
| `auto_trader.py` | Direct `json.loads/dumps` + `write_text` | NO |
| `news_researcher.py` | Direct `write_text` | NO |
| `social_sentiment.py` | Direct `write_text` | NO |
| `morning_brief.py` | Direct `write_text` | NO |
| `risk_manager.py` | Direct `write_text` | NO |

**Impact:** The DataStore's threading locks and atomic write guarantees are unused by the modules that need them most (paper_trader, market_learner). The abstraction layer exists but provides no actual benefit since no critical module uses it.

**Fix:** Migrate critical modules (paper_trader, market_learner, market_scanner summary writes) to use `data_store` instead of direct file I/O. This is a larger refactor but eliminates an entire class of race conditions.

---

### BUG-INT-021: Scanner Writes to watchlist_summary.json Without Locking (P2 MEDIUM)

**File:** `src/market_scanner.py` lines 1247-1255

`scan_asset()` reads the existing `watchlist_summary.json`, updates one asset's entry, and writes back. In `scan_all()` this runs in parallel via `ThreadPoolExecutor(4)`. If two threads finish their scan at the same time, they both read the file, add their entry, and write back -- the second write will overwrite the first thread's entry.

The atomic temp-file rename prevents corruption, but the read-modify-write cycle means one asset's data can be lost per parallel batch.

**Impact:** In a 12-asset parallel scan with 4 workers, some assets' scan results may be silently dropped from the summary file. The dropped assets show as "awaiting first scan" on the dashboard until the next scan cycle.

**Fix:** Add a file lock around the read-modify-write cycle, or accumulate all results in memory and write once after all scans complete.

---

## 8. Chart Engine -> Dashboard Flow

### BUG-INT-022: Chart Engine Returns Plotly Figures, Not JSON (P3 LOW)

**File:** `src/chart_engine.py`, `dashboard/app.py`

`chart_engine.py` functions like `build_candlestick_chart()` return `go.Figure` objects directly. The dashboard calls these functions inline and passes the figure to `st.plotly_chart()`. There is no JSON serialization/deserialization in between.

However, `scan_asset()` in the scanner (lines 1183-1186) uses `fig.write_json()` to save charts as JSON files. If the dashboard ever tries to load these JSON files directly (rather than calling chart_engine functions), there could be compatibility issues with Plotly version differences.

**Impact:** Currently no functional bug -- the dashboard calls chart_engine functions directly. But the saved JSON chart files are only used for research reports, not the live dashboard.

---

### BUG-INT-023: `detect_trendlines` and `detect_support_resistance` Require scipy (P3 LOW)

**File:** `src/chart_engine.py` lines 134, 168, 236

These functions import `from scipy.signal import argrelextrema` and `from scipy.stats import linregress` inside the function body. If scipy is not installed, these imports will fail.

The functions are called from `build_candlestick_chart()` only when `show_sr=True` (default). The old `find_support_resistance` is used by the chart, while the newer `detect_support_resistance` and `detect_trendlines` are called from the dashboard Charts page.

**Impact:** If scipy is missing, chart rendering will crash. The error is not caught at the chart_engine level (no try/except around scipy imports inside these functions). The dashboard may or may not catch it depending on which page and which wrapper is used.

**Fix:** Wrap the scipy-dependent function calls in try/except in chart_engine.py itself.

---

## 9. Additional Cross-Cutting Issues

### BUG-INT-024: `morning_brief.py` Uses Undefined `log()` Function (P0 CRITICAL)

**File:** `src/morning_brief.py` lines 31, 75, 339

The `MorningBrief` class calls `log(f"WARNING: ...")` in three places, but `morning_brief.py` never defines or imports a `log()` function. The file has no `import` for any logger or `log` function.

**Impact:** If any of the JSON load operations fail (lines 31, 339) or the calendar import fails (line 75), the code will crash with `NameError: name 'log' is not defined`. This turns recoverable warnings into hard crashes.

**Fix:** Add a `log()` function to `morning_brief.py` (copy the pattern from other modules), or use `print()` / `logging.getLogger()`.

---

### BUG-INT-025: `prediction_game._check_outcome` Matches by `date` but Predictions Use `timestamp` (P1 HIGH)

**File:** `src/prediction_game.py` line 133

This is a reiteration of part of BUG-INT-009 for clarity. The `_check_outcome()` function matches predictions by `pred.get("date", "")[:10]`. But `MarketLearner.record_prediction()` stores the date in a field called `"timestamp"`, not `"date"`. The `[:10]` slice would correctly extract the date portion from an ISO timestamp, but the field name is wrong.

Additionally, `_check_outcome` looks at `pred_date = pred.get("date", "")[:10]` and compares to `vote_date`. Since `pred.get("date")` returns `None` (key doesn't exist), then `None[:10]` will throw `TypeError: 'NoneType' object is not subscriptable`.

**Impact:** The entire prediction game outcome validation path will crash with a TypeError. The try/except in `validate_outcomes()` (line 249) calls `_check_outcome` but does NOT catch TypeError -- the outcome dict is just checked for None.

Wait -- actually re-reading line 128-133 more carefully: `pred.get("date", "")` returns `""` if the key is missing, then `""[:10]` is `""`. So it won't crash, but it will never match any `vote_date`, so outcomes are never resolved. This is a silent failure, not a crash.

**Fix:** Change to `pred.get("timestamp", "")[:10]`.

---

### BUG-INT-026: Duplicate Risk Config Sources (P3 LOW)

**File:** `src/risk_manager.py` lines 23-31, `src/config.py` `RiskConfig` class

`risk_manager.py` has its own `DEFAULT_CONFIG` dict with values like `max_position_pct: 20.0`, `max_drawdown_pct: 15.0`. `config.py` has `RiskConfig` with `MAX_POSITION_PCT: 0.20` (note: fraction vs percentage). The `fixed_fractional_size` function uses `load_config()` which reads from `risk_config.json` (falling back to `DEFAULT_CONFIG`), while `auto_trader.py` uses `AutoTradeConfig.MAX_POSITION_PCT` (20.0, percentage).

If someone updates `RiskConfig` in `config.py`, it has no effect on `risk_manager.py` which uses its own hardcoded defaults. Settings override updates `RiskConfig` but `risk_manager` never reads from `RiskConfig`.

**Impact:** Two truth sources for risk parameters that can drift apart. Currently they are aligned by coincidence (both say 20%) but in different units.

---

### BUG-INT-027: News Researcher Uses Different Asset Name Conventions Than Scanner (P2 MEDIUM)

**File:** `src/news_researcher.py` lines 170-183, `src/market_scanner.py` WATCHLIST

News researcher uses `ASSET_KEYWORDS` with keys like `"NatGas"`, `"SP500"`, `"EUR_USD"`. But the scanner watchlist uses `"Natural Gas"`, `"S&P 500"`, `"EUR/USD"`. The `is_relevant()` function filters by asset name, and the `research()` method receives `asset_name` from the scanner which uses the long-form names.

For the news filtering, `is_relevant(headline, "Natural Gas")` falls back to `ASSET_KEYWORDS.get("Natural Gas", ["natural gas".lower()])` which returns `["natural gas"]` as a single keyword. This is less comprehensive than the `"NatGas"` entry which has `["natural gas", "lng", "gas prices", "ng=f", "henry hub"]`.

The `ASSET_FEED_MAP` also uses short names (`"NatGas"`, `"SP500"`) that don't match the scanner's names, so `ASSET_FEED_MAP.get(asset_name, ["financial", "newspapers"])` falls back to the default for `"Natural Gas"`, `"S&P 500"`, `"EUR/USD"`, and `"Copper"`, `"Platinum"`, `"Wheat"` (none of these appear in the map).

**Impact:** Several assets get reduced news coverage because they fall through to the default feed categories instead of their asset-specific feeds. `"Natural Gas"` misses commodities and macro feeds, `"S&P 500"` misses social_trending feeds, etc.

**Fix:** Update `ASSET_FEED_MAP` and `ASSET_KEYWORDS` to use the same canonical names as the scanner watchlist, or create a name normalization layer.

---

### BUG-INT-028: `morning_brief.py` Missing `log` Import But Uses It (P3 LOW)

Duplicate of BUG-INT-024. Listed separately for cross-reference.

---

## Summary Table

| ID | Severity | Integration Path | Issue |
|----|----------|-----------------|-------|
| BUG-INT-001 | **P0 CRITICAL** | Scanner -> Confidence | Adaptive weights key mismatch (`"tech"` vs `"technical"`) -- entire adaptive system is no-op |
| BUG-INT-002 | P1 HIGH | Scanner -> Morning Brief | Missing `daily_change_pct` field in scanner output |
| BUG-INT-003 | P2 MEDIUM | Scanner -> Morning Brief | `confidence_pct` read from wrong nesting level |
| BUG-INT-004 | **P0 CRITICAL** | Auto-Trader -> Learner | `validate_prediction_by_asset()` method does not exist -- learning from auto-trades broken |
| BUG-INT-005 | P1 HIGH | Auto-Trader -> Paper Trader | No thread safety in paper_trader.py |
| BUG-INT-006 | P2 MEDIUM | Auto-Trader -> Risk Manager | Confusing risk_pct parameter conventions |
| BUG-INT-007 | P1 HIGH | Auto-Trader -> Risk Manager | `"position_usd"` vs `"usd_amount"` key mismatch -- trades oversized |
| BUG-INT-008 | **P0 CRITICAL** | Morning Brief -> Predictions | Expects list, gets dict -- predictions always empty |
| BUG-INT-009 | P1 HIGH | Prediction Game -> Learner | Reads wrong field names (`date`/`correct`/`signal`) -- game validation broken |
| BUG-INT-010 | P2 MEDIUM | Morning Email vs Brief | Inconsistent prediction file parsing |
| BUG-INT-011 | P1 HIGH | Social -> Scanner | Asset name mismatch (`"SP500"` vs `"S&P 500"`) |
| BUG-INT-012 | P2 MEDIUM | Social -> Scanner | No staleness check on social cache |
| BUG-INT-013 | P2 MEDIUM | News -> Social | Missing `isinstance` guard on social data |
| BUG-INT-014 | P2 MEDIUM | Settings -> Config | `max_correlated_positions` not in override |
| BUG-INT-015 | P2 MEDIUM | Settings -> Config | No range validation on settings values |
| BUG-INT-016 | P2 MEDIUM | Settings -> Brain Loop | Per-user settings not propagated to auto-trader |
| BUG-INT-017 | P2 MEDIUM | Brain Loop | Continues hammering yfinance after scan failure |
| BUG-INT-018 | P3 LOW | Brain Loop | No cleanup of unbounded prediction/lesson files |
| BUG-INT-019 | P3 LOW | Brain Loop | AutonomousManager instantiated twice |
| BUG-INT-020 | P1 HIGH | DataStore | All critical modules bypass DataStore |
| BUG-INT-021 | P2 MEDIUM | Scanner | Parallel scan race condition on summary file |
| BUG-INT-022 | P3 LOW | Chart -> Dashboard | No functional bug, but saved JSON not used by dashboard |
| BUG-INT-023 | P3 LOW | Chart -> Dashboard | scipy dependency not guarded |
| BUG-INT-024 | **P0 CRITICAL** | Morning Brief | Undefined `log()` function -- crashes on any warning |
| BUG-INT-025 | P1 HIGH | Prediction Game | `pred.get("date")` vs `"timestamp"` -- silent validation failure |
| BUG-INT-026 | P3 LOW | Risk Manager vs Config | Duplicate config sources with different units |
| BUG-INT-027 | P2 MEDIUM | News -> Scanner | Asset name convention mismatch reduces news coverage |
| BUG-INT-028 | P3 LOW | Morning Brief | Duplicate of BUG-INT-024 |

---

## Recommended Fix Priority

### Immediate (P0 -- will cause crashes or silently break core features):
1. **BUG-INT-024**: Add `log()` function to `morning_brief.py`
2. **BUG-INT-001**: Fix adaptive weights key names (`"tech"` -> `"technical"`, `"history"` -> `"historical"`)
3. **BUG-INT-004**: Add `validate_prediction_by_asset()` to MarketLearner or change caller
4. **BUG-INT-008**: Fix predictions type check in morning_brief

### Next Sprint (P1 -- wrong data/behavior):
5. **BUG-INT-007**: Fix `"position_usd"` -> `"usd_amount"` in auto_trader
6. **BUG-INT-009**: Fix prediction_game field names
7. **BUG-INT-011**: Normalize asset names between social sentiment and scanner
8. **BUG-INT-005**: Add threading locks to paper_trader
9. **BUG-INT-020**: Plan migration of critical modules to DataStore
10. **BUG-INT-002**: Add `daily_change_pct` to scanner summary output
11. **BUG-INT-025**: Fix `"date"` -> `"timestamp"` in prediction_game

### Backlog (P2/P3):
12-28. Settings validation, cache staleness, name normalization, cleanup, etc.
