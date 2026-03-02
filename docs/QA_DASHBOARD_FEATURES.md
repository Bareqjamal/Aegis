# QA Dashboard Features Report

**File Under Test:** `dashboard/app.py` (~8788 lines)
**Date:** 2026-02-27
**Auditor:** Dashboard Feature QA Agent
**Scope:** All 28 views, navigation, auth, sidebar, helpers, edge cases

---

## Summary

| Severity | Count |
|----------|-------|
| P0 CRITICAL | 0 |
| P1 HIGH | 3 |
| P2 MEDIUM | 10 |
| P3 LOW | 8 |
| **Total** | **21** |

All backend module APIs were cross-referenced. Every function called from `app.py` was verified to exist in its target module. No broken imports were found.

---

## Findings by Page

---

### 1. Imports & Module Reloading (Lines 1-73)

**PASS** -- All imports are valid. `importlib.reload()` correctly reloads `config` first (before re-importing classes), then all other backend modules. The reload order prevents stale `__pycache__` issues.

**Verified modules:** config, data_store, auth_manager, i18n, token_manager, market_scanner, news_researcher, social_sentiment, chart_engine, market_learner, auto_trader, paper_trader, risk_manager, performance_analytics, alert_manager, fundamentals, strategy_builder, backtester, portfolio_optimizer, watchlist_manager, report_generator, economic_calendar, morning_brief, geopolitical_monitor, macro_regime, hindsight_simulator, prediction_game, chief_monitor, agents, autonomous_manager, sector_analysis, market_discovery, hyperopt_engine.

No finding.

---

### 2. CSS & Constants (Lines 75-542)

**PASS** -- `TERMINAL_CSS` is well-structured. Color constants match the style guide (green `#3fb950`, blue `#58a6ff`, gray `#6e7681`). Signal style mappings are complete for all 5 signal labels. Disclaimer text is present.

No finding.

---

### 3. Helper Functions & Caching (Lines 549-1070)

**PASS** -- `generate_sparkline_svg()`, `load_watchlist_summary()`, `_fetch_live_prices_cached()`, `fetch_live_prices()`, `_fetch_correlation_data_90d()`, `_fetch_benchmark_returns()`, `get_sparklines_batch()` all have proper error handling with try/except blocks and `@st.cache_data` decorators with TTL values.

No finding.

---

### 4. signal_card_html() (Lines 1076-1170)

#### F-01: `entry` can be None, causing TypeError in f-string formatting
- **Severity:** P1 HIGH
- **Location:** Line 1131
- **Code:**
  ```python
  entry = data.get("entry")  # line 1098 — no default, can be None
  # ...
  if target is not None and stop_loss is not None:  # line 1124 — does NOT check entry
      # ...
      f"Entry: <b style=\"color:#e6edf3;\">${entry:,.2f}</b>"  # line 1131 — crashes if entry is None
  ```
- **Impact:** If the scanner produces a signal with `target` and `stop_loss` but no `entry` price, the entire Advisor page crashes with `TypeError: unsupported format character`.
- **Fix:** Add `entry is not None` to the guard on line 1124:
  ```python
  if target is not None and stop_loss is not None and entry is not None:
  ```

---

### 5. Authentication Flow (Lines 1182-1368)

**PASS** -- Login, register, guest mode, session restore, email verification gate, and disclaimer gate are all correctly implemented. The remember-me flow uses file-based sessions (`_active_session.json`). Rate limiting on email verification is enforced via `auth_manager`.

No finding.

---

### 6. Auto-Refresh Setup (Lines 1370-1377)

#### F-02: Default view fallback inconsistency
- **Severity:** P2 MEDIUM
- **Location:** Line 1372
- **Code:**
  ```python
  _current_view = st.session_state.get("view", "watchlist")  # line 1372 — default "watchlist"
  # ...
  st.session_state["view"] = "advisor"  # line 2047 — actual default is "advisor"
  ```
