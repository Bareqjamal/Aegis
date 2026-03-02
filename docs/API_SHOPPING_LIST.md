# Project Aegis: API & Infrastructure Shopping List

> **Prepared:** 2026-02-27 | **For:** CEO Decision | **Author:** Broker & API Specialist
>
> Covers all APIs, brokers, and infrastructure needed to take Project Aegis
> from a paper-trading prototype to a production-grade, revenue-generating
> multi-asset trading terminal.

---

## Table of Contents

1. [Current State & What Needs Replacing](#1-current-state)
2. [Market Data APIs](#2-market-data-apis)
3. [Broker APIs (Real Trading)](#3-broker-apis)
4. [News & Sentiment APIs](#4-news--sentiment-apis)
5. [Infrastructure](#5-infrastructure)
6. [Payment Processing](#6-payment-processing)
7. [Budget Scenarios](#7-budget-scenarios)
8. [Recommended Implementation Order](#8-implementation-order)

---

## 1. Current State

| Component       | Current Solution       | Problem                                      |
|-----------------|------------------------|----------------------------------------------|
| Market data     | yfinance (free)        | 15-min delay on stocks/commodities, unreliable, no SLA, breaks randomly |
| News            | RSS feeds (free)       | No structured sentiment, limited sources, no filtering |
| Trading         | Paper-only simulation  | No real money execution, no broker connection |
| Hosting         | Local machine          | Not accessible to users, no uptime guarantee |
| Payments        | None                   | Cannot charge subscribers                    |
| Email           | Raw SMTP (env vars)    | No deliverability guarantees, likely to hit spam |
| Monitoring      | None                   | No visibility into uptime or failures        |

### Assets We Trade (12 total)

| Asset Class  | Tickers                    | Data Difficulty |
|-------------|----------------------------|-----------------|
| Commodities | GC=F, SI=F, PL=F, HG=F    | HARD -- futures need specialized feeds |
| Crypto      | BTC-USD, ETH-USD           | EASY -- many free sources |
| Energy      | CL=F, NG=F                 | HARD -- futures |
| Indices     | ^GSPC, ^IXIC               | MEDIUM -- delayed free, real-time paid |
| Agriculture | ZW=F                       | HARD -- futures |
| Forex       | EURUSD=X                   | MEDIUM -- many sources, spreads vary |

---

## 2. Market Data APIs

### 2.1 Polygon.io

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Real-time and historical data for US stocks, options, forex, crypto. Aggregates, trades, quotes, snapshots. WebSocket streaming. |
| **Free tier**     | Yes -- end-of-day data only, 5 calls/min. Stocks + forex + crypto. NO commodities. |
| **Starter plan**  | $29/month -- unlimited calls, 5yr history, real-time stocks |
| **Developer plan**| $79/month -- 10yr history, all stock endpoints |
| **Advanced plan** | $199-500/month -- options data, full feature set |
| **Rate limits**   | Unlimited on paid plans (no per-minute cap) |
| **Reliability**   | High -- used by Robinhood, major fintech. 99.99% uptime SLA on paid plans |
| **Commodities**   | NO -- does not cover commodity futures (GC=F, CL=F, etc.) |
| **Why we need it**| Best stock/crypto data quality. Does NOT solve our commodity futures problem. |
| **Verdict**       | GOOD for stocks + crypto, but we need a complementary source for commodities |

### 2.2 Twelve Data

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Stocks, forex, crypto, ETFs, indices, commodities. REST + WebSocket. Technical indicators built-in. |
| **Free tier**     | Yes -- 8 calls/min, 800/day. US equities + forex + crypto. NO commodities on free. |
| **Grow plan**     | $29/month -- 55+ calls/min, no daily limit, Level A stocks + ETFs + indices |
| **Pro plan**      | $99/month -- 610+ calls/min, Level B assets, essential fundamentals |
| **Ultra plan**    | $329/month -- 2,584+ calls/min, Level C stocks, all fundamentals, 99.95% SLA |
| **Rate limits**   | Generous on paid plans. WebSocket available on Grow and above. |
| **Reliability**   | High -- well-documented, responsive support |
| **Commodities**   | YES on paid plans -- covers Gold, Silver, Oil, Natural Gas, Wheat, etc. |
| **Why we need it**| ONLY provider on this list that covers ALL 12 of our assets in one API (stocks, crypto, forex, commodities, indices) at a reasonable price |
| **Verdict**       | TOP PICK. The $29/mo Grow plan covers everything we need. Already recommended in REALTIME_DATA.md |

### 2.3 Alpha Vantage

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Stocks, forex, crypto, commodities, technical indicators, fundamentals |
| **Free tier**     | Yes -- 25 calls/day, 5 calls/min. Very limited. |
| **Cheapest paid** | $49.99/month -- 75 calls/min, no daily limit |
| **Higher tiers**  | Plans scale by calls/min: Plan150, Plan300, Plan600, Plan1200 |
| **Rate limits**   | Tight on free. Paid plans vary from 75 to 1200 calls/min |
| **Reliability**   | MEDIUM -- known for occasional data gaps, slower support |
| **Commodities**   | YES -- covers commodity data |
| **Why we need it**| Fallback option if Twelve Data is unavailable. Built-in technical indicators. |
| **Verdict**       | BACKUP ONLY. More expensive than Twelve Data for less capability. $49.99/mo vs $29/mo. |

### 2.4 Finnhub

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Real-time US stocks, forex. Company fundamentals, SEC filings, earnings. WebSocket streaming. |
| **Free tier**     | Yes -- 60 calls/min. Real-time US stock prices + WebSocket (50 symbols). Very generous. |
| **Paid plans**    | Start at $49-50/month per market/data bundle. Modular pricing. |
| **Rate limits**   | 60/min free, higher on paid |
| **Reliability**   | HIGH -- fast WebSocket, good uptime |
| **Commodities**   | LIMITED -- no direct commodity futures |
| **Why we need it**| FREE real-time US stock data + WebSocket. Perfect complement to Twelve Data. Use for S&P 500 + NASDAQ real-time streaming. |
| **Verdict**       | USE FREE TIER for index streaming. Already planned in REALTIME_DATA.md Phase 1. |

### 2.5 CoinGecko

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Crypto prices, market caps, volumes, historical data, exchange rates, DeFi data |
| **Free tier**     | Yes -- 30 calls/min, 10,000 calls/month. Covers BTC + ETH easily. |
| **Analyst plan**  | $129/month -- higher rate limits, exclusive endpoints |
| **Lite plan**     | $499/month |
| **Pro plan**      | $999/month |
| **Rate limits**   | Free: 30/min. Paid: 500-1000/min |
| **Reliability**   | HIGH -- industry standard for crypto data |
| **Why we need it**| We only trade 2 crypto assets. Free tier is MORE than enough. |
| **Verdict**       | USE FREE TIER. 10,000 calls/month handles BTC + ETH easily. Paid plans are overkill for 2 assets. |

### 2.6 CoinMarketCap

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Crypto rankings, pricing, market cap, exchange data |
| **Free tier**     | Yes -- 10,000 calls/month, 11 endpoints |
| **Hobbyist plan** | $29/month -- 110,000 calls, 15 endpoints |
| **Startup plan**  | $79/month -- 300,000 calls, 23 endpoints |
| **Standard plan** | $299/month -- 1.2M calls, 28 endpoints |
| **Rate limits**   | Vary by plan |
| **Reliability**   | HIGH -- owned by Binance |
| **Why we need it**| Alternative to CoinGecko. Similar free tier. |
| **Verdict**       | SKIP -- CoinGecko free tier is equivalent and CoinGecko has broader data. Pick one, not both. |

### Data Latency Comparison

| Provider     | Real-Time | 15-min Delay | End-of-Day | WebSocket |
|-------------|-----------|--------------|------------|-----------|
| yfinance    | Crypto only | Stocks/Commodities | All | No |
| Polygon.io  | Paid only | Free tier | Free tier | Paid |
| Twelve Data | Paid only | Free tier (stocks) | Free tier | Grow+ |
| Alpha Vantage | Paid only | -- | Free tier | No |
| Finnhub     | FREE (stocks) | -- | -- | FREE (50 symbols) |
| CoinGecko   | FREE (crypto) | -- | FREE | No |
| Binance     | FREE (crypto) | -- | FREE | FREE |

### RECOMMENDATION: Market Data Stack

| Source      | Assets Covered                | Cost    | Role              |
|-------------|-------------------------------|---------|-------------------|
| Twelve Data | ALL 12 assets (primary feed)  | $29/mo  | Primary data      |
| Finnhub     | S&P 500, NASDAQ (WebSocket)   | FREE    | Real-time indices  |
| Binance     | BTC, ETH (WebSocket)          | FREE    | Real-time crypto   |
| CoinGecko   | BTC, ETH (REST fallback)      | FREE    | Crypto fallback    |
| yfinance    | All (last resort fallback)    | FREE    | Emergency fallback |
| **TOTAL**   |                               | **$29/mo** |                |

---

## 3. Broker APIs (Real Trading)

### 3.1 Alpaca Markets

| Detail              | Value |
|---------------------|-------|
| **What it does**    | Commission-free trading API for US stocks, ETFs, options, crypto |
| **Supported assets**| US stocks, ETFs, options, 20+ crypto pairs |
| **NOT supported**   | Commodities (no futures), Forex, International markets |
| **Minimum deposit** | $0 (no minimum) |
| **Commissions**     | $0 for stocks, ETFs, options, crypto |
| **Paper trading**   | YES -- free, real-time simulation, unlimited resets |
| **API quality**     | Excellent -- REST + WebSocket, Python SDK, well-documented |
| **Other fees**      | $25 domestic wire, $50 international wire. ACH free. |
| **Regulation**      | SEC/FINRA registered broker-dealer |
| **Why we need it**  | Easiest broker API to integrate. Zero commission. Great paper trading. |
| **Limitation**      | Cannot trade 8 of our 12 assets (no Gold, Silver, Oil, etc.) |
| **Verdict**         | USE for stocks (S&P proxy ETFs like SPY) + crypto (BTC, ETH). Cannot replace IBKR for full coverage. |

### 3.2 Interactive Brokers (IBKR)

| Detail              | Value |
|---------------------|-------|
| **What it does**    | Full-service brokerage API: stocks, options, futures, forex, bonds, crypto, commodities |
| **Supported assets**| EVERYTHING -- 170 markets in 40 countries. Stocks, futures, forex, crypto, commodities, bonds |
| **Minimum deposit** | $0 (cash account), $2,000 (margin account) |
| **Commissions**     | IBKR Lite: $0 stocks. IBKR Pro: $0.005/share (min $1). Futures: $0.25-0.85/contract. Forex: $2/100K. |
| **Paper trading**   | YES -- full paper trading account mirroring live |
| **API quality**     | COMPLEX but powerful. TWS API (Python/Java/C++), Web API, FIX protocol. Requires TWS or IB Gateway running. |
| **Other fees**      | Market data subscriptions ($1-10/mo per exchange), $10/mo inactivity fee waived at $100K+ or $30/mo commissions |
| **Regulation**      | SEC/FINRA, FCA, and 10+ regulators globally |
| **Why we need it**  | ONLY broker that can trade ALL 12 of our assets. Gold futures, Oil futures, Wheat futures, EUR/USD, everything. |
| **Limitation**      | Complex API setup (TWS Gateway). Steeper learning curve. Market data feeds cost extra ($1-10/mo per exchange). |
| **Verdict**         | ESSENTIAL for real trading of commodities + futures. The only way to trade all 12 assets through one broker. |

### 3.3 Binance

| Detail              | Value |
|---------------------|-------|
| **What it does**    | Crypto exchange API: spot, futures, margin, staking |
| **Supported assets**| Crypto only -- 350+ trading pairs |
| **NOT supported**   | Stocks, commodities, forex, indices |
| **Minimum deposit** | No formal minimum (varies by payment method) |
| **Commissions**     | Spot: 0.1% maker/taker (base). Futures: 0.02% maker / 0.05% taker. BNB discount: ~25% off |
| **Paper trading**   | YES -- Testnet available (spot + futures). Resets monthly. |
| **API quality**     | Excellent -- REST + WebSocket, Python SDK, high throughput |
| **Other fees**      | Withdrawal fees vary by coin/network |
| **Regulation**      | Varies by jurisdiction. Binance.US for US residents (limited). |
| **Why we need it**  | Best crypto execution + cheapest fees. Free WebSocket data. |
| **Limitation**      | US users MUST use Binance.US (fewer pairs). Crypto only. |
| **Verdict**         | USE for crypto execution if prioritizing lowest fees. Alpaca is simpler for just BTC + ETH. |

### 3.4 OANDA

| Detail              | Value |
|---------------------|-------|
| **What it does**    | Forex and CFD broker with REST API (v20) |
| **Supported assets**| 70+ forex pairs, some CFDs (indices, commodities as CFDs -- not futures) |
| **NOT supported**   | Stocks, crypto, real futures |
| **Minimum deposit** | $0 (spread-only account), $10,000 (Core Pricing account) |
| **Commissions**     | Spread-only: 0 commission, ~1.7 pip spread on EUR/USD. Core: $5 per $100K side + 0.4 pip spread. |
| **Paper trading**   | YES -- practice account with virtual funds |
| **API quality**     | Good -- REST v20 API, Python library, 32yr historical data |
| **Other fees**      | Financing charges on overnight positions |
| **Regulation**      | CFTC/NFA (US), FCA (UK), ASIC (AU) |
| **Why we need it**  | Best standalone forex API. Clean REST interface. Great for EUR/USD. |
| **Limitation**      | Forex + CFDs only. CFDs are NOT real commodity futures. |
| **Verdict**         | USE for dedicated forex trading. IBKR can also handle forex, so OANDA is optional if using IBKR. |

### Broker Coverage Matrix

| Asset            | Alpaca | IBKR | Binance | OANDA |
|------------------|--------|------|---------|-------|
| Gold (GC=F)      | --     | YES  | --      | CFD*  |
| Silver (SI=F)    | --     | YES  | --      | CFD*  |
| Platinum (PL=F)  | --     | YES  | --      | --    |
| Copper (HG=F)    | --     | YES  | --      | --    |
| BTC-USD          | YES    | YES  | YES     | --    |
| ETH-USD          | YES    | YES  | YES     | --    |
| Oil (CL=F)       | --     | YES  | --      | CFD*  |
| Nat Gas (NG=F)   | --     | YES  | --      | --    |
| S&P 500 (SPY)    | YES    | YES  | --      | CFD*  |
| NASDAQ (QQQ)     | YES    | YES  | --      | CFD*  |
| Wheat (ZW=F)     | --     | YES  | --      | --    |
| EUR/USD          | --     | YES  | --      | YES   |

*CFDs are not real futures -- different regulation, different risk profile.

### RECOMMENDATION: Broker Stack

| Phase           | Broker   | Assets                          | Cost       |
|----------------|----------|----------------------------------|------------|
| Phase 1 (now)  | Alpaca   | SPY, QQQ, BTC, ETH              | $0         |
| Phase 2 (3mo)  | + IBKR   | All 12 assets via futures/forex  | $0 base + market data |
| Optional        | Binance  | If needing advanced crypto       | $0         |
| Optional        | OANDA    | If needing dedicated forex       | $0         |

---

## 4. News & Sentiment APIs

### 4.1 NewsAPI.org

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Global news aggregation. 80,000+ sources. Search by keyword, category, source. |
| **Free tier**     | Yes -- 100 requests/day, development only, 1 month old articles, no production use |
| **Paid plan**     | $35/month -- 5,000 requests/day, production use |
| **Rate limits**   | 100/day free, 5,000/day paid |
| **Reliability**   | HIGH -- well-established, clean JSON responses |
| **Why we need it**| Structured news search by keyword. Better than scraping RSS. |
| **Limitation**    | Free tier is dev-only (cannot use in production). No built-in sentiment. |
| **Verdict**       | GOOD upgrade from RSS at $35/mo. But no sentiment scoring -- we still need our own. |

### 4.2 Benzinga

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Financial news API. Stock-specific news, earnings, analyst ratings, SEC filings. Real-time streaming. |
| **Free tier**     | Yes -- headlines + teaser only, links to Benzinga.com for full text |
| **Paid plans**    | Custom pricing -- contact sales. Estimated $100-500/mo depending on data needs |
| **Rate limits**   | Varies by plan |
| **Reliability**   | HIGH -- institutional-grade, used by major platforms |
| **Why we need it**| Stock-specific news with company tagging. Better than generic news for trading signals. |
| **Limitation**    | Expensive. Requires sales call. No transparent pricing. |
| **Verdict**       | SKIP for now. Too expensive for our stage. Revisit at scale. |

### 4.3 MarketAux

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Free financial news API. Stocks, crypto, forex, commodities. Sentiment analysis included. |
| **Free tier**     | Yes -- 100 requests/day, 3 articles per request, global news, 5,000+ sources |
| **Paid plan**     | $199/month (or $166/month billed annually) -- 50,000 requests/day, 100 articles per request |
| **Rate limits**   | 100/day free, 50,000/day paid |
| **Reliability**   | MEDIUM -- newer service, growing |
| **Why we need it**| FREE financial news with built-in sentiment. Covers all our asset classes. Best free option. |
| **Limitation**    | 100 requests/day on free tier is tight. |
| **Verdict**       | USE FREE TIER immediately. Best complement to our existing RSS. Upgrade to paid only if needed. |

### Current vs. Upgraded News Pipeline

| Feature             | Current (RSS)     | + MarketAux Free    | + NewsAPI Paid     |
|---------------------|-------------------|---------------------|---------------------|
| Sources             | ~20 RSS feeds     | + 5,000 sources     | + 80,000 sources    |
| Asset-tagged        | Manual keyword    | YES (auto-tagged)   | Manual keyword      |
| Sentiment           | Our own scoring   | Built-in + ours     | Our own scoring     |
| Real-time           | RSS polling       | REST polling        | REST polling        |
| Cost                | $0                | $0                  | $35/mo              |
| Production ready    | Yes               | Yes                 | Yes                 |

### RECOMMENDATION: News Stack

| Source      | Role                          | Cost    |
|-------------|-------------------------------|---------|
| RSS feeds   | Keep existing (base layer)    | FREE    |
| MarketAux   | Structured financial news     | FREE    |
| NewsAPI.org | Broad news coverage (Phase 2) | $35/mo  |
| Benzinga    | Later at scale                | Skip    |
| **TOTAL**   |                               | **$0 now, $35/mo later** |

---

## 5. Infrastructure

### 5.1 Server Hosting

#### Hetzner Cloud (RECOMMENDED)

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Cloud VPS hosting from German data centers |
| **CX22 plan**     | ~$5.50/month (post-April 2026 pricing) -- 2 vCPU, 4GB RAM, 40GB SSD, 20TB transfer |
| **CX32 plan**     | ~$10.50/month -- 4 vCPU, 8GB RAM, 80GB SSD, 20TB transfer |
| **Locations**     | Germany, Finland, USA (Ashburn, Hillsboro), Singapore |
| **Note**          | Prices increased ~30-37% in April 2026 |
| **Why Hetzner**   | Best price/performance ratio in Europe. Already recommended in COMPANY.md. |

#### DigitalOcean

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Cloud VPS (Droplets) with managed services |
| **Basic plan**    | $4/month -- 1 vCPU, 512MB RAM (too small for us) |
| **Recommended**   | $24/month -- 2 vCPU, 4GB RAM |
| **Billing**       | Per-second billing (Jan 2026+), monthly cap |
| **Transfer**      | 500GB/month free outbound per Droplet |
| **Why DO**        | Simpler UI than Hetzner. US data centers. Managed databases/Redis available. |

#### AWS (for reference)

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Full cloud platform |
| **t3.medium**     | ~$30-35/month (2 vCPU, 4GB RAM) |
| **Why NOT**       | 3-5x more expensive than Hetzner/DO for same specs. Complex billing. Overkill for our stage. |

#### RECOMMENDATION

| Stage       | Provider    | Plan              | Cost/month |
|-------------|------------|-------------------|------------|
| MVP/Launch  | Hetzner    | CX22 (2CPU/4GB)   | ~$5.50     |
| Growth      | Hetzner    | CX32 (4CPU/8GB)   | ~$10.50    |
| Scale       | DigitalOcean or AWS | As needed  | $24+       |

### 5.2 Domain + SSL

| Item          | Provider      | Cost        |
|---------------|---------------|-------------|
| .com domain   | Namecheap     | ~$7 first year, ~$15/year renewal |
| SSL cert      | Let's Encrypt | FREE (auto-renews) |
| **Total**     |               | **~$1.25/month** |

Let's Encrypt provides free DV certificates that auto-renew via certbot. No reason to pay for SSL.

### 5.3 Email Service

#### SendGrid (RECOMMENDED)

| Detail            | Value |
|-------------------|-------|
| **Free tier**     | 100 emails/day forever (after 40K first-30-days bonus) |
| **Essentials**    | $19.95/month -- 50,000 emails/month |
| **Pro**           | $89.95/month -- 1.5M emails, dedicated IP |
| **Why SendGrid**  | Industry standard. Great deliverability. Python SDK. Replaces our raw SMTP. |

#### Mailgun

| Detail            | Value |
|-------------------|-------|
| **Free tier**     | 100 emails/day |
| **Starter**       | $15/month -- 10,000 emails |
| **Why Mailgun**   | Developer-friendly. Slightly cheaper. Good alternative. |

#### Current SMTP vs. Email Service

| Feature            | Raw SMTP (current) | SendGrid Free | SendGrid Essentials |
|--------------------|---------------------|---------------|---------------------|
| Deliverability     | Poor (likely spam)  | Good          | Excellent           |
| Emails/day         | Unlimited*          | 100           | ~1,600              |
| Tracking           | None                | Open/click    | Full analytics      |
| Templates          | Manual HTML         | Template engine | Template engine   |
| Cost               | $0                  | $0            | $19.95/mo           |

*Unlimited but likely to be blocked by spam filters without proper DKIM/SPF.

#### RECOMMENDATION

Use SendGrid free tier immediately (100/day is plenty for verification emails at our stage). Upgrade to Essentials ($19.95/mo) when subscriber count exceeds ~100 active users.

### 5.4 Monitoring

#### UptimeRobot

| Detail            | Value |
|-------------------|-------|
| **Free tier**     | 50 monitors, 5-min check interval. Personal/non-commercial only. |
| **Solo plan**     | $15/month -- 50 monitors, 60-sec interval, commercial use |
| **Why use it**    | Dead simple. HTTP/ping/keyword monitoring. Alerts via email/Slack/webhook. |

#### Healthchecks.io

| Detail            | Value |
|-------------------|-------|
| **Free tier**     | 20 checks (cron job monitoring). Generous. |
| **Paid plans**    | Start cheap. Ideal for monitoring our aegis_brain.py autonomous loop. |
| **Why use it**    | Monitors CRON JOBS specifically -- perfect for our scan loop, auto-trader cycle, daily reflections. |

#### RECOMMENDATION

| Service         | Use For                        | Cost   |
|----------------|--------------------------------|--------|
| UptimeRobot    | Dashboard uptime + HTTP checks | FREE   |
| Healthchecks.io | aegis_brain.py loop monitoring | FREE   |
| **Total**       |                                | **$0** |

Both free tiers are sufficient for launch.

---

## 6. Payment Processing

### Stripe

| Detail            | Value |
|-------------------|-------|
| **What it does**  | Payment processing, subscriptions, invoicing |
| **Setup cost**    | $0 -- no monthly fee, no setup fee |
| **Domestic rate** | 2.9% + $0.30 per transaction |
| **International** | 3.9% + $0.30 per transaction |
| **ACH/bank**      | 0.8% per transaction (capped at $5) |
| **Subscription billing** | Built-in -- recurring, trials, upgrades, cancellations |
| **Chargebacks**   | $15 per dispute |
| **Payout speed**  | 2 business days standard, instant for 1% fee |
| **Why Stripe**    | Industry standard. Best docs. Python SDK. Handles EU/US/global. |
| **Integration effort** | ~2-3 days for subscription billing |

### Revenue Math Example

At $29/month (Operator tier), 100 subscribers:

| Item              | Amount |
|-------------------|--------|
| Gross revenue     | $2,900/month |
| Stripe fees (2.9% + $0.30) | ~$114/month |
| Net revenue       | ~$2,786/month |
| Stripe take rate  | ~3.9% |

Stripe is the only realistic choice for SaaS subscription billing. No alternatives needed.

---

## 7. Budget Scenarios

### Scenario A: MINIMAL ($50-100/month)
> **Goal:** Better data for paper trading. No real money. Publish the app.

| Line Item            | Provider       | Cost/month |
|----------------------|----------------|------------|
| Market data (all 12) | Twelve Data Grow | $29.00   |
| Crypto streaming     | Binance WebSocket | FREE     |
| Index streaming      | Finnhub WebSocket | FREE     |
| Crypto REST fallback | CoinGecko free | FREE       |
| News (structured)    | MarketAux free | FREE       |
| News (broad)         | RSS feeds      | FREE       |
| Server               | Hetzner CX22   | $5.50     |
| Domain               | Namecheap .com | $1.25     |
| SSL                  | Let's Encrypt  | FREE       |
| Email                | SendGrid free  | FREE       |
| Monitoring           | UptimeRobot + Healthchecks | FREE |
| Payments             | Stripe (pay-per-use) | $0 base |
| Paper trading        | Alpaca paper   | FREE       |
| **TOTAL**            |                | **~$36/month** |

**What you get:** Production-deployed app with real-time data for all 12 assets,
paper trading, news intelligence, and ability to accept subscribers. This is enough
to launch and start validating the product.

---

### Scenario B: SERIOUS ($200-400/month)
> **Goal:** One real-money broker connected. Better news. Growing subscriber base.

| Line Item            | Provider         | Cost/month |
|----------------------|------------------|------------|
| Market data (all 12) | Twelve Data Grow | $29.00     |
| Crypto streaming     | Binance WebSocket | FREE      |
| Index streaming      | Finnhub WebSocket | FREE      |
| Crypto REST fallback | CoinGecko free   | FREE       |
| News (structured)    | MarketAux free   | FREE       |
| News (broad)         | NewsAPI.org paid | $35.00     |
| Server               | Hetzner CX32     | $10.50    |
| Domain               | Namecheap .com   | $1.25     |
| SSL                  | Let's Encrypt    | FREE       |
| Email                | SendGrid Essentials | $19.95  |
| Monitoring           | UptimeRobot Solo | $15.00    |
| Monitoring (cron)    | Healthchecks.io free | FREE   |
| Payments             | Stripe           | $0 base   |
| Broker (stocks+crypto) | Alpaca (live)  | FREE      |
| Broker (full)        | IBKR (all assets)| ~$10-20 (market data fees) |
| Broker (forex)       | OANDA            | FREE      |
| **TOTAL**            |                  | **~$121-$131/month** |

**What you get:** Real trading across stocks, crypto, and forex via Alpaca + IBKR + OANDA.
Full commodity futures trading through IBKR. Production-grade email, monitoring, and news.
This setup can serve 100-500 paid subscribers.

---

### Scenario C: FULL ($500-1000/month)
> **Goal:** Multi-broker, premium data, scale infrastructure, prepare for growth.

| Line Item            | Provider         | Cost/month |
|----------------------|------------------|------------|
| Market data (primary) | Twelve Data Pro | $99.00     |
| Market data (stocks) | Polygon.io Starter | $29.00   |
| Crypto streaming     | Binance WebSocket | FREE      |
| Index streaming      | Finnhub WebSocket | FREE      |
| Crypto REST          | CoinGecko Analyst| $129.00   |
| News (structured)    | MarketAux paid   | $166.00   |
| News (broad)         | NewsAPI.org paid | $35.00     |
| Server (app)         | Hetzner CX32     | $10.50    |
| Server (worker)      | Hetzner CX22     | $5.50     |
| Database (managed)   | DigitalOcean Managed PostgreSQL | $15.00 |
| Domain               | Namecheap .com   | $1.25     |
| SSL                  | Let's Encrypt    | FREE       |
| Email                | SendGrid Pro     | $89.95    |
| Monitoring           | UptimeRobot Solo | $15.00    |
| Monitoring (cron)    | Healthchecks.io paid | ~$10.00 |
| Payments             | Stripe           | $0 base   |
| Broker (stocks+crypto) | Alpaca (live)  | FREE      |
| Broker (full)        | IBKR (all assets)| ~$20-30   |
| Broker (forex)       | OANDA            | FREE      |
| Broker (crypto)      | Binance          | FREE      |
| **TOTAL**            |                  | **~$625-$660/month** |

**What you get:** Redundant data feeds (Twelve Data + Polygon + Finnhub), premium
news coverage, multi-broker execution across all asset classes, managed database,
dedicated worker server for the autonomous loop, premium email with dedicated IP.
This setup can serve 1,000+ subscribers and provides institutional-grade reliability.

---

## 8. Implementation Order

### Phase 1: Launch (Week 1-2) -- ~$36/month

1. Sign up for Twelve Data Grow ($29/mo) -- replace yfinance as primary
2. Wire Finnhub free WebSocket for S&P + NASDAQ real-time
3. Wire Binance free WebSocket for BTC + ETH real-time
4. Add MarketAux free to news pipeline
5. Deploy to Hetzner CX22
6. Register domain + Let's Encrypt SSL
7. Set up Stripe for subscription billing
8. Set up SendGrid free for email verification
9. Set up UptimeRobot + Healthchecks.io (free)
10. Integrate Alpaca paper trading (validate real-broker integration)

### Phase 2: Real Trading (Month 2) -- ~$121/month

1. Alpaca live account for stocks + crypto
2. IBKR account for commodity futures + forex
3. Upgrade to NewsAPI.org paid ($35/mo)
4. Upgrade to SendGrid Essentials ($19.95/mo)
5. Upgrade monitoring to commercial tier
6. Scale Hetzner to CX32 if needed

### Phase 3: Scale (Month 4+) -- ~$625/month

1. Add redundant data feeds (Polygon)
2. Upgrade Twelve Data to Pro
3. Add managed PostgreSQL (replace JSON files)
4. Dedicated worker server for autonomous loop
5. Premium news feeds
6. Dedicated email IP for deliverability

---

## Key Takeaways for the CEO

1. **You can launch for $36/month.** Twelve Data ($29) + Hetzner ($5.50) + domain ($1.25) covers everything needed for a production deployment with real-time data.

2. **IBKR is the only broker that can trade all 12 assets.** Alpaca is easier but limited to US stocks + crypto. For Gold, Oil, Wheat, EUR/USD -- you need IBKR.

3. **Twelve Data is the single most important API purchase.** It is the only reasonably-priced provider that covers stocks, crypto, forex, AND commodity futures in one subscription.

4. **Free tiers are surprisingly powerful.** Finnhub (real-time stocks), CoinGecko (crypto), MarketAux (news), Binance (WebSocket), Alpaca (paper trading), SendGrid (email), UptimeRobot (monitoring) -- all free and production-usable.

5. **$1000/month budget is generous.** Even the "Full" scenario only reaches ~$660/month. The remaining $340 is buffer for: unexpected API overages, premium features as you discover needs, marketing spend, or saving for a React migration.

6. **Stripe costs nothing until you make money.** No monthly fee -- you only pay the 2.9% + $0.30 per transaction when subscribers pay you.

7. **Start Minimal, scale by revenue.** Launch at $36/month, get first paying subscribers, then upgrade infrastructure and data as revenue justifies it.

---

## Sources

- [Polygon.io Pricing](https://polygon.io/pricing)
- [Twelve Data Pricing](https://twelvedata.com/pricing)
- [Alpha Vantage Premium](https://www.alphavantage.co/premium/)
- [Finnhub Pricing](https://finnhub.io/pricing)
- [CoinGecko API Pricing](https://www.coingecko.com/en/api/pricing)
- [CoinMarketCap API Pricing](https://coinmarketcap.com/api/pricing/)
- [Alpaca Markets](https://alpaca.markets/)
- [Alpaca Commission Fees](https://alpaca.markets/support/commission-clearing-fees)
- [Interactive Brokers Commissions](https://www.interactivebrokers.com/en/pricing/commissions-home.php)
- [Interactive Brokers API](https://www.interactivebrokers.com/en/trading/ib-api.php)
- [Binance Spot Trading Fees](https://www.binance.com/en/fee/schedule)
- [OANDA Pricing](https://www.oanda.com/us-en/trading/our-pricing/)
- [OANDA API](https://developer.oanda.com/)
- [NewsAPI Pricing](https://newsapi.org/pricing)
- [MarketAux Pricing](https://www.marketaux.com/pricing)
- [Benzinga APIs](https://www.benzinga.com/apis/)
- [Hetzner Cloud Pricing](https://www.hetzner.com/cloud)
- [DigitalOcean Droplet Pricing](https://www.digitalocean.com/pricing/droplets)
- [SendGrid Pricing](https://sendgrid.com/en-us/pricing)
- [Mailgun Pricing](https://www.mailgun.com/pricing/)
- [UptimeRobot Pricing](https://uptimerobot.com/pricing/)
- [Healthchecks.io Pricing](https://healthchecks.io/pricing/)
- [Stripe Pricing](https://stripe.com/pricing)
- [Namecheap Domains](https://www.namecheap.com/domains/)
