# Project Aegis — Employee Feedback Report (All Departments)
**Date:** March 1, 2026 | **Report by:** VP People & Culture (Maria Santos)
**Methodology:** Anonymous survey across all 12 departments. 847/1000 employees responded (84.7%).

---

## Company-Wide Pulse

| Metric | Score |
|--------|-------|
| Employee satisfaction | 7.2 / 10 |
| Belief in product | 8.4 / 10 |
| Confidence in leadership | 7.8 / 10 |
| Would recommend as employer | 74% |
| "Are we building the right thing?" | 81% yes |
| "Can we be top-10?" | 62% yes, 28% maybe |
| Top concern | "Technical debt will slow us down" |
| Top pride | "Signal intelligence is genuinely innovative" |

---

## Department-by-Department Feedback

---

### 1. ENGINEERING (300 employees, 261 responded)

**Satisfaction: 6.8/10** | **Morale: Medium**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| 8,630-line monolith (app.py) is unmaintainable | 89% | CRITICAL |
| Zero automated tests | 84% | CRITICAL |
| JSON file storage won't scale past 100 users | 78% | HIGH |
| No CI/CD pipeline — deploying is manual | 71% | HIGH |
| No API layer — frontend talks directly to Python modules | 65% | HIGH |
| yfinance is unreliable, breaks weekly | 62% | HIGH |
| No code review process | 54% | MEDIUM |
| Single-threaded scanning bottleneck | 48% | MEDIUM |

#### Verbatim from Engineers:

> "app.py is 8,630 lines. I need 45 minutes just to find the function I need to modify. This is the single biggest productivity killer." — Sr. Frontend Engineer

> "We have ZERO tests. Not one. Every deploy is a prayer. When we fixed prices last sprint, we broke percentage calculations and didn't catch it for hours." — Backend Engineer

> "JSON files with file locks? We're one concurrent write away from corrupting someone's portfolio. This MUST move to PostgreSQL before launch." — Database Specialist

> "The yfinance thread safety fix was a band-aid. We need a real market data service. Twelve Data or Polygon.io — just pick one and commit." — Data Pipeline Engineer

> "I love the product vision but I'm embarrassed to show my engineer friends the codebase. No tests, no types, no API layer, no container. It's a prototype pretending to be production." — Platform Engineer

#### What They Love:
- Signal scoring algorithm is genuinely clever (72%)
- Working on a real product with real impact (68%)
- Founder's vision and hustle (65%)
- Freedom to make architectural decisions (58%)

#### Top Requests:
1. Split app.py into separate view files (89%)
2. Add pytest + CI/CD before ANY new features (84%)
3. PostgreSQL migration plan with timeline (78%)
4. Code review requirement for all PRs (54%)
5. TypeScript + React migration roadmap (48%)

---

### 2. DATA & AI (120 employees, 104 responded)

**Satisfaction: 7.4/10** | **Morale: High**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| No ML models — everything is rule-based | 82% | HIGH |
| Sentiment is keyword-matching, not NLP | 76% | HIGH |
| No model evaluation framework | 71% | MEDIUM |
| Signal explanations are templates, not AI | 64% | MEDIUM |
| No data pipeline infrastructure | 58% | MEDIUM |
| No A/B testing for signal strategies | 51% | MEDIUM |

#### Verbatim:

> "We call ourselves an 'AI Trading Terminal' but there's zero machine learning in production. It's all if-else rules. Technically accurate but misleading to users." — ML Engineer

> "The keyword sentiment works surprisingly well for a v1. But FinBERT would be 30-40% more accurate on financial text. It's a weekend project." — NLP Specialist

> "We need an ML experimentation platform. Right now if someone wants to test an XGBoost model vs the rule engine, there's no way to do it safely." — Data Scientist

> "Social sentiment from Reddit is gold but we're scraping with feedparser. A proper Reddit API integration would give us real-time buzz detection." — Data Engineer

#### What They Love:
- Fear & Greed Index design is elegant (79%)
- Multi-source sentiment blending is architecturally sound (74%)
- Massive opportunity to add real ML (71%)
- The data is THERE — it just needs proper ML on top (67%)

#### Top Requests:
1. FinBERT integration for real NLP sentiment (76%)
2. XGBoost signal model as first ML feature (71%)
3. MLflow or similar for model tracking (64%)
4. Real-time data pipeline (Kafka or similar) (58%)
5. A/B testing framework for strategies (51%)

