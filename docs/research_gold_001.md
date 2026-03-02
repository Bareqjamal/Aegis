# Research Report: Gold (XAU/USD) — AEGIS-009

**Date:** 2026-02-08
**Analyst:** Project Aegis Researcher
**Ticker:** GC=F (Gold Futures)

---

## 1. Technical Analysis (from `market_researcher.py`)

| Metric | Value |
|--------|-------|
| Current Price | $4,979.80 |
| SMA-50 | $4,525.42 |
| SMA-200 | $3,809.16 |
| Trend Signal | **BULLISH** (Golden Cross — SMA-50 above SMA-200) |
| RSI-14 | 60.29 (neutral, trending toward overbought) |
| 30-Day High | $5,586.20 |
| 30-Day Low | $4,285.00 |
| 30-Day Range | $1,301.20 (26% swing — high volatility) |
| Data Points | 251 daily rows (1 year) |

**Key observation:** SMA-50 ($4,525) is significantly above SMA-200 ($3,809), a strong golden cross confirming a sustained uptrend. The spread of ~$716 between the two SMAs indicates strong momentum, not a fresh crossover. RSI at 60 is neutral — not yet overbought, leaving room for further upside.

---

## 2. Macro Environment

### Federal Reserve Policy

- The Fed held rates at **3.50–3.75%** at the January 2026 meeting.
- December 2025 projection suggested only **1 rate cut** of 25bps for all of 2026, but analysts expect **3–4 cuts** if recession risks mount.
- The Fed initiated short-term Treasury purchases in late 2025 — not officially QE, but a **liquidity tailwind** for gold.
- A **criminal probe into Federal Reserve operations** (reported by CNBC, Jan 2026) has fueled safe-haven demand and gold ETF inflows.

**Sources:**
- [Kitco: Gold jumps to $4,200 as Fed cuts rates](https://www.kitco.com/news/article/2025-12-10/gold-jumps-back-4200-fed-cuts-rates-provides-little-forward-guidance-2026)
- [CNBC: Gold smashes $4,600 record on Powell probe](https://www.cnbc.com/2026/01/12/gold-record-haven-powell-venezuela-iran.html)
- [SSGA: Gold 2026 Outlook — structural bull to $5,000](https://www.ssga.com/us/en/intermediary/insights/gold-2026-outlook-can-the-structural-bull-cycle-continue-to-5000)

### Inflation Impact

- Persistent inflation continues to erode fiat purchasing power, driving investors into gold as a store of value.
- Gold's 2025–2026 rally is attributed to: inflation persistence, prior underperformance, and skyrocketing global debt.
- Inflation expectations remain elevated, supporting gold even if rate cuts are delayed.

**Sources:**
- [World Gold Council: Gold Outlook 2026](https://www.gold.org/goldhub/research/gold-outlook-2026)
- [UBP: Gold's bull market continues into 2026](https://www.ubp.com/en/news-insights/newsroom/gold-s-bull-market-is-set-to-continue-into-2026-investment-outlook-2026)

---

## 3. Analyst Price Targets (2026)

| Institution | Target | Timeframe |
|-------------|--------|-----------|
| J.P. Morgan | $5,055–$6,300/oz | Q4 2026 |
| Goldman Sachs | $4,900/oz | End 2026 |
| RBC Capital Markets | $4,600 avg / $4,800 year-end | 2026 |
| TD Securities | $4,831 avg / $5,400 high | H1 2026 |

Consensus: **$4,800–$5,400 range** by year-end, with upside to $6,300 if macro deteriorates further.

---

## 4. Current Market Technicals (Feb 2026)

- Moving averages show **mixed signals** short-term: 6 buy / 6 sell across MA5–MA200.
- $4,405 is the key **pivotal support** (confluence of 50-day MA, ascending channel lower boundary, Fibonacci extension).
- Expected February trading range: **$4,700–$4,940** near-term, $4,915–$5,719 by month-end.
- MACD is currently **negative (-27.56)** — a short-term sell signal despite the longer-term bullish trend.
- Gold recently plunged 9% from highs before bouncing at the $4,405 inflection level.

**Sources:**
- [FXStreet: Gold forecast — will XAU/USD defend 21-day SMA](https://www.fxstreet.com/analysis/gold-price-forecast-will-xau-usd-defend-21-day-sma-on-a-daily-closing-basis-202602020313)
- [MarketPulse: Gold extends plunge approaching $4,405](https://www.marketpulse.com/markets/chart-alert-gold-extends-plunge-by-9-approaching-4405-inflection-level-for-potential-minor-bounce/)

---

## 5. Suggested Strategy

### Primary: Trend-Following with Pullback Entries

Given the strong golden cross and bullish macro backdrop, the recommended approach is:

1. **SMA Crossover (50/200) as the base signal** — remain long while SMA-50 > SMA-200.
2. **RSI pullback entries** — add to positions when RSI dips below 40 during the uptrend (buying the dip).
3. **Bollinger Band support** — use BB lower band touches as confirmation for pullback entries.
4. **Risk management** — stop-loss at $4,405 (key technical support / 50-day MA confluence).

### Why this combination:

- The macro environment (Fed liquidity, inflation, geopolitical uncertainty) is structurally bullish.
- The 9% recent pullback from highs provides a potential entry zone.
- RSI at 60 is not overbought — the trend has room to run.
- All major banks target prices above current levels.

### Risks:

- A hawkish Fed pivot (fewer cuts than expected) could trigger a correction.
- Dollar strength from global risk-off could pressure gold short-term.
- The 30-day range of $1,301 (26%) signals high volatility — position sizing must be conservative.

---

## 6. Next Steps

- [ ] Backtest SMA Crossover + RSI pullback combo on 1yr Gold data
- [ ] Add Gold to the Streamlit dashboard alongside BTC
- [ ] Monitor $4,405 support level — if breached, reassess thesis
- [ ] Track Fed meeting calendar for rate decision catalysts
