# Project Aegis: Competitive Intelligence & Gap Analysis
## Head of Competitive Intelligence Report

**Date:** Feb 26, 2026 | **Updated:** Sprint 13 (Landing Page Deep-Dive) | **Status:** Actionable

---

# 1. COMPETITOR FEATURE MATRIX

> Legend: [x] = Has feature | [~] = Partial/limited | [ ] = Missing
> Aegis column reflects current state (Sprint 11, Feb 2026)

| Feature / Capability | TradingView | Bloomberg Terminal | Thinkorswim | Koyfin | TrendSpider | Trade Ideas | 3Commas | **Aegis (Current)** |
|---|---|---|---|---|---|---|---|---|
| **DATA & COVERAGE** | | | | | | | | |
| Real-time market data | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [ ] (15min delay) |
| Asset coverage (stocks) | [x] 100K+ | [x] Global | [x] US/Global | [x] 70K+ | [x] US stocks | [x] US stocks | [ ] | [ ] (0 stocks) |
| Asset coverage (crypto) | [x] 500+ | [~] Limited | [~] Limited | [~] Some | [ ] | [ ] | [x] 700+ | [~] (2: BTC, ETH) |
| Asset coverage (commodities) | [x] | [x] | [x] Futures | [~] | [~] | [ ] | [ ] | [x] (7 commodities) |
| Asset coverage (forex) | [x] 80+ pairs | [x] Full | [x] Full | [~] | [~] | [ ] | [ ] | [~] (1: EUR/USD) |
| Asset coverage (indices) | [x] Global | [x] Global | [x] Global | [x] Global | [x] US | [ ] | [ ] | [~] (2: S&P, NASDAQ) |
| Options data/chain | [x] | [x] | [x] Best-in-class | [ ] | [ ] | [x] | [ ] | [ ] |
| Level 2 / order book | [x] | [x] | [x] | [ ] | [ ] | [x] | [x] (crypto) | [ ] |
| Economic calendar | [x] | [x] | [x] | [x] | [ ] | [ ] | [ ] | [x] (15 event types) |
| Earnings calendar | [x] | [x] | [x] | [x] | [x] | [x] | [ ] | [~] (fundamentals.py) |
| Historical data depth | [x] 50+ years | [x] 30+ years | [x] 20+ years | [x] 20+ years | [x] 10+ years | [x] 10+ years | [x] Crypto | [~] yfinance varies |
| **CHARTING & TECHNICALS** | | | | | | | | |
| Interactive charts | [x] Best-in-class | [x] | [x] | [x] | [x] | [x] | [~] | [~] Plotly (basic) |
| Chart drawing tools | [x] 100+ tools | [x] | [x] 60+ | [~] Limited | [x] Auto-drawn | [ ] | [ ] | [ ] |
| Technical indicators | [x] 400+ | [x] 200+ | [x] 300+ | [x] 50+ | [x] 200+ | [x] 100+ | [~] | [~] 5 (SMA/RSI/MACD/BB/Vol) |
| Custom indicators (scripting) | [x] Pine Script | [x] BQL | [x] ThinkScript | [ ] | [ ] | [ ] | [ ] | [ ] |
| Multi-timeframe analysis | [x] | [x] | [x] | [x] | [x] Auto | [~] | [ ] | [~] (4H+Daily, basic) |
| Chart types (candle/heikin/renko) | [x] 15+ types | [x] | [x] 12+ types | [x] 5+ | [x] | [~] | [~] | [~] (candlestick only) |
| Replay / time-travel | [x] | [ ] | [x] | [ ] | [x] | [ ] | [ ] | [~] (hindsight_simulator) |
| **AI / MACHINE LEARNING** | | | | | | | | |
| AI-generated signals | [ ] | [ ] | [ ] | [ ] | [~] Pattern only | [x] Holly AI | [~] DCA bots | [x] (tech+news+social) |
| AI signal confidence scoring | [ ] | [ ] | [ ] | [ ] | [ ] | [x] | [ ] | [x] (0-100%) |
| Sentiment analysis (news) | [ ] | [x] Bloomberg NLP | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (weighted keywords) |
| Social sentiment tracking | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (influencers+Reddit) |
| Prediction tracking / report card | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (unique feature) |
| Self-learning / adaptation | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (MarketLearner) |
| Automated pattern recognition | [ ] | [ ] | [x] | [ ] | [x] Best-in-class | [x] | [ ] | [ ] |
| NLP for strategy building | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (strategy_builder.py) |
| Geopolitical impact analysis | [ ] | [x] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (8 event types) |
| Macro regime detection | [ ] | [x] Bloomberg Econ | [ ] | [~] | [ ] | [ ] | [ ] | [x] (Risk-On/Off/etc.) |
| **TRADING & EXECUTION** | | | | | | | | |
| Real broker integration | [ ] (via partners) | [x] EMSX | [x] Native | [ ] | [x] | [x] | [x] 18+ exchanges | [ ] |
| Paper trading | [x] | [ ] | [x] | [ ] | [x] | [x] | [x] | [x] |
| Autonomous trading bot | [ ] | [ ] | [ ] | [ ] | [~] Auto-alerts | [~] Holly AI | [x] Grid/DCA bots | [x] (12+ gate system) |
| Position sizing (Kelly/risk-based) | [ ] | [x] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (Kelly + fixed frac) |
| Stop-loss / take-profit | [ ] (chart only) | [x] | [x] | [ ] | [x] | [x] | [x] | [x] (auto-calculated) |
| Portfolio optimization | [ ] | [x] PORT | [ ] | [ ] | [ ] | [ ] | [ ] | [x] (Mean-variance, 4 strategies) |
| Risk management (VaR, exposure) | [ ] | [x] | [~] | [ ] | [ ] | [ ] | [ ] | [x] (VaR, Kelly, correlation) |
| Backtesting | [x] Pine Script | [x] | [x] | [ ] | [x] | [x] | [x] | [x] (strategy backtester) |
| **SOCIAL & COMMUNITY** | | | | | | | | |
| Social network / ideas | [x] 60M+ users | [x] IB Chat | [~] | [ ] | [ ] | [x] Trade room | [ ] | [ ] |
| Shared charts / ideas | [x] Best-in-class | [ ] | [~] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Copy trading | [x] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] Marketplace | [ ] |
| Leaderboards | [x] | [ ] | [ ] | [ ] | [ ] | [x] | [x] | [ ] |
| Community forums | [x] | [ ] | [ ] | [ ] | [ ] | [x] | [x] | [ ] |
| **ALERTS & NOTIFICATIONS** | | | | | | | | |
| Price alerts | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] |
| Technical condition alerts | [x] | [x] | [x] | [ ] | [x] Auto | [x] | [ ] | [~] (signal-based) |
| Push notifications (mobile) | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [ ] |
| Email alerts | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [ ] |
| SMS alerts | [x] | [ ] | [ ] | [ ] | [x] | [x] | [ ] | [ ] |
| Telegram / Discord bots | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [x] | [ ] |
| Webhook integrations | [x] | [x] | [ ] | [ ] | [x] | [ ] | [x] | [ ] |
| **PLATFORM & UX** | | | | | | | | |
| Web application | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] (Streamlit) |
| Desktop application | [x] | [x] (required) | [x] Native | [ ] | [x] | [x] | [ ] | [ ] |
| Mobile app (iOS) | [x] | [x] | [x] | [x] | [x] | [~] | [x] | [ ] |
| Mobile app (Android) | [x] | [x] | [x] | [x] | [x] | [~] | [x] | [ ] |
| API access | [x] (paid) | [x] B-PIPE | [x] | [x] | [ ] | [ ] | [x] | [ ] |
| Multi-monitor / layouts | [x] 8 layouts | [x] | [x] Flexible | [~] | [~] | [~] | [ ] | [ ] |
| Dark mode | [x] | [x] | [x] | [x] | [x] | [~] | [x] | [x] (default only) |
| Keyboard shortcuts | [x] | [x] Extensive | [x] | [~] | [~] | [~] | [ ] | [ ] |
| Customizable dashboards | [x] | [x] | [x] | [x] | [~] | [~] | [ ] | [ ] (fixed layout) |
| Watchlists (multiple) | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] (5 presets + custom) |
| Screener / scanner | [x] | [x] | [x] | [x] | [x] | [x] Best-in-class | [ ] | [x] (12 assets only) |
| Multi-language (i18n) | [x] 20+ | [x] | [ ] | [ ] | [ ] | [ ] | [x] | [x] (3: EN/DE/AR) |
| **PRICING** | | | | | | | | |
| Free tier | [x] (limited) | [ ] | [x] (with account) | [x] | [ ] | [ ] | [x] (limited) | [x] |
| Entry paid tier | $14.95/mo | ~$2,000/mo | $0 (with brokerage) | $27.50/mo | $29/mo | $84/mo (standard) | $37/mo (Pro) | $29/mo |
| Top tier | $59.95/mo (Premium+) | ~$2,400/mo | $0 | $83.30/mo | $139/mo (Elite) | $167/mo (premium) | $79/mo (Expert) | $199/seat/mo |

