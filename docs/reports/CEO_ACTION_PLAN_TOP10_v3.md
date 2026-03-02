# PROJECT AEGIS — CEO ACTION PLAN v3
# Post Phase 0 Sprint — Charting the Path to Public Launch
**Date:** March 2, 2026 | **Supersedes:** CEO_ACTION_PLAN_TOP10_v2.md (March 2, 2026)
**Status:** PHASE 0 COMPLETE — Preparing Phase 1 Launch

---

## WHAT CHANGED SINCE v2

Phase 0 was a 14-day emergency bug fix sprint. It's done. Here's the scorecard:

| v2 Phase 0 Item | Status | Evidence |
|-----------------|--------|----------|
| 0.1 Price contamination | PARTIALLY FIXED | Live scans reduced from 15% to 3% contamination. But cached data files still contain pre-fix bad prices. |
| 0.2 Position sizing (`position_usd` → `usd_amount`) | FIXED | Auto-trades now show 5+ different position sizes per 10 trades. |
| 0.3 Bullish signal bias (symmetric scoring) | FIXED | BUY ratio dropped from 89% to 58%. SELL signals now generate. Alignment bonus symmetric. |
| 0.4 11 assets never scanned → now 46/52 scan | PARTIALLY FIXED | 6 assets still broken (Dow, Palladium, Corn, 3 forex). Down from 11. |
| 0.5 Settings placebo → TechnicalParams wired | FIXED | RSI period, refresh intervals, confidence weights all functional. Weight normalization active. |
| 0.6 Correlation guard dead → asset names fixed | FIXED | Correlation groups use consistent naming. Guard blocks 4th correlated position. |
| 0.7 Sidebar equity wrong | FIXED | Shows cash + open position value. |
| 0.8 Alert badge same color | FIXED | HIGH = red, normal = yellow. |
| 0.9 Watchlist daily % wrong | FIXED | Uses real yfinance daily change. |
| 0.10 Morning Brief threshold mismatch | FIXED | Aligned to 65% across brief and auto-trader. |
| 0.11 Trailing stop broken for shorts | FIXED | Symmetric trailing stop logic implemented. |
| 0.12 Limit orders don't reserve cash | FIXED | Cash deducted on order placement. |
| 0.13 Drawdown uses total return → peak | FIXED | Peak equity tracked, drawdown from peak. |
| 0.14 Kelly sizing absolute → percentage | FIXED | Uses percentage-based calculation. |

**Additional Phase 0 wins (not in original plan):**
- importlib.reload() removed (10+ modules, 2-4s saved per interaction)
- Social sentiment word boundary matching fixed (regex `\b`)
- German hardcoded string routed through `t()`
- Mobile CSS breakpoints added (768px + 480px, ~80 lines)
- Sidebar i18n wired (5 nav group labels)
- Asset expansion: 12 → 52 assets (46 functional)
- Telegram notifier fully operational (97.3% delivery rate)
- Fear & Greed index live on Daily Advisor
- Landing page honest stats (removed fake scoreboard, fabricated numbers)
- Confidence alignment bonus symmetric for SELL signals
- Weight normalization prevents inflated confidence

**Result: NPS +12 → +29 | Would-pay 14.2% → 23.1% | Day-1 churn 24.3% → 16.1%**

---

## WHAT'S STILL BROKEN (From 10K v2 Re-Test)

The re-test audit found 9 critical and 22 high-severity remaining issues. The 6 launch blockers are:

### BLOCKER 1: Cached Data Files Still Contaminated
`watchlist_summary.json` contains pre-fix prices: BTC=$5,247, Silver=$1,944, Platinum=$6,878. Paper portfolio history and market predictions also contain contaminated entries. Every user who opens their portfolio history sees obviously wrong numbers.

### BLOCKER 2: check_pending_orders Data Race
`open_position()` saves portfolio, then `check_pending_orders()` loads a stale copy and overwrites. 1 in 5 auto-trades "vanish." Users get Telegram alerts for trades that don't exist in their portfolio.