- **Impact:** If `view` is not yet in session state at line 1372 (before the initialization at line 2046-2047), the fallback is `"watchlist"` instead of `"advisor"`. In practice this may not matter since `"watchlist"` is not in the auto-refresh list `("logs", "monitor")`, but it is semantically incorrect and could cause confusion if the auto-refresh lists change.
- **Fix:** Change default to `"advisor"` on line 1372:
  ```python
  _current_view = st.session_state.get("view", "advisor")
  ```

---

### 7. Sidebar Navigation (Lines 1386-1541)

**PASS** -- Navigation groups (TRADING/INTELLIGENCE/SYSTEM/RESEARCH) render correctly. Active view styling uses glow/border matching group colors. Locked views (PRO_VIEWS: optimizer, strategy_lab) show lock icons and redirect to upgrade prompts. Research entries dynamically list markdown files.

No finding.

---

### 8. Sidebar Portfolio Ticker (Lines 1543-1575)

#### F-03: Uses private method `paper_trader._load()`
- **Severity:** P3 LOW
- **Location:** Line 1545
- **Code:**
  ```python
  _sb_port = paper_trader._load()
  ```
- **Impact:** Relies on a private API. If `paper_trader` refactors `_load()`, this breaks. However, the entire block is wrapped in `try/except Exception: pass` so it degrades silently rather than crashing.
- **Fix:** Add a public `load_portfolio()` method to `paper_trader.py` or accept the private usage with a comment.

#### F-04: Equity calculation ignores unrealized P&L from open positions
- **Severity:** P2 MEDIUM
- **Location:** Line 1546
- **Code:**
  ```python
  _sb_equity = _sb_port.get("cash", 1000)
  ```
- **Impact:** The sidebar ticker shows only cash balance, not total equity (cash + unrealized P&L). Users see a misleading portfolio value that does not include the value of open positions. The Paper Trading page itself correctly shows unrealized P&L, but the always-visible sidebar ticker does not.
- **Fix:** Use `paper_trader.get_portfolio_summary()` with live prices to get accurate total equity, or add a note "(cash only)" to the label.

---

### 9. Navigation Helpers (Lines 1916-1994)

**PASS** -- `_navigate_to()`, `render_page_header()`, `asset_link_button()`, and `render_page_info()` all correctly manage `previous_view` tracking and rerun on navigation. The `_VIEW_GROUP_MAP` covers all 28 views.

No finding.

---

### 10. Feature Gating (Lines 2053-2122)

**PASS** -- Locked views show upgrade prompts with feature previews. Only `optimizer` and `strategy_lab` are gated. The redirect mechanism correctly shows what users are missing rather than dead-ending.

No finding.

---

### 11. Daily Advisor Page (Lines 2150-3109)

#### F-05: Both branches of alert badge color ternary produce same value
- **Severity:** P2 MEDIUM
- **Location:** Line 2833
- **Code:**
  ```python
  _badge_color = "#d29922" if _first_alert.get("alert_level") == "HIGH" else "#d29922"
  ```
- **Impact:** HIGH and non-HIGH alerts are visually indistinguishable. The ternary is a no-op. LOW/MEDIUM alerts should probably use a different color (e.g., `#8b949e` for low, `#58a6ff` for medium).
- **Fix:**
  ```python
  _badge_color = "#f85149" if _first_alert.get("alert_level") == "HIGH" else "#d29922"
  ```

#### F-06: MTF agreement boolean expression missing parentheses
- **Severity:** P2 MEDIUM
- **Location:** Line 2854
- **Code:**
  ```python
  _mtf_agrees = signal in ("BUY", "STRONG BUY") and _mtf_lbl == "BULLISH" or signal in ("SELL", "STRONG SELL") and _mtf_lbl == "BEARISH"
  ```
- **Impact:** Due to Python operator precedence (`and` binds tighter than `or`), this evaluates as `(A and B) or (C and D)` which is the intended logic. However, the expression is fragile and confusing to maintain. Any future modification could introduce a logic error.
- **Fix:** Add explicit parentheses for clarity:
  ```python
  _mtf_agrees = (signal in ("BUY", "STRONG BUY") and _mtf_lbl == "BULLISH") or (signal in ("SELL", "STRONG SELL") and _mtf_lbl == "BEARISH")
  ```

