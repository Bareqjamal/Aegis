# PROJECT AEGIS — CEO ACTION PLAN v2
# Critical Update After 10,000-User Deep Test
**Date:** March 2, 2026 | **Supersedes:** CEO_ACTION_PLAN_TOP10.md (March 1, 2026)
**Status:** EMERGENCY REVISION — 27 critical bugs found

---

## WHAT CHANGED SINCE v1

The v1 plan was written based on the 1,000-user feedback report, which captured *user opinions*. The 10,000-user deep test included a **full code audit** that discovered problems far worse than users reported:

| Discovery | v1 Assumption | v2 Reality |
|-----------|---------------|------------|
| Price accuracy | "Fixed in Sprint 15" | **STILL BROKEN.** 28.5% of users saw wrong prices. BTC/ETH/Gold contaminated. |
| Position sizing | "Kelly Criterion works" | **COMPLETELY BROKEN.** Wrong dict key → every trade = 50% of max. |
| Signal fairness | "Unbiased scoring" | **STRUCTURAL BULLISH BIAS.** Max bearish = -35, max bullish = +100. 89% of signals are BUY. |
| Settings page | "User-configurable" | **PLACEBO.** TA params, refresh intervals, all hardcoded. Settings are saved but never read. |
| Asset coverage | "48 assets working" | **11 ASSETS BROKEN.** Zero scan data for 23% of watchlist. |
| Correlation guard | "Prevents overexposure" | **NEVER FIRES.** Asset name mismatch → guard is dead code. |
| Security | "PBKDF2 passwords, good" | **SESSION TOKENS IN PLAINTEXT.** No password reset. No IP rate limiting. |

**v1 called us "B+ product on D infrastructure." v2 says: we are a C- product on D infrastructure with an A+ idea.**

The idea — signal intelligence with explanations — is still our moat. But the execution has critical bugs that will destroy trust faster than our explanations can build it.

---

## REVISED PHASE STRUCTURE

```
OLD (v1):
  Phase 1: Foundation (Days 1-30)    → Features + infra
  Phase 2: Credibility (Days 31-90)  → Accuracy + mobile
  Phase 3: Growth (Days 91-180)      → 10K users
  Phase 4: Scale (Days 181-365)      → 100K users

NEW (v2):
  Phase 0: EMERGENCY BUG FIX (Days 1-14)  → Fix 5 launch blockers   ← NEW
  Phase 1: Foundation (Days 15-45)         → Infra + real-time data
  Phase 2: Credibility (Days 46-105)       → Accuracy + mobile
  Phase 3: Growth (Days 106-195)           → 10K users
  Phase 4: Scale (Days 196-365)            → 100K users
```

**We CANNOT launch publicly until Phase 0 is complete.** The v1 plan assumed we could launch at Day 91. The v2 plan says we cannot launch until the 5 blockers are fixed (Day 14 minimum).

---

## PHASE 0: EMERGENCY BUG FIX SPRINT (Days 1-14)
### Theme: "No user should see wrong data"
### Status: LAUNCH BLOCKER — must complete before any public release

