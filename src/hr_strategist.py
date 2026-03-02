"""HR Strategist Agent — audits capabilities and proposes new sub-agents.

Analyzes the current system, identifies gaps, and writes structured
proposals for new agents to research_outputs/.

Usage:
    python hr_strategist.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = PROJECT_ROOT / "research_outputs"
KANBAN_PATH = PROJECT_ROOT / "kanban_board.json"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"

import sys
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from agents import AGENT_PROFILES


def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [HRStrategist] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Capability audit
# ---------------------------------------------------------------------------

CURRENT_CAPABILITIES = {
    "Price data fetching": {"status": "covered", "agents": ["Scanner"], "notes": "yfinance, 4 assets"},
    "Technical indicators": {"status": "covered", "agents": ["Scanner", "Analyst"], "notes": "SMA, RSI, MACD, BB"},
    "Signal scoring": {"status": "covered", "agents": ["Analyst"], "notes": "7-factor model, -100 to +100"},
    "Macro research": {"status": "covered", "agents": ["Researcher"], "notes": "Web search, Fed/inflation"},
    "Decision explanation": {"status": "covered", "agents": ["Reasoner"], "notes": "Plain-language Warum? section"},
    "Dashboard & UI": {"status": "covered", "agents": ["Designer"], "notes": "Streamlit Command Center"},
    "Budget monitoring": {"status": "covered", "agents": ["ChiefMonitor"], "notes": "Token tracking, cost guard"},
    "Error memory": {"status": "covered", "agents": ["Analyst"], "notes": "memory_manager.py"},
    "Backtesting": {"status": "covered", "agents": ["Coder"], "notes": "4 strategies on BTC, expandable"},
    "Sentiment analysis (social)": {"status": "gap", "agents": [], "notes": "No Twitter/Reddit/news sentiment"},
    "On-chain analytics": {"status": "gap", "agents": [], "notes": "No blockchain data (whale movements, exchange flows)"},
    "Portfolio management": {"status": "gap", "agents": [], "notes": "No position tracking or portfolio allocation"},
    "Alert delivery": {"status": "gap", "agents": [], "notes": "No push notifications (Telegram, email, Slack)"},
    "Correlation analysis": {"status": "gap", "agents": [], "notes": "No cross-asset correlation tracking"},
}

# ---------------------------------------------------------------------------
# Proposed new agents
# ---------------------------------------------------------------------------

PROPOSED_AGENTS = [
    {
        "name": "SentimentAnalyst",
        "display_name": "Social Sentiment Analyst",
        "icon": "💬",
        "priority": "high",
        "gap_addressed": "Sentiment analysis (social)",
        "role": "Monitors Twitter/X, Reddit, and news headlines for asset-specific sentiment shifts.",
        "system_prompt": (
            "You are the Sentiment Analyst. You monitor social media and news for "
            "sentiment shifts around Gold, BTC, ETH, and Silver. You produce a daily "
            "sentiment score (-1.0 to +1.0) per asset based on: "
            "1) Twitter/X volume and sentiment (via API or scraping). "
            "2) Reddit r/cryptocurrency and r/gold discussion tone. "
            "3) Major news headline sentiment (GDELT or NewsAPI). "
            "Output: sentiment_report.json with scores and top 5 headlines per asset."
        ),
        "required_apis": ["Twitter/X API or snscrape", "Reddit API (PRAW)", "NewsAPI or GDELT"],
        "estimated_cost_per_day": "$0.15 (mostly Haiku calls for classification)",
        "integration": "Feed sentiment scores into Scanner's signal scoring as factor #8.",
        "file_structure": [
            "src/sentiment_analyst.py — main agent logic",
            "src/data/sentiment_daily.json — daily sentiment data",
        ],
    },
    {
        "name": "OnChainTracker",
        "display_name": "On-Chain Analytics Tracker",
        "icon": "⛓️",
        "priority": "medium",
        "gap_addressed": "On-chain analytics",
        "role": "Tracks whale wallet movements, exchange inflows/outflows, and network metrics for BTC/ETH.",
        "system_prompt": (
            "You are the On-Chain Tracker. You monitor blockchain data for BTC and ETH: "
            "1) Large wallet movements (whale alerts). "
            "2) Exchange net flows (Glassnode or CryptoQuant). "
            "3) Network hash rate and active addresses. "
            "Produce alerts when whale movements exceed 1000 BTC or 10000 ETH. "
            "Output: onchain_report.json."
        ),
        "required_apis": ["Glassnode API or CryptoQuant", "Blockchain.com API (free tier)"],
        "estimated_cost_per_day": "$0.05 (data fetching only, minimal LLM use)",
        "integration": "Add on-chain signals to BTC/ETH scoring in Scanner.",
        "file_structure": [
            "src/onchain_tracker.py — main agent logic",
            "src/data/onchain_daily.json — daily blockchain metrics",
        ],
    },
    {
        "name": "PortfolioManager",
        "display_name": "Portfolio & Position Manager",
        "icon": "💼",
        "priority": "high",
        "gap_addressed": "Portfolio management",
        "role": "Tracks hypothetical positions, calculates portfolio allocation, and monitors P&L.",
        "system_prompt": (
            "You are the Portfolio Manager. You maintain a virtual portfolio: "
            "1) Track open positions (entry price, size, current P&L). "
            "2) Calculate optimal allocation using risk parity or Kelly criterion. "
            "3) Emit REBALANCE alerts when allocation drifts >5%% from target. "
            "4) Track overall portfolio Sharpe, max drawdown, and total return. "
            "Output: portfolio_state.json. Never execute real trades."
        ),
        "required_apis": ["None — uses existing price data from Scanner"],
        "estimated_cost_per_day": "$0.02 (mostly computation, minimal LLM)",
        "integration": "New dashboard tab 'Portfolio' showing positions and P&L chart.",
        "file_structure": [
            "src/portfolio_manager.py — position tracking and allocation",
            "src/data/portfolio_state.json — current positions",
            "dashboard/app.py — new Portfolio tab",
        ],
    },
    {
        "name": "AlertDispatcher",
        "display_name": "Alert Delivery Agent",
        "icon": "📨",
        "priority": "medium",
        "gap_addressed": "Alert delivery",
        "role": "Sends TRADE ALERT notifications via Telegram, email, or Slack.",
        "system_prompt": (
            "You are the Alert Dispatcher. When a new TRADE ALERT ticket appears in "
            "the kanban 'To Do' column, you send a notification with the signal summary "
            "and Execution Plan to the configured channels. Supported: Telegram bot, "
            "SMTP email, Slack webhook. Never send more than 5 alerts per hour to avoid spam."
        ),
        "required_apis": ["Telegram Bot API", "SMTP (Gmail/Outlook)", "Slack Webhooks"],
        "estimated_cost_per_day": "$0.00 (API calls only, no LLM needed)",
        "integration": "Hook into kanban_board.json watcher or scanner post-processing.",
        "file_structure": [
            "src/alert_dispatcher.py — notification logic",
            "config/alerts_config.json — channel settings and rate limits",
        ],
    },
]


def write_audit_report() -> Path:
    """Write the full capability audit and hiring proposals."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    filepath = RESEARCH_DIR / "HR_Strategy_Capability_Audit.md"

    lines = [
        "# HR Strategy: Capability Audit & Agent Proposals",
        "",
        f"**Generated:** {ts} UTC",
        f"**Analyst:** HR Strategist Agent",
        "",
        "---",
        "",
        "## Current Capability Matrix",
        "",
        "| Capability | Status | Covered By | Notes |",
        "|-----------|--------|-----------|-------|",
    ]

    for cap, info in CURRENT_CAPABILITIES.items():
        status_icon = "COVERED" if info["status"] == "covered" else "**GAP**"
        agents = ", ".join(info["agents"]) if info["agents"] else "—"
        lines.append(f"| {cap} | {status_icon} | {agents} | {info['notes']} |")

    lines += [
        "",
        "---",
        "",
        "## Current Agent Roster",
        "",
        "| Icon | Agent | Role | Cost Tier |",
        "|------|-------|------|-----------|",
    ]

    for name, profile in AGENT_PROFILES.items():
        lines.append(f"| {profile['icon']} | {profile['name']} | {profile['role']} | {profile['cost_tier']} |")

    lines += [
        "",
        f"**Total active agents:** {len(AGENT_PROFILES)}",
        "",
        "---",
        "",
        "## Identified Gaps & Proposed New Agents",
        "",
    ]

    for i, agent in enumerate(PROPOSED_AGENTS, 1):
        lines += [
            f"### {i}. {agent['icon']} {agent['display_name']} (`{agent['name']}`)",
            "",
            f"**Priority:** {agent['priority'].upper()}",
            f"**Gap addressed:** {agent['gap_addressed']}",
            f"**Role:** {agent['role']}",
            "",
            "**System Prompt:**",
            f"> {agent['system_prompt']}",
            "",
            f"**Required APIs:** {', '.join(agent['required_apis']) if isinstance(agent['required_apis'], list) else agent['required_apis']}",
            f"**Estimated daily cost:** {agent['estimated_cost_per_day']}",
            f"**Integration:** {agent['integration']}",
            "",
            "**Proposed file structure:**",
        ]
        for f in agent["file_structure"]:
            lines.append(f"- `{f}`")
        lines += ["", "---", ""]

    lines += [
        "## Hiring Priority Roadmap",
        "",
        "| Priority | Agent | Impact | Effort |",
        "|----------|-------|--------|--------|",
        "| 1 | Social Sentiment Analyst | High — adds sentiment factor to scoring | Medium (API setup) |",
        "| 2 | Portfolio Manager | High — enables position tracking and P&L | Low (no external APIs) |",
        "| 3 | Alert Dispatcher | Medium — enables mobile notifications | Low (webhook setup) |",
        "| 4 | On-Chain Tracker | Medium — adds blockchain intelligence for crypto | High (API costs) |",
        "",
        "---",
        "",
        "*This audit was generated by the HR Strategist Agent.*",
    ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


if __name__ == "__main__":
    log("Starting capability audit...")
    report_path = write_audit_report()
    log(f"Audit report written: {report_path.name}")
    log(f"Identified {sum(1 for v in CURRENT_CAPABILITIES.values() if v['status'] == 'gap')} capability gaps.")
    log(f"Proposed {len(PROPOSED_AGENTS)} new agents.")
    print(f"\nReport: {report_path}")
