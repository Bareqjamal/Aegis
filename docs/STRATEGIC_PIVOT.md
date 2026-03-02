# Project Aegis — Strategic Pivot Document

**Date:** February 27, 2026
**Author:** CEO (emergency strategy session)
**Status:** APPROVED — Execution begins immediately

---

## THE WAKE-UP CALL

We ran 4 critical review teams. A Product Strategist, a Technical Architect, a User Psychologist, and a Landing Page Critic. They all said the same thing from different angles:

**70% of what we built is commodity. TradingView does it better, for free, with real-time data.**

Our SMA/RSI/MACD signals? TradingView shows them interactively on real-time charts.
Our RSS keyword sentiment? TradingView has Reuters and Dow Jones.
Our Plotly charts? TradingView has 25+ chart types with drawing tools.
Our paper trading? TradingView has it, with real order books.

We are a worse version of TradingView wrapped in a Streamlit app that serves 5 users max.

**But 30% of what we built exists nowhere else.** And that 30% is what matters.

---

## THE 30% THAT MATTERS

### 1. Prediction Report Card (UNIQUE — Nobody else does this)
Every signal we generate is recorded, timestamped, validated against real market outcomes, and graded. We publish our accuracy rate. TradingView does not grade their indicators. Bloomberg does not grade their analyst research. No broker grades their own signals. This is radical transparency.

### 2. Self-Improving Signals (UNIQUE — Real adaptive weights)
When a prediction fails, the system diagnoses WHY (RSI was unreliable, MACD diverged) and adjusts confidence weights for that specific asset. The signals genuinely change over time based on outcomes.

### 3. Explainable Autonomous Bot (UNIQUE — Not a black box)
The 13-gate system shows exactly why it traded or didn't trade. "Gate 5c FAIL: 3 correlated metal positions." "Gate 2: Confidence 61% below threshold 65%." No bot on 3Commas, TrendSpider, or Cryptohopper explains its reasoning this transparently.

### 4. Multi-Layer Intelligence Stack (DIFFERENTIATED)
Technical + News + Social + Macro Regime + Geopolitical Risk + Historical Accuracy, all blended with transparent weights. Each layer is basic alone, but the combination is unique.

---

## THE PIVOT

### From: "AI Trading Terminal" (generic, competing with TradingView)
### To: "The World's First Transparent AI Trading System"

**New tagline:** "The trading AI that shows its homework."

**Core product = The Prediction Report Card.**
Not signals. Not charts. Not news sentiment. The REPORT CARD is the product. Everything else supports it.

**The positioning no incumbent can copy:**
- TradingView sells tools, not opinions. They can't publish accuracy rates.
- Brokers can't publish accuracy rates (regulatory risk).
- Roboadvisors (Wealthfront, Betterment) are black boxes by design.
- Trading bots (3Commas) execute strategies but never explain or grade them.

We are the only product willing to say: "Here's every prediction we made. Here's how many were right. Here's what we learned from the wrong ones."

---

## THE ENGAGEMENT REVOLUTION

### Current (Broken)
```
User hears about Aegis → Opens app → Sees signals → Closes tab → Forgets → Never returns
```

### New (Hooked)
```
7 AM: Email/Telegram arrives → "Were you right yesterday?" →
User opens app → Sees scorecard (3 correct, 1 wrong) →
Sees today's signals → Taps "Agree/Disagree" on each →
Tomorrow: "Were you right?" → Repeat → Streak builds → Can't stop
```

### The 3 Missing Pieces

**1. External Trigger (Morning email/Telegram)**
The alert_manager already has SMTP + webhook support. The morning_brief already generates content. Wire them. Without a trigger, no engagement loop can exist.

**2. "Agree/Disagree" Buttons on Every Signal**
Turn passive consumers into active participants. The user makes a prediction alongside the AI. Tomorrow they see: "You agreed with 4/6 signals. 3 were correct. Your accuracy: 67%. The AI: 58%. You're beating the AI."

**3. The Scorecard as the Landing Page**
The FIRST thing users see is NOT today's signals. It's YESTERDAY'S RESULTS. Were you right? What did you miss? What would you have made? Then today's signals.

---

## THE KILL LIST

### Pages to Kill (10 of 28)
| Page | Verdict | Reason |
|------|---------|--------|
| kanban | KILL | Developer tool, not a product feature |
| evolution | KILL | Internal AI navel-gazing. No trader cares |
| monitor | KILL | Agent health monitoring = ops page |
| budget | KILL | Token costs = our problem, not the user's |
| logs | KILL | Debug console, not a feature |
| performance | MERGE → analytics | Redundant |
| market_overview | MERGE → watchlist | Sector breadth = tab on watchlist |
| strategy_lab | MERGE → optimizer | Half-baked without proper UI |
| fundamentals | MERGE → asset_detail | Belongs on the detail page |
| watchlist_mgr | MERGE → watchlist | Settings modal, not a page |

### Features to Stop Building
- **i18n (German/Arabic)** — Zero users. Ship English only until 1,000 users.
- **Tier gating** — Remove all Pro restrictions. Free = full product until we have retention data.
- **More indicators** — SMA/RSI/MACD/BB is enough. Stop adding.
- **Chart improvements** — We will NEVER beat TradingView on charts. Stop trying.
- **Company infrastructure** — Dockerfiles, deploy pipelines, company blueprints. Zero users = premature.

