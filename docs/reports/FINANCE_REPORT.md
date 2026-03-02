# Project Aegis: Finance Report
## CFO Strategic Financial Plan

**Date:** February 28, 2026 | **Stage:** Pre-Seed / Pre-Revenue | **Author:** Finance & Strategy

---

## Executive Summary

Project Aegis is a pre-revenue AI trading terminal targeting the $15B+ retail trading tools market.
The product combines AI-generated signals, news sentiment, social tracking, and autonomous paper trading
in a Bloomberg-style interface at a fraction of competitor pricing. This report establishes the
financial architecture for scaling from 0 to $22M ARR over 3 years, benchmarked against fintech SaaS
industry standards.

**Key Financial Headlines:**
- **Blended gross margin target:** 78-82% (in line with SaaS median of 75-80%)
- **Break-even:** Month 9-12 at ~1,700 paid users
- **Path to $1M ARR:** Month 14-18 with ~2,200 paid users
- **LTV:CAC target:** >3:1 across all paid tiers (industry minimum for healthy SaaS)
- **Monthly burn rate (Year 1):** $87K, declining to $62K post-revenue

---

## 1. Revenue Model Design

### 1.1 Tier Structure

| Tier | Price (Monthly) | Price (Annual) | Target Mix | Key Features | Positioning |
|------|----------------|----------------|------------|--------------|-------------|
| **Recruit (Free)** | $0 | $0 | 70% of users | 12 assets, delayed data, basic signals (BUY/SELL/NEUTRAL), paper trading (10 positions), 3 scans/day, 60s refresh | Generous free tier for top-of-funnel. Must be genuinely useful (not crippled) to drive organic growth |
| **Operator (Pro)** | $29/mo | $261/yr (save 10%) | 20% of users | 48 assets, real-time data, full signal spectrum + numeric confidence, autonomous bot, social sentiment, optimizer, strategy lab, 25 alerts, 10s refresh | Core revenue driver. Priced below TrendSpider ($29) and Koyfin ($27.50), far below Trade Ideas ($84-167) |
| **Command (Enterprise)** | $99/mo | $891/yr (save 25%) | 8% of users | API access, priority signals, advanced risk analytics, phone support, unlimited backtests, custom signal weights, bulk data export | Power users + small prop desks. Positioned against Koyfin Pro ($83.30) and TrendSpider Elite ($139) |
| **Institutional** | $249/mo | $2,241/yr (save 25%) | 2% of users | White-label, custom asset universe, dedicated infrastructure, SLA (99.9%), SSO/SAML, team workspace (25 seats), audit logs | Prop trading desks + fintech builders. Positioned as 92x cheaper than Bloomberg Terminal ($24K/yr) |

**Pricing Psychology (from GTM Playbook):**
- Free tier genuinely useful (not crippled) -- drives organic word-of-mouth
- $29 Pro price is the "Netflix of trading" price point -- low enough for impulse, high enough for perceived value
- Annual toggle with 10-25% savings increases commitment and reduces churn
- Dollar-value framing in marketing: "One good signal pays for 12 months of Pro"

### 1.2 Additional Revenue Streams

| Stream | Revenue Model | Est. Revenue (Year 2) | Margin | Notes |
|--------|--------------|----------------------|--------|-------|
| **Broker Referral Commissions** | $5-15 per funded account (Alpaca, IBKR) | $50K-150K/yr | 100% | Zero cost. Alpaca pays $15/funded account. At 10K users, 10% fund = $15K |
| **API Licensing (Signal-as-a-Service)** | $500-5,000/mo per client | $120K-600K/yr | 85% | Sell signal feed to other fintech apps, robo-advisors, prop desks |
| **Premium Data Add-ons** | $19-49/mo per user | $100K-300K/yr | 60% | Options flow, dark pool data, institutional positioning. Requires Polygon.io or similar |
| **Educational Content** | $99-299 one-time purchase | $30K-100K/yr | 95% | Trading courses, AI signal methodology, strategy building certifications |
| **White-Label Licensing** | $2,000-10,000/mo per client | $48K-240K/yr | 75% | Branded versions for financial advisors, trading academies |

**Year 2 Additional Revenue Potential: $350K-1.4M** (conservative: $500K)

### 1.3 Revenue Mix Targets

| Revenue Source | Year 1 | Year 2 | Year 3 |
|---------------|--------|--------|--------|
| Subscription (core) | 100% | 75% | 60% |
| Broker referrals | 0% | 8% | 10% |
| API licensing | 0% | 10% | 15% |
| Data add-ons | 0% | 5% | 10% |
| Education + white-label | 0% | 2% | 5% |

---

## 2. Unit Economics (Per User)

### 2.1 Cost Breakdown by Tier

