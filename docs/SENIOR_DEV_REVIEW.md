# Senior Developer Review: Performance Optimization & Cloud Migration

**Project:** Aegis AI Trading Terminal
**Prepared:** March 2, 2026
**Purpose:** Technical review session for senior developers
**Duration:** 60-90 minutes
**Pre-read:** `docs/GOOGLE_CLOUD_MEETING.md` (Google Cloud $300 free credits plan)

---

## PART 1: Current Performance Diagnosis

### The Problem
Users experience **2-8 second page loads**, visible UI **flickering/bouncing every 30 seconds**, and occasional **45-second freezes**. The app feels sluggish and unreliable despite having good feature coverage.

### Root Cause: 5 Issues Cascading Together

```
User clicks button
    --> Streamlit reruns ENTIRE 9,900-line app.py
        --> 264 widgets re-render
        --> 50+ JSON files re-read from disk
        --> 10 yfinance HTTP calls queued (45s timeout each)
        --> Auto-refresh triggers again in 30s
            --> Loop repeats
```

---

### Issue #1: MONOLITHIC SINGLE FILE (Critical)

| Metric | Value |
|--------|-------|
| `dashboard/app.py` | **9,900+ lines** |
| Views in one file | **28 views** |
| If/elif routing chain | **26 sequential conditions** |
| Functions defined | **66 functions** |

**Impact:** Every button click, tab switch, or auto-refresh re-executes the entire file from line 1. A user on view #26 still runs code for views #1-25 first.

**Fix:** Split into `pages/` directory using Streamlit's `st.navigation()` API (available since Streamlit 1.36+). Each view becomes its own file. Only the active page executes.

```
dashboard/
    app.py          (200 lines — shell, auth, sidebar only)
    pages/
        advisor.py
        watchlist.py
        paper_trading.py
        charts.py
        ... (28 files)
    components/
        signal_card.py
        portfolio_ticker.py
        search_bar.py
```

**Estimated impact:** 70-80% reduction in per-rerun execution time.

---

### Issue #2: SYNCHRONOUS YFINANCE ON RENDER PATH (Critical)

| Metric | Value |
|--------|-------|
| `fetch_live_prices()` calls per page | **10 locations** |
| Timeout per call | **45 seconds** |
| Assets per call | **12 tickers** |
| Worst case per page load | **45 seconds frozen UI** |

**Where it's called:**
- Daily Advisor (line 2691)
- Asset Detail (line 3782)
- Watchlist (line 4373)
- Paper Trading (line 6314)
- Analytics (line 7340)
- Alerts (line 7601)
- Risk Dashboard (line 8884)
- + 3 more locations

**Impact:** yfinance is a blocking HTTP call. When Yahoo Finance is slow (common), the entire UI freezes.

**Fix options:**

| Option | Effort | Impact |
|--------|--------|--------|
| A. Background price service (separate process) | Medium | Best — UI never blocks |
| B. `@st.fragment` for price-dependent sections | Low | Good — isolates reruns |
| C. Increase cache TTL from 60s to 300s | Trivial | Quick win but stale data |
| D. Google Cloud Function on 1-min cron | Medium | Best long-term (see Part 2) |

---

### Issue #3: AUTO-REFRESH TRIGGERS FULL RERUN (High)

```python
# Current: Lines 1641-1645
if view in ("logs", "monitor"):
    st_autorefresh(interval=10_000)     # Every 10 seconds!
elif view in ("watchlist", "advisor", "paper_trading"):
    st_autorefresh(interval=30_000)     # Every 30 seconds
```

**Impact:** Auto-refresh triggers a FULL app rerun (9,900 lines + all I/O). This is why the UI "bounces" — every 30 seconds the entire page reloads.

**Fix:**
- Replace `st_autorefresh` with `@st.fragment` + targeted refresh (Streamlit 1.37+)
- Only refresh the price/data section, not the entire page
- Use WebSocket push from a background service instead of polling

---

### Issue #4: INSUFFICIENT CACHING (High)

| Cached | Not Cached |
|--------|------------|
| 5 functions with `@st.cache_data` | 50+ JSON file reads per page |
| Live prices (60s TTL) | Social sentiment data |
| Correlation data (5-10min TTL) | Geopolitical analysis |
| Sparklines (5min TTL) | News impact cache |
| Hindsight data (10min TTL) | Brain status, bot activity |
| | Alert schedules, predictions |
| | Auth checks (18x per render) |

**Fix:** Add `@st.cache_data(ttl=60)` to ALL file-reading functions:
```python
@st.cache_data(ttl=60)
def load_social_sentiment():
    ...

@st.cache_data(ttl=300)
def load_geopolitical_analysis():
    ...
```

**Quick win:** Just adding cache decorators to the top 10 uncached functions would cut I/O by ~60%.

---

### Issue #5: 264 INTERACTIVE WIDGETS (Medium)