### What to Double Down On
- The Report Card (make it the hero, not page 19 of 28)
- Plain-English bot explanations ("I bought Gold because...")
- The "Agree/Disagree" prediction game
- Morning email with yesterday's scorecard
- Accuracy streaks and personal records
- "Signals You Ignored" regret engine

---

## THE 3-PAGE PRODUCT

Strip 28 pages to 3 core pages + settings:

### Page 1: "TODAY" (Advisor + Morning Brief + Scorecard merged)
1. Yesterday's scorecard (top, most prominent)
2. Your accuracy streak
3. Signals you ignored that hit
4. Today's signals with Agree/Disagree buttons
5. Bot status (one line)

### Page 2: "MY PORTFOLIO" (Paper Trading + Journal + Analytics merged)
1. Equity curve
2. Open positions with live P&L
3. Recent trades with outcomes
4. Key metrics (Sharpe, win rate, drawdown)

### Page 3: "DEEP DIVE" (Charts + News + Asset Detail merged)
1. Technical chart (embed TradingView Lightweight Charts = free, MIT)
2. News + sentiment for this asset
3. Social pulse
4. Support/resistance + fundamentals

Everything else → collapsible "Advanced" section for power users.

---

## TECHNICAL ROADMAP

### Month 1-2: "Make It Real" ($0-29/month)
| Task | Cost | Effort | Impact |
|------|------|--------|--------|
| Binance WebSocket (BTC/ETH real-time) | $0 | 1 week | Eliminates "delayed data" for crypto |
| Finnhub WebSocket (SPY/QQQ real-time) | $0 | 3 days | Real-time indices |
| Telegram bot for signal notifications | $0 | 1 week | External trigger = retention |
| "Agree/Disagree" buttons + daily scorecard | $0 | 1 week | Core engagement mechanic |
| Morning email delivery | $0 | 3 days | Daily habit loop trigger |
| FinBERT sentiment (replace keywords) | $0 | 2 weeks | Real NLP, not keyword matching |
| TradingView widget on landing page | $0 | 2 hours | Live data, instant credibility |
| Twelve Data for commodities/forex | $29/mo | 1 week | All 12 assets real-time |

### Month 3-4: "Make It Smart"
| Task | Cost | Effort | Impact |
|------|------|--------|--------|
| FastAPI backend | $0 | 3 weeks | Unlocks everything |
| Alpaca broker integration (paper + real) | $0 | 2 weeks | Real stakes = engagement |
| XGBoost on prediction history | $0 | 2 weeks | Actually self-learning signals |
| TradingView Lightweight Charts component | $0 | 2 weeks | Pro-grade charts |
| Public prediction feed page | $0 | 1 week | SEO + social proof |

### Month 5-6: "Make It Scale"
| Task | Cost | Effort | Impact |
|------|------|--------|--------|
| React/Next.js frontend | $0 | 6-8 weeks | 50+ concurrent users |
| PostgreSQL migration | $20/mo | 2 weeks | Proper data storage |
| Mobile PWA + Telegram bot v2 | $0 | 2 weeks | Mobile experience |
| Public leaderboard | $0 | 1 week | Social proof + competition |
| Shareable scorecard images | $0 | 3 days | Viral loop (Wordle model) |

---

## THE LANDING PAGE THAT PROVES IT

### Current State: Static brochure with fake data
### Target State: Live proof the product works

**Hero:** "Every Signal Recorded. Every Prediction Graded."
Below: A live mini-scoreboard showing last 5 predictions and outcomes.

**Ticker:** Replace hardcoded prices with TradingView's free Ticker Tape widget (iframe, real data, zero maintenance).

**Demo:** Embed TradingView chart widget with Aegis signal overlays. Visitors can interact with a REAL chart before signing up.

**Social Proof:** "347 predictions tracked. 63% accuracy on Gold. 58% on BTC. See the full report card."

**The Transparency Section:** Full-width. Shows prediction history. The wins AND the losses. "We got this wrong. Here's what we learned." This is the section that makes us impossible to ignore.

---

## METRICS THAT MATTER

| Metric | Current | Target (Month 3) | Target (Month 6) |
|--------|---------|-------------------|-------------------|
| Daily "Agree/Disagree" predictions | 0 | 50/day | 500/day |
| Morning email open rate | N/A | 40% | 50% |
| Day-7 retention | ~0% (no notifications) | 25% | 40% |
| Prediction accuracy (published) | Unknown | Published weekly | Published daily |
| Landing page conversion | 0% (dead CTAs) | 3% | 7% |
| Real-time assets | 0/12 | 4/12 (crypto+indices) | 12/12 |

---

## THE DECISION

We stop being a "trading terminal" and start being **the world's first transparent AI trading system**.

We stop competing with TradingView on charts and data.
We stop building features nobody asked for.
We stop hiding our accuracy behind 28 pages of dashboard.

We start showing our homework.
We start grading ourselves publicly.
We start building the daily habit loop that makes traders check Aegis before they check anything else.

**The prediction report card is not a feature. It is the entire product.**

Everything else is in service of that one idea.

---

*"The only sustainable competitive advantage is radical transparency when everyone else is hiding behind black boxes."*

— Aegis Strategic Pivot, February 27, 2026