| Metric | Free (Recruit) | Pro (Operator, $29) | Enterprise (Command, $99) | Institutional ($249) |
|--------|---------------|--------------------|--------------------------|-------------------|
| **Monthly Revenue** | $0 | $29 | $99 | $249 |
| Infrastructure (compute/CDN) | $0.50 | $2.00 | $5.00 | $15.00 |
| Data Feed Cost (Twelve Data share) | $0 | $3.00 | $8.00 | $20.00 |
| AI API Cost (Claude Haiku) | $0 | $0.50 | $1.50 | $3.00 |
| Support Cost (blended) | $0.10 | $1.00 | $5.00 | $25.00 |
| Payment Processing (Stripe 2.9%) | $0 | $0.84 | $2.87 | $7.22 |
| **Total COGS** | **$0.60** | **$7.34** | **$22.37** | **$70.22** |
| **Gross Profit** | **-$0.60** | **$21.66** | **$76.63** | **$178.78** |
| **Gross Margin** | -inf | **74.7%** | **77.4%** | **71.8%** |

**Blended Gross Margin (paid users only): ~75%**

Industry benchmark: Median SaaS gross margin is 75-80% (KeyBanc 2024 SaaS Survey). Aegis is within range.
Top-quartile fintech SaaS achieves 82-85% gross margin at scale (infrastructure costs amortize).

### 2.2 Customer Acquisition Cost (CAC)

| Channel | CAC | Target Tier | Payback Period | Notes |
|---------|-----|-------------|----------------|-------|
| Organic (SEO, content, Product Hunt) | $2-5 | Free | N/A | Public signal pages, embeddable widgets, Reddit/HN posts |
| Content Marketing (blog, YouTube) | $8-15 | Free -> Pro | 1 month | Weekly market analysis, AI demo videos, newsletter |
| Paid Social (Reddit, Twitter/X ads) | $25-40 | Pro | 1-2 months | Targeted: r/wallstreetbets, Crypto Twitter, trading communities |
| Google Ads (SEM) | $40-80 | Pro | 2-3 months | Keywords: "AI trading signals", "best trading terminal" |
| Influencer / Affiliate | $15-25 | Pro | 1 month | Trading YouTubers, fintech bloggers, 20% rev share |
| Enterprise Sales (outbound) | $200-500 | Enterprise | 3-5 months | Direct outreach to prop desks, RIAs, fintech startups |
| Institutional Sales | $2,000-5,000 | Institutional | 10-20 months | Conference presence, relationship-based, long sales cycle |

**Blended CAC Target: $35 (Year 1), declining to $20 (Year 3) as organic share grows**

Industry benchmark: Median SaaS CAC is $200-400 for mid-market. Aegis targets SMB/retail, where
CAC is typically $15-50 for self-serve products (OpenView 2024 Benchmarks).

### 2.3 Lifetime Value (LTV)

| Tier | ARPU (Monthly) | Gross Margin | Monthly Churn | Avg Lifetime | LTV | LTV:CAC |
|------|---------------|-------------|---------------|-------------|-----|---------|
| **Pro ($29)** | $29.00 | 74.7% | 5.0% | 20 months | $433 | 17:1 (organic) / 11:1 (paid) |
| **Enterprise ($99)** | $99.00 | 77.4% | 3.0% | 33 months | $2,527 | 13:1 (sales) |
| **Institutional ($249)** | $249.00 | 71.8% | 2.0% | 50 months | $8,944 | 4.5:1 (enterprise sales) |
| **Blended (paid)** | $52.30 | 75.1% | 4.5% | 22 months | $862 | **24:1 (organic) / 8:1 (blended)** |

**LTV Formula:** LTV = ARPU x Gross Margin / Monthly Churn Rate

Industry benchmarks (fintech SaaS):
- Healthy LTV:CAC ratio: >3:1 (Bessemer Venture Partners "good"), >5:1 is excellent
- Median monthly churn for SMB SaaS: 3-7% (fintech tends toward 4-6%)
- Median monthly churn for enterprise SaaS: 1-3%
- CAC payback period target: <12 months (Aegis target: 1-3 months for Pro)

### 2.4 Churn Analysis & Benchmarks

| Metric | Aegis Target | Industry Median (Fintech SaaS) | Top Quartile | Source |
|--------|-------------|-------------------------------|-------------|--------|
| Monthly logo churn (SMB) | 5.0% | 5-7% | <3% | OpenView 2024 |
| Monthly logo churn (Enterprise) | 3.0% | 2-4% | <1.5% | KeyBanc 2024 |
| Annual net revenue retention | 105% | 100-110% | >120% | Bessemer Cloud Index |
| Annual gross revenue retention | 85% | 80-90% | >92% | KBCM SaaS Survey |
| Free-to-paid conversion | 3-5% | 2-5% | >7% | OpenView Product Benchmarks |
| Trial-to-paid conversion | 25% | 15-25% | >40% | Totango SaaS Metrics |