#### F-07: Prediction game `_pg_scored` iteration assumes dict structure
- **Severity:** P3 LOW
- **Location:** Lines 2200-2230 (approximate)
- **Impact:** If `prediction_game.get_scored_predictions()` returns entries with missing keys, the `.get()` calls handle it gracefully. No crash risk. This is a robustness note only.

---

### 12. Asset Detail Page (Lines 3113-3406)

**PASS** -- 5-tab layout (Chart, News, Social, Fundamentals, Trades) correctly reads from `st.session_state["detail_asset"]`. The quick-trade buttons, social sentiment display, and fundamentals metrics all use proper error handling. Back navigation works via `render_page_header()`.

No finding.

---

### 13. Watchlist Page (Lines 3411-3657)

#### F-08: Hardcoded German text not wrapped in i18n
- **Severity:** P3 LOW
- **Location:** Line 3581
- **Code:**
  ```python
  f"Token-Kosten heute: ${daily_cost:.4f} | Budget: ${tm.budget_remaining():.4f} verbleibend"
  ```
- **Impact:** German text ("Token-Kosten heute", "verbleibend") appears regardless of the user's language setting. Should use `t()` translation function.
- **Fix:** Replace with i18n-wrapped strings or translate to English as default:
  ```python
  f"Token cost today: ${daily_cost:.4f} | Budget: ${tm.budget_remaining():.4f} remaining"
  ```

---

### 14. News Intelligence Page (Lines 3662-4190)

#### F-09: Both branches of influencer alert color ternary produce same value
- **Severity:** P2 MEDIUM
- **Location:** Line 3861
- **Code:**
  ```python
  _al_color = "#d29922" if _al_level == "HIGH" else "#d29922"
  ```
- **Impact:** Identical to F-05. HIGH and non-HIGH influencer alerts use the same color. No visual differentiation.
- **Fix:**
  ```python
  _al_color = "#f85149" if _al_level == "HIGH" else "#d29922"
  ```

---

### 15. Paper Trading Page (Lines 5255-6016)

#### F-10: Risk Guardian `usd_amount` KeyError potential
- **Severity:** P1 HIGH
- **Location:** Line 5312
- **Code:**
  ```python
  _rg_exp_usd = sum(p["usd_amount"] for p in _rg_open_pos)
  ```
- **Impact:** If any open position dictionary is missing the `"usd_amount"` key (e.g., older positions created before this field was added, or positions modified by external edits), this line crashes with `KeyError`, breaking the entire Paper Trading page.
- **Fix:** Use `.get()` with a default:
  ```python
  _rg_exp_usd = sum(p.get("usd_amount", 0) for p in _rg_open_pos)
  ```

#### F-11: Variable name `_auto_closed` reused in different scopes
- **Severity:** P3 LOW
- **Location:** Lines 5272 and 5838
- **Code:**
  ```python
  _auto_closed = paper_trader.check_automated_exits(_pt_live_prices)  # line 5272
  # ... ~560 lines later ...
  _auto_closed = len(_auto_cycle.get("exits_closed", []))  # line 5838
  ```
- **Impact:** No runtime bug because line 5272's value is consumed immediately (lines 5273-5274) before being overwritten at line 5838. However, this is a maintenance hazard. If someone adds code between these two assignments that references `_auto_closed`, they could get the wrong value.
- **Fix:** Rename line 5838 variable to `_auto_cycle_closed` or similar.

#### F-12: Auto-scheduler runs on every page refresh when interval elapsed
- **Severity:** P3 LOW
- **Location:** Lines 5830-5847
- **Impact:** The auto-scheduler checks if enough time has passed since last run and triggers a bot cycle. Since the Paper Trading page auto-refreshes every 60 seconds, the bot could run every 60 seconds if the configured interval is <= 60 seconds. This is by design but could be surprising to users who set a 1-minute interval. The minimum selectable interval (5 minutes) mitigates this.

---

### 16. Charts Page (Lines 6021-6284)

