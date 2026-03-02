# VP Trading Systems — Department Report
> Aegis Trading Terminal | February 2026

---

## 1. Signal Engine Assessment

### Current Scoring Model (`market_scanner.py` — 1200+ lines)

| Indicator | Weight | Range | What It Measures |
|-----------|--------|-------|-----------------|
| SMA-50/200 | Cross detection | Trend | Golden cross (bullish) / Death cross (bearish) |
| RSI-14 | Momentum | 0-100 | Overbought (>70) / Oversold (<30) |
| MACD | Signal line cross | Momentum | Bullish/bearish divergence |
| Bollinger Bands | Band position | Volatility | Price relative to 2-sigma bands |

**Composite Technical Score:** -100 to +100

### Confidence Formula
```
confidence = (tech_score * 0.40) + (news_sentiment * 0.20) + (historical_accuracy * 0.40)
```

Additional modifiers:
- `regime_boost`: +/- based on macro regime alignment
- `dynamic_asset_adj`: Per-asset historical accuracy adjustment
- `social_boost`: +/-10 points when social sentiment aligns with signal direction
- `geo_multiplier`: Reduces confidence during EXTREME geopolitical risk

### Signal Labels
| Label | Score Range | Action |
|-------|-----------|--------|
| STRONG BUY | > +60 | High conviction long |
| BUY | +20 to +60 | Moderate long |
| NEUTRAL | -20 to +20 | No action |
| SELL | -60 to -20 | Moderate short |
| STRONG SELL | < -60 | High conviction short |

### Asset Coverage (48 assets across 7 classes)
| Class | Count | Examples |
|-------|-------|---------|
| Stocks | 20 | AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, JPM, etc. |
| Crypto | 10 | BTC, ETH, SOL, XRP, DOGE, ADA, AVAX, LINK, DOT, LTC |
| Metals | 5 | Gold, Silver, Platinum, Copper, Palladium |
| Energy | 2 | Oil (CL=F), Natural Gas (NG=F) |
| Indices | 4 | S&P 500, NASDAQ, Dow Jones, Russell 2000 |
| Forex | 5 | EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF |
| Agriculture | 2 | Wheat (ZW=F), Corn (ZC=F) |

### Strengths
- Multi-factor scoring (technical + sentiment + social + historical)
- Self-grading predictions (48h validation loop via `market_learner.py`)
- Regime-aware (adjusts for risk-on/risk-off macro environments)
- Price sanity bounds (catches garbage yfinance data with 5-day median fallback)

### Weaknesses
- Rule-based only (no ML models yet)
- Limited to 4 technical indicators (no volume, order flow, VWAP, Ichimoku)
- No multi-timeframe confirmation (4H badge exists but not in scoring)
- yfinance data is delayed 15-20 minutes and unreliable

---

## 2. Auto-Trader: 12+ Gate Decision System (`auto_trader.py`)

The auto-trader is the crown jewel of Aegis — a multi-gate decision engine that evaluates whether to execute a paper trade. Every signal must pass ALL gates.

### Gate Architecture

| Gate | Name | Logic | Configurable |
|------|------|-------|-------------|
| 1 | **Confidence Threshold** | confidence >= MIN_CONFIDENCE_PCT (default 65%) | Yes (Settings) |
| 2 | **Signal Strength** | Signal must be in ALLOWED_SIGNALS list | Yes |
| 3 | **Risk Per Trade** | Position size <= MAX_POSITION_PCT of portfolio | Yes (default 20%) |
| 4 | **Portfolio Exposure** | Total invested <= max exposure limit | Yes |
| 5a | **Max Positions** | Open positions < MAX_CONCURRENT_POSITIONS (default 5) | Yes |
| 5b | **Asset Class Limit** | Not too many of same class | Yes |
| 5c | **Correlation Guard** | Max 3 correlated positions per group (metals, crypto, indices, energy) | Yes (default 3) |
| 6 | **Regime Filter** | Skip growth assets during risk-off if USE_REGIME_AWARENESS=True | Yes |
| 7 | **Drawdown Check** | -10% = 50% size reduction, -15% = FULL HALT (graduated) | Yes |
| 8 | **Geo-Risk Filter** | Reduce size during HIGH/EXTREME geopolitical risk | Yes |
| 9 | **Social Alignment** | Boost/penalize confidence based on social sentiment alignment | Yes |
| 10 | **Budget Check** | Daily trade count within budget limits | Yes |
| 11 | **Duplicate Check** | No existing open position in same asset | Automatic |
| 12 | **Cooldown Period** | Must wait COOLDOWN_HOURS since last trade in same asset (default 6h) | Yes |