**Churn Reduction Strategies:**
1. **Prediction accountability** -- Signal Report Card proves value (unique to Aegis)
2. **Autonomous bot** -- daily engagement without user effort (stickiness)
3. **Morning Brief** -- daily email/notification creates habit loop
4. **Annual pricing** -- 25% discount locks in 12-month commitment (reduces effective churn by 60%)
5. **Progressive feature unlock** -- users discover new features over time

---

## 3. Financial Projections (3-Year)

### 3.1 Year 1: Foundation (0 to 10,000 Users)

| Quarter | Total Users | Free (70%) | Pro (20%) | Enterprise (8%) | Institutional (2%) | MRR | ARR (Run Rate) |
|---------|------------|-----------|-----------|-----------------|-------------------|-----|----------------|
| Q1 (M1-3) | 1,500 | 1,200 | 225 | 60 | 15 | $12,360 | $148K |
| Q2 (M4-6) | 3,500 | 2,660 | 595 | 196 | 49 | $30,547 | $367K |
| Q3 (M7-9) | 6,500 | 4,810 | 1,170 | 416 | 104 | $63,486 | $762K |
| Q4 (M10-12) | 10,000 | 7,000 | 2,000 | 800 | 200 | $137,700 | $1.65M |

**Year 1 Total Revenue: ~$732K** (cumulative MRR across 12 months)
**Year 1 Exit ARR: $1.65M**

Assumptions:
- User growth: 500/mo Q1, 700/mo Q2, 1,000/mo Q3, 1,200/mo Q4 (organic + content + early paid)
- Tier distribution stabilizes at 70/20/8/2 by Q3
- Monthly churn offset by new acquisition (net growth positive)
- No additional revenue streams in Year 1 (conservative)

### 3.2 Year 2: Growth (10,000 to 50,000 Users)

| Quarter | Total Users | Free | Pro | Enterprise | Institutional | MRR | ARR (Run Rate) |
|---------|------------|------|-----|-----------|--------------|-----|----------------|
| Q5 | 18,000 | 12,600 | 3,600 | 1,440 | 360 | $247,860 | $2.97M |
| Q6 | 27,000 | 18,900 | 5,400 | 2,160 | 540 | $371,790 | $4.46M |
| Q7 | 38,000 | 26,600 | 7,600 | 3,040 | 760 | $523,740 | $6.28M |
| Q8 | 50,000 | 35,000 | 10,000 | 4,000 | 1,000 | $689,000 | $8.27M |

**Year 2 Total Revenue: ~$5.5M** (subscriptions) + **$500K** (additional streams) = **~$6.0M**
**Year 2 Exit ARR: $8.27M** (subscriptions only)

### 3.3 Year 3: Scale (50,000 to 200,000 Users)

| Quarter | Total Users | Free | Pro | Enterprise | Institutional | MRR | ARR (Run Rate) |
|---------|------------|------|-----|-----------|--------------|-----|----------------|
| Q9 | 80,000 | 56,000 | 16,000 | 6,400 | 1,600 | $1,102,400 | $13.2M |
| Q10 | 120,000 | 84,000 | 24,000 | 9,600 | 2,400 | $1,653,600 | $19.8M |
| Q11 | 160,000 | 112,000 | 32,000 | 12,800 | 3,200 | $2,204,800 | $26.5M |
| Q12 | 200,000 | 140,000 | 40,000 | 16,000 | 4,000 | $2,756,000 | $33.1M |

**Year 3 Total Revenue: ~$23.1M** (subscriptions) + **$3.5M** (additional streams) = **~$26.6M**
**Year 3 Exit ARR: $33.1M** (subscriptions only)

### 3.4 Growth Rate Analysis

| Metric | Year 1 | Year 2 | Year 3 | Benchmark |
|--------|--------|--------|--------|-----------|
| User Growth | 0 -> 10K | 10K -> 50K (5x) | 50K -> 200K (4x) | Top SaaS: 3-4x annual |
| ARR Growth | $0 -> $1.65M | $1.65M -> $8.27M (5x) | $8.27M -> $33.1M (4x) | T2D3 rule (triple, triple, double, double, double) |
| MRR Growth (MoM) | ~30% avg | ~15% avg | ~12% avg | >10% MoM is "exceptional" (a16z) |
| Net Revenue Retention | N/A | 105% | 110% | Median fintech SaaS: 100-110% |

---

## 4. Cost Structure

### 4.1 Year 1 Operating Budget

