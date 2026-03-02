# Project Aegis - Architecture Log

## 2026-02-08: Project Initialization

**Decision:** Established initial project structure.

```
project-aegis/
  src/           # Core application code
  docs/          # Architecture decisions and documentation
  memory/        # Error lessons and memory manager
  dashboard/     # Streamlit UI
  kanban_board.json
```

**Rationale:**
- Flat top-level layout keeps things simple until complexity demands more.
- `kanban_board.json` at root so both dashboard and other scripts can reference it easily.
- `memory/` separated from `src/` because it contains data files alongside its manager script.

**Stack:** Python, Streamlit for dashboard.

## 2026-02-08: Bitcoin Strategy Research

**Decision:** Focus on 4 core strategies for BTC analysis, ranked by research findings.

| # | Strategy | Indicator(s) | Why |
|---|----------|-------------|-----|
| 1 | SMA Crossover (Golden/Death Cross) | SMA-50 / SMA-200 | Catches major trend shifts; well-documented on BTC |
| 2 | RSI Overbought/Oversold | RSI-14 | Mean reversion signal; RSI < 30 buy, RSI > 70 sell |
| 3 | MACD Crossover | MACD(12,26,9) | Momentum confirmation; >60% accuracy on BTC per research |
| 4 | Bollinger Band Mean Reversion | BB(20,2) + RSI | Combined mean reversion; Sharpe ~2.3 post-2021 |

**Key finding:** A 50/50 blend of momentum + mean reversion delivered Sharpe 1.71 and 56% annualized return across market regimes (QuantPedia).

**Rationale:**
- Start with simple, well-understood indicators before adding complexity.
- Use `yfinance` for free historical OHLCV data (no API key needed).
- Backtest each strategy independently, then test blended portfolio.
- All strategies are analysis/backtesting only — no live trading.

## 2026-02-08: Gold (XAU/USD) Research — AEGIS-009

**Decision:** Added Gold as second analysis target. Built `src/market_researcher.py` as a reusable, multi-asset research tool.

**Key findings:**
- Gold at $4,979.80 with a strong golden cross (SMA-50 $4,525 > SMA-200 $3,809).
- Macro environment structurally bullish: Fed holding rates, liquidity additions, persistent inflation, geopolitical safe-haven demand.
- Analyst consensus targets $4,800–$5,400 by year-end 2026, upside to $6,300 (JPM).
- Recent 9% pullback from highs creates potential entry zone; $4,405 is key support.

**Suggested strategy:** SMA Crossover trend-following with RSI pullback entries.

**Rationale:**
- `market_researcher.py` accepts `--symbol` and `--period` flags — reusable for any yfinance ticker.
- Applied yfinance CSV parsing lesson from error memory (skiprows for multi-level headers).
- Full report in `docs/research_gold_001.md`.

## 2026-02-08: Agent Research Command Center — AEGIS-010

**Decision:** Replaced the basic kanban dashboard with a full interactive Command Center.

**Features implemented:**
1. **Research Hub** — sidebar scans `research_outputs/` for `.md` files, sorted newest-first.
2. **Clickable Analyses** — click a file in the sidebar to render formatted markdown (tables, headings, links) in the main area.
3. **Interactive Kanban** — Done tickets are clickable buttons. Clicking searches `research_outputs/` for a file mentioning the ticket ID and navigates to it.
4. **Live Log Stream** — displays the last 50 lines of `agent_logs.txt` in a code block.
5. **Auto-Refresh** — page reruns every 5 seconds to pick up new files and log entries.

**Rationale:**
- No external dependencies beyond Streamlit (no watchdog needed — Streamlit's rerun loop handles refresh).
- `research_outputs/` is the canonical drop zone: any agent writes a `.md` there and it appears in the sidebar automatically.
- `agent_logs.txt` is a simple append-only text file — any process can write to it.
- Done ticket linking uses content search (grep for ticket ID) rather than a rigid naming convention.