### Position Sizing Methods
| Method | Logic | When Used |
|--------|-------|-----------|
| **Kelly Criterion** | Optimal fraction based on win rate + avg win/loss ratio | When 3+ wins and 1+ loss in history |
| **Fixed Fractional** | 2% of portfolio per trade | Fallback when insufficient history |

Size modifiers applied after base sizing:
```
final_size = base_size * regime_multiplier * geo_multiplier
```
- regime_mult: risk-on = 1.2x, risk-off = 0.5x
- geo_mult: extreme = 0.3x, high = 0.6x, elevated = 0.8x

### Assessment
- **Excellent**: Most sophisticated paper trading bot in the retail space — no competitor has 12+ risk gates
- **Good**: Graduated drawdown (not binary), regime-aware, correlation-aware
- **Missing**: No trailing stop automation, no partial profit-taking rules, no time-based exit (hold duration limits)

---

## 3. Risk Management System (`risk_manager.py` — ~545 lines)

### Current Capabilities
| Feature | Implementation | Status |
|---------|---------------|--------|
| Kelly Criterion Sizing | `calculate_kelly_size()` — requires 3+ wins, 1+ loss | Production |
| Fixed Fractional Sizing | 2% of portfolio per trade | Production |
| Correlation Matrix | 90-day Pearson correlation across all assets | Production |
| Correlation Heatmap | RdYlGn Plotly heatmap + insights | Production |
| VaR Calculation | Historical VaR at 95% confidence | Production |
| Exposure Tracking | By asset class + total portfolio | Production |
| Drawdown Monitoring | Graduated: -10% reduce, -15% halt | Production |
| Stop-Loss Management | Per-trade SL/TP with auto-calculation | Production |
| Risk Guardian Panel | 13-gate diagnostic display on Paper Trading page | Production |

### Gaps (What We Need for Top-10)
| Gap | Priority | Impact |
|-----|----------|--------|
| Real-time risk monitoring (streaming) | P0 | Can't react fast enough to flash crashes |
| Greeks calculation (for options) | P2 | Required before options trading |
| Stress testing / Monte Carlo VaR | P1 | Regulators expect this for institutional tier |
| Liquidity risk assessment | P1 | Thin markets can trap positions |
| Maximum adverse excursion (MAE) analysis | P2 | Optimize stop-loss placement |
| Risk parity portfolio construction | P2 | Alternative to mean-variance |

---

## 4. Paper Trading Engine (`paper_trader.py`)

### Current Capabilities
| Feature | Status |
|---------|--------|
| Long/Short execution | Production |
| Cash tracking | Production |
| Position sizing (auto) | Production |
| Stop-loss / Take-profit | Production |
| Partial close | Production |
| SL/TP adjustment | Production |
| Trade notes | Production |
| Trade journal export (CSV) | Production |
| P&L tracking (realized + unrealized) | Production |
| Portfolio equity curve | Production |

### What's Missing for Live Trading
| Requirement | Effort | Priority |
|------------|--------|----------|
| Broker API integration (Alpaca) | Large | P0 |
| Slippage modeling | Medium | P1 |
| Commission tracking | Small | P1 |
| Market/Limit/Stop order types | Medium | P1 |
| Order status tracking (filled/partial/rejected) | Medium | P0 |
| Execution logging with timestamps | Small | P1 |
| Multi-account support | Large | P2 |

---

## 5. Market Data Assessment

### Current Stack
| Source | Data | Latency | Reliability | Cost |
|--------|------|---------|------------|------|
| yfinance | OHLCV, fundamentals | 15-20min delayed | Low (frequent failures) | Free |
| RSS Feeds | News headlines | 5-30min | Medium | Free |
| Reddit JSON | Social sentiment | 1-5min | Medium (rate limited) | Free |

### Price Sanity System (`config.py`)
- `PRICE_SANITY_BOUNDS` defines min/max expected price per asset
- `_sanity_check_price()` in market_scanner.py validates all prices
- Falls back to 5-day median if current price is outside bounds
- Catches the "BTC at $64.97" type garbage data from yfinance