| Category | Monthly (Avg) | Annual | % of Revenue | Notes |
|----------|--------------|--------|-------------|-------|
| **Personnel** | | | | |
| - Engineering (3 FTEs) | $30,000 | $360,000 | 49% | 2 backend + 1 frontend, avg $120K fully loaded |
| - Product / Design (1 FTE) | $10,000 | $120,000 | 16% | Product manager / UX designer |
| - Marketing (1 FTE) | $8,000 | $96,000 | 13% | Content marketer + growth |
| - Support (0.5 FTE) | $3,000 | $36,000 | 5% | Part-time, scaling to full-time in Q3 |
| **Subtotal Personnel** | **$51,000** | **$612,000** | **84%** | |
| | | | | |
| **Infrastructure** | | | | |
| - Hosting (Hetzner -> AWS) | $500 | $6,000 | <1% | Hetzner VPS ($4/mo) -> AWS at 1K users ($200/mo) |
| - Data APIs (Twelve Data + Claude) | $500 | $6,000 | <1% | Twelve Data $29/mo + Claude Haiku ~$10/mo at start |
| - CDN / Storage | $100 | $1,200 | <1% | Cloudflare (free tier -> Pro $20/mo) |
| **Subtotal Infrastructure** | **$1,100** | **$13,200** | **2%** | Scales to $3K/mo by Q4 |
| | | | | |
| **Marketing & Growth** | | | | |
| - Paid Acquisition | $3,000 | $36,000 | 5% | Reddit ads, Google SEM, Twitter/X |
| - Content Production | $1,000 | $12,000 | 2% | Blog posts, video, newsletter tools |
| - Tools (analytics, email) | $500 | $6,000 | <1% | PostHog, Resend, Stripe |
| **Subtotal Marketing** | **$4,500** | **$54,000** | **7%** | |
| | | | | |
| **Operations** | | | | |
| - Legal & Compliance | $2,000 | $24,000 | 3% | Regulatory setup, ToS, privacy policy |
| - Accounting / Finance | $500 | $6,000 | <1% | Bookkeeper + tax prep |
| - Insurance | $300 | $3,600 | <1% | E&O, D&O |
| - Misc / Contingency | $1,000 | $12,000 | 2% | Buffer for unexpected costs |
| **Subtotal Operations** | **$3,800** | **$45,600** | **6%** | |
| | | | | |
| **TOTAL MONTHLY BURN** | **$60,400** | **$724,800** | **100%** | |

**Note:** Year 1 budget reduced from initial $87K/mo estimate to $60.4K/mo by:
- Starting with 5.5 FTEs instead of 15 (remote-first, lean team)
- Using Hetzner ($4/mo) before migrating to AWS
- Organic-first marketing (content > paid ads initially)

### 4.2 Year 2 Operating Budget

| Category | Monthly | Annual | Notes |
|----------|---------|--------|-------|
| Personnel (12 FTEs) | $120,000 | $1,440,000 | +4 eng, +1 sales, +1 support, +1 data science |
| Infrastructure | $8,000 | $96,000 | AWS/K8s, scaling with users |
| Data APIs | $3,000 | $36,000 | Twelve Data Pro + Polygon.io + Claude |
| Marketing | $20,000 | $240,000 | Scaled paid acquisition + events |
| Operations | $8,000 | $96,000 | Legal, accounting, insurance |
| **Total** | **$159,000** | **$1,908,000** | |

### 4.3 Year 3 Operating Budget

| Category | Monthly | Annual | Notes |
|----------|---------|--------|-------|
| Personnel (30 FTEs) | $300,000 | $3,600,000 | Full product, eng, sales, support, ops teams |
| Infrastructure | $25,000 | $300,000 | Multi-region, high availability |
| Data APIs | $8,000 | $96,000 | Premium data feeds, institutional grade |
| Marketing | $60,000 | $720,000 | Brand + performance + events + PR |
| Operations | $20,000 | $240,000 | Full ops stack |
| **Total** | **$413,000** | **$4,956,000** | |

### 4.4 Profitability Timeline

| Milestone | Month | Users | MRR | Monthly Burn | Net Cash Flow |
|-----------|-------|-------|-----|-------------|---------------|
| First revenue | M1 | 100 | $1,500 | $60,400 | -$58,900 |
| 500 paid users | M6 | 3,500 | $30,500 | $60,400 | -$29,900 |
| **Break-even (monthly)** | **M10** | **7,500** | **$63,000** | **$62,000** | **+$1,000** |
| 2,000 paid users | M12 | 10,000 | $137,700 | $65,000 | +$72,700 |
| Cash-flow positive (cumulative) | M15 | 15,000 | $200,000 | $100,000 | +$100,000 |

**Break-even requires: ~1,700 paid users** (at blended $37 ARPU after Stripe fees and COGS)

---

## 5. Funding Strategy

### 5.1 Current State

| Metric | Value |
|--------|-------|
| Revenue | $0 (pre-launch) |
| Users | 0 (beta testers only) |
| Product | Functional MVP, 28 views, 12 assets, paper trading |
| Team | 1 founder (solo) |
| Runway | Bootstrap / personal funds |
| IP | Proprietary AI signal engine, prediction tracking, autonomous trading bot |