| # | Bug | Fix | Owner | Days | Priority |
|---|-----|-----|-------|------|----------|
| 0.1 | **Price contamination** — BTC/ETH/Gold getting each other's prices | Replace yfinance entirely with Twelve Data API for price fetching. Keep yfinance ONLY for historical OHLCV. Never use yfinance for current prices. | Backend Lead | 1-5 | P0 |
| 0.2 | **Position sizing broken** — `position_usd` key doesn't exist | Change `auto_trader.py` line 427: `sizing.get("position_usd"` → `sizing.get("usd_amount"`. One-line fix. | Trading Lead | 1 | P0 |
| 0.3 | **Bullish signal bias** — max bearish score is -35 vs +100 bullish | Rebalance scoring: death cross = -20, support distance penalty, symmetric RSI/MACD/BB scoring. Target: max bearish = -100. | Signal Engineer | 1-7 | P0 |
| 0.4 | **11 assets never scanned** — Dow Jones, LTC, NFLX, etc. | Run forced scan of all 48 assets. Add scan health monitoring: if an asset hasn't been scanned in 24h, flag it and retry. | Backend Lead | 1-3 | P0 |
| 0.5 | **Settings are placebo** — TA params and refresh hardcoded | Wire `TechnicalParams` into `market_scanner.py` lines 224-247. Wire `DashboardConfig` refresh into `app.py` line 1550-1553. Validate confidence weights sum to 1.0. | Full-stack | 3-7 | P0 |
| 0.6 | **Correlation guard dead** — asset name mismatch | Normalize all asset names to use the same format (the watchlist key). Update `auto_trader.py` correlation groups. | Trading Lead | 1-2 | P1 |
| 0.7 | **Sidebar equity wrong** — shows cash only, ignores positions | Call `paper_trader.get_portfolio_summary()` for sidebar equity display. | Frontend | 1 | P1 |
| 0.8 | **Alert badge same color** — HIGH and non-HIGH identical | Fix `app.py` line 3092: HIGH = `#f85149`, else = `#d29922`. Same at line 4138. | Frontend | 1 | P1 |
| 0.9 | **Watchlist daily % wrong** — compares to scan price, not yesterday close | Use yfinance daily change (like the Advisor view already does) instead of scan-to-live comparison. | Frontend | 1-2 | P1 |
| 0.10 | **Morning Brief vs Auto-Trader threshold mismatch** — 60% vs 65% | Align to 65% minimum for "BUY NOW" label in morning_brief.py. | Signal Engineer | 1 | P1 |
| 0.11 | **Trailing stop broken for shorts** — no logic exists | Add symmetric trailing stop logic for short positions in `risk_manager.py`. Write `highest_price` back to position data. | Trading Lead | 2-3 | P1 |
| 0.12 | **Limit orders don't reserve cash** — can overspend | Deduct cash when limit order is placed; refund if cancelled. | Trading Lead | 1-2 | P1 |
| 0.13 | **Drawdown check uses total return, not max drawdown** — misses 30% drops during profitable periods | Track peak equity and compute drawdown from peak, not from starting balance. | Trading Lead | 2-3 | P2 |
| 0.14 | **Kelly sizing uses absolute dollars, not percentages** — BTC gets 100x the fraction of Gold | Use `(target - price) / price` for percentage-based calculation. | Trading Lead | 1 | P2 |

**Phase 0 Investment:** 2 weeks, full engineering team focused on fixes only. ZERO new features.
**Phase 0 Outcome:** All 48 assets scan correctly with accurate prices, fair signal distribution, working risk management, and functional settings.

### Phase 0 Verification Checklist:
- [ ] Scan all 48 assets. Verify all 48 have unique, correct prices.
- [ ] Generate signals. Verify BUY/SELL distribution is 55-65% / 20-30% (not 89% / 4%).
- [ ] Place 10 auto-trades. Verify position sizes vary by risk calculation (not all 50%).
- [ ] Buy 3 correlated assets (AAPL, MSFT, NVDA). Verify correlation guard blocks the 3rd.
- [ ] Change RSI period in Settings. Run scan. Verify signal changes.
- [ ] Check sidebar equity with open positions. Verify it includes unrealized P&L.
- [ ] Verify all 11 missing assets now have scan data and charts.
- [ ] Compare Watchlist daily % with Advisor daily %. Must match.

---

## PHASE 1: FOUNDATION (Days 15-45) — REVISED

### What stayed from v1:
| # | Action | Days |
|---|--------|------|
| 1.1 | Twelve Data API (replaces yfinance for live prices) | 15-21 |
| 1.2 | Stripe billing integration | 15-20 |
| 1.3 | PostgreSQL migration (users + portfolio) | 21-42 |
| 1.4 | CI/CD pipeline (GitHub Actions) | 15-21 |
| 1.5 | pytest suite (50% coverage on critical paths) | 15-35 |
| 1.6 | SEC disclaimers on all signal cards | 15-21 |

### What's NEW in v2 (added from deep audit):