---

### 3. PRODUCT (60 employees, 53 responded)

**Satisfaction: 7.6/10** | **Morale: High**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| No user analytics (no Mixpanel/Amplitude) | 85% | HIGH |
| Feature priorities driven by gut, not data | 72% | HIGH |
| 28 views is too many — users are overwhelmed | 68% | MEDIUM |
| No user personas defined | 59% | MEDIUM |
| No onboarding flow for new users | 55% | MEDIUM |
| Accessibility (a11y) not tested | 41% | LOW |

#### Verbatim:

> "We have 28 views but no analytics. We literally don't know which views people use. We could be maintaining 10 views that nobody opens." — Product Manager

> "The product needs a strong opinion about WHO it's for. Right now it's trying to serve crypto degens and institutional analysts. Pick one." — UX Researcher

> "Onboarding is: sign up → full dashboard. No tour, no highlights, no 'start here'. Beginners are lost immediately." — UX Designer

> "The Daily Advisor is our best view by far. Everything should radiate from there. Don't make users hunt for information." — Product Lead

#### Top Requests:
1. User analytics integration (Mixpanel/PostHog) (85%)
2. Define 3 primary user personas (72%)
3. Consolidate 28 views into 8-10 focused views (68%)
4. Interactive onboarding tutorial (55%)
5. A/B test feature variants (48%)

---

### 4. TRADING SYSTEMS (80 employees, 71 responded)

**Satisfaction: 7.9/10** | **Morale: High (highest)**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| No live trading integration | 87% | CRITICAL |
| Paper trading P&L calculation edge cases | 62% | HIGH |
| No order types beyond market orders | 58% | MEDIUM |
| Auto-trader correlation groups need expansion | 49% | MEDIUM |
| No tick-level data for intraday strategies | 45% | MEDIUM |

#### Verbatim:

> "The 12-gate auto-trader decision system is our competitive moat. No retail platform has this sophistication. We need to PROTECT and MARKET this." — Quant Developer

> "Alpaca integration should be sprint 16 priority. Paper trading proves we can make decisions. Alpaca proves we can EXECUTE them." — Trading Systems Lead

> "Our signal engine doesn't have multi-timeframe confluence. A stock that's BUY on daily but SELL on weekly shouldn't get a high confidence score." — Strategy Developer

> "Position sizing via Kelly Criterion is advanced stuff. But we need to explain it to users in plain English. Right now it's a black box." — Risk Analyst

#### What They Love:
- Signal scoring algorithm is genuinely novel (91%)
- Risk management suite is institutional-grade (84%)
- Auto-trader 12-gate system is unique (79%)
- Portfolio optimizer using Markowitz MPT (71%)

#### Top Requests:
1. Alpaca broker integration (87%)
2. Multi-timeframe signal confluence (58%)
3. Limit/stop order types for paper trading (58%)
4. Backtesting with real historical accuracy tracking (52%)
5. Options pricing models (Black-Scholes at minimum) (38%)

---

### 5. MARKETING & GROWTH (100 employees, 88 responded)

**Satisfaction: 7.0/10** | **Morale: Medium**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| No public-facing product demo | 81% | HIGH |
| Landing page doesn't convert — no social proof | 74% | HIGH |
| We can't market "AI" when it's rule-based | 69% | HIGH |
| No referral program built yet | 64% | MEDIUM |
| SEO is non-existent | 58% | MEDIUM |
| No content marketing pipeline | 52% | MEDIUM |

#### Verbatim:

> "How do I sell a trading terminal with no real-time prices? Our #1 feature gap is our #1 marketing obstacle." — Growth Marketing Manager

> "The landing page removed fake trades (good) but now the 'Scoreboard' section says 'Coming Soon'. Visitors see an incomplete product." — Content Lead

> "We need case studies. Even paper trading performance data. Show that our signals WORK." — Performance Marketing

> "TradingView has 60 million users. They got there with free charts + community. We need our version of that viral loop." — Growth Hacker

#### Top Requests:
1. Interactive demo (no signup required) (81%)
2. Public signal accuracy dashboard (74%)
3. Content marketing: 3 blog posts/week (58%)
4. Referral program: give 1 month Pro, get 1 month Pro (64%)
5. YouTube channel with signal reviews (48%)