### 5.2 Funding Rounds

| Round | Timing | Amount | Valuation | Dilution | Trigger | Use of Funds |
|-------|--------|--------|-----------|----------|---------|-------------|
| **Pre-Seed** | Now (M0) | $100-250K | $1-2M (SAFE) | 10-15% | Product launch | First 2 hires, infrastructure, legal |
| **Seed** | M6-9 | $500K-1.5M | $5-8M | 15-20% | 1,000+ users, $30K MRR | Team to 8, paid acquisition, data APIs |
| **Series A** | M18-24 | $5-10M | $30-50M | 15-20% | 10K+ users, $1M+ ARR, 5x growth | Scale team to 25, enterprise sales, React rebuild |
| **Series B** | M36+ | $15-30M | $100-200M | 10-15% | 50K+ users, $8M+ ARR | International expansion, M&A, institutional product |

### 5.3 Valuation Benchmarks

| Metric | Early Stage (Seed) | Growth Stage (Series A) | Scale (Series B+) | Source |
|--------|-------------------|------------------------|-------------------|--------|
| Revenue Multiple (ARR) | 20-50x | 15-25x | 10-20x | Bessemer Cloud Index 2024 |
| Fintech Premium | +20-40% | +15-30% | +10-20% | a16z Fintech State of 2024 |
| Comparable Exits | -- | -- | TradingView: $3B (2024), Koyfin: ~$50M est. | Public reports |
| Rule of 40 target | N/A (growth phase) | 60%+ (growth + margin) | 40%+ (balanced) | Industry standard |

**Aegis Valuation Scenarios (at Series A):**

| Scenario | ARR | Multiple | Valuation |
|----------|-----|----------|-----------|
| Conservative | $1.0M | 15x | $15M |
| Base | $1.5M | 20x | $30M |
| Optimistic | $2.5M | 25x | $62.5M |

### 5.4 Key Investor Targets

| Category | Firms | Why They Fit |
|----------|-------|-------------|
| **Fintech Specialists** | Ribbit Capital, QED Investors, Nyca Partners | Deep fintech expertise, portfolio synergies |
| **AI / ML Focused** | a16z (AI fund), Lux Capital, Radical Ventures | AI-first product thesis aligns |
| **Retail Trading** | Robinhood Ventures, Point72 Ventures, Jump Trading | Strategic interest in retail trading infrastructure |
| **European VC** | HV Capital, Cherry Ventures, EQT Ventures | German founder network, EU fintech ecosystem |
| **Angels** | Trading platform founders, ex-Bloomberg engineers | Domain expertise, warm intros |

### 5.5 Bootstrapping Alternative

If choosing not to raise external funding:

| Month | Cumulative Investment | MRR | Gap | Cumulative Cash Needed |
|-------|----------------------|-----|-----|----------------------|
| M1-3 | $181K | $5K | -$176K | $176K |
| M4-6 | $362K | $30K | -$152K | $328K |
| M7-9 | $543K | $63K | -$118K | $446K |
| M10-12 | $724K | $138K | +$73K | $373K |
| **Total Y1** | **$724K** | | | **$373K peak** |

**Minimum bootstrapping capital needed: ~$400K** to reach break-even without external funding.

---

## 6. API Investment ROI

### 6.1 API Cost vs. Revenue Impact

| API / Service | Cost/mo | What It Unlocks | Break-even (Pro Users) | ROI at 1K Paid Users | Priority |
|---------------|---------|-----------------|----------------------|---------------------|----------|
| **Claude Haiku** | $10 | AI signal explanations, natural language insights | <1 user | 2,900x | P0 (Day 1) |
| **Twelve Data (Grow)** | $29 | Real-time prices for all 48 assets, WebSocket streaming | 1 user | 1,000x | P0 (Day 1) |
| **Resend (Email)** | $20 | Transactional email (verification, alerts, morning brief) | 1 user | 1,450x | P0 (Day 1) |
| **Stripe** | 2.9% + $0.30 | Payment processing | Covers itself | N/A | P0 (Day 1) |
| **PostHog** | $0 (free tier) | Product analytics, feature flags, session replay | 0 users | Infinite | P0 (Day 1) |
| **Polygon.io (Starter)** | $29 | US stocks real-time, options data | 1 user | 1,000x | P1 (Month 3) |
| **Alpaca (Trading API)** | $0 | Paper + live trading, broker referral revenue | 0 users | Infinite | P1 (Month 3) |
| **News API (Pro)** | $449 | Premium structured news sentiment | 16 users | 65x | P2 (Month 6) |
| **Polygon.io (Advanced)** | $199 | Institutional stocks + options data | 7 users | 145x | P2 (Month 9) |
| **Twelve Data (Pro)** | $99 | Higher rate limits, fundamentals | 4 users | 290x | P2 (Month 9) |

### 6.2 Infrastructure Scaling ROI