| # | Action | Days | Why Added |
|---|--------|------|-----------|
| 1.7 | **Split app.py into view modules** | 15-28 | 8,630-line monolith is #1 developer productivity killer. Every engineer survey says this. |
| 1.8 | **Remove `importlib.reload()` calls** | 15-16 | Lines 66-74 reload 10+ modules on every Streamlit rerun, defeating all caching, causing 3-5s latency per interaction. |
| 1.9 | **Password reset / forgot password** | 18-25 | CRITICAL security gap — locked-out users have NO recovery path. |
| 1.10 | **Login rate limiting by IP, not just email** | 15-17 | Current per-email limiting doesn't prevent credential stuffing attacks across accounts. |
| 1.11 | **Session token hashing** | 18-22 | Tokens are stored as plaintext in `_sessions.json`. Must hash tokens at rest. |
| 1.12 | **Fix social sentiment word boundary matching** | 15-17 | `social_sentiment.py` uses `if word in text` substring matching. "up" matches "setup", "update". Produces massive false positives. Must use regex `\b` like `news_researcher.py` does. |
| 1.13 | **Fix German hardcoded strings in app.py** | 15-16 | Line 4702 shows German text to ALL users. Line 7 of scanner generates German reasoning for English users. Route through `t()`. |
| 1.14 | **Add error boundary for views** | 15-18 | Any exception shows raw Python traceback to users. Wrap all views in try/except with graceful "Something went wrong" UI. |
| 1.15 | **Fix RSS feed duplicate** | 15 | Two CNBC feeds use identical URLs, doubling processing for no gain. |

### What was REMOVED from v1:

| Action | Why Removed |
|--------|-------------|
| FinBERT sentiment (was v1 Phase 1) | Moved to Phase 2. Fix word-boundary matching first (1.12). FinBERT is nice-to-have after fundamentals work. |
| Tier restructure (was v1 Phase 1) | Moved to Phase 1 still, but AFTER Stripe. Can't restructure what we can't bill for. |

---

## PHASE 2: CREDIBILITY (Days 46-105) — REVISED

### What stayed from v1:
| # | Action | Days |
|---|--------|------|
| 2.1 | Signal Accuracy Dashboard (public) | 46-70 |
| 2.2 | Alpaca paper trading integration | 46-66 |
| 2.4 | Mobile PWA | 52-80 |
| 2.5 | Interactive demo (no signup) | 46-60 |
| 2.6 | Chart drawing tools | 60-80 |
| 2.7 | Onboarding flow | 46-60 |
| 2.8 | Help center (20 articles) | 46-66 |

### What's NEW in v2:

| # | Action | Days | Why Added |
|---|--------|------|-----------|
| 2.9 | **FinBERT sentiment** (moved from Phase 1) | 50-70 | After word-boundary fix (1.12), upgrade to real NLP. +35% accuracy. |
| 2.10 | **Multi-timeframe signal confluence** | 60-80 | 18% of users requested. Fix overlapping boolean logic in `market_scanner.py` lines 359-366 (bullish AND bearish both increment from same RSI). |
| 2.11 | **Landing page overhaul** | 46-55 | Replace static mockup data with live API pulls. Fix OG image. Fix mobile grids (4-col and 5-col). Remove Tailwind CDN for production build. Add real testimonials (from 10K test users). |
| 2.12 | **Watchlist page price cache indicator** | 46-50 | When showing 24h-old cached prices (line 1060), display "Cached from X hours ago" warning. Users must know when data is stale. |
| 2.13 | **Guest mode data isolation** | 46-52 | Generate unique `guest_XXXX` user IDs instead of shared `default`. Prevent data races. |
| 2.14 | **No-op button fix** | 46-48 | "Details" button on signal cards does nothing if no research file exists (line 3216). Show "No research available" toast instead. |
| 2.15 | **Config validation + per-user isolation** | 52-60 | Settings override must validate bounds (no negative confidence, weights sum to 1.0). Use per-user session state, not global class attributes. |

### What was REMOVED from v2:

| Action | Why |
|--------|-----|
| XGBoost signal model (was v1 Phase 2) | Moved to Phase 3. Must fix scoring bias first. ML on top of biased rules = biased ML. |

---

## PHASE 3 & 4: UNCHANGED from v1

Phases 3 (Growth, Days 106-195) and Phase 4 (Scale, Days 196-365) remain as outlined in v1, with these additions:

**Phase 3 additions:**
- XGBoost signal model (moved from Phase 2)
- OAuth login (Google, Apple) — 23% of users want this
- GDPR right-to-delete — required before EU marketing push
- Persistent audit logging — required before live trading

**Phase 4 additions:**
- SOC 2 Type I preparation — mandatory before institutional clients
- Penetration testing by external firm — before broker integration goes live

---

## REVISED METRIC TARGETS

