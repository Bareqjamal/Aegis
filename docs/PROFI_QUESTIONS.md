# Project Aegis: The Profi's Questions
## A Chief Questioning Officer's Audit of Project Aegis

**Author:** The Profi (CQO) | **Date:** February 26, 2026 | **Verdict:** Impressive prototype. Not ready for paying customers. Here is what needs answering before launch.

---

I have read every strategic document, every deployment file, the configuration, the auto-trader, the scanner, the paper trader, and the test suite. What follows is not criticism for its own sake. This project has serious engineering depth -- 28 views, a 10-gate trading system, macro regime awareness, social sentiment, and geopolitical overlays. That is real work. But real work does not guarantee a real business. The questions below are the ones that will determine whether Project Aegis becomes a product or remains a prototype.

---

## Section 1: Questions That Keep Me Up at Night

These are existential risks. Any one of them could kill the project.

### 1.1 What happens when yfinance breaks? [CRITICAL]

The entire data pipeline -- prices, technicals, signals, paper trading P&L -- depends on a single unofficial Yahoo Finance scraping library. yfinance is not an API with an SLA. It is a Python wrapper around Yahoo's undocumented endpoints. Yahoo has changed their endpoints before (2017, 2021, 2023) and each time it broke yfinance for days or weeks. The `market_scanner.py` hardcodes `yf.download()` calls. The `portfolio_optimizer.py` uses the same pattern. The `auto_trader.py` fetches live prices through it. If yfinance goes down for 48 hours, the entire platform shows stale prices, the bot trades on wrong data, and every signal is meaningless. **What is the contingency plan?** The REALTIME_DATA.md mentions Binance and Finnhub but zero lines of code implement this. The fallback in the dashboard reads cached prices from `watchlist_summary.json`, but those cached prices were also fetched via yfinance. There is no independent price source anywhere in the codebase.

### 1.2 Is the "publisher's exclusion" actually enough legal protection? [CRITICAL]

REGULATORY.md claims Aegis operates under the publisher's exclusion of the Investment Advisers Act of 1940, same as TradingView and Seeking Alpha. But there is a critical difference: TradingView provides charting tools. Aegis generates BUY/SELL signals with confidence percentages AND has an autonomous bot that executes trades on those signals. The Lowe v. SEC ruling (1985) protects impersonal investment advice distributed to the public. But an autonomous bot that makes personalized trade decisions based on a user's portfolio, position size, risk tolerance, and account balance may cross the line into "personalized investment advice." Has a securities attorney actually reviewed the auto-trader's behavior? The AutoPilot feature adjusts position sizing using Kelly Criterion based on the user's specific portfolio equity and trade history. That is arguably personalized. The budget line item says "$5K-$15K one-time legal review" -- has this actually been spent, or is it still a line item?

### 1.3 What is the ACTUAL signal accuracy, and is it statistically significant? [CRITICAL]

The landing page copy promises "67% average signal accuracy." The Signal Report Card page exists. But where is the rigorous backtest? The `ValidationConfig` in `config.py` defines success as a 1% move in the predicted direction within 48 hours. That is an extremely forgiving definition -- a BUY signal on BTC only needs a 1% up-move in 2 days to be "correct." BTC moves 1% in an hour on an average day. What is the accuracy when measured against a meaningful threshold like 3% or 5%? What is the accuracy net of transaction costs? What is the sample size? Is 67% from 30 predictions or 3,000? Is it statistically distinguishable from random? The test suite (`test_smoke.py`) has zero tests for signal accuracy. There is no backtest validation suite. No Monte Carlo simulation. The system could be claiming 67% accuracy on a sample size that is statistically meaningless.

### 1.4 Why would anyone switch from TradingView? [HIGH]

TradingView has 60 million users, a mature charting library, Pine Script, a social community with millions of published ideas, broker integrations, and a mobile app. Aegis has 12 assets, a Streamlit frontend, JSON files, and no user authentication. The competitive positioning in STRATEGY.md says "Autonomous analysis + AI autopilot." But TradingView has a marketplace of auto-trading bots that connect to real brokers. The "Bloomberg at 1/240th the price" angle is clever marketing, but Bloomberg's value is the data terminal (Level 2 quotes, options flow, fixed income analytics, corporate actions, filings), not the charting. Aegis has none of that data depth. **What is the honest, defensible reason a user who already has TradingView Free would pay $29/month for Aegis?** The answer needs to be one sentence, and it cannot include anything TradingView also does.

