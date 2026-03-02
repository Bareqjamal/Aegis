# Project Aegis: Complete Product Strategy
## From "I heard about Aegis" to "I can't live without it"

**Author:** Head of Product | **Date:** Feb 26, 2026 | **Status:** Execution-Ready

---

# 1. USER JOURNEY MAP

## Stage 1: Discovery — "How do they find us?"

### Channels (ranked by expected conversion rate)

| Channel | Cost | Timeline | Expected Conversion |
|---------|------|----------|-------------------|
| Product Hunt launch | Free | Day 1 | 3-5% signup from visitors |
| Reddit (r/algotrading, r/wallstreetbets, r/CryptoCurrency) | Free | Week 1-4 | 2-4% (high intent) |
| YouTube demo video (5-min screen recording) | Free | Week 2 | 5-8% (shows product working) |
| Twitter/X crypto & trading community | Free | Ongoing | 1-2% |
| Hacker News "Show HN" | Free | Week 2 | 2-3% (developer audience) |
| SEO blog content (target "free trading signals", "AI trading bot") | Free | Month 3-6 | 1-2% (compounds) |
| Discord trading servers (guest posts, not spam) | Free | Ongoing | 3-5% |
| Fintech newsletter sponsorships | $200-500 | Month 3+ | 1-3% |

### Landing Page — First Impression

**URL structure:** `aegis.trading` or `getaegis.com`

**Above the fold (what they see in 3 seconds):**
- Hero headline + subheadline (see Section 4 for copy)
- 15-second looping GIF: the Daily Advisor showing BUY/SELL signals with confidence scores
- Single CTA button: "Try Free — No Credit Card"
- Trust line: "12 assets. AI signals. Paper trading. Zero cost to start."

**Below the fold (scroll journey):**
1. Feature blocks (4 cards with screenshots)
2. "How it works" — 3-step visual flow
3. Live demo embed (read-only Streamlit instance with demo data)
4. Social proof (GitHub stars, user count, testimonials)
5. Pricing table (3 tiers)
6. FAQ
7. Final CTA: "Start Scanning Markets in 60 Seconds"

**What convinces them to try it:**
- The GIF is the closer. Seeing real BUY/SELL signals with confidence percentages and price data is immediately credible.
- "No credit card" removes friction entirely.
- Paper trading with $1,000 virtual money makes it feel safe.
- The Bloomberg-dark aesthetic signals "this is serious software, not a toy."

---

## Stage 2: Onboarding — "First 5 Minutes" (step by step)

This is the make-or-break window. Current state: we have a basic onboarding card (lines 1733-1760 of app.py) that shows when watchlist_summary.json is empty. That is necessary but not sufficient.

### Minute 0:00 — Signup
- **Option A (recommended for launch):** Email + password via `streamlit-authenticator`. Simple. Ships in 3 days.
- **Option B (Month 2):** Google OAuth + GitHub OAuth. Reduces friction by 40% based on SaaS benchmarks.
- **Skip for now (wrong):** Anonymous access creates no retention hook. We need an email for the daily digest.

After signup, user lands on the Daily Advisor page. This is correct — it is already the default view.

### Minute 0:30 — The Welcome Modal (NEW — does not exist yet)
Instead of the current inline card, build a modal overlay with 3 screens:

**Screen 1: "What do you trade?"**
- Checkboxes: Crypto, Commodities, Stocks/Indices, Forex, "All of the above"
- This pre-selects their watchlist from the 5 presets (already built in watchlist_manager.py)
- Psychology: they feel ownership immediately

**Screen 2: "Your AI terminal is ready"**
- Show their selected watchlist (e.g., "Crypto Focus: BTC, ETH + 2 more")
- Big green button: "Run First Scan"
- Auto-triggers `scan_all()` — the scan progress bar (already built in Sprint 10) keeps them engaged for ~40 seconds

**Screen 3: "Your first signals" (appears after scan completes)**
- Show top 3 signals with BUY/SELL badges and confidence %
- Highlight the strongest signal with a pulsing border
- Button: "Place Your First Paper Trade" (links to the Quick Trade button on the strongest signal)

### Minute 2:00 — The "Aha Moment"
The aha moment is: **Seeing a STRONG BUY signal with 78% confidence on an asset they care about, and realizing the AI already analyzed technicals + news + social sentiment to get there.**

This happens when scan completes and the Advisor cards render. The current card design already delivers this — it shows signal, confidence, score, RSI, news sentiment, social buzz, and a one-line reasoning.

### Minute 3:00 — First Paper Trade
User clicks "Quick LONG" on the strongest BUY signal. The system:
- Opens a paper position with Kelly-sized allocation
- Shows a toast: "Opened LONG BTC at $87,450. Stop-loss: $83,078. Target: $95,000."
- The sidebar portfolio ticker updates instantly (already built)