---

# 2. TOP 20 FEATURES WE ARE MISSING

Ranked by competitive impact (how much we lose by NOT having this):

| # | Missing Feature | Who Has It | Impact | Effort | Priority |
|---|---|---|---|---|---|
| 1 | **Real-time / streaming data** | ALL competitors | CRITICAL | Medium (Phase 1: $0, Phase 2: $29/mo) | P0 |
| 2 | **Mobile app or PWA** | ALL except Koyfin desktop | CRITICAL | High (PWA: 2-3 weeks, native: months) | P1 |
| 3 | **Push / email / Telegram notifications** | ALL competitors | HIGH | Low (Telegram: 1 week) | P0 |
| 4 | **Broker integration (Alpaca, IBKR)** | TradingView, Thinkorswim, 3Commas, Trade Ideas | HIGH | Medium (Alpaca API: 2-3 weeks) | P1 |
| 5 | **Massively larger asset universe** (1000+) | TradingView (100K+), Thinkorswim, Koyfin | HIGH | Medium (scanner refactor) | P1 |
| 6 | **Interactive chart drawing tools** (trendlines, fib, channels) | TradingView, Thinkorswim, TrendSpider | HIGH | High (need JS charting lib) | P2 |
| 7 | **Stock screener / universe scanner** | TradingView, Trade Ideas, Thinkorswim | HIGH | Medium | P1 |
| 8 | **Options chain / options analytics** | TradingView, Thinkorswim (best), Bloomberg | MEDIUM | High | P2 |
| 9 | **Automated pattern recognition** (head & shoulders, flags, etc.) | TrendSpider (best), Trade Ideas, Thinkorswim | MEDIUM | Medium (ML model) | P2 |
| 10 | **Social / community features** (share ideas, follow traders) | TradingView (60M users), 3Commas marketplace | MEDIUM | High (full social platform) | P2 |
| 11 | **Copy trading / strategy marketplace** | TradingView, 3Commas | MEDIUM | High | P3 |
| 12 | **Webhook integrations** (connect to Zapier, IFTTT, Discord) | TradingView, TrendSpider, 3Commas | MEDIUM | Low (1-2 weeks) | P1 |
| 13 | **API access for programmatic use** | Bloomberg, TradingView, Koyfin, 3Commas | MEDIUM | Medium (FastAPI layer) | P1 |
| 14 | **Multi-monitor / layout customization** | TradingView (8 layouts), Bloomberg, Thinkorswim | MEDIUM | High (Streamlit limitation) | P3 |
| 15 | **Keyboard shortcuts** | Bloomberg, TradingView, Thinkorswim | LOW | Low (1 week) | P2 |
| 16 | **Custom scripting language** (Pine Script equivalent) | TradingView (Pine), Bloomberg (BQL), Thinkorswim (ThinkScript) | LOW | Very High | P3 |
| 17 | **Desktop application** | Bloomberg, TradingView, Thinkorswim, TrendSpider | LOW | Medium (Electron wrap) | P3 |
| 18 | **Level 2 / order book depth** | Bloomberg, TradingView, Thinkorswim, 3Commas | LOW | Medium (requires data feed) | P3 |
| 19 | **Heatmaps** (sector, market cap, performance) | TradingView, Koyfin, Bloomberg | LOW | Low-Medium (2 weeks) | P2 |
| 20 | **Light mode toggle** | ALL competitors | LOW | Low (CSS theme, 3 days) | P2 |