| Users | Monthly Infra Cost | Revenue per $1 Infra | Gross Margin |
|-------|-------------------|---------------------|-------------|
| 100 | $40 (Hetzner) | $37.50 | 97% |
| 1,000 | $200 (managed VPS) | $75.00 | 99% |
| 5,000 | $600 (K8s cluster) | $125.00 | 99% |
| 10,000 | $2,000 (AWS K8s) | $68.85 | 99% |
| 50,000 | $8,000 (multi-region) | $86.13 | 99% |

Infrastructure is never the bottleneck. Data APIs and personnel dominate costs.

---

## 7. Break-Even Analysis

### 7.1 Fixed vs. Variable Costs

| Cost Type | Monthly Amount | Behavior |
|-----------|---------------|----------|
| **Fixed Costs** | | |
| Personnel | $51,000 | Step function (increases with hires) |
| Office / tools | $2,000 | Fixed |
| Legal / insurance | $2,300 | Fixed |
| Base infrastructure | $500 | Fixed |
| **Total Fixed** | **$55,800** | |
| | | |
| **Variable Costs (per paid user)** | | |
| Infrastructure (marginal) | $1.50 | Scales with users |
| Data API (marginal) | $2.00 | Scales with assets queried |
| AI API (marginal) | $0.30 | Scales with explanations generated |
| Payment processing | $1.50 | 2.9% + $0.30 per transaction |
| Support | $0.80 | Scales with tickets |
| **Total Variable (per paid user)** | **$6.10** | |

### 7.2 Break-Even Calculation

```
Break-even paid users = Fixed Costs / (ARPU - Variable Cost per User)
Break-even paid users = $55,800 / ($52.30 - $6.10)
Break-even paid users = $55,800 / $46.20
Break-even paid users = 1,208

At 70/30 free-to-paid ratio:
Total users at break-even = 1,208 / 0.30 = ~4,027 total users

With paid tier distribution (20% Pro, 8% Ent, 2% Inst):
Blended ARPU = (0.667 x $29) + (0.267 x $99) + (0.067 x $249) = $19.34 + $26.43 + $16.68 = $62.45
Break-even = $55,800 / ($62.45 - $6.10) = $55,800 / $56.35 = 990 paid users

Total users = 990 / 0.30 = ~3,300 total users
```

**Break-even: ~990 paid users (~3,300 total users)**
**Expected timeline: Month 8-10**

### 7.3 Sensitivity Analysis

| Scenario | Pro Price | Conversion Rate | Churn | Break-even Users | Timeline |
|----------|----------|----------------|-------|-----------------|----------|
| **Base case** | $29 | 30% paid | 5% | 990 paid / 3,300 total | Month 10 |
| Optimistic | $29 | 35% paid | 4% | 850 paid / 2,430 total | Month 8 |
| Pessimistic | $29 | 20% paid | 7% | 1,100 paid / 5,500 total | Month 14 |
| Price increase | $39 | 25% paid | 5% | 720 paid / 2,880 total | Month 9 |
| Price decrease | $19 | 35% paid | 6% | 1,500 paid / 4,290 total | Month 13 |
| High churn | $29 | 30% paid | 10% | 990 paid (same) but never compounds | Month 18+ |

**Key insight:** Churn rate is the most sensitive variable. Reducing churn from 5% to 3% increases LTV by 67%.
Price is secondary to retention. Invest in stickiness features (bot, morning brief, alerts) before optimizing price.

---

## 8. Key Financial Metrics & KPIs

### 8.1 Monthly Dashboard

| Metric | Definition | Month 3 Target | Month 6 | Month 12 | Benchmark |
|--------|-----------|----------------|---------|----------|-----------|
| **MRR** | Monthly recurring revenue | $5,000 | $30,000 | $138,000 | -- |
| **ARR** | MRR x 12 | $60K | $360K | $1.65M | -- |
| **MRR Growth Rate** | MoM % change | >20% | >15% | >10% | >10% = "exceptional" |
| **Paid Users** | Total paying subscribers | 150 | 850 | 3,000 | -- |
| **Free-to-Paid Conversion** | Paid / total users | 3% | 4% | 5% | Median: 2-5% |
| **Monthly Logo Churn** | Lost customers / start customers | <8% | <6% | <5% | Median SMB: 5-7% |
| **Net Revenue Retention** | (Start MRR + expansion - churn) / Start MRR | 95% | 100% | 105% | Median: 100-110% |
| **CAC** | Total S&M spend / new paid users | $15 | $25 | $35 | SMB median: $15-50 |
| **CAC Payback** | CAC / (ARPU x Gross Margin) | 1 mo | 1.5 mo | 2 mo | Target: <12 months |
| **LTV:CAC** | Lifetime value / CAC | >10:1 | >8:1 | >5:1 | Healthy: >3:1 |
| **Gross Margin** | (Revenue - COGS) / Revenue | 75% | 76% | 78% | Median SaaS: 75-80% |
| **Burn Multiple** | Net burn / net new ARR | 3.0x | 2.0x | 1.0x | Good: <2x, Great: <1x |
| **Rule of 40** | Revenue growth % + profit margin % | N/A | N/A | 50%+ | >40% = healthy |
| **ARPU** | Revenue / paid users | $40 | $48 | $52 | -- |
| **DAU/MAU** | Daily active / monthly active | >30% | >35% | >40% | Good: >25% |

