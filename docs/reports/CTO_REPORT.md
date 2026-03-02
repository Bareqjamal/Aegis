# CTO Engineering Report — Project Aegis Trading Terminal

**Date:** 2026-02-28
**Author:** CTO Office
**Classification:** Internal — Leadership Team
**Version:** 1.0

---

## Executive Summary

Project Aegis is a functional autonomous trading terminal with 28 dashboard views, 48 backend modules, a multi-agent AI orchestration loop, and a working paper trading system. The product demonstrates significant feature depth and domain sophistication. However, the architecture is prototypical — optimized for rapid iteration by a solo developer, not for production multi-user deployment. This report inventories the current technical state, identifies every scalability wall we will hit, and lays out a phased migration plan from prototype to production-grade SaaS platform.

**Bottom line:** We have a working product with real signal-generation IP. The engineering challenge is not "can we build it?" — it is "can we re-platform it without losing momentum?" The answer is yes, in three phases over 12 months, at a cumulative infrastructure cost of ~$840K in Year 1.

---

## Table of Contents

1. [Current Technical Architecture Assessment](#1-current-technical-architecture-assessment)
2. [Scalability Bottlenecks](#2-scalability-bottlenecks)
3. [Technology Migration Roadmap](#3-technology-migration-roadmap)
4. [Engineering Team Scaling Plan](#4-engineering-team-scaling-plan)
5. [Security Assessment](#5-security-assessment)
6. [DevOps & CI/CD Roadmap](#6-devops--cicd-roadmap)
7. [Key Technical Decisions](#7-key-technical-decisions)
8. [Cost Summary & Timeline](#8-cost-summary--timeline)
9. [Risk Register](#9-risk-register)
10. [Appendix: Module Inventory](#appendix-module-inventory)

---

## 1. Current Technical Architecture Assessment

### 1.1 Tech Stack

| Layer | Technology | Status |
|-------|-----------|--------|
| Frontend | Streamlit 1.x + Plotly + streamlit-autorefresh | Working, single-process |
| Backend | Python 3.9+ (48 modules in `src/`) | Working, no API layer |
| Data Storage | JSON files on disk (`src/data/`, `memory/`, `users/`) | Working, no ACID guarantees |
| Market Data | yfinance (free tier), RSS via feedparser | Working, rate-limited |
| Social Data | Reddit JSON API (free), RSS influencer feeds | Working, fragile |
| Auth | PBKDF2-HMAC-SHA256, file-based sessions | Working, not scalable |
| i18n | Custom 3-language system (en/de/ar) with RTL | Working |
| Deployment | `run.bat` (Windows manual start) | No CI/CD, no containers in production |

### 1.2 Codebase Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| `dashboard/app.py` | **~8,940 lines** | Critical — single monolithic file containing all 28 views |
| Backend modules (`src/`) | **48 Python files** | Good modularity at the engine level |
| `src/market_scanner.py` | ~1,200+ lines | Largest backend module, manageable |
| `src/auth_manager.py` | ~620 lines | Well-structured auth with tier gating |
| `src/config.py` | ~200+ lines | Clean centralized config with override pipeline |
| `src/data_store.py` | ~100+ lines | Abstraction layer ready for DB swap |
| `src/performance_analytics.py` | ~587 lines | 9 chart functions, solid analytics |
| `src/risk_manager.py` | ~545 lines | Kelly sizing, VaR, correlation matrix |
| `src/portfolio_optimizer.py` | ~553 lines | Mean-variance optimization, scipy-backed |
| Total estimated LOC | **~25,000+** | Significant codebase for a prototype |
| Test files | **0** | No automated tests exist |
| CI/CD pipelines | **0** | No GitHub Actions, no automated deployment |

### 1.3 Technical Debt Inventory

#### Critical (Must Fix Before Scaling)

| # | Debt Item | Impact | Effort |
|---|-----------|--------|--------|
| 1 | **Single-file dashboard** (`app.py` at 8,940 lines) | Unmaintainable, merge conflicts, slow IDE, impossible to parallelize frontend work | 2-3 weeks to split into component modules |
| 2 | **JSON file storage** (no database) | No ACID transactions, no concurrent write safety beyond threading.Lock, data corruption risk at scale, no query capability | 2-4 weeks for PostgreSQL migration |
| 3 | **No API layer** (Streamlit calls Python directly) | Frontend and backend are coupled, no mobile/API clients possible, no horizontal scaling | 3-4 weeks for FastAPI REST layer |
| 4 | **Zero test coverage** | Every change is a regression risk, no confidence in refactoring, no CI/CD possible without tests | 4-6 weeks for baseline test suite |
| 5 | **No CI/CD** | Manual deployment, no automated quality gates, no rollback capability | 1-2 weeks for GitHub Actions pipeline |
| 6 | **File-based sessions** (`users/_active_session.json`) | Single-server only, no horizontal scaling, session loss on restart | 1 week for Redis session store |

#### High (Should Fix Within 3 Months)

| # | Debt Item | Impact |
|---|-----------|--------|
| 7 | **`importlib.reload()` hack** in app.py | Fragile hot-reload workaround for Streamlit caching; will break in multi-worker setup |
| 8 | **yfinance as sole data provider** | Free tier rate limits (~2,000 requests/day), no real-time data, no SLA |
| 9 | **Threading.Lock for file writes** | Process-level only; breaks with multiple Streamlit workers or containers |
| 10 | **Hardcoded 2026 dates** in economic_calendar.py | Manual maintenance burden, breaks every year |
| 11 | **No input sanitization** on user-facing forms | XSS/injection risk in Streamlit (partially mitigated by Streamlit's own escaping) |
| 12 | **No request rate limiting** on the application layer | DoS vulnerability, yfinance abuse risk |

#### Medium (Fix Within 6 Months)

| # | Debt Item | Impact |
|---|-----------|--------|
| 13 | No database migrations framework | Schema changes are manual JSON edits |
| 14 | No structured logging | Print statements and file writes, no log aggregation |
| 15 | No feature flags system | Feature gating is hardcoded sets in auth_manager.py |
| 16 | No error tracking/APM | Errors lost in log files, no alerting |
| 17 | No health check endpoints | No way to monitor service health programmatically |
| 18 | Duplicate path definitions | `app.py` and `config.py` both define PROJECT_ROOT, KANBAN_PATH, etc. |

### 1.4 What Works Well

These components are production-quality and should be preserved during migration:

1. **Authentication system** (`auth_manager.py`): PBKDF2-HMAC-SHA256 with random salt (100K iterations), proper tier definitions, email verification with rate limiting. This is solid cryptography — only the storage layer needs upgrading.

2. **Config pipeline** (`config.py`): Centralized configuration with `apply_settings_override()` that patches config classes at runtime. Backend engines call this on import. Clean separation of defaults and user overrides.

3. **DataStore abstraction** (`data_store.py`): Already designed for backend swap. The comment on line 5 literally says "Phase 2: Swap internals to PostgreSQL/Redis without changing callers." Shared vs. per-user data paths are cleanly separated.

4. **Signal scoring engine** (`market_scanner.py`): Multi-factor scoring (technical 40% + news 20% + historical 40%), parallelized with ThreadPoolExecutor, price sanity bounds with 5-day median fallback. This is core IP.

5. **Multi-agent orchestration** (`aegis_brain.py`): 7-step autonomous loop with budget-aware operation, error recovery, and self-improvement. Well-structured step-by-step execution with reporting.

6. **Sentiment pipeline**: Three-layer sentiment (RSS keywords + social/Reddit + influencer tracking) with negation detection and engagement weighting. Differentiated capability.

7. **Modular backend**: 48 modules with clear single-responsibility boundaries. `market_scanner.py`, `auto_trader.py`, `risk_manager.py`, `portfolio_optimizer.py` are each self-contained engines.

8. **Price sanity checks** (`PRICE_SANITY_BOUNDS` in config.py): Catches garbage yfinance data (like BTC at $64.97) with bounds validation and 5-day median fallback. Production-grade data quality guard.

---

## 2. Scalability Bottlenecks

### 2.1 At 100 Concurrent Users

**Timeline:** Month 1-3 after launch

| Bottleneck | Cause | Impact | Mitigation |
|------------|-------|--------|------------|
| JSON file contention | Multiple users writing to same JSON files simultaneously | Data corruption, lost writes, race conditions | `threading.Lock` helps for single-process only; fails with multiple workers |
| yfinance rate limits | Free tier: ~2,000 requests/day, 15-minute delay | API throttling, stale data, scan failures | Shared cache layer (Redis) + batch requests |
| Streamlit memory | Each user session consumes ~50-100MB RAM | 5-10GB RAM needed for 100 sessions | Vertical scaling (bigger server) |
| File-based sessions | `_active_session.json` read/written on every request | Session conflicts, slow auth checks | Redis session store |
| Sparkline generation | SVG sparklines generated per-user per-asset | Redundant computation, slow page loads | Pre-computed sparkline cache |

**Estimated infrastructure cost:** $200-500/month (single VPS with 16GB RAM)

### 2.2 At 1,000 Concurrent Users

**Timeline:** Month 4-6

| Bottleneck | Cause | Impact | Mitigation |
|------------|-------|--------|------------|
| Streamlit single-process | Streamlit runs one Python process per session | Cannot scale horizontally, 50-100GB RAM needed | FastAPI backend + React frontend |
| No caching layer | Every page load fetches fresh data from disk/yfinance | 12,000+ yfinance calls/hour, instant rate limiting | Redis caching (60s TTL for prices, 10min for analysis) |
| No CDN | Static assets (CSS, JS, fonts) served from application server | Wasted bandwidth, slow global load times | CloudFront or Cloudflare CDN |
| No background processing | Brain cycle runs inline or via manual `aegis_brain.py` | Blocks user requests, no reliable scheduling | Celery + Redis task queue |
| Per-user file directories | `users/{user_id}/` creates thousands of directories | Filesystem performance degrades, backup complexity | PostgreSQL with user_id foreign keys |

**Estimated infrastructure cost:** $2,000-5,000/month (multiple servers + managed DB)

### 2.3 At 10,000 Concurrent Users

**Timeline:** Month 7-12

| Bottleneck | Cause | Impact | Mitigation |
|------------|-------|--------|------------|
| Single-server architecture | No load balancing, single point of failure | One crash takes down all users | Kubernetes with 3+ replicas |
| No real-time data | yfinance provides 15-minute delayed data | Unacceptable for active traders | WebSocket feeds (Twelve Data, Binance) |
| Monolithic deployment | All 48 modules deploy as one unit | Slow deploys, can't scale hot modules independently | Service decomposition (Signal, Trading, User, Data) |
| No multi-region | All users hit single datacenter | High latency for EU/Asia users (>200ms) | Multi-region deployment (US-East + EU-West) |
| No read replicas | Single database instance | Read contention on portfolio/signal queries | PostgreSQL read replicas |

**Estimated infrastructure cost:** $15,000-25,000/month (Kubernetes cluster + managed services)

### 2.4 At 100,000 Concurrent Users

**Timeline:** Year 2+

| Bottleneck | Cause | Impact | Mitigation |
|------------|-------|--------|------------|
| Service coupling | Synchronous calls between services | Cascade failures, slow response under load | Event streaming (Kafka) for async communication |
| Data volume | Millions of signals, trades, predictions per day | Query performance, storage costs | TimescaleDB for time-series, S3 for archives |
| Global latency | Users on 4+ continents | >500ms for distant users | CDN + edge caching + 3 regional clusters |
| Real-time fanout | 100K users needing live price updates | WebSocket connection management | Dedicated WebSocket gateway service with pub/sub |
| Compliance | GDPR, SOC 2, data residency requirements | Legal risk, enterprise customer blockers | Data residency per region, audit logging |

**Estimated infrastructure cost:** $50,000-100,000/month (multi-region K8s + Kafka + managed DB clusters)

---

## 3. Technology Migration Roadmap

### Phase 1: Foundation (Month 1-3) — Target: $5,000/month infrastructure

**Goal:** Production-ready single-server deployment with real database, API layer, and CI/CD.

#### 3.1.1 PostgreSQL + Redis (Weeks 1-4)

**Replace JSON files with PostgreSQL for persistence and Redis for caching/sessions.**

```
Priority: P0 — blocks everything else
Effort: 2 backend engineers, 4 weeks
```

Schema design:
```sql
-- Core tables
users (id, email, password_hash, salt, tier, created_at, verified, language)
user_settings (user_id FK, settings_json, updated_at)
sessions (session_id, user_id FK, created_at, expires_at, ip_address)

-- Market data
watchlist_assets (id, user_id FK, asset_name, ticker, category, enabled)
scan_results (id, asset_name, signal, confidence, score, scanned_at)
market_predictions (id, asset_name, predicted_signal, confidence, created_at, validated_at, outcome)

-- Trading
paper_positions (id, user_id FK, asset_name, direction, entry_price, current_price, size, stop_loss, take_profit, opened_at, closed_at, pnl, notes)
trade_journal (id, position_id FK, user_id FK, event_type, details_json, created_at)

-- Intelligence
news_cache (id, asset_name, title, source, url, sentiment_score, fetched_at, expires_at)
social_sentiment (id, asset_name, influencer, platform, score, buzz_level, fetched_at)
alerts (id, user_id FK, asset_name, alert_type, threshold, triggered, created_at)

-- System
brain_cycles (id, started_at, completed_at, steps_json, errors_json)
error_lessons (id, agent, lesson, created_at)
daily_reflections (id, date, reflection_json)
```

Migration strategy:
1. Add SQLAlchemy models alongside existing JSON code
2. Write dual-write adapter in `data_store.py` (writes to both JSON and PostgreSQL)
3. Run parallel for 2 weeks to verify data consistency
4. Cut over to PostgreSQL, keep JSON as backup export format
5. Add Alembic for schema migrations

Redis usage:
- Session storage (replace `_active_session.json`)
- Price cache (60s TTL, eliminates redundant yfinance calls)
- Scan result cache (5min TTL)
- Rate limiting counters (sliding window)
- Pub/sub for real-time updates (future)

**Cost:** PostgreSQL managed (Hetzner): $15/month | Redis managed: $10/month

#### 3.1.2 FastAPI REST Layer (Weeks 3-6)

**Decouple frontend from backend with a proper API.**

```
Priority: P0 — enables frontend migration, mobile clients, horizontal scaling
Effort: 2 backend engineers, 4 weeks (overlaps with DB migration)
```

API structure:
```
/api/v1/
  /auth/
    POST /login
    POST /register
    POST /logout
    POST /verify-email
    GET  /me
  /market/
    GET  /watchlist
    GET  /scan/{asset}
    GET  /scan/all
    GET  /signals
    GET  /sentiment/{asset}
    GET  /news/{asset}
    GET  /calendar
    GET  /morning-brief
  /trading/
    GET  /portfolio
    POST /trade
    PATCH /position/{id}
    DELETE /position/{id}
    GET  /journal
  /analysis/
    GET  /chart/{asset}
    GET  /risk-dashboard
    GET  /correlations
    GET  /optimizer
    GET  /analytics
  /settings/
    GET  /
    PUT  /
  /admin/
    GET  /brain-status
    POST /brain-cycle
    GET  /health
```

Key decisions:
- JWT tokens (access: 15min, refresh: 7 days) replace file-based sessions
- OpenAPI/Swagger auto-generated documentation
- Pydantic models for request/response validation
- CORS middleware for cross-origin React frontend
- Background task runner for long operations (scans, brain cycles)

#### 3.1.3 Docker + docker-compose (Weeks 2-3)

**Containerized deployment for consistency across environments.**

```
Priority: P1 — enables reproducible deploys
Effort: 1 DevOps engineer, 2 weeks
```

Services:
```yaml
services:
  api:        # FastAPI backend (2 workers)
  dashboard:  # Streamlit frontend (temporary, until React migration)
  postgres:   # PostgreSQL 16
  redis:      # Redis 7
  worker:     # Celery worker (brain cycles, scans)
  beat:       # Celery beat (scheduled tasks)
  nginx:      # Reverse proxy + TLS termination
```

Note: Existing `Dockerfile` and `docker-compose.yml` from Sprint 10 provide a starting point but need significant updates for the new architecture.

#### 3.1.4 GitHub Actions CI/CD (Weeks 3-4)

**Automated testing, building, and deployment.**

```
Priority: P1 — quality gate before any production deploy
Effort: 1 DevOps engineer, 1 week
```

Pipeline:
```
Push to main →
  1. Lint (ruff, mypy)
  2. Unit tests (pytest, target 60% coverage)
  3. Integration tests (API endpoints, DB operations)
  4. Docker build + push to registry
  5. Deploy to staging
  6. Smoke tests on staging
  7. Manual approval gate
  8. Deploy to production
  9. Health check + rollback on failure
```

#### 3.1.5 Basic Monitoring (Weeks 4-6)

```
Priority: P1
Effort: 1 DevOps engineer, 1 week
```

- **Sentry**: Error tracking + performance monitoring ($29/month)
- **UptimeRobot**: Uptime monitoring + alerting (free tier)
- **Structured logging**: Replace print statements with Python `logging` + JSON formatter
- **Health endpoint**: `/api/v1/admin/health` returns DB, Redis, yfinance status
- **Grafana + Prometheus**: Basic dashboards for request latency, error rates, DB connections (self-hosted, $0)

#### Phase 1 Cost Summary

| Item | Monthly Cost |
|------|-------------|
| Hetzner VPS (CX41: 8 vCPU, 16GB RAM) | $30 |
| Managed PostgreSQL (Hetzner) | $15 |
| Managed Redis (Hetzner) | $10 |
| Sentry (Team plan) | $29 |
| GitHub Actions (free tier) | $0 |
| Domain + TLS (Let's Encrypt) | $15 |
| **Total** | **~$100/month** |
| **Engineering cost** (3 engineers x 3 months x $12K avg) | **$108,000** |
| **Phase 1 Total (3 months)** | **~$108,300** |

---

### Phase 2: Scale (Month 4-6) — Target: $15,000/month infrastructure

**Goal:** Handle 1,000+ concurrent users with real-time data and proper frontend.

#### 3.2.1 Split app.py into Component Modules (Weeks 1-3)

**The 8,940-line monolith must die.**

```
Priority: P0 — blocks frontend parallelization
Effort: 2 frontend engineers, 3 weeks
```

Decomposition plan (if staying Streamlit temporarily):
```
dashboard/
  app.py              → 200 lines (router + layout only)
  components/
    sidebar.py         → Navigation + portfolio ticker
    auth_forms.py      → Login/register/verify
    page_header.py     → Breadcrumb + back button
  views/
    trading/
      advisor.py       → Daily Advisor (default)
      watchlist.py     → Watchlist with sparklines
      charts.py        → Technical charts + trendlines
      paper_trading.py → Paper trading + bot controls
      trade_journal.py → Trade journal + export
      morning_brief.py → Morning Brief
      alerts.py        → Alert management
      asset_detail.py  → Single-asset deep dive
      watchlist_mgr.py → Watchlist manager
    intelligence/
      news_intel.py    → News Intelligence (4 tabs)
      econ_calendar.py → Economic Calendar
      report_card.py   → Signal Report Card
      fundamentals.py  → Fundamentals view
      strategy_lab.py  → Strategy Lab
      analytics.py     → Performance Analytics
      risk_dashboard.py → Risk Dashboard
      optimizer.py     → Portfolio Optimizer
      market_overview.py → Market Overview
    system/
      kanban.py        → Task board
      evolution.py     → System evolution
      performance.py   → Agent performance
      monitor.py       → Agent monitor
      budget.py        → Budget tracker
      logs.py          → Live logs
      settings.py      → Settings page
```

This decomposition is an intermediate step. The real target is React (Phase 3).

#### 3.2.2 React Migration Begins (Weeks 2-12)

**Start building the React + TypeScript frontend in parallel with Streamlit.**

```
Priority: P0 — long-lead item, start early
Effort: 2 senior frontend engineers, ongoing through Phase 3
```

Stack:
- React 18 + TypeScript
- TanStack Query (data fetching + caching)
- Zustand (state management)
- Recharts or Plotly.js (charting)
- Tailwind CSS (styling — already used in landing page)
- Vite (build tool)

Migration order (by user value and complexity):
1. Login/Register/Auth flows
2. Daily Advisor (default landing page)
3. Watchlist with sparklines
4. Charts page (Plotly.js direct port)
5. Paper Trading
6. News Intelligence
7. Remaining views in priority order

#### 3.2.3 Kubernetes Deployment (Weeks 4-8)

**Move from single docker-compose to orchestrated deployment.**

```
Priority: P1 — needed before 500+ users
Effort: 1 senior DevOps engineer, 4 weeks
```

Target: Hetzner Cloud (cost-effective) or AWS EKS (if enterprise customers require it)

Cluster specification:
- 3 worker nodes (4 vCPU, 8GB RAM each)
- Ingress controller (nginx-ingress or Traefik)
- Cert-manager for TLS
- Horizontal Pod Autoscaler on API pods
- PersistentVolumeClaims for PostgreSQL (if self-managed)

#### 3.2.4 WebSocket Layer for Real-Time Prices (Weeks 6-10)

**Replace yfinance polling with streaming price data.**

```
Priority: P1 — required for serious traders
Effort: 1 backend engineer, 4 weeks
```

Data provider evaluation:
| Provider | Cost | Assets | Latency | Recommendation |
|----------|------|--------|---------|---------------|
| Twelve Data | $79-299/month | Stocks, Forex, Crypto | 1-5s | Best value for Phase 2 |
| Binance WebSocket | Free | Crypto only | <100ms | Add for BTC/ETH |
| Finnhub | $0-149/month | US stocks | 1-15s | Good free tier |
| Polygon.io | $199/month | Full US market | <1s | Phase 3 |

Architecture:
```
Market Data Service
  ├── WebSocket connections to providers
  ├── Price normalization + validation (reuse PRICE_SANITY_BOUNDS)
  ├── Redis pub/sub for internal distribution
  └── WebSocket server for frontend clients
```

#### 3.2.5 Celery + Redis Task Queue (Weeks 4-6)

**Replace `aegis_brain.py` loop with proper background task processing.**

```
Priority: P1 — reliability + scalability of background work
Effort: 1 backend engineer, 2 weeks
```

Task definitions:
```python
# Periodic tasks (Celery Beat)
scan_all_assets          → every 5 minutes
social_sentiment_scan    → every 15 minutes
validate_predictions     → every 1 hour
chief_monitor_reflection → daily at 00:00 UTC
morning_brief_generation → daily at 06:00 UTC

# On-demand tasks
scan_single_asset(asset_name)
execute_paper_trade(trade_params)
generate_report(user_id)
run_backtest(strategy_params)
optimize_portfolio(user_id, params)
```

#### 3.2.6 APM Monitoring (Weeks 8-10)

```
Priority: P2
Effort: 1 DevOps engineer, 1 week
```

- **Datadog** or **Grafana Cloud**: Full APM with distributed tracing ($23/host/month for Datadog, free tier for Grafana Cloud)
- Custom dashboards: API latency p50/p95/p99, error rates by endpoint, DB query performance
- Alerts: >500ms p95 latency, >1% error rate, DB connection pool exhaustion

#### Phase 2 Cost Summary

| Item | Monthly Cost |
|------|-------------|
| Hetzner K8s cluster (3 nodes) | $120 |
| Managed PostgreSQL (HA) | $50 |
| Managed Redis (HA) | $30 |
| Twelve Data (Pro plan) | $149 |
| Sentry (Business) | $89 |
| Grafana Cloud (Pro) | $49 |
| Domain + CDN (Cloudflare Pro) | $25 |
| **Infrastructure Total** | **~$512/month** |
| **Engineering cost** (5 engineers x 3 months x $12K avg) | **$180,000** |
| **Phase 2 Total (3 months)** | **~$181,500** |

---

### Phase 3: Production (Month 7-12) — Target: $50,000/month infrastructure

**Goal:** Full production SaaS platform handling 10,000+ concurrent users with enterprise-grade reliability.

#### 3.3.1 Full React + TypeScript Frontend (Months 7-10)

**Complete Streamlit-to-React migration for all 28 views.**

```
Priority: P0 — Streamlit cannot scale beyond ~500 concurrent users
Effort: 3 frontend engineers, 4 months
```

Component architecture:
```
src/
  components/
    layout/        → Sidebar, Header, PageWrapper, Breadcrumb
    trading/       → SignalCard, SparklineChart, TradeForm, PositionCard
    charts/        → TechnicalChart, CandlestickChart, TrendlineOverlay
    intelligence/  → NewsCard, SentimentGauge, CalendarEvent
    shared/        → DataTable, MetricCard, LoadingSpinner, ErrorBoundary
  pages/           → One file per view (28 pages)
  hooks/           → useMarketData, usePortfolio, useSignals, useWebSocket
  stores/          → authStore, marketStore, tradingStore, settingsStore
  api/             → Typed API client (auto-generated from OpenAPI spec)
  types/           → TypeScript interfaces matching Pydantic models
```

Key frontend features:
- Server-sent events (SSE) or WebSocket for live price updates
- Offline-capable with service worker (show cached data when offline)
- Dark/light theme toggle (currently dark-only)
- Responsive design (mobile-first, replace current desktop-only Streamlit)
- Keyboard shortcuts for power users (Bloomberg-style)

#### 3.3.2 Microservices Decomposition (Months 8-12)

**Split the monolithic Python backend into focused services.**

```
Priority: P1 — enables independent scaling and deployment
Effort: 3 backend engineers, 4 months
```

Service boundaries:
```
┌─────────────────────────────────────────────────────┐
│                    API Gateway                       │
│              (nginx / Kong / Traefik)                │
└─────┬──────┬──────┬──────┬──────┬──────┬───────────┘
      │      │      │      │      │      │
┌─────┴─┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴──┐ ┌──┴────┐
│ User  │ │Signal│ │Trade│ │Data │ │News │ │Brain  │
│Service│ │Svc   │ │ Svc │ │ Svc │ │ Svc │ │ Svc   │
└───────┘ └──────┘ └─────┘ └─────┘ └─────┘ └───────┘
```

| Service | Modules Absorbed | Scaling Pattern |
|---------|-----------------|-----------------|
| **User Service** | auth_manager, i18n, data_store (user ops) | Low CPU, scales with user count |
| **Signal Service** | market_scanner, chart_engine, strategy_builder, backtester, hyperopt_engine | CPU-intensive, auto-scale on scan load |
| **Trading Service** | auto_trader, paper_trader, risk_manager, portfolio_optimizer, alert_manager | Medium CPU, scales with trade volume |
| **Data Service** | config, data_store (market ops), market_discovery, fundamentals, sector_analysis | I/O-intensive, cache-heavy |
| **News Service** | news_researcher, social_sentiment, geopolitical_monitor, morning_brief, economic_calendar | I/O-intensive, scheduled batch processing |
| **Brain Service** | aegis_brain, autonomous_manager, chief_monitor, market_learner, memory_manager | Background processing, single instance with leader election |

#### 3.3.3 Kafka Event Streaming (Months 9-12)

**Asynchronous event-driven communication between services.**

```
Priority: P2 — needed at 10K+ users for decoupling
Effort: 1 backend engineer + 1 DevOps engineer, 6 weeks
```

Event topics:
```
aegis.market.prices       → Real-time price updates
aegis.market.signals      → New signal generated
aegis.trading.orders      → Trade executed
aegis.trading.alerts      → Alert triggered
aegis.news.articles       → New article ingested
aegis.news.sentiment      → Sentiment score updated
aegis.user.actions        → User activity (analytics)
aegis.brain.cycles        → Brain cycle completed
```

#### 3.3.4 Multi-Region Deployment (Months 10-12)

```
Priority: P2 — needed for EU users (GDPR) and latency
Effort: 1 senior DevOps engineer, 4 weeks
```

Regions:
- **US-East** (primary): us-east-1 (AWS) or fsn1 (Hetzner)
- **EU-West** (secondary): eu-central-1 (AWS) or nbg1 (Hetzner)
- PostgreSQL cross-region replication (read replicas in EU)
- Redis cluster per region
- CloudFront CDN for static assets globally

#### 3.3.5 CDN + Static Asset Optimization (Month 7-8)

```
Priority: P1
Effort: 1 frontend engineer, 1 week
```

- CloudFront or Cloudflare for React build artifacts
- Image optimization (WebP for charts, lazy loading)
- Brotli compression for API responses
- Cache headers: immutable for hashed assets, 5min for API responses

#### Phase 3 Cost Summary

| Item | Monthly Cost |
|------|-------------|
| AWS EKS / Hetzner K8s (2 regions, 6+ nodes) | $1,200 |
| Managed PostgreSQL (HA, 2 regions) | $400 |
| Managed Redis (HA, 2 regions) | $200 |
| Kafka (Confluent Cloud or self-managed) | $500 |
| Twelve Data (Enterprise) | $299 |
| Polygon.io (Starter) | $199 |
| Datadog (APM + Infrastructure) | $500 |
| Sentry (Business) | $89 |
| CloudFront CDN | $100 |
| Domain + DNS (Route 53) | $50 |
| **Infrastructure Total** | **~$3,537/month** |
| **Engineering cost** (8 engineers x 6 months x $12K avg) | **$576,000** |
| **Phase 3 Total (6 months)** | **~$597,222** |

---

## 4. Engineering Team Scaling Plan

### 4.1 Current State: 1 Developer (Solo Founder)

The entire codebase was built by a single developer. This is both impressive (velocity, coherent vision) and dangerous (bus factor = 1, no code review, no QA).

### 4.2 First 5 Hires (Month 1-3) — Core Team

| # | Role | Focus | Why First |
|---|------|-------|-----------|
| 1 | **Senior Backend Engineer (FastAPI)** | API layer, DB migration, service architecture | Unblocks all backend scaling |
| 2 | **Senior Frontend Engineer (React/TS)** | React migration, component library | Unblocks Streamlit replacement |
| 3 | **DevOps / Platform Engineer** | CI/CD, Docker, K8s, monitoring | Unblocks automated deployment |
| 4 | **QA Lead / SDET** | Test framework, E2E tests, regression suite | Unblocks confident refactoring |
| 5 | **Data Engineer** | PostgreSQL migration, data pipeline, market data feeds | Unblocks JSON-to-DB transition |

**Estimated salary cost:** $600K-$800K/year (US market, remote-friendly)

### 4.3 Scale to 20 (Month 4-12) — Feature Teams

| # | Role | Team |
|---|------|------|
| 6-7 | 2x Backend Engineers | Signal Service, Trading Service |
| 8-9 | 2x Frontend Engineers | Dashboard views, mobile-responsive |
| 10 | Mobile Engineer (React Native) | iOS/Android app |
| 11 | ML Engineer | Signal model improvement, prediction accuracy |
| 12 | DBA / Data Engineer | PostgreSQL optimization, data pipelines |
| 13 | Security Engineer | Penetration testing, SOC 2 prep, audit |
| 14 | Product Manager | Feature prioritization, user research |
| 15-16 | 2x Full-Stack Engineers | Feature development velocity |
| 17 | SRE / On-Call Engineer | Incident response, reliability |
| 18 | Technical Writer | API docs, user guides |
| 19 | Designer (UI/UX) | Design system, user flows |
| 20 | Engineering Manager | Team coordination, 1:1s, hiring |

**Estimated salary cost:** $2.5M-$3.5M/year

### 4.4 Scale to 50 (Year 2) — Sub-Teams

```
Engineering (50 people)
├── Platform Team (8)
│   ├── Team Lead
│   ├── 3x Backend (API gateway, shared services)
│   ├── 2x DevOps/SRE
│   └── 2x Data Engineers
├── Trading Team (10)
│   ├── Team Lead
│   ├── 4x Backend (signal engine, auto-trader, risk)
│   ├── 3x Frontend (trading views)
│   └── 2x QA
├── Intelligence Team (8)
│   ├── Team Lead
│   ├── 3x Backend (news, sentiment, calendar)
│   ├── 2x ML Engineers
│   └── 2x Frontend
├── Growth Team (8)
│   ├── Team Lead
│   ├── 3x Full-Stack (onboarding, engagement, referrals)
│   ├── 2x Frontend
│   └── 2x Mobile (React Native)
├── Security & Compliance (4)
│   ├── Security Lead
│   ├── 2x Security Engineers
│   └── 1x Compliance Specialist
├── QA Team (4)
│   ├── QA Lead
│   └── 3x SDET
├── Design (3)
│   ├── Design Lead
│   ├── 1x Product Designer
│   └── 1x UX Researcher
├── VP Engineering
├── 2x Engineering Managers
└── 2x Product Managers
```

### 4.5 Target: 300 (Per ORG_STRUCTURE.md)

Full organizational structure as defined in the existing `docs/reports/ORG_STRUCTURE.md`. Engineering would comprise approximately 120-150 of the 300 headcount, with the remainder split across Product, Design, Sales, Marketing, Support, Legal, Finance, and Operations.

---

## 5. Security Assessment

### 5.1 Current Security Posture

#### What We Have (Good)

| Control | Implementation | Assessment |
|---------|---------------|------------|
| Password hashing | PBKDF2-HMAC-SHA256, 100K iterations, random salt | Industry-standard, OWASP-compliant |
| Per-user data isolation | Separate directories per user_id | Effective for file-based storage |
| Email verification | 6-digit code, 15min TTL, rate-limited | Good — 5 attempts/15min, 3 resends/hr |
| Feature gating | Tier-based view access control | Functional, needs enforcement at API level |
| Price sanity checks | Bounds validation with fallback | Prevents data manipulation from bad sources |
| Guest mode isolation | Default user_id, no cross-contamination | Acceptable for demo purposes |

#### What We Are Missing (Critical Gaps)

| Gap | Risk Level | Impact | Remediation |
|-----|-----------|--------|-------------|
| **No CSRF protection** | HIGH | Cross-site request forgery on trade execution | Add CSRF tokens to all state-changing endpoints |
| **No rate limiting on application layer** | HIGH | DoS, brute-force attacks on login | Redis-based rate limiter (flask-limiter or FastAPI middleware) |
| **No input sanitization** | HIGH | XSS, injection (partially mitigated by Streamlit) | Input validation on all API endpoints (Pydantic) |
| **No session expiry** | MEDIUM | Stolen sessions never expire | JWT with 15min access + 7day refresh tokens |
| **No Content Security Policy** | MEDIUM | XSS amplification | CSP headers on all responses |
| **No audit logging** | MEDIUM | Cannot trace who did what | Audit log table for all state-changing operations |
| **No secrets management** | MEDIUM | SMTP credentials in env vars, no rotation | HashiCorp Vault or AWS Secrets Manager |
| **No HTTPS enforcement** | HIGH | Credentials transmitted in cleartext | TLS termination at nginx/ingress |
| **No SQL injection prevention** | HIGH (future) | Required when PostgreSQL is added | Parameterized queries via SQLAlchemy ORM |
| **No penetration testing** | MEDIUM | Unknown vulnerabilities | Annual pentest starting Month 6 |

### 5.2 SOC 2 Type I Roadmap (6-Month Plan)

SOC 2 Type I certification is required for enterprise customers (Command tier at $199/month). Estimated cost: $30K-$50K for audit + tooling.

| Month | Activity |
|-------|----------|
| 1 | Gap assessment against Trust Service Criteria (TSC). Engage compliance consultant |
| 2 | Implement access controls: RBAC, MFA for admin, audit logging |
| 3 | Implement infrastructure controls: encryption at rest (PostgreSQL), encryption in transit (TLS everywhere), backup verification |
| 4 | Implement operational controls: incident response plan, change management process, employee security training |
| 5 | Evidence collection: 30 days of logs, access reviews, vulnerability scans |
| 6 | SOC 2 Type I audit by independent auditor (Vanta, Drata, or similar platform to streamline) |

### 5.3 GDPR Compliance Checklist

| Requirement | Status | Action |
|-------------|--------|--------|
| Data processing register | Missing | Document all personal data flows |
| Right to deletion | Partial | Need API endpoint + cascade delete |
| Right to export | Missing | Need data export endpoint (JSON/CSV) |
| Cookie consent | Missing | Add consent banner (landing page) |
| Privacy policy | Missing | Legal review + publish |
| DPA with sub-processors | Missing | Required for yfinance, SMTP provider |
| Data residency | Not addressed | EU region deployment in Phase 3 |

---

## 6. DevOps & CI/CD Roadmap

### 6.1 Current State: Zero Automation

```
Developer laptop → run.bat → Streamlit starts → hope for the best
```

There is no version control workflow (no branch protection, no PR reviews), no automated testing, no deployment pipeline, no rollback capability, and no monitoring. A single bad commit can take down the entire application with no way to recover except manual intervention.

### 6.2 Target State: Full CI/CD with Progressive Delivery

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Commit  │───→│   CI     │───→│  Staging  │───→│  Canary  │───→│Production│
│  + Push  │    │  Pipeline│    │  Deploy   │    │  (10%)   │    │  (100%)  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │                │               │               │
                 ┌───┴───┐       ┌───┴───┐      ┌───┴───┐     ┌───┴───┐
                 │ Lint  │       │ Smoke │      │Monitor│     │Health │
                 │ Test  │       │ Tests │      │Errors │     │ Check │
                 │ Build │       │ E2E   │      │Latency│     │Rollback│
                 │ Scan  │       │       │      │       │     │       │
                 └───────┘       └───────┘      └───────┘     └───────┘
```

### 6.3 Implementation Phases

#### Phase A: Basic CI (Week 1-2)

```yaml
# .github/workflows/ci.yml
name: CI Pipeline
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff mypy
      - run: ruff check src/ dashboard/
      - run: mypy src/ --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:16, env: {...} }
      redis: { image: redis:7 }
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -v --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
      - run: pip install bandit safety
      - run: bandit -r src/ -ll
      - run: safety check
```

#### Phase B: Docker Build + Deploy (Week 3-4)

```yaml
  build:
    needs: [lint, test, security]
    steps:
      - run: docker build -t aegis-api:${{ github.sha }} .
      - run: docker push ghcr.io/project-aegis/api:${{ github.sha }}

  deploy-staging:
    needs: build
    environment: staging
    steps:
      - run: kubectl set image deployment/api api=ghcr.io/project-aegis/api:${{ github.sha }}
      - run: kubectl rollout status deployment/api --timeout=120s

  deploy-production:
    needs: deploy-staging
    environment:
      name: production
      url: https://app.projectaegis.com
    steps:
      - run: kubectl set image deployment/api api=ghcr.io/project-aegis/api:${{ github.sha }}
      - run: ./scripts/smoke-test.sh https://app.projectaegis.com
```

#### Phase C: Progressive Delivery (Month 4+)

- Canary deployments: 10% traffic to new version, monitor error rates, auto-promote or rollback
- Feature flags (LaunchDarkly or Unleash self-hosted) for gradual rollouts
- Database migration safety: Alembic with `--autogenerate`, always backward-compatible changes
- Blue-green deployments for zero-downtime releases

### 6.4 Branch Strategy

```
main (protected)
  ├── develop (integration branch)
  │   ├── feature/AEGIS-123-react-advisor
  │   ├── feature/AEGIS-124-postgres-migration
  │   └── fix/AEGIS-125-sparkline-cache
  └── release/v1.0.0
      └── hotfix/v1.0.1
```

Rules:
- `main` requires 1 approval + passing CI
- `develop` requires passing CI
- Feature branches: squash merge to develop
- Release branches: merge to main with tag
- Hotfix: cherry-pick from main, backport to develop

---

## 7. Key Technical Decisions

### 7.1 Streamlit to React: When and Why

**Decision:** Begin React migration in Month 4, complete by Month 10.

**Why not keep Streamlit?**
- Streamlit runs one Python process per user session (~50-100MB RAM each)
- At 500 concurrent users: 25-50GB RAM just for the frontend
- No component reuse, no design system, no accessibility
- 8,940-line single file is unmaintainable
- No mobile support (Streamlit is desktop-only)
- No offline capability
- No fine-grained state management (everything in `st.session_state`)

**Why not migrate immediately?**
- Current Streamlit app works and generates user value
- React migration is a 4-month effort minimum
- Better to stabilize backend (DB, API) first, then swap frontend
- Streamlit can serve 100-200 users while React is built in parallel

**Trigger for urgency:** If we hit 500 concurrent users before React is ready, we scale Streamlit horizontally with sticky sessions (temporary, expensive) as a bridge.

### 7.2 JSON to PostgreSQL: Day 1 Priority

**Decision:** PostgreSQL migration is the single highest priority engineering task.

**Why Day 1?**
- JSON files have no ACID guarantees — concurrent writes corrupt data
- `threading.Lock` only works within a single process — useless with multiple workers
- No query capability (want "show all trades with PnL > $100" — requires loading all JSON into memory)
- No referential integrity (orphaned records, inconsistent state)
- No backup strategy (file copy is not a backup)
- DataStore abstraction (`data_store.py`) was explicitly designed for this swap

**Migration risk:** LOW. The DataStore pattern means callers do not change. We replace the internal `_read_json` / `_write_json` methods with SQLAlchemy queries. Dual-write period ensures zero data loss.

### 7.3 Monolith to Microservices: After 10K Users, Not Before

**Decision:** Stay monolithic (single FastAPI application) through Phase 2. Decompose into microservices only when scaling demands it.

**Why not microservices from Day 1?**
- Distributed systems are 10x harder to debug, deploy, and monitor
- Network latency between services adds 2-5ms per hop
- Team of 5 cannot maintain 6 separate services
- Premature decomposition creates wrong service boundaries
- A well-structured monolith (FastAPI with clean module boundaries) scales to 10K users

**When to decompose:**
- Signal Service: When scan load exceeds what one service can handle (10K+ scans/hour)
- Trading Service: When trade volume requires independent scaling
- News Service: When RSS/social scraping needs isolation from user-facing services

**How to prepare now:**
- Clean module boundaries in the FastAPI app (already exist in `src/`)
- Shared-nothing architecture (no global state between modules)
- Database schema that supports future service ownership (clear foreign key boundaries)
- API versioning from Day 1 (`/api/v1/`)

### 7.4 Language Choice: Python Backend, TypeScript Frontend

**Decision:** Keep Python for all backend services. TypeScript only for the React frontend.

**Why keep Python?**
- 48 existing modules, ~25,000+ lines of working domain logic
- Team expertise (solo founder, likely first hires)
- yfinance, pandas, numpy, scipy, plotly — all Python ecosystem
- FastAPI performance is excellent (async, Uvicorn, comparable to Node.js for I/O-bound work)
- ML/data science future features are Python-native

**Why TypeScript for frontend?**
- React ecosystem is TypeScript-first
- Type safety catches bugs at compile time (critical for financial data display)
- Better IDE support for large frontend codebases
- Industry standard for production web applications

### 7.5 Hosting: Hetzner First, AWS Later

**Decision:** Start on Hetzner Cloud (Phase 1-2), migrate to AWS if enterprise customers require it (Phase 3).

**Why Hetzner first?**
- 60-80% cheaper than AWS for equivalent compute
- GDPR-compliant EU datacenters (German company)
- Managed PostgreSQL and Kubernetes available
- Sufficient for 0-10K users
- Existing deployment files reference Hetzner ($4/month VPS)

**When to consider AWS:**
- Enterprise customers require AWS PrivateLink / VPC peering
- Need managed Kafka (MSK), managed Elasticsearch, or other AWS-only services
- Multi-region beyond EU + US-East
- SOC 2 auditors prefer AWS (more established compliance documentation)

---

## 8. Cost Summary & Timeline

### 8.1 Year 1 Total Cost Projection

| Phase | Timeline | Infrastructure/Month | Engineering Cost | Phase Total |
|-------|----------|---------------------|------------------|-------------|
| Phase 1: Foundation | Month 1-3 | $100 | $108,000 | $108,300 |
| Phase 2: Scale | Month 4-6 | $512 | $180,000 | $181,536 |
| Phase 3: Production | Month 7-12 | $3,537 | $576,000 | $597,222 |
| **Year 1 Total** | | | | **~$887,058** |

### 8.2 Year 1 Infrastructure Cost Growth

```
Month  1: $100   ████
Month  2: $100   ████
Month  3: $100   ████
Month  4: $300   ████████████
Month  5: $400   ████████████████
Month  6: $512   ████████████████████
Month  7: $1,500 ████████████████████████████████████████████████████████████
Month  8: $2,000 ████████████████████████████████████████████████████████████████████████████████
Month  9: $2,500 ████████████████████████████████████████████████████████████████████████████████████████████████████
Month 10: $3,000 ████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
Month 11: $3,500 ████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
Month 12: $3,537 ████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████
```

### 8.3 Revenue Break-Even Analysis

Assuming pricing: Free ($0), Operator ($29/month), Command ($199/month).

| Scenario | Paying Users Needed | Monthly Revenue | Break-Even |
|----------|-------------------|-----------------|------------|
| Phase 1 costs ($100/mo infra) | 4 Operator | $116 | Month 2 (infra only) |
| Phase 2 costs ($512/mo infra) | 18 Operator | $522 | Month 5 (infra only) |
| Phase 3 costs ($3,537/mo infra) | 18 Command | $3,582 | Month 10 (infra only) |
| Full Year 1 (incl. eng salaries) | 250 Operator + 20 Command | $11,230/mo | Month 18-24 |

### 8.4 Milestone Timeline

```
Month 1  ─── PostgreSQL migration begins, CI/CD pipeline live
Month 2  ─── FastAPI API layer v1 deployed, Docker in production
Month 3  ─── Database migration complete, file-based storage retired
             ✓ Phase 1 complete: Production-ready single server
Month 4  ─── React frontend development begins, app.py decomposition
Month 5  ─── Kubernetes deployment, WebSocket price feeds
Month 6  ─── Celery task queue replaces brain loop, React MVP (5 views)
             ✓ Phase 2 complete: 1,000-user capacity
Month 7  ─── React migration accelerates (15+ views)
Month 8  ─── Service boundary planning, Kafka evaluation
Month 9  ─── Full React frontend, Streamlit decommissioned
Month 10 ─── Multi-region deployment (US + EU)
Month 11 ─── SOC 2 Type I audit begins
Month 12 ─── Microservice extraction begins for Signal Service
             ✓ Phase 3 complete: 10,000-user capacity, enterprise-ready
```

---

## 9. Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | yfinance API changes or gets rate-limited aggressively | HIGH | Service degradation for all users | Multi-provider fallback (Twelve Data, Finnhub), aggressive caching |
| R2 | PostgreSQL migration causes data loss | LOW | Loss of user portfolios and trade history | Dual-write period, JSON backup exports, migration dry runs |
| R3 | React migration takes longer than 4 months | MEDIUM | Stuck on Streamlit, scaling ceiling at 500 users | Horizontal Streamlit scaling as bridge (sticky sessions + load balancer) |
| R4 | Key engineer leaves during migration | MEDIUM | Knowledge loss, timeline slip | Documentation, pair programming, no single-owner modules |
| R5 | Reddit blocks free JSON API access | MEDIUM | Social sentiment engine breaks | Backup: official Reddit API ($100/month) or switch to Twitter/X API |
| R6 | Security breach before SOC 2 | LOW | Reputation damage, user data exposure | Prioritize HTTPS, rate limiting, and input validation in Phase 1 |
| R7 | Streamlit drops backward compatibility | LOW | Dashboard breaks on update | Pin Streamlit version, migrate to React faster |
| R8 | Cost overruns on engineering hires | MEDIUM | Budget exhaustion before revenue | Remote-first hiring (global talent pool), contractor bridge for Phase 1 |
| R9 | yfinance price data quality issues recur | HIGH | Bad signals, bad trades, user trust loss | Price sanity bounds (already implemented), multi-source validation |
| R10 | Regulatory action (classified as investment advisor) | LOW | Forced registration or shutdown | Publisher's exclusion defense (see REGULATORY.md), prominent disclaimers |

---

## Appendix: Module Inventory

### Backend Modules (`src/`) — 48 Files

| Module | Lines (est.) | Purpose | Migration Priority |
|--------|-------------|---------|-------------------|
| `market_scanner.py` | 1,200+ | Asset scanning, signal scoring, ThreadPoolExecutor parallelization | P0 — core IP |
| `auth_manager.py` | 620 | Authentication, tiers, email verification, feature gating | P0 — user management |
| `performance_analytics.py` | 587 | Sharpe ratio, drawdown, 9 chart functions | P1 — analytics |
| `portfolio_optimizer.py` | 553 | Mean-variance optimization, efficient frontier (scipy) | P1 — pro feature |
| `risk_manager.py` | 545 | Kelly sizing, VaR, exposure limits, correlation matrix | P0 — risk engine |
| `auto_trader.py` | 500+ | 12+ gate system, regime-aware paper trading | P0 — trading engine |
| `social_sentiment.py` | 400+ | Influencer tracking, Reddit scraping, buzz scoring | P1 — intelligence |
| `chart_engine.py` | 400+ | Technical indicators, chart JSON, auto-trendlines, S/R detection | P0 — charting |
| `paper_trader.py` | 350+ | Portfolio simulation, trade notes, position modification | P0 — trading |
| `news_researcher.py` | 350+ | RSS feeds, weighted keyword sentiment, negation detection | P1 — intelligence |
| `watchlist_manager.py` | 275 | Multiple named watchlists, presets, CRUD operations | P1 — user feature |
| `report_generator.py` | 272 | Self-contained HTML performance reports | P2 — export |
| `config.py` | 200+ | Central config, settings override pipeline, price sanity bounds | P0 — infrastructure |
| `data_store.py` | 150+ | JSON I/O abstraction, user isolation, atomic writes | P0 — data layer |
| `aegis_brain.py` | 150+ | Main orchestration loop, 7-step autonomous cycle | P0 — core engine |
| `economic_calendar.py` | 200+ | 15 event types, countdowns, impact ratings | P1 — intelligence |
| `geopolitical_monitor.py` | 200+ | 8 event types, asset impact mapping | P2 — intelligence |
| `macro_regime.py` | 150+ | Risk-On/Off/Inflationary/Deflationary/Volatile detection | P1 — regime |
| `morning_brief.py` | 150+ | Auto-generated daily market summary | P2 — content |
| `i18n.py` | 200+ | 3 languages, 81 translation keys, RTL support | P1 — i18n |
| `fundamentals.py` | 150+ | Earnings, valuations, analyst targets | P2 — data |
| `sector_analysis.py` | 150+ | Cross-market correlations, breadth | P2 — analytics |
| `market_learner.py` | 150+ | Prediction tracking, validation, accuracy scoring | P1 — learning |
| `chief_monitor.py` | 100+ | Daily health checks, reflections | P2 — monitoring |
| `autonomous_manager.py` | 100+ | Budget-aware autonomous decisions | P2 — orchestration |
| `strategy_builder.py` | 100+ | Natural language strategy parsing | P2 — pro feature |
| `backtester.py` | 100+ | Strategy backtesting | P2 — pro feature |
| `hyperopt_engine.py` | 100+ | Optuna parameter optimization | P2 — optimization |
| `alert_manager.py` | 100+ | Price/signal alerts | P1 — user feature |
| `market_discovery.py` | 100+ | Extended asset scanner | P2 — discovery |
| `hindsight_simulator.py` | 100+ | 48h time-travel backtesting | P2 — analysis |
| `token_manager.py` | 50+ | API cost tracking | P2 — billing |
| `agents.py` | 50+ | Agent registry, system prompts | P2 — agents |
| `signal_explainer.py` | 50+ | Signal explanation generation | P2 — UX |
| `fear_greed.py` | 50+ | Fear & Greed index | P2 — indicator |
| `telegram_notifier.py` | 50+ | Telegram notifications | P2 — notifications |
| `api_server.py` | 50+ | Early API server (likely incomplete) | P1 — API |
| `brain_entrypoint.py` | 50+ | Brain startup wrapper | P2 — ops |
| `brain_runner.py` | 50+ | Brain execution helper | P2 — ops |
| `morning_email.py` | 50+ | Email delivery for morning brief | P2 — notifications |
| `prediction_game.py` | 50+ | Prediction gamification | P2 — engagement |
| `scanner_scheduler.py` | 50+ | Scan scheduling | P2 — ops |
| `realtime_monitor.py` | 50+ | Real-time monitoring | P2 — ops |
| `hr_strategist.py` | 50+ | HR/team strategy | P2 — internal |
| `chart_generator.py` | 50+ | Chart generation helper | P2 — charting |
| `market_researcher.py` | 50+ | Market research | P2 — research |
| `strategies.py` | 50+ | Strategy definitions | P2 — trading |
| `fetch_data.py` | 50+ | Data fetching utilities | P2 — data |

### Frontend (`dashboard/`)

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 8,940 | ALL 28 views, sidebar, auth forms, routing, styling |

### Memory System (`memory/`)

| File | Purpose |
|------|---------|
| `memory_manager.py` | Error lessons, reflections, evolution tracking |
| `error_lessons.json` | Accumulated error prevention rules |
| `market_lessons.json` | Market behavior patterns learned |
| `market_predictions.json` | Prediction tracking for accuracy validation |
| `daily_reflections.json` | AI self-reflection logs |
| `paper_portfolio.json` | Paper trading portfolio state |
| `hindsight_simulations.json` | 48h backtesting results |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | CTO Office | Initial comprehensive assessment |

---

*This document should be reviewed and updated quarterly, or after any major architectural change.*