---

# 3. TOP 10 DESIGN / UX PATTERNS TO ADOPT

### 3.1 TradingView's "Chart-First, Everything-Else-Second" Layout
**What they do:** The chart dominates 80% of the screen. Watchlist, alerts, and orderbook are collapsible side panels. Every interaction keeps you on the chart.
**What we should adopt:** Make the Charts page the hero experience. Add a persistent mini-chart panel on the Advisor page. Clicking any asset should open an overlay chart, not navigate away.

### 3.2 Bloomberg's Command Line / Quick-Action Bar
**What they do:** The "BLP:" command bar lets users type any function (e.g., `BTC <Curncy> GP` for a chart). Power users never touch the mouse.
**What we should adopt:** Add a "Command Palette" (Ctrl+K) that lets users type asset names, page names, or actions. Example: type "BTC chart" to jump to BTC's chart view. Streamlit's `st.text_input` with autocomplete can simulate this.

### 3.3 Thinkorswim's Customizable Grid Layout
**What they do:** Users drag-and-drop widgets (chart, scanner, watchlist, news) into a flexible grid. Every trader creates their own layout.
**What we should adopt (Streamlit-compatible version):** Offer 3-4 pre-built layout presets on the Advisor page: "Signal Focus" (current), "Chart + Signals" (split view), "Full Dashboard" (4-panel grid). Use `st.columns` with user-selectable widths.

### 3.4 Koyfin's Data Density with Readability
**What they do:** Bloomberg-level information density but with modern typography, consistent spacing, and clear visual hierarchy. Tables are the primary UI element with sortable columns, inline sparklines, and color-coded deltas.
**What we should adopt:** Standardize our data tables across all 28 views. Every table should have: sortable columns, color-coded +/- values, inline sparklines, and hover tooltips. Replace ad-hoc `st.metric` grids with a consistent `render_data_table()` component.

