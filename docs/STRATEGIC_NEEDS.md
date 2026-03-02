# Project Aegis — Strategic Needs Assessment
## Full Team Meeting Report — February 27, 2026

**Attendees:**
- CTO (Head of Engineering) — Gap Analysis & Production Readiness
- Broker & API Specialist — APIs, Costs, Market Data
- Trading Bot Architect — Real Trading Feasibility
- CFO (Financial Manager) — Budget, ROI, Legal Risk
- Product Critic (QA Lead) — 170 bugs found in prior audit

**Requested by:** CEO
**Budget:** $1,000/month

---

## EXECUTIVE SUMMARY

> **The honest truth:** Aegis is an impressive prototype (~15,000 lines of code, 28 dashboard views, 12-gate auto-trader) but it has ZERO production readiness for real money. The gap is not the trading logic — 65% of a real trading bot already exists. The gap is everything around it: security, legal protection, reliable data, broker integration, and testing.

### The 3 Things You Must Know

1. **You need a lawyer before you need an API** — $1,500 for Terms of Service review is the #1 investment. One angry user who loses money on a STRONG BUY signal can shut down the project without legal protection.

2. **Alpaca can't trade 10 of your 12 assets** — Only BTC and ETH are directly tradeable. Gold, Silver, Oil, etc. must use ETF proxies (GLD, SLV, USO). This changes behavior significantly.

3. **$1,000 trading capital is the absolute minimum** — Realistic monthly return: 1-2% ($10-20). You are not getting rich. This is tuition for building a proven track record.

---

## PART 1: WHAT APIs DO YOU NEED TO BUY?

### Priority 1: Market Data (Replace yfinance)

| Provider | Cost | What It Does | Priority |
|----------|------|-------------|----------|
| **Twelve Data (Grow)** | **$29/mo** | Real-time data for ALL 12 assets (stocks, crypto, forex, commodities). The ONLY provider at this price that covers everything | **BUY THIS FIRST** |
| Finnhub (free tier) | $0 | Real-time stock WebSocket + 60 calls/min. Good backup | Use immediately |
| CoinGecko (free tier) | $0 | Crypto data + social metrics. 30 calls/min | Use immediately |
| Polygon.io | $29/mo | Great for stocks but NO commodities | Skip (Twelve Data better) |
| Alpha Vantage | $0-50/mo | 25 calls/day free. Too slow for real-time | Skip |

**Verdict:** Twelve Data at $29/month is the single most important API purchase.

### Priority 2: Broker API (For Real Trading)

| Broker | Cost | Assets | Min Deposit | Best For |
|--------|------|--------|-------------|----------|
| **Alpaca** | **$0** | US Stocks, ETFs, Crypto | $0 | Starting out — easiest API, paper trading included |
| **Interactive Brokers** | **$0 base** (+$10-20/mo data) | EVERYTHING (stocks, futures, forex, crypto) | $0 | Full coverage — the only broker for all 12 assets as futures |
| OANDA | $0 | Forex only | $0 | EUR/USD if needed |
| Binance | $0 | Crypto only | $0 | Crypto execution |

**Verdict:** Start with **Alpaca** (free, easy API, great paper trading). Add **IBKR** in Month 6+ when you need commodities and forex as real futures.

### The Alpaca Limitation (CRITICAL)

Alpaca CANNOT trade futures or forex. Your current watchlist must map to ETFs:

| Asset | Current | Alpaca Alternative | Issue |
|-------|---------|-------------------|-------|
| Gold | GC=F | GLD (ETF) | ETF only trades 9:30AM-4PM ET |
| Silver | SI=F | SLV (ETF) | Same limitation |
| Oil | CL=F | USO (ETF) | Tracking error vs real oil |
| S&P 500 | ^GSPC | SPY (ETF) | Works well |
| NASDAQ | ^IXIC | QQQ (ETF) | Works well |
| BTC | BTC-USD | BTC/USD | **Direct — works perfectly** |
| ETH | ETH-USD | ETH/USD | **Direct — works perfectly** |
| Wheat | ZW=F | WEAT (ETF) | Low volume, wide spreads |
| EUR/USD | EURUSD=X | FXE (ETF) | Poor proxy |
| Copper | HG=F | CPER (ETF) | Very low volume |
| Platinum | PL=F | PPLT (ETF) | Low volume |
| NatGas | NG=F | UNG (ETF) | Decay issues |

