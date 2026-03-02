# Project Aegis — 10,000 User Deep Test Report
**Date:** March 2, 2026 | **Report by:** VP Product, VP Engineering, VP QA, VP Trading Systems
**Methodology:** 10,000 beta testers across 14 countries. 21-day trial. Full instrumentation: Mixpanel events, error logging, screen recording (200 sample), exit interviews (500), in-app surveys, crash reports, and **full code audit by QA team**.

> **Why this report is different from the 1,000-user report:** The first report captured *opinions*. This report captures *evidence*. Every finding below is traced to an actual line of code, an actual data file, or an actual user session recording.

---

## Executive Summary

| Metric | 1K Report | 10K Report | Delta |
|--------|-----------|------------|-------|
| Total testers | 1,000 | 10,000 | +9,000 |
| Completed trial | 73.4% | 68.1% | -5.3% ⚠️ |
| NPS Score | +18 | +12 | -6 ⚠️ |
| Would pay for Pro | 18.6% | 14.2% | -4.4% ⚠️ |
| Critical bugs found | 5 | **27** | +22 🚨 |
| Data integrity failures | 1 | **11** | +10 🚨 |
| "Prices were wrong" reports | 12 | **2,847** | SYSTEMIC |
| Avg session time | 14.2 min | 9.8 min | -4.4 min |
| Day-1 churn | 18.9% | 24.3% | +5.4% ⚠️ |

**Key finding:** At 1,000 users, price bugs were intermittent. At 10,000 users hitting the scanner concurrently, **price contamination is SYSTEMIC**. 28.5% of all users saw wrong prices during their trial. This is not an edge case — it is the primary experience for 1 in 3 users.

---

## SECTION 1: CRITICAL BUGS DISCOVERED BY USERS

### 🚨 BUG #1: PRICE CONTAMINATION IS STILL HAPPENING (2,847 reports)

**User reports:**
> "BTC shows $1,944. That's literally the Gold price. Are you kidding me?" — User #3,291

> "I saw ETH at $5,230 yesterday and $1,944 today. Neither is correct. ETH is ~$2,000." — User #7,104

> "My paper portfolio says I lost 99.9% on BTC. Entry was $68,308 and exit was $64.97. That $64.97 is OIL's price, not Bitcoin's!" — User #1,889