### 3.5 TrendSpider's "Automated Technical Analysis" Visual Layer
**What they do:** The platform auto-draws trendlines, support/resistance levels, and pattern boundaries on charts. Users see AI analysis visually, not just as text signals.
**What we should adopt:** On our chart page, overlay computed support/resistance lines, SMA crossover points, and detected patterns directly on Plotly charts. Our `chart_engine.py` already computes these values -- we just need to render them visually.

### 3.6 Trade Ideas' Real-Time Streaming Signal Board
**What they do:** Holly AI signals appear as a live streaming feed, sorted by confidence. New signals slide in from the top with a brief flash animation. Users see the market "moving" in real-time.
**What we should adopt:** On our Advisor page, add a "Live Signal Feed" ticker at the top that shows the most recent signal changes (e.g., "BTC: upgraded to STRONG BUY [82%] -- 3 min ago"). Use `st_autorefresh` with a condensed signal strip.

### 3.7 3Commas' Bot Configuration Wizard
**What they do:** Non-technical users configure trading bots through a step-by-step wizard with sliders, dropdowns, and visual previews. Each parameter has an explanation tooltip. A "Backtest" button shows projected performance before going live.
**What we should adopt:** Our auto-trader settings (currently buried in the Settings page with 15+ parameters) should become a visual "Bot Builder" wizard: Step 1 (Risk Level slider), Step 2 (Asset selection), Step 3 (Regime awareness toggle), Step 4 (Backtest preview), Step 5 (Activate).

### 3.8 TradingView's Social Proof Everywhere
**What they do:** Every chart, every idea, every indicator shows how many people are watching, liking, or using it. Social proof drives engagement ("12,400 traders watching BTC right now").
**What we should adopt (solo-user version):** Show "community signal" data on each asset card: "78% of Aegis signals were BUY on Gold this week" or "Social buzz: HIGH -- 342 Reddit mentions in 24h." We already have social sentiment data; surface it as social proof.

### 3.9 Koyfin's Breadcrumb + Context Navigation
**What they do:** Every page shows exactly where you are in the hierarchy (Dashboard > Equity > AAPL > Financials > Income Statement). Clicking any breadcrumb level navigates back. Side panel shows related pages.
**What we should adopt:** We already have `render_page_header()` with breadcrumbs (Sprint 9). Enhance it: add a "Related Pages" section below the breadcrumb (e.g., on the Charts page, show links to "News for this asset", "Fundamentals", "Social Buzz"). The `asset_detail` page already does some of this -- extend the pattern.

### 3.10 TrendSpider's Alert-to-Action Pipeline
**What they do:** When an alert triggers, users see the alert AND a one-click action: "RSI crossed 30 on AAPL -- [Buy Now] [Paper Trade] [Dismiss]". The alert is not just informational; it is actionable.
**What we should adopt:** Our alert system (`alert_manager.py`) currently stores alerts passively. When an alert triggers, show it as a toast with action buttons: "[Open Trade] [View Chart] [Dismiss]". Connect alerts directly to the quick-trade flow.

---

# 4. TOP 5 QUICK WINS (Achievable in 1-2 Weeks Each)

### Quick Win #1: Telegram Bot for Signal Notifications
**Gap it closes:** No push notifications (every competitor has notifications)
**Effort:** 1 week (python-telegram-bot library, ~200 lines)
**Implementation:** New file `src/telegram_bot.py`. On every scan cycle, if signal changes (e.g., NEUTRAL to BUY), send a formatted message to the user's Telegram chat. Bot token via env var `AEGIS_TELEGRAM_TOKEN`. Registration flow: user sends `/start` to bot, gets a chat_id, enters it in Settings page.
**Impact:** Users get notified without opening the app. Retention multiplier.

### Quick Win #2: Webhook / Discord Integration for Alerts
**Gap it closes:** No external integrations (TradingView, TrendSpider, 3Commas all have webhooks)
**Effort:** 1 week (~150 lines)
**Implementation:** Add a `webhook_url` field in Settings. When alerts trigger or signals change, POST a JSON payload to the URL. Users can connect to Discord (via Discord webhooks), Zapier, or custom systems. Pattern: `requests.post(url, json={"asset": "BTC", "signal": "STRONG BUY", "confidence": 82})`.
**Impact:** Makes Aegis programmable and connectable to the broader trading tool ecosystem.

### Quick Win #3: Visual Support/Resistance on Charts
**Gap it closes:** Charts are basic compared to TrendSpider and TradingView auto-analysis
**Effort:** 1 week (Plotly hline/shapes, ~100 lines in chart_engine.py)
**Implementation:** `chart_engine.py` already computes support/target prices (from config). Add `fig.add_hline()` for support (red dashed) and target (green dashed), plus SMA-50/200 crossover markers. Add Bollinger Band shading. This transforms our charts from "data display" to "analytical tool."
**Impact:** Charts become competitive with basic TrendSpider output. Users see the AI's analysis visually.

