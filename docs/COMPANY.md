# Project Aegis: Company Blueprint

## The Complete Playbook for Going from Prototype to Business

*Compiled from 6 specialized agent reports, February 2026*

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [What Aegis Is (And Is Not)](#2-what-aegis-is)
3. [Infrastructure & Deployment](#3-infrastructure)
4. [Technical Architecture](#4-technical-architecture)
5. [Product Strategy](#5-product-strategy)
6. [Integrations: Messaging & Broker APIs](#6-integrations)
7. [Pricing & Monetization](#7-pricing)
8. [Go-to-Market](#8-go-to-market)
9. [Team & Company Formation](#9-team-and-company)
10. [Security & Legal](#10-security-and-legal)
11. [Execution Roadmap](#11-execution-roadmap)
12. [Files Created This Session](#12-files-created)

---

## 1. EXECUTIVE SUMMARY

Project Aegis is an AI-powered trading terminal that combines market scanning, signal generation, news sentiment, social intelligence, and autonomous paper trading into a Bloomberg-style command center for retail traders.

**Current state:** Working prototype with 28 views, 12 assets, autonomous bot, paper trading, and comprehensive analytics. Single-user, JSON storage, Streamlit frontend. Zero revenue.

**Target state:** Multi-user SaaS with authentication, Stripe payments, real-time data, notification system, and broker API integration. Revenue-generating within 8 weeks.

### Key Decisions Made

| Decision | Choice | Cost |
|----------|--------|------|
| Business model | Advisory platform (NOT broker) | Disclaimers only |
| Hosting | Hetzner VPS (EUR 3.79/mo) | ~$4/mo |
| Database | JSON + SQLite now, Supabase later | $0 |
| Frontend | Streamlit now, React at 500 users | $0 |
| Architecture | Modular monolith | Single deploy |
| Real-time data | Phase 1: Binance + Finnhub (free) | $0 |
| Notifications | Telegram bot (free) | $0 |
| Payment | Stripe Checkout | 2.9% + $0.30/txn |
| Legal entity | Delaware C-Corp (via Stripe Atlas) | $500 |
| Total monthly cost at launch | | **~$4.10** |

---

## 2. WHAT AEGIS IS (AND IS NOT)

**Aegis = "The AI Brain"** (intelligence layer)
**Binance/Plus500 = "The Hands"** (execution layer)

### Aegis IS:
- AI-generated market research + signals + paper trading
- Revenue via subscriptions ($29-$199/mo)
- Protected under publisher's exclusion (Investment Advisers Act 1940)
- Same legal category as TradingView, Trade Ideas, Seeking Alpha

### Aegis is NOT:
- A broker (no custody of customer funds)
- A registered investment adviser (no personalized advice)
- An execution platform (users connect their own broker accounts later)

### Why Not a Broker?

| Factor | Broker | Aegis (Advisory) |
|--------|--------|-------------------|
| Capital required | $750K-$20M+ | $50K-$200K |
| Regulatory licenses | FCA, CySEC, SEC, FINRA | Disclaimers only |
| Time to market | 18-36 months | 3-6 months |
| Compliance costs | $500K-$2M/year | $5K-$15K one-time |
| Holds customer money | Yes (enormous liability) | No |

*Full analysis: [docs/REGULATORY.md](REGULATORY.md)*

---

## 3. INFRASTRUCTURE & DEPLOYMENT

### Hosting Decision: Hetzner VPS

| Provider | Comparable Spec | Monthly Cost |
|----------|----------------|-------------|
| **Hetzner CX22** | 4GB RAM, 2 vCPU | **EUR 3.79** |
| DigitalOcean | 4GB RAM, 2 vCPU | $24.00 |
| AWS EC2 t3.medium | 4GB RAM, 2 vCPU | ~$30.00 |
| Railway | Similar compute | ~$20.00 |

### Stack

```
Nginx (reverse proxy, WebSocket support)
  └── Streamlit (dashboard, port 8501)
  └── Redis (cache, session state)
  └── PostgreSQL (future multi-user data)
```

### Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Production Docker image |
| `docker-compose.yml` | Full stack: Streamlit + Redis + PostgreSQL |
| `.dockerignore` | Excludes dev files from build |
| `.env.example` | Environment variable template |
| `deploy/nginx.conf` | Reverse proxy with WebSocket support |
| `deploy/setup-vps.sh` | One-command VPS provisioning |
| `deploy/sentry_init.py` | Error tracking integration |
| `.github/workflows/deploy.yml` | CI/CD: Lint, Test, Build, Deploy |
| `tests/test_smoke.py` | 15+ smoke tests (imports, config, JSON, signals) |

### Scaling Path

```
Month 1-3:   Hetzner CX22 (EUR 3.79)  -- 1-15 users -- JSON files
Month 3-6:   Hetzner CX32 (EUR 7.49)  -- 15-40 users -- Add Supabase for auth
Month 6-12:  Hetzner CX42 (EUR 14.99) -- 40+ users -- Background worker
Year 2:      React + FastAPI migration -- Break Streamlit ceiling -- Multi-node
```

### Critical Pre-Scale Change

**Background data fetcher.** Currently every user session calls yfinance on page load. Before 5+ concurrent users:
1. A background process fetches all 12 asset prices every 60 seconds
2. Writes to Redis (or shared JSON)
3. All Streamlit sessions read from cache instead of yfinance
4. Eliminates rate limiting, reduces load from 3-5s to <500ms

---

## 4. TECHNICAL ARCHITECTURE

### 7 Binding Decisions (Head of Engineering)

**Decision 1: Streamlit now, React at 500 users**
- Streamlit ships today. React ships in Month 4-6.
- The bridge: FastAPI backend works for both frontends.
- React stack when ready: Next.js 15, TradingView Lightweight Charts, shadcn/ui, Zustand, WebSocket.

**Decision 2: Modular monolith**
- One deploy target, clean module boundaries.
- `core/` (domain logic) never imports from `api/` or `dashboard/`.
- Pydantic models for all data shapes (replace raw dicts).

**Decision 3: Split app.py into view modules**
- 7,326 lines is past the pain threshold.
- New structure: thin router app.py (~150 lines) + `views/` directory (one file per view).
- Migration: extract views one at a time, test after each extraction.

**Decision 4: Testing with pytest**
- 40 tests minimum before first deploy.
- Priority: money-touching code first (signal scoring, paper trader, auto-trader, risk manager).
- Mock yfinance in all tests (no network calls in CI).

**Decision 5: FastAPI with JWT + API keys**
- 35 endpoints mapping to existing `src/` modules.
- JWT for web users, API keys for bots/developers.
- WebSocket for real-time prices and signal push.

**Decision 6: Security checklist (25 items)**
- HTTPS, CORS whitelist, bcrypt passwords, JWT from env vars.
- Rate limiting, input validation, XSS audit.
- No secrets in code, no secrets in logs.

**Decision 7: Dev environment**
- VS Code + GitHub + trunk-based development + ruff + pre-commit hooks.
- Branch lifetime: max 3 days. Squash merge to main.

*Full technical document: saved in Head of Engineering agent output*

---

## 5. PRODUCT STRATEGY

### User Personas

| Persona | Age | Portfolio | Tier | Killer Feature |
|---------|-----|-----------|------|----------------|
| **Crypto Carlos** | 26 | $15K crypto | Pro ($29/mo) | AutoPilot + Social Sentiment |
| **Investor Inga** | 42 | $200K diversified | Pro ($249/yr) | Morning Brief + Optimizer |
| **Prop Desk Pete** | 35 | $2M firm | Enterprise (8 seats) | API + Team + Risk Dashboard |
| **Builder Bilal** | 30 | $30K index | Enterprise (1 seat) | REST API + Signal JSON |

### Activation Definition

User is "activated" when they complete 3 of 5 actions:
1. Run a scan
2. Customize watchlist
3. Place a paper trade
4. Read morning brief
5. Enable AutoPilot

### Retention Loops

1. **Morning Brief email** (7 AM daily) -- replaces manual research
2. **Bot activity notifications** (Telegram) -- users check back to see bot trades
3. **Weekly accuracy scorecard** -- ego loop, competitive element

### Top 5 Features to Build Next

| Rank | Feature | Effort | Impact |
|------|---------|--------|--------|
| 1 | User Authentication | 5-8 days | Blocker |
| 2 | Landing Page | 3-5 days | Blocker |
| 3 | Email + Telegram Alerts | 4-6 days | High |
| 4 | Stripe Payment | 3-4 days | Blocker |
| 5 | Legal Disclaimers | 1-2 days | Non-negotiable |

*Full product strategy: [docs/PRODUCT_STRATEGY.md](PRODUCT_STRATEGY.md)*

---

## 6. INTEGRATIONS: MESSAGING & BROKER APIs

### Notification Channels (Priority Order)

| Channel | Cost | Effort | Use Case |
|---------|------|--------|----------|
| **Telegram Bot** | FREE | 2 days | Signal alerts, bot activity, morning brief |
| **Email (Resend/SendGrid)** | FREE tier | 2 days | Morning digest, trial reminders, onboarding |
| **Discord Webhook** | FREE | 1 day | Community alerts |
| **WhatsApp (Meta API)** | $0.005/msg | 3 days | Premium feature (Enterprise) |

### Broker API Integration (Phase 2, Month 6+)

| Broker | Assets | API Quality | Integration Effort |
|--------|--------|------------|-------------------|
| **Alpaca** | US Stocks, ETFs | Excellent (REST + WebSocket) | 3-4 days |
| **Binance** | Crypto (500+ pairs) | Excellent | 2-3 days |
| **OANDA** | Forex + Commodities | Good (v20 REST) | 3-4 days |
| **IBKR** | Everything | Complex (TWS API) | 5-7 days |

### Architecture: Unified BrokerManager

```python
class BrokerInterface(ABC):
    def place_order(asset, side, quantity, order_type) -> Order
    def get_positions() -> list[Position]
    def get_balance() -> Balance

class BrokerManager:
    brokers: dict[str, BrokerInterface]  # "alpaca", "binance", "oanda"
    # Routes orders to correct broker based on asset type
    # Encrypted credential storage (Fernet)
    # Symbol translation (Gold -> GC=F -> XAUUSD)
```

**Key principle:** USER clicks BUY = software tool (not regulated). AUTO-execute = may need RIA registration.

---

## 7. PRICING & MONETIZATION

### Tiers

| | Recruit (Free) | Operator (Pro) | Command (Enterprise) |
|---|---|---|---|
| **Price** | $0/forever | $29/mo or $249/yr | $199/seat/mo (min 5) |
| **Assets** | 5 | 50 | Unlimited + custom |
| **Scans** | 3/day | Unlimited | Unlimited |
| **Signals** | BUY/SELL only | Full spectrum + confidence % | Custom weights |
| **AutoPilot** | -- | Included | Included |
| **Social Sentiment** | -- | Included | Included |
| **API** | -- | -- | REST + WebSocket |

### Revenue Projections (Conservative)

| Month | Free Users | Pro | Enterprise Seats | MRR |
|-------|-----------|-----|-----------------|-----|
| 3 | 500 | 15 | 0 | $435 |
| 6 | 2,000 | 80 | 10 | $4,310 |
| 12 | 8,000 | 350 | 50 | $20,000 |
| 18 | 20,000 | 1,000 | 150 | $58,850 |
| 24 | 50,000 | 3,000 | 400 | $166,600 |

**Path to $1M ARR:** ~2,900 Pro subscribers (18-24 months)

### Competitive Positioning

| vs Competitor | Aegis Advantage |
|---------------|-----------------|
| Bloomberg ($24K/yr) | 97% cheaper ($348/yr Pro) |
| TradingView | Autonomous analysis + AI autopilot |
| Trade Ideas | 5 signal sources vs 1 |
| Plus500/Binance | AI intelligence (they are just execution) |
| Seeking Alpha | Real-time + AI (SA is human articles) |

*Full strategy: [docs/STRATEGY.md](STRATEGY.md)*

---

## 8. GO-TO-MARKET

### Launch Strategy (Day -30 to Day 90)

**Pre-Launch (4 weeks before):**
- Landing page with waitlist (position-based, referrals move you up)
- 3 demo videos, 2 blog posts, beta recruitment from 6 channels
- Target: 50-100 beta testers

**Launch Day:**
- Product Hunt submission at 12:05 AM PST (target: Top 5)
- Reddit posts across 4 subreddits (tailored per community)
- Hacker News "Show HN"
- Twitter/X blitz with demo screenshots
- Target: 200-500 signups

**Month 1-3: Community-Led**
- "Founding Member Pricing" at $19/mo for life (early adopter lock-in)
- Discord server for community + support
- Blog: 2 posts/week targeting "AI trading signals", "crypto screener"
- YouTube: weekly demos + market analysis

**Month 3-6: Content + SEO**
- Newsletter "The Aegis Brief" (weekly market summary)
- Ticker-specific landing pages (aegis.ai/signals/gold) for SEO
- Partnership outreach (education platforms, broker APIs)

### Content Plan (5 Blog Posts + 5 Videos Ready to Produce)

**Blog:** "I Replaced My Bloomberg Terminal With a $29 AI" | "How AI Trading Signals Actually Work" | "Gold Price Prediction: What AI Says" (template for all 12 assets) | "I Let an AI Paper Trade for 30 Days" | "5 Technical Indicators That Actually Predict Price"

**YouTube:** "Bloomberg Terminal for $29/Month" | "AI Traded for Me for 30 Days" (viral potential) | "How AI Reads the News" | "Free Tools I Used to Build a Trading AI" | "Gold vs BTC vs S&P 500: AI Signals"

### Referral Program

- 1 referral = 1 week free, 3 = 1 month, 5 = Founding badge, 10 = 50% lifetime, 25 = free Pro forever
- Referee gets 30-day Pro trial (vs standard 14-day)
- Target K-factor: 0.3-0.5

### Path to 1,000 Users

| Month | Signups | Pro Users | MRR |
|-------|---------|-----------|-----|
| 1 | 575-1,550 | 50 | $1,450 |
| 2 | +740-1,490 | 200 | $5,800 |
| 3 | +1,530-3,550 | 500 | $14,500 |
| 5-6 | -- | **1,000** | $29-49K |

### Conversion Funnel

```
Discovery (landing page / Product Hunt / Reddit)
  └── Signup (free, no credit card)
       └── Onboarding (3-screen wizard, first scan)
            └── Activation (3/5 actions in 7 days)
                 └── Trial (14-day Pro, no credit card)
                      └── Conversion (Stripe checkout)
                           └── Retention (daily email, bot notifications)
```

**Target conversion rate:** 5-10% Free-to-Pro (early adopters), 3-5% at scale

*Full playbook: [docs/GTM_PLAYBOOK.md](GTM_PLAYBOOK.md)*

---

## 9. TEAM & COMPANY FORMATION

### Entity: Delaware C-Corp via Stripe Atlas ($500)

Why: Every VC, accelerator, and legal template assumes Delaware C-Corp. If bootstrapping, start as LLC and convert later.

### Hiring Roadmap

| When | Hire | Role | Cost |
|------|------|------|------|
| Month 1 | Hire #1 | Growth Marketer (contractor) | $3-5K/mo |
| Month 4-6 | Hire #2 | Full-Stack Engineer | $80-120K + equity |
| Month 8-12 | Hire #3 | Customer Success | $45-65K |

### What AI Replaces

| Role | AI Replacement | Feasibility |
|------|---------------|-------------|
| Tier-1 support | Chatbot (Intercom Fin) | High |
| Content drafts | Claude/GPT-4 | High |
| QA testing | Playwright + CI/CD | Medium |
| Social scheduling | Buffer + AI generation | Medium |
| Design | Not yet | Low |
| Sales calls | Not yet | Low |

### Budget (First 12 Months, Bootstrapped)

| Category | Amount |
|----------|--------|
| Incorporation + legal | $3,000 |
| Growth marketing (6 months) | $12,000 |
| Infrastructure + tools | $3,000 |
| Design (landing page, brand) | $2,000 |
| Paid ads testing | $4,000 |
| Emergency / contingency | $6,000 |
| **Total needed** | **$30,000** |

### Tools (Day 1 Stack, ~$20-60/mo total)

| Category | Tool | Cost |
|----------|------|------|
| Communication | Discord | Free |
| Project Mgmt | GitHub Projects | Free |
| Docs | Notion | Free |
| Analytics | PostHog | Free |
| Support | Crisp | Free |
| Email | Google Workspace | $6/mo |
| Hosting | Hetzner VPS | $4/mo |
| Errors | Sentry | Free |
| CI/CD | GitHub Actions | Free |
| Payments | Stripe | 2.9% + $0.30/txn |

### Advisors Needed

1. **Fintech advisor** (0.25-1% equity, 2yr vest) -- former trading platform founder
2. **Securities attorney** ($2-5K consultation) -- before any real trading features
3. **Technical advisor** (0.25-0.5% equity) -- scaling experience

### Should You Raise?

**Bootstrap first (6-12 months).** Prove people will pay. Then:
- Pre-seed: $250-750K at $2-5M pre-money valuation
- Best targets: Y Combinator ($500K for 7%), fintech angels on AngelList
- YC is strongly recommended -- the network alone is worth the equity

---

## 10. SECURITY & LEGAL

### Required Disclaimers (already added to dashboard)

1. **Global footer** on every page: "Not investment advice. Trading involves risk."
2. **Signal-specific**: "AI-generated, not a personal recommendation."
3. **Paper trading**: "Simulated results, not actual trading."
4. **Sidebar**: Compact version of above.
5. **Regional**: US (publisher's exclusion), EU (MiFID II), UK (not FCA regulated)

### Pre-Launch Security Checklist

- [ ] HTTPS everywhere (Let's Encrypt + HSTS)
- [ ] CORS whitelist (only your domain)
- [ ] Bcrypt passwords (cost factor 12)
- [ ] JWT secrets from environment variables
- [ ] API key hashing (SHA-256, shown once)
- [ ] Rate limiting on auth (5 attempts/15min/IP)
- [ ] No secrets in code or logs
- [ ] .env in .gitignore
- [ ] Input validation (Pydantic on all endpoints)
- [ ] XSS audit (`unsafe_allow_html=True` instances)
- [ ] Non-root Docker process
- [ ] Firewall (only 80/443 open)
- [ ] Dependency audit (`pip audit`)
- [ ] Automated daily backup of JSON data

---

## 11. EXECUTION ROADMAP

### Sprint 11 (Week 1-2): "Make It Launchable"
- [ ] User authentication (streamlit-authenticator)
- [ ] Per-user data isolation (watchlists, portfolio, settings)
- [ ] Feature gating (tier checks in sidebar + views)
- [ ] Landing page (static HTML, deploy to Vercel)
- [ ] First-login disclaimer acknowledgment modal

### Sprint 12 (Week 3-4): "Make It Sticky"
- [ ] Telegram bot for signal notifications
- [ ] Email integration (Resend/SendGrid + morning brief template)
- [ ] Stripe payment (Checkout flow + webhook handler)
- [ ] Onboarding wizard (3-screen modal after signup)

### Sprint 13 (Week 5-6): "Make It Polished"
- [ ] Real-time prices (Binance REST for crypto, Finnhub for stocks)
- [ ] Background data fetcher (decouple yfinance from user sessions)
- [ ] Mobile-responsive CSS
- [ ] Product Hunt launch

### Sprint 14 (Week 7-8): "Make It Real"
- [ ] Broker API integration (Alpaca paper trading first)
- [ ] FastAPI endpoints for Enterprise API
- [ ] Referral system
- [ ] Analytics integration (PostHog)

### Month 3-6: Growth Phase
- Content marketing + SEO
- Hit 100 users, validate willingness to pay
- Target: $3-5K MRR

### Month 6-12: Scale Phase
- React + FastAPI migration planning (at 500 users)
- Hire engineer #1
- Target: $10-20K MRR

---

## 12. FILES CREATED THIS SESSION

### Strategic Documents
| File | Content |
|------|---------|
| `docs/COMPANY.md` | This document -- master blueprint |
| `docs/STRATEGY.md` | Pricing tiers, revenue projections, competitive moat |
| `docs/REGULATORY.md` | Advisory vs broker analysis, legal disclaimers |
| `docs/REALTIME_DATA.md` | 3-phase path to real-time prices |
| `docs/PRODUCT_STRATEGY.md` | User journey, personas, feature prioritization, landing page copy |
| `docs/GTM_PLAYBOOK.md` | Go-to-market playbook: launch plan, content strategy, referral program |

### Deployment Files (CTO Agent)
| File | Purpose |
|------|---------|
| `Dockerfile` | Production Docker image for Streamlit |
| `docker-compose.yml` | Full stack: Streamlit + Redis + PostgreSQL |
| `.dockerignore` | Build exclusions |
| `.env.example` | Environment variable template |
| `deploy/nginx.conf` | Nginx reverse proxy with WebSocket support |
| `deploy/setup-vps.sh` | One-command VPS provisioning script |
| `deploy/sentry_init.py` | Sentry error tracking snippet |
| `.github/workflows/deploy.yml` | CI/CD pipeline (lint, test, Docker build, deploy) |
| `tests/test_smoke.py` | 15+ smoke tests |
| `tests/__init__.py` | Test package init |

### Dashboard Changes
- Legal disclaimers added (global footer + sidebar)
- Sidebar highlight bug fixed (default "advisor" not "watchlist")
- Social Pulse made interactive (navigation + scan buttons)
- Empty states fixed in Analytics page (3 locations)
- Silent exception logging in morning_brief.py and news_researcher.py

---

## THE ONE-LINER

**Aegis is a $29/mo AI trading terminal that gives retail traders Bloomberg-grade intelligence -- signals, sentiment, risk management, and an autonomous paper trading bot -- without the $24,000/year price tag or regulatory complexity of being a broker.**

---

*Compiled by the Aegis Agent Team, February 26, 2026*
*Source reports: CTO, Head of Integrations, Head of Product, Head of Engineering, VP Operations*