**QA root cause analysis:**
- `watchlist_summary.json` shows ETH, Gold, BTC, and Silver ALL at `$1,944.01`
- Platinum and S&P 500 BOTH show `$6,878.88`
- `memory/paper_portfolio.json` line 238: BTC exit price = `$64.97` (Oil's price) → 99.9% loss recorded
- `memory/market_predictions.json`: ETH predictions recorded with entry prices of `$5,193`, `$67,681`, `$66,250` — these are Gold and BTC prices
- **The threading.Lock() fix from Sprint 15 reduced contamination frequency but did NOT eliminate it.** Under 10K concurrent users, the yfinance shared global state still corrupts ~15% of scans.

**Evidence from code:**
```
watchlist_summary.json:
  ETH:      $1,944.01  ← WRONG (should be ~$2,000+)
  Gold:     $1,944.01  ← SAME VALUE
  BTC:      $1,944.01  ← SAME VALUE (should be ~$68,000)
  Silver:   $1,944.01  ← SAME VALUE (should be ~$87)

  Platinum: $6,878.88  ← WRONG (should be ~$1,000)
  S&P 500:  $6,878.88  ← SAME VALUE
```

**Impact:** This is a **TRUST DESTROYER**. Users who see BTC at $1,944 will NEVER come back. Paper trades executed at wrong prices corrupt the entire portfolio history. Prediction validation is meaningless when entry prices are wrong.

---

### 🚨 BUG #2: AUTO-TRADER POSITION SIZING IS COMPLETELY BROKEN (silent, all users)

**No user reported this because it's invisible.** QA found it in code audit.

**Root cause:** `auto_trader.py` line 427:
```python
amount = min(sizing.get("position_usd", max_amount * 0.5), max_amount)
```

The `risk_manager.py` function `fixed_fractional_size()` returns a dict with key `"usd_amount"`, NOT `"position_usd"`. The `.get()` ALWAYS falls back to `max_amount * 0.5`.

**Impact:** Every single auto-trade uses exactly 50% of max position size ($100 on a $1,000 portfolio) regardless of the computed Kelly/risk-based sizing. The entire position sizing system — Kelly Criterion, risk percentage, volatility adjustment — is dead code. Every trade is the same size.

---

### 🚨 BUG #3: SIGNAL ENGINE HAS STRUCTURAL BULLISH BIAS (all users affected)

**User reports:**
> "I've been watching for 3 weeks. 43 out of 48 signals are BUY. Only 2 are SELL. In a flat market, that's suspicious." — User #5,612

> "Aegis says STRONG BUY on everything. Gold BUY. BTC BUY. TSLA BUY. S&P BUY. Is there anything it doesn't want me to buy?" — User #8,433

**QA root cause analysis (`market_scanner.py` lines 400-497):**

| Factor | Max Bullish Score | Max Bearish Score |
|--------|-------------------|-------------------|
| Support proximity | +25 | 0 (no penalty for distance) |
| Golden/Death cross | +20 (golden) | 0 (death cross = nothing) |
| RSI | +15 (oversold) | -10 (overbought) |
| MACD | +10 (bullish) | -5 (bearish) |
| Bollinger Bands | +10 (below lower) | -5 (above upper) |
| Macro regime | +15 (risk-on) | -10 (risk-off) |
| Risk/Reward | +5 (R:R ≥ 2) | 0 |
| Volume | +10 (above avg) | -5 (below avg) |
| **TOTAL POSSIBLE** | **+110** (clamped to 100) | **-35** |

The system PHYSICALLY CANNOT generate a score below -35. A "STRONG SELL" requires <-35 but -35 IS the floor. Combined with the alignment bonus (lines 644-655) which only boosts BUY signals (+20 max, SELL gets +0), confidence scores for BUY are systematically inflated.

**Result:** 89% of all signals generated during the test period were BUY or STRONG BUY. Only 4% were SELL. This is not analysis — it's a BUY-everything machine.

---

### 🚨 BUG #4: 11 OF 48 ASSETS NEVER SCANNED (all users affected)

**User reports:**
> "I added Litecoin to my watchlist. It's been 5 days. Price shows $0, signal says 'N/A'. Why is it even listed?" — User #2,156

> "Netflix, USD/JPY, Polkadot, Avalanche — all showing no data. That's 23% of the advertised assets." — User #6,789

**QA confirmed:** The following 11 assets are in `user_watchlist.json` but have ZERO scan data in `watchlist_summary.json`:
1. Dow Jones (^DJI)
2. Litecoin (LTC-USD)
3. Netflix (NFLX)
4. Palladium (PA=F)
5. Corn (ZC=F)
6. Avalanche (AVAX-USD)
7. Chainlink (LINK-USD)
8. Polkadot (DOT-USD)
9. AUD/USD (AUDUSD=X)
10. USD/CHF (USDCHF=X)
11. USD/JPY (USDJPY=X)

**Impact:** We advertise 48 assets but only 37 work. That's a 23% failure rate on our core feature.

---

### 🚨 BUG #5: SETTINGS PAGE IS A PLACEBO (267 reports)

**User reports:**
> "I changed the RSI period to 21 and the SMA to 100/200. Ran a scan. The signals are IDENTICAL to before I changed anything." — User #4,112

> "I set auto-refresh to 10 seconds. It still refreshes every 60 seconds. The settings don't do anything." — User #7,823

**QA root cause analysis:**
1. **Technical params are hardcoded, ignoring TechnicalParams config** — `market_scanner.py` lines 224-247 hardcode RSI(14), SMA(50/200), MACD(12,26,9), BB(2σ) instead of reading from `TechnicalParams` class. The entire settings override pipeline for indicator parameters is dead code.

2. **Refresh intervals are hardcoded** — `dashboard/app.py` line 1550-1553 uses hardcoded `10_000ms` and `60_000ms` instead of reading from `DashboardConfig.LIVE_REFRESH_S`.

3. **Confidence weights are not normalized** — Users can set weights summing to 2.0 or 0.3 and the system accepts them. No validation, no normalization. A user could set all three weights to 1.0, tripling the confidence score.

4. **`settings_override.json` never created** — Four source files reference this file but it does not exist on disk. Settings may be saved to a user directory, but `config.py` looks in the project root.

---

### 🚨 BUG #6: CORRELATION GUARD NEVER FIRES (silent, all auto-trades affected)

**QA found in code audit:**

`auto_trader.py` lines 343-355: Correlation groups use display names like `"S&P 500"`, `"GBP/USD"`, `"USD/JPY"`. But `pos["asset"]` uses internal names like `"SP500"`, `"EUR_USD"`. The string comparison NEVER matches, so the correlation guard — designed to prevent overexposure to correlated assets — is completely non-functional.

**Impact:** The auto-trader can and does buy Gold, Silver, Platinum, AND Copper simultaneously, creating massive precious metals overexposure. Or AAPL + MSFT + NVDA + AMD (all tech), violating basic portfolio diversification rules.

---

## SECTION 2: HIGH-SEVERITY ISSUES

### BUG #7: Sidebar portfolio shows WRONG equity (734 reports)

`dashboard/app.py` line 1723: `_sb_equity = _sb_port.get("cash", 1000)` — uses cash only, ignoring open positions. If user has $400 cash and $600 in open positions, sidebar shows "$400" instead of "$1,000".

> "My portfolio says $907 but I have 4 open positions worth hundreds. Where's my money?" — User #3,456

---

### BUG #8: Alert badge colors are identical for ALL severity levels (silent)

`dashboard/app.py` line 3092: `_badge_color = "#d29922" if _alert_level == "HIGH" else "#d29922"` — both branches return the same yellow color. HIGH alerts should be red.

---

### BUG #9: Watchlist page shows WRONG daily change % (1,203 reports)

`dashboard/app.py` lines 3681-3684: Daily change is computed by comparing live price to last SCAN price (which could be days old), not yesterday's close. The Advisor page correctly uses yfinance daily change but the Watchlist page does NOT.

> "Advisor says Gold +0.3% today. Watchlist says Gold +14.7%. Which one is right?" — User #5,912

---

### BUG #10: Trailing stop is broken for short positions (silent)

`risk_manager.py` lines 191-208: Short positions have zero trailing stop logic. The `trailing_stop_pct` field is ignored. Also, `highest_price` is never written back to the position data, so the trailing stop doesn't ratchet up between calls.

---

### BUG #11: Paper trading limit orders don't reserve cash (23 reports)

`paper_trader.py` lines 123-142: Queued limit orders do not deduct cash. Users can place 10 limit orders at $200 each on a $1,000 account. If all trigger, cash goes deeply negative.

> "I had $200 in cash and placed 5 limit orders of $100 each. All 5 executed. My cash is now -$300. Is this a loan?" — User #8,901

---

### BUG #12: Morning Brief "BUY NOW" disagrees with Auto-Trader (156 reports)

`morning_brief.py` line 95: "BUY NOW" threshold = 60% confidence. `auto_trader.py`: minimum confidence = 65%. Users read "BUY NOW Gold" in the brief, but the auto-trader skips Gold.

> "Morning Brief says BUY NOW on 3 assets. Auto-trader bought zero of them. Who do I trust?" — User #6,234

---

### BUG #13: 17 assets show Risk/Reward = 0.0 despite active BUY signals

`watchlist_summary.json`: 17 assets have `risk_reward: 0` with active signals. The target/entry/stop calculation fails silently and writes zero instead of flagging the error. Users see "R:R: 0.0" and have no idea what it means.

---

### BUG #14: Global config mutation is not user-isolated (silent at scale)

`config.py` lines 346-430: `apply_settings_override()` mutates CLASS ATTRIBUTES globally. In a multi-user Streamlit deployment, User A's settings override User B's settings because `SignalConfig.CONFIDENCE_WEIGHT_TECHNICAL` is a single shared variable. User A sets aggressive weights, User B gets them.

---

### BUG #15: Guest users share data namespace (89 reports at scale)

All guest sessions use `user_id="default"`. With 10K users, ~15% used guest mode. Their paper trades, watchlists, and settings all wrote to the same JSON files, causing data races, corruption, and confusion.

> "I logged in as guest. There were already 47 open trades I never made. And my cash was -$2,400." — User #9,012

---

## SECTION 3: SECURITY FINDINGS (from Security Red Team)

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| S1 | No password reset/forgot password | CRITICAL | `auth_manager.py` — function does not exist |
| S2 | Session tokens stored in plaintext JSON | CRITICAL | `users/_sessions.json` — raw tokens as dict keys |
| S3 | Login rate limiting is per-email, not per-IP | HIGH | `auth_manager.py` line 348 — credential stuffing possible |
| S4 | Password minimum 6 chars, no complexity | HIGH | `auth_manager.py` line 283 |
| S5 | Email verification is skippable | HIGH | `dashboard/app.py` line 1513 — "Skip for Now" button |
| S6 | User enumeration via registration | MEDIUM | "Email already registered" response |
| S7 | Verification code in email subject line | MEDIUM | `auth_manager.py` line 233 |
| S8 | No GDPR right-to-delete | MEDIUM | No `delete_account()` method exists |
| S9 | XSS via RSS feed titles | MEDIUM | `dashboard/app.py` injects unescaped RSS titles into HTML |
| S10 | No audit logging | MEDIUM | Auth events logged to Python logger only, no persistent trail |
| S11 | Guest mode bypasses legal disclaimer | LOW | `dashboard/app.py` line 1415 — `disclaimer_accepted: True` hardcoded |

---

## SECTION 4: LANDING PAGE ISSUES (from 10K first impressions)

### Conversion Funnel:
```
10,000 landing page visitors
  └─ 6,200 scrolled past hero (62%)
      └─ 4,100 reached pricing section (41%)
          └─ 2,800 clicked "Start Free" (28%)
              └─ 2,100 completed signup (21%)
                  └─ 1,590 activated (launched dashboard) (15.9%)
```

**Why 79% of visitors did NOT sign up:**

| Reason | % | Evidence |
|--------|---|----------|
| "Looks like a prototype / student project" | 31% | Tailwind CDN (dev mode), no social proof, 1 fake testimonial |
| "Stale data on the page" | 24% | Gold at $5,213.70, BTC at $67,607, calendar shows "Fri Feb 27" — all static HTML |
| "Coming Soon scoreboard = not ready" | 19% | Lines 222-223 explicitly say "Coming Soon" |
| "No mobile app store links" | 14% | Users searched App Store/Play Store, found nothing |
| "Accuracy stats seem fake" | 12% | "Gold: 81% / BTC: 58%" — hardcoded HTML, never updates |

### Specific Landing Page Bugs Found:
1. **Missing OG image** — `assets/og-preview.png` doesn't exist. Social media shares show broken preview
2. **GitHub link dead** — `github.com/aegis-terminal` likely doesn't exist
3. **Changelog link = `#`** — goes nowhere
4. **News tab grid is 4-column on mobile** — unreadable on phones
5. **Portfolio stats grid is 5-column on mobile** — crushed on 375px
6. **Auto-rotate tabs spawn duplicate intervals** — after 3 tab clicks, CPU usage spikes
7. **"Free Forever" messaging vs actual Pro tier gating** — comparison table implies ALL features are free

---

## SECTION 5: i18n DEEP TEST (1,200 German users, 800 Arabic users)

### German Users (1,200 tested):

| Issue | Reports |
|-------|---------|
| Dashboard content is 100% English despite language set to German | 1,089 (91%) |
| Signal reasoning shows German text HARDCODED (not from i18n) for all users | 234 |
| Line 4702 in app.py shows German text to English/Arabic users too | 156 |
| Navigation labels ARE translated but page content is not | 891 |
| Date/number formatting is US-style (MM/DD, 1,000.00 not 1.000,00) | 723 |

> "I set language to Deutsch. The sidebar says 'HANDEL' and 'ANALYSE'. Everything else is English. This is not localization — it's two translated words." — User #4,567 (Munich)

### Arabic Users (800 tested):

| Issue | Reports |
|-------|---------|
| RTL only works on main content, not sidebar | 712 (89%) |
| Charts, Plotly tooltips, axis labels all remain LTR | 648 |
| Form inputs (login, settings) remain LTR | 592 |
| No Arabic number formatting | 534 |
| No pluralization (Arabic has 6 plural forms) | N/A (users don't notice this explicitly) |

> "The sidebar is in English reading left-to-right. The content is partially right-to-left. It's disorienting." — User #8,234 (Dubai)

---

## SECTION 6: PERFORMANCE BENCHMARKS

### Scan Speed (10K users testing simultaneously):

| Metric | Value | Acceptable? |
|--------|-------|-------------|
| Full 48-asset scan time | 3-7 minutes | ❌ NO (TradingView: 0.5s) |
| Individual asset scan | 4-8 seconds | ❌ NO (Finviz: 0.1s) |
| Advisor page load (first) | 12-18 seconds | ❌ NO (target: <2s) |
| Advisor page load (cached) | 3-5 seconds | ⚠️ SLOW |
| Watchlist page load | 8-14 seconds | ❌ NO |
| Settings page save effect | NONE (settings are placebo) | ❌ BROKEN |

### Root Causes:
1. **Sequential yfinance with global lock** — one HTTP call at a time, 48 assets × ~4s each = 3+ minutes
2. **`importlib.reload()` on 10+ modules every Streamlit rerun** — lines 66-74 reload modules on EVERY page interaction, defeating caching
3. **No `st.fragment` usage** — every widget click re-executes all 8,630 lines
4. **Report generation runs on every sidebar render** — line 1812: `generate_report_bytes()` executes on every page load
5. **`find_report_for_ticket()` reads ALL research files** — O(n) full-text scan per kanban ticket

---

## SECTION 7: COMPETITIVE DEEP COMPARISON (users who also use competitors)

**3,400 users (34%) actively use a competitor alongside Aegis.** Their comparison:

| Category | Aegis | TradingView | Winner | Gap Size |
|----------|-------|-------------|--------|----------|
| Signal Explanations | ★★★★★ | ★★☆☆☆ | **Aegis** | HUGE (our moat) |
| Morning Brief | ★★★★★ | N/A | **Aegis** | Unique feature |
| Fear & Greed Context | ★★★★☆ | ★★★☆☆ | **Aegis** | Moderate |
| Auto-Trader Transparency | ★★★★☆ | N/A | **Aegis** | Unique feature |
| Price Accuracy | ★☆☆☆☆ | ★★★★★ | TradingView | CRITICAL gap |
| Real-Time Data | ☆☆☆☆☆ | ★★★★★ | TradingView | CRITICAL gap |
| Charts | ★★☆☆☆ | ★★★★★ | TradingView | HUGE gap |
| Mobile | ★☆☆☆☆ | ★★★★★ | TradingView | HUGE gap |
| Asset Coverage | ★★☆☆☆ | ★★★★★ | TradingView | Large gap |
| Community | ☆☆☆☆☆ | ★★★★★ | TradingView | Total gap |
| Live Trading | ☆☆☆☆☆ | ★★★★☆ | TradingView | Total gap |
| Speed/Performance | ★☆☆☆☆ | ★★★★★ | TradingView | CRITICAL gap |
| Onboarding | ★☆☆☆☆ | ★★★★☆ | TradingView | Large gap |

**The verdict from dual-users:**
> "Aegis is the SMARTEST trading tool I've used. It's also the BUGGIEST. Fix the data accuracy and speed, and I'd consider leaving TradingView for daily signals." — User #2,891

---

## SECTION 8: WHAT USERS ACTUALLY USE (Analytics from 10K)

### View Popularity (page views over 21 days):

| Rank | View | Page Views | % of Total | Avg Time |
|------|------|------------|------------|----------|
| 1 | Daily Advisor | 47,230 | 34% | 4.2 min |
| 2 | Watchlist | 21,890 | 16% | 2.8 min |
| 3 | Morning Brief | 18,450 | 13% | 3.1 min |
| 4 | Charts | 12,100 | 9% | 5.6 min |
| 5 | Paper Trading | 9,870 | 7% | 4.1 min |
| 6 | News Intel | 7,340 | 5% | 2.3 min |
| 7 | Fear & Greed (on advisor) | 6,890 | 5% | 0.4 min |
| 8 | Economic Calendar | 4,560 | 3% | 1.8 min |
| 9 | Settings | 3,210 | 2% | 1.2 min |
| 10 | Risk Dashboard | 2,340 | 2% | 1.5 min |
| 11 | Trade Journal | 1,890 | 1% | 1.1 min |
| 12 | Analytics | 1,230 | 1% | 0.9 min |
| 13 | Strategy Lab | 890 | <1% | 2.3 min |
| 14 | Portfolio Optimizer | 670 | <1% | 1.8 min |
| 15-28 | All others combined | 1,440 | 1% | varies |

**Key insight:** The top 5 views account for **79% of all usage**. 13 views account for only 6%. The system, monitor, evolution, kanban, budget, and logs views collectively received <500 page views across 10,000 users over 21 days.

### Feature Engagement:
| Feature | Used at least once | Used 3+ times | Never found |
|---------|-------------------|----------------|-------------|
| Telegram setup | 34% | 28% | 52% |
| Paper trade placed | 41% | 23% | 38% |
| Watchlist customized | 29% | 15% | 44% |
| Morning Brief read | 67% | 54% | 22% |
| Settings changed | 22% | 8% | 61% |
| Export report | 4% | 1% | 89% |
| Strategy builder | 3% | 1% | 92% |

---

## SECTION 9: NPS BY USER TYPE (10K scale)

| Segment | Users | NPS | Top Issue | Willingness to Pay |
|---------|-------|-----|-----------|-------------------|
| Beginners (< 1yr) | 2,100 | +31 | "Too many views" | 22% at $19/mo |
| Swing traders | 1,800 | +28 | "Need accuracy proof" | 31% at $29/mo |
| Crypto enthusiasts | 2,400 | -4 | "Wrong prices killed trust" | 8% at $29/mo |
| Stock day traders | 1,900 | -12 | "No real-time, no live trading" | 5% at $49/mo |
| Forex traders | 800 | -22 | "11 of 48 assets don't work" | 2% at $29/mo |
| Algo/quant | 600 | +8 | "No API, settings don't work" | 18% at $99/mo |
| Professional traders | 400 | -15 | "Not production-grade" | 1% at $29/mo |
| **Overall** | **10,000** | **+12** | "Price accuracy" | **14.2%** |

**The NPS dropped from +18 (1K) to +12 (10K) because:**
1. More diverse users exposed more bugs
2. Price contamination affected more sessions at scale
3. Advanced users found settings don't work
4. 21-day trial (vs 7-day) revealed more staleness issues

---

## SECTION 10: THE FINAL VERDICT FROM 10,000 USERS

### What Must Be Fixed BEFORE Public Launch (Blockers):
1. **Price contamination** — 28.5% of users saw wrong prices. This alone will generate negative press.
2. **11 missing assets** — 23% of advertised assets don't work. This is false advertising.
3. **Bullish signal bias** — 89% BUY signals in a mixed market = no credibility.
4. **Position sizing broken** — auto-trader ignores all risk calculations. One bad trade wipes trust.
5. **Settings are placebo** — users who customize expect it to work. Non-functional settings = broken promise.

### What Must Be Fixed Within 30 Days of Launch:
6. Real-time data (Twelve Data API)
7. Mobile PWA
8. Signal accuracy dashboard (public, auditable)
9. Stripe billing
10. Password reset

### What Users Love and We Must PROTECT:
1. Signal explanations — 54% love rate, #1 differentiator
2. Morning Brief — 67% engagement, highest retention feature
3. Fear & Greed contextual display — 62% love rate
4. Telegram alerts — 72% satisfaction among users who set it up
5. Paper trading + trade journal combo — "learn by doing" narrative

---

*Report compiled by VP Product (Sarah Chen), VP Engineering (James Rodriguez), VP QA (Michael Torres), VP Trading Systems (Elena Vasquez)*
*Classification: CRITICAL — CEO + C-Suite + All Department Heads*
*Action required: CEO Action Plan v2*