### Quick Win #4: Command Palette (Ctrl+K Quick Navigation)
**Gap it closes:** No keyboard shortcuts (Bloomberg and TradingView power users live on keyboard)
**Effort:** 3-5 days (~80 lines)
**Implementation:** A Streamlit text input at the top of sidebar with autocomplete. Type asset name -> jumps to asset detail. Type page name -> navigates. Use `st.selectbox` with search or a custom Streamlit component. Map common commands: "btc" -> BTC detail, "advisor" -> Advisor page, "bot" -> Paper Trading.
**Impact:** Power-user efficiency. Bloomberg users will feel at home.

### Quick Win #5: Market Heatmap Page
**Gap it closes:** No visual market overview (TradingView heatmaps are iconic)
**Effort:** 1-2 weeks (~200 lines)
**Implementation:** New view "market_heatmap" using Plotly treemap. Each rectangle is an asset from the watchlist, sized by market cap proxy, colored by daily % change (green/red gradient). Clicking a rectangle navigates to asset detail. Data already available from `scan_all()`.
**Impact:** Visually striking. Great for screenshots/marketing. Makes the 12-asset universe feel comprehensive.

---

# 5. TOP 5 STRATEGIC GAPS (Existential Risks if Not Addressed)

### Strategic Gap #1: Real-Time Data is Non-Negotiable
**The problem:** Aegis uses yfinance with 15-minute delays on stocks/commodities. Every single competitor offers real-time data. For a tool that generates BUY/SELL signals, stale data makes signals unreliable and destroys trust.
**Why it's existential:** A user sees "STRONG BUY Gold" but the price has already moved 2% in the 15 minutes since our data was fetched. They act on it and lose money. They never come back. Word spreads that "Aegis signals are delayed."
**The fix:** Already documented in `docs/REALTIME_DATA.md`. Phase 1 (Binance + Finnhub, $0) gets crypto and indices to near-real-time. Phase 2 (Twelve Data, $29/mo) covers all 12 assets. This is Sprint 12 P0.
**Timeline:** 2-3 weeks for Phase 1+2.

### Strategic Gap #2: Asset Universe is Tiny (12 vs 100,000+)
**The problem:** Aegis covers 12 assets. TradingView covers 100,000+. Even Koyfin covers 70,000+. Trade Ideas scans 8,000+ US stocks. A user who trades AAPL, TSLA, or NVDA cannot use Aegis at all.
**Why it's existential:** The addressable market for "people who only trade Gold, BTC, ETH, Oil, and 8 other assets" is a tiny fraction of all retail traders. Stock traders (the largest segment) are completely excluded.
**The fix:** Phase 1 -- Add top 50 US stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META, etc.) to DISCOVERY_ASSETS. yfinance already supports them. Scanner needs minor refactoring to handle stock-specific fundamentals (P/E, earnings). Phase 2 -- Allow users to add ANY ticker via search. Phase 3 -- Full universe screener.
**Timeline:** Phase 1: 2 weeks. Phase 2: 3-4 weeks.

### Strategic Gap #3: No Broker Integration = No Real Money = No Retention
**The problem:** Aegis is paper-trading only. 3Commas connects to 18+ exchanges. Thinkorswim IS a broker. TradingView partners with multiple brokers. Users who want to act on signals must leave Aegis, open another platform, and manually execute.
**Why it's existential:** The friction between "see signal" and "execute trade" is where users drop off. Paper trading is great for learning, but users who are ready for real money have no path within Aegis. They graduate to a competitor.
**The fix:** Alpaca API (free, commission-free US stocks + crypto) is the obvious first integration. Their API is simple (REST + WebSocket, Python SDK available). Implementation: new `src/broker_alpaca.py` (~300 lines), add "Live Trading" toggle on Paper Trading page. Start with stocks + crypto. Later: IBKR for international + futures.
**Timeline:** 3-4 weeks for Alpaca MVP.

### Strategic Gap #4: No Mobile Experience at All
**The problem:** Every competitor except Bloomberg (which has its own mobile app) offers mobile access. Streamlit is responsive but not mobile-optimized. Our 28-page navigation is desktop-designed.
**Why it's existential:** 60%+ of retail trading app usage is mobile (industry stat). Users want to check signals on their phone during the commute, get push alerts, and quick-trade from anywhere. An app that only works on desktop loses the majority of engagement moments.
**The fix:** Phase 1 (Quick) -- PWA (Progressive Web App). Add a `manifest.json` and service worker to the Streamlit app. Enables "Add to Home Screen" on mobile. Optimize sidebar for mobile (hamburger menu, larger touch targets). Phase 2 (Medium) -- React Native app with shared API backend (after FastAPI migration).
**Timeline:** PWA: 2 weeks. Native app: 3-6 months (after React migration).