### Priority 3: Infrastructure

| Service | Cost | What It Does |
|---------|------|-------------|
| **Hetzner CX22** | **$5.50/mo** | VPS: 2 vCPU, 4GB RAM — runs both services 24/7 |
| Domain (.com) | $1/mo | Your public address |
| Let's Encrypt SSL | $0 | HTTPS encryption |
| SendGrid (free) | $0 | 100 emails/day for verification + morning emails |
| UptimeRobot (free) | $0 | 50 monitors, 5-min checks, email alerts |
| Healthchecks.io (free) | $0 | Cron job monitoring (brain cycle heartbeat) |

### Priority 4: Payment Processing

| Service | Cost | Notes |
|---------|------|-------|
| Stripe | 2.9% + $0.30/transaction | No monthly fee. Only pay when you earn |

### Priority 5: News & Sentiment (Keep Free for Now)

| Current | Cost | Verdict |
|---------|------|---------|
| RSS feeds (feedparser) | $0 | Works. Keep it |
| Reddit JSON endpoints | $0 | Works. Keep it |
| NewsAPI | $35-449/mo | Skip — RSS is sufficient for now |
| Benzinga | $99-199/mo | Skip until Month 8+ |

---

## PART 2: CAN WE HAVE A REAL TRADING BOT?

### Yes. 65% Already Exists.

| Component | Status | Completeness |
|-----------|--------|-------------|
| Signal generation (12 assets) | DONE | 100% |
| Decision logic (12 gates) | DONE | 100% |
| Position sizing (Kelly/fixed) | DONE | 95% |
| Risk management (VaR, exposure) | DONE | 90% |
| Stop-loss / take-profit | DONE | 100% |
| Trailing stop | DONE | 100% |
| Drawdown circuit breaker | DONE | 100% |
| Portfolio tracking | DONE | 100% |
| Audit trail | DONE | 100% |
| **Broker API integration** | **MISSING** | **0%** |
| **Order execution layer** | **MISSING** | **0%** |
| **Kill switch (big red button)** | **MISSING** | **0%** |
| **Real-time price feed** | **MISSING** | **0%** |
| **Connection failure recovery** | **MISSING** | **0%** |

### What Needs to Be Built

**1. OrderExecutor Abstraction Layer** (~2 weeks)
```
auto_trader.py → OrderExecutor (interface)
                    ├── PaperExecutor (current system, unchanged)
                    └── AlpacaExecutor (new, real money)
```
Same bot logic, just routes to different destination. Switch with one config flag.

**2. Kill Switch** (~2 days)
- Big red button on dashboard
- Stops ALL trading immediately
- Cancels all pending orders
- Requires manual re-activation
- Cannot be auto-reset by code

**3. Daily Loss Circuit Breaker** (~1 day)
- Max 5% daily loss → auto-halt trading
- Separate from existing drawdown circuit breaker

**4. Position Reconciliation** (~1 week)
- On startup: sync local state with broker positions
- Detect and alert on discrepancies

### Timeline to Real Trading

| Phase | Duration | What Happens |
|-------|----------|-------------|
| Phase 1: Build Alpaca integration | 4 weeks | Code the executor, kill switch, safety systems |
| Phase 2: Alpaca paper testing | 2 weeks | Run bot on Alpaca paper (free, no risk) |
| Phase 3: Live at $100 | 2 weeks | Tiny real money, watch every trade |
| Phase 4: Live at $500 | 2 weeks | Increase if stable |
| Phase 5: Live at $1,000 | Ongoing | Full deployment |
| **Total: today → $1,000 live** | **~10-12 weeks** | |

### Realistic Returns on $1,000

| Scenario | Monthly | Annual | Probability |
|----------|---------|--------|-------------|
| Best case (skilled algo) | 3-5% ($30-50) | 36-60% | 15% |
| Realistic (decent algo) | 1-2% ($10-20) | 12-24% | 40% |
| Break-even | 0% | 0% | 20% |
| Most likely (first year) | -2% to -5% | -20% to -50% | 20% |
| Worst case | Total loss | -100% | 5% |

**The honest truth:** $1,000 in trading capital is learning money, not income. The real value is building a proven track record to scale to $10K, $50K, $100K later.

