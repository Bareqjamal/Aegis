"""Market Discovery Agent — scans broader markets for buy/sell opportunities.

Goes beyond the core watchlist (Gold, BTC, ETH, Silver) to scan
Oil, Natural Gas, S&P 500, NASDAQ, Copper, Platinum, and more.
Produces discovery reports with signals and recommendations.

Usage:
    python market_discovery.py                    # scan all discovery assets
    python market_discovery.py --asset Oil        # scan one asset
    python market_discovery.py --add-to-watchlist # promote signals to main watchlist
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = PROJECT_ROOT / "research_outputs"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
KANBAN_PATH = PROJECT_ROOT / "kanban_board.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from news_researcher import NewsResearcher
from chart_generator import ChartGenerator

RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Discovery Watchlist — assets beyond the core 4
# ---------------------------------------------------------------------------
DISCOVERY_ASSETS = {
    "Oil": {
        "ticker": "CL=F",
        "display": "Crude Oil (WTI)",
        "support": 60.00,
        "target": 85.00,
        "stop_pct": 0.05,
        "macro_bias": "neutral",
        "macro_reasons": [
            "OPEC+ production cuts supporting prices",
            "Global demand recovery uncertain",
            "US shale production at record levels",
            "Geopolitical risk premium from Middle East tensions",
        ],
        "category": "energy",
    },
    "NatGas": {
        "ticker": "NG=F",
        "display": "Natural Gas",
        "support": 2.50,
        "target": 5.00,
        "stop_pct": 0.08,
        "macro_bias": "neutral",
        "macro_reasons": [
            "LNG export demand growing globally",
            "Winter weather patterns driving short-term demand",
            "US production elevated, storage levels moderate",
            "European energy security concerns persist",
        ],
        "category": "energy",
    },
    "SP500": {
        "ticker": "^GSPC",
        "display": "S&P 500 Index",
        "support": 6200.00,
        "target": 7500.00,
        "stop_pct": 0.03,
        "macro_bias": "bullish",
        "macro_reasons": [
            "Fed rate cuts supporting equities",
            "Corporate earnings growth resilient",
            "AI/tech sector driving index gains",
            "Consumer spending remains strong",
        ],
        "category": "index",
    },
    "NASDAQ": {
        "ticker": "^IXIC",
        "display": "NASDAQ Composite",
        "support": 20000.00,
        "target": 26000.00,
        "stop_pct": 0.04,
        "macro_bias": "bullish",
        "macro_reasons": [
            "AI investment cycle accelerating",
            "Big tech earnings beating expectations",
            "Lower rates favor growth/tech stocks",
            "Digital transformation spending continues",
        ],
        "category": "index",
    },
    "Copper": {
        "ticker": "HG=F",
        "display": "Copper Futures",
        "support": 4.80,
        "target": 6.80,
        "stop_pct": 0.05,
        "macro_bias": "bullish",
        "macro_reasons": [
            "EV and renewable energy demand boosting copper",
            "Supply constraints from major mines",
            "China infrastructure stimulus",
            "Green transition requires massive copper tonnage",
        ],
        "category": "metal",
    },
    "Platinum": {
        "ticker": "PL=F",
        "display": "Platinum Futures",
        "support": 1800.00,
        "target": 2500.00,
        "stop_pct": 0.05,
        "macro_bias": "neutral",
        "macro_reasons": [
            "Hydrogen economy potential (fuel cells use platinum)",
            "Auto catalyst demand steady",
            "South African supply constraints",
            "Trading at deep discount to gold historically",
        ],
        "category": "metal",
    },
    "Wheat": {
        "ticker": "ZW=F",
        "display": "Wheat Futures",
        "support": 500.00,
        "target": 750.00,
        "stop_pct": 0.06,
        "macro_bias": "neutral",
        "macro_reasons": [
            "Black Sea export corridor uncertainty",
            "Global food inflation concerns",
            "Weather patterns affecting harvests",
            "Stockpile levels normalizing",
        ],
        "category": "agriculture",
    },
    "EUR_USD": {
        "ticker": "EURUSD=X",
        "display": "EUR/USD Forex",
        "support": 1.10,
        "target": 1.25,
        "stop_pct": 0.02,
        "macro_bias": "neutral",
        "macro_reasons": [
            "ECB and Fed rate differential narrowing",
            "Eurozone growth lagging US",
            "Dollar strength from safe-haven flows",
            "Trade policy uncertainty",
        ],
        "category": "forex",
    },
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [Discovery] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Technical analysis (reused from market_scanner pattern)
# ---------------------------------------------------------------------------

def analyze_asset(ticker: str, period: str = "1y") -> dict:
    """Fetch data and compute technical profile."""
    df = yf.download(ticker, period=period, interval="1d")
    if df.empty:
        raise ValueError(f"No data for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors="coerce")

    close = df["Close"]
    current = close.iloc[-1]

    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1]
    sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_val = macd_line.iloc[-1]
    macd_sig = signal_line.iloc[-1]

    # Bollinger Bands
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = (bb_sma + 2 * bb_std).iloc[-1]
    bb_lower = (bb_sma - 2 * bb_std).iloc[-1]

    # Volatility
    last_30 = df.tail(30)
    high_30 = last_30["High"].max()
    low_30 = last_30["Low"].min()
    vol_30 = (high_30 - low_30) / current * 100

    return {
        "current_price": round(float(current), 4),
        "sma_20": round(float(sma_20), 4),
        "sma_50": round(float(sma_50), 4),
        "sma_200": round(float(sma_200), 4) if sma_200 is not None else None,
        "rsi_14": round(float(rsi), 2),
        "macd": round(float(macd_val), 6),
        "macd_signal": round(float(macd_sig), 6),
        "macd_bullish": bool(macd_val > macd_sig),
        "bb_upper": round(float(bb_upper), 4),
        "bb_lower": round(float(bb_lower), 4),
        "high_30d": round(float(high_30), 4),
        "low_30d": round(float(low_30), 4),
        "volatility_30d_pct": round(float(vol_30), 1),
        "golden_cross": bool(sma_200 is not None and sma_50 > sma_200),
        "rows": len(df),
    }


# ---------------------------------------------------------------------------
# Signal scoring
# ---------------------------------------------------------------------------

def score_signal(name: str, tech: dict, config: dict) -> dict:
    """Score an asset from -100 to +100."""
    score = 0
    reasons = []

    price = tech["current_price"]
    support = config["support"]
    target = config["target"]

    # 1. Proximity to support
    distance = (price - support) / support if support > 0 else 1
    if distance <= 0.02:
        score += 25
        reasons.append(f"Price near support (within 2%)")
    elif distance <= 0.05:
        score += 15
        reasons.append(f"Price within 5% of support")
    elif distance <= 0.10:
        score += 5
        reasons.append(f"Price within 10% of support")

    # 2. Golden cross
    if tech["golden_cross"]:
        score += 20
        reasons.append("Golden Cross active (SMA-50 > SMA-200)")

    # 3. RSI
    rsi = tech["rsi_14"]
    if rsi < 30:
        score += 15
        reasons.append(f"RSI {rsi} — oversold")
    elif rsi < 45:
        score += 10
        reasons.append(f"RSI {rsi} — low, room for upside")
    elif rsi < 60:
        score += 5
        reasons.append(f"RSI {rsi} — neutral")
    elif rsi > 70:
        score -= 10
        reasons.append(f"RSI {rsi} — overbought")

    # 4. MACD
    if tech["macd_bullish"]:
        score += 10
        reasons.append("MACD above signal (bullish)")
    else:
        score -= 5
        reasons.append("MACD below signal (bearish)")

    # 5. Bollinger position
    if price <= tech["bb_lower"] * 1.01:
        score += 10
        reasons.append("Price near Bollinger lower band")
    elif price >= tech["bb_upper"] * 0.99:
        score -= 5
        reasons.append("Price near Bollinger upper band")

    # 6. Macro bias
    bias = config["macro_bias"]
    if bias == "bullish":
        score += 15
        reasons.append("Macro environment bullish")
    elif bias == "bearish":
        score -= 10
        reasons.append("Macro environment bearish")

    # 7. Risk/reward
    risk = price - (support * (1 - config["stop_pct"]))
    reward = target - price
    rr = reward / risk if risk > 0 else 0
    if rr >= 2:
        score += 5
        reasons.append(f"Risk/Reward {rr:.1f}:1")

    score = max(-100, min(100, score))

    if score >= 60:
        label = "STRONG BUY"
    elif score >= 35:
        label = "BUY"
    elif score >= -10:
        label = "NEUTRAL"
    elif score >= -35:
        label = "SELL"
    else:
        label = "STRONG SELL"

    stop_loss = round(support * (1 - config["stop_pct"]), 4)

    return {
        "score": score,
        "label": label,
        "reasons": reasons,
        "execution": {
            "entry": price,
            "target": config["target"],
            "stop_loss": stop_loss,
            "risk_reward": round(rr, 1),
        },
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_discovery_report(name: str, config: dict, tech: dict, signal: dict, news: dict | None = None) -> Path:
    """Write a discovery report to research_outputs/."""
    ex = signal["execution"]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    safe_name = name.replace("/", "_").replace(" ", "_")
    filename = f"{safe_name}_Signal_{signal['label'].replace(' ', '_')}.md"
    filepath = RESEARCH_DIR / filename

    lines = [
        f"# {signal['label']}: {config['display']} ({config['ticker']})",
        f"",
        f"**Generated:** {ts} UTC",
        f"**Signal Score:** {signal['score']}/100",
        f"**Signal Label:** {signal['label']}",
        f"**Category:** {config['category'].title()}",
        f"**Discovered by:** Market Discovery Agent",
    ]

    if news:
        lines.append(f"**News Sentiment:** {news['sentiment_label']} ({news['sentiment_score']:+.2f})")

    lines += [
        f"",
        f"---",
        f"",
        f"## Why this signal?",
        f"",
    ]
    for r in signal["reasons"]:
        lines.append(f"- {r}")

    # News section
    if news and (news.get("top_bullish") or news.get("top_bearish")):
        lines += [
            f"",
            f"---",
            f"",
            f"## Latest News",
            f"",
            f"**Sentiment:** {news['sentiment_label']} ({news['sentiment_score']:+.2f}) "
            f"from {news['relevant_count']} relevant articles",
            f"",
        ]
        if news.get("top_bullish"):
            lines.append("**Bullish:**")
            for art in news["top_bullish"]:
                link = art.get("link", "")
                title = art["title"]
                source = art.get("source", "")
                lines.append(f"- [{title}]({link}) — *{source}*" if link else f"- {title} — *{source}*")
            lines.append("")
        if news.get("top_bearish"):
            lines.append("**Bearish:**")
            for art in news["top_bearish"]:
                link = art.get("link", "")
                title = art["title"]
                source = art.get("source", "")
                lines.append(f"- [{title}]({link}) — *{source}*" if link else f"- {title} — *{source}*")
            lines.append("")

    lines += [
        f"",
        f"---",
        f"",
        f"## Execution Plan",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| **Entry** | ${ex['entry']:,.4f} |",
        f"| **Target** | ${ex['target']:,.4f} |",
        f"| **Stop-Loss** | ${ex['stop_loss']:,.4f} |",
        f"| **Risk/Reward** | {ex['risk_reward']}:1 |",
        f"",
        f"---",
        f"",
        f"## Technical Snapshot",
        f"",
        f"| Indicator | Value |",
        f"|-----------|-------|",
        f"| Current Price | ${tech['current_price']:,.4f} |",
        f"| SMA-20 | ${tech['sma_20']:,.4f} |",
        f"| SMA-50 | ${tech['sma_50']:,.4f} |",
    ]
    if tech["sma_200"]:
        lines.append(f"| SMA-200 | ${tech['sma_200']:,.4f} |")
    lines += [
        f"| RSI-14 | {tech['rsi_14']} |",
        f"| MACD | {tech['macd']} ({'above' if tech['macd_bullish'] else 'below'} signal) |",
        f"| Golden Cross | {'Yes' if tech['golden_cross'] else 'No'} |",
        f"| 30-Day Volatility | {tech['volatility_30d_pct']}% |",
        f"",
        f"---",
        f"",
        f"## Macro Context ({config['macro_bias'].upper()})",
        f"",
    ]
    for r in config["macro_reasons"]:
        lines.append(f"- {r}")

    lines += [
        f"",
        f"---",
        f"",
        f"*Discovered by Aegis Market Discovery Agent*",
    ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Scan loop
# ---------------------------------------------------------------------------

def discover_asset(name: str) -> dict:
    """Scan a single discovery asset."""
    config = DISCOVERY_ASSETS[name]
    log(f"Discovering {name} ({config['ticker']})...")

    try:
        tech = analyze_asset(config["ticker"])
    except Exception as e:
        log(f"ERROR fetching {name}: {e}")
        raise

    signal = score_signal(name, tech, config)
    log(f"{name}: {signal['label']} (score {signal['score']}) — Price ${tech['current_price']:,.4f}")

    # News research
    news_data = None
    try:
        researcher = NewsResearcher()
        news_data = researcher.research(name, config["ticker"])
        log(f"News for {name}: {news_data['sentiment_label']} ({news_data['sentiment_score']:+.2f})")
    except Exception as e:
        log(f"WARNING: News failed for {name}: {e}")

    # Chart generation
    try:
        chart_gen = ChartGenerator()
        figures = chart_gen.generate_all(
            ticker=config["ticker"],
            asset_name=name.lower(),
            config=config,
            signal=signal,
            news_data=news_data,
        )
        chart_dir = PROJECT_ROOT / "src" / "data" / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)
        for chart_name, fig in figures.items():
            fig.write_json(str(chart_dir / f"{name.lower()}_{chart_name}.json"))
        log(f"Charts for {name}: {len(figures)} generated")
    except Exception as e:
        log(f"WARNING: Charts failed for {name}: {e}")

    # Write report
    report_path = write_discovery_report(name, config, tech, signal, news=news_data)
    log(f"Discovery report: {report_path.name}")

    # Create kanban ticket for strong signals
    if signal["score"] >= 35:
        _create_discovery_alert(name, config, signal)

    return {"name": name, "signal": signal, "tech": tech, "news": news_data, "config": config}


def _create_discovery_alert(name: str, config: dict, signal: dict) -> None:
    """Create a discovery alert ticket in kanban."""
    ex = signal["execution"]
    title = f"DISCOVERY: {signal['label']} {config['display']} — Target ${ex['target']:,.2f}"

    with open(KANBAN_PATH, "r", encoding="utf-8") as f:
        board_data = json.load(f)

    # Check duplicates
    for tickets in board_data["board"].values():
        for t in tickets:
            if config["display"] in t["title"] and "DISCOVERY" in t["title"]:
                return

    all_ids = []
    for tickets in board_data["board"].values():
        for t in tickets:
            num = t["id"].replace("AEGIS-", "")
            if num.isdigit():
                all_ids.append(int(num))
    next_id = max(all_ids) + 1 if all_ids else 20

    ticket = {
        "id": f"AEGIS-{next_id:03d}",
        "title": title,
        "description": (
            f"Score: {signal['score']}/100 | "
            f"Entry: ${ex['entry']:,.4f} | Target: ${ex['target']:,.4f} | "
            f"Stop: ${ex['stop_loss']:,.4f} | R:R {ex['risk_reward']}:1 | "
            f"Category: {config['category']}"
        ),
        "priority": "medium",
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    board_data["board"]["To Do"].insert(0, ticket)

    with open(KANBAN_PATH, "w", encoding="utf-8") as f:
        json.dump(board_data, f, indent=2, ensure_ascii=False)
    log(f"DISCOVERY ALERT: {ticket['id']} — {name}")


def discover_all() -> list[dict]:
    """Scan all discovery assets."""
    log("=== Starting Market Discovery scan ===")
    results = []
    for name in DISCOVERY_ASSETS:
        try:
            result = discover_asset(name)
            results.append(result)
        except Exception:
            continue
    log(f"=== Discovery complete: {len(results)}/{len(DISCOVERY_ASSETS)} scanned ===")
    return results


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*90}")
    print(f"  MARKET DISCOVERY SUMMARY")
    print(f"{'='*90}")
    print(f"  {'Asset':<12} {'Category':<10} {'Price':>12} {'Signal':<14} {'Score':>6} {'Target':>12} {'R:R':>6}")
    print(f"  {'-'*80}")
    for r in results:
        s = r["signal"]
        ex = s["execution"]
        cat = r["config"]["category"]
        print(
            f"  {r['name']:<12} {cat:<10} ${r['tech']['current_price']:>10,.4f} "
            f"{s['label']:<14} {s['score']:>5} "
            f"${ex['target']:>10,.2f} {ex['risk_reward']:>4.1f}:1"
        )

    # Highlight opportunities
    buys = [r for r in results if r["signal"]["score"] >= 35]
    if buys:
        print(f"\n  OPPORTUNITIES FOUND ({len(buys)}):")
        for r in buys:
            print(f"    >> {r['name']}: {r['signal']['label']} (score {r['signal']['score']})")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Discovery Agent")
    parser.add_argument("--asset", default=None, help="Discover a single asset")
    args = parser.parse_args()

    if args.asset:
        if args.asset not in DISCOVERY_ASSETS:
            print(f"Unknown: '{args.asset}'. Available: {', '.join(DISCOVERY_ASSETS.keys())}")
            sys.exit(1)
        results = [discover_asset(args.asset)]
    else:
        results = discover_all()

    print_summary(results)