| Metric | v1 Target | v2 Target | Why Changed |
|--------|-----------|-----------|-------------|
| End Phase 0 users | N/A | 0 (internal only) | NEW PHASE. No public launch until bugs fixed. |
| End Phase 1 users | 200 | 100 (invited beta) | Tighter control during foundation work |
| End Phase 2 users | 2,000 | 1,500 | Delayed by 2-week Phase 0 |
| End Phase 3 users | 10,000 | 10,000 | Same — make up time with better product |
| End Phase 4 users | 100,000 | 100,000 | Same |
| Signal accuracy | "Tracking" | **58%+ verified** | Must PROVE it before public launch |
| BUY/SELL ratio | Not measured | **<65% BUY** in any 30-day window | Prevents bias perception |
| Price accuracy | "Fixed" | **99.9%+ correct** (zero contamination) | Non-negotiable after 10K findings |
| NPS | +18 → +30 → +40 | +12 → **+25** → +40 | Realistic from current +12 baseline |
| 24h churn | 19% → 10% | 24.3% → **12%** → 5% | Worse baseline at 10K scale |

---

## THE 5 THINGS THAT CHANGED IN THE CEO PLAN

### 1. "FIX BUGS" COMES BEFORE "ADD FEATURES"

v1 started with Twelve Data, Stripe, FinBERT. v2 starts with fixing price contamination, signal bias, and dead code. You cannot add real-time data to a system that mixes up which asset has which price.

**New rule:** For the next 14 days, the only allowed code changes are BUG FIXES. Zero new features. Zero new views. Zero new integrations. Fix what's broken.

### 2. THE SIGNAL ENGINE NEEDS SURGERY, NOT JUST ML

v1 assumed the rule-based engine was fair and ML would make it better. The audit found the engine has a structural +100/-35 asymmetry that makes 89% of signals BUY. No amount of ML fixes a fundamentally biased scoring system.

**New rule:** Before any ML model is trained, the rule-based scoring must produce a balanced signal distribution (55-65% BUY, 20-30% SELL, 10-20% NEUTRAL in a sideways market).

### 3. THE AUTO-TRADER IS NOT PRODUCTION-GRADE

v1 assumed the 12-gate auto-trader was our competitive moat and ready for Alpaca. The audit found:
- Position sizing uses wrong dict key (always 50% of max)
- Correlation guard uses wrong asset names (never fires)
- Drawdown check uses total return, not peak drawdown
- Kelly sizing uses absolute dollars, not percentages

**New rule:** The auto-trader gets a full code review and test suite BEFORE any broker integration. We cannot connect a broken decision engine to real money.

### 4. THE SETTINGS PAGE IS A LIABILITY

v1 assumed settings work. They don't. TA parameters, refresh intervals, and confidence weights are all either hardcoded or unvalidated. Users who customize their experience and see NO change will leave.

**New rule:** Every setting must have a corresponding code path that reads it. If a setting has no code path, remove it from the UI. "Fewer working features" > "many broken features."

### 5. SECURITY IS A PHASE 0 ISSUE, NOT A PHASE 2 ISSUE

v1 deferred security to Phase 1-2. The audit found plaintext session tokens, no password reset, email-only rate limiting, and skippable email verification. These are not "nice-to-haves" — they are legal liabilities.

**New rule:** Login rate limiting (by IP), password reset, and session token hashing move to Phase 1 (Days 15-25). No public launch without these.

---

## SPRINT 15 WEEK 3 EXECUTIVE ORDER (March 2-16, 2026)

**Sprint 15 Week 3 = Phase 0 = EMERGENCY BUG FIX**

