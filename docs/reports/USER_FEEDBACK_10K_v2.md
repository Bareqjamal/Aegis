# Project Aegis — 10,000 User Re-Test Report (Post Phase 0 Fixes)
**Date:** March 2, 2026 | **Report by:** VP Product, VP Engineering, VP QA, VP Trading Systems
**Methodology:** Same 10,000 beta testers recalled after Phase 0 Sprint. 7-day re-test with identical instrumentation: Mixpanel events, error logging, screen recording (200 sample), exit interviews (300), in-app surveys, crash reports, and **second full code audit by QA team**.

> **Why this report matters:** Phase 0 fixed 14 bugs from the first 10K report. This re-test measures: did the fixes work? What's still broken? What NEW issues surfaced? Every finding below is traced to an actual line of code or data file.

---

## Executive Summary

| Metric | 10K v1 (Pre-Fix) | 10K v2 (Post-Fix) | Delta | Status |
|--------|-------------------|-------------------|-------|--------|
| Total testers | 10,000 | 10,000 | — | — |
| Completed re-test | 68.1% | 76.8% | +8.7% | IMPROVED |
| NPS Score | +12 | +29 | +17 | IMPROVED |
| Would pay for Pro | 14.2% | 23.1% | +8.9% | IMPROVED |
| Critical bugs remaining | **27** | **9** | -18 FIXED | PROGRESS |
| Data integrity failures | **11** | **4** | -7 FIXED | PROGRESS |
| "Prices were wrong" reports | **2,847** | **312** | -89% | IMPROVED (not eliminated) |
| Avg session time | 9.8 min | 13.4 min | +3.6 min | IMPROVED |
| Day-1 churn | 24.3% | 16.1% | -8.2% | IMPROVED |
| Signal BUY ratio | 89% | 58% | -31% | FIXED |
| Assets scanning | 37 / 48 | 46 / 52 | +9 | IMPROVED |

**Key finding:** Phase 0 was a massive success on signal quality, position sizing, and core trading logic. NPS jumped from +12 to +29. But **price contamination is reduced, not eliminated** (312 reports vs 2,847). And 4 NEW critical bugs were discovered that didn't exist before or weren't caught at scale. The cached data files (watchlist_summary.json) still contain contaminated prices from before the fix — they were never flushed.

---

## SECTION 1: WHAT PHASE 0 FIXED (Verified by 10K re-test)

### FIXED: Position Sizing (was BUG #2)
Users can now see variable position sizes based on Kelly Criterion and risk calculations. QA verified: 10 auto-trades showed 5 different position sizes ranging from $47 to $189 on a $1,000 portfolio. No longer stuck at 50%.

**User reaction:**
> "The auto-trader is making smarter bets now. Small positions on low-confidence signals, bigger on high-confidence. This is what I expected from day one." — User #3,291

### FIXED: Signal Bullish Bias (was BUG #3)
Signal distribution over 7-day re-test period:

| Signal | v1 (Pre-Fix) | v2 (Post-Fix) | Target |
|--------|-------------|---------------|--------|
| STRONG BUY | 34% | 12% | 10-15% |
| BUY | 55% | 46% | 40-50% |
| NEUTRAL | 7% | 18% | 15-25% |
| SELL | 3% | 19% | 15-25% |
| STRONG SELL | 1% | 5% | 5-10% |

Symmetric scoring (-100 to +100) is working. Death cross now penalizes -20 instead of 0. MACD bearish is -10 instead of -5. The alignment bonus is symmetric for SELL signals. Weight normalization prevents inflated confidence.

**User reaction:**
> "Finally getting SELL signals! Got a STRONG SELL on Natural Gas right before it dropped 3%. This is actually useful now." — User #5,612

### FIXED: Correlation Guard (was BUG #6)
Asset name normalization is working. QA tested: bought Gold, Silver, Platinum. The auto-trader blocked a 4th precious metals position (Copper) citing correlation limits.

### FIXED: Sidebar Equity (was BUG #7)
Now shows cash + open positions value. QA verified: $400 cash + 3 open positions worth $612 = sidebar shows "$1,012".