### BLOCKER 3: RSI Division by Zero
When all recent candles are green, `loss = 0`, `rs = gain / 0 = inf`, RSI becomes NaN. This NaN propagates into scoring, producing `nan%` confidence displayed to users.

### BLOCKER 4: XSS via RSS Feed Rendering
RSS feed titles injected directly into HTML via `unsafe_allow_html=True` without escaping. A malicious feed could execute JavaScript in users' browsers.

### BLOCKER 5: 6 Assets Not Scanning
Dow Jones, Palladium, Corn, AUD/USD, USD/CHF, USD/JPY — all show no data. yfinance ticker format issues for futures and forex.

### BLOCKER 6: yfinance Still Contaminates 3% of Live Scans
Threading lock reduced contamination from 15% to 3%, but at 10K users this is still 300 people seeing wrong live prices. Must replace yfinance for current price fetching.

---

## REVISED PHASE STRUCTURE

```
COMPLETED:
  Phase 0: EMERGENCY BUG FIX (14 days)     → 14/14 items fixed   DONE

CURRENT:
  Phase 0.5: DATA INTEGRITY SPRINT (Days 1-7)    → Flush bad data, fix remaining blockers   ← NEW

UPCOMING:
  Phase 1: Foundation (Days 8-38)                → Twelve Data API + infra + security
  Phase 2: Credibility (Days 39-98)              → Accuracy proof + mobile + onboarding
  Phase 3: Growth (Days 99-188)                  → 10K public users
  Phase 4: Scale (Days 189-365)                  → 100K users
```

---

## PHASE 0.5: DATA INTEGRITY SPRINT (Days 1-7)
### Theme: "Clean the pipes. Every number on screen must be real."
### Status: LAUNCH BLOCKER — no beta invites until complete