### Strategic Gap #5: No Community or Social Features = No Network Effect
**The problem:** TradingView's moat is its 60M-user community. Users publish ideas, follow top traders, and discuss markets. This creates a network effect: more users = more content = more users. Aegis is a solo tool with zero social features.
**Why it's existential:** Without network effects, growth is purely marketing-driven (expensive, linear). With community, growth compounds. TradingView spends almost nothing on user acquisition because users bring other users through shared chart links and trading ideas.
**The fix:** Phase 1 -- "Aegis Community" signal sharing. Users can publish their signals/predictions (anonymized), creating a "community consensus" overlay. Phase 2 -- Leaderboard based on paper trading performance (accuracy %). Phase 3 -- Following/copying top performers. Phase 4 -- Discord integration for real-time chat.
**Timeline:** Phase 1: 3-4 weeks. Full social: 3-6 months.

---

# 6. PRICING COMPARISON

| Platform | Free Tier | Entry Paid | Mid Tier | Top Tier | Enterprise | Model |
|---|---|---|---|---|---|---|
| **TradingView** | Yes (limited charts/indicators) | Essential: ~$13/mo | Plus: ~$28/mo | Premium: ~$68/mo | Ultimate: ~$240/mo | Freemium (6 tiers) |
| **Bloomberg Terminal** | No | ~$2,665/mo (~$32K/yr) | -- | ~$2,360/mo (multi-seat) | Volume discounts | Subscription |
| **AlphaSense** | Free trial | ~$833/mo (~$10K/yr) | -- | ~$1,667/mo (~$20K/yr) | $50K-$100K+/yr | Sales-led |
| **Koyfin** | Yes (2yr data, 2 watchlists) | Plus: $39/mo | Premium: $79/mo | Advisor Core: $209/mo | Advisor Pro: $299/mo | Freemium (6 tiers) |
| **TrendSpider** | No ($19-49 paid trial) | Standard: $89/mo ($59 annual) | Premium: $149/mo ($99) | Enhanced: $199/mo ($133) | Advanced: $349/mo ($233) | Subscription |
| **Trade Ideas** | Yes (delayed data) | TI Basic: $89/mo | -- | TI Premium: $178/mo | Money Machine: $5,000 | Freemium |
| **3Commas** | Trial only (no free tier) | Starter: $20/mo ($15 disc.) | Pro: $50/mo ($40) | Expert: $140/mo ($110) | Asset Manager: $223+ | Subscription |
| **CLEO** | Free (B2C backtesting) | Essential: EUR 29/mo | Pro: EUR 69/mo | Elite: EUR 149/mo | B2B prop: custom | Dual (B2C + B2B) |
| **Aegis (Planned)** | Yes (12 assets, ALL core AI) | Pro: $29/mo | -- | Enterprise: $199/seat/mo | Min 5 seats | Freemium SaaS |

### Pricing Analysis

**Where we are positioned well:**
- $29/mo Pro is competitive with TrendSpider ($29) and cheaper than Trade Ideas ($84) and Koyfin Pro ($55).
- Free tier is more generous than TradingView Free (which limits to 2 indicators and 1 chart with ads). Aegis Free gives all 12 assets, full signals, and paper trading.
- Enterprise at $199/seat is dramatically cheaper than Bloomberg ($2,000/mo) for teams that want AI signals + terminal aesthetic.

**Where we are exposed:**
- Thinkorswim is FREE with a Schwab account. It has vastly more features (real-time data, options, 300+ indicators, full broker integration). We cannot compete on features-per-dollar with a brokerage platform that monetizes through order flow.
- TradingView at $14.95/mo (Essential) offers real-time data, 100K+ assets, and the world's best charting. Our $29/mo Pro must justify the premium through AI signals, autonomous trading, and prediction tracking that TradingView lacks.
- 3Commas at $37/mo offers actual crypto exchange integration with live automated trading. Our $29/mo paper-only bot is less valuable until we add broker integration.

**Pricing recommendations:**
1. **Keep $29/mo Pro** -- it is correctly positioned. But we MUST deliver real-time data and more assets at this price point to justify it vs TradingView Essential.
2. **Consider a $14.99/mo "Scout" tier** between Free and Pro -- matching TradingView Essential price. This captures price-sensitive users who want more than free but balk at $29.
3. **Enterprise at $199/seat is well positioned** as a Bloomberg alternative for small prop desks. But it requires the API access, team workspace, and custom assets promised in STRATEGY.md to be built.
4. **Annual discount matters** -- $249/yr ($20.75/mo effective) vs TradingView Plus at $29.95/mo makes Aegis Pro the better annual deal. Promote annual aggressively.

---

# 7. AEGIS COMPETITIVE ADVANTAGES (What We Have That Others Don't)

These are features where Aegis is AHEAD of all or most competitors. Protect and promote these:

| Advantage | Details | Who Comes Close |
|---|---|---|
| **AI Signal Confidence Scoring** | Numeric 0-100% confidence combining technicals + news + social + historical accuracy | Trade Ideas (Holly AI) has signals but no transparent confidence methodology |
| **Prediction Tracking & Report Card** | Every signal is recorded, validated against outcomes, accuracy tracked over time | NO competitor does this. This is our single most unique feature |
| **Self-Learning System** | MarketLearner + Chief Monitor autonomously adjust weights based on past accuracy | NO competitor does this publicly |
| **Autonomous Paper Trading Bot** | 12+ gate system with regime awareness, geo-risk, correlation guards, graduated drawdown | 3Commas has bots but no regime/geo awareness. Trade Ideas has Holly but no paper bot |
| **Geopolitical Impact Analysis** | 8 event types mapped to specific asset impacts with risk scoring | Bloomberg has it but at $2,000/mo. No retail competitor offers this |
| **Macro Regime Detection** | Risk-On/Off/Inflationary/Deflationary/Volatile classification affecting all signals | Bloomberg Economics has this. No retail competitor does |
| **Social Sentiment (Influencer + Reddit)** | Tracks Trump, Musk, Saylor, Powell + 8 subreddits, blended into signals | No competitor blends social sentiment directly into trading signals |
| **Integrated Intelligence Stack** | Single platform combining AI signals + news + social + geo + macro + autonomous trading | No single competitor has all of these in one platform |
| **Transparent Signal Methodology** | Users can see exactly how every signal is computed (40% tech + 20% news + 40% accuracy) | Trade Ideas and 3Commas are black boxes |
| **Extremely Low Cost Structure** | All data from free sources (yfinance, RSS, Reddit). Profitable at first Pro subscriber | Competitors spend $10K-100K+/mo on data feeds |

---

# 8. EXECUTIVE SUMMARY & RECOMMENDED PRIORITIES

## Immediate (Sprint 12-13, Next 4 Weeks)
1. **Real-time data** -- Phase 1+2 from REALTIME_DATA.md ($0-$29/mo)
2. **Telegram bot** for signal notifications (1 week)
3. **Webhook integration** for alerts (1 week)
4. **Settings pipeline fix** -- wire settings_override.json into backend (already Sprint 12 P0)
5. **Visual chart overlays** -- support/resistance lines on Plotly charts (1 week)

## Near-Term (Sprint 14-16, Weeks 5-12)
6. **Expand to 50 US stocks** in the asset universe
7. **Alpaca broker integration** MVP (paper + live)
8. **PWA for mobile** (manifest.json + responsive optimization)
9. **Command palette** (Ctrl+K navigation)
10. **Market heatmap** page

## Medium-Term (Sprint 17-24, Months 4-6)
11. **Stock screener** with AI signals on full US universe
12. **Community signal sharing** (anonymized consensus)
13. **API access** (FastAPI layer for Enterprise tier)
14. **Automated pattern recognition** on charts
15. **$14.99 Scout tier** pricing experiment

## The Winning Narrative
Project Aegis should not try to be "another TradingView." We cannot win on charting breadth, asset coverage, or community size. Instead, our positioning is:

**"The AI trading terminal that thinks for you."**

- TradingView shows you charts. **Aegis tells you what to do and tracks whether it was right.**
- Bloomberg gives you data. **Aegis gives you decisions with confidence scores.**
- 3Commas runs bots blindly. **Aegis runs bots that understand macro regimes, geopolitics, and social sentiment.**
- Trade Ideas finds patterns. **Aegis learns from its mistakes and gets smarter over time.**

The prediction report card and self-learning system are our moat. No competitor can replicate years of tracked predictions and accuracy data overnight. Every day Aegis runs, the track record grows, and the moat deepens.

---

---

# 9. COMPETITOR LANDING PAGE ANALYSIS (Sprint 13 Update)

## Landing Page Patterns Observed

### Hero Section Patterns
| Competitor | Tagline | Strategy | Social Proof |
|---|---|---|---|
| **TradingView** | "Where the world does markets" | Community scale + free entry | 100M users |
| **3Commas** | "Crypto Trading Bots & Automation" | Pain point (emotional trading) | 2M+ traders since 2017 |
| **Koyfin** | "The only platform you need" | Consolidation play | Advisor/investor trust |
| **TrendSpider** | "Replace All Your Trading Tools with One" | Consolidation + automation | 20K+ active users, Inc. 5000 |
| **Trade Ideas** | "Catch The Big Move First" | Speed/alpha + named AI (Holly) | "#1 for Active Investors" |
| **CLEO** | "Scale your trading business" | B2B infrastructure | 5M+ trades/month |
| **Bloomberg** | "Most powerful tool for financial professionals" | Authority/legacy | 350K connected professionals |
| **AlphaSense** | "AI insights you can trust" | AI-native + trust | "#1 market research tool" |