#### F-13: No try/except around `chart_engine.fetch_ohlcv()`
- **Severity:** P2 MEDIUM
- **Location:** Line 6045
- **Code:**
  ```python
  _ch_df = chart_engine.fetch_ohlcv(_ch_ticker, period=_period, interval=_interval)
  if not _ch_df.empty:
  ```
- **Impact:** If yfinance raises a network error, connection timeout, or any other exception, the entire Charts page crashes with an unhandled exception. Other pages that fetch data (Advisor, Paper Trading) use try/except or ThreadPoolExecutor timeouts.
- **Fix:** Wrap in try/except:
  ```python
  try:
      _ch_df = chart_engine.fetch_ohlcv(_ch_ticker, period=_period, interval=_interval)
  except Exception:
      _ch_df = pd.DataFrame()
      st.warning("Failed to fetch chart data. Check network connection.")
  ```

#### F-14: `st.selectbox` may not honor session state `chart_asset` from navigation
- **Severity:** P3 LOW
- **Location:** Line 6030
- **Code:**
  ```python
  _ch_asset = st.selectbox("Asset", list(_ch_watchlist.keys()), key="chart_asset")
  ```
- **Impact:** When navigating from Advisor via `_navigate_to("charts", chart_asset="Gold")`, the selectbox uses `key="chart_asset"` which Streamlit should honor from session state. This works correctly in most cases. However, if the watchlist order changes between renders, the selectbox index may not match the session state value, causing a brief flicker. Cosmetic only.

---

### 17. Analytics Page (Lines 6289-6434)

**PASS** -- All 9 chart functions from `performance_analytics` are correctly called. The 3-tab layout (Returns, Patterns, Advanced) displays charts with proper fallback messages when no trade history exists.

No finding.

---

### 18. Strategy Lab Page (Lines 6439-6543)

**PASS** -- Strategy builder, templates, and optimizer tabs are correctly structured. Feature-gated for pro users. Backend calls to `strategy_builder` and `backtester` are valid.

No finding.

---

### 19. Alerts Page (Lines 6546-6625)

**PASS** -- Active alerts display, create alert form (price/signal type), and notification settings (Discord/Telegram/Email webhook URLs) are implemented. Backend calls to `alert_manager` verified.

No finding.

---

### 20. Report Card Page (Lines 6630-6841)

**PASS** -- Prediction accuracy display, hindsight simulations, and lessons learned all read from JSON files with proper error handling. The grading system (A+ through F) is correctly implemented.

No finding.

---

### 21. Fundamentals Page (Lines 6846-7030)

**PASS** -- Key metrics and earnings calendar correctly call `fundamentals.get_fundamentals()` and `fundamentals.get_price_performance()`. Error handling wraps yfinance calls.

No finding.

---

### 22. Morning Brief Page (Lines 7091-7345)

**PASS** -- One-page daily snapshot with regime overview, top picks, calendar events, social pulse, and key takeaway. Correctly uses `morning_brief.generate_brief()` with fallback to cached data. All section renders are wrapped in try/except.

No finding.

---

### 23. Economic Calendar Page (Lines 7350-7529)

**PASS** -- Event listing with countdown timers, impact ratings (1-3 stars), affected assets, and historical context. Correctly uses `economic_calendar.get_upcoming_events()` with proper date formatting.

No finding.

---

### 24. Trade Journal Page (Lines 7532-7758)

**PASS** -- Filters (asset, direction, date range), 3 charts (P&L over time, P&L by asset, win/loss distribution), trade table with notes, and CSV export button. All `paper_trader` and `performance_analytics` calls verified.

No finding.

---

### 25. Risk Dashboard Page (Lines 7763-8180)

#### F-15: Kelly Criterion display multiplies by 2 without explanation to user
- **Severity:** P3 LOW
- **Location:** Line 7805
- **Code:**
  ```python
  _full_kelly = risk_manager.kelly_criterion(_k_wr, _k_avgw, _k_avgl) * 2  # show full kelly (we use half)
  ```