| Day | Action | Owner | Verification |
|-----|--------|-------|-------------|
| 1 | Fix `position_usd` → `usd_amount` in auto_trader.py | Trading Lead | Place 5 auto-trades, verify sizes vary |
| 1 | Fix alert badge color (HIGH = red) | Frontend | Visual check |
| 1 | Fix duplicate CNBC RSS feed | Backend | Feed count check |
| 1-2 | Fix correlation group asset names | Trading Lead | Buy 3 tech stocks, verify 3rd blocked |
| 1-2 | Fix sidebar equity to include positions | Frontend | Open position + verify sidebar total |
| 1-2 | Fix watchlist daily % to use real daily change | Frontend | Compare Advisor vs Watchlist percentages |
| 1-2 | Fix Morning Brief threshold 60% → 65% | Signal Engineer | Compare brief labels vs auto-trader actions |
| 1-3 | Force scan all 48 assets + scan health monitor | Backend | All 48 in watchlist_summary.json |
| 1-5 | Rebalance signal scoring (symmetric -100 to +100) | Signal Engineer | Generate signals in flat market, verify <65% BUY |
| 2-3 | Fix trailing stop for short positions | Trading Lead | Open short, price drops, verify trail ratchets |
| 2-3 | Fix limit order cash reservation | Trading Lead | Place limit > cash, verify rejection |
| 3-5 | Fix drawdown from peak, not inception | Trading Lead | Simulate +50% then -30%, verify circuit breaker |
| 3-5 | Fix Kelly sizing to use percentages | Trading Lead | Compare Kelly fraction for BTC vs Gold |
| 3-7 | Wire TechnicalParams into market_scanner (RSI, SMA, MACD, BB) | Signal Engineer | Change RSI in settings, verify signal changes |
| 3-7 | Wire DashboardConfig refresh into app.py autorefresh | Frontend | Change refresh in settings, verify timing changes |
| 3-7 | Add confidence weight normalization | Signal Engineer | Set weights summing to 2.0, verify normalized to 1.0 |
| 5-7 | Fix social sentiment word boundary matching | Data Engineer | "setup" should NOT match "up" keyword |
| 5-7 | Fix German hardcoded strings (app.py line 4702, scanner reasoning) | Frontend | Switch to English, verify no German text |
| 7-10 | Add view-level error boundary (try/except with graceful UI) | Frontend | Cause an exception, verify no traceback shown |
| 7-10 | Remove importlib.reload() calls | Backend | Measure page load time, verify <3s improvement |
| 10-14 | Full regression scan: all 48 assets, verify all data integrity | QA | Automated verification script |

**Sprint 15 Week 3 Goal:** "Every number on the screen is correct. Every button does what it says. Every setting takes effect."

---

## WHAT THE CEO PLAN v1 GOT RIGHT (unchanged)

1. **The thesis:** "Tell me what to trade, tell me WHY, and prove you're right." — STILL CORRECT.
2. **The positioning:** "Signal Intelligence Platform" — STILL CORRECT.
3. **The moat:** Signal explanations + multi-source sentiment + auto-trader transparency — STILL CORRECT.
4. **The wedge:** Enter top-10 via intelligence, not charts — STILL CORRECT.
5. **The target personas:** Swing traders (NPS +28) and beginners (NPS +31) — CONFIRMED by 10K data.
6. **Twelve Data API:** $29/mo removes #1 user complaint — STILL CRITICAL.
7. **The 4-phase structure:** Foundation → Credibility → Growth → Scale — STILL RIGHT, just needs Phase 0 prepended.

**The vision was never wrong. The execution assessment was too optimistic. v2 fixes that.**

---

## CLOSING STATEMENT

> "The 1,000-user test told us users love our intelligence. The 10,000-user test told us our intelligence is built on a foundation with cracks.
>
> 28.5% of users saw wrong prices. Our auto-trader ignores its own risk calculations. Our signal engine is a BUY-everything machine. Our settings page is a placebo. 11 of our 48 assets don't work.
>
> None of these problems are hard to fix. The position sizing bug is a one-word change. The alert color bug is literally changing one hex code. The signal bias needs a week of rebalancing. The missing assets need a forced scan.
>
> But they must be fixed BEFORE we go public. One viral tweet showing BTC at $1,944 on our platform and we're dead. One Reddit post showing 89% of our signals are BUY and we're a joke.
>
> Phase 0 takes 14 days. It pushes our public launch by 2 weeks. Those 2 weeks buy us credibility that takes years to rebuild if lost.
>
> The plan is still the same: be the smartest, most transparent signal platform in the market. But smart means our data is right. Transparent means our scoring is fair. And platform means our settings actually work.
>
> Sprint 15 Week 3 starts today. Bug fixes only. No new features. Fix the foundation, then we build the future.
>
> Top 50 in 12 months. Top 10 in 24. But only if Day 1 users see correct prices."

---

*Approved by: CEO*
*Effective: March 2, 2026*
*Supersedes: CEO_ACTION_PLAN_TOP10.md (March 1, 2026)*
*Distribution: All employees*
*Sprint 15 Week 3 kickoff: IMMEDIATE*