---

### 6. SALES (80 employees, 66 responded)

**Satisfaction: 6.5/10** | **Morale: Medium-Low**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| Free tier is too generous — no reason to upgrade | 82% | CRITICAL |
| No Stripe billing = can't actually sell Pro | 77% | CRITICAL |
| No sales collateral (pitch deck, one-pager) | 65% | HIGH |
| Enterprise tier has no differentiating features | 59% | HIGH |
| No CRM integration | 48% | MEDIUM |

#### Verbatim:

> "We gave away the store. Autopilot, social sentiment, risk dashboard — all FREE. What exactly does Pro include that's worth $29/month? I can't answer that and I'm in sales." — Sales Rep

> "We can't process payments. Stripe isn't integrated. So even if someone wants to pay, they can't." — Sales Manager

> "The Enterprise tier at $99/month — what does it include that Pro doesn't? API access? We don't have an API. White-label? We can't white-label Streamlit." — Enterprise Sales

#### Top Requests:
1. Stripe billing integration ASAP (77%)
2. Redefine free vs Pro feature gates (82%)
3. Sales pitch deck with ROI calculator (65%)
4. Enterprise features that justify $99+/mo (59%)
5. CRM (HubSpot free tier to start) (48%)

---

### 7. CUSTOMER SUCCESS (80 employees, 68 responded)

**Satisfaction: 7.3/10** | **Morale: Medium-High**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| No in-app help/docs/FAQ | 79% | HIGH |
| Users don't understand signal confidence | 71% | HIGH |
| No feedback collection mechanism | 63% | MEDIUM |
| Support tickets go to a shared inbox (no ticketing) | 54% | MEDIUM |
| No user health scoring | 47% | MEDIUM |

#### Verbatim:

> "Users email asking 'what does 73% confidence mean?' We need a tooltip or education center explaining every metric." — CS Manager

> "The signal explanations are great but the terminology isn't beginner-friendly. 'RSI oversold bounce with MACD histogram divergence' means nothing to 60% of our users." — Customer Education

> "We need a knowledge base. At minimum, one doc page per view explaining what it does and how to use it." — Support Lead

#### Top Requests:
1. In-app tooltips on every metric (79%)
2. Help center / knowledge base (71%)
3. Glossary of trading terms (63%)
4. Intercom or Zendesk for support tickets (54%)
5. User onboarding emails (automated 7-day drip) (47%)

---

### 8. SECURITY (40 employees, 36 responded)

**Satisfaction: 6.2/10** | **Morale: Low (lowest)**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| Passwords stored correctly (PBKDF2) but no rate limiting on login | 89% | CRITICAL |
| No HTTPS enforcement | 83% | CRITICAL |
| JSON files readable by any process | 78% | HIGH |
| No audit logging | 72% | HIGH |
| No penetration testing done | 67% | HIGH |
| API keys (if added) have no vault solution | 61% | HIGH |
| No GDPR compliance | 56% | MEDIUM |

#### Verbatim:

> "If someone deploys this on a VPS, user passwords are in a JSON file with no file-level encryption. One server breach = all credentials leaked." — Security Engineer

> "There's no login rate limiting. Someone could brute-force passwords with zero throttling." — AppSec Lead

> "Before we touch real money (broker integration), we need SOC 2 Type I at minimum. That's a 6-month process." — Compliance Officer

> "GDPR requires right-to-delete. Our JSON files don't have that capability cleanly." — Privacy Engineer

#### Top Requests:
1. Login rate limiting + account lockout (89%)
2. HTTPS enforcement before any public deployment (83%)
3. Database migration (JSON → encrypted at rest) (78%)
4. Comprehensive security audit (67%)
5. SOC 2 roadmap (start preparation now) (56%)

---

### 9. FINANCE (40 employees, 34 responded)

**Satisfaction: 7.1/10** | **Morale: Medium**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| $0 revenue with $60K/mo burn target | 82% | CRITICAL |
| No billing system = can't monetize | 76% | CRITICAL |
| Free tier cannibalization of Pro | 68% | HIGH |
| No financial dashboards/reporting | 53% | MEDIUM |

#### Verbatim:

> "We modeled $367K ARR at 6 months. We're at $0 at month... I don't even know what month we're in. No Stripe = no revenue. Period." — Financial Analyst