- **Impact:** The code is correct -- `kelly_criterion()` returns half-Kelly, and the display shows full Kelly for educational purposes. However, the UI label says "KELLY CRITERION BREAKDOWN" without indicating this is FULL Kelly, while the system actually uses half-Kelly for position sizing. Users may be confused about why their actual position sizes are half of what the display suggests.
- **Fix:** Add clarifying text in the UI: "Full Kelly shown below (system uses half-Kelly for safety)."

#### F-16: Correlation heatmap data fetch has no timeout protection
- **Severity:** P2 MEDIUM
- **Location:** Lines 7875-7900 (approximate, via `_fetch_correlation_data_90d`)
- **Impact:** The cached correlation data fetch (`@st.cache_data` with 10-minute TTL) calls `yf.download()` for multiple tickers. If yfinance hangs (DNS failure, API rate limit), the entire Risk Dashboard page hangs until Streamlit's default timeout. Other data-fetching pages use `ThreadPoolExecutor` with 15-second timeouts.
- **Fix:** Wrap `_fetch_correlation_data_90d()` internals with the same `ThreadPoolExecutor` + 15s timeout pattern used elsewhere.

---

### 26. Watchlist Manager Page (Lines 8183-8375)

**PASS** -- Named watchlist CRUD (create, switch, delete, duplicate), preset loading (5 presets), add/remove assets, and backward compatibility sync to `user_watchlist.json`. All `watchlist_manager` calls verified.

No finding.

---

### 27. Portfolio Optimizer Page (Lines 8378-8546)

**PASS** -- 4 optimization strategies (Max Sharpe, Min Variance, Equal Weight, Half-Kelly), efficient frontier chart, allocation bar/pie charts. Correctly feature-gated. All `portfolio_optimizer` calls verified.

No finding.

---

### 28. Settings Page (Lines 8551-8758)

#### F-17: Refresh interval settings saved but not wired to auto-refresh
- **Severity:** P2 MEDIUM
- **Location:** Lines 8700-8720 (approximate) vs Lines 1370-1376
- **Code (settings save):**
  ```python
  # Settings page allows users to change refresh intervals
  # Saved to settings_override.json
  ```
  ```python
  # But auto-refresh is hardcoded at top of file:
  st_autorefresh(interval=10_000, ...)  # line 1374 — hardcoded 10s
  st_autorefresh(interval=60_000, ...)  # line 1376 — hardcoded 60s
  ```
- **Impact:** Users can change refresh intervals in Settings and see them save successfully, but the actual auto-refresh behavior never changes because the intervals are hardcoded at the top of `app.py`. The settings values are written to `settings_override.json` but never read back for the autorefresh calls.
- **Fix:** Read refresh interval from settings at line 1370:
  ```python
  _refresh_live = config.get_setting("refresh_live_ms", 10000)
  _refresh_trading = config.get_setting("refresh_trading_ms", 60000)
  ```

---

### 29. "Killed" Pages (Lines 4317-5252)

#### F-18: Dead code for 6 killed pages still accessible and executing
- **Severity:** P2 MEDIUM
- **Location:** Lines 4317-4588 (evolution), 4591-4709 (performance), 4712-4772 (kanban), 4775-4930 (monitor), 4933-5062 (budget), 5065-5252 (logs)
- **Impact:** Although these pages are removed from the sidebar navigation, they can still be accessed by directly setting `st.session_state["view"]` (e.g., via URL parameters, browser console, or session state manipulation). Each page loads and executes its full code, including backend API calls. This is ~935 lines of dead code that:
  - Increases page load time (Python parses all branches)
  - Creates maintenance burden (changes to backend APIs must account for dead code)
  - Could confuse developers
- **Fix:** Either (a) remove the code entirely, (b) add a guard at the top of each killed view that redirects to advisor, or (c) consolidate them under a single "deprecated" redirect.

---

### 30. Global Footer (Lines 8770-8788)

**PASS** -- Legal disclaimer renders on every page with correct versioning. The `DISCLAIMER_SHORT` constant is properly referenced.

No finding.

---

### 31. View Routing & Fallback (Lines 8764-8767)

