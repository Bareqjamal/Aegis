# Project Aegis - AI Trading Terminal

## What is this?
Autonomous market research & trading signals system. Bloomberg-style command center for retail trading.
Multi-agent AI system that scans assets, generates BUY/SELL/NEUTRAL signals with confidence scores,
auto-executes paper trades, tracks predictions, validates outcomes, and learns from mistakes.

## Tech Stack
- **Frontend:** Streamlit (dark terminal theme) + Plotly charts + streamlit-autorefresh
- **Backend:** Python 3.9+
- **Data:** JSON files (no database) - watchlist_summary.json, paper_portfolio.json, market_predictions.json, etc.
- **Market Data:** yfinance (free), RSS feeds via feedparser (free)
- **No paid API keys required** for core functionality

## Project Structure
```
project-aegis/
├── src/                          # Core engine
│   ├── aegis_brain.py            # Main orchestration loop
│   ├── market_scanner.py         # Asset scanner + signal scoring (1200+ lines)
│   ├── market_learner.py         # Prediction tracking & validation
│   ├── auto_trader.py            # Paper trading decision engine
│   ├── news_researcher.py        # RSS news sentiment (weighted keywords + negation detection)
│   ├── chart_engine.py           # Technical indicators + chart JSON + auto-trendlines (S/R detection, trendline fitting)
│   ├── strategy_builder.py       # Natural language strategy parsing
│   ├── backtester.py             # Strategy backtesting
│   ├── paper_trader.py           # Paper portfolio simulation + trade notes + position modification (partial close, SL/TP adjust)
│   ├── risk_manager.py           # Position sizing, stop-loss, correlation matrix
│   ├── alert_manager.py          # Price/signal alerts
│   ├── agents.py                 # Agent registry & system prompts
│   ├── config.py                 # Central config + settings override pipeline + price sanity bounds
│   ├── data_store.py             # DataStore abstraction (JSON I/O, user isolation, atomic writes)
│   ├── auth_manager.py           # Authentication (register, login, tiers, email verification, feature gating)
│   ├── i18n.py                   # Multi-language support (English, German, Arabic) with RTL
│   ├── token_manager.py          # API cost tracking
│   ├── chief_monitor.py          # Daily health checks & reflections
│   ├── autonomous_manager.py     # Budget-aware autonomous decision engine
│   ├── hyperopt_engine.py        # Optuna parameter optimization
│   ├── performance_analytics.py  # Sharpe ratio, drawdown, 9 chart functions, trade timeline/streaks
│   ├── fundamentals.py           # Earnings, valuations, analyst targets
│   ├── sector_analysis.py        # Cross-market correlations, breadth
│   ├── market_discovery.py       # Extended asset scanner (Oil, Gas, S&P, etc.)
│   ├── hindsight_simulator.py    # 48h time-travel backtesting
│   ├── geopolitical_monitor.py   # Geopolitical event detection + asset impact mapping
│   ├── macro_regime.py           # Macro regime detector (Risk-On/Off/Inflationary/etc.)
│   ├── economic_calendar.py      # Economic event calendar with countdown timers
│   ├── morning_brief.py          # Auto-generated daily market summary
│   ├── social_sentiment.py      # Influencer tracking (Trump/Musk/Powell) + Reddit social buzz
│   ├── portfolio_optimizer.py   # Mean-variance optimization + efficient frontier (553 lines)
│   ├── watchlist_manager.py     # Multiple named watchlists + presets (275 lines)
│   ├── report_generator.py      # Self-contained HTML performance reports (272 lines)
│   └── data/                     # JSON data files + chart JSONs + news cache
│       ├── user_watchlist.json   # User-configurable watchlist (12 assets, add/remove via UI)
│       └── watchlists/           # Named watchlist storage (Default.json, _active.json, etc.)
│
├── dashboard/
│   └── app.py                    # Main Streamlit dashboard (~8630 lines, ALL 28 views in one file)
│
├── memory/                       # AI learning & persistence
│   ├── memory_manager.py         # Error lessons, reflections
│   ├── error_lessons.json
│   ├── market_lessons.json
│   ├── market_predictions.json
│   ├── daily_reflections.json
│   ├── paper_portfolio.json
│   └── hindsight_simulations.json
│
├── research_outputs/             # Generated markdown research reports
├── docs/                         # Architecture docs
├── kanban_board.json             # Task board
├── CHECKPOINT.md                 # Progress tracking for cross-session continuity
└── run.bat                       # Windows startup script
```