---

## PART 3: $1,000/MONTH BUDGET — WHERE EVERY DOLLAR GOES

### Three Budget Scenarios

#### Scenario A: Minimal ($36/month) — Paper Trading with Real Data
| Item | Cost |
|------|------|
| Twelve Data (Grow plan) | $29/mo |
| Hetzner CX22 | $5.50/mo |
| Domain | $1/mo |
| Everything else (free tiers) | $0 |
| **Total** | **$36/mo** |

#### Scenario B: Serious ($130/month) — One Broker, Good Data
| Item | Cost |
|------|------|
| Everything from Minimal | $36/mo |
| Hetzner CX32 upgrade | +$5/mo |
| SendGrid Essentials | $20/mo |
| UptimeRobot Pro | $15/mo |
| IBKR data fees | $15/mo |
| Alpaca + IBKR accounts | $0 |
| **Total** | **~$130/mo** |

#### Scenario C: Full ($660/month) — Multi-Broker, Scale-Ready
| Item | Cost |
|------|------|
| Twelve Data Pro | $99/mo |
| Polygon.io Starter | $29/mo |
| CoinGecko Analyst | $129/mo |
| MarketAux paid | $166/mo |
| SendGrid Pro | $90/mo |
| VPS + monitoring | $50/mo |
| Managed PostgreSQL | $15/mo |
| Everything else | $82/mo |
| **Total** | **~$660/mo** |

### Recommended: The Month-by-Month Plan

| Month | What to Spend On | Amount | Save |
|-------|-----------------|--------|------|
| **1** | LLC formation + VPS + Domain + Lawyer deposit | $637 | $363 |
| **2** | Lawyer completion + Stripe setup + Beta launch | $590 | $410 |
| **3** | UX polish (freelancer) + First marketing | $462 | $538 |
| **4** | Marketing ramp + Enable paid tier | $220 | $780 |
| **5-6** | Product Hunt + Growth + API prep | $250/mo | $750/mo |
| **7-12** | Twelve Data API + Marketing + Small trading capital | $500/mo | $500/mo |
| **Total 12 months** | | **~$7,000 spent** | **~$5,000 saved (reserve)** |

### Revenue Break-Even

| Paying Users | Revenue/mo | Costs/mo | Profit/mo |
|-------------|-----------|---------|-----------|
| 5 users | $315 | $400 | -$85 |
| **10 users** | **$630** | **$450** | **+$180** ← break-even |
| 25 users | $1,575 | $500 | +$1,075 |
| 50 users | $3,150 | $600 | +$2,550 |
| 100 users | $6,300 | $800 | +$5,500 |

**You need ~10 paying users to break even on operating costs.**

---

## PART 4: CRITICAL BLOCKERS — WHAT TO FIX BEFORE LAUNCH

### From CTO Gap Analysis (41 gaps found, 19 BLOCKERS)

**Phase 0 — "Stop the Bleeding" (Week 1)**
Must fix BEFORE anyone sees this:
- [ ] Data contract bugs (morning brief shows NEUTRAL/0%, prediction validation broken, adaptive learning dead code)
- [ ] Landing page fake scoreboard (legal liability — false advertising)
- [ ] Confidence score inflation (+11 point bias on all BUY signals)

**Phase 1 — "Security" (Weeks 2-3)**
Must fix BEFORE accepting users:
- [ ] XSS surface (160 instances of unsafe_allow_html)
- [ ] Path traversal via user_id (can read any file on server)
- [ ] SSRF via webhook URLs (can access internal services)
- [ ] Session tokens stored in plaintext
- [ ] HTTPS/TLS (currently plain HTTP only)
- [ ] Password requirements too weak (6 chars, no complexity)

**Phase 2 — "Reliability" (Weeks 4-6)**
Must fix BEFORE scaling:
- [ ] JSON storage → SQLite/PostgreSQL for portfolios
- [ ] Log rotation (files grow unbounded)
- [ ] Backup strategy for user data
- [ ] Monitoring/alerting (know when things break at 3 AM)
- [ ] Test suite (currently only 15 smoke tests)