| Widget Type | Count |
|-------------|-------|
| `st.button()` | 120+ |
| `st.selectbox()` | 20+ |
| `st.text_input()` | 25+ |
| `st.tabs()` | 15+ |
| `st.checkbox()` | 20+ |
| `st.slider()` | 10+ |
| `st.radio()` | 15+ |
| `st.rerun()` explicit calls | **57** |

Every widget interaction triggers a full rerun. With 264 widgets, even scrolling through cards can cause cascading reruns.

**Fix:** Wrap independent widget groups in `@st.fragment` decorators. Use `st.form()` to batch inputs.

---

### Performance Budget (Current vs Target)

| Metric | Current | Target | How |
|--------|---------|--------|-----|
| Page load (cold) | 5-45s | < 2s | Split app + async prices |
| Page load (cached) | 2-8s | < 0.5s | Add caching + fragments |
| Auto-refresh flicker | Every 30s | None | Fragment-based refresh |
| Button click response | 1-3s | < 0.3s | Split app into pages |
| yfinance timeout | 45s freeze | 0s (background) | Background price service |

---

## PART 2: Google Cloud $300 Implementation Plan

> **Pre-read:** `docs/GOOGLE_CLOUD_MEETING.md` for the full cost breakdown.

### Why Cloud Matters for Performance

The performance issues above can be **structurally solved** by moving specific workloads to the cloud:

| Local Problem | Cloud Solution | Service | Est. Cost/mo |
|--------------|----------------|---------|--------------|
| yfinance blocks UI | Background price worker | **Cloud Run** job on 1-min cron | $5 |
| JSON file I/O | Real database | **Firestore** or **Cloud SQL** | $10-15 |
| Single-machine bottleneck | Horizontal scaling | **Cloud Run** (auto-scale) | $15-20 |
| No real-time updates | Push notifications | **Pub/Sub** + Cloud Functions | $2-5 |
| Brain loop runs locally | Scheduled serverless | **Cloud Scheduler** + **Cloud Functions** | $3-5 |

### Recommended Implementation Phases

#### Phase 1: "Stop the Bleeding" (Week 1-2, ~$20/month)

**Goal:** Eliminate UI freezes without rewriting the app.

```
[Cloud Scheduler] --> every 1 min --> [Cloud Function: fetch_prices]
                                            |
                                            v
                                      [Firestore: live_prices collection]
                                            |
                                            v
                          [Streamlit reads from Firestore instead of yfinance]
```

**What changes:**
1. Deploy a Cloud Function that fetches all 12 asset prices every minute
2. Stores results in Firestore (or Cloud Storage JSON)
3. Dashboard reads from Firestore instead of calling yfinance directly
4. **Result: Zero yfinance calls on render path = instant page loads**

**Services:**
- Cloud Scheduler: 1 job, 1-min interval = ~$0.10/month
- Cloud Functions: ~1,440 invocations/day = ~$0.50/month
- Firestore: 12 docs updated/min = ~$2/month
- **Total: ~$3/month**

#### Phase 2: "Brain in the Cloud" (Week 3-4, ~$30/month)

**Goal:** Run `aegis_brain.py` autonomously in the cloud 24/7.

```
[Cloud Scheduler] --> every 30 min --> [Cloud Run Job: aegis_brain.py]
                                            |
                                            v
                                      [Full market scan + auto-trade]
                                            |
                                            v
                              [Firestore: scan results, trades, alerts]
                                            |
                                            v
                              [Pub/Sub --> Telegram/Discord notifications]
```

**Services:**
- Cloud Run Job: 48 runs/day, ~2min each = ~$8/month
- Firestore: scan results storage = ~$5/month
- Pub/Sub: alert delivery = ~$1/month
- Secret Manager: API keys = ~$0.50/month
- **Total: ~$15/month**

#### Phase 3: "Scale Ready" (Week 5-8, ~$50/month)

**Goal:** Multi-user cloud deployment.

```
[Cloud Run: Streamlit app] <--> [Firestore: user data]
         |                              |
         v                              v
  [Cloud CDN: static assets]    [Cloud SQL: if needed later]
         |
         v
  [Cloud Monitoring: uptime, latency, errors]
```

**Services:**
- Cloud Run (Streamlit): auto-scaling, $15-20/month
- Cloud CDN: landing page, $2-5/month
- Cloud Monitoring: free tier
- Cloud Logging: free tier (first 50GB)
- **Total: ~$20-30/month**

### 90-Day Budget Allocation

| Phase | Timeline | Monthly Cost | 90-Day Total |
|-------|----------|-------------|--------------|
| Phase 1: Price Service | Week 1-2 | $3 | $9 |
| Phase 2: Brain in Cloud | Week 3-4 | $15 | $45 |
| Phase 3: Full Deploy | Week 5-8 | $50 | $100 |
| Buffer for experiments | Ongoing | — | $46 |
| **TOTAL** | | | **$200 of $300** |