### Upgrade Path
| Phase | Provider | Cost | What It Unlocks |
|-------|----------|------|-----------------|
| Phase 1 | Twelve Data | $29/mo | Real-time WebSocket prices, 1-min bars |
| Phase 2 | Polygon.io | $199/mo | Institutional stocks + options + dark pool |
| Phase 3 | Binance WebSocket | Free | Real-time crypto (BTC, ETH, etc.) |
| Phase 4 | Direct exchange feeds | $500+/mo | Sub-second for institutional tier |

---

## 6. Roadmap to Live Trading

### Phase 1: Alpaca Paper Trading API (Month 1-2)
- Replace internal paper_trader.py with Alpaca paper trading
- Real order execution simulation with market/limit orders
- Slippage and commission modeling
- **Regulatory**: No license needed for paper trading
- **Team**: 2 backend engineers + 1 QA

### Phase 2: Alpaca Live Trading — Stocks + ETFs (Month 3-4)
- Small real-money positions ($100-1000 per trade)
- Commission tracking and tax lot management
- **Regulatory**: Publisher's exclusion (advisory, not broker-dealer)
- Disclaimers: "Not financial advice" on every signal
- **Team**: 3 engineers + 1 compliance + 1 QA

### Phase 3: Multi-Broker — Crypto (Month 5-8)
- Binance / Coinbase API integration for crypto
- Unified portfolio view across brokers
- Cross-asset risk management
- **Regulatory**: Crypto regulation varies by jurisdiction (MiCA in EU)
- **Team**: 4 engineers + 2 compliance + 2 QA

### Phase 4: Institutional Grade (Month 9-12)
- Interactive Brokers integration (options, futures)
- FIX protocol for institutional order routing
- Multi-strategy portfolio management
- White-label execution for enterprise clients
- **Regulatory**: May need RIA registration or partnership
- **Team**: 6 engineers + 3 compliance + 3 QA

---

## 7. Trading System KPIs

| Metric | Current | 6-Month Target | 12-Month Target |
|--------|---------|---------------|-----------------|
| Signal accuracy (48h validation) | ~55% est. | 65% | 75% |
| Average confidence score | ~50 | 60 | 70 |
| Paper trade win rate | ~45% est. | 55% | 60% |
| Risk-adjusted return (Sharpe) | Not measured | 1.0 | 1.5 |
| Max drawdown tolerance | -15% halt | -12% | -10% |
| Signal generation latency | ~130s (full scan) | <30s | <5s |
| Assets covered | 48 | 100 | 500+ |
| Auto-trader gate pass rate | ~15% est. | 25% | 35% |
| False positive (STRONG BUY → loss) | Not tracked | <20% | <12% |
| Prediction tracking coverage | 100% | 100% | 100% |

---

## 8. Competitive Position

### What Aegis Does That NO Competitor Has
1. **Self-grading predictions** — every signal validated at 48h, accuracy fed back into confidence
2. **12-gate risk system** — most bots have 2-3 gates max
3. **Regime-aware trading** — auto-adjusts for risk-on/off macro environments
4. **Transparent confidence** — users see exactly why a signal is BUY/SELL with AI explanation
5. **Graduated drawdown** — not binary stop, but intelligent size reduction

### What Competitors Have That We Need
1. **Real-time data** — TradingView/Bloomberg/Binance all sub-second
2. **Live trading** — eToro copy-trading, Robinhood instant execution
3. **Options/futures** — Thinkorswim, IBKR have full derivatives
4. **Backtesting** — TradingView Pine Script, QuantConnect (100+ years of data)
5. **Mobile** — Every competitor has native mobile apps

---

## 9. Investment Recommendations (VP Trading → CEO)

| Priority | Investment | Cost | Impact |
|----------|-----------|------|--------|
| **P0** | Twelve Data API (real-time) | $29/mo | Eliminates #1 user complaint (delayed data) |
| **P0** | Alpaca integration (paper + live) | Free | Enables real trading → monetization |
| **P1** | Add 6 more technical indicators | 2 eng-weeks | Better signal accuracy |
| **P1** | ML signal model (XGBoost baseline) | 4 eng-weeks | 10-15% accuracy improvement |
| **P2** | Options data (Polygon.io) | $199/mo | Unlocks advanced trader segment |
| **P2** | Multi-timeframe scoring | 3 eng-weeks | Higher conviction signals |