### 1.5 Customer Acquisition Cost vs. Lifetime Value: does the math work? [CRITICAL]

The revenue projection assumes 350 Pro users at month 12. GTM_PLAYBOOK.md relies on free channels: Product Hunt, Reddit, Hacker News, YouTube. These are real channels but they have limits. Product Hunt gives you one day of visibility. Reddit suppresses promotional posts aggressively. HN is hit-or-miss. YouTube requires 6-12 months to build an audience. If organic channels produce 50 Pro users instead of 350, and you need paid ads, what is the CAC? Typical fintech CAC for a $29/month product runs $80-$200. At $29/month with 15% monthly churn (common for new SaaS), LTV is about $193. If CAC is $150, the margin is $43 per customer. At that margin, reaching $20K MRR means acquiring 690 Pro users at a marketing spend of $103,500. The total 12-month budget in COMPANY.md is $30,000. **Where does the rest come from?** What churn rate is baked into the revenue projections? I cannot find it mentioned anywhere.

### 1.6 Single-founder risk: what happens when you burn out? [HIGH]

The dashboard is 7,158 lines in a single file. The entire backend is 20+ Python modules maintained by one person. The GTM plan requires daily Twitter posts, weekly YouTube videos, 2 blog posts per week, Discord community management, AND shipping 2-week sprints of new features. The execution calendar in GTM_PLAYBOOK.md maps out a solo founder's schedule that assumes 12-16 hour days, 7 days a week, for 8 consecutive weeks just to get to launch. There is no co-founder. The first hire is a contractor growth marketer at month 1. **What happens at week 6 when the founder is exhausted, a critical yfinance bug ships to production, and 3 Reddit users post negative reviews?** Is there a "minimum viable operation" plan that defines what gets cut first?

### 1.7 The 7,158-line single file: is this maintainable? [HIGH]

`dashboard/app.py` contains all 28 views in one file. STRATEGY.md correctly identifies this as past the pain threshold and recommends splitting into a views directory. But this has not been done. Every new feature adds lines to this file. Every bug fix requires scrolling through 7,000+ lines. No other developer could onboard to this codebase without weeks of orientation. The `if/elif` chain for view routing is fragile -- a typo in a view name silently fails. **What is the plan and timeline for splitting this file?** The longer it grows, the harder it becomes to split. And the moment you hire engineer #2, this file becomes a merge conflict nightmare.

### 1.8 Are users being misled about data freshness? [HIGH]

The REALTIME_DATA.md doc states: "Worst case: ~16 minutes stale." The auto-refresh on trading pages is 10 seconds. This creates a false sense of real-time data. A user sees the page refresh every 10 seconds and reasonably assumes the prices are updating. They are not. The cached price from yfinance may be 16 minutes old, and the 10-second refresh just re-renders the same stale price. For crypto, yfinance gives near-real-time data (~2s), but for commodities and forex, it is 15 minutes delayed. Gold could move $30 in 15 minutes. If a user places a paper trade at the displayed price, the actual market price may be significantly different. Is this disclosed anywhere in the UI? I do not see a "prices delayed by 15 minutes" notice in the codebase.

### 1.9 Paper trading gets boring. What is the path to real money? [HIGH]

The REGULATORY.md roadmap puts broker API integration at month 6-18, with real auto-execution requiring RIA registration at month 18-36. That means the product is paper-trading-only for at least 6 months after launch, potentially 18 months. The GTM plan projects 350 paying users at month 12, all of whom are paying $29/month to paper trade. The novelty of paper trading wears off in 2-4 weeks. After that, users need a reason to keep paying. The Alpaca integration is listed as "Sprint 14 (Week 7-8)" but the regulatory analysis says auto-execution may need RIA registration. **Which is it?** Connecting a broker API where the USER clicks buy is different from the bot auto-executing. The documents contradict each other on timeline.

### 1.10 Zero authentication, zero security: what about the first 10 users? [CRITICAL]

Right now, anyone who knows the URL can access the application. There is no login, no session management, no data isolation. The docker-compose.yml exposes PostgreSQL on port 5432 and Redis on port 6379 with default credentials (`aegis` / `aegis_secret`). The security checklist in COMPANY.md has 14 items, all unchecked. The test suite has zero security tests. There are 67 instances of `json.dump` / `_save()` / `.write_text()` across the source code, all writing to shared file paths with no user scoping. A single malicious user could corrupt every other user's data by manipulating shared JSON files. **Authentication is listed as Sprint 11, but there is no authentication library installed, no user model defined, and no data isolation pattern implemented.** How realistic is the "5-8 days" estimate?