### 8.2 Cohort Analysis Framework

Track monthly cohorts to measure:
1. **Activation rate** -- % of signups who complete first scan within 24 hours
2. **Day-7 retention** -- % of activated users returning after 1 week
3. **Day-30 retention** -- % still active after 1 month (target: >40%)
4. **Conversion timing** -- median days from signup to first payment
5. **Expansion revenue** -- % of Pro users upgrading to Enterprise within 6 months

---

## 9. Risk Factors & Mitigation

### 9.1 Financial Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Slower than projected growth** | Medium | High | Conservative projections already. Reduce burn if growth is <50% of plan |
| **Higher churn than expected** | Medium | Critical | Invest in retention features early. Annual pricing incentives. Monitor weekly |
| **Free tier too costly to serve** | Low | Medium | Free tier uses cached data only. Marginal cost <$0.50/user. Rate limit if needed |
| **Data API price increases** | Low | Medium | Multiple provider options. Can switch Twelve Data -> Polygon.io + free crypto APIs |
| **Competitor price war** | Low | Low | Aegis already cheapest with most features. Race to zero favors us |
| **Regulatory action** | Low | High | Advisory-only positioning (not broker). Publisher's exclusion. Disclaimers everywhere |
| **Key person risk (solo founder)** | High | Critical | Hire co-founder or CTO as first priority. Document all systems. Bus factor = 1 |

### 9.2 Scenario Planning

| Scenario | Year 1 ARR | Year 2 ARR | Action |
|----------|-----------|-----------|--------|
| **Bull case** (viral growth) | $2.5M | $15M | Raise Series A early, hire aggressively |
| **Base case** (steady growth) | $1.65M | $8.3M | Follow plan, raise Seed at M6, Series A at M18 |
| **Bear case** (slow growth) | $500K | $2M | Cut burn to $40K/mo, focus on retention, delay hiring |
| **Worst case** (no traction) | <$100K | <$500K | Pivot to B2B API-only model, or acqui-hire exit |

---

## 10. Fintech SaaS Industry Benchmarks

### 10.1 Comparable Company Metrics

| Company | Segment | ARR (Est.) | Users | ARPU/mo | Gross Margin | Valuation | Multiple |
|---------|---------|-----------|-------|---------|-------------|-----------|----------|
| TradingView | Charting + social | ~$500M | 60M+ | $0.70 (blended) | ~85% | $3B (2024) | ~6x ARR |
| Trade Ideas | AI trading signals | ~$30M | ~15K | $167 | ~80% | Private | ~10-15x |
| Koyfin | Financial data terminal | ~$10M | ~50K | $17 | ~75% | ~$50M | ~5x |
| TrendSpider | Automated TA | ~$15M | ~30K | $42 | ~80% | Private | ~8-12x |
| 3Commas | Crypto bots | ~$20M | ~200K | $8 (blended) | ~70% | ~$100M | ~5x |
| **Aegis (Year 2 target)** | **AI trading terminal** | **$8.3M** | **50K** | **$52** | **~78%** | **$30-50M** | **15-25x** |

### 10.2 Industry Growth Rates

| Metric | Fintech SaaS Median | Top Quartile | Aegis Target |
|--------|--------------------|--------------|--------------|
| YoY revenue growth (early stage) | 80-120% | >200% | 400%+ (Year 1-2) |
| YoY revenue growth (growth stage) | 40-60% | >100% | 300% (Year 2-3) |
| Gross margin | 70-80% | >85% | 78% |
| Net revenue retention | 100-110% | >130% | 105-110% |
| CAC payback (months) | 12-18 | <6 | 1-3 |
| Monthly logo churn | 3-7% | <2% | 3-5% |
| Free-to-paid conversion | 2-5% | >7% | 3-5% |
| Revenue per employee | $150-250K | >$400K | $300K (Year 2) |

### 10.3 Valuation Multiples by Stage

| Stage | Revenue Multiple | Typical ARR | Key Metric |
|-------|-----------------|-------------|------------|
| Pre-Seed | 50-100x (on projections) | $0 | Team + product vision |
| Seed | 20-50x ARR | $100K-500K | Product-market fit signals |
| Series A | 15-25x ARR | $1-5M | Growth rate + retention |
| Series B | 10-20x ARR | $5-20M | Unit economics + efficiency |
| Late Stage | 8-15x ARR | $20-100M | Rule of 40 + path to profitability |
| Public Fintech | 5-12x ARR | $100M+ | Profitability + growth balance |