### Landing Page Best Practices (What Works)
1. **Single clear value prop** above the fold (not feature lists)
2. **Social proof number** prominently displayed (users, trades, years)
3. **Free entry CTA** as primary button ("Get started for free" / "Start free trial")
4. **Persona segmentation** (3Commas: Newbies/Advanced/Pine Users/Asset Managers)
5. **Feature comparison table** vs competitors on pricing page
6. **Dark theme for terminals** (TrendSpider, Bloomberg), light for SaaS (3Commas, Koyfin)
7. **Video/interactive demo** above the fold (AlphaSense, TradingView)

### Key Pricing Insights
- **TrendSpider is the most expensive** retail tool ($89-$349/mo) — our $29/mo undercuts massively
- **Trade Ideas charges $178/mo** for AI signals — our AI signals are FREE
- **3Commas has NO free tier** anymore (just trial) — our free tier is a weapon
- **Koyfin has advisor-specific tiers** ($209-$299/mo) — validates our $199 enterprise pricing
- **Bloomberg at ~$32K/yr** — even our enterprise ($199/mo = $2,388/yr) is 13x cheaper
- **Annual discounts range 17-32%** across competitors — we should offer 20-30%

---

# 10. AEGIS LANDING PAGE REQUIREMENTS

## What We Need to Build

### Page 1: Landing Page (/)
**Goal:** Convert visitors to free signups

**Above the Fold:**
- Hero tagline: **"The AI Trading Terminal That Thinks For You"**
- Sub-headline: "AI-powered signals, autonomous paper trading, and prediction tracking. Free forever."
- Primary CTA: **"Start Free — No Credit Card"** (green button)
- Secondary CTA: "Watch Demo" (ghost button)
- Social proof: "X signals generated | Y predictions tracked | Z% average accuracy"
- Dark Bloomberg-terminal background with subtle animated chart/data

**Below the Fold (Sections):**
1. **3 Key Differentiators** (cards):
   - "AI Signals with Confidence Scores" (vs TradingView's manual analysis)
   - "Prediction Report Card" (unique — no competitor has this)
   - "Autonomous Paper Trading Bot" (vs 3Commas' dumb bots)

2. **Feature Grid** (6 cards with icons):
   - 12+ Asset Coverage (Gold, BTC, Commodities, Indices)
   - Multi-Agent Intelligence (Scanner, Researcher, AutoTrader)
   - Risk Guardian (real-time risk monitoring)
   - Social Sentiment (Influencer + Reddit tracking)
   - Geopolitical Radar (macro regime + geo events)
   - Auto-Trendlines & Chart Analysis

3. **"How It Works"** (3 steps):
   - Step 1: Sign up free → See AI signals instantly
   - Step 2: Paper trade with confidence scores
   - Step 3: Track predictions, bot learns from mistakes

4. **Comparison Table** ("Why Aegis vs..."):
   | Feature | Aegis Free | TradingView ($14/mo) | Trade Ideas ($178/mo) | 3Commas ($20/mo) |
   |---|---|---|---|---|
   | AI Signals | Yes | No | Yes (Holly) | No |
   | Prediction Tracking | Yes | No | No | No |
   | Paper Trading Bot | Yes (12+ gates) | Basic | Basic | DCA bots |
   | Social Sentiment | Yes | No | No | No |
   | Geo/Macro Analysis | Yes | No | No | No |
   | Price | $0 | $14.95/mo | $178/mo | $20/mo |

5. **Testimonials / Screenshots** (dark terminal screenshots showing the dashboard)

6. **Pricing Preview** (link to pricing page)

7. **Footer** with legal disclaimer, links, "Built by traders, powered by AI"

### Page 2: Pricing Page (/pricing)
**Goal:** Convert free users to Pro/Enterprise

**Structure:**
- 3 tier cards side-by-side (Recruit/Operator/Command from STRATEGY.md)
- Feature comparison table (checkmarks per tier)
- FAQ section
- "Start Free" CTA on every tier
- Annual toggle with savings displayed
- Enterprise: "Contact Us" button

### Page 3: Features Page (/features)
**Goal:** SEO + detailed feature showcase
- One section per major feature with screenshot
- "Available in Free tier" badges where applicable

### Tech Stack for Landing Page
- **Static HTML/CSS/JS** (no Streamlit — needs to be fast, SEO-friendly)
- **Tailwind CSS** for styling (dark theme)
- **Deploy to Vercel** (free tier, instant deploys, custom domain)
- **Separate repo** or `/landing` directory in project-aegis
- Link "Launch App" button to Streamlit dashboard URL

### Estimated Effort
- Landing page: 2-3 days (HTML/Tailwind, responsive)
- Pricing page: 1 day
- Features page: 1-2 days
- Total: ~1 week for MVP landing site

---

*Updated by Aegis CEO, Sprint 13, Feb 26, 2026*