### 1.11 What happens when two users hit the bot at the same time? [HIGH]

The `paper_trader.py` _save() function writes to a single `paper_portfolio.json` file. It uses a temp-file-then-rename pattern for atomicity, which is good. But there is no file locking. No mutex. No advisory lock. If two Streamlit sessions trigger trades simultaneously, the last write wins and the first write's trade is silently lost. The grep across the codebase shows zero uses of `file_lock`, `fcntl`, `threading.Lock`, or any concurrency primitive. With 67 JSON write points across 20 files, concurrent access will cause data loss. This is not a theoretical risk -- Streamlit spawns a new Python thread for each user session.

### 1.12 The autonomous bot makes real decisions on your behalf. Is this tested? [CRITICAL]

The auto-trader has a 10-gate decision system involving regime awareness, geopolitical risk, lesson filtering, correlation limits, Kelly sizing, and drawdown circuit breakers. This is the most safety-critical code in the entire system. The test suite has exactly zero tests for the auto-trader's decision logic. No test verifies that the drawdown circuit breaker actually pauses trading at -15%. No test verifies that the correlation limit prevents 4 crypto positions. No test verifies Kelly sizing produces sane position sizes. The config has `DRAWDOWN_PAUSE_PCT = -15.0` but what if the equity curve calculation has a bug? The bot would keep trading through a catastrophic drawdown. **The money-touching code has zero test coverage.**

---

## Section 2: Data Architecture Deep Dive

Where is the data? What happens when it breaks?

### 2.1 JSON files on disk: what about data corruption? [HIGH]

There are 20+ JSON files scattered across `src/data/` and `memory/`. Each module manages its own persistence with its own `_load()` / `_save()` pattern. There is no transaction log, no write-ahead log, no journaling. If the process crashes mid-write, the JSON file may be truncated (partially written), causing a `json.JSONDecodeError` on next load. The `paper_trader.py` uses a temp-file-rename pattern which mitigates this for portfolio data, but most other modules do direct `json.dump()` to the target file. A power failure during `market_scanner.py` writing `watchlist_summary.json` would corrupt the primary data source for the entire dashboard.

### 2.2 Redis is in docker-compose but not used anywhere in the code. [MEDIUM]

The `docker-compose.yml` provisions a Redis container with 128MB memory and AOF persistence. The `REDIS_URL` environment variable is passed to the Streamlit container. But `grep -r "redis" src/` returns zero matches. No module imports Redis. No module reads `REDIS_URL`. The Redis container starts, consumes memory, and does nothing. This is not harmful, but it signals that infrastructure decisions are aspirational rather than implemented. **When will Redis actually be integrated?** The caching layer is critical for the background data fetcher described in COMPANY.md Section 3.

### 2.3 PostgreSQL is in docker-compose but has no schema, no migrations, no ORM. [MEDIUM]

Same story as Redis. The PostgreSQL container starts with default credentials. There are no SQL files, no Alembic migrations, no SQLAlchemy models, no schema definition anywhere in the codebase. The STRATEGY.md says "PostgreSQL schema + migration (5 days)" in Phase 1. This is the foundation for multi-user data isolation. Without it, every user shares the same JSON files. **Has any thought been given to the actual schema design?** User tables, portfolio tables, watchlist tables, prediction audit trail? Five days for schema design + ORM setup + migration framework + refactoring 20+ modules from JSON to database is aggressive. Most teams estimate 2-4 weeks for a similar migration.

### 2.4 What is the backup strategy? [HIGH]

Docker volumes (`aegis-data`, `aegis-memory`, `aegis-research`) persist data across container restarts. But what if the host machine's disk fails? What if `docker compose down -v` is run accidentally (it deletes volumes)? The security checklist mentions "Automated daily backup of JSON data" -- unchecked. There is no backup script, no S3 upload, no rsync to a secondary server. For a product that tracks portfolio equity, trade history, and prediction accuracy -- data that users rely on and cannot recreate -- this is a significant gap. **What is the Recovery Point Objective (RPO)?** How much data can you afford to lose?

### 2.5 How do you ensure consistency across JSON files? [HIGH]

A single trade involves writes to: `paper_portfolio.json` (position opened), `trade_decisions.json` (decision logged), `bot_activity.json` (activity recorded), `watchlist_summary.json` (price updated), and potentially `market_predictions.json` (prediction created). These are five separate files with no transactional guarantee. If the process crashes after writing to `paper_portfolio.json` but before writing to `trade_decisions.json`, the portfolio shows a position that has no corresponding decision record. The trade journal would be incomplete. The analytics would be wrong. **Is there any reconciliation process?** Any way to detect and repair inconsistent state?