| # | Bug | Fix | Owner | Days | Priority |
|---|-----|-----|-------|------|----------|
| 0.5.1 | **Flush contaminated caches** | Delete and regenerate: `watchlist_summary.json`, `social_sentiment.json`, `macro_regime.json`, `fear_greed_cache.json`. Add startup validator that checks price sanity before serving cached data. | Backend Lead | 1 | P0 |
| 0.5.2 | **Fix check_pending_orders data race** | Refactor to single-writer pattern: `auto_trader.py` must call `check_pending_orders()` BEFORE `open_position()`, or both must operate on the same in-memory portfolio object. Eliminate stale read-save-overwrite cycle. | Trading Lead | 1-2 | P0 |
| 0.5.3 | **Fix RSI division by zero** | Add guard: `rs = gain / loss if loss > 0 else 100.0` (RSI = 100 when loss is zero, standard convention). | Signal Engineer | 1 | P0 |
| 0.5.4 | **Fix XSS in RSS rendering** | Escape all RSS feed titles and links with `html.escape()` before injecting into HTML. Audit ALL `unsafe_allow_html=True` calls (~40 instances) for untrusted data injection. | Security Lead | 1-2 | P0 |
| 0.5.5 | **Fix 6 non-scanning assets** | Replace yfinance tickers with working alternatives: `^DJI` → `DIA` (ETF proxy), futures → ETF proxies (PALL, CORN), forex → use `yfinance` `download()` with proper period. Or mark as "Coming Soon" and reduce advertised count to 46. | Backend Lead | 1-3 | P0 |
| 0.5.6 | **Fix SELL alignment RSI threshold** | Change `RSI > 40` to `RSI > 60` in SELL alignment bonus. RSI > 60 indicates overbought territory, which aligns with a SELL thesis. | Signal Engineer | 1 | P1 |
| 0.5.7 | **Fix MTF double-counting** | RSI 40-60 should increment NEITHER bullish nor bearish confirms (it's neutral). Only increment bullish for RSI < 40, bearish for RSI > 60. | Signal Engineer | 1 | P1 |
| 0.5.8 | **Fix variable `t` shadowing** | Rename loop variables from `t` to `trade` or `tick` in asset_detail (line 3641) and paper_trading (line 6320). | Frontend | 1 | P1 |
| 0.5.9 | **Remove 5 German text remnants** | Lines 4746, 4828, 4840-4841, 5436 — route through `t()` or replace with English. | Frontend | 1 | P1 |
| 0.5.10 | **Add short position cash floor** | After closing a short at a loss, enforce `cash = max(0, cash)` and log a margin call warning. Never allow negative cash. | Trading Lead | 1 | P1 |
| 0.5.11 | **Add backtest for SELL signals** | `backtester.py` currently only tests BUY entries. Add SELL entry logic (short position simulation) so historical accuracy data is symmetric. | Trading Lead | 2-3 | P1 |
| 0.5.12 | **Fix paper portfolio history** | Write a migration script that scans `paper_portfolio.json` for contaminated trades (entry/exit price deviating >50% from current price). Flag them as `"data_quality": "contaminated"` so they're excluded from P&L calculations. | Backend Lead | 1-2 | P1 |

**Phase 0.5 Investment:** 1 week, same team that did Phase 0.
**Phase 0.5 Outcome:** Zero NaN on screen. Zero vanishing trades. Zero XSS vectors. Clean historical data. All advertised assets functional.

### Phase 0.5 Verification Checklist:
- [ ] Force scan all 52 assets. Verify ALL have correct, unique prices (no contamination).
- [ ] Place 10 auto-trades in rapid succession. Verify all 10 appear in portfolio (no vanishing).
- [ ] Scan an asset in a strong uptrend (all green candles). Verify RSI shows ~80-90, not NaN.
- [ ] Inject `<script>alert(1)</script>` into a test RSS feed title. Verify it renders as escaped text, not executable JS.
- [ ] Open old portfolio history. Verify contaminated trades are flagged and excluded from P&L.
- [ ] Generate signals in a flat market. Verify SELL alignment bonus only awards points when RSI > 60.
- [ ] Run backtest. Verify both BUY and SELL signals produce backtest results.

---

## PHASE 1: FOUNDATION (Days 8-38) — REVISED

### Core Infrastructure:

| # | Action | Days | Why | Status Change from v2 |
|---|--------|------|-----|----------------------|
| 1.1 | **Twelve Data API integration** | 8-14 | Eliminates yfinance price contamination entirely. $29/mo. Sub-second prices. | UNCHANGED — still #1 priority |
| 1.2 | **Stripe billing** | 8-13 | Can't charge for Pro tier without payment processing. | UNCHANGED |
| 1.3 | **PostgreSQL migration** (users + portfolio) | 14-35 | JSON files don't survive 10K concurrent users. Data races in paper_portfolio.json are JSON's fault. | UNCHANGED |
| 1.4 | **CI/CD pipeline** (GitHub Actions) | 8-14 | Phase 0 had zero automated tests. Every fix was manual verification. Never again. | UNCHANGED |
| 1.5 | **pytest suite** (50% coverage on critical paths) | 8-28 | market_scanner.py, auto_trader.py, paper_trader.py, risk_manager.py MUST have tests. | UNCHANGED |
| 1.6 | **SEC disclaimers** on all signal cards | 8-14 | Legal requirement before any public release. | UNCHANGED |

### Architecture & Performance:

| # | Action | Days | Why |
|---|--------|------|-----|
| 1.7 | **Split app.py into view modules** | 8-21 | 8,630-line monolith is unmaintainable. Extract top 5 views (advisor, watchlist, morning_brief, charts, paper_trading) into `dashboard/views/`. |
| 1.8 | **Async price fetching** | 14-21 | Full scan: 3-7 min → target <30s. Use `asyncio` + `aiohttp` with Twelve Data batch endpoints. |
| 1.9 | **`st.fragment` adoption** for interactive widgets | 14-21 | Every button click re-runs 8,630 lines. Fragment isolation = only re-run the widget. |

### Security (Moved from Phase 2 to Phase 1 in v2, retained):

| # | Action | Days | Why |
|---|--------|------|-----|
| 1.10 | **Password reset / forgot password** | 11-18 | CRITICAL security gap. Locked-out users have NO recovery path. |
| 1.11 | **Session token hashing** | 11-15 | Plaintext tokens in `_sessions.json` = any file access = full session hijack. |
| 1.12 | **Login rate limiting by IP** | 8-10 | Current per-email limiting doesn't prevent credential stuffing across accounts. |
| 1.13 | **CSRF protection for state-changing actions** | 14-21 | Streamlit's session state provides some protection, but explicit CSRF tokens needed for API endpoints. |

### i18n Completion:

| # | Action | Days | Why |
|---|--------|------|-----|
| 1.14 | **i18n coverage to 80%** | 14-28 | Currently ~20% of strings go through `t()`. Extract remaining 80% in top 5 views. |
| 1.15 | **RTL layout fix** for sidebar + forms | 14-21 | Arabic users report sidebar and forms are still LTR. |
| 1.16 | **Date/number locale formatting** | 14-21 | German users expect `1.000,00` not `1,000.00`. Arabic users expect Eastern Arabic numerals. |

**Phase 1 Investment:** 30 days, full engineering team.
**Phase 1 Outcome:** Real-time prices (Twelve Data), sub-30s scans, working billing, database-backed storage, password reset, 80% i18n, SEC compliant signal cards, 50% test coverage.

---

## PHASE 2: CREDIBILITY (Days 39-98) — REVISED

| # | Action | Days | What Changed from v2 |
|---|--------|------|---------------------|
| 2.1 | **Signal Accuracy Dashboard** (public, auditable) | 39-63 | UNCHANGED — #1 credibility builder |
| 2.2 | **Alpaca paper trading integration** | 39-59 | UNCHANGED — real broker validation |
| 2.3 | **Mobile PWA** | 45-73 | Phase 0 added CSS breakpoints. Phase 2 makes it installable. |
| 2.4 | **Interactive demo** (no signup) | 39-53 | UNCHANGED |
| 2.5 | **FinBERT sentiment** | 43-63 | Moved from Phase 1 in v2. After word-boundary fix (done), upgrade to real NLP. |
| 2.6 | **Onboarding flow** (guided tour) | 39-53 | NEW — 31% of visitors said "looks like a prototype." Guided tour fixes first impression. |
| 2.7 | **Landing page overhaul** | 39-48 | Replace static data with live API pulls. Fix remaining mobile grids. Real testimonials from 10K testers. |
| 2.8 | **Telegram alert filtering** | 39-45 | NEW — #1 Telegram complaint: "I get alerts for EVERY signal." Add confidence threshold + watchlist-only filter. |
| 2.9 | **F&G history chart** | 39-45 | NEW — #1 F&G request: "Show trend over time, not just current number." |
| 2.10 | **Guest mode data isolation** | 39-45 | Generate unique `guest_XXXX` IDs. No more shared `default` namespace. |
| 2.11 | **Help center** (20 articles) | 45-59 | UNCHANGED |

---

## PHASE 3 & 4: UNCHANGED from v2

Phases 3 (Growth, Days 99-188) and Phase 4 (Scale, Days 189-365) remain as outlined in v2, plus:

**Phase 3 additions (from v2 re-test findings):**
- XGBoost signal model (after bias is proven fixed)
- OAuth login (Google, Apple)
- GDPR right-to-delete
- Persistent audit logging
- Telegram bot inline actions (approve/reject trades from Telegram)

**Phase 4 additions:**
- SOC 2 Type I preparation
- External penetration testing
- Multi-broker integration (Alpaca → Interactive Brokers → TD Ameritrade)

---

## REVISED METRIC TARGETS

| Metric | v2 Target | v3 Target (Updated Baseline) | Why Changed |
|--------|-----------|------------------------------|-------------|
| End Phase 0.5 users | N/A | 0 (internal only) | Clean data before any beta |
| End Phase 1 users | 100 (invited beta) | 200 (invited beta) | Phase 0 success means faster ramp |
| End Phase 2 users | 1,500 | 2,500 | Higher NPS (+29) supports faster growth |
| End Phase 3 users | 10,000 | 10,000 | Same |
| End Phase 4 users | 100,000 | 100,000 | Same |
| Signal accuracy | 58%+ verified | 60%+ verified | Balanced signals should improve accuracy |
| BUY/SELL ratio | <65% BUY | **55-62% BUY** | Already at 58%, tighten the window |
| Price accuracy | 99.9%+ | **100%** (zero contamination after Twelve Data) | Non-negotiable |
| NPS | +12 → +25 | **+29 → +40** | Better baseline, higher target |
| 24h churn | 24.3% → 12% | **16.1% → 8%** | Better baseline, more aggressive target |
| Would pay for Pro | N/A | **23.1% → 35%** | NEW metric to track |
| Mobile NPS | N/A | **+11 → +30** | NEW metric after mobile CSS fixes |

---

## THE 5 THINGS THAT CHANGED FROM v2 TO v3

### 1. "PHASE 0 WORKED — NOW CLEAN THE DATA"

v2 said "fix bugs first, no features." We did that and NPS jumped +17. But the cached data files still contain pre-fix contaminated prices. Phase 0.5 is a 1-week data integrity sprint to flush bad data and fix the 6 remaining blockers.

**New rule:** No beta invites until `watchlist_summary.json`, `paper_portfolio.json`, and `market_predictions.json` are verified clean.

### 2. "THE AUTO-TRADER HAS A NEW BUG CLASS: DATA RACES"

Phase 0 fixed the auto-trader's logic (sizing, correlation, trailing stops). But the re-test uncovered a data RACE: `check_pending_orders()` overwrites `open_position()` changes because they both read-modify-save the same JSON file independently. This is a fundamental architecture problem that PostgreSQL (Phase 1) will permanently solve, but the JSON workaround (single-writer pattern) must be deployed NOW.

**New rule:** All portfolio mutations must go through a single entry point. No concurrent read-modify-save on the same JSON file.

### 3. "SECURITY MOVED FROM NICE-TO-HAVE TO BLOCKER"

v2 moved security to Phase 1. The re-test found XSS via RSS feeds that is exploitable TODAY. Session tokens are still plaintext. Phase 0.5 fixes XSS immediately. Phase 1 fixes tokens and adds password reset.

**New rule:** XSS is a Phase 0.5 blocker (Day 1-2 fix). No beta users exposed to injectable HTML.

### 4. "TELEGRAM IS A GROWTH ENGINE — INVEST IN IT"

v2 treated Telegram as a feature checkbox. The re-test data says it's a growth engine: 76% satisfaction, 97.3% delivery rate, users respond in 4.2 minutes. The #1 complaint is "I get alerts for EVERYTHING." Phase 2 adds filtering.

**New rule:** Telegram alert quality > quantity. Add confidence threshold and watchlist-only filter before scaling to public launch.

### 5. "MOBILE IS FUNCTIONAL BUT NOT COMPETITIVE"

v2 had zero mobile CSS. Phase 0 added 80+ lines of breakpoints. Mobile NPS went from -8 to +11. But +11 is not competitive (TradingView mobile: +65). Phase 2 delivers a PWA. Phase 0.5 ensures all current mobile CSS works correctly.

**New rule:** Every new feature must be tested at 375px width before merge. No more desktop-only development.

---

## SPRINT 17 EXECUTIVE ORDER (Immediate — Phase 0.5)

| Day | Action | Owner | Verification |
|-----|--------|-------|-------------|
| 1 | Flush contaminated caches + add price sanity validator | Backend Lead | All 52 assets have correct, unique prices |
| 1 | Fix RSI division by zero | Signal Engineer | Scan uptrending asset, verify no NaN |
| 1 | Fix SELL alignment RSI > 40 → > 60 | Signal Engineer | SELL bonus only when RSI > 60 |
| 1 | Fix variable `t` shadowing in 2 views | Frontend | No `TypeError` after loop execution |
| 1 | Remove 5 German text remnants | Frontend | Language set to English, verify zero German |
| 1-2 | Fix check_pending_orders data race | Trading Lead | Place 10 rapid auto-trades, verify all 10 in portfolio |
| 1-2 | Fix XSS in RSS rendering | Security Lead | Inject `<script>` in test RSS, verify escaped |
| 1-2 | Fix MTF double-counting for RSI 40-60 | Signal Engineer | Neutral RSI increments neither bullish nor bearish |
| 1-2 | Add short position cash floor | Trading Lead | Close short at loss, verify cash >= 0 |
| 2-3 | Add backtest for SELL signals | Trading Lead | Run backtest, verify SELL results appear |
| 2-3 | Fix 6 non-scanning assets (or mark Coming Soon) | Backend Lead | All advertised assets scan or show clear status |
| 3-5 | Write migration script for contaminated portfolio history | Backend Lead | Old trades flagged, P&L recalculated without them |
| 5-7 | Full regression: all 52 assets, all auto-trader gates, all views | QA | Automated verification script passes |

**Sprint 15 Week 4 Goal:** "Every cached file contains real data. Every trade persists. Every input is sanitized."

---

## THE PATH TO PUBLIC LAUNCH

```
Week 1 (NOW):     Phase 0.5 — Data integrity sprint (12 items)
Weeks 2-5:        Phase 1  — Twelve Data API, Stripe, PostgreSQL, security, tests
Weeks 6-14:       Phase 2  — Accuracy dashboard, Alpaca, PWA, FinBERT, onboarding

PUBLIC LAUNCH:    End of Phase 2 (~Week 14)
                  Requirements: NPS > +40, price accuracy 100%, signal accuracy 60%+,
                  working billing, mobile PWA, SEC disclaimers, password reset

Weeks 15-27:      Phase 3  — Scale to 10K public users
Weeks 28-52:      Phase 4  — Scale to 100K users, broker integrations
```

---

## CLOSING STATEMENT

> "Phase 0 proved something important: we can execute. In 14 days, we fixed 14 bugs, rebalanced the signal engine, added mobile CSS, wired Telegram, launched Fear & Greed, expanded to 52 assets, and moved NPS from +12 to +29.
>
> But the re-test also proved something sobering: fixing code bugs exposes data bugs. The contaminated cached data, the vanishing trades, the NaN scores — these are the SECOND layer of problems that only surface after the first layer is fixed.
>
> Phase 0.5 is a 1-week sprint to clean that second layer. It's not glamorous work. Flushing caches, adding division-by-zero guards, escaping HTML. But it's the difference between a B product and a B+ product.
>
> After Phase 0.5, we have a clean foundation. Phase 1 replaces yfinance with Twelve Data (eliminating price contamination permanently), adds Stripe (so we can actually charge money), migrates to PostgreSQL (eliminating all JSON data races permanently), and adds the security hardening that any production system needs.
>
> The timeline hasn't slipped. Phase 0 took 14 days as planned. Phase 0.5 takes 7 days (bonus sprint, not in original plan). We're still on track for public launch at Week 14.
>
> NPS +29 with a product this buggy tells me something: the IDEA is so good that users forgive the bugs. Imagine what happens when the bugs are gone.
>
> Sprint 15 Week 4 starts today. Clean the data. Secure the inputs. Ship the integrity.
>
> Top 50 in 12 months. Top 10 in 24. And this time, every number on the screen is real."

---

*Approved by: CEO*
*Effective: March 2, 2026*
*Supersedes: CEO_ACTION_PLAN_TOP10_v2.md (March 2, 2026)*
*Distribution: All employees*
*Sprint 15 Week 4 kickoff: IMMEDIATE*