### Minute 4:00 — Guided Exploration
After the first trade, show a subtle bottom banner (not a modal — don't block them):
"You placed your first trade. Here is what to explore next:"
- Morning Brief (daily summary)
- Charts (deep technical view)
- Enable AutoPilot (the bot trades for you)

### Minute 5:00 — The Hook is Set
User has: a personalized watchlist, live signals, and a paper trade in play. They have a reason to come back tomorrow to check if their trade is winning.

### How We Avoid Overwhelming Them with 28 Views

**Progressive disclosure.** Not all 28 views are shown to new users.

| User State | Visible Views | Hidden Views |
|------------|--------------|--------------|
| Just signed up (no scan) | Advisor, Watchlist | Everything else |
| After first scan | + Morning Brief, Charts, Paper Trading | Intelligence + System |
| After first paper trade | + Trade Journal, News Intel | System views |
| After 3 days active | + Analytics, Risk Dashboard, all Intelligence | System still hidden |
| Pro user (paid) | All 28 views | None |

Implementation: Add a `user_level` field to session state. Sidebar rendering already iterates `NAV_GROUPS` (line 1182 of app.py) — add a filter that checks `user_level` before rendering each item.

---

## Stage 3: Activation — "First Week"

### Definition of "Activated User"
A user is activated when they have completed 3 of these 5 actions:

| # | Action | Tracking Event | Why It Matters |
|---|--------|---------------|----------------|
| 1 | Run first market scan | `event: scan_complete` | Proves the product works |
| 2 | Customize watchlist (add or remove 1 asset) | `event: watchlist_edit` | Creates ownership |
| 3 | Place first paper trade | `event: trade_opened` | Skin in the game |
| 4 | Read Morning Brief | `event: brief_viewed` | Daily habit seed |
| 5 | Enable AutoPilot bot | `event: bot_enabled` | The addictive feature |

### Activation Checklist (visible in sidebar)

Build a small progress widget below the portfolio ticker:

```
GETTING STARTED [###-------] 3/5
[x] Scan markets
[x] Customize watchlist
[x] Place first trade
[ ] Read Morning Brief
[ ] Enable AutoPilot
```

When all 5 are complete, replace with a congratulations message and hide after 24 hours. Store completion state in user preferences JSON.

### Gamification — Lightweight, Not Childish

Trading terminals should feel professional. No cartoon badges. Instead:

**Achievement Titles** (shown in user profile):
- "Recruit" — signed up
- "Analyst" — completed 5 scans
- "Operator" — 10 paper trades completed
- "Strategist" — built a custom strategy in Strategy Lab
- "Commander" — portfolio above $1,200 (20% return)

These titles map to the pricing tier names (Recruit = Free, Operator = Pro, Command = Enterprise), creating subconscious association.

### Free-to-Pro Trigger Points

The transition desire is triggered by encountering a **visible limitation at a moment of high engagement:**

1. **Asset ceiling:** User tries to add a 6th asset to their watchlist. Toast: "Free accounts support 5 assets. Upgrade to Pro for 50."
2. **Scan limit:** Third scan of the day blocked. Message: "You have used 3/3 daily scans. Pro users get unlimited scans."
3. **Bot restriction:** User tries to enable AutoPilot. Modal: "AutoPilot is a Pro feature. It would have traded 4 times this week based on your signals. Try Pro free for 14 days."
4. **Signal detail:** Free users see "HIGH confidence" instead of "78% confidence." The numeric precision creates envy.
5. **Missed signals alert:** After 7 days on free, show a card: "While you were away, Aegis detected 3 STRONG BUY signals you missed because Free accounts scan 3x/day. Pro scans continuously."

The most effective trigger is #5 — loss aversion (showing what they missed) converts 3x better than feature marketing.

---

## Stage 4: Retention — "Month 1+"

### Why Users Come Back Daily

The retention engine is built on 3 loops:

**Loop 1: Morning Brief (daily ritual)**
- 7:00 AM local time: Email with 1-paragraph market summary + top 3 signals
- Subject line: "AEGIS: BTC STRONG BUY (82%) | Gold SELL (64%) | 2 new trades opened"
- One-click from email to full Morning Brief page
- This is the single most important retention feature. Every trading platform that retains users has a daily notification.

**Loop 2: Bot Activity (check-in hook)**
- AutoPilot trades on its own. Users come back to see: Did the bot make money? What did it trade?
- Paper Trading page already shows bot activity feed (last 200 cycles in bot_activity.json)
- Push notification (Telegram or WhatsApp): "AutoPilot opened LONG ETH at $2,840. Confidence: 71%."

**Loop 3: Prediction Scorecard (ego loop)**
- Signal Report Card shows prediction accuracy: "Your signals are 67% accurate this month."
- Weekly email: "Your Aegis accuracy: 67% (up from 62% last week). Here is what the AI learned."
- Competitive element: "Average Aegis user accuracy: 61%. You are in the top 30%."

### The Daily Active User Workflow

```
7:00 AM  — Email notification: "3 new signals overnight"
7:02 AM  — Open Aegis → Morning Brief (30-second skim)
7:05 AM  — Check Daily Advisor → See BUY on BTC → Click Quick LONG
7:06 AM  — Glance at Paper Trading → Bot opened 1 trade overnight, +2.1% on ETH
7:08 AM  — Check Risk Dashboard → Exposure is 60%, no action needed
7:10 AM  — Done. Close app. Come back at lunch for mid-day scan.
12:30 PM — Quick scan → News Intel for any breaking events → Done.
6:00 PM  — PM notification: "Gold hit take-profit. +4.2% closed."
```

Total daily engagement: 8-15 minutes across 2-3 sessions. This matches Bloomberg Terminal usage patterns for retail.

### Engagement Metrics to Track

| Metric | Target (Month 1) | Target (Month 6) |
|--------|------------------|------------------|
| DAU/MAU ratio | 25% | 40% |
| Sessions per week | 4 | 6 |
| Average session length | 5 min | 8 min |
| Morning Brief open rate | 35% | 50% |
| Paper trades per week | 3 | 7 |
| 30-day retention | 30% | 45% |

---

## Stage 5: Conversion — "Free to Pro"

### The Trigger Event

Based on SaaS conversion data, the highest-converting trigger is: **The user has been active for 7+ days, has 5+ paper trades, and encounters a limitation during a high-engagement moment.**

Specifically:
- Day 7-10: Show a persistent (but dismissable) banner: "You have made 8 trades with 62% accuracy. Pro users get AutoPilot, which would have caught 5 additional opportunities this week. Try free for 14 days."
- Day 14 (end of trial if they started one): "Your trial ends tomorrow. Your bot has earned +$47 in paper profits. Keep it running?"

### Pricing Page Design

**Layout:** 3-column comparison table. Middle column (Pro) is visually emphasized (larger, green border, "MOST POPULAR" badge).

| | Recruit (Free) | Operator (Pro) | Command (Enterprise) |
|---|---|---|---|
| **Price** | $0/forever | $29/mo or $249/yr (save 28%) | $199/seat/mo (min 5) |
| **Assets** | 5 | 50 | Unlimited + custom |
| **Scans** | 3/day | Unlimited | Unlimited |
| **Signals** | Basic (BUY/SELL) | Full spectrum + numeric confidence | Custom weights |
| **AutoPilot** | -- | Included | Included |
| **Social Sentiment** | -- | Included | Included |
| **Paper Trading** | 10 positions | Unlimited | Unlimited |
| **Charts** | 3 indicators | 30+ indicators | 30+ + custom |
| **Morning Brief** | Summary only | Full brief + email | Full + API |
| **Risk Dashboard** | -- | Included | Included |
| **Portfolio Optimizer** | -- | Included | Included |
| **Backtesting** | -- | 5/day | Unlimited |
| **Reports** | -- | HTML export | API + scheduled |
| **Support** | Community | Email (48h) | Priority + Slack |
| **API** | -- | -- | REST + WebSocket |
| | [Start Free] | [Start 14-Day Trial] | [Contact Sales] |

### Trial Strategy: 14-Day Pro Trial

Why 14 days (not 7 or 30):
- 7 days is too short — users need 2 weekends to form a habit
- 30 days is too long — urgency disappears
- 14 days = 2 full market weeks = enough to see the bot trade, validate predictions, and get hooked on Morning Brief emails

Trial mechanics:
- Full Pro features unlocked for 14 days
- No credit card required to start (reduces friction, increases trial starts by 60%)
- Day 10: Email — "4 days left. Here is what your Pro account has done for you: [stats]."
- Day 13: Email — "Final day tomorrow. Your bot has $1,074 in paper equity. Don't lose it."
- Day 14: Features downgrade to Free. Bot pauses. Positions remain but no new ones.
- Day 15: Email — "Your AutoPilot paused. It would have traded STRONG BUY on Gold today. Reactivate?"

### Urgency Mechanisms (ethical, not dark-pattern)

1. **Missed signal counter:** "You missed 3 STRONG BUY signals today because Free scans 3x/day."
2. **Bot opportunity cost:** "AutoPilot would have earned +$23.40 this week on your watchlist."
3. **Annual discount clock:** "Save 28% with annual billing. This offer is always available." (no fake countdown)
4. **Peer comparison:** "Pro users average 71% signal accuracy vs 58% for Free users." (because they have access to more data)

---

## Stage 6: Expansion — "Pro to Enterprise / Referral"

### Pro Users Become Advocates When:
1. They have a verifiable track record (Signal Report Card shows 65%+ accuracy over 30 days)
2. They share a screenshot of a winning trade on Twitter/Discord (enable 1-click sharing)
3. They want to show friends: build a "Share My Dashboard" read-only link

### Referral Program Design

**Structure:** "Give $10, Get $10"
- Pro user shares a referral link
- Friend signs up and starts Pro trial
- If friend converts to paid Pro, both get $10 credit (applied to next billing cycle)
- Cap: 10 referrals per user per month (prevents gaming)

**Implementation:** Unique referral codes stored in user profile JSON. Track via URL parameter `?ref=USER_CODE`.

### Enterprise Triggers
A Pro user needs Enterprise when:
1. They manage money for others (needs team workspace + audit logs)
2. They want to build on top of Aegis (needs API access)
3. They have 5+ people who need access (price break at 5 seats)
4. They need custom asset universes (not just the standard 12-50)

**Enterprise sales motion:** Self-serve up to Pro. Enterprise requires a demo call. Add "Book a Demo" button on Enterprise tier that opens a Calendly link.

---

# 2. USER PERSONAS

## Persona 1: Crypto Carlos

| Attribute | Detail |
|-----------|--------|
| **Age** | 26 |
| **Location** | Miami, FL |
| **Occupation** | Marketing coordinator (trades on the side) |
| **Portfolio** | $15K, 80% crypto (BTC, ETH, SOL), 20% meme coins |
| **Current tools** | TradingView (free), Crypto Twitter, Coinglass, DEXScreener |
| **Trading style** | Momentum + social signal following. Checks Twitter 20x/day for alpha. |
| **Income** | $55K salary + $5-15K/yr trading gains |
| **Tech comfort** | High. Uses APIs, has tried trading bots. |

**Goals:**
- Find BUY signals before Crypto Twitter catches on
- Automate his "check RSI + MACD + Twitter sentiment" routine
- Build a track record to eventually manage friends' money

**Pain points:**
- TradingView free has limited indicators and no alerts
- Twitter is noisy — 95% of "alpha" is wrong
- No way to track prediction accuracy (does not know his real win rate)
- Spends 2+ hours/day manually checking charts

**How he finds Aegis:**
- Sees a screenshot on Crypto Twitter of the Daily Advisor with BUY signals
- OR: Reddit r/CryptoCurrency post about "free AI trading bot"
- OR: YouTube review by a crypto influencer

**Journey to paid:**
- Signs up free → selects "Crypto Focus" watchlist → runs first scan → sees BTC STRONG BUY
- Day 1: Places 3 paper trades. Checks back 4 hours later. Hooked.
- Day 3: Tries to enable AutoPilot. Hits paywall. Starts 14-day trial.
- Day 7: Bot has made 2 profitable trades. Social sentiment caught a Musk tweet.
- Day 14: Converts to Pro ($29/mo). "Cheaper than TradingView Premium."

**Tier:** Pro ($29/mo)
**Favorite features:** AutoPilot bot, Social Sentiment (influencer tracking), Signal Report Card (proof of accuracy)

---

## Persona 2: Investor Inga

| Attribute | Detail |
|-----------|--------|
| **Age** | 42 |
| **Location** | Frankfurt, Germany |
| **Occupation** | Senior project manager at a manufacturing company |
| **Portfolio** | $200K across ETFs, gold, a few individual stocks |
| **Current tools** | Seeking Alpha (free), Finviz, her broker's research portal |
| **Trading style** | Monthly rebalancing. Macro-driven. Buys dips, holds long. |
| **Income** | EUR 95K salary |
| **Tech comfort** | Medium. Uses Excel, comfortable with web apps, does not code. |

**Goals:**
- Spend less time on research (currently 3-4 hours/weekend reading reports)
- Get a clear "risk on / risk off" signal for her monthly rebalance
- Understand how macro events (FOMC, ECB) affect her portfolio
- Not miss major market moves while she is at work

**Pain points:**
- Information overload: reads 5 sources, gets conflicting views
- No unified view of technicals + macro + news
- Her broker's tools are clunky and 10 years old
- Missed the October 2025 gold rally because she was busy at work

**How she finds Aegis:**
- Google search: "AI investment signal tool" or "free market scanner"
- OR: Newsletter recommendation from a European finance blog
- OR: Word of mouth from a colleague who trades crypto

**Journey to paid:**
- Signs up free → selects "All Assets" watchlist → runs scan
- Week 1: Reads Morning Brief daily at 7 AM. It replaces her weekend research routine.
- Week 2: Uses Economic Calendar to time her next rebalance around FOMC
- Week 3: Discovers Portfolio Optimizer. Runs Max Sharpe analysis. Mind blown.
- Week 4: Hits 5-asset limit on Free. Needs Gold + Silver + S&P + NASDAQ + Oil + BTC = 6 assets.
- Converts to Pro for the expanded watchlist + Morning Brief emails + Risk Dashboard.

**Tier:** Pro ($29/mo, annual billing = $249/yr)
**Favorite features:** Morning Brief (daily email), Economic Calendar, Portfolio Optimizer, Risk Dashboard

---

## Persona 3: Prop Desk Pete

| Attribute | Detail |
|-----------|--------|
| **Age** | 35 |
| **Location** | Chicago, IL |
| **Occupation** | Head of trading at an 8-person prop trading desk |
| **Portfolio** | $2M+ firm capital under management |
| **Current tools** | Bloomberg Terminal ($24K/yr/seat), proprietary Python scripts, internal Slack |
| **Trading style** | Multi-asset, systematic. Trades futures, FX, crypto. 50+ trades/week. |
| **Income** | $180K base + performance bonus |
| **Tech comfort** | Very high. Reads Python, manages quant developers. |

**Goals:**
- Reduce Bloomberg Terminal cost ($192K/yr for 8 seats)
- Give junior traders a signal system that enforces discipline
- Track team performance and signal accuracy across all traders
- API access to integrate Aegis signals into their existing execution system

**Pain points:**
- Bloomberg is expensive and 80% of features go unused
- Junior traders make emotional trades. Needs a system to enforce rules.
- No affordable tool combines signals + risk management + backtesting for a team
- Internal Python scripts are fragile and unmaintained

**How he finds Aegis:**
- Hacker News "Show HN" post → tries it personally first
- OR: Fintech conference demo → sees the autonomous trading bot
- OR: A junior trader on his desk discovers it and shows the team

**Journey to paid:**
- Uses Free personally for 1 week to evaluate
- Upgrades to Pro to test AutoPilot + Risk Dashboard
- After 2 weeks, emails sales@: "Can 8 people use this? Need API access."
- Gets Enterprise demo. Converts team at $199/seat/mo = $1,592/mo ($19K/yr vs $192K Bloomberg)
- "This is 90% of Bloomberg at 10% of the cost for signal generation."

**Tier:** Enterprise (8 seats x $199/mo = $1,592/mo)
**Favorite features:** API access (webhook signals into their execution engine), team workspace, Risk Dashboard, Signal Report Card (tracks junior trader accuracy)

---

## Persona 4: Builder Bilal

| Attribute | Detail |
|-----------|--------|
| **Age** | 30 |
| **Location** | Berlin, Germany |
| **Occupation** | Full-stack developer at a fintech startup |
| **Portfolio** | $30K personal (mostly index funds + some BTC) |
| **Current tools** | Python + pandas + yfinance + custom Jupyter notebooks |
| **Trading style** | Algorithmic. Builds strategies, backtests, deploys. |
| **Income** | EUR 75K salary |
| **Tech comfort** | Expert. Builds trading bots professionally. |

**Goals:**
- Access a pre-built signal API instead of maintaining his own infrastructure
- Integrate Aegis signals into his personal trading bot (Alpaca broker)
- Build a side project: a Telegram bot that forwards Aegis signals to subscribers
- Eventually white-label Aegis signals for his startup's product

**Pain points:**
- Maintaining a market scanner is tedious (yfinance breaks, RSS feeds change)
- His custom sentiment analysis is basic compared to what Aegis does
- No affordable signal API exists (alternatives are $500+/mo)
- He wants to build ON TOP of signals, not rebuild the signal engine

**How he finds Aegis:**
- GitHub: sees the open-source repo, stars it, reads the code
- OR: Product Hunt: "AI trading terminal with signal API"
- OR: r/algotrading: someone shares their Aegis API integration

**Journey to paid:**
- Clones the repo. Runs it locally. Reads the code (especially market_scanner.py).
- Week 1: Uses it as a personal dashboard on Free tier
- Week 2: Wants API access to pipe signals into his Alpaca bot
- Emails sales@: "Do you have a REST API for signals?"
- Gets Enterprise access for the API. Builds his Telegram bot in a weekend.
- His Telegram bot gets 500 subscribers. He approaches Aegis about white-labeling.

**Tier:** Enterprise (1 seat for API, $199/mo). Eventually negotiates a custom deal for white-label.
**Favorite features:** REST API, Signal data (JSON), Backtesting engine, Webhook alerts

---

# 3. FEATURE PRIORITIZATION

## Current State Inventory

**What Aegis already has (28 views, working):**
- Full market scanner with 12 assets and signal scoring
- Paper trading with autonomous bot (10+ gate system)
- News sentiment (RSS + weighted keywords + negation detection)
- Social sentiment (influencer tracking + Reddit)
- Economic calendar, morning brief, geopolitical monitor
- Risk dashboard, portfolio optimizer, trade journal
- Multiple watchlists, strategy lab, backtesting
- Settings page, glossary tooltips, onboarding card

**What is completely missing for a paying customer:**
1. No user authentication (single-user, no login)
2. No legal disclaimers (regulatory risk)
3. No notification system (no email, no push, no Telegram)
4. No broker connection (paper trading only, forever)
5. No real-time prices (yfinance has 15-min delay)
6. Not mobile-responsive (Streamlit desktop-only)
7. No landing page (no way to discover the product)
8. No payment system (no way to charge)
9. No onboarding wizard (current card is minimal)
10. No email digest (no re-engagement)

## Top 5 Features to Build Next (Ranked by Conversion Impact)

### #1: User Authentication + Multi-User Support
**Impact on conversion: CRITICAL (blocker)**
**Effort: 5-8 days**

Without auth, there is no product to sell. There is no concept of "my signals" vs "your signals," no persistence across devices, no email to send notifications to, and no account to attach a payment to.

Build sequence:
- Day 1-2: `streamlit-authenticator` with email + hashed password
- Day 3: User profile JSON (name, email, preferences, tier, created_at)
- Day 4-5: Per-user data isolation (watchlists, portfolio, trades, settings)
- Day 6: Session management (login, logout, remember me)
- Day 7-8: Google OAuth via `authlib` (optional but recommended)

This unlocks everything else: email notifications, payment, feature gating, analytics.

### #2: Landing Page + Marketing Site
**Impact on conversion: CRITICAL (no discovery = no users)**
**Effort: 3-5 days**

The best product in the world with zero distribution is a hobby project. A landing page is the gateway to all user acquisition.

Build sequence:
- Day 1-2: Static HTML/CSS page (dark theme matching the terminal aesthetic)
- Day 3: Deploy to Vercel/Netlify (separate from the Streamlit app)
- Day 4: SEO optimization (meta tags, OG images, sitemap)
- Day 5: Product Hunt listing preparation

The landing page copy is in Section 4 of this document.

### #3: Daily Email Digest + Telegram Alerts
**Impact on conversion: HIGH (retention = revenue)**
**Effort: 4-6 days**

Email is the retention engine. Without it, users must remember to open the app. With it, the app comes to them every morning. This is the difference between 25% DAU/MAU and 40% DAU/MAU.

Build sequence:
- Day 1-2: Email service integration (SendGrid free tier: 100 emails/day, enough for 100 DAU)
- Day 3: Morning Brief email template (HTML, dark theme, responsive)
- Day 4: Alert email template (signal alerts, bot trade notifications)
- Day 5: Telegram bot integration (python-telegram-bot library)
- Day 6: User notification preferences in Settings page

Why this ranks above payment: a user who gets daily emails for 14 days is 3x more likely to convert than one who only uses the web app.

### #4: Payment Integration (Stripe)
**Impact on conversion: CRITICAL (no payment = no revenue)**
**Effort: 3-4 days**

Once auth + landing page + email are in place, you need the ability to actually charge money.

Build sequence:
- Day 1: Stripe account setup + subscription products (Free, Pro monthly, Pro annual)
- Day 2: Stripe Checkout session integration (redirect flow, simplest approach)
- Day 3: Webhook handler for subscription events (activated, cancelled, payment failed)
- Day 4: Feature gating system (check user.tier before rendering Pro features)

Keep it simple: use Stripe Checkout (hosted payment page), not custom payment forms. This handles PCI compliance, receipts, cancellation, and card updates.

### #5: Legal Disclaimers on Every Page
**Impact on conversion: MEDIUM (but risk mitigation is non-negotiable)**
**Effort: 1-2 days**

Any product that shows BUY/SELL signals on financial assets needs legal protection. Without disclaimers, you face regulatory risk from SEC, FCA, BaFin (since the founder is in Germany), and others.

Build sequence:
- Day 1: Add footer disclaimer to every page: "For educational purposes only. Not financial advice. Paper trading only. Past performance does not indicate future results."
- Day 1: Add full legal disclaimer page (Terms of Service, Privacy Policy)
- Day 2: First-login acknowledgment modal: "I understand this is not financial advice" checkbox

This is boring but essential. Financial regulators have shut down products for less.

### Full Ranking of All 14 Features

| Rank | Feature | Impact | Effort | Build When |
|------|---------|--------|--------|------------|
| 1 | User Authentication | Blocker | 5-8 days | Sprint 11 |
| 2 | Landing Page | Blocker | 3-5 days | Sprint 11 |
| 3 | Email Digest + Telegram | High | 4-6 days | Sprint 12 |
| 4 | Stripe Payment | Blocker | 3-4 days | Sprint 12 |
| 5 | Legal Disclaimers | Medium (risk) | 1-2 days | Sprint 11 |
| 6 | Onboarding Wizard | Medium | 2-3 days | Sprint 12 |
| 7 | Mobile-Responsive | Medium | 5-7 days | Sprint 13 |
| 8 | Real-Time Prices | Medium | 3-5 days | Sprint 13 |
| 9 | Broker API (Alpaca) | High (but later) | 5-8 days | Sprint 14 |
| 10 | Daily Email Digest | Medium | 2-3 days | Part of #3 |
| 11 | API for Developers | Medium | 5-8 days | Sprint 15 |
| 12 | WhatsApp/Telegram | Low | 2-3 days | Part of #3 |
| 13 | Performance Leaderboard | Low | 3-4 days | Sprint 16 |
| 14 | Strategy Marketplace | Low | 8-12 days | Sprint 17+ |
| 15 | Social Features | Low | 5-8 days | Sprint 17+ |

---

# 4. LANDING PAGE COPY

## Hero Section

**Headline:**
> Your AI Trading Terminal. Signals You Can Trust.

**Subheadline:**
> Aegis scans 12+ markets, runs technical + news + social analysis, and delivers BUY/SELL signals with confidence scores. Paper trade with an autonomous AI bot. See exactly how accurate each signal is.

**CTA Button:** `Start Free — No Credit Card Required`

**Trust line:** `Join 500+ traders using Aegis | 12 assets | Real-time signals | $0 to start`

---

## Feature Blocks

### Block 1: "AI-Powered Signal Engine"
**Icon:** Radar / Signal waves

Aegis combines 5 layers of market intelligence into a single BUY or SELL verdict for each asset. Technical indicators (RSI, MACD, Bollinger Bands, SMA crossovers) form the base. News sentiment from 15+ RSS feeds adds context. Social signals from Reddit and key market influencers detect emerging trends. Macro regime detection (Risk-On, Risk-Off, Inflationary) adjusts the model. Every signal comes with a confidence percentage so you know how much to trust it.

### Block 2: "Autonomous Paper Trading Bot"
**Icon:** Robot / Autopilot

Enable AutoPilot and Aegis trades for you — on paper. The bot runs a 10-gate decision system: signal strength, confidence threshold, regime adjustment, geopolitical risk overlay, lesson filter (it learns from past mistakes), position limits, cooldown periods, and a drawdown circuit breaker. It sizes positions using Kelly Criterion or fixed-fractional methods. You watch. It learns. You decide when to go live.

### Block 3: "Track Record You Can Audit"
**Icon:** Clipboard / Checkmark

Every signal Aegis generates is recorded and validated against actual market outcomes. The Signal Report Card shows accuracy by asset, by time period, by signal type. No black box. No "trust us." Open the Report Card and see: "BTC BUY signals have been 72% accurate over the last 30 days." This is how you build confidence before risking real capital.

### Block 4: "Bloomberg-Grade Intelligence at 1% of the Cost"
**Icon:** Globe / Dashboard

Morning Brief summarizes overnight moves in 60 seconds. Economic Calendar counts down to FOMC, NFP, CPI, ECB, and OPEC. Geopolitical Monitor maps global events to your portfolio. Risk Dashboard shows Value-at-Risk, exposure, and correlations. Portfolio Optimizer runs mean-variance analysis with 4 strategies. All of this runs on free data sources. No $24,000/year terminal required.

---

## "How It Works" Section

**Step 1: Pick Your Markets**
Choose from crypto, commodities, indices, and forex. Start with a preset watchlist or build your own.

**Step 2: Scan and Receive Signals**
Aegis analyzes technicals, news, social sentiment, and macro conditions. Each asset gets a signal (STRONG BUY to STRONG SELL) with a confidence percentage.

**Step 3: Trade, Track, and Learn**
Place paper trades with one click. Enable AutoPilot for hands-free trading. Track every prediction against actual outcomes. The system learns from its mistakes and gets smarter over time.

---

## Social Proof Section

> "I replaced 3 hours of weekend chart analysis with a 2-minute Morning Brief scan. My paper portfolio is up 18% in 6 weeks."
> -- Early beta tester

> "The Signal Report Card changed how I think about trading. I finally know my actual accuracy rate instead of guessing."
> -- Early beta tester

**Metrics bar:**
- "12 assets tracked"
- "500+ signals generated"
- "67% average signal accuracy"
- "10-gate autonomous trading system"

*(Replace with real metrics once you have user data)*

---

## Pricing Table

*(Use the table from Stage 5 above — the 3-tier comparison)*

**Below the pricing table:**
"All plans include: dark terminal interface, 14 technical indicators, paper trading, economic calendar, and community support. Upgrade or cancel anytime."

---

## FAQ Section

**Q1: Is Aegis a financial advisor? Will it tell me what to invest in?**
No. Aegis is a market research and analysis tool for educational purposes. It generates signals based on technical and sentiment analysis, but these are not financial advice. All trading is paper (simulated). You should consult a licensed financial advisor before making investment decisions with real money.

**Q2: Do I need to pay for market data or API keys?**
No. Aegis runs entirely on free data sources (Yahoo Finance, RSS news feeds, public Reddit data). The Free tier costs nothing. Pro adds more assets and features but the underlying data remains free.

**Q3: How accurate are the signals?**
Every signal is tracked and validated against actual market outcomes. You can view accuracy rates on the Signal Report Card page. Typical accuracy ranges from 55-75% depending on the asset and time period. Past performance does not guarantee future results.

**Q4: Can I connect Aegis to a real broker?**
Not yet. Aegis currently supports paper trading only. Broker integration (Alpaca, Interactive Brokers) is on our roadmap. When available, it will be a Pro feature with additional risk disclosures.

**Q5: Is my data private?**
Yes. Your watchlists, paper portfolio, trade history, and preferences are private to your account. Market data (prices, news, economic events) is shared across all users. We do not sell user data. Full privacy policy is available at /privacy.

---

## Final CTA Section

**Headline:** "Stop Guessing. Start Scanning."

**Subheadline:** "Join Aegis and see your first AI-generated trading signals in under 2 minutes."

**CTA Button:** `Create Free Account`

**Below CTA:** "Free forever. No credit card. Upgrade when you're ready."

---

# 5. EXECUTION ROADMAP (Solo Founder)

## Sprint 11 (Week 1-2): "Make It Launchable"
- [ ] User authentication (streamlit-authenticator)
- [ ] Legal disclaimers (footer + TOS page + first-login acknowledgment)
- [ ] Landing page (static HTML, deploy to Vercel)
- [ ] Feature gating logic (user.tier checks in sidebar + view rendering)

## Sprint 12 (Week 3-4): "Make It Sticky"
- [ ] Email integration (SendGrid + morning brief template)
- [ ] Telegram bot for alert notifications
- [ ] Stripe payment (Checkout flow + webhook handler)
- [ ] Onboarding wizard (3-screen modal after signup)
- [ ] Activation checklist (sidebar widget)

## Sprint 13 (Week 5-6): "Make It Polished"
- [ ] Mobile-responsive CSS (Streamlit custom CSS for tablet/phone)
- [ ] Real-time prices (Finnhub free tier or Binance for crypto)
- [ ] Product Hunt launch preparation + submission
- [ ] Analytics integration (Plausible or PostHog for user tracking)

## Sprint 14 (Week 7-8): "Make It Real"
- [ ] Broker API integration (Alpaca paper trading first, then live)
- [ ] API endpoint for Enterprise (FastAPI sidecar)
- [ ] Performance leaderboard (anonymized, opt-in)
- [ ] Referral system (unique codes + credit tracking)

**Total time to revenue-generating product: 8 weeks of focused execution.**

---

# 6. KEY METRICS TO TRACK

## North Star Metric
**Weekly Active Traders (WAT):** Users who placed at least 1 paper trade or had AutoPilot execute 1+ trade in the last 7 days.

## Supporting Metrics

| Category | Metric | Target (Month 3) |
|----------|--------|------------------|
| Acquisition | Signups/week | 100 |
| Activation | % completing 3/5 checklist items within 7 days | 40% |
| Retention | 30-day retention | 30% |
| Revenue | MRR | $435 |
| Revenue | Free-to-Pro conversion rate | 3-5% |
| Engagement | Morning Brief email open rate | 35% |
| Engagement | Sessions per user per week | 4 |
| Product | Average signal accuracy (system-wide) | 60%+ |

---

# 7. RISKS AND MITIGATIONS

| Risk | Severity | Mitigation |
|------|----------|------------|
| Regulatory action (unlicensed advice) | High | Disclaimers everywhere. "Educational only." No real money trading until broker API with proper disclosures. |
| yfinance rate limiting or shutdown | High | Already mitigated with 15s timeout + caching. Plan migration to Finnhub/Polygon.io. |
| Signal accuracy drops below 55% | Medium | MarketLearner already adapts. Add FinBERT NLP to improve news sentiment. Transparent Report Card builds trust even when accuracy dips. |
| Streamlit scaling ceiling (~5K users) | Medium | Plan React + FastAPI migration at 2-3K concurrent users (Month 9-12 per STRATEGY.md). |
| Single founder burnout | High | Automate everything possible. The autonomous brain loop already self-improves. Focus on auth + payment + landing page, then content marketing (lower effort). |
| No mobile experience | Medium | 60%+ of retail traders check markets on mobile. CSS-only responsive fix buys time before native app. |

---

*This document is the execution plan. Auth and landing page are Sprint 11. Revenue starts Sprint 12. Product Hunt launch at Sprint 13. Everything here can be built by one person in 8 weeks.*