### 2.6 What happens to data during a deploy? [MEDIUM]

The GitHub Actions workflow builds a new Docker image and presumably deploys it. During the deploy, the old container stops and the new one starts. Between stop and start, any in-flight data (cached prices, pending bot decisions, mid-write JSON operations) is lost. The volumes persist, but the application state in memory does not. The auto-scheduler runs trades on a timer -- what if a deploy interrupts a trade execution cycle? Does the bot resume correctly? Is there a graceful shutdown handler?

### 2.7 67 JSON write operations across 20 files: have you mapped all of them? [MEDIUM]

This is a maintenance concern. When the migration to PostgreSQL eventually happens, every one of those 67 write points needs to be found and converted. Some are in obvious `_save()` functions. Others may be inline `json.dump()` calls buried in helper functions. Without a clear audit, the migration will miss writes, creating a hybrid state where some data goes to the database and some still goes to JSON. **Is there a data flow diagram?** A map of which modules write to which files?

### 2.8 User watchlist data lives in three places. Which is authoritative? [MEDIUM]

The `watchlist_manager.py` manages named watchlists in `src/data/watchlists/*.json` with an `_active.json` pointer. It also syncs to `src/data/user_watchlist.json` for backward compatibility. The `market_scanner.py` loads from `user_watchlist.json`. The `config.py` has a `CORE_WATCHLIST` dict. That is three sources of truth for "which assets should the scanner scan." If they diverge, the scanner scans different assets than the UI displays. The memory notes say "Always syncs to user_watchlist.json for backward compat" -- but is that sync reliable under concurrent access? What if the sync fails silently?

---

## Section 3: User Experience Gaps

Things a real user would encounter on day one.

### 3.1 Page load takes 3-5 seconds on first visit. [HIGH]

Every Streamlit page load that involves market data triggers yfinance API calls. The `_fetch_live_prices_cached` function has a 60-second TTL, so the first visitor in any 60-second window pays the full 3-5 second penalty. For a product positioning itself against Bloomberg (which loads in under a second), this is jarring. The COMPANY.md acknowledges this and proposes a background data fetcher, but it does not exist yet. **Will the background fetcher be ready before launch?** Without it, every page transition that shows prices will feel sluggish. First impressions matter enormously for conversion.

### 3.2 No mobile experience at all. [HIGH]

The product strategy document notes that 60%+ of retail traders check markets on mobile. Streamlit's default layout is desktop-only. The sidebar collapses on mobile but the content area does not reflow. Plotly charts do not resize. The Advisor cards likely overflow. The sparklines are fixed at 120x30px. The dark terminal aesthetic that looks impressive on a 27-inch monitor will be unreadable on a phone. Mobile responsiveness is listed as Sprint 13 (Week 5-6), which means it will not exist at launch. **What percentage of Product Hunt and Reddit traffic is mobile?** If it is 50%+ (typical), half your launch-day visitors will have a broken experience.

### 3.3 Alerts exist but do they actually notify anyone? [HIGH]

The `alert_manager.py` has code for email (SMTP), Discord webhooks, and Telegram webhooks. It has rate limiting and input sanitization. But there is no evidence that email credentials, Discord webhook URLs, or Telegram bot tokens are configured anywhere. The `.env.example` file presumably has placeholders, but the alert configuration UI in the dashboard -- does it actually let users enter their notification endpoints? Or does it just create alerts that trigger silently into the void? A user who sets a "Gold above $5,000" alert and never gets notified will lose trust immediately.

### 3.4 What does a new user see with zero data? [MEDIUM]

The Advisor page is the default landing page. It shows signal cards for each watchlist asset. But signals require a completed scan. The scan takes 30-40 seconds. Before the first scan, what does the user see? The memory notes mention "onboarding card (lines 1733-1760 of app.py) that shows when watchlist_summary.json is empty." But is this enough? Does the Morning Brief page show anything? Does the Trade Journal show an empty table? Does the Risk Dashboard show zeroes or errors? Every page that reads from `paper_portfolio.json`, `market_predictions.json`, or `watchlist_summary.json` needs a graceful empty state. Have all 28 views been tested with completely empty data?

### 3.5 No comparison view: you cannot put Gold and BTC side by side. [MEDIUM]