---

## 11. Capital Allocation Plan

### 11.1 Pre-Seed ($150K)

| Allocation | Amount | % | Purpose |
|-----------|--------|---|---------|
| Engineering hire #1 | $60,000 | 40% | Full-stack developer (6-month contract) |
| Infrastructure + APIs | $15,000 | 10% | Twelve Data, hosting, Stripe, tooling for 12 months |
| Legal + compliance | $15,000 | 10% | Terms of service, privacy policy, regulatory review |
| Marketing launch | $10,000 | 7% | Product Hunt, initial content, design assets |
| Contingency | $50,000 | 33% | Runway extension buffer |

### 11.2 Seed ($750K)

| Allocation | Amount | % | Purpose |
|-----------|--------|---|---------|
| Engineering (3 hires) | $360,000 | 48% | Backend, frontend, data engineer (12-month runway) |
| Marketing + growth | $120,000 | 16% | Paid acquisition, content, events |
| Data + infrastructure | $60,000 | 8% | Premium APIs, AWS migration, monitoring |
| Sales (1 hire) | $90,000 | 12% | Enterprise sales (starts M6) |
| Operations | $60,000 | 8% | Legal, accounting, insurance |
| Contingency | $60,000 | 8% | Runway extension buffer |

---

## 12. Financial Controls & Governance

### 12.1 Spending Policies

| Threshold | Approval Required |
|-----------|------------------|
| < $500 | Founder discretion |
| $500 - $5,000 | Founder + budget review |
| $5,000 - $25,000 | Board notification |
| > $25,000 | Board approval |

### 12.2 Financial Reporting Cadence

| Report | Frequency | Audience |
|--------|-----------|----------|
| Cash position + burn rate | Weekly | Founder |
| MRR + churn dashboard | Weekly | Founder + investors (post-seed) |
| P&L statement | Monthly | Founder + board |
| Full financial package | Quarterly | Board + investors |
| Annual audit | Yearly | Board + investors + regulatory |

### 12.3 Key Accounting Decisions

- **Revenue recognition:** Monthly subscription recognized ratably. Annual subscriptions recognized 1/12 per month (ASC 606 compliant)
- **CAC capitalization:** Expensed as incurred (conservative approach for early stage)
- **R&D vs. operations:** Engineering salaries capitalized as R&D where applicable (tax benefits)
- **Currency:** USD primary. EUR accepted via Stripe (auto-converted)

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **ARR** | Annual Recurring Revenue (MRR x 12) |
| **MRR** | Monthly Recurring Revenue |
| **ARPU** | Average Revenue Per User |
| **CAC** | Customer Acquisition Cost |
| **LTV** | Customer Lifetime Value |
| **Logo Churn** | Percentage of customers who cancel per period |
| **Revenue Churn** | Percentage of revenue lost to cancellations per period |
| **Net Revenue Retention (NRR)** | Start MRR + expansion - contraction - churn, divided by Start MRR |
| **Gross Margin** | (Revenue - Cost of Goods Sold) / Revenue |
| **Burn Multiple** | Net burn / net new ARR (efficiency metric) |
| **Rule of 40** | Revenue growth rate % + profit margin % (should exceed 40) |
| **T2D3** | Triple, Triple, Double, Double, Double -- ideal SaaS growth trajectory |
| **SAFE** | Simple Agreement for Future Equity (YC standard) |

---

## Appendix B: Assumptions & Methodology

1. **User growth:** Based on comparable fintech SaaS launches (Koyfin, TrendSpider trajectory). Assumes Product Hunt launch + organic + content-led growth
2. **Tier distribution:** 70/20/8/2 based on industry freemium benchmarks (OpenView SaaS Benchmarks report typical 2-5% free-to-paid; Aegis targets 30% due to higher-intent trading audience)
3. **Churn rates:** Based on Profitwell/Paddle SaaS benchmarks for SMB ($10-50 ARPU range). Trading tools have slightly lower churn than general SaaS due to data dependency
4. **Infrastructure costs:** Based on Hetzner -> AWS pricing calculator. Assumes efficient caching (shared market data) reduces per-user compute cost
5. **Valuation multiples:** Based on Bessemer Cloud Index, a16z Fintech State reports, and recent comparable transactions
6. **Personnel costs:** Based on European remote-first hiring (lower than SF/NYC). Fully loaded = salary + benefits + equipment
7. **No revenue from additional streams in Year 1.** Broker referrals, API licensing, and data add-ons modeled starting Year 2 only

---

*Generated by Aegis Finance & Strategy Team | February 28, 2026*
*Next review: Quarterly (May 2026) or upon material change in assumptions*