**$100 remaining** for Vertex AI/Gemini experiments (smart causal analysis, natural language commands).

---

## PART 3: Optimization Roadmap (Prioritized)

### Sprint A: Quick Wins (1-2 days, no cloud needed)

- [ ] Add `@st.cache_data(ttl=60)` to top 10 uncached file-read functions
- [ ] Increase `_fetch_live_prices_cached` TTL from 60s to 120s
- [ ] Reduce auto-refresh from 30s to 60s on Advisor/Watchlist
- [ ] Disable auto-refresh on non-trading pages entirely
- [ ] Cache auth checks: `can_access_view()` results per session

**Expected result:** Page loads drop from 5-8s to 2-4s.

### Sprint B: Architecture (3-5 days, no cloud needed)

- [ ] Split `app.py` into `pages/` directory (28 files)
- [ ] Use `st.navigation()` for page routing
- [ ] Move shared components to `components/` module
- [ ] Wrap price-dependent sections in `@st.fragment`
- [ ] Replace `st_autorefresh` with fragment-based polling

**Expected result:** Page loads drop from 2-4s to 0.5-1s. Flickering eliminated.

### Sprint C: Cloud Phase 1 (3-5 days, uses free credits)

- [ ] Set up Google Cloud project
- [ ] Deploy price-fetch Cloud Function
- [ ] Set up Firestore for live prices
- [ ] Wire dashboard to read from Firestore
- [ ] Set up billing alerts ($50, $100, $200)

**Expected result:** Zero yfinance calls on render path. Sub-second page loads.

### Sprint D: Cloud Phase 2-3 (1-2 weeks, uses free credits)

- [ ] Deploy aegis_brain.py as Cloud Run Job
- [ ] Set up Pub/Sub for alert notifications
- [ ] Deploy Streamlit to Cloud Run
- [ ] Set up Cloud Monitoring dashboard
- [ ] Performance benchmarking vs local

**Expected result:** 24/7 autonomous operation, multi-user ready.

---

## PART 4: Discussion Questions for Senior Devs

1. **Architecture:** Should we split app.py now (Sprint B) or go straight to cloud (Sprint C)? Both fix the core issue differently.

2. **Database:** Firestore (NoSQL, Google native) vs Cloud SQL (PostgreSQL, more familiar)? Current JSON storage works but doesn't scale.

3. **Real-time:** WebSocket push (via Cloud Run + Pub/Sub) vs polling (current approach)? WebSocket eliminates auto-refresh entirely.

4. **Framework:** Stay with Streamlit or migrate to React/Next.js? Streamlit's rerun model IS the root cause of flickering. React would eliminate it but requires full frontend rewrite.

   | Factor | Streamlit | React/Next.js |
   |--------|-----------|---------------|
   | Dev speed | Fast | Slow |
   | Performance | Limited by rerun model | Full control |
   | Real-time | Polling only | WebSocket native |
   | User threshold | Good up to ~50 users | Scales to thousands |
   | Migration effort | N/A | 4-8 weeks full rewrite |

5. **AI/ML:** Vertex AI (Gemini) for smarter causal analysis? Current rules-based engine works but could be enhanced with LLM reasoning. $15-30/month from free credits.

6. **Monitoring:** What metrics should we track from day 1? Suggested: page load time, yfinance latency, error rate, active users, cache hit rate.

---

## Appendix A: Key File Sizes

| File | Lines | Size |
|------|-------|------|
| `dashboard/app.py` | 9,900+ | ~1.7MB |
| `src/market_scanner.py` | 1,500+ | ~270KB |
| `src/auto_trader.py` | ~800 | ~140KB |
| `src/chart_engine.py` | ~450 | ~80KB |
| `src/news_impact.py` | ~280 | ~50KB |
| **Total codebase** | ~15,000+ | ~2.5MB |

## Appendix B: Current Tech Stack

| Layer | Technology | Limitation |
|-------|-----------|------------|
| Frontend | Streamlit | Full rerun on every interaction |
| Data | JSON files | No concurrent access, no indexing |
| Market Data | yfinance (free) | Rate limited, 45s timeout |
| Charts | Plotly | Heavy rendering, no streaming |
| Hosting | Local machine | Single user, not 24/7 |
| CI/CD | None | Manual deployment |

## Appendix C: Existing Cloud-Ready Files

These files already exist and can accelerate cloud deployment:

- `Dockerfile` — Python 3.11-slim, Streamlit config, healthcheck
- `docker-compose.yml` — Streamlit + Redis + PostgreSQL services
- `.env.example` — All environment variables documented
- `src/config.py` — Centralized configuration, easy to swap for env vars
- `src/data_store.py` — DataStore abstraction (currently JSON, designed for DB swap)

---

*Document prepared for Project Aegis senior developer review session.*
*See also: `docs/GOOGLE_CLOUD_MEETING.md` for meeting agenda and cost breakdown.*