**PASS** -- Unknown views redirect to advisor with a warning message. The `else:` clause at the end of the if/elif chain catches any unrecognized view state.

No finding.

---

## Cross-Cutting Concerns

### 32. Backend API Verification

All backend functions called from `dashboard/app.py` were verified to exist in their respective modules:

| Module | Functions Called | Status |
|--------|----------------|--------|
| paper_trader | _load, open_position, close_position, get_open_positions_with_pnl, get_portfolio_summary, get_trade_history, get_equity_curve, record_equity_snapshot, check_automated_exits, check_pending_orders, get_pending_orders, cancel_order, partial_close, update_stop_loss, update_take_profit, save_position_note, save_trade_note, reset_portfolio, export_trades_csv | PASS (18 functions) |
| risk_manager | suggest_position_size, max_drawdown, kelly_criterion, portfolio_exposure, exposure_pie_chart, calculate_stop_take | PASS (6 functions) |
| performance_analytics | generate_report, equity_drawdown_chart, cumulative_pnl_chart, pnl_distribution_chart, pnl_by_asset_chart, trade_timeline_chart, performance_by_day_chart, rolling_win_rate_chart, win_loss_streak_chart, consecutive_wins_losses, avg_holding_time, hourly_performance_chart | PASS (12 functions) |
| alert_manager | get_alerts, add_alert, delete_alert, check_alerts, get_notification_settings, save_notification_settings, export_alerts, clear_triggered | PASS (8 functions) |
| chart_engine | fetch_ohlcv, add_indicators, build_candlestick_chart, detect_support_resistance, detect_trendlines, detect_patterns, build_macd_chart | PASS (7 functions) |
| fundamentals | get_fundamentals, get_price_performance | PASS (2 functions) |
| portfolio_optimizer | optimize_from_watchlist, efficient_frontier_chart, allocation_bar_chart, allocation_pie_chart | PASS (4 functions) |
| prediction_game | PredictionGame (make_prediction, get_active_predictions, get_scored_predictions, score_pending, get_stats, get_leaderboard) | PASS (6 methods) |
| social_sentiment | SocialSentimentEngine.load_cached | PASS (1 method) |
| report_generator | generate_report_bytes | PASS (1 function) |
| auth_manager | authenticate, register, can_access_view, accept_disclaimer, get_profile, start_email_verification, verify_email, resend_verification | PASS (8+ methods) |
| data_store | get_profile | PASS (1 method) |

**Result:** No broken imports or missing function calls found.

---

### 33. State Management

#### F-19: No session state cleanup on logout
- **Severity:** P3 LOW
- **Location:** Logout flow (sidebar)
- **Impact:** When a user logs out, session state keys like `detail_asset`, `chart_asset`, `previous_view`, and prediction game data from the previous user's session remain in memory. If a new user logs in on the same Streamlit session, they may briefly see stale navigation state. The auth gate prevents data access, but stale UI state could cause confusion.
- **Fix:** Clear relevant session state keys on logout.

---

### 34. Error Handling Patterns

#### F-20: Inconsistent error handling across data fetches
- **Severity:** P2 MEDIUM
- **Location:** Throughout
- **Detail:** Some pages use `try/except` around data fetches (Advisor, Paper Trading, Morning Brief), while others do not (Charts page line 6045, correlation heatmap). The inconsistency means some pages are resilient to network failures while others crash entirely.
- **Fix:** Standardize all `yfinance` / network calls to use `try/except` with user-friendly error messages.

---

### 35. i18n Coverage

#### F-21: Multiple hardcoded English strings throughout dashboard
- **Severity:** P3 LOW
- **Location:** Throughout (estimated 50+ instances)
- **Detail:** While the i18n system supports 3 languages (en/de/ar) with 81 keys, only navigation labels and a few headers use `t()`. The vast majority of UI text (button labels, metric headers, explanation text, error messages) is hardcoded in English. The German text at line 3581 is the most visible example of this inconsistency.
- **Fix:** This is a large effort. Prioritize user-facing labels and headers for i18n wrapping. At minimum, fix the German text at line 3581 that appears regardless of language setting.