## Authentication & User Management
- Auth flow: Login/Register form → session state → full dashboard
- Guest mode: "Continue as Guest" uses `user_id="default"` (backward compat)
- Passwords: PBKDF2-HMAC-SHA256 with random salt (100K iterations)
- User profiles: `users/_profiles.json` (user_id → profile dict)
- Per-user data: `users/{user_id}/` directory with isolated JSON files
- Tiers: `free` (Recruit), `pro` (Operator), `enterprise` (Command)
- Feature gating: `PRO_VIEWS` set blocks free users from Pro-only pages (only optimizer + strategy_lab)
- Email verification: 6-digit code via SMTP (AEGIS_SMTP_* env vars), skippable, with resend, rate-limited (5 attempts/15min, 3 resends/hr)
- Trial: 14-day Pro trial, auto-downgrades on expiry
- Disclaimer: First-login acceptance required before dashboard access
- i18n: 3 languages (en/de/ar) with RTL support, sidebar selector
- Settings: `settings_override.json` read by `config.py:apply_settings_override()`, wired into auto_trader + market_scanner
- Price sanity: `PRICE_SANITY_BOUNDS` in config.py validates all yfinance prices (5-day median fallback)
- Key files: `src/auth_manager.py`, `src/data_store.py`, `src/i18n.py`, `src/config.py`

## Dashboard Navigation (dashboard/app.py)
All views live in a single file. Navigation via `st.session_state["view"]`.

### Sidebar Groups:
- **TRADING** (green): **advisor** (default), morning_brief, watchlist, charts, paper_trading, trade_journal, watchlist_mgr, alerts + **asset_detail** (contextual, not in sidebar)
- **INTELLIGENCE** (blue): news_intel, econ_calendar, report_card, fundamentals, strategy_lab, analytics, risk_dashboard, optimizer, market_overview
- **SYSTEM** (gray): kanban, evolution, performance, monitor, budget, logs, **settings**
- **RESEARCH**: Dynamic list from research_outputs/*.md files

### View routing pattern:
```python
if view == "advisor": ...      # Daily Advisor (default landing page)
elif view == "morning_brief": ...  # Morning Brief
elif view == "watchlist": ...      # Watchlist with sparklines
elif view == "econ_calendar": ...  # Economic Calendar
# etc. - sequential if/elif chain
```

## Watchlist Assets (src/data/user_watchlist.json — user-configurable)
- **All 12 assets enabled by default:** Gold, BTC, ETH, Silver, Oil, Natural Gas, S&P 500, NASDAQ, Copper, Platinum, Wheat, EUR/USD
- Users can add/remove assets via the "Manage Watchlist" UI on the Watchlist page
- market_scanner.py loads from user_watchlist.json (falls back to hardcoded defaults if missing)

## Signal Scoring
- Technical score: -100 to +100 (SMA-50/200, RSI-14, MACD, Bollinger Bands)
- Confidence: tech 40% + news 20% + historical accuracy 40%
- Labels: STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL

## Sentiment Scoring (news_researcher.py)
- Weighted keywords: 3 tiers (3.0 strong, 2.0 moderate, 1.0 mild)
- Negation detection: "not", "no", "never", etc. within 3 words flips sentiment
- Failure words: "fail", "halt", "reject", "stall" always bearish
- Score range: -1.0 (very bearish) to +1.0 (very bullish)
- Blended: news 70% + social sentiment 30%

## Social Sentiment (social_sentiment.py)
- Influencer tracking: Trump, Elon Musk, Michael Saylor, Jerome Powell, Janet Yellen, Larry Fink
- Per-influencer: asset impact weights, bullish/bearish keyword detection
- Reddit: 8 subreddits (wallstreetbets, CryptoCurrency, stocks, investing, Gold, Bitcoin, ethereum, Commodities)
- Engagement-weighted scoring (high-upvote posts count more)
- Per-asset social score: influencer 60% + Reddit 40%
- Buzz level: HIGH/MEDIUM/LOW based on mention velocity
- Confidence boost: +/-10 points based on social alignment with signal

## Economic Calendar (economic_calendar.py)
- 15 recurring event types: FOMC, NFP, CPI, PPI, ECB, OPEC, GDP, ISM, PCE, etc.
- Hardcoded 2026 key dates (FOMC, ECB, OPEC) + dynamic generation (NFP, CPI, PCE, Claims)
- Countdown timers, impact ratings (1-3 stars), affected assets, historical context

## Multi-Agent System
Scanner, Analyst, Researcher, Reasoner, Coder, NewsResearcher, MarketLearner, AutoTrader, Chief Monitor

## Autonomous Loop (aegis_brain.py)
Scan -> Social sentiment -> Auto-trade -> Validate predictions -> Market discovery -> Chief Monitor reflection -> Self-improvement

## Style Guidelines
- Dark Bloomberg-terminal aesthetic
- Color scheme: green (#3fb950) for trading, blue (#58a6ff) for intelligence, gray (#6e7681) for system
- Fonts: JetBrains Mono for data, Inter for UI text
- Auto-refresh: 10s for trading views, 30s for analytics views
- Sparklines: green for up, red for down, 30-day SVG, 120x30px