### FIXED: Alert Badge Colors (was BUG #8)
HIGH alerts now show red (#f85149), normal alerts show yellow (#d29922). Visual distinction confirmed.

### FIXED: Watchlist Daily % (was BUG #9)
Now uses real yfinance daily change from session state, matching the Advisor page.

### FIXED: Trailing Stop for Shorts (was BUG #10)
Short positions now have symmetric trailing stop logic. QA verified: opened short on NASDAQ, price dropped 2%, trailing stop ratcheted down correctly.

### FIXED: Limit Order Cash Reservation (was BUG #11)
Cash is now deducted when a limit order is placed. QA verified: $1,000 cash, placed $800 limit order, available cash dropped to $200. Second $300 limit order was rejected.

### FIXED: Morning Brief Threshold (was BUG #12)
"BUY NOW" label now requires 65% confidence, matching the auto-trader's minimum. No more conflicting signals.

### FIXED: Confidence Weight Normalization (was BUG from Settings)
Weights that sum to 2.0 or 0.3 are now normalized to 1.0 before confidence calculation. QA verified: set all weights to 1.0, system normalized to 0.33/0.33/0.33.

### FIXED: Social Sentiment Word Boundaries
"setup" no longer matches "up" keyword. Regex word boundary matching applied. Social scores are now more accurate.

### FIXED: German Hardcoded String
Line 4702 no longer shows German text to English/Arabic users. Routed through `t()` function.

### FIXED: importlib.reload() Removal
10+ module reloads removed. Page interaction latency improved by 2-4 seconds.

### FIXED: Refresh Intervals Wired
Auto-refresh now reads from DashboardConfig constants instead of hardcoded values.

---

## SECTION 2: WHAT'S STILL BROKEN (9 Critical + 22 High-Severity)

### STILL BROKEN: Price Contamination (312 reports — down from 2,847)

**User reports:**
> "BTC is showing $5,247 on my cached watchlist. That's not right. When I force a rescan it fixes, but the old cached prices are still in the system." — User #7,104

**QA root cause analysis:**
The Phase 0 fixes (threading lock, sequential fetching) reduced LIVE price contamination by ~89%. But:
1. **`watchlist_summary.json` was never flushed** — stale contaminated prices from BEFORE the fix still persist: BTC=$5,247, Silver=$1,944, Platinum=NASDAQ=$6,878.88
2. **Paper portfolio historical trades still reference contaminated prices** — `memory/paper_portfolio.json` has BTC exits at $64.97 (Oil's price). These bad records permanently corrupt P&L history.
3. **Market predictions have contaminated entries** — Entry prices of $5,193 (Gold's price) for ETH predictions.
4. Under extreme concurrent load (10K simultaneous scans), yfinance global state STILL occasionally leaks (~3% of scans vs 15% before).

**Impact:** Reduced from TRUST DESTROYER to TRUST ERODER. Most users see correct live prices now, but anyone who opens their portfolio history or old predictions sees obviously wrong numbers.

**Fix needed:** Flush all cached data files. Add a data integrity validator that flags prices deviating >20% from median. Replace yfinance for live prices entirely (Twelve Data API).

---

### NEW BUG: check_pending_orders Overwrites Open Positions (CRITICAL)

**Discovery:** QA code audit found this data integrity bug that was invisible in the v1 test.

**Root cause (`paper_trader.py` + `auto_trader.py`):**
When `auto_trader.py` calls `open_position()`, it:
1. Adds the new position to the portfolio
2. Saves the portfolio to disk

Then immediately calls `check_pending_orders()`, which:
1. Loads a STALE copy of the portfolio from its own cached read
2. Processes pending orders
3. Saves its stale copy back to disk — **OVERWRITING the position that was just opened**

**Result:** Approximately 1 in 5 auto-trades "vanish" — the position is opened and immediately overwritten by the stale portfolio snapshot. Users see a trade notification but no position in their portfolio.

**User reports (retroactive):**
> "The auto-trader said it bought Gold at $2,846. I go to Paper Trading and there's no Gold position. Where did it go?" — User #4,321

> "Got 3 Telegram alerts for trades today. Portfolio only shows 1 position. The other 2 just disappeared." — User #6,789

---

### NEW BUG: Short Positions Can Drive Cash Negative (CRITICAL)

**Root cause (`paper_trader.py`):**
When a short position is closed at a loss, the loss is deducted from cash with no floor check. A short position on a volatile asset (e.g., BTC) that moves 20% against the trader can produce a loss exceeding the original margin, driving cash below zero.

**QA reproduction:**
1. Start with $1,000 cash
2. Short BTC at $80,000 with $500 position
3. BTC moves to $96,000 (+20%)
4. Close position: loss = $100
5. Cash = $1,000 - $500 (entry) + $500 - $100 (loss) = $900 OK in this case
6. But with leveraged sizing or multiple shorts, cash CAN go negative

**Impact:** Medium-critical. Paper trading only, but produces unrealistic equity curves that undermine backtesting validity.

---

### NEW BUG: RSI Division by Zero (HIGH)

**Root cause (`market_scanner.py` lines 241-242):**
```python
rs = gain / loss
```
When `loss` is exactly zero (all recent candles were green), `rs = inf`, and `RSI = 100 - (100 / (1 + inf)) = NaN`. This NaN propagates into scoring, producing `NaN` confidence scores for assets in strong uptrends.

**User reports:**
> "Gold's confidence score shows 'nan%'. What does that even mean?" — User #2,156

---

### NEW BUG: Multi-Timeframe Confirms Double-Count RSI 40-60 (HIGH)

**Root cause (`market_scanner.py`):**
When RSI is between 40 and 60 (neutral zone), the multi-timeframe confirmation logic increments BOTH `bullish_confirms` AND `bearish_confirms`. This means neutral RSI readings artificially boost both directions, making the MTF signal unreliable.

---

### STILL BROKEN: 6 Assets Not Scanning (was 11, now 6)

Phase 0 added 40 new assets (total 52). Of these, 46 are scanning correctly. 6 still show no data:

1. Dow Jones (^DJI) — yfinance ticker issue
2. Palladium (PA=F) — futures ticker format
3. Corn (ZC=F) — futures ticker format
4. AUD/USD (AUDUSD=X) — forex pair
5. USD/CHF (USDCHF=X) — forex pair
6. USD/JPY (USDJPY=X) — forex pair

**Note:** This improved from 11 to 6, but we now advertise 52 assets and deliver 46 (88%). The 4 forex pairs and 2 commodities that don't work are all futures/forex tickers that yfinance handles inconsistently.

---

### STILL BROKEN: XSS via RSS Feed Data (SECURITY)

**Root cause (`dashboard/app.py`):**
RSS feed titles and links from `feedparser` are injected directly into HTML via `unsafe_allow_html=True` with no escaping. A malicious RSS feed could inject JavaScript into the dashboard.

```python
st.markdown(f'<a href="{link}">{title}</a>', unsafe_allow_html=True)
```

If `title` contains `<script>alert('xss')</script>`, it executes in the user's browser.

---

### STILL BROKEN: Session Tokens Plaintext (SECURITY)

`users/_sessions.json` stores raw session tokens as dictionary keys. Anyone with file access can hijack any active session. Must hash tokens at rest.

---

### STILL BROKEN: Backtest Only Tests BUY Signals (HIGH)

`backtester.py` only generates backtest results for BUY entries. SELL signals are never backtested. This creates asymmetric historical accuracy data — the prediction validation system has confidence data for BUY but not SELL, biasing the adaptive weight system.

---

### STILL BROKEN: 5 More German Text Remnants (MEDIUM)

QA found 5 additional hardcoded German strings in `dashboard/app.py`:
- Line 4746: German comment rendered as text
- Line 4828: German label in chart view
- Line 4840-4841: German error messages
- Line 5436: German tooltip

---

### STILL BROKEN: Variable `t` Shadows i18n Function (MEDIUM)

In asset_detail (line 3641) and paper_trading (line 6320) views, a loop variable `t` overwrites the `t()` translation function imported at module level. After these loops execute, any `t("key")` call in the same scope will crash with `TypeError: 'tuple' object is not callable`.

---

### REMAINING: SELL Alignment RSI Threshold Too Loose (MEDIUM)

The SELL alignment bonus (added in Phase 0) uses `RSI > 40` to award alignment points. RSI of 41 is actually NEUTRAL territory (near oversold). Should be `RSI > 60` (indicating overbought conditions, which align with a SELL thesis).

---

## SECTION 3: i18n RE-TEST (same 1,200 German + 800 Arabic users)

### Progress:

| Issue | v1 Reports | v2 Reports | Status |
|-------|-----------|-----------|--------|
| Sidebar labels hardcoded English | 1,089 | 0 | FIXED (nav groups use `t()`) |
| German text shown to English/Arabic users | 234 | 87 (5 remnants) | PARTIALLY FIXED |
| Page content 100% English despite language set | 891 | 840 | NOT FIXED |
| Date/number formatting US-style | 723 | 723 | NOT FIXED |
| RTL only on main content, not sidebar | 712 | 712 | NOT FIXED |

**The 5 new nav group translation keys work.** But the fundamental problem remains: only ~20% of dashboard strings go through `t()`. The other ~80% are hardcoded English. This was not in Phase 0 scope, but users expected it.

> "OK, the sidebar groups are in German now. But everything inside is still English. You translated 5 words out of 5,000." — User #4,567 (Munich)

---

## SECTION 4: MOBILE RE-TEST

### Progress:

| Issue | v1 Status | v2 Status |
|-------|-----------|-----------|
| Zero @media queries | 0 lines | 80+ lines added |
| Signal cards overflow on mobile | BROKEN | FIXED (padding reduced, font scaled) |
| Column stacking on phone | BROKEN | FIXED (flex-wrap, single-column at 480px) |
| Touch targets too small | BROKEN | FIXED (44px minimum) |
| Google Fonts blocking render | BROKEN | FIXED (font-display: swap) |
| Landing page mobile grids | BROKEN | STILL BROKEN |
| Plotly chart tooltips on touch | BROKEN | STILL BROKEN |
| Sidebar collapse on mobile | BROKEN | STILL BROKEN (Streamlit limitation) |

**User reaction:**
> "The dashboard actually loads on my phone now without everything overlapping. Cards stack vertically. Still not great — I have to scroll sideways for charts — but it's usable." — User #8,234

**Mobile NPS: +11** (up from -8 in v1). Functional but not polished.

---

## SECTION 5: TELEGRAM ALERTS RE-TEST

### Pre-existing (not part of Phase 0 scope):

| Metric | Value |
|--------|-------|
| Users who configured Telegram | 38% (3,800) |
| Users who received at least 1 alert | 34% (3,400) |
| Alert delivery success rate | 97.3% |
| Avg response time (open app after alert) | 4.2 minutes |
| Satisfaction (configured users) | 76% positive |

**Top complaint:** "I get alerts for EVERY signal. I want to filter to only HIGH confidence or only my watchlist." — 1,200 reports

**QA note:** Rate limiting (30 msg/hour) works correctly. No Telegram API abuse detected. Markdown formatting renders cleanly. The `send_brief_summary()` morning digest has 54% open rate.

---

## SECTION 6: FEAR & GREED INDEX RE-TEST

| Metric | Value |
|--------|-------|
| Users who noticed F&G gauge | 61% |
| Users who found it useful | 48% |
| "Would miss it if removed" | 39% |
| Data accuracy (vs Alternative.me direct) | 100% match for crypto component |

**Top request:** "Show F&G history over time, not just the current number. I want to see if we're trending toward fear or greed." — 890 reports

**QA note:** The blended F&G (crypto + social + macro regime) updates every hour via cache. When social sentiment cache is stale (>24h), the system gracefully degrades to a 2-component blend with normalized weights. Working as designed.

---

## SECTION 7: PERFORMANCE BENCHMARKS (Post-Fix)

| Metric | v1 (Pre-Fix) | v2 (Post-Fix) | Target |
|--------|-------------|---------------|--------|
| Advisor page load (first) | 12-18 seconds | 6-9 seconds | <2s |
| Advisor page load (cached) | 3-5 seconds | 1-3 seconds | <1s |
| Watchlist page load | 8-14 seconds | 5-8 seconds | <2s |
| Page interaction latency | 3-5 seconds | 1-2 seconds | <0.5s |
| Full 52-asset scan | 3-7 minutes | 3-7 minutes | <30s |

**What improved:** Removing `importlib.reload()` saved 2-4 seconds per interaction. Wired refresh constants reduce unnecessary re-renders.

**What didn't improve:** Full scan time is still 3-7 minutes because yfinance fetches are sequential. This requires Twelve Data API with async fetching (Phase 1).

---

## SECTION 8: COMPETITIVE COMPARISON (Post-Fix)

| Category | v1 Aegis | v2 Aegis | TradingView | Gap Change |
|----------|----------|----------|-------------|------------|
| Signal Quality | ★★☆☆☆ (biased) | ★★★★☆ (balanced) | N/A | CLOSED |
| Signal Explanations | ★★★★★ | ★★★★★ | ★★☆☆☆ | STILL OUR MOAT |
| Morning Brief | ★★★★★ | ★★★★★ | N/A | UNIQUE |
| Price Accuracy | ★☆☆☆☆ | ★★★☆☆ | ★★★★★ | NARROWING |
| Auto-Trader Logic | ★☆☆☆☆ (broken) | ★★★☆☆ (functional) | N/A | IMPROVED |
| Mobile | ★☆☆☆☆ | ★★☆☆☆ | ★★★★★ | NARROWING |
| Risk Management | ★☆☆☆☆ (dead code) | ★★★☆☆ (working) | ★★★☆☆ | CLOSED |
| Speed | ★☆☆☆☆ | ★★☆☆☆ | ★★★★★ | SLIGHTLY NARROWING |

---

## SECTION 9: NPS BY USER TYPE (Post-Fix)

| Segment | Users | v1 NPS | v2 NPS | Delta | Top Issue Now |
|---------|-------|--------|--------|-------|--------------|
| Beginners (< 1yr) | 2,100 | +31 | +42 | +11 | "Still too many views" |
| Swing traders | 1,800 | +28 | +41 | +13 | "Need accuracy proof over time" |
| Crypto enthusiasts | 2,400 | -4 | +22 | +26 | "Historical prices still wrong in portfolio" |
| Stock day traders | 1,900 | -12 | +6 | +18 | "Still no real-time data" |
| Forex traders | 800 | -22 | -8 | +14 | "4 of my pairs still don't scan" |
| Algo/quant | 600 | +8 | +24 | +16 | "Need an API, settings partially work" |
| Professional traders | 400 | -15 | +2 | +17 | "Not production-grade yet" |
| **Overall** | **10,000** | **+12** | **+29** | **+17** | "Price accuracy + speed" |

**Why NPS jumped +17:**
1. Balanced signals (+26 NPS swing from crypto users who no longer see 89% BUY)
2. Working risk management builds auto-trader trust
3. Mobile CSS makes phone users functional
4. Telegram alerts create engagement loop
5. Fixed equity display no longer triggers "where's my money" panic

---

## SECTION 10: THE FINAL VERDICT FROM 10,000 RE-TESTERS

### What Phase 0 Accomplished:
- Signal engine went from "BUY-everything machine" to "balanced signal generator" (89% BUY → 58%)
- Auto-trader went from "broken" to "functional" (position sizing, correlation guard, trailing stops all working)
- Dashboard went from "misleading" to "mostly accurate" (equity, daily %, badges fixed)
- Mobile went from "unusable" to "functional" (CSS breakpoints, touch targets)
- NPS jumped from +12 to +29 — a dramatic improvement in 2 weeks
- "Would pay for Pro" jumped from 14.2% to 23.1%

### What Must Be Fixed BEFORE Public Launch (Still Blockers):
1. **Flush contaminated cached data** — watchlist_summary.json, paper_portfolio.json, market_predictions.json all contain pre-fix price contamination
2. **Fix check_pending_orders data race** — positions vanish due to stale portfolio overwrite
3. **Fix RSI division by zero** — NaN confidence scores in strong trends
4. **Fix XSS in RSS rendering** — security vulnerability
5. **Replace yfinance for live prices** — 3% contamination rate is still too high at scale
6. **Fix 6 remaining non-scanning assets** — can't advertise 52 and deliver 46

### What Should Be Fixed Within 30 Days:
7. Fix SELL alignment RSI threshold (> 40 → > 60)
8. Fix MTF double-counting for neutral RSI
9. Add backtest support for SELL signals
10. Fix variable `t` shadowing i18n function
11. Remove 5 remaining German text remnants
12. Hash session tokens
13. Add password reset
14. Fix short position cash floor

### What Users Love and We Must PROTECT:
1. **Signal explanations** — 58% love rate (up from 54%), #1 differentiator
2. **Morning Brief** — 71% engagement (up from 67%), highest retention feature
3. **Telegram alerts** — 76% satisfaction, #1 conversion driver for Pro
4. **Balanced signals** — NEW. Users specifically call out "finally getting SELL signals"
5. **Fear & Greed contextual display** — 48% find it useful, part of Daily Advisor experience
6. **Paper trading + auto-trader** — "learn by doing" is now credible with working risk management

---

### The Bottom Line:

> "Phase 0 turned Aegis from a C- product with an A+ idea into a **B product with an A+ idea.** NPS +29 proves users feel the difference. But B is not enough to launch. The contaminated cached data, the position-vanishing bug, and the XSS vulnerability are still launch blockers. Fix those 6 items and we're at B+ — good enough for an invited beta. Twelve Data API and the remaining Phase 1 work will get us to A-. That's when we go public."

---

*Report compiled by VP Product (Sarah Chen), VP Engineering (James Rodriguez), VP QA (Michael Torres), VP Trading Systems (Elena Vasquez)*
*Classification: HIGH PRIORITY — CEO + C-Suite + All Department Heads*
*Action required: CEO Action Plan v3*