---

## Prioritized Fix List

### P1 HIGH (Fix immediately)

| ID | Page | Line | Description |
|----|------|------|-------------|
| F-01 | signal_card_html | 1131 | `entry` can be None, crashes exec_row f-string with TypeError |
| F-10 | Paper Trading | 5312 | `p["usd_amount"]` KeyError if position lacks key |

### P2 MEDIUM (Fix in next sprint)

| ID | Page | Line | Description |
|----|------|------|-------------|
| F-02 | Auto-refresh | 1372 | Default view fallback says "watchlist" but actual default is "advisor" |
| F-04 | Sidebar Ticker | 1546 | Shows cash only, not total equity with unrealized P&L |
| F-05 | Advisor | 2833 | Both ternary branches produce same color "#d29922" |
| F-06 | Advisor | 2854 | MTF agreement boolean missing parentheses (works by accident) |
| F-09 | News Intel | 3861 | Both ternary branches produce same color "#d29922" (duplicate of F-05 pattern) |
| F-13 | Charts | 6045 | No try/except around fetch_ohlcv — page crashes on network error |
| F-16 | Risk Dashboard | ~7880 | Correlation data fetch has no timeout protection |
| F-17 | Settings | ~8700 | Refresh interval settings saved but auto-refresh is hardcoded |
| F-18 | Killed pages | 4317-5252 | ~935 lines of dead code still accessible via direct state manipulation |
| F-20 | Cross-cutting | Various | Inconsistent error handling across data fetch calls |

### P3 LOW (Fix when convenient)

| ID | Page | Line | Description |
|----|------|------|-------------|
| F-03 | Sidebar Ticker | 1545 | Uses private method `paper_trader._load()` |
| F-07 | Advisor | ~2210 | Prediction game robustness note (handles gracefully) |
| F-08 | Watchlist | 3581 | Hardcoded German text ("Token-Kosten heute") |
| F-11 | Paper Trading | 5272/5838 | Variable name `_auto_closed` reused in different scopes |
| F-12 | Paper Trading | 5830 | Auto-scheduler runs on every refresh when interval elapsed (by design) |
| F-14 | Charts | 6030 | selectbox may briefly ignore session state on watchlist reorder |
| F-15 | Risk Dashboard | 7805 | Kelly display shows full Kelly without clarifying label |
| F-19 | Auth | Logout | Session state not fully cleaned on logout |
| F-21 | Cross-cutting | Various | ~50+ hardcoded English strings not wrapped in i18n |

---

## Pages With No Findings (Clean)

The following pages passed all checks with no issues found:

1. **Asset Detail** (3113-3406) -- 5-tab layout, clean error handling
2. **Analytics** (6289-6434) -- 9 charts, proper fallbacks
3. **Strategy Lab** (6439-6543) -- Feature-gated, valid backend calls
4. **Alerts** (6546-6625) -- CRUD + notification settings
5. **Report Card** (6630-6841) -- Prediction accuracy, grading system
6. **Fundamentals** (6846-7030) -- Metrics display, earnings calendar
7. **Morning Brief** (7091-7345) -- Daily snapshot with full error handling
8. **Economic Calendar** (7350-7529) -- Event listing with countdowns
9. **Trade Journal** (7532-7758) -- Filters, charts, CSV export
10. **Watchlist Manager** (8183-8375) -- Named watchlists, presets, sync
11. **Portfolio Optimizer** (8378-8546) -- 4 strategies, feature-gated

---

## Methodology

1. Read the entire `dashboard/app.py` file (8788 lines) in sequential chunks
2. For each page/section, checked: imports, state management, data flow, error handling, UI rendering, navigation
3. Cross-referenced every backend function call against its source module using grep
4. Verified function signatures and return types match dashboard expectations
5. Checked for common Streamlit pitfalls: cache invalidation, session state races, f-string issues, unsafe_allow_html usage
6. Assessed edge cases: None values, missing dict keys, empty DataFrames, network failures

---

*End of QA report.*