The Charts page shows one asset at a time. There is no overlay, no split-screen, no relative performance comparison. TradingView's most basic free feature is multi-chart layout. A user who wants to compare Gold, Silver, and Platinum (natural comparison set) has to click between three separate chart views. The Portfolio Optimizer runs correlation analysis, but you cannot visually compare assets. For a product called a "terminal," this is a notable gap.

### 3.6 No way to share signals externally. [MEDIUM]

The GTM playbook mentions "shareable signal cards" for Twitter and "1-click sharing" as future features. The report generator creates HTML exports. But there is no way to share a single signal, a specific chart, or a trade result as a link, image, or embed. TradingView's growth was built on shareable chart ideas. If an Aegis user wants to post "Look what the AI detected" on Twitter, they have to take a screenshot manually. Social proof requires shareability.

### 3.7 No dark/light mode toggle: forced dark only. [LOW]

The Bloomberg aesthetic is compelling for the target persona. But accessibility guidelines recommend offering a light mode alternative. Some users have visual impairments that make low-contrast dark UIs difficult to read. The `ThemeColors` class in `config.py` hardcodes dark values. Adding a light mode later means creating an entirely parallel color scheme.

### 3.8 Auto-refresh creates a jarring experience. [MEDIUM]

The 10-second auto-refresh on trading views causes the entire Streamlit page to re-render. If a user is reading an Advisor card or scrolling through the Trade Journal, the refresh snaps them back to the top. This is a known Streamlit limitation but it makes the product feel unpolished. Users will think the page is broken or loading incorrectly. Is `streamlit-autorefresh` configured to preserve scroll position? Does it re-trigger yfinance calls on every refresh?

### 3.9 The Settings page: what can users actually configure? [LOW]

The sidebar mentions a Settings view (added recently). What settings exist? Can users change their base currency? Their timezone? Their risk tolerance? Their notification preferences? Or is it a placeholder? Configuration depth signals product maturity. If the Settings page has three toggles, it feels like an afterthought.

---

## Section 4: Business Model Stress Test

Devil's advocate on whether anyone will actually pay.

### 4.1 Free tier shows 5 assets. Is that enough to hook, or too much to convert? [HIGH]

The free tier includes 5 assets, 3 scans/day, basic signals, and manual paper trading with 10 positions. For a casual trader who follows BTC, ETH, Gold, S&P 500, and one more asset, the free tier covers their entire watchlist. They get signals (albeit without numeric confidence), they can paper trade, they can read the Morning Brief summary. **What exactly forces the upgrade?** The product strategy says the trigger is hitting the 6th asset. But if 5 assets satisfy 70% of casual users, you have a generous free tier with a weak conversion trigger. Have you analyzed whether the median retail trader follows more than 5 assets? Most data suggests casual traders follow 3-5.

### 4.2 What does the user get for $29/month that they cannot get free elsewhere? [CRITICAL]

TradingView free gives you charting, basic indicators, and community ideas. Finviz free gives you screening. Yahoo Finance gives you prices and news. Reddit gives you social sentiment. CoinGlass gives you crypto metrics. StockTwits gives you social buzz. Seeking Alpha free gives you analyst opinions. All of these are free. For $29/month, Aegis gives you: all of the above combined in one dashboard + an autonomous paper trading bot + a confidence percentage on signals + the Signal Report Card. **Is the "all-in-one" value proposition strong enough?** Or will users just keep their 5 free tabs open? The honest pitch might be: "Aegis saves you 2 hours/day by combining 5 tools into one. That is worth $1/day." Is that compelling?

### 4.3 Enterprise at $199/seat: name three real companies that would buy this. [HIGH]

PRODUCT_STRATEGY.md describes "Prop Desk Pete" managing $2M at an 8-person desk currently paying $192K/year for Bloomberg. The pitch is $19K/year for Aegis instead. But Bloomberg provides Level 2 market data, options chains, bond analytics, corporate filings, chat/messaging, and a 40-year track record. Aegis provides 12-asset signals from free data sources and paper trading. No prop desk managing real money will replace Bloomberg with this. They might ADD it as a supplementary tool, but replacing Bloomberg is not credible. **Who are the realistic Enterprise buyers?** Small trading education companies? Fintech startups who need a signal API? Be specific. The $199/seat minimum 5 seats ($995/month) is a significant commitment for an unproven product.

### 4.4 The referral program rewards free months. But you need cash. [MEDIUM]