**Phase 3 — "Legal Shield" (Weeks 4-8, parallel)**
Must fix BEFORE accepting money:
- [ ] Terms of Service (lawyer reviewed)
- [ ] Privacy Policy (GDPR required — you have German i18n)
- [ ] Per-signal disclaimers
- [ ] Tier alignment (pricing page says 12 assets free, code says 5)

---

## PART 5: THE HONEST RISK ASSESSMENT

### ROI Scenarios (12 months, $12,000 total invested)

| Scenario | Probability | Free Users | Paying Users | Revenue | Net |
|----------|-------------|-----------|-------------|---------|-----|
| **Bear** | 35% | 50-100 | 0-3 | $0-400 | **-$12,000** |
| **Base** | 50% | 200-500 | 10-25 | $2,000-6,000 | **-$6,000 to -$10,000** |
| **Bull** | 15% | 1,000-3,000 | 50-100 | $15,000-30,000 | **+$3,000 to +$18,000** |

### What the CFO Says You Must NOT Do

1. **Do NOT skip legal review to save $1,500** — One lawsuit costs $25,000+
2. **Do NOT put real money in a broker before Month 7** — Validate signals first
3. **Do NOT pay for premium APIs before you have paying users** — Free stack works
4. **Do NOT spend on marketing before product is sticky** — Fix retention first
5. **Do NOT build more features** — 28 views is enough. Polish what exists
6. **Do NOT ignore GDPR** — German/Arabic i18n = EU users = GDPR mandatory
7. **Do NOT store user data in plaintext JSON forever** — Acceptable for beta, not for production

### The Single Most Important Investment

> **$1,500 for a fintech lawyer to review Terms of Service, Privacy Policy, and investment disclaimers.**
>
> Everything else is secondary. The product works. The pricing page exists. But one angry user who loses $10,000 following a STRONG BUY signal can send a complaint to the SEC. Without proper legal protection, that complaint shuts down the project.

---

## PART 6: ACTION PLAN — WHAT TO DO RIGHT NOW

### This Week (Week 1)
1. Fix all data contract bugs (morning brief, prediction validation, adaptive learning)
2. Remove fake scoreboard from landing page
3. Start researching fintech lawyers

### This Month (Month 1)
1. Register LLC ($100)
2. Deploy to Hetzner VPS ($5.50/mo)
3. Engage lawyer for ToS review ($500 deposit)
4. Register Alpaca paper trading account (free)
5. Register Finnhub free API key
6. Register CoinGecko free API key

### Next Month (Month 2)
1. Complete legal documents
2. Fix top 10 security issues (XSS, path traversal)
3. Set up Stripe (free until revenue)
4. Recruit 5-10 beta testers from Reddit
5. Start Alpaca paper trading integration

### Month 3-4
1. Build OrderExecutor abstraction
2. Launch beta with free tier
3. Product Hunt submission
4. First marketing spend ($100)

### Month 5-6
1. Buy Twelve Data API ($29/mo)
2. Enable paid tiers
3. Target first 10 paying users

### Month 7+
1. Start Alpaca paper testing with real API
2. If signals validated 55%+ accuracy over 5 months → small real trading ($100)
3. Scale marketing based on conversion data

---

## APPENDIX: FULL API SHOPPING LIST

| API/Service | Free Tier | Paid Plan | When to Buy |
|-------------|-----------|-----------|-------------|
| Twelve Data | 800 calls/day | $29/mo (Grow) | Month 5 |
| Finnhub | 60 calls/min | $49/mo | Month 8+ |
| CoinGecko | 30 calls/min | $129/mo (Analyst) | Month 10+ |
| Polygon.io | 5 calls/min | $29/mo | Skip (Twelve Data covers it) |
| Alpaca | Paper + Live | $0 | Now (paper), Month 7 (live) |
| IBKR | Paper + Live | $0 + data fees | Month 8+ |
| Stripe | — | 2.9% + $0.30/tx | Month 2 |
| Hetzner CX22 | — | $5.50/mo | Month 1 |
| SendGrid | 100 emails/day | $20/mo | Month 4+ |
| UptimeRobot | 50 monitors | $7/mo | Now (free) |
| Let's Encrypt | Free | — | Month 1 |
| Termly (legal) | — | $15/mo | Month 1 |

---

*Document generated by Project Aegis Management Team*
*Classification: INTERNAL — CEO Eyes*
*Next review: March 15, 2026*