> "The free tier includes everything except optimizer and strategy_lab. That's $0 ARPU for 98% of users." — Revenue Analyst

> "Cost of yfinance is $0 but it's costing us users. Twelve Data at $29/month might be the highest-ROI spend in the company." — FP&A Manager

---

### 10. LEGAL & COMPLIANCE (30 employees, 24 responded)

**Satisfaction: 6.4/10** | **Morale: Medium-Low**

#### Top Concerns:
| Issue | % Mentioning | Severity |
|-------|-------------|----------|
| "Signal" language might constitute investment advice | 88% | CRITICAL |
| No regulatory disclosures on landing page | 79% | HIGH |
| Terms of Service are minimal | 71% | HIGH |
| Auto-trader could trigger SEC scrutiny | 63% | HIGH |
| No data processing agreement (DPA) for GDPR | 54% | MEDIUM |

#### Verbatim:

> "Calling a signal 'STRONG BUY' with a target price is borderline investment advice. We need disclaimers EVERYWHERE." — General Counsel

> "The auto-trader making trades on behalf of users, even paper trades, creates a fiduciary-adjacent relationship. This needs legal review before any live trading." — Regulatory Compliance

> "We need 'Not Financial Advice' disclaimers on every signal card, every alert, and every page. Not just a login disclaimer." — Legal Counsel

---

### 11. HR & PEOPLE (40 employees, 35 responded)

**Satisfaction: 7.5/10** | **Morale: High**

#### Summary:
- Strong belief in mission (89%)
- Concerned about burnout from fast pace (54%)
- Want more structured career paths (48%)
- Appreciate flat hierarchy and access to leadership (72%)

---

### 12. OPERATIONS (30 employees, 27 responded)

**Satisfaction: 6.9/10** | **Morale: Medium**

#### Top Concerns:
- No deployment automation (85%)
- No infrastructure monitoring (Datadog/New Relic) (74%)
- No disaster recovery plan (67%)
- Server costs will spike without optimization (56%)

---

## Cross-Department Themes

### Theme 1: TECHNICAL DEBT IS THE #1 INTERNAL THREAT
- **8/12 departments** cited technical debt as a blocker
- The 8,630-line app.py, zero tests, JSON storage, and no CI/CD are not just engineering problems — they block sales, marketing, security, and growth

### Theme 2: FREE TIER CANNIBALIZATION
- **Sales, Finance, and Product** all agree: the free tier is too generous
- Sprint 15 expanded free tier (autopilot, social sentiment, risk dashboard all free)
- Pro tier has almost no unique value proposition — only optimizer + strategy_lab
- **Recommendation:** Re-gate 2-3 features or add Pro-exclusive features

### Theme 3: REAL-TIME DATA IS THE KINGMAKER
- **Engineering, Trading, Marketing, Sales, Customer Success** — all 5 user-facing departments say delayed data is the #1 obstacle
- $29/month for Twelve Data would resolve this for all 48 assets

### Theme 4: THE PRODUCT HAS A GENUINE MOAT
- **Trading Systems, Data & AI, Product** unanimously agree: signal explanations + 12-gate auto-trader + multi-source sentiment blending = unique value
- No competitor explains WHY a signal is what it is
- This is the hill to die on — protect and amplify this advantage

### Theme 5: MOBILE IS NON-NEGOTIABLE
- External users (61%) and internal product/marketing teams agree
- PWA is the fastest path; native app is the right long-term play

---

## Employee eNPS (Employee Net Promoter Score)

| Department | eNPS | Top Issue |
|-----------|------|-----------|
| Trading Systems | +52 | No live trading yet |
| Data & AI | +41 | No ML in production |
| HR & People | +38 | Career paths unclear |
| Product | +34 | No user analytics |
| Customer Success | +22 | No help docs |
| Engineering | +14 | Monolith + no tests |
| Marketing & Growth | +10 | Can't demo the product |
| Operations | +4 | No deployment automation |
| Finance | -2 | $0 revenue |
| Sales | -8 | Nothing to sell (free tier too generous) |
| Legal & Compliance | -12 | Regulatory risk |
| Security | -18 | Fundamental gaps |

**Company-wide eNPS: +16**

---

*Report compiled by VP People & Culture (Maria Santos)*
*Confidential — for leadership review only*
*Next pulse survey: April 1, 2026*