The referral structure gives away free months to both referrer and referee. At the early stage, when every dollar of MRR matters, giving away revenue to drive growth is risky. A user who refers 10 friends gets "50% lifetime" discount. That user is now paying $14.50/month forever. Their 10 friends each get a 30-day Pro trial. If 3 of 10 convert, that is $87/month in new revenue, minus the $14.50/month perpetual discount on the referrer. The math works long-term, but in the first 6 months when you need cash for hosting, marketing, and legal, every free month is cash not collected. **Would a simpler "first month free, then full price" referral be better for cash flow?**

### 4.5 Revenue projections assume $20K MRR at month 12. What if it is $500? [CRITICAL]

The projection shows 350 Pro users at $29/month at month 12. That assumes 8,000 free users with a 4.4% conversion rate. But the median B2C SaaS conversion rate is 2-3%. At 2% conversion from 8,000 free users, you have 160 Pro users ($4,640 MRR). At a more realistic 4,000 free users (organic channels only, no paid), at 2%, that is 80 Pro users ($2,320 MRR). That does not cover the $3-5K/month growth marketer contractor. **What is the survival plan if MRR plateaus at $2K/month for 6 months?** Do you cut the contractor? Do you take on a day job? Do you seek funding? The $30K budget gives you 12 months at $2,500/month burn. If revenue is $500/month, the runway is 10 months. If revenue is $2,000/month, the runway extends to 60 months. But the founder still needs to eat.

### 4.6 Annual billing at $249/year: have you modeled the cash flow impact? [MEDIUM]

The annual plan saves users 28% ($249 vs $348). For the business, it means collecting $249 upfront but recognizing $20.75/month. If 50% of Pro users choose annual billing, you get large upfront payments but then 12 months of no recurring revenue from those users. If those users churn at renewal, you have already spent the upfront cash. Annual billing is great for metrics (lower churn, higher LTV) but dangerous for cash flow if the business is also spending on growth. **What is the expected annual vs. monthly billing split?**

### 4.7 $4/month hosting is compelling. But what about hidden costs? [MEDIUM]

Hetzner at EUR 3.79/month is the infrastructure cost. But: Twelve Data for real-time commodities is $29/month. SendGrid for email scales past free tier at 100 users. Stripe takes 2.9% + $0.30 per transaction. Sentry scales past free tier. PostHog scales past free tier. Google Workspace is $6/month. Domain registration. SSL certificate (free via Let's Encrypt). **What is the realistic all-in monthly cost at 100 users, 500 users, and 1,000 users?** The competitive positioning says "runs on free data sources" but the real-time data upgrade costs $29/month. At scale, data costs dominate.

### 4.8 The "Founding Member" $19/month lifetime pricing: have you calculated the exposure? [MEDIUM]

GTM_PLAYBOOK.md recommends "$19/mo for life" as a launch incentive. If 50 founding members lock in at $19/month and you later raise prices to $39/month, those 50 users represent $12,000/year in revenue you cannot access. Over 3 years, that is $36,000 of lost revenue compared to full price. Founding member pricing creates goodwill but it also creates a permanent underpriced cohort. **Is there a cap on founding member seats?** A time limit? The playbook says "limited-time" but does not specify the limit.

---

## Section 5: Things Nobody Has Thought About

Blind spots, edge cases, and "what if" scenarios.

### 5.1 What if yfinance returns wrong data? [HIGH]

This has happened. In 2023, yfinance returned incorrect stock split adjustments for multiple tickers. In 2024, it returned stale commodity prices for hours without any error. The scanner trusts yfinance output implicitly. If yfinance returns a Gold price of $0.00 (has happened with API glitches), the technical indicators compute on garbage, the signal says STRONG BUY (price below support), the bot opens a massive position, and the paper portfolio records a trade at $0.00. Is there any price sanity check? Any "if price changed more than 20% in one hour, flag as suspicious"? I do not see one in the scanner code.

### 5.2 What if a 40% market crash happens in one day? [HIGH]

March 2020. COVID crash. S&P 500 dropped 12% in a single day. BTC dropped 50% in 48 hours. The auto-trader has a `DRAWDOWN_PAUSE_PCT = -15.0` circuit breaker, but this is measured against the paper portfolio's starting balance, not against a trailing high-water mark. If the portfolio is up 30% and then drops 15% from that peak (still up 10.5% overall), the circuit breaker does NOT trigger because the portfolio is not down 15% from its starting balance. **Is the drawdown calculation correct?** A 15% drop from peak is very different from a 15% drop from start.

### 5.3 Timezone handling: whose 2:00 PM is it? [MEDIUM]

The Economic Calendar says "FOMC at 2:00 PM." The countdown timers in `economic_calendar.py` presumably use UTC or EST. But Streamlit runs in the server's timezone. The founder is in Germany (CET/CEST). Users could be anywhere. If a user in Tokyo sees "FOMC in 3 hours" but it is actually "FOMC in 12 hours" because the timezone calculation is wrong, they will make trading decisions based on incorrect timing. **Are all timestamps displayed with explicit timezone labels?** Is there a user timezone preference?

### 5.4 What if someone clones the codebase? [MEDIUM]

The code is not open-source but it is on a development machine with no particular access controls mentioned. The STRATEGY.md mentions "Open-source scanner -> contributor funnel -> paid tiers" as part of the competitive moat. If the scanning engine and signal logic are open-sourced, what prevents a well-funded competitor from forking it, adding better data sources, and launching a competing product? The "learning loop" (MarketLearner + Chief Monitor) is the defensible moat, but the learning data (market_lessons.json, daily_reflections.json) would not transfer with the code. **Is the moat in the code or in the accumulated data?** If it is in the data, the open-source strategy undermines the moat.

### 5.5 Reddit API rate limiting and Terms of Service. [HIGH]

The social sentiment engine scrapes Reddit via the public JSON API with a 0.5-second delay between requests. Reddit's API Terms of Service require authentication via OAuth2 and limit unauthenticated access to 10 requests per minute. At 8 subreddits with multiple pages, the scanner may exceed this limit. Reddit has been actively restricting API access since 2023 (the pricing controversy that killed third-party apps). **If Reddit blocks the IP, the social sentiment score drops to zero for all assets.** Is there a fallback? Is the social component robust enough to degrade gracefully?

### 5.6 What about taxes when users move to real money? [MEDIUM]

Paper trading has no tax implications. But the roadmap promises broker integration at month 6-18. The moment users connect a real broker, every trade is a taxable event. Different jurisdictions have wildly different rules: US has wash sale rules, Germany has a flat 25% Abgeltungssteuer, UK has capital gains allowance. If the auto-trader executes 50 trades per month, the tax reporting burden is enormous. **Will Aegis provide any tax reporting features?** Or will users be surprised at tax time with hundreds of transactions and no summary?

### 5.7 The influencer tracking system: legal and ethical concerns. [MEDIUM]

The social sentiment engine tracks specific named individuals: Trump, Musk, Saylor, Powell, Yellen, Fink. It scrapes their public statements for bullish/bearish keywords. Is there a legal risk in naming specific public figures in a commercial product's trading signals? If the system says "Elon Musk sentiment: BULLISH on BTC" and Musk sues for unauthorized commercial use of his name, what is the exposure? This may fall under fair use / public figure commentary, but it has not been reviewed by counsel.

### 5.8 What if the Streamlit open-source project is discontinued? [LOW]

Streamlit was acquired by Snowflake in 2022. Snowflake's core business is cloud data warehousing, not web frameworks. If Snowflake decides to sunset Streamlit or pivot it into a Snowflake-only tool, the entire frontend needs rewriting. The migration plan mentions React at 500 users (month 9-12), but if Streamlit breaks before then, there is no frontend at all. This is low probability but high impact.

### 5.9 Internationalization: will this be multilingual? [LOW]

The founder speaks German. One persona (Investor Inga) is in Frankfurt. Another (Builder Bilal) is in Berlin. The EU market is a natural target. But the entire UI is English-only. News feeds are English-only. The RSS sources are English-language outlets. German-language financial news (Handelsblatt, Boerse.de) is not included. If the product targets European users, at minimum the disclaimers need to be in the user's language (GDPR requirement for terms of service). **Is English-only a deliberate decision or an oversight?**

### 5.10 What if the AI "learns" the wrong lessons? [HIGH]

The MarketLearner tracks predictions and validates outcomes. The Chief Monitor writes daily reflections. The auto-trader consults market lessons before trading. This is a self-reinforcing feedback loop. If the system learns a false pattern (e.g., "Gold always goes up after FOMC"), it will filter future trades based on that false lesson. Over time, these false lessons compound. There is no mechanism to expire old lessons, no statistical significance test for lesson validity, and no human review of what the AI has "learned." The `LOOP_DETECTION_THRESHOLD = 10` in MonitorConfig prevents the monitor from repeating the same reflection, but it does not prevent the system from internalizing wrong conclusions. **Who reviews the AI's lessons?** Is there a dashboard that shows what the system has learned and lets a human override bad lessons?

---

## Section 6: My Recommendations

After all the questioning, here are the five most important actions before any public launch, ranked by urgency.

### Recommendation 1: Validate Signal Accuracy With Statistical Rigor [CRITICAL -- Do This Week]

Before anything else, run a proper backtest. Take 6 months of historical data for all 12 assets. Run the scanner's signal logic against known outcomes. Measure accuracy at 1%, 3%, and 5% thresholds. Calculate the p-value: is the accuracy statistically distinguishable from a coin flip? If the accuracy is below 55% on a meaningful sample (500+ predictions), the entire product premise collapses. Do not launch a product that charges money for signals that do not beat random chance. Write tests for the auto-trader's decision logic, especially the drawdown circuit breaker, position sizing, and correlation limits. This is the code that handles money. It needs 100% branch coverage in tests.

**Deliverable:** A backtest report with sample size, accuracy per asset, per threshold, p-values, and a comparison against a buy-and-hold benchmark. Plus 20+ unit tests for auto-trader decision logic.

### Recommendation 2: Add Authentication and Data Isolation [CRITICAL -- Sprint 11, No Exceptions]

Nothing else matters if two users share the same portfolio file. Use `streamlit-authenticator` as planned, but also implement per-user directories for all JSON files. The pattern: `memory/{user_id}/paper_portfolio.json` instead of `memory/paper_portfolio.json`. This is a bigger refactor than the 5-8 day estimate suggests because it requires changing every module that calls `_load()` / `_save()` to accept a user context. Plan for 10-14 days. Do not ship multi-user access without data isolation -- it is worse than single-user.

**Deliverable:** Login/logout flow, per-user data directories, user context passed to all data access functions, shared market data kept separate from user data.

### Recommendation 3: Add a "Prices Delayed" Disclosure and Price Sanity Checks [HIGH -- Do Before Launch]

Add a visible label on every page that shows prices: "Commodity and forex prices delayed up to 15 minutes. Crypto prices near real-time." Add a price sanity check in the scanner: if any price changes more than 15% from the previous cached value, flag it as suspicious and use the cached value instead. Log the anomaly. This protects against yfinance glitches and protects user trust. It takes 1 day to implement.

**Deliverable:** UI disclosure label, price anomaly detection function, logging for flagged prices.

### Recommendation 4: Split app.py Before Adding Any More Features [HIGH -- Sprint 11]

Every day you add code to a 7,158-line file, the technical debt compounds. Create a `dashboard/views/` directory. Extract one view at a time, starting with the simplest (e.g., `logs`, `kanban`, `settings`). Each extraction is a 30-minute task. After extracting 5 simple views, extract the complex ones (Advisor, Paper Trading). The main `app.py` becomes a thin router: import the view module, call its `render()` function. This is not glamorous work. It does not ship a new feature. But it is the foundation for everything else: hiring a second engineer, debugging production issues, and maintaining sanity.

**Deliverable:** `dashboard/views/` directory with at least 10 extracted view modules, `app.py` reduced to under 3,000 lines.

### Recommendation 5: Engage a Securities Attorney [CRITICAL -- Before Any Public Monetization]

The $5K-$15K budget line for legal review is the best money you will spend. Specifically, get written opinions on: (a) whether the AutoPilot feature constitutes personalized investment advice under SEC rules, (b) whether the publisher's exclusion applies when the AI adjusts signals based on user-specific portfolio data, (c) what disclaimers are legally required in Germany (BaFin) given the founder's location, and (d) whether the influencer tracking feature creates any liability. Do not wait until month 2-3 as the roadmap suggests. Do this before accepting any payment. A cease-and-desist letter from a regulator will end the business faster than any technical bug.

**Deliverable:** Written legal opinion from a securities attorney covering the four items above, plus any required disclaimer changes.

---

## Final Word

This project has more technical depth at the prototype stage than most funded startups I have seen. The multi-agent architecture, the 10-gate trading system, the prediction tracking with self-improvement -- this is genuine engineering, not a ChatGPT wrapper with a pretty UI.

But engineering depth is not product-market fit. The hard questions are not about code. They are about whether the signals actually work, whether users will pay, whether the legal foundation holds, and whether one person can ship, market, and support a financial product simultaneously.

Answer these questions honestly, and you will know whether to charge forward or pivot. Ignore them, and you will find out the hard way.

*-- The Profi*

---

*This document should be revisited every 4 weeks. Mark questions as RESOLVED when they have been addressed with evidence, not just with plans.*
