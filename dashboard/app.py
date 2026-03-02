"""Project Aegis — Agent Research Command Center v5.0 (Bloomberg Edition).

Dark-themed trading terminal with: Watchlist Overview, Signal Cards,
Research Hub (charts + news), Kanban, System Evolution, Agent Performance,
Budget, Agent Monitor, and Live Logs.
"""

import html
import importlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------------------------
# Paths & imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KANBAN_PATH = PROJECT_ROOT / "kanban_board.json"
RESEARCH_DIR = PROJECT_ROOT / "research_outputs"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
USAGE_FILE = PROJECT_ROOT / "token_usage.json"
CHART_DIR = PROJECT_ROOT / "src" / "data" / "charts"
NEWS_DIR = PROJECT_ROOT / "src" / "data"
WATCHLIST_FILE = PROJECT_ROOT / "src" / "data" / "watchlist_summary.json"
PREDICTIONS_FILE = PROJECT_ROOT / "memory" / "market_predictions.json"
MARKET_LESSONS_FILE = PROJECT_ROOT / "memory" / "market_lessons.json"
HINDSIGHT_FILE = PROJECT_ROOT / "memory" / "hindsight_simulations.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "memory"))
from auth_manager import auth_manager, TIERS, PRO_VIEWS
from data_store import data_store
from token_manager import TokenManager
from chief_monitor import ChiefMonitor
from agents import AGENT_PROFILES
import paper_trader
import chart_engine
import risk_manager
import performance_analytics
import alert_manager
import fundamentals
import sector_analysis
import strategy_builder
import hyperopt_engine
import geopolitical_monitor
import macro_regime as macro_regime_mod
import economic_calendar as econ_cal_mod
import morning_brief as morning_brief_mod
import prediction_game as prediction_game_mod
from news_researcher import NewsResearcher, RSS_FEEDS, ASSET_FEED_MAP, ASSET_KEYWORDS
import portfolio_optimizer
from watchlist_manager import WatchlistManager
import report_generator
import signal_explainer
import config as _config_mod
from i18n import t, language_selector, get_rtl_css, is_rtl, LANGUAGES

# Import config classes and auth (no reload — modules are stable between reruns)
from config import SignalConfig, RiskConfig, AutoTradeConfig, DashboardConfig, TechnicalParams
import auth_manager as _auth_mod
from auth_manager import auth_manager, TIERS, PRO_VIEWS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# -- Design System Colors (match landing page Tailwind config) ----------------
_C = {
    "green": "#3fb950", "blue": "#58a6ff", "red": "#f85149",
    "yellow": "#d29922", "purple": "#bc8cff", "muted": "#6e7681",
}
COLUMN_COLORS = {"Backlog": _C["muted"], "To Do": _C["blue"], "In Progress": _C["yellow"], "Done": _C["green"]}
PRIORITY_COLORS = {"high": _C["red"], "medium": _C["yellow"], "low": _C["green"]}
SIGNAL_STYLES = {
    "STRONG BUY": {"color": "#fff", "bg": "#2ea043", "glow": "rgba(63,185,80,0.5)"},
    "BUY":        {"color": "#fff", "bg": _C["green"], "glow": "rgba(63,185,80,0.4)"},
    "NEUTRAL":    {"color": "#fff", "bg": _C["muted"], "glow": "rgba(110,118,129,0.3)"},
    "SELL":       {"color": "#fff", "bg": _C["yellow"], "glow": "rgba(210,153,34,0.5)"},
    "STRONG SELL":{"color": "#fff", "bg": _C["red"], "glow": "rgba(248,81,73,0.5)"},
}
HEALTH_COLORS = {"HEALTHY": _C["green"], "DEGRADED": _C["yellow"], "UNHEALTHY": _C["red"]}
CONF_COLORS = {"HIGH": _C["green"], "MEDIUM": _C["yellow"], "LOW": _C["red"], "VERY LOW": _C["muted"]}

# ---------------------------------------------------------------------------
# Legal Disclaimers (required for SaaS launch)
# ---------------------------------------------------------------------------
DISCLAIMER_SHORT = (
    "Aegis provides AI-generated market research for informational purposes only. "
    "Not investment advice. Past performance does not guarantee future results. "
    "Trading involves substantial risk of loss."
)
DISCLAIMER_SIGNAL = (
    "AI-generated signal based on technical indicators, sentiment analysis, and "
    "historical patterns. Not a personal recommendation. Signals can be wrong."
)
DISCLAIMER_PAPER = (
    "Paper trading results are simulated and do not reflect actual trading. "
    "No representation is made that any account will achieve similar results."
)

# ---------------------------------------------------------------------------
# Dark trading terminal CSS (UI/UX Designer Agent v5)
# ---------------------------------------------------------------------------
TERMINAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    /* ── Base ───────────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(145deg, #080b12 0%, #0d1117 40%, #0f1923 100%);
        color: #c9d1d9;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #131a24 100%);
        border-right: 1px solid rgba(48, 54, 61, 0.6);
    }

    /* ── Typography ────────────────────────────────────────── */
    h1, h2, h3 {
        color: #e6edf3 !important;
        font-family: 'Inter', -apple-system, sans-serif;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    h1 {
        font-size: 1.6rem !important;
        border-bottom: 1px solid rgba(88, 166, 255, 0.15);
        padding-bottom: 10px;
        margin-bottom: 20px !important;
    }
    h2 { font-size: 1.3rem !important; }
    h3 {
        font-size: 1.05rem !important;
        color: #8b949e !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
    }
    p, li, span, label, .stMarkdown { color: #c9d1d9; }

    /* ── Metric Cards ──────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.95) 100%);
        border: 1px solid rgba(48, 54, 61, 0.5);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.03);
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(88, 166, 255, 0.3);
        box-shadow: 0 4px 20px rgba(88, 166, 255, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }
    [data-testid="stMetricValue"] {
        color: #58a6ff;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #6e7681;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 500;
    }

    /* ── Tables / DataFrames ───────────────────────────────── */
    .stDataFrame {
        border: 1px solid rgba(48, 54, 61, 0.5);
        border-radius: 12px;
        overflow: hidden;
    }

    /* ── Code blocks ───────────────────────────────────────── */
    code, pre {
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 0.8em;
    }

    /* ── Sidebar ───────────────────────────────────────────── */
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #58a6ff !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem !important;
        letter-spacing: 0.15em;
    }
    section[data-testid="stSidebar"] button {
        border: 1px solid rgba(48, 54, 61, 0.3) !important;
        background: rgba(22, 27, 34, 0.5) !important;
        color: #c9d1d9 !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        padding: 6px 12px !important;
        margin-bottom: 2px !important;
        transition: all 0.25s ease !important;
        text-align: left !important;
    }
    section[data-testid="stSidebar"] button:hover {
        border-color: rgba(88, 166, 255, 0.5) !important;
        background: rgba(88, 166, 255, 0.08) !important;
        color: #e6edf3 !important;
        box-shadow: 0 0 12px rgba(88, 166, 255, 0.1) !important;
    }

    /* ── Sidebar section headers ──────────────────────────── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 4px 0;
        margin: 2px 0;
    }
    .section-header .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .section-header .label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7em;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #6e7681;
    }

    /* ── Info boxes ────────────────────────────────────────── */
    .page-info-box {
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.06) 0%, rgba(22, 27, 34, 0.8) 100%);
        border: 1px solid rgba(88, 166, 255, 0.15);
        border-left: 3px solid #58a6ff;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
        font-size: 0.88em;
        color: #8b949e;
        line-height: 1.55;
    }
    .page-info-box strong { color: #c9d1d9; }
    .page-info-box .info-title {
        color: #58a6ff;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78em;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
        display: block;
    }

    /* ── Geopolitical event cards ──────────────────────────── */
    .geo-event-card {
        background: linear-gradient(145deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.9) 100%);
        border: 1px solid rgba(48, 54, 61, 0.5);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    .geo-event-card:hover {
        border-color: rgba(88, 166, 255, 0.3);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .geo-event-card .event-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.68em;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.05em;
        margin-right: 6px;
    }

    /* ── Dividers ──────────────────────────────────────────── */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(48, 54, 61, 0.6), transparent) !important;
        margin: 16px 0 !important;
    }

    /* ── Signal Badges ─────────────────────────────────────── */
    .signal-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.7em;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    .signal-badge-glow-green {
        box-shadow: 0 0 12px rgba(25, 135, 84, 0.4), 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    .signal-badge-glow-red {
        box-shadow: 0 0 12px rgba(220, 53, 69, 0.4), 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    /* ── Signal Trading Cards ─────────────────────────────── */
    .signal-card {
        background: linear-gradient(145deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.9) 100%);
        border: 1px solid rgba(48, 54, 61, 0.5);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 12px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .signal-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }
    .signal-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 14px 14px 0 0;
    }
    .signal-card-buy::before { background: linear-gradient(90deg, #2ea043, #3fb950); }
    .signal-card-sell::before { background: linear-gradient(90deg, #da3633, #f85149); }
    .signal-card-neutral::before { background: linear-gradient(90deg, #484f58, #6e7681); }
    .signal-card .card-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8em;
        font-weight: 700;
        color: #e6edf3;
        line-height: 1.2;
    }
    .signal-card .card-asset {
        font-family: 'Inter', sans-serif;
        font-size: 0.85em;
        color: #8b949e;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .signal-card .card-reasoning {
        font-size: 0.8em;
        color: #8b949e;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid rgba(48, 54, 61, 0.3);
        font-style: italic;
    }
    .signal-card .card-meta {
        display: flex;
        justify-content: space-between;
        margin-top: 8px;
        font-size: 0.72em;
        color: #8b949e;
        font-family: 'JetBrains Mono', monospace;
    }
    .conf-bar {
        height: 6px;
        border-radius: 3px;
        background: rgba(48, 54, 61, 0.3);
        margin-top: 10px;
        overflow: hidden;
    }
    .conf-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    /* ── News Impact / "Why Is It Moving?" ────────────────── */
    .impact-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.65em;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-left: 6px;
    }
    .impact-tailwind { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.3); }
    .impact-headwind { background: rgba(218, 54, 51, 0.15); color: #f85149; border: 1px solid rgba(218, 54, 51, 0.3); }
    .impact-neutral  { background: rgba(110, 118, 129, 0.15); color: #8b949e; border: 1px solid rgba(110, 118, 129, 0.3); }
    .chain-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 61, 0.5);
        font-size: 0.68em;
        color: #c9d1d9;
        margin: 2px 3px 2px 0;
        font-family: 'Inter', sans-serif;
    }
    .chain-pill-bull { border-color: rgba(46, 160, 67, 0.3); color: #3fb950; }
    .chain-pill-bear { border-color: rgba(218, 54, 51, 0.3); color: #f85149; }

    /* ── Watchlist Table ──────────────────────────────────── */
    .watchlist-row {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid rgba(48, 54, 61, 0.3);
        border-radius: 10px;
        margin-bottom: 6px;
        transition: all 0.2s ease;
    }
    .watchlist-row:hover {
        border-color: rgba(88, 166, 255, 0.3);
        background: rgba(22, 27, 34, 0.8);
    }

    /* ── Agent Health Cards ────────────────────────────────── */
    .agent-card {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.9) 100%);
        border: 1px solid rgba(48, 54, 61, 0.4);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
    }
    .agent-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 12px 12px 0 0;
    }
    .agent-card:hover {
        border-color: rgba(88, 166, 255, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    .agent-card-healthy::before { background: linear-gradient(90deg, #2ea043, #3fb950); }
    .agent-card-degraded::before { background: linear-gradient(90deg, #9e6a03, #d29922); }
    .agent-card-unhealthy::before { background: linear-gradient(90deg, #da3633, #f85149); }
    .agent-card .agent-icon { font-size: 1.8em; margin-bottom: 6px; display: block; }
    .agent-card .agent-name { color: #e6edf3; font-weight: 600; font-size: 0.9em; }
    .agent-card .agent-role { color: #6e7681; font-size: 0.75em; line-height: 1.4; margin: 4px 0 8px 0; }
    .agent-card .agent-meta {
        color: #8b949e; font-size: 0.7em; font-family: 'JetBrains Mono', monospace;
        margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(48, 54, 61, 0.3);
    }

    /* ── Kanban Cards ──────────────────────────────────────── */
    .kanban-column-header {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem; font-weight: 700; letter-spacing: 0.06em;
        padding: 8px 0 12px 0; border-bottom: 2px solid; margin-bottom: 12px;
    }
    .kanban-ticket {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(17, 22, 30, 0.95) 100%);
        border: 1px solid rgba(48, 54, 61, 0.4); border-radius: 10px;
        padding: 12px 14px; margin-bottom: 8px; transition: all 0.2s ease;
    }
    .kanban-ticket:hover { border-color: rgba(88, 166, 255, 0.3); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); }
    .kanban-ticket .ticket-id { color: #58a6ff; font-family: 'JetBrains Mono', monospace; font-size: 0.72em; font-weight: 700; }
    .kanban-ticket .ticket-title { color: #c9d1d9; font-size: 0.82em; font-weight: 500; margin-top: 4px; }
    .kanban-ticket .ticket-desc { color: #8b949e; font-size: 0.72em; margin-top: 4px; line-height: 1.4; }

    .trade-alert-card {
        background: linear-gradient(135deg, rgba(13, 40, 24, 0.5) 0%, rgba(13, 17, 23, 0.9) 100%);
        border: 1px solid rgba(25, 135, 84, 0.3); border-left: 3px solid #3fb950;
        padding: 12px 14px; border-radius: 10px; margin-bottom: 8px;
        color: #c9d1d9; transition: all 0.2s ease;
    }
    .trade-alert-card:hover { border-color: rgba(63, 185, 80, 0.5); box-shadow: 0 0 16px rgba(63, 185, 80, 0.1); }
    .trade-alert-card .ticket-id { color: #3fb950; font-family: 'JetBrains Mono', monospace; font-size: 0.72em; font-weight: 700; }
    .trade-alert-card .ticket-title { color: #c9d1d9; font-size: 0.82em; font-weight: 500; margin-top: 2px; }

    /* ── Status Banner ─────────────────────────────────────── */
    .status-banner {
        padding: 12px 20px; border-radius: 10px; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
        text-align: center; margin-bottom: 20px; letter-spacing: 0.08em;
    }
    .status-allclear {
        background: linear-gradient(135deg, rgba(13, 40, 24, 0.6) 0%, rgba(13, 17, 23, 0.8) 100%);
        color: #3fb950; border: 1px solid rgba(35, 134, 54, 0.4);
    }
    .status-warning {
        background: linear-gradient(135deg, rgba(45, 27, 0, 0.6) 0%, rgba(13, 17, 23, 0.8) 100%);
        color: #d29922; border: 1px solid rgba(158, 106, 3, 0.4);
    }
    .status-critical {
        background: linear-gradient(135deg, rgba(61, 0, 0, 0.6) 0%, rgba(13, 17, 23, 0.8) 100%);
        color: #f85149; border: 1px solid rgba(218, 54, 51, 0.4);
        animation: pulse-red 2s ease-in-out infinite;
    }
    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 20px rgba(248, 81, 73, 0.08); }
        50% { box-shadow: 0 0 30px rgba(248, 81, 73, 0.15); }
    }

    /* ── Progress Bars ─────────────────────────────────────── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #1a7f37, #3fb950) !important;
        border-radius: 6px;
    }
    .stProgress { background: rgba(48, 54, 61, 0.3); border-radius: 6px; }

    /* ── Scrollbar ─────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(48, 54, 61, 0.6); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(88, 166, 255, 0.3); }

    /* ── Logo / Branding ───────────────────────────────────── */
    .aegis-logo {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem; font-weight: 700; color: #58a6ff;
        letter-spacing: 0.2em; text-align: center; padding: 12px 0;
        border-bottom: 1px solid rgba(48, 54, 61, 0.3); margin-bottom: 12px;
        text-shadow: 0 0 20px rgba(88, 166, 255, 0.3);
    }
    .aegis-logo .logo-sub {
        display: block; font-size: 0.55em; color: #8b949e;
        letter-spacing: 0.1em; font-weight: 400; margin-top: 2px;
    }

    /* ── Section headers ───────────────────────────────────── */
    .section-header {
        display: flex; align-items: center; gap: 8px; margin: 20px 0 12px 0;
    }
    .section-header .dot {
        width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    }
    .section-header .label {
        font-family: 'Inter', sans-serif; font-size: 0.8rem; font-weight: 600;
        color: #8b949e; text-transform: uppercase; letter-spacing: 0.06em;
    }

    /* ── Evolution/Performance cards ──────────────────────── */
    .lesson-card {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid rgba(48, 54, 61, 0.4);
        border-left: 3px solid #58a6ff;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 8px;
        font-size: 0.82em;
    }
    .reflection-card {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.8) 0%, rgba(18, 24, 38, 0.9) 100%);
        border: 1px solid rgba(88, 166, 255, 0.2);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }

    /* ── Bloomberg Density ──────────────────────────────── */
    .stApp .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
    }
    /* Tighter Streamlit element spacing */
    .stRadio > div { gap: 0.3rem !important; }
    .stRadio > div > label {
        padding: 4px 12px !important;
        font-size: 0.78rem !important;
        border-radius: 16px !important;
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        color: #8b949e !important;
        transition: all 0.2s !important;
    }
    .stRadio > div > label[data-checked="true"],
    .stRadio > div > label:has(input:checked) {
        background: rgba(88,166,255,0.12) !important;
        border-color: #58a6ff !important;
        color: #58a6ff !important;
        font-weight: 600 !important;
    }
    /* Hide radio circles — tabs look like pills */
    .stRadio > div > label > div:first-child { display: none !important; }
    /* Tighter vertical spacing */
    .stMarkdown { margin-bottom: -4px !important; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.4rem !important; }
    /* Category tab active state glow */
    .stRadio > div > label:hover {
        border-color: rgba(88,166,255,0.4) !important;
        color: #e6edf3 !important;
    }

    /* ── Mobile responsive — Tablet (768px) ──────────────── */
    @media (max-width: 768px) {
        /* Stack columns vertically */
        [data-testid="column"] { min-width: 100% !important; }
        .stApp .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }

        /* Signal cards: compact layout */
        .signal-card { padding: 14px !important; margin-bottom: 10px !important; }
        .signal-card .card-price { font-size: 1.3em !important; }
        .signal-card .card-meta { flex-direction: column !important; gap: 4px !important; }
        .signal-card .card-reasoning { font-size: 0.78em !important; }

        /* Watchlist rows: tighter */
        .watchlist-row { padding: 10px 12px !important; flex-wrap: wrap !important; gap: 6px !important; }

        /* Section headers */
        .section-header { flex-direction: row !important; gap: 6px !important; }

        /* Info boxes */
        .page-info-box { padding: 12px 14px !important; font-size: 0.85em !important; }

        /* Pill tabs: wrap on small screens */
        .stRadio > div { flex-wrap: wrap !important; gap: 4px !important; }

        /* Kanban: tighter */
        .kanban-ticket { padding: 10px 12px !important; }

        /* Agent cards: smaller */
        .agent-card { padding: 12px !important; }
        .agent-card .agent-icon { font-size: 1.4em !important; }

        /* Metrics: smaller */
        [data-testid="stMetric"] { padding: 12px 14px !important; }
        [data-testid="stMetricValue"] { font-size: 1.1rem !important; }

        /* Touch targets: minimum 44px for accessibility */
        section[data-testid="stSidebar"] button {
            min-height: 44px !important;
            padding: 10px 12px !important;
            font-size: 0.82rem !important;
        }
        button, a, [role="button"] { min-height: 44px !important; }

        /* Tables: horizontal scroll */
        .stDataFrame { overflow-x: auto !important; -webkit-overflow-scrolling: touch !important; }
    }

    /* ── Mobile responsive — Phone (480px) ─────────────── */
    @media (max-width: 480px) {
        .stApp .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }

        /* Signal cards: ultra-compact */
        .signal-card { padding: 10px !important; margin: 4px 0 !important; border-radius: 10px !important; }
        .signal-card .card-price { font-size: 1.1em !important; }
        .signal-card .card-asset { font-size: 0.78em !important; }
        .signal-card .card-meta span { font-size: 0.68em !important; }
        .signal-card .card-reasoning { font-size: 0.75em !important; }
        .signal-card:hover { transform: none !important; }

        /* Typography: slightly smaller */
        h1 { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 0.9rem !important; }

        /* Pill tabs: smaller */
        .stRadio > div > label { padding: 3px 8px !important; font-size: 0.72rem !important; }

        /* Section headers */
        .section-header .label { font-size: 0.72em !important; }

        /* Watchlist rows: stack vertically */
        .watchlist-row { flex-direction: column !important; align-items: flex-start !important; gap: 4px !important; padding: 8px 10px !important; }

        /* Sidebar logo: compact */
        .aegis-logo { font-size: 0.95rem !important; padding: 8px 0 !important; }
        .aegis-logo .logo-sub { font-size: 0.5em !important; }

        /* Geo event cards: compact */
        .geo-event-card { padding: 12px 14px !important; }

        /* Status banner: compact */
        .status-banner { padding: 8px 14px !important; font-size: 0.78rem !important; }
    }
</style>
"""

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_board() -> dict:
    if not KANBAN_PATH.exists():
        return {}
    with open(KANBAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("board", {})

def list_research_files() -> list[Path]:
    if not RESEARCH_DIR.exists():
        return []
    return sorted(RESEARCH_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

def read_file(path: Path) -> str:
    """Read a file and escape $ signs to prevent LaTeX interpretation."""
    content = path.read_text(encoding="utf-8")
    # Streamlit interprets $...$ as LaTeX math — escape dollar signs in non-LaTeX context
    # Preserve real LaTeX by only escaping $ followed by digits (i.e. prices like $6.01)
    import re
    content = re.sub(r'\$(\d)', r'\\$\1', content)
    return content

def detect_signal_label(path: Path) -> str | None:
    name = path.stem.upper()
    for label in SIGNAL_STYLES:
        if label.replace(" ", "_") in name:
            return label
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines()[:15]:
            m = re.search(r"\*\*Signal Label:\*\*\s*(STRONG BUY|BUY|NEUTRAL|SELL|STRONG SELL)", line)
            if m:
                return m.group(1)
            if line.startswith("# "):
                for label in SIGNAL_STYLES:
                    if label in line.upper():
                        return label
    except Exception:
        pass
    return None

def read_log_tail(n: int = 50) -> str:
    if not LOG_FILE.exists():
        return "_No log file found._"
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n:])

def find_report_for_ticket(ticket_id: str) -> Path | None:
    for f in list_research_files():
        if ticket_id in f.read_text(encoding="utf-8"):
            return f
    return None

def find_report_for_trade_alert(title: str) -> Path | None:
    m = re.search(r"Buy (\w+)", title)
    if not m:
        return None
    asset = m.group(1)
    for f in list_research_files():
        if asset.lower() in f.name.lower():
            return f
    return None


KNOWN_SIGNAL_ASSETS = {
    "gold": "gold", "btc": "btc", "eth": "eth", "silver": "silver",
    "oil": "oil", "natgas": "natgas", "sp500": "sp500", "nasdaq": "nasdaq",
    "copper": "copper", "platinum": "platinum", "wheat": "wheat", "eur_usd": "eur_usd",
}

def detect_asset_from_filename(path: Path) -> str | None:
    name = path.stem.lower()
    if "_signal_" not in name:
        return None
    for key, asset in KNOWN_SIGNAL_ASSETS.items():
        if key in name:
            return asset
    return None


def load_chart(asset: str, chart_type: str) -> go.Figure | None:
    chart_path = CHART_DIR / f"{asset}_{chart_type}.json"
    if not chart_path.exists():
        return None
    try:
        return pio.from_json(chart_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_news(asset: str) -> dict | None:
    news_path = NEWS_DIR / f"news_{asset}.json"
    if not news_path.exists():
        return None
    try:
        return json.loads(news_path.read_text(encoding="utf-8"))
    except Exception:
        return None


USER_WATCHLIST_FILE = PROJECT_ROOT / "src" / "data" / "user_watchlist.json"


def _load_raw_watchlist_summary() -> dict:
    """Load the raw watchlist_summary.json (scanner output)."""
    if not WATCHLIST_FILE.exists():
        return {}
    try:
        return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


_watchlist_cache = {"data": None, "ts": 0}

def load_watchlist_summary() -> dict:
    """Load watchlist data for ALL configured assets.

    Merges scanned data from watchlist_summary.json with user_watchlist.json.
    Assets that haven't been scanned yet get a placeholder entry with NEUTRAL signal.
    Cached for 10 seconds to prevent repeated file reads on page switches.
    """
    import time as _time_mod
    now = _time_mod.time()
    if _watchlist_cache["data"] is not None and (now - _watchlist_cache["ts"]) < 10:
        return _watchlist_cache["data"]

    scanned = _load_raw_watchlist_summary()
    user_wl = {}
    if USER_WATCHLIST_FILE.exists():
        try:
            user_wl = json.loads(USER_WATCHLIST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    merged = dict(scanned)  # Start with scanned data

    # Add placeholder entries for configured assets that haven't been scanned
    for name, cfg in user_wl.items():
        if not cfg.get("enabled", True):
            continue
        if name not in merged:
            merged[name] = {
                "name": name,
                "ticker": cfg.get("ticker", ""),
                "price": 0,
                "signal_label": "NEUTRAL",
                "signal_score": 0,
                "confidence": {"confidence_pct": 0, "level": "VERY LOW"},
                "rsi": 0,
                "news_sentiment": "PENDING",
                "backtest_rate": None,
                "backtest_signals": None,
                "report_mode": "pending_scan",
                "reasoning_short": "Awaiting first scan — run the scanner to get signals for this asset.",
                "category": cfg.get("category", ""),
                "support": cfg.get("support", 0),
                "target": cfg.get("target", 0),
                "_needs_scan": True,
            }

    _watchlist_cache["data"] = merged
    _watchlist_cache["ts"] = now
    return merged


def load_user_watchlist() -> dict:
    """Load the user-configurable watchlist (all assets)."""
    if not USER_WATCHLIST_FILE.exists():
        return {}
    try:
        return json.loads(USER_WATCHLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_user_watchlist(watchlist: dict) -> None:
    """Save updated user watchlist to disk."""
    USER_WATCHLIST_FILE.write_text(
        json.dumps(watchlist, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def generate_sparkline_svg(ticker: str, width: int = 120, height: int = 30) -> str:
    """Generate a tiny SVG sparkline for a ticker's 30-day price history.

    Returns an inline SVG string, or empty string on failure.
    """
    import yfinance as yf
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if df.empty or len(df) < 3:
            return ""
        prices = df["Close"].dropna().tolist()
        if not prices:
            return ""
        # Handle MultiIndex columns from yfinance
        if hasattr(prices[0], '__iter__'):
            prices = [float(p) for p in prices]
        else:
            prices = [float(p) for p in prices]
        min_p = min(prices)
        max_p = max(prices)
        rng = max_p - min_p if max_p > min_p else 1
        # Normalize to SVG coordinates
        n = len(prices)
        points = []
        for i, p in enumerate(prices):
            x = round(i / (n - 1) * width, 1)
            y = round(height - (p - min_p) / rng * height, 1)
            points.append(f"{x},{y}")
        polyline = " ".join(points)
        # Color: green if up, red if down
        color = "#3fb950" if prices[-1] >= prices[0] else "#f85149"
        svg = (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
            f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        return svg
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_correlation_data(ticker_str: str, names_str: str) -> dict:
    """Fetch 30-day prices for correlation analysis. Cached 5 minutes."""
    import yfinance as yf
    tickers = ticker_str.split(" ")
    names = names_str.split("|")
    try:
        df = yf.download(ticker_str, period="30d", interval="1d", progress=False)
        if df.empty:
            return {}
        result = {}
        for name, tick in zip(names, tickers):
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    col_data = df["Close"][tick].dropna().tolist()
                else:
                    col_data = df["Close"].dropna().tolist()
                if len(col_data) >= 5:
                    result[name] = col_data
            except (KeyError, TypeError):
                pass
        return result
    except Exception:
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_correlation_data_90d() -> dict:
    """Fetch 90 days of daily close prices for all 12 watchlist assets.

    Uses ThreadPoolExecutor with 15s timeout (same pattern as rest of codebase).
    Returns {friendly_name: [close_prices]} dict.
    Cached 10 minutes.
    """
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    # All 12 watchlist assets: ticker -> friendly name
    _CORR_ASSETS = {
        "GC=F": "Gold",
        "BTC-USD": "BTC",
        "ETH-USD": "ETH",
        "SI=F": "Silver",
        "CL=F": "Oil",
        "NG=F": "Nat Gas",
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "HG=F": "Copper",
        "PL=F": "Platinum",
        "ZW=F": "Wheat",
        "EURUSD=X": "EUR/USD",
    }

    def _do_download():
        ticker_str = " ".join(_CORR_ASSETS.keys())
        return yf.download(ticker_str, period="90d", interval="1d", progress=False)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_download)
            df = future.result(timeout=15)

        if df is None or df.empty:
            return {}

        # Build aligned DataFrame — do NOT dropna per-ticker (causes unequal lengths)
        result = {}
        for ticker, name in _CORR_ASSETS.items():
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    col_data = df["Close"][ticker]
                else:
                    col_data = df["Close"]
                result[name] = col_data
            except (KeyError, TypeError):
                pass

        if len(result) < 2:
            return {}

        # Align all series by index, then drop rows with any NaN
        aligned = pd.DataFrame(result).dropna()
        # Convert to dict of lists (all same length now)
        return {col: aligned[col].tolist() for col in aligned.columns if len(aligned[col]) >= 10}
    except (FuturesTimeoutError, Exception):
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_benchmark_returns() -> dict:
    """Fetch 30-day benchmark returns. Cached 5 minutes."""
    import yfinance as yf
    benchmarks = {}
    for name, ticker in [("S&P 500", "^GSPC"), ("Bitcoin", "BTC-USD")]:
        try:
            df = yf.download(ticker, period="30d", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                closes = df["Close"].iloc[:, 0].dropna()
            else:
                closes = df["Close"].dropna()
            if len(closes) >= 2:
                benchmarks[name] = round(float(closes.iloc[-1] / closes.iloc[0] - 1) * 100, 2)
        except Exception:
            pass
    return benchmarks


@st.cache_data(ttl=600)
def get_sparklines_batch(tickers: list[str]) -> dict[str, str]:
    """Batch-generate sparkline SVGs for a list of tickers. Cached 10 min."""
    result = {}
    import yfinance as yf
    if not tickers:
        return result
    try:
        ticker_str = " ".join(tickers)
        df = yf.download(ticker_str, period="1mo", interval="1d", progress=False)
        if df.empty:
            return result
        width, height = 120, 30
        for tick in tickers:
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    prices = df["Close"][tick].dropna().tolist()
                else:
                    prices = df["Close"].dropna().tolist()
                if len(prices) < 3:
                    continue
                prices = [float(p) for p in prices]
                min_p = min(prices)
                max_p = max(prices)
                rng = max_p - min_p if max_p > min_p else 1
                n = len(prices)
                points = []
                for i, p in enumerate(prices):
                    x = round(i / (n - 1) * width, 1)
                    y = round(height - (p - min_p) / rng * height, 1)
                    points.append(f"{x},{y}")
                polyline = " ".join(points)
                color = "#3fb950" if prices[-1] >= prices[0] else "#f85149"
                svg = (
                    f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
                    f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
                    f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</svg>'
                )
                result[tick] = svg
            except Exception:
                continue
    except Exception:
        pass
    return result


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_live_prices_cached(ticker_str: str, ticker_names: str) -> dict:
    """Internal cached price fetch. Keyed by ticker string for cache.

    Cached for 60 seconds to prevent yfinance spam on page switches.
    Uses individual Ticker().history() calls (one per ticker) to avoid
    the batch yf.download() cross-contamination bug. Fetches sequentially
    with a short timeout to keep the page responsive.
    """
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    tickers_map = dict(zip(ticker_names.split("|"), ticker_str.split(" ")))

    def _fetch_one(name_tick):
        name, tick = name_tick
        try:
            df = yf.Ticker(tick).history(period="5d", interval="1d")
            closes = df["Close"].dropna() if not df.empty else pd.Series(dtype=float)
            if len(closes) >= 1:
                price = float(closes.iloc[-1])
                # Calculate real daily change from yfinance data (not from stale scan)
                daily_pct = 0.0
                if len(closes) >= 2:
                    prev = float(closes.iloc[-2])
                    if prev > 0:
                        daily_pct = round((price - prev) / prev * 100, 2)
                return name, round(price, 2), daily_pct
        except Exception:
            pass
        return name, None, 0.0

    try:
        prices = {}
        daily_changes = {}
        # Fetch each ticker individually to prevent cross-contamination.
        # Use a single worker to serialize calls (yfinance is not thread-safe).
        with ThreadPoolExecutor(max_workers=1) as executor:
            def _fetch_all():
                result_p = {}
                result_c = {}
                for n, t in tickers_map.items():
                    nm, pr, chg = _fetch_one((n, t))
                    if pr is not None:
                        result_p[nm] = pr
                        result_c[nm] = chg
                return result_p, result_c
            future = executor.submit(_fetch_all)
            prices, daily_changes = future.result(timeout=45)
        # Stash daily changes in session state so the advisor can use them
        import streamlit as _st_mod
        _st_mod.session_state["_live_daily_changes"] = daily_changes
        return prices
    except (FuturesTimeout, Exception):
        return {}


_PRICE_CACHE_FILE = PROJECT_ROOT / "src" / "data" / "price_cache.json"


def _save_price_cache(prices: dict) -> None:
    """Persist last known good prices to disk for fallback."""
    try:
        cache = {"prices": prices, "timestamp": datetime.now(timezone.utc).isoformat()}
        _PRICE_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except OSError:
        pass


def _load_price_cache() -> dict:
    """Load cached prices from disk (max 24h old)."""
    if not _PRICE_CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(_PRICE_CACHE_FILE.read_text(encoding="utf-8"))
        ts = data.get("timestamp", "")
        cache_time = datetime.fromisoformat(ts)
        age = (datetime.now(timezone.utc) - cache_time).total_seconds()
        if age < 86400:  # 24 hours
            return data.get("prices", {})
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        pass
    return {}


def fetch_live_prices(watchlist: dict) -> dict:
    """Fetch current prices for all watchlist assets from yfinance.

    Returns {asset_name: live_price} dict. Cached 60s. Falls back to:
    1. Disk price cache (last known good prices, max 24h old)
    2. Prices from watchlist_summary.json scan data
    """
    tickers = {name: data.get("ticker", "") for name, data in watchlist.items() if data.get("ticker")}
    if not tickers:
        return {}
    ticker_str = " ".join(tickers.values())
    ticker_names = "|".join(tickers.keys())
    live = _fetch_live_prices_cached(ticker_str, ticker_names)

    # Save good prices to disk cache for future fallback
    if live and len(live) >= len(tickers) * 0.5:
        _save_price_cache(live)

    if live:
        return live

    # Fallback 1: disk price cache (last known good prices)
    cached = _load_price_cache()
    if cached:
        return cached

    # Fallback 2: prices from watchlist scan data
    fallback = {}
    for name, data in watchlist.items():
        p = data.get("price", 0)
        if p and p > 0:
            fallback[name] = p
    return fallback


def load_predictions() -> dict:
    if not PREDICTIONS_FILE.exists():
        return {"predictions": [], "stats": {"total": 0, "validated": 0, "correct": 0}}
    try:
        return json.loads(PREDICTIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"predictions": [], "stats": {}}


def load_market_lessons() -> dict:
    if not MARKET_LESSONS_FILE.exists():
        return {"lessons": [], "rules": []}
    try:
        return json.loads(MARKET_LESSONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"lessons": [], "rules": []}


def load_hindsight() -> dict:
    if not HINDSIGHT_FILE.exists():
        return {"simulations": [], "stats": {"total": 0, "correct": 0, "incorrect": 0, "neutral": 0, "accuracy": 0}}
    try:
        return json.loads(HINDSIGHT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"simulations": [], "stats": {}}


def extract_report_meta(path: Path) -> dict:
    meta = {"score": None, "label": None, "news_sentiment": None, "news_score": None, "confidence": None}
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines()[:25]:
            m = re.search(r"\*\*Signal Score:\*\*\s*(-?\d+)/100", line)
            if m:
                meta["score"] = int(m.group(1))
            m = re.search(r"\*\*Signal Label:\*\*\s*(STRONG BUY|BUY|NEUTRAL|SELL|STRONG SELL)", line)
            if m:
                meta["label"] = m.group(1)
            m = re.search(r"\*\*News Sentiment:\*\*\s*(\w+)\s*\(([\+\-]?[\d\.]+)\)", line)
            if m:
                meta["news_sentiment"] = m.group(1)
                meta["news_score"] = float(m.group(2))
            m = re.search(r"\*\*Confidence:\*\*\s*([\d\.]+)%\s*\((\w+(?:\s+\w+)?)\)", line)
            if m:
                meta["confidence"] = float(m.group(1))
                meta["confidence_level"] = m.group(2)
    except Exception:
        pass
    return meta

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def badge_html(text: str, bg: str, color: str = "#fff", glow: str = "") -> str:
    cls = f"signal-badge {glow}".strip()
    return f"<span class='{cls}' style='background:{bg};color:{color};'>{text}</span>"

def signal_badge_html(label: str) -> str:
    s = SIGNAL_STYLES.get(label)
    if not s:
        return ""
    glow = ""
    if "BUY" in label:
        glow = "signal-badge-glow-green"
    elif "SELL" in label:
        glow = "signal-badge-glow-red"
    return badge_html(label, s["bg"], s["color"], glow)

def mode_badge_html(mode: str) -> str:
    if mode == "deep_research":
        return badge_html("DEEP RESEARCH", "#6f42c1")
    return badge_html("FAST SCAN", "#3fb950")

def health_badge(health: str) -> str:
    c = HEALTH_COLORS.get(health, "#6c757d")
    return badge_html(health, c)

def status_banner_html(status: str) -> str:
    cls = {"ALL CLEAR": "status-allclear", "WARNING": "status-warning", "CRITICAL": "status-critical"}
    return f"<div class='status-banner {cls.get(status, 'status-warning')}'>{status}</div>"


def signal_card_html(data: dict) -> str:
    """Generate a Bloomberg-style trading signal card with execution plan."""
    label = data.get("signal_label", "NEUTRAL")
    style = SIGNAL_STYLES.get(label, SIGNAL_STYLES["NEUTRAL"])
    price = data.get("price", 0)
    name = data.get("name", "???")
    ticker = data.get("ticker", "")
    conf = data.get("confidence", {})
    conf_pct = conf.get("confidence_pct", 0) if isinstance(conf, dict) else 0
    conf_level = conf.get("level", "LOW") if isinstance(conf, dict) else "LOW"
    conf_color = CONF_COLORS.get(conf_level, "#6e7681")
    reasoning = data.get("reasoning_short", "")
    backtest = data.get("backtest_rate")
    bt_signals = data.get("backtest_signals", 0)
    rsi = data.get("rsi", 0)
    news_sent = data.get("news_sentiment", "N/A")
    score = data.get("signal_score", 0)
    report_mode = data.get("report_mode", "standard")

    # Execution plan
    target = data.get("target")
    stop_loss = data.get("stop_loss")
    entry = data.get("entry")
    rr = data.get("risk_reward")

    card_class = "signal-card-buy" if "BUY" in label else ("signal-card-sell" if "SELL" in label else "signal-card-neutral")

    # Backtest display: show % only if there were actual signals
    if backtest is not None and bt_signals > 0:
        bt_str = f"BT: {backtest}% ({bt_signals} trades)"
    elif bt_signals == 0 and backtest is not None:
        bt_str = "BT: no signals"
    else:
        bt_str = ""

    high_prob_badge = ""
    if backtest is not None and backtest > 60 and bt_signals > 0:
        high_prob_badge = (
            "<div style='margin-top:6px;'>"
            "<span style='background:linear-gradient(90deg,#238636,#3fb950);color:#fff;"
            "padding:3px 10px;border-radius:4px;font-family:JetBrains Mono,monospace;"
            "font-size:0.65em;font-weight:700;letter-spacing:0.06em;"
            "box-shadow:0 0 12px rgba(63,185,80,0.3);'>HIGH PROBABILITY</span></div>"
        )
    mode_icon = {"deep_dive": "&#9733;&#9733;&#9733;", "standard": "&#9733;&#9733;", "brief": "&#9733;"}.get(report_mode, "")

    # Execution plan row (target / stop-loss / R:R)
    exec_row = ""
    if target is not None and stop_loss is not None and entry is not None:
        target_color = "#3fb950"
        stop_color = "#f85149"
        rr_str = f"{rr}:1" if rr else ""
        exec_row = (
            f"<div style='display:flex;justify-content:space-between;margin-top:10px;padding-top:10px;"
            f"border-top:1px solid rgba(48,54,61,0.3);font-family:JetBrains Mono,monospace;font-size:0.72em;'>"
            f"<span style='color:#8b949e;'>Entry: <b style=\"color:#e6edf3;\">${entry:,.2f}</b></span>"
            f"<span style='color:{target_color};'>Target: <b>${target:,.2f}</b></span>"
            f"<span style='color:{stop_color};'>Stop: <b>${stop_loss:,.2f}</b></span>"
            f"<span style='color:#58a6ff;'>R:R <b>{rr_str}</b></span>"
            f"</div>"
        )

    # Build as compact single-line HTML — Streamlit's markdown parser breaks
    # multi-line indented HTML by treating indented lines as code blocks.
    parts = [
        f"<div class='signal-card {card_class}'>",
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>",
        f"<div>",
        f"<span class='card-asset'>{name} <span style='color:#8b949e;'>{ticker}</span></span>",
        f"<div class='card-price'>${price:,.2f}</div>",
        f"</div>",
        f"<div style='text-align:right;'>",
        f"<span class='signal-badge' style='background:{style['bg']};color:{style['color']};"
        f"box-shadow:0 0 14px {style['glow']};font-size:0.85em;padding:6px 14px;'>{label}</span>",
        f"<div style='margin-top:8px;font-family:JetBrains Mono,monospace;font-size:0.75em;color:#8b949e;'>Score: {score}/100</div>",
        high_prob_badge,
        f"</div>",
        f"</div>",
        f"<div style='margin-top:12px;'>",
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>",
        f"<span style='font-family:JetBrains Mono,monospace;font-size:0.8em;color:{conf_color};font-weight:700;'>Confidence: {conf_pct}%</span>",
        f"<span style='font-size:0.7em;color:#8b949e;'>{conf_level} {mode_icon}</span>",
        f"</div>",
        f"<div class='conf-bar'><div class='conf-bar-fill' style='width:{conf_pct}%;background:{conf_color};'></div></div>",
        f"</div>",
        exec_row,
        f"<div class='card-reasoning'>{reasoning}</div>",
        f"<div class='card-meta'>",
        f"<span>RSI: {rsi}</span>",
        f"<span>News: {news_sent}</span>",
        f"<span>{bt_str}</span>",
        f"</div>",
        f"</div>",
    ]
    return "".join(parts)


# ===========================================================================
# PAGE CONFIG
# ===========================================================================
st.set_page_config(page_title="Aegis Terminal", page_icon="< />", layout="wide", initial_sidebar_state="expanded")
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)

# ===========================================================================
# AUTHENTICATION GATE
# ===========================================================================
def _render_auth_page():
    """Render login/register page with product showcase."""
    # ── HERO SECTION ──
    st.markdown(
        "<div style='text-align:center;padding:30px 0 10px 0;'>"
        "<div style='font-size:2.8rem;font-weight:800;color:#58a6ff;"
        "font-family:JetBrains Mono,monospace;letter-spacing:0.06em;"
        "text-shadow:0 0 40px rgba(88,166,255,0.3);'>AEGIS</div>"
        "<div style='color:#e6edf3;font-size:1.1em;font-family:Inter,sans-serif;"
        "font-weight:500;margin-top:4px;'>AI-Powered Trading Intelligence</div>"
        "<div style='color:#8b949e;font-size:0.82em;margin-top:6px;'>"
        "48 assets &middot; Self-learning signals &middot; Autonomous trading bot</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── FEATURE HIGHLIGHTS (3 columns) ──
    st.markdown(
        "<div style='display:flex;gap:12px;margin:16px 0 20px 0;flex-wrap:wrap;justify-content:center;'>"
        # Feature 1
        "<div style='background:#161b22;border:1px solid rgba(63,185,80,0.3);border-radius:10px;"
        "padding:14px 16px;flex:1;min-width:180px;max-width:280px;'>"
        "<div style='font-size:1.4em;margin-bottom:6px;'>🎯</div>"
        "<div style='color:#3fb950;font-weight:700;font-size:0.82em;margin-bottom:4px;'>"
        "Self-Grading Signals</div>"
        "<div style='color:#8b949e;font-size:0.72em;line-height:1.4;'>"
        "Tracks every prediction. Shows when it was right AND wrong. No other tool does this.</div></div>"
        # Feature 2
        "<div style='background:#161b22;border:1px solid rgba(88,166,255,0.3);border-radius:10px;"
        "padding:14px 16px;flex:1;min-width:180px;max-width:280px;'>"
        "<div style='font-size:1.4em;margin-bottom:6px;'>🤖</div>"
        "<div style='color:#58a6ff;font-weight:700;font-size:0.82em;margin-bottom:4px;'>"
        "12-Gate Trading Bot</div>"
        "<div style='color:#8b949e;font-size:0.72em;line-height:1.4;'>"
        "Regime-aware, geo-risk-aware autonomous bot with institutional drawdown management.</div></div>"
        # Feature 3
        "<div style='background:#161b22;border:1px solid rgba(210,153,34,0.3);border-radius:10px;"
        "padding:14px 16px;flex:1;min-width:180px;max-width:280px;'>"
        "<div style='font-size:1.4em;margin-bottom:6px;'>📊</div>"
        "<div style='color:#d29922;font-weight:700;font-size:0.82em;margin-bottom:4px;'>"
        "Stocks, Crypto, Forex</div>"
        "<div style='color:#8b949e;font-size:0.72em;line-height:1.4;'>"
        "AAPL, NVDA, BTC, ETH, SOL, Gold, EUR/USD and 40+ more assets in one terminal.</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── LIVE STATS BAR ──
    st.markdown(
        "<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;"
        "padding:8px 16px;margin-bottom:20px;display:flex;justify-content:center;"
        "gap:24px;flex-wrap:wrap;'>"
        "<span style='color:#3fb950;font-family:JetBrains Mono,monospace;font-size:0.75em;'>"
        "48 Assets</span>"
        "<span style='color:#58a6ff;font-family:JetBrains Mono,monospace;font-size:0.75em;'>"
        "5 Indicators</span>"
        "<span style='color:#d29922;font-family:JetBrains Mono,monospace;font-size:0.75em;'>"
        "Auto Paper Trading</span>"
        "<span style='color:#bc8cff;font-family:JetBrains Mono,monospace;font-size:0.75em;'>"
        "100% Free</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── AUTH FORM (centered, narrower) ──
    _auth_spacer_l, _auth_center, _auth_spacer_r = st.columns([1, 2, 1])
    with _auth_center:
        _auth_tab_login, _auth_tab_register = st.tabs(["Sign In", "Create Account"])
        with _auth_tab_login:
            with st.form("login_form"):
                _login_email = st.text_input("Email", key="login_email_input")
                _login_pw = st.text_input("Password", type="password", key="login_pw_input")
                _remember_me = st.checkbox("Stay logged in", value=True, key="remember_me_cb")
                _login_submit = st.form_submit_button("Sign In", use_container_width=True)
            if _login_submit and _login_email and _login_pw:
                result = auth_manager.login(_login_email, _login_pw)
                if isinstance(result, dict):
                    st.session_state["user"] = result
                    st.session_state["user_id"] = result["user_id"]
                    if _remember_me:
                        try:
                            _token = auth_manager.create_session(result["user_id"])
                            st.session_state["session_token"] = _token
                            auth_manager.save_active_session(_token)
                        except Exception:
                            pass
                    st.rerun()
                else:
                    st.error(result)
        with _auth_tab_register:
            with st.form("register_form"):
                _reg_name = st.text_input("Name", key="reg_name_input")
                _reg_email = st.text_input("Email", key="reg_email_input")
                _reg_pw = st.text_input("Password (6+ chars)", type="password", key="reg_pw_input")
                _reg_pw2 = st.text_input("Confirm Password", type="password", key="reg_pw2_input")
                _reg_submit = st.form_submit_button("Create Account", use_container_width=True)
            if _reg_submit:
                if _reg_pw != _reg_pw2:
                    st.error("Passwords don't match.")
                elif _reg_email and _reg_pw:
                    result = auth_manager.register(_reg_email, _reg_pw, _reg_name)
                    if isinstance(result, dict):
                        st.session_state["user"] = result
                        st.session_state["user_id"] = result["user_id"]
                        st.session_state["pending_verification"] = True
                        try:
                            _token = auth_manager.create_session(result["user_id"])
                            st.session_state["session_token"] = _token
                            auth_manager.save_active_session(_token)
                        except Exception:
                            pass
                        st.success("Account created! Check your email for a verification code.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(result)

        # Guest mode
        st.markdown("<div style='text-align:center;padding:8px 0;'>"
                    "<span style='color:#484f58;font-size:0.72em;'>or try it instantly</span></div>",
                    unsafe_allow_html=True)
        if st.button("Continue as Guest — No signup required", use_container_width=True, key="guest_btn"):
            st.session_state["user"] = {
                "user_id": "default", "name": "Guest", "email": "",
                "tier": "free", "disclaimer_accepted": True, "onboarding_complete": True,
            }
            st.session_state["user_id"] = "default"
            st.rerun()

    # ── BOTTOM: What users say ──
    st.markdown(
        "<div style='text-align:center;padding:20px 0 8px 0;'>"
        "<div style='color:#8b949e;font-size:0.72em;font-style:italic;max-width:500px;"
        "margin:0 auto;line-height:1.5;'>"
        "\"The prediction report card is unlike anything else. "
        "No trading tool openly shows when it was wrong.\"</div>"
        "<div style='color:#484f58;font-size:0.62em;margin-top:4px;'>— Pro Trader Feedback</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='text-align:center;padding:12px 0;'>"
        f"<span style='color:#21262d;font-size:0.55em;font-family:Inter,sans-serif;'>"
        f"{DISCLAIMER_SHORT}</span></div>",
        unsafe_allow_html=True,
    )

# Check if user is authenticated — try saved session file first (remember-me)
if "user" not in st.session_state:
    try:
        _restored = auth_manager.load_active_session()
        if _restored:
            _restored_token = _restored.pop("_session_token", "")
            st.session_state["user"] = _restored
            st.session_state["user_id"] = _restored["user_id"]
            if _restored_token:
                st.session_state["session_token"] = _restored_token
    except Exception:
        pass  # Session restore unavailable — fall through to login
    if "user" not in st.session_state:
        _render_auth_page()
        st.stop()

# User is authenticated — get their info
_current_user = st.session_state["user"]
_current_user_id = st.session_state.get("user_id", "default")
_current_tier = _current_user.get("tier", "free")
_tier_config = auth_manager.get_tier_config(_current_tier)

# Route paper_trader to the authenticated user's portfolio file
paper_trader.set_user(_current_user_id)

# Check trial expiry
if _current_user_id != "default":
    auth_manager.check_trial_expiry(_current_user_id)
    # Reload in case tier changed
    _fresh_profile = data_store.get_profile(_current_user_id)
    if _fresh_profile:
        _current_user = _fresh_profile
        _current_tier = _current_user.get("tier", "free")
        _tier_config = auth_manager.get_tier_config(_current_tier)
        st.session_state["user"] = _current_user

# ===========================================================================
# EMAIL VERIFICATION (optional — shown after registration, skippable)
# ===========================================================================
if (
    st.session_state.get("pending_verification")
    and _current_user_id != "default"
    and not _current_user.get("email_verified", False)
):
    st.markdown(
        "<div style='text-align:center;padding:40px 0 20px 0;'>"
        "<span style='font-size:2rem;'>📧</span><br>"
        "<span style='font-size:1.4rem;font-weight:600;color:#e6edf3;'>"
        "Verify Your Email</span><br>"
        f"<span style='color:#8b949e;font-size:0.85em;'>We sent a 6-digit code to "
        f"<strong style=\"color:#58a6ff;\">{_current_user.get('email', '')}</strong></span>"
        "</div>",
        unsafe_allow_html=True,
    )
    _vc1, _vc2, _vc3 = st.columns([1, 2, 1])
    with _vc2:
        with st.form("verify_form"):
            _verify_code = st.text_input(
                "Verification Code", max_chars=6, placeholder="123456",
                key="verify_code_input",
            )
            _verify_submit = st.form_submit_button("Verify", use_container_width=True)
        if _verify_submit and _verify_code:
            vr = auth_manager.verify_email(_current_user_id, _verify_code)
            if isinstance(vr, dict):
                st.session_state["user"] = vr
                st.session_state.pop("pending_verification", None)
                st.success("Email verified!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(vr)
        _resend_col, _skip_col = st.columns(2)
        with _resend_col:
            if st.button("Resend Code", key="resend_verify_btn", use_container_width=True):
                auth_manager.resend_verification(_current_user_id)
                st.success("New code sent!")
        with _skip_col:
            if st.button("Skip for Now", key="skip_verify_btn", use_container_width=True):
                st.session_state.pop("pending_verification", None)
                st.rerun()
    st.stop()

# ===========================================================================
# DISCLAIMER ACCEPTANCE (first login only)
# ===========================================================================
if not _current_user.get("disclaimer_accepted", False) and _current_user_id != "default":
    st.markdown(
        "<div style='text-align:center;padding:40px 0 20px 0;'>"
        "<span style='font-size:1.8rem;font-weight:700;color:#58a6ff;'>Welcome to Aegis</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("### Important Disclaimer")
    st.warning(
        "**Please read and accept before continuing:**\n\n"
        "1. Aegis provides AI-generated market research for **informational purposes only**.\n"
        "2. Nothing on this platform constitutes investment advice.\n"
        "3. All trading is **paper (simulated)** — no real money is at risk.\n"
        "4. AI signals can be wrong. Past performance does not guarantee future results.\n"
        "5. You should consult a licensed financial advisor before making real investment decisions.\n\n"
        "*Aegis operates under the publisher's exclusion (Investment Advisers Act 1940).*"
    )
    _accept_col1, _accept_col2 = st.columns([3, 1])
    with _accept_col1:
        _accepted = st.checkbox("I understand and accept these terms", key="disclaimer_check")
    with _accept_col2:
        if st.button("Continue", key="disclaimer_accept_btn", disabled=not _accepted):
            auth_manager.accept_disclaimer(_current_user_id)
            st.session_state["user"]["disclaimer_accepted"] = True
            st.rerun()
    st.stop()

# Auto-refresh: Only for truly live-data pages (logs, monitor).
# Other pages use manual refresh buttons or st.fragment for partial updates.
_current_view = st.session_state.get("view", "watchlist")
if _current_view in ("logs", "monitor"):
    st_autorefresh(interval=DashboardConfig.LIVE_REFRESH_MS, limit=None, key="aegis_live_refresh")
elif _current_view in ("watchlist", "advisor", "paper_trading"):
    st_autorefresh(interval=DashboardConfig.SLOW_REFRESH_MS, limit=None, key="aegis_medium_refresh")

tm = TokenManager()

if not tm.check_budget():
    st.error(f"**BUDGET EXCEEDED** — Daily limit ${tm.max_daily_budget:.2f} reached. Agents PAUSED.")

# ===========================================================================
# SIDEBAR
# ===========================================================================
st.sidebar.markdown(
    "<div class='aegis-logo'>AEGIS<span class='logo-sub'>AI Trading Terminal v6.0</span></div>",
    unsafe_allow_html=True,
)
# User info + tier badge + logout
_user_display = _current_user.get("name", "Guest")
_tier_badge_colors = {"free": "#6e7681", "pro": "#3fb950", "enterprise": "#a371f7"}
_tier_badge_clr = _tier_badge_colors.get(_current_tier, "#6e7681")
_tier_label = _tier_config.get("name", "Free")
st.sidebar.markdown(
    f"<div style='display:flex;align-items:center;justify-content:space-between;"
    f"padding:4px 0 6px 0;'>"
    f"<span style='color:#8b949e;font-size:0.75em;font-family:Inter,sans-serif;'>"
    f"{_user_display}</span>"
    f"<span style='color:{_tier_badge_clr};font-size:0.6em;font-weight:600;"
    f"font-family:JetBrains Mono,monospace;border:1px solid {_tier_badge_clr};"
    f"border-radius:4px;padding:1px 6px;'>{_tier_label}</span></div>",
    unsafe_allow_html=True,
)
_now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
_refresh_label = "Live" if _current_view in ("logs", "monitor") else "60s" if _current_view in ("watchlist", "advisor") else "Manual"
st.sidebar.caption(f"{_now_utc} | Refresh: {_refresh_label}")
# Logout button (only for non-guests)
if _current_user_id != "default":
    if st.sidebar.button("Sign Out", key="logout_btn", use_container_width=True):
        # Destroy persistent session + clear remember-me file
        _logout_token = st.session_state.pop("session_token", "")
        if _logout_token:
            try:
                auth_manager.destroy_session(_logout_token)
            except Exception:
                pass
        try:
            auth_manager.clear_active_session()
        except Exception:
            pass
        for k in ["user", "user_id"]:
            st.session_state.pop(k, None)
        st.rerun()

# Language selector in sidebar
language_selector(sidebar=True)

# Apply RTL CSS if Arabic selected
st.markdown(get_rtl_css(), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar Navigation — Grouped, Color-Coded, with Icons & Priority Badges
# ---------------------------------------------------------------------------

# Active view highlight style
_active_view = st.session_state.get("view", "advisor")

# Auto-trading status indicator
_autotrade_status = "ACTIVE"
_autotrade_color = "#3fb950"
try:
    from config import AutoTradeConfig
    if not AutoTradeConfig.ENABLED:
        _autotrade_status = "PAUSED"
        _autotrade_color = "#f85149"
except Exception:
    _autotrade_status = "N/A"
    _autotrade_color = "#6e7681"

# Show auto-trading status badge in sidebar
st.sidebar.markdown(
    f"<div style='text-align:center;padding:6px 12px;margin-bottom:8px;"
    f"background:rgba({','.join(str(int(_autotrade_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.12);"
    f"border:1px solid {_autotrade_color};border-radius:8px;'>"
    f"<span style='font-family:JetBrains Mono,monospace;font-size:0.72em;color:{_autotrade_color};'>"
    f"AutoPilot: {_autotrade_status}</span></div>",
    unsafe_allow_html=True,
)

# ── GLOBAL SEARCH BAR ──
# Build searchable index of assets + pages
_SEARCH_PAGES = {
    "Daily Advisor": "advisor", "Morning Brief": "morning_brief",
    "Watchlist": "watchlist", "Charts": "charts", "Paper Trading": "paper_trading",
    "Trade Journal": "trade_journal", "Alerts": "alerts",
    "Report Card": "report_card", "News Intelligence": "news_intel",
    "Economic Calendar": "econ_calendar", "Analytics": "analytics",
    "Risk Dashboard": "risk_dashboard", "Optimizer": "optimizer", "Settings": "settings",
}
_search_query = st.sidebar.text_input(
    "🔍", placeholder="Search assets, pages…", key="global_search", label_visibility="collapsed",
)
if _search_query and len(_search_query) >= 2:
    _sq = _search_query.lower().strip()
    _search_hits = []
    # Search assets from watchlist
    try:
        _search_wl = _load_raw_watchlist_summary() if callable(_load_raw_watchlist_summary) else {}
    except Exception:
        _search_wl = {}
    if not _search_wl:
        try:
            from watchlist_manager import WatchlistManager as _SWM
            _swm = _SWM()
            _search_wl = {a["name"]: a for a in _swm.get_active_watchlist().get("assets", [])}
        except Exception:
            _search_wl = {}
    if not _search_wl:
        try:
            _search_uwl = json.loads((Path(__file__).parent.parent / "src" / "data" / "user_watchlist.json").read_text())
            _search_wl = _search_uwl
        except Exception:
            _search_wl = {}
    for _s_name in _search_wl:
        if _sq in _s_name.lower() or _sq in str(_search_wl[_s_name].get("ticker", "")).lower():
            _search_hits.append(("asset", _s_name, _search_wl[_s_name].get("ticker", "")))
    # Search pages
    for _s_page, _s_key in _SEARCH_PAGES.items():
        if _sq in _s_page.lower():
            _search_hits.append(("page", _s_page, _s_key))
    # Show results
    if _search_hits:
        for _s_type, _s_label, _s_extra in _search_hits[:8]:
            if _s_type == "asset":
                if st.sidebar.button(f"📈 {_s_label} ({_s_extra})", key=f"search_{_s_label}",
                                     use_container_width=True):
                    st.session_state["previous_view"] = st.session_state.get("view", "advisor")
                    st.session_state["view"] = "asset_detail"
                    st.session_state["selected_asset"] = _s_label
                    st.rerun()
            else:
                if st.sidebar.button(f"📄 {_s_label}", key=f"search_p_{_s_extra}",
                                     use_container_width=True):
                    st.session_state["previous_view"] = st.session_state.get("view", "advisor")
                    st.session_state["view"] = _s_extra
                    st.rerun()
    else:
        st.sidebar.caption(f"No results for '{_search_query}'")
    st.sidebar.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

# Navigation groups with icons and priority coloring
# ── Strategic Pivot: 28 pages → 18 focused pages ──
# KILLED: kanban, evolution, monitor, budget, logs (developer tools, not product)
# MERGED: performance→analytics, market_overview→watchlist, fundamentals→asset_detail,
#         strategy_lab→optimizer, watchlist_mgr→watchlist
NAV_GROUPS = {
    t("nav.group_trading"): {
        "color": "#3fb950",      # green — money-making pages
        "icon": "💰",
        "items": {
            f"💡 {t('nav.daily_advisor')}": "advisor",
            f"☀️ {t('nav.morning_brief')}": "morning_brief",
            f"📊 {t('nav.watchlist_overview')}": "watchlist",
            f"📈 {t('nav.advanced_charts')}": "charts",
            f"💼 {t('nav.paper_trading')}": "paper_trading",
            f"📓 {t('nav.trade_journal')}": "trade_journal",
            f"🔔 {t('nav.alerts')}": "alerts",
        },
        "priority": True,        # shows a green dot = primary section
    },
    t("nav.group_intelligence"): {
        "color": "#58a6ff",      # blue — research & analysis
        "icon": "🧠",
        "items": {
            f"🎯 {t('nav.signal_report_card')}": "report_card",
            f"🌍 {t('nav.news_intelligence')}": "news_intel",
            f"📅 {t('nav.economic_calendar')}": "econ_calendar",
            f"📉 {t('nav.analytics')}": "analytics",
            f"🛡️ {t('nav.risk_dashboard')}": "risk_dashboard",
            f"⚖️ {t('nav.optimizer')}": "optimizer",
        },
        "priority": False,
    },
    t("nav.group_account"): {
        "color": "#6e7681",      # gray — user settings
        "icon": "⚙️",
        "items": {
            f"⚙️ {t('nav.settings')}": "settings",
        },
        "priority": False,
    },
}

for group_name, group in NAV_GROUPS.items():
    _gc = group["color"]
    _dot = f"<span style='display:inline-block;width:7px;height:7px;border-radius:50%;background:{_gc};"
    _dot += "box-shadow:0 0 6px " + _gc + ";' ></span>" if group["priority"] else ";'></span>"
    st.sidebar.markdown(
        f"<div class='section-header'>{_dot}"
        f"<span class='label' style='color:{_gc};font-size:0.72em;letter-spacing:0.15em;'>"
        f"{group_name}</span></div>",
        unsafe_allow_html=True,
    )
    _gc_hex = _gc.lstrip("#")
    _gc_rgb = f"{int(_gc_hex[0:2],16)},{int(_gc_hex[2:4],16)},{int(_gc_hex[4:6],16)}"
    for label, key in group["items"].items():
        _is_active = (_active_view == key)
        _is_locked = not auth_manager.can_access_view(key, _current_tier)
        if _is_active:
            # Active page: styled like a selected button with glow
            st.sidebar.markdown(
                f"<div style='border:1px solid {_gc};border-left:3px solid {_gc};"
                f"background:rgba({_gc_rgb},0.12);"
                f"border-radius:8px;padding:6px 12px;margin-bottom:2px;"
                f"box-shadow:0 0 10px rgba({_gc_rgb},0.15);'>"
                f"<span style='color:#e6edf3;font-family:Inter,sans-serif;font-size:0.8rem;"
                f"font-weight:600;'>{label}</span></div>",
                unsafe_allow_html=True,
            )
        elif _is_locked:
            # Locked: still clickable — navigates to page where upgrade prompt shows
            if st.sidebar.button(f"{label} 🔒", key=f"nav_{key}", use_container_width=True):
                st.session_state["previous_view"] = st.session_state.get("view", "advisor")
                st.session_state["view"] = key
                st.rerun()
        else:
            if st.sidebar.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state["previous_view"] = st.session_state.get("view", "advisor")
                st.session_state["view"] = key
                st.rerun()
    st.sidebar.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

# ── SIDEBAR PORTFOLIO TICKER ──
try:
    _sb_port = paper_trader._load()
    # Total equity = cash + market value of open positions
    _sb_cash = _sb_port.get("cash", 1000)
    _sb_open = _sb_port.get("open_positions", [])
    _sb_pos_value = sum(p.get("usd_amount", 0) for p in _sb_open)
    _sb_equity = _sb_cash + _sb_pos_value
    _sb_start = _sb_port.get("starting_balance", 1000)
    _sb_pos_count = len(_sb_open)
    _sb_trade_count = len(_sb_port.get("trade_history", []))
    _sb_return = ((_sb_equity / _sb_start) - 1) * 100 if _sb_start > 0 else 0
    _sb_ret_color = "#3fb950" if _sb_return >= 0 else "#f85149"
    _sb_ret_icon = "▲" if _sb_return >= 0 else "▼"
    st.sidebar.markdown(
        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.4);"
        f"border-radius:8px;padding:10px 14px;margin:6px 0 4px 0;'>"
        f"<div style='color:#8b949e;font-size:0.65em;letter-spacing:0.12em;margin-bottom:4px;'>"
        f"PORTFOLIO</div>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;'>"
        f"<span style='color:#e6edf3;font-family:JetBrains Mono,monospace;"
        f"font-size:1.05em;font-weight:700;'>${_sb_equity:,.2f}</span>"
        f"<span style='color:{_sb_ret_color};font-family:JetBrains Mono,monospace;"
        f"font-size:0.82em;font-weight:600;'>{_sb_ret_icon} {_sb_return:+.2f}%</span>"
        f"</div>"
        f"<div style='color:#8b949e;font-size:0.65em;margin-top:3px;'>"
        f"{_sb_pos_count} open · {_sb_trade_count} trades</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Open Portfolio", key="sb_portfolio_link", use_container_width=True):
        st.session_state["previous_view"] = st.session_state.get("view", "advisor")
        st.session_state["view"] = "paper_trading"
        st.rerun()
except Exception:
    pass

# ── SIDEBAR BRAIN STATUS ──
try:
    _brain_status_path = Path(__file__).resolve().parent.parent / "src" / "data" / "brain_status.json"
    if _brain_status_path.exists():
        _bs = json.loads(_brain_status_path.read_text(encoding="utf-8"))
        _bs_status = _bs.get("status", "offline")
        _bs_last = _bs.get("last_cycle", "")
        _bs_cycles = _bs.get("cycles_today", 0)
        _bs_interval = _bs.get("interval_min", 30)
        _bs_error = _bs.get("last_error")

        # Calculate "ago" string
        _bs_ago = ""
        if _bs_last:
            try:
                _bs_last_dt = datetime.fromisoformat(_bs_last.replace("Z", "+00:00"))
                _bs_delta = (datetime.now(timezone.utc) - _bs_last_dt).total_seconds()
                if _bs_delta < 60:
                    _bs_ago = f"{int(_bs_delta)}s ago"
                elif _bs_delta < 3600:
                    _bs_ago = f"{int(_bs_delta // 60)}m ago"
                else:
                    _bs_ago = f"{int(_bs_delta // 3600)}h ago"
            except (ValueError, TypeError):
                _bs_ago = ""

        # Status indicator
        if _bs_status == "running":
            _bs_dot = "#d29922"
            _bs_label = "SCANNING"
        elif _bs_status == "idle":
            _bs_dot = "#3fb950"
            _bs_label = "ACTIVE"
        elif _bs_status == "error":
            _bs_dot = "#f85149"
            _bs_label = "ERROR"
        else:
            _bs_dot = "#484f58"
            _bs_label = "OFFLINE"

        _bs_detail = f"{_bs_cycles} cycles today" + (f" · last {_bs_ago}" if _bs_ago else "")

        st.sidebar.markdown(
            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.4);"
            f"border-radius:8px;padding:8px 14px;margin:4px 0;'>"
            f"<div style='display:flex;align-items:center;gap:6px;'>"
            f"<span style='display:inline-block;width:7px;height:7px;border-radius:50%;"
            f"background:{_bs_dot};box-shadow:0 0 6px {_bs_dot};'></span>"
            f"<span style='color:#8b949e;font-size:0.65em;letter-spacing:0.12em;'>BRAIN: {_bs_label}</span>"
            f"</div>"
            f"<div style='color:#6e7681;font-size:0.6em;margin-top:3px;'>{_bs_detail}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
except Exception:
    pass

# Export report download
try:
    _report_bytes = report_generator.generate_report_bytes()
    _report_fname = f"aegis_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.html"
    st.sidebar.download_button(
        label="Export Report",
        data=_report_bytes,
        file_name=_report_fname,
        mime="text/html",
        use_container_width=True,
        key="sidebar_export_report",
    )
except Exception:
    pass

# ── DATA FRESHNESS INDICATOR ──
_ws_path = NEWS_DIR / "watchlist_summary.json"
if _ws_path.exists():
    _ws_mtime = datetime.fromtimestamp(_ws_path.stat().st_mtime, tz=timezone.utc)
    _ws_age_min = (datetime.now(timezone.utc) - _ws_mtime).total_seconds() / 60
    if _ws_age_min < 5:
        _fresh_color, _fresh_label = "#3fb950", "FRESH"
    elif _ws_age_min < 30:
        _fresh_color, _fresh_label = "#d29922", f"{_ws_age_min:.0f}m ago"
    elif _ws_age_min < 120:
        _fresh_color, _fresh_label = "#f0883e", f"{_ws_age_min:.0f}m ago"
    else:
        _fresh_color, _fresh_label = "#f85149", "STALE"
    st.sidebar.markdown(
        f"<div style='text-align:center;padding:4px 8px;margin:4px 0;'>"
        f"<span style='color:#8b949e;font-size:0.62em;font-family:JetBrains Mono,monospace;'>"
        f"Data: </span>"
        f"<span style='color:{_fresh_color};font-size:0.62em;font-family:JetBrains Mono,monospace;"
        f"font-weight:600;'>{_fresh_label}</span>"
        f"<span style='color:#8b949e;font-size:0.62em;'> · "
        f"{_ws_mtime.strftime('%H:%M UTC')}</span></div>",
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        "<div style='text-align:center;padding:4px 8px;margin:4px 0;'>"
        "<span style='color:#f85149;font-size:0.62em;font-family:JetBrains Mono,monospace;"
        "font-weight:600;'>NO DATA — Run a scan first</span></div>",
        unsafe_allow_html=True,
    )

st.sidebar.divider()

# Research files
st.sidebar.markdown(
    "<div class='section-header'><span class='dot' style='background:#3fb950;'></span>"
    "<span class='label'>Research</span></div>",
    unsafe_allow_html=True,
)
research_files = list_research_files()
if not research_files:
    st.sidebar.caption("No reports yet.")
for f in research_files:
    label = f.stem.replace("_", " ")
    signal = detect_signal_label(f)
    if signal:
        st.sidebar.markdown(f"{signal_badge_html(signal)} &nbsp; {label}", unsafe_allow_html=True)
    if st.sidebar.button(f"{'>> ' if signal and 'BUY' in (signal or '') else ''}{label}", key=f"r_{f.name}", use_container_width=True):
        st.session_state["previous_view"] = st.session_state.get("view", "advisor")
        st.session_state["selected_research"] = str(f)
        st.session_state["view"] = "research"
        st.rerun()

st.sidebar.divider()
mode_label = "Deep Research" if tm.mode == "deep_research" else "Fast Scan"
st.sidebar.markdown(
    f"<div style='text-align:center;padding:8px 0;'>"
    f"<span style='color:#8b949e;font-family:JetBrains Mono,monospace;font-size:0.7em;'>"
    f"{len(research_files)} reports &middot; {mode_label}</span></div>",
    unsafe_allow_html=True,
)

# Sidebar legal disclaimer
st.sidebar.markdown(
    "<div style='border-top:1px solid rgba(48,54,61,0.3);padding:8px 4px 4px 4px;"
    "margin-top:8px;text-align:center;'>"
    "<span style='color:#30363d;font-size:0.55em;font-family:Inter,sans-serif;"
    "line-height:1.4;display:block;'>"
    "Not investment advice. AI signals can be wrong. "
    "Trading involves risk of loss. "
    "Paper trading results are simulated.</span></div>",
    unsafe_allow_html=True,
)

# ===========================================================================
# Page Info Helper — every page gets an info box explaining what it does
# ===========================================================================

PAGE_INFO = {
    "advisor": {
        "title": "YOUR DAILY TRADING ADVISOR",
        "text": (
            "<strong>This is your morning briefing.</strong> Clear, actionable advice "
            "based on all available data: technical signals, news sentiment, geopolitical "
            "events, and macro regime. "
            "<br><br>"
            "Each asset gets a simple verdict: <strong>BUY NOW</strong>, "
            "<strong>WAIT</strong>, or <strong>AVOID</strong> — with plain-language "
            "reasoning you can act on immediately."
        ),
    },
    "watchlist": {
        "title": "WHAT IS THIS PAGE?",
        "text": (
            "<strong>Your live trading dashboard.</strong> Each card shows a real-time signal "
            "(BUY/SELL/NEUTRAL) with a <strong>Confidence Score</strong> — the AI's probability "
            "estimate that this trade will be profitable. "
            "<br><br>"
            "<strong>Confidence %</strong> = How likely the trade wins (based on technicals 40% + "
            "news sentiment 20% + historical accuracy 40%). These weights adapt automatically "
            "per asset based on what has worked before. "
            "<br>"
            "<strong>Signal Score</strong> = Technical strength from -100 to +100. "
            "<strong>Backtest</strong> = Would this strategy have worked in the last 30 days?"
        ),
    },
    "charts": {
        "title": "ADVANCED CHARTS",
        "text": (
            "<strong>Interactive price charts</strong> with technical indicators overlaid. "
            "Use this to visually confirm signals — look for where moving averages cross, "
            "RSI extremes (below 30 = oversold, above 70 = overbought), and Bollinger Band squeezes."
        ),
    },
    "paper_trading": {
        "title": "PAPER TRADING — PRACTICE MODE",
        "text": (
            "<strong>Risk-free practice trading.</strong> Open and close positions with virtual money "
            "($1,000 starting balance). Every trade has automatic <strong>stop-loss</strong> (limits your "
            "downside) and <strong>take-profit</strong> (locks in gains). "
            "<br><br>"
            "The AutoPilot system opens trades here automatically when signals are strong enough. "
            "Your real skill is tracked here before you ever risk real money."
        ),
    },
    "alerts": {
        "title": "PRICE & SIGNAL ALERTS",
        "text": (
            "<strong>Get notified</strong> when prices hit your targets, RSI reaches extremes, "
            "or percentage moves happen. Alerts trigger via the dashboard and optionally via "
            "Discord/Email. Set alerts on assets you're watching but not ready to trade yet."
        ),
    },
    "news_intel": {
        "title": "NEWS INTELLIGENCE — THE EDGE",
        "text": (
            "<strong>This is where you catch opportunities before others.</strong> "
            "When a geopolitical event happens (war, sanctions, rate cuts), this page shows you: "
            "<br>1) What happened historically in similar situations "
            "<br>2) Which assets moved and by how much "
            "<br>3) Whether the current market setup matches those patterns "
            "<br><br>"
            "Think of it like a <strong>trading playbook</strong> — Iran tensions? Oil historically "
            "rises. Fed rate cut? Gold and BTC rally. This page connects the dots for you."
        ),
    },
    "report_card": {
        "title": "SIGNAL REPORT CARD — AI ACCOUNTABILITY",
        "text": (
            "<strong>Every prediction Aegis makes is tracked and graded.</strong> "
            "This page shows how accurate our signals have been — wins, losses, and "
            "lessons learned. No cherry-picking, no hiding failures. "
            "<br><br>"
            "<strong>Why this matters:</strong> An AI that grades itself publicly is one "
            "you can trust. Watch the accuracy trend over time as the system learns."
        ),
    },
    "fundamentals": {
        "title": "FUNDAMENTAL ANALYSIS",
        "text": (
            "<strong>Beyond price charts.</strong> See the underlying financial health, "
            "earnings data, revenue growth, and valuation ratios. Fundamentals tell you "
            "<em>what</em> to buy; technicals tell you <em>when</em> to buy."
        ),
    },
    "strategy_lab": {
        "title": "STRATEGY LAB — BUILD & TEST",
        "text": (
            "<strong>Design custom trading strategies</strong> using plain language or templates. "
            "Backtest them against real historical data to see if they would have made money. "
            "<br><br>"
            "<strong>HyperOptimizer</strong> automatically tunes strategy parameters to find the "
            "best RSI thresholds, stop-loss %, and take-profit levels for each asset."
        ),
    },
    "analytics": {
        "title": "PERFORMANCE ANALYTICS",
        "text": (
            "<strong>How well is the system performing?</strong> "
            "<br><strong>Sharpe Ratio</strong> = Risk-adjusted return (above 1.0 is good, above 2.0 is excellent). "
            "<br><strong>Win Rate</strong> = Percentage of trades that were profitable. "
            "<br><strong>Max Drawdown</strong> = Worst peak-to-trough drop (lower is safer). "
            "<br><strong>Profit Factor</strong> = Total gains / Total losses (above 1.5 is strong)."
        ),
    },
    "market_overview": {
        "title": "MARKET OVERVIEW",
        "text": (
            "<strong>See the big picture.</strong> Cross-market sector performance, "
            "correlations between assets, and momentum rankings. Useful for understanding "
            "whether the overall market environment is favorable for trading."
        ),
    },
    "kanban": {
        "title": "KANBAN TASK BOARD",
        "text": (
            "<strong>All trade alerts and tasks</strong> organized as cards. "
            "Backlog → To Do → In Progress → Done. "
            "The scanner automatically creates trade alert tickets here when strong signals are found."
        ),
    },
    "evolution": {
        "title": "SYSTEM EVOLUTION — AI LEARNING",
        "text": (
            "<strong>Watch the AI learn from its mistakes.</strong> "
            "Every prediction is tracked, validated, and scored. Wrong predictions become "
            "<strong>lessons</strong> that prevent the same mistake. Win rates improve over time. "
            "This page shows the learning curve, prediction accuracy, and stored lessons."
        ),
    },
    "performance": {
        "title": "AGENT PERFORMANCE",
        "text": (
            "<strong>Under the hood.</strong> See how each AI agent (Scanner, Researcher, "
            "Analyst, Trader) is performing — their task counts, success rates, and timing."
        ),
    },
    "monitor": {
        "title": "AGENT MONITOR — LIVE STATUS",
        "text": (
            "<strong>Real-time health check</strong> of all system agents. "
            "Green = healthy, Yellow = degraded, Red = unhealthy. "
            "Shows what each agent last did and when."
        ),
    },
    "budget": {
        "title": "BUDGET & API USAGE",
        "text": (
            "<strong>Track your API costs.</strong> Shows daily token usage, "
            "cost per operation, and remaining budget. Helps you optimize between "
            "Fast Scan (cheap) and Deep Research (thorough but more expensive) modes."
        ),
    },
    "logs": {
        "title": "LIVE AGENT LOGS",
        "text": (
            "<strong>Full activity log</strong> of every action taken by every agent. "
            "Auto-refreshes. Useful for debugging and understanding exactly what the "
            "system is doing on each brain cycle."
        ),
    },
    "morning_brief": {
        "title": "MORNING BRIEF — YOUR DAILY MARKET SNAPSHOT",
        "text": (
            "<strong>One page, everything you need.</strong> Auto-generated summary of "
            "today's market conditions: macro regime, geopolitical risk, top trading "
            "opportunities, upcoming economic events, and a clear bottom-line takeaway. "
            "<br><br>"
            "Think of this as your daily newspaper for the markets — read it in 60 seconds "
            "and know exactly where you stand."
        ),
    },
    "trade_journal": {
        "title": "TRADE JOURNAL — YOUR FULL TRADING HISTORY",
        "text": (
            "<strong>Every trade, every lesson.</strong> "
            "See your complete trade history with filters by asset, direction, and outcome. "
            "Track win/loss streaks, best/worst trades, and P&L by time of day. "
            "<br><br>"
            "<strong>Export your data</strong> as CSV for external analysis. "
            "This is your trading diary — the key to improving over time."
        ),
    },
    "risk_dashboard": {
        "title": "RISK DASHBOARD — PORTFOLIO PROTECTION",
        "text": (
            "<strong>Know your risk before it knows you.</strong> "
            "See portfolio exposure by asset class, direction, and individual positions. "
            "Monitor concentration risk, correlation heatmaps, and Value at Risk (VaR). "
            "<br><br>"
            "<strong>Position sizing recommendations</strong> based on Kelly Criterion "
            "help you size trades optimally. Compare your performance against benchmarks."
        ),
    },
    "watchlist_mgr": {
        "title": "WATCHLIST MANAGER — MULTIPLE CONFIGURATIONS",
        "text": (
            "<strong>Create and manage multiple watchlists.</strong> "
            "Switch between different asset configurations instantly — "
            "Crypto Focus, Commodities, Safe Haven, or your own custom sets. "
            "<br><br>"
            "<strong>Presets</strong> give you instant templates. "
            "<strong>Duplicate</strong> an existing list to experiment without losing your setup."
        ),
    },
    "optimizer": {
        "title": "PORTFOLIO OPTIMIZER — MEAN-VARIANCE ALLOCATION",
        "text": (
            "<strong>Find the optimal portfolio allocation</strong> using modern portfolio theory. "
            "Compares Max Sharpe, Min Variance, Equal Weight, and Half-Kelly strategies. "
            "<br><br>"
            "<strong>Efficient Frontier</strong> shows the best possible risk-return tradeoff. "
            "See exactly which assets to overweight and which to trim."
        ),
    },
    "econ_calendar": {
        "title": "ECONOMIC CALENDAR — KNOW WHAT'S COMING",
        "text": (
            "<strong>Never get caught off guard.</strong> Tracks all major market-moving "
            "events: FOMC decisions, NFP, CPI, ECB, OPEC, and more. Each event shows a "
            "countdown timer, impact rating, affected assets, and historical context. "
            "<br><br>"
            "High-impact events (3 stars) can move markets 2-5% in minutes. "
            "Plan your trades around the calendar, not despite it."
        ),
    },
    "asset_detail": {
        "title": "ASSET DEEP DIVE",
        "text": (
            "<strong>Everything about one asset in one place.</strong> "
            "Charts, news, social sentiment, fundamentals, and your trading history — "
            "all filtered to this single asset. Use the tabs to explore every angle."
        ),
    },
    "settings": {
        "title": "TERMINAL SETTINGS",
        "text": (
            "<strong>Configure your terminal.</strong> Adjust signal weights, risk thresholds, "
            "auto-trader gates, and refresh intervals. Changes are saved and persist across sessions."
        ),
    },
}


def asset_link_button(asset_name: str, key_prefix: str) -> None:
    """Render a small button that navigates to the Asset Detail page."""
    if st.button(asset_name, key=f"alink_{key_prefix}_{asset_name}", use_container_width=True):
        _navigate_to("asset_detail", detail_asset=asset_name)


def render_page_info(view_key: str, collapsed: bool = True) -> None:
    """Render the info box for a given page. Collapsed by default."""
    info = PAGE_INFO.get(view_key)
    if not info:
        return
    with st.expander(f"ℹ️ {info['title']} — Click to learn what this page does", expanded=not collapsed):
        st.markdown(
            f"<div class='page-info-box'>{info['text']}</div>",
            unsafe_allow_html=True,
        )


# Build view→group lookup for breadcrumbs
_VIEW_GROUP_MAP: dict[str, tuple[str, str]] = {}
for _gname, _gdata in NAV_GROUPS.items():
    for _glabel, _gkey in _gdata["items"].items():
        _VIEW_GROUP_MAP[_gkey] = (_gname, _gdata["color"])
# Contextual pages (not in sidebar but still belong to a group)
_VIEW_GROUP_MAP["asset_detail"] = (t("nav.group_trading"), "#3fb950")
_VIEW_GROUP_MAP["research"] = (t("nav.group_research"), "#3fb950")
# Killed pages still get a group mapping for breadcrumbs if accessed via URL/state
_VIEW_GROUP_MAP["kanban"] = (t("nav.group_system"), "#6e7681")
_VIEW_GROUP_MAP["evolution"] = (t("nav.group_system"), "#6e7681")
_VIEW_GROUP_MAP["performance"] = (t("nav.group_system"), "#6e7681")
_VIEW_GROUP_MAP["monitor"] = (t("nav.group_system"), "#6e7681")
_VIEW_GROUP_MAP["budget"] = (t("nav.group_system"), "#6e7681")
_VIEW_GROUP_MAP["logs"] = (t("nav.group_system"), "#6e7681")
_VIEW_GROUP_MAP["fundamentals"] = (t("nav.group_intelligence"), "#58a6ff")
_VIEW_GROUP_MAP["market_overview"] = (t("nav.group_intelligence"), "#58a6ff")
_VIEW_GROUP_MAP["strategy_lab"] = (t("nav.group_intelligence"), "#58a6ff")
_VIEW_GROUP_MAP["watchlist_mgr"] = (t("nav.group_trading"), "#3fb950")


def _navigate_to(target_view: str, **extra_state) -> None:
    """Set previous_view, switch to target, and rerun."""
    st.session_state["previous_view"] = st.session_state.get("view", "advisor")
    st.session_state["view"] = target_view
    for k, v in extra_state.items():
        st.session_state[k] = v
    st.rerun()


def render_page_header(title: str, view_key: str = "", subtitle: str = "") -> None:
    """Render breadcrumb + title + back button for every page."""
    _vk = view_key or st.session_state.get("view", "")
    _group_name, _group_color = _VIEW_GROUP_MAP.get(_vk, ("", "#6e7681"))

    _bc_col, _back_col = st.columns([5, 1])
    with _bc_col:
        if _group_name:
            st.markdown(
                f"<div style='margin-bottom:2px;'>"
                f"<span style='color:{_group_color};font-size:0.72em;"
                f"font-family:JetBrains Mono,monospace;letter-spacing:0.1em;'>"
                f"{_group_name}</span>"
                f"<span style='color:#8b949e;font-size:0.72em;'> / </span>"
                f"<span style='color:#e6edf3;font-size:0.72em;'>{title}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(f"# {title}")
        if subtitle:
            st.markdown(
                f"<div style='color:#8b949e;font-size:0.85em;margin-top:-10px;"
                f"margin-bottom:16px;'>{subtitle}</div>",
                unsafe_allow_html=True,
            )
    with _back_col:
        _prev = st.session_state.get("previous_view", "")
        if _prev and _prev != _vk:
            if st.button("< Back", key=f"back_{_vk}", use_container_width=True):
                _navigate_to(_prev)


# ===========================================================================
# GLOSSARY — inline tooltips for technical terms
# ===========================================================================

GLOSSARY = {
    "RSI": "Relative Strength Index (0-100). Below 30 = oversold (buy signal), above 70 = overbought (sell signal).",
    "MACD": "Moving Average Convergence Divergence. Measures momentum — bullish when MACD crosses above signal line.",
    "SMA": "Simple Moving Average. Average closing price over N days. SMA-50 crossing above SMA-200 = Golden Cross (bullish).",
    "Bollinger Bands": "Price channel 2 standard deviations around SMA-20. Price near lower band = potential buy.",
    "Sharpe Ratio": "Risk-adjusted return. Higher = better. Above 1.0 is good, above 2.0 is excellent.",
    "Sortino Ratio": "Like Sharpe but only penalizes downside risk. Better measure for volatile assets.",
    "Kelly Criterion": "Optimal bet sizing formula. Suggests what % of portfolio to risk per trade based on win rate.",
    "VaR": "Value at Risk. Maximum expected loss over a time period at a given confidence level (e.g., 95%).",
    "Drawdown": "Peak-to-trough decline in portfolio value. Max Drawdown = worst historical drop.",
    "R:R": "Risk-to-Reward Ratio. E.g., 2:1 means potential profit is 2x the potential loss.",
    "Stop-Loss": "Automatic sell order triggered when price falls to a set level, limiting losses.",
    "Take-Profit": "Automatic sell order triggered when price rises to a set target, locking in gains.",
    "Confidence": "Signal strength (0-100%). Blends technical analysis (40%), news sentiment (20%), and historical accuracy (40%).",
    "Regime": "Current market environment: Risk-On (bullish), Risk-Off (defensive), Inflationary, Deflationary, or Volatile.",
}


def glossary_css() -> str:
    """Return CSS for glossary tooltips — injected once."""
    return (
        "<style>"
        ".glossary{position:relative;display:inline;border-bottom:1px dotted #58a6ff;"
        "color:#58a6ff;cursor:help;font-size:inherit;}"
        ".glossary .gdef{visibility:hidden;opacity:0;position:absolute;bottom:125%;"
        "left:50%;transform:translateX(-50%);background:#1c2333;color:#c9d1d9;"
        "padding:8px 12px;border-radius:8px;border:1px solid #30363d;"
        "font-size:0.78em;line-height:1.4;width:260px;z-index:999;"
        "font-family:Inter,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.4);"
        "transition:opacity 0.15s;pointer-events:none;}"
        ".glossary:hover .gdef{visibility:visible;opacity:1;}"
        "</style>"
    )


def gtip(term: str) -> str:
    """Return HTML for a glossary tooltip. Usage: st.markdown(f'...{gtip(\"RSI\")}...', unsafe_allow_html=True)"""
    defn = GLOSSARY.get(term, "")
    if not defn:
        return term
    return f"<span class='glossary'>{term}<span class='gdef'>{defn}</span></span>"


# ===========================================================================
# VIEWS
# ===========================================================================
if "view" not in st.session_state:
    st.session_state["view"] = "advisor"
view = st.session_state["view"]

# ---------------------------------------------------------------------------
# Feature Gating — redirect locked views to upgrade prompt
# ---------------------------------------------------------------------------
if not auth_manager.can_access_view(view, _current_tier):
    # Page-specific previews so users see what they're missing
    _gate_previews = {
        "optimizer": {
            "icon": "📊", "title": "Portfolio Optimizer",
            "features": [
                "Mean-variance optimization across your watchlist",
                "4 strategies: Max Sharpe, Min Variance, Equal Weight, Half-Kelly",
                "Efficient frontier visualization",
                "Allocation recommendations with expected returns",
            ],
        },
        "strategy_lab": {
            "icon": "🧪", "title": "Strategy Lab",
            "features": [
                "Build custom strategies in plain English",
                "Backtest against historical data",
                "Win rate, Sharpe ratio, max drawdown analysis",
                "Compare strategies side-by-side",
            ],
        },
    }
    _gate_info = _gate_previews.get(view, {
        "icon": "🔒", "title": "Pro Feature",
        "features": ["Advanced analytics and tools"],
    })
    st.markdown(
        f"<div style='text-align:center;padding:40px 20px 20px;'>"
        f"<span style='font-size:3rem;'>{_gate_info['icon']}</span><br><br>"
        f"<span style='font-size:1.4rem;color:#e6edf3;font-weight:600;'>{_gate_info['title']}</span><br>"
        f"<span style='color:#8b949e;font-size:0.9em;'>Unlock with Operator (Pro) subscription</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    # Show feature preview list
    _feat_html = "".join(
        f"<li style='color:#c9d1d9;padding:4px 0;'>{f}</li>"
        for f in _gate_info["features"]
    )
    st.markdown(
        f"<div style='max-width:500px;margin:20px auto;background:rgba(22,27,34,0.8);"
        f"border:1px solid rgba(48,54,61,0.6);border-radius:10px;padding:20px 28px;'>"
        f"<div style='color:#58a6ff;font-size:0.75em;letter-spacing:0.1em;margin-bottom:8px;'>"
        f"WHAT YOU GET</div>"
        f"<ul style='margin:0;padding-left:20px;font-size:0.9em;'>{_feat_html}</ul></div>",
        unsafe_allow_html=True,
    )
    _gate_col1, _gate_col2, _gate_col3 = st.columns([1, 2, 1])
    with _gate_col2:
        st.markdown(
            "<div style='background:linear-gradient(135deg,rgba(63,185,80,0.1),rgba(63,185,80,0.05));"
            "border:1px solid rgba(63,185,80,0.3);border-radius:12px;padding:20px;text-align:center;'>"
            "<span style='color:#3fb950;font-weight:600;font-size:1.1em;'>Operator — $29/mo</span><br>"
            "<span style='color:#8b949e;font-size:0.8em;'>"
            "Unlimited scans &middot; AutoPilot &middot; Portfolio Optimizer &middot; "
            "Strategy Lab &middot; Backtesting &middot; Export Reports"
            "</span></div>",
            unsafe_allow_html=True,
        )
        if _current_user_id != "default" and not _current_user.get("trial_started"):
            if st.button("Start 14-Day Free Trial", key="start_trial_btn", use_container_width=True):
                auth_manager.start_trial(_current_user_id)
                st.session_state["user"]["tier"] = "pro"
                st.rerun()
        elif _current_user_id == "default":
            st.info("Create an account to start a free trial.")
        if st.button("Back", key="gate_back_btn", use_container_width=True):
            st.session_state["view"] = st.session_state.get("previous_view", "advisor")
            st.rerun()
    st.stop()

# Inject glossary CSS once
st.markdown(glossary_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Global: Influencer Alert Toasts — show ONCE per session only
# ---------------------------------------------------------------------------
if "toasts_shown" not in st.session_state:
    st.session_state["toasts_shown"] = True
    _toast_social_file = NEWS_DIR / "social_sentiment.json"
    if _toast_social_file.exists():
        try:
            _toast_social = json.loads(_toast_social_file.read_text(encoding="utf-8"))
            _toast_alerts = _toast_social.get("alerts", [])
            _toast_high = [a for a in _toast_alerts if a.get("alert_level") == "HIGH"]
            for _ta in _toast_high[:2]:
                _ta_msg = _ta.get("message", "")
                if _ta_msg:
                    st.toast(_ta_msg, icon="📡")
        except Exception:
            pass


# ===========================
# DAILY ADVISOR — Clear, Actionable Trading Advice
# ===========================
if view == "advisor":
    _adv_now = datetime.now(timezone.utc)
    _adv_date = _adv_now.strftime("%A, %B %d, %Y")
    _adv_time = _adv_now.strftime("%H:%M UTC")

    render_page_header("Daily Advisor", view_key="advisor", subtitle=f"{_adv_date} &middot; {_adv_time}")
    render_page_info("advisor")

    # ── Onboarding welcome for first-time users ──
    _ws_file = NEWS_DIR / "watchlist_summary.json"
    if not _ws_file.exists() or _ws_file.stat().st_size < 50:
        st.markdown(
            "<div style='background:linear-gradient(135deg,#161b22,#1c2333);"
            "border:1px solid #3fb950;border-radius:12px;padding:24px 28px;"
            "margin-bottom:20px;'>"
            "<h3 style='color:#3fb950;margin:0 0 12px 0;'>Welcome to Aegis Trading Terminal</h3>"
            "<p style='color:#c9d1d9;margin:0 0 16px 0;font-size:0.95em;'>"
            "Your AI-powered market command center. Here's how to get started:</p>"
            "<ol style='color:#8b949e;margin:0;padding-left:20px;line-height:1.8;'>"
            "<li><b style='color:#e6edf3;'>Scan the markets</b> — Click <b style='color:#3fb950;'>"
            "\"Scan All Assets\"</b> (top right). This fetches live data for 12 assets and takes ~2 min.</li>"
            "<li><b style='color:#e6edf3;'>Read the verdicts</b> — Each asset gets a "
            "<b style='color:#3fb950;'>BUY</b> / <b style='color:#f0883e;'>WAIT</b> / "
            "<b style='color:#f85149;'>AVOID</b> signal based on technical + news + historical analysis.</li>"
            "<li><b style='color:#e6edf3;'>Paper trade</b> — Click Quick LONG/SHORT to place "
            "simulated trades with a $1,000 virtual portfolio. Zero real money at risk.</li>"
            "<li><b style='color:#e6edf3;'>Explore</b> — Click any asset name to see its "
            "full detail page (charts, news, social, fundamentals).</li>"
            "</ol>"
            "<p style='color:#6e7681;margin:12px 0 0 0;font-size:0.82em;'>"
            "Hover over highlighted terms like "
            f"{gtip('RSI')}, {gtip('MACD')}, or {gtip('Confidence')} "
            "anywhere in the app for quick definitions.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Scan buttons ──
    _adv_btn_col0, _adv_btn_col1, _adv_btn_col2 = st.columns([2, 1, 1])
    with _adv_btn_col1:
        _do_social = st.button("📡 Refresh Social Pulse", key="adv_social_btn", use_container_width=True)
    with _adv_btn_col2:
        _do_scan = st.button("🔍 Scan All Assets", key="adv_scan_btn", use_container_width=True)
    if _do_social:
        with st.spinner("Scanning influencers + Reddit social sentiment..."):
            try:
                import social_sentiment as _ss_adv
                _ss_eng = _ss_adv.SocialSentimentEngine()
                _ss_res = _ss_eng.scan_all()
                st.success(f"Social scan done! {_ss_res['stats']['total_alerts']} alerts found.")
                st.rerun()
            except Exception as _ss_err:
                st.error(f"Social scan failed: {_ss_err}")
    if _do_scan:
        from market_scanner import scan_all as _ms_scan_all
        _scan_bar = st.progress(0, text="Initializing scan...")
        _scan_status = st.empty()
        _scan_done = {}

        def _adv_scan_cb(asset_name, index, total, success):
            _scan_done[asset_name] = success
            _scan_bar.progress(index / total, text=f"Scanned {index}/{total} assets...")
            _icons = [f"{'OK' if ok else 'FAIL'} {n}" for n, ok in _scan_done.items()]
            _scan_status.caption(" · ".join(_icons))

        try:
            _ms_scan_all(progress_callback=_adv_scan_cb)
            _scan_bar.progress(1.0, text="Scan complete!")
            _scan_status.empty()
            st.success("Scan complete! All assets updated.")
            import time as _t; _t.sleep(0.5)
            st.rerun()
        except Exception as _scan_err:
            _scan_bar.empty()
            _scan_status.empty()
            st.error(f"Scan failed: {_scan_err}")

    # ══════════════════════════════════════════════════════════════════════════
    # YESTERDAY'S SCORECARD (top of advisor — most prominent)
    # ══════════════════════════════════════════════════════════════════════════
    _pg_user_id = st.session_state.get("user_id", "default")
    _pg = prediction_game_mod.PredictionGame(user_id=_pg_user_id)
    _pg_scorecard = _pg.get_yesterday_scorecard()
    _pg_streak = _pg.get_streak()
    _pg_today_votes = _pg.get_today_votes()

    if _pg_scorecard["total_votes"] > 0:
        _sc = _pg_scorecard
        _sc_user_pct = f"{_sc['user_accuracy']:.0f}%"
        _sc_ai_pct = f"{_sc['ai_accuracy']:.0f}%"
        _sc_beat = _sc.get("user_beat_ai")
        _sc_beat_color = "#3fb950" if _sc_beat else ("#f85149" if _sc_beat is False else "#6e7681")
        _sc_beat_text = "You beat the AI!" if _sc_beat else ("The AI beat you" if _sc_beat is False else "Pending...")
        _sc_beat_icon = "🏆" if _sc_beat else ("🤖" if _sc_beat is False else "⏳")

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#161b22,#1a2332);"
            f"border:2px solid {_sc_beat_color};border-radius:14px;"
            f"padding:20px 24px;margin-bottom:20px;'>"
            f"<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;'>"
            f"<div>"
            f"<div style='color:#8b949e;font-family:JetBrains Mono,monospace;font-size:0.7em;"
            f"letter-spacing:0.12em;margin-bottom:6px;'>YESTERDAY'S SCORECARD &mdash; {_sc['date']}</div>"
            f"<div style='font-size:1.3em;font-weight:800;color:{_sc_beat_color};'>"
            f"{_sc_beat_icon} {_sc_beat_text}</div>"
            f"</div>"
            f"<div style='display:flex;gap:24px;text-align:center;'>"
            f"<div>"
            f"<div style='color:#8b949e;font-size:0.65em;letter-spacing:0.1em;'>YOUR ACCURACY</div>"
            f"<div style='color:#e6edf3;font-family:JetBrains Mono,monospace;"
            f"font-size:1.8em;font-weight:700;'>{_sc_user_pct}</div>"
            f"<div style='color:#8b949e;font-size:0.7em;'>{_sc['user_correct']}✓ {_sc['user_wrong']}✗</div>"
            f"</div>"
            f"<div style='border-left:1px solid #30363d;'></div>"
            f"<div>"
            f"<div style='color:#8b949e;font-size:0.65em;letter-spacing:0.1em;'>AI ACCURACY</div>"
            f"<div style='color:#58a6ff;font-family:JetBrains Mono,monospace;"
            f"font-size:1.8em;font-weight:700;'>{_sc_ai_pct}</div>"
            f"<div style='color:#8b949e;font-size:0.7em;'>{_sc['ai_correct']}✓ {_sc['ai_wrong']}✗</div>"
            f"</div>"
            f"<div style='border-left:1px solid #30363d;'></div>"
            f"<div>"
            f"<div style='color:#8b949e;font-size:0.65em;letter-spacing:0.1em;'>STREAK</div>"
            f"<div style='color:#d29922;font-family:JetBrains Mono,monospace;"
            f"font-size:1.8em;font-weight:700;'>🔥 {_pg_streak['current']}</div>"
            f"<div style='color:#8b949e;font-size:0.7em;'>Best: {_pg_streak['best']}</div>"
            f"</div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
    elif _pg_streak["total_votes"] == 0:
        # First time — encourage engagement
        st.markdown(
            "<div style='background:linear-gradient(135deg,#161b22,#1a2332);"
            "border:2px solid #58a6ff;border-radius:14px;"
            "padding:20px 24px;margin-bottom:20px;'>"
            "<div style='display:flex;align-items:center;gap:16px;'>"
            "<div style='font-size:2em;'>🎯</div>"
            "<div>"
            "<div style='color:#58a6ff;font-size:1.1em;font-weight:700;margin-bottom:4px;'>"
            "Can You Beat the AI?</div>"
            "<div style='color:#8b949e;font-size:0.85em;'>"
            "For each signal below, tap <b style='color:#3fb950;'>Agree</b> or "
            "<b style='color:#f85149;'>Disagree</b>. Tomorrow you'll see who was right &mdash; "
            "you or the AI. Build your accuracy streak!</div>"
            "</div></div></div>",
            unsafe_allow_html=True,
        )

    # ── Load all data ──
    _adv_watchlist = load_watchlist_summary()
    _adv_prices = fetch_live_prices(_adv_watchlist) if _adv_watchlist else {}

    # ── Stale data warning banner ──
    if _adv_watchlist:
        _stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        _timestamps = []
        for _wd in _adv_watchlist.values():
            _ts_str = _wd.get("timestamp", "")
            if _ts_str:
                try:
                    _timestamps.append(datetime.fromisoformat(_ts_str))
                except (ValueError, TypeError):
                    pass
        _newest = max(_timestamps) if _timestamps else None
        _data_age_str = ""
        if _newest:
            _age_delta = datetime.now(timezone.utc) - _newest
            if _age_delta.total_seconds() < 3600:
                _data_age_str = f"{int(_age_delta.total_seconds() / 60)}m ago"
            elif _age_delta.total_seconds() < 86400:
                _data_age_str = f"{_age_delta.total_seconds() / 3600:.1f}h ago"
            else:
                _data_age_str = f"{_age_delta.days}d ago"
        _live_count = len(_adv_prices)
        _total_count = len(_adv_watchlist)

        if _newest and _newest < _stale_cutoff:
            st.markdown(
                f"<div style='background:#2d1b00;border:1px solid #d29922;border-radius:8px;"
                f"padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;gap:10px;'>"
                f"<span style='font-size:1.2em;'>⚠️</span>"
                f"<span style='color:#d29922;font-family:JetBrains Mono,monospace;font-size:0.78em;'>"
                f"STALE DATA — Last scan: {_data_age_str} &middot; Live prices: {_live_count}/{_total_count} "
                f"&middot; Run <b>Scan All Assets</b> for fresh signals</span></div>",
                unsafe_allow_html=True,
            )
        elif _live_count == 0 and _total_count > 0:
            st.markdown(
                "<div style='background:#2d1b00;border:1px solid #d29922;border-radius:8px;"
                "padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;gap:10px;'>"
                "<span style='font-size:1.2em;'>📡</span>"
                "<span style='color:#d29922;font-family:JetBrains Mono,monospace;font-size:0.78em;'>"
                "LIVE PRICES UNAVAILABLE — Market data API may be down. "
                "Showing last scanned prices.</span></div>",
                unsafe_allow_html=True,
            )

    # Update prices in watchlist — use REAL daily change from yfinance, not stale scan delta
    _live_daily_chg = st.session_state.get("_live_daily_changes", {})
    for name, live_price in _adv_prices.items():
        if name in _adv_watchlist:
            _adv_watchlist[name]["price"] = live_price
            # Prefer real daily change from yfinance (vs yesterday's close)
            if name in _live_daily_chg and _live_daily_chg[name] is not None:
                _adv_watchlist[name]["price_change_pct"] = _live_daily_chg[name]
            else:
                # Fallback: compare to scan price — but ONLY if scan is recent enough
                # to be a valid previous-day price. Stale scans produce garbage deltas
                # like BTC: (65000 - 5300) / 5300 = +1123%.
                old_price = _adv_watchlist[name].get("entry", 0) or _adv_watchlist[name].get("price", 0)
                if old_price > 0 and live_price > 0:
                    raw_pct = round((live_price - old_price) / old_price * 100, 2)
                    # If delta > ±10%, the scan price is likely stale/wrong — show nothing
                    if abs(raw_pct) <= 10:
                        _adv_watchlist[name]["price_change_pct"] = raw_pct
                    else:
                        _adv_watchlist[name]["price_change_pct"] = None  # don't display garbage

    # Load geopolitical analysis
    _adv_geo = {}
    _geo_cache = PROJECT_ROOT / "src" / "data" / "geopolitical_analysis.json"
    if _geo_cache.exists():
        try:
            _adv_geo = json.loads(_geo_cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load or detect macro regime
    _adv_regime_data = None
    _regime_cache = PROJECT_ROOT / "src" / "data" / "macro_regime.json"
    if _regime_cache.exists():
        try:
            _adv_regime_data = json.loads(_regime_cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load news impact cache (causal reasoning per asset)
    _adv_impact_cache = {}
    _impact_cache_path = PROJECT_ROOT / "src" / "data" / "news_impact.json"
    if _impact_cache_path.exists():
        try:
            _adv_impact_cache = json.loads(_impact_cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # ── COMPACT MARKET CONTEXT BAR (regime + geo in one line) ──
    if _adv_regime_data:
        _regime = _adv_regime_data.get("regime", "NEUTRAL")
        _regime_icon = _adv_regime_data.get("icon", "")
        _regime_conf = _adv_regime_data.get("confidence", 0)
    else:
        _regime = "UNKNOWN"
        _regime_icon = "❓"
        _regime_conf = 0

    _regime_colors = {
        "RISK_ON": "#3fb950", "RISK_OFF": "#f85149", "INFLATIONARY": "#d29922",
        "DEFLATIONARY": "#58a6ff", "HIGH_VOLATILITY": "#a371f7",
        "NEUTRAL": "#6e7681", "UNKNOWN": "#484f58",
    }
    _rc = _regime_colors.get(_regime, "#6e7681")

    _geo_risk = _adv_geo.get("risk_level", "UNKNOWN")
    _geo_color = {
        "EXTREME": "#f85149", "ELEVATED": "#d29922", "MODERATE": "#d29922",
        "LOW": "#3fb950", "CALM": "#6e7681",
    }.get(_geo_risk, "#484f58")
    _geo_dom = _adv_geo.get("dominant_events", {})
    _geo_themes = ", ".join(
        geopolitical_monitor.EVENT_KEYWORDS.get(et, {}).get("label", et)
        for et in list(_geo_dom.keys())[:2]
    ) if _geo_dom else "None detected"

    # ── Fear & Greed Index ──
    _fg_data = None
    try:
        from fear_greed import FearGreedIndex as _FGI
        _fg_data = _FGI().get_index()
    except Exception:
        pass
    _fg_val = _fg_data["value"] if _fg_data else 50
    _fg_label = _fg_data["label"] if _fg_data else "N/A"
    _fg_color = _fg_data.get("color", "#8b949e") if _fg_data else "#8b949e"
    _fg_icon = {"Extreme Fear": "😱", "Fear": "😟", "Neutral": "😐", "Greed": "😏", "Extreme Greed": "🤑"}.get(_fg_label, "📊")

    st.markdown(
        f"<div style='display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap;'>"
        # Regime chip
        f"<div style='background:#161b22;border:1px solid {_rc};border-radius:8px;"
        f"padding:8px 14px;display:flex;align-items:center;gap:8px;flex:1;min-width:200px;'>"
        f"<span style='font-size:1.2em;'>{_regime_icon}</span>"
        f"<span style='color:{_rc};font-family:JetBrains Mono,monospace;font-size:0.78em;font-weight:700;'>"
        f"REGIME: {_regime.replace('_', ' ')}</span>"
        f"<span style='color:#484f58;font-size:0.65em;'>{_regime_conf:.0%}</span>"
        f"</div>"
        # Geo chip
        f"<div style='background:#161b22;border:1px solid {_geo_color};border-radius:8px;"
        f"padding:8px 14px;display:flex;align-items:center;gap:8px;flex:1;min-width:200px;'>"
        f"<span style='font-size:1.2em;'>🌍</span>"
        f"<span style='color:{_geo_color};font-family:JetBrains Mono,monospace;font-size:0.78em;font-weight:700;'>"
        f"GEO RISK: {_geo_risk}</span>"
        f"<span style='color:#8b949e;font-size:0.68em;'>{_geo_themes}</span>"
        f"</div>"
        # Fear & Greed chip
        f"<div style='background:#161b22;border:1px solid {_fg_color};border-radius:8px;"
        f"padding:8px 14px;display:flex;align-items:center;gap:8px;flex:1;min-width:200px;'>"
        f"<span style='font-size:1.2em;'>{_fg_icon}</span>"
        f"<span style='color:{_fg_color};font-family:JetBrains Mono,monospace;font-size:0.78em;font-weight:700;'>"
        f"F&G: {_fg_val}</span>"
        f"<span style='color:#8b949e;font-size:0.68em;'>{_fg_label}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ── COMPACT STATUS BAR (bot + social + sizing in one strip) ──
    _adv_bot_file = PROJECT_ROOT / "memory" / "bot_activity.json"
    _adv_bot_last = None
    _adv_sched_file = PROJECT_ROOT / "memory" / "bot_schedule.json"
    _adv_sched_on = False
    if _adv_sched_file.exists():
        try:
            _adv_sched = json.loads(_adv_sched_file.read_text(encoding="utf-8"))
            _adv_sched_on = _adv_sched.get("enabled", False)
        except Exception:
            pass
    if _adv_bot_file.exists():
        try:
            _adv_bot_acts = json.loads(_adv_bot_file.read_text(encoding="utf-8"))
            if _adv_bot_acts:
                _adv_bot_last = _adv_bot_acts[-1]
        except Exception:
            pass

    _adv_social_file = NEWS_DIR / "social_sentiment.json"
    _adv_social_data = None
    if _adv_social_file.exists():
        try:
            _adv_social_data = json.loads(_adv_social_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Build compact HTML strip
    _bot_html = ""
    if _adv_bot_last:
        _bl_equity = _adv_bot_last.get("portfolio_equity", 0)
        _bl_ret = _adv_bot_last.get("portfolio_return_pct", 0)
        _bl_ret_color = "#3fb950" if _bl_ret >= 0 else "#f85149"
        _bl_auto = "AUTO" if _adv_sched_on else "MANUAL"
        _bot_html = (
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<span style='font-size:1em;'>🤖</span>"
            f"<span style='color:#8b949e;font-size:0.7em;'>BOT</span>"
            f"<span style='color:{_bl_ret_color};font-family:JetBrains Mono,monospace;"
            f"font-size:0.85em;font-weight:700;'>${_bl_equity:,.0f}</span>"
            f"<span style='color:{_bl_ret_color};font-size:0.7em;'>({_bl_ret:+.1f}%)</span>"
            f"<span style='background:{'#3fb950' if _adv_sched_on else '#484f58'};color:#0d1117;"
            f"padding:1px 6px;border-radius:8px;font-size:0.58em;font-weight:700;'>{_bl_auto}</span>"
            f"</div>"
        )
    else:
        _bot_html = (
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<span>🤖</span><span style='color:#484f58;font-size:0.7em;'>Bot inactive</span></div>"
        )

    _social_html = ""
    if _adv_social_data:
        _sp_stats = _adv_social_data.get("stats", {})
        _sp_total = _sp_stats.get("total_alerts", 0)
        _sp_high = _sp_stats.get("high_alerts", 0)
        _sp_color = "#f85149" if _sp_high > 0 else "#3fb950"
        _social_html = (
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<span>📡</span>"
            f"<span style='color:{_sp_color};font-family:JetBrains Mono,monospace;"
            f"font-size:0.85em;font-weight:700;'>{_sp_total} alerts</span>"
            f"<span style='color:#f85149;font-size:0.65em;'>({_sp_high} high)</span>"
            f"</div>"
        )
    else:
        _social_html = (
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<span>📡</span><span style='color:#484f58;font-size:0.7em;'>No social data</span></div>"
        )

    _sizing_html = ""
    try:
        _adv_equity = paper_trader.get_portfolio_summary(_adv_prices).get("equity", 1000)
        _adv_trade_hist = paper_trader.get_trade_history()
        _adv_sizing = risk_manager.suggest_position_size(
            capital=_adv_equity, entry_price=1.0, trade_history=_adv_trade_hist)
        _sz_method = "Kelly" if _adv_sizing["method"] == "half_kelly" else "Fixed"
        _sz_amount = _adv_sizing["suggested_usd"]
        _sizing_html = (
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<span>💰</span>"
            f"<span style='color:#58a6ff;font-family:JetBrains Mono,monospace;"
            f"font-size:0.85em;font-weight:700;'>${_sz_amount:,.0f}/trade</span>"
            f"<span style='color:#484f58;font-size:0.6em;'>{_sz_method}</span>"
            f"</div>"
        )
    except Exception:
        pass

    st.markdown(
        f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;"
        f"padding:8px 16px;margin-bottom:12px;display:flex;justify-content:space-between;"
        f"align-items:center;flex-wrap:wrap;gap:8px;'>"
        f"{_bot_html}<span style='color:#21262d;'>│</span>"
        f"{_social_html}<span style='color:#21262d;'>│</span>"
        f"{_sizing_html}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── MARKET SUMMARY STRIP (Bloomberg-style) ──
    if _adv_watchlist:
        _sum_buys = [n for n, d in _adv_watchlist.items() if d.get("signal_label", "") in ("BUY", "STRONG BUY")]
        _sum_sells = [n for n, d in _adv_watchlist.items() if d.get("signal_label", "") in ("SELL", "STRONG SELL")]
        _sum_neutrals = len(_adv_watchlist) - len(_sum_buys) - len(_sum_sells)
        _sum_buy_str = ", ".join(_sum_buys[:5]) + (f" +{len(_sum_buys)-5}" if len(_sum_buys) > 5 else "") if _sum_buys else "None"
        _sum_sell_str = ", ".join(_sum_sells[:5]) + (f" +{len(_sum_sells)-5}" if len(_sum_sells) > 5 else "") if _sum_sells else "None"
        st.markdown(
            f"<div style='background:linear-gradient(90deg,#0d1117,#161b22);border:1px solid #30363d;"
            f"border-radius:8px;padding:10px 18px;margin-bottom:16px;display:flex;"
            f"justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>"
            f"<div style='display:flex;gap:20px;flex-wrap:wrap;align-items:center;'>"
            f"<span style='color:#3fb950;font-family:JetBrains Mono,monospace;font-size:0.78em;font-weight:700;'>"
            f"▲ {len(_sum_buys)} BUY</span>"
            f"<span style='color:#8b949e;font-size:0.72em;'>{_sum_buy_str}</span>"
            f"<span style='color:#30363d;'>│</span>"
            f"<span style='color:#f85149;font-family:JetBrains Mono,monospace;font-size:0.78em;font-weight:700;'>"
            f"▼ {len(_sum_sells)} SELL</span>"
            f"<span style='color:#8b949e;font-size:0.72em;'>{_sum_sell_str}</span>"
            f"<span style='color:#30363d;'>│</span>"
            f"<span style='color:#6e7681;font-family:JetBrains Mono,monospace;font-size:0.78em;'>"
            f"● {_sum_neutrals} NEUTRAL</span>"
            f"</div>"
            f"<span style='color:#484f58;font-size:0.65em;font-family:JetBrains Mono,monospace;'>"
            f"{len(_adv_watchlist)} ASSETS TRACKED</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── ASSET ADVICE CARDS ──
    st.markdown("## Today's Verdicts")

    if _adv_watchlist:
        # Load social data for verdict enrichment
        _adv_social_scores = {}
        _adv_social_alerts_map = {}
        _adv_social_summary = {}
        try:
            _adv_ss_file = NEWS_DIR / "social_sentiment.json"
            if _adv_ss_file.exists():
                _adv_ss = json.loads(_adv_ss_file.read_text(encoding="utf-8"))
                _adv_social_scores = _adv_ss.get("asset_scores", {}) if isinstance(_adv_ss, dict) else {}
                _adv_social_summary = _adv_ss.get("summary", {}) if isinstance(_adv_ss, dict) else {}
                for _al in _adv_ss.get("alerts", []):
                    _al_asset = _al.get("asset", "")
                    if _al_asset not in _adv_social_alerts_map:
                        _adv_social_alerts_map[_al_asset] = []
                    _adv_social_alerts_map[_al_asset].append(_al)
        except Exception:
            pass

        # ── Pre-load per-asset news headlines for signal cards ──
        _adv_news_cache: dict[str, list[dict]] = {}  # asset_name -> top relevant articles
        def _load_asset_news(asset_name: str) -> list[dict]:
            """Load cached news articles for an asset, return top relevant ones."""
            if asset_name in _adv_news_cache:
                return _adv_news_cache[asset_name]
            safe = asset_name.lower().replace("/", "_").replace("\\", "_").replace(" ", "_").replace("&", "&")
            candidates = [
                NEWS_DIR / f"news_{safe}.json",
                NEWS_DIR / f"news_{asset_name.lower().replace(' ', '_')}.json",
                NEWS_DIR / f"news_{asset_name.lower()}.json",
            ]
            articles = []
            for path in candidates:
                if path.exists():
                    try:
                        nd = json.loads(path.read_text(encoding="utf-8"))
                        all_arts = nd.get("articles", [])
                        # Filter relevant articles, sort by recency (published desc)
                        relevant = [a for a in all_arts if a.get("relevant")]
                        if not relevant:
                            relevant = all_arts[:5]  # fallback to first 5
                        articles = relevant[:5]  # top 5 relevant
                        break
                    except Exception:
                        pass
            _adv_news_cache[asset_name] = articles
            return articles

        def _relative_time(published_str: str) -> str:
            """Convert published date string to relative time (e.g., '2h ago')."""
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(published_str)
                now = datetime.now(timezone.utc)
                diff = now - dt
                secs = diff.total_seconds()
                if secs < 0:
                    return "just now"
                if secs < 3600:
                    return f"{int(secs // 60)}m ago"
                if secs < 86400:
                    return f"{int(secs // 3600)}h ago"
                days = int(secs // 86400)
                if days == 1:
                    return "1d ago"
                if days < 30:
                    return f"{days}d ago"
                return f"{days // 30}mo ago"
            except Exception:
                return ""

        def _extract_source(title: str) -> str:
            """Extract source name from article title (text after last ' - ')."""
            if " - " in title:
                return title.rsplit(" - ", 1)[-1].strip()
            return ""

        def _clean_title(title: str) -> str:
            """Remove source suffix from title for display."""
            if " - " in title:
                return title.rsplit(" - ", 1)[0].strip()
            return title

        # Social data is already shown in the compact status bar above — skip redundant mini-dashboard

        # ── ASSET CLASS MAPPING (all 48 assets) ──
        _ASSET_CLASS_MAP = {
            # Crypto
            "BTC-USD": "Crypto", "ETH-USD": "Crypto", "SOL-USD": "Crypto",
            "XRP-USD": "Crypto", "DOGE-USD": "Crypto", "ADA-USD": "Crypto",
            "AVAX-USD": "Crypto", "LINK-USD": "Crypto", "DOT-USD": "Crypto",
            "LTC-USD": "Crypto",
            # Metals
            "GC=F": "Metals", "SI=F": "Metals", "PL=F": "Metals", "HG=F": "Metals",
            "PA=F": "Metals",
            # Energy
            "CL=F": "Energy", "NG=F": "Energy",
            # Indices
            "^GSPC": "Indices", "^IXIC": "Indices", "^DJI": "Indices", "^RUT": "Indices",
            # Forex
            "EURUSD=X": "Forex", "GBPUSD=X": "Forex", "USDJPY=X": "Forex",
            "AUDUSD=X": "Forex", "USDCHF=X": "Forex",
            # Agriculture
            "ZW=F": "Agriculture", "ZC=F": "Agriculture",
            # Stocks
            "AAPL": "Stocks", "MSFT": "Stocks", "NVDA": "Stocks", "GOOGL": "Stocks",
            "AMZN": "Stocks", "META": "Stocks", "TSLA": "Stocks", "JPM": "Stocks",
            "BRK-B": "Stocks", "UNH": "Stocks", "V": "Stocks", "JNJ": "Stocks",
            "WMT": "Stocks", "MA": "Stocks", "XOM": "Stocks", "AMD": "Stocks",
            "NFLX": "Stocks", "INTC": "Stocks", "KO": "Stocks", "DIS": "Stocks",
        }
        _ASSET_CLASS_NAME_MAP = {
            "BTC": "Crypto", "ETH": "Crypto", "SOL": "Crypto", "XRP": "Crypto",
            "DOGE": "Crypto", "ADA": "Crypto", "AVAX": "Crypto", "LINK": "Crypto",
            "DOT": "Crypto", "LTC": "Crypto",
            "Gold": "Metals", "Silver": "Metals", "Platinum": "Metals",
            "Copper": "Metals", "Palladium": "Metals",
            "Oil": "Energy", "Natural Gas": "Energy",
            "S&P 500": "Indices", "NASDAQ": "Indices", "Dow Jones": "Indices",
            "Russell 2000": "Indices",
            "EUR/USD": "Forex", "GBP/USD": "Forex", "USD/JPY": "Forex",
            "AUD/USD": "Forex", "USD/CHF": "Forex",
            "Wheat": "Agriculture", "Corn": "Agriculture",
        }

        def _get_asset_class(asset_name, asset_data):
            """Determine asset class from ticker or name."""
            ticker = asset_data.get("ticker", "")
            cls = _ASSET_CLASS_MAP.get(ticker)
            if cls:
                return cls
            cls = _ASSET_CLASS_NAME_MAP.get(asset_name)
            if cls:
                return cls
            cat = asset_data.get("category", "").lower()
            if "crypto" in cat:
                return "Crypto"
            if "stock" in cat or "equity" in cat:
                return "Stocks"
            if "commodity" in cat:
                return "Metals"
            if "index" in cat or "indices" in cat:
                return "Indices"
            if "forex" in cat:
                return "Forex"
            return "Other"

        # ── CATEGORY TABS (TradingView-style) ──
        _all_classes = sorted(set(
            _get_asset_class(n, d) for n, d in _adv_watchlist.items()
        ))
        _tab_order = ["Stocks", "Crypto", "Metals", "Energy", "Indices", "Forex", "Agriculture", "Other"]
        _visible_tabs = [c for c in _tab_order if c in _all_classes]
        _tab_labels = ["🌐 ALL"] + [
            {"Stocks": "📈 Stocks", "Crypto": "₿ Crypto", "Metals": "🥇 Metals",
             "Energy": "⛽ Energy", "Indices": "📊 Indices", "Forex": "💱 Forex",
             "Agriculture": "🌾 Agri", "Other": "📦 Other"}.get(c, c)
            for c in _visible_tabs
        ]
        _selected_tab = st.radio(
            "Category", options=_tab_labels, horizontal=True,
            key="adv_cat_tab", label_visibility="collapsed",
        )
        # Determine selected class
        if _selected_tab == "🌐 ALL":
            _flt_classes = []
        else:
            _tab_idx = _tab_labels.index(_selected_tab) - 1
            _flt_classes = [_visible_tabs[_tab_idx]] if _tab_idx >= 0 else []

        # ── FILTER BAR (compact, inline) ──
        _flt_col1, _flt_col2 = st.columns([2, 1])
        with _flt_col1:
            _flt_signal = st.radio(
                "Signal", options=["ALL", "BUY", "SELL", "NEUTRAL"],
                horizontal=True, key="adv_flt_signal", label_visibility="collapsed",
            )
        with _flt_col2:
            _flt_sort = st.selectbox(
                "Sort", options=["Confidence ↓", "R:R Ratio ↓", "Signal Strength", "Name A-Z"],
                key="adv_flt_sort", label_visibility="collapsed",
            )

        # ── Apply filters ──
        _filtered_items = list(_adv_watchlist.items())

        # Filter by signal type
        if _flt_signal == "BUY":
            _filtered_items = [(n, d) for n, d in _filtered_items
                               if d.get("signal_label", "") in ("BUY", "STRONG BUY")]
        elif _flt_signal == "SELL":
            _filtered_items = [(n, d) for n, d in _filtered_items
                               if d.get("signal_label", "") in ("SELL", "STRONG SELL")]
        elif _flt_signal == "NEUTRAL":
            _filtered_items = [(n, d) for n, d in _filtered_items
                               if d.get("signal_label", "") == "NEUTRAL"]

        # Filter by asset class
        if _flt_classes:
            _filtered_items = [(n, d) for n, d in _filtered_items
                               if _get_asset_class(n, d) in _flt_classes]

        # Sort
        if _flt_sort == "Confidence ↓":
            _sorted_assets = sorted(
                _filtered_items,
                key=lambda x: x[1].get("confidence", {}).get("confidence_pct", 0)
                if isinstance(x[1].get("confidence"), dict) else 0,
                reverse=True,
            )
        elif _flt_sort == "R:R Ratio ↓":
            _sorted_assets = sorted(
                _filtered_items,
                key=lambda x: x[1].get("risk_reward", 0),
                reverse=True,
            )
        elif _flt_sort == "Signal Strength":
            _sorted_assets = sorted(
                _filtered_items,
                key=lambda x: abs(x[1].get("signal_score", 0)),
                reverse=True,
            )
        elif _flt_sort == "Name A-Z":
            _sorted_assets = sorted(_filtered_items, key=lambda x: x[0])
        else:
            _sorted_assets = sorted(
                _filtered_items,
                key=lambda x: x[1].get("confidence", {}).get("confidence_pct", 0)
                if isinstance(x[1].get("confidence"), dict) else 0,
                reverse=True,
            )

        # Show filter result count
        _total_count = len(_adv_watchlist)
        _shown_count = len(_sorted_assets)
        if _shown_count < _total_count:
            st.caption(f"Showing {_shown_count} of {_total_count} assets")

        for name, data in _sorted_assets:
            signal = data.get("signal_label", "NEUTRAL")
            score = data.get("signal_score", 0)
            price = data.get("price", 0)
            conf = data.get("confidence", {})
            conf_pct = conf.get("confidence_pct", 0) if isinstance(conf, dict) else 0
            rsi = data.get("rsi", 50)
            news_sent = data.get("news_sentiment", "N/A")
            reasoning = data.get("reasoning_short", "")
            target = data.get("target", 0)
            stop_loss = data.get("stop_loss", 0)
            entry = data.get("entry", price)
            rr = data.get("risk_reward", 0)
            chg = data.get("price_change_pct")

            # Get geopolitical impact for this asset
            _geo_impact = _adv_geo.get("asset_impact", {}).get(name, {})
            _geo_dir = _geo_impact.get("direction", "")
            _geo_score = _geo_impact.get("total_impact", 0)

            # Get regime multiplier
            _regime_mult = 1.0
            if _adv_regime_data and _adv_regime_data.get("multipliers"):
                _regime_mult = _adv_regime_data["multipliers"].get(name, 1.0)

            # Adjusted confidence
            _adj_conf = min(conf_pct * _regime_mult, 100)

            # Generate verdict
            if signal in ("STRONG BUY", "BUY") and _adj_conf >= 60:
                verdict = "BUY NOW"
                verdict_color = "#3fb950"
                verdict_icon = "🟢"
            elif signal in ("STRONG BUY", "BUY") and _adj_conf >= 40:
                verdict = "CONSIDER BUYING"
                verdict_color = "#3fb950"
                verdict_icon = "🔵"
            elif signal in ("STRONG SELL", "SELL") and _adj_conf >= 50:
                verdict = "AVOID / SELL"
                verdict_color = "#f85149"
                verdict_icon = "🔴"
            elif signal == "NEUTRAL" or _adj_conf < 40:
                verdict = "WAIT"
                verdict_color = "#d29922"
                verdict_icon = "🟡"
            else:
                verdict = "WAIT"
                verdict_color = "#6e7681"
                verdict_icon = "⚪"

            # Build plain-language advice
            advice_parts = []
            if signal in ("BUY", "STRONG BUY"):
                advice_parts.append(f"Technical signals are bullish (score: {score})")
            elif signal in ("SELL", "STRONG SELL"):
                advice_parts.append(f"Technical signals are bearish (score: {score})")
            else:
                advice_parts.append(f"Mixed signals (score: {score})")

            if rsi < 30:
                advice_parts.append("RSI oversold — potential bounce opportunity")
            elif rsi > 70:
                advice_parts.append("RSI overbought — be cautious, pullback possible")

            if news_sent == "BULLISH":
                advice_parts.append("News sentiment is positive")
            elif news_sent == "BEARISH":
                advice_parts.append("News sentiment is negative")

            if _geo_dir == "BULLISH" and _geo_score > 0.3:
                advice_parts.append(f"Geopolitical events are supportive (+{_geo_score:.1f})")
            elif _geo_dir == "BEARISH" and _geo_score < -0.3:
                advice_parts.append(f"Geopolitical headwinds ({_geo_score:.1f})")

            if _regime_mult > 1.05:
                advice_parts.append(f"Macro regime favors this asset (x{_regime_mult:.2f})")
            elif _regime_mult < 0.95:
                advice_parts.append(f"Macro regime works against this asset (x{_regime_mult:.2f})")

            # Social sentiment
            _card_social = _adv_social_scores.get(name, {})
            if not isinstance(_card_social, dict):
                _card_social = {}
            _card_ss_score = _card_social.get("social_score", 0)
            _card_ss_label = _card_social.get("social_label", "N/A")
            _card_ss_buzz = _card_social.get("buzz_level", "LOW")
            _card_ss_alerts = _adv_social_alerts_map.get(name, [])

            if _card_ss_label in ("VERY_BULLISH", "BULLISH"):
                advice_parts.append(f"Social sentiment is bullish ({_card_ss_score:+.2f})")
            elif _card_ss_label in ("VERY_BEARISH", "BEARISH"):
                advice_parts.append(f"Social sentiment is bearish ({_card_ss_score:+.2f})")
            if _card_ss_buzz == "HIGH":
                advice_parts.append("High social buzz — increased volatility likely")

            _advice_text = ". ".join(advice_parts) + "."

            # Social alert badge for the card
            _social_badge = ""
            if _card_ss_alerts:
                _first_alert = _card_ss_alerts[0]
                _badge_color = "#f85149" if _first_alert.get("alert_level") == "HIGH" else "#d29922"
                _badge_icon = "📡"
                _badge_text = _first_alert.get("message", "")[:60]
                _social_badge = (
                    f"<div style='background:rgba({','.join(str(int(_badge_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.1);"
                    f"border:1px solid {_badge_color};border-radius:6px;padding:6px 12px;margin-top:8px;'>"
                    f"<span style='font-size:0.85em;'>{_badge_icon}</span> "
                    f"<span style='color:{_badge_color};font-size:0.78em;font-weight:600;'>"
                    f"{_badge_text}</span></div>"
                )

            # MTF confirmation badge
            _mtf_badge = ""
            _card_conf = data.get("confidence", {})
            _card_mtf = _card_conf.get("mtf_data", {}) if isinstance(_card_conf, dict) else {}
            if _card_mtf and _card_mtf.get("available"):
                _mtf_b = _card_mtf.get("bullish_confirms", 0)
                _mtf_e = _card_mtf.get("bearish_confirms", 0)
                _mtf_tot = _mtf_b + _mtf_e
                _mtf_lbl = "BULLISH" if _mtf_b > _mtf_e else "BEARISH" if _mtf_e > _mtf_b else "MIXED"
                _mtf_clr = "#3fb950" if _mtf_lbl == "BULLISH" else "#f85149" if _mtf_lbl == "BEARISH" else "#d29922"
                _mtf_agrees = signal in ("BUY", "STRONG BUY") and _mtf_lbl == "BULLISH" or signal in ("SELL", "STRONG SELL") and _mtf_lbl == "BEARISH"
                _mtf_icon = "✅" if _mtf_agrees else "⚠️"
                _mtf_badge = (
                    f"<div style='display:inline-flex;align-items:center;gap:6px;margin-top:8px;"
                    f"background:rgba({','.join(str(int(_mtf_clr.lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.1);"
                    f"border:1px solid {_mtf_clr};border-radius:6px;padding:4px 12px;'>"
                    f"<span style='font-size:0.8em;'>{_mtf_icon}</span>"
                    f"<span style='color:{_mtf_clr};font-size:0.75em;font-weight:700;'>"
                    f"4H: {max(_mtf_b, _mtf_e)}/{_mtf_tot} {_mtf_lbl}</span></div>"
                )

            # Price change string
            _chg_str = f"{chg:+.2f}%" if chg is not None else ""
            _chg_color = "#3fb950" if (chg or 0) > 0 else "#f85149" if (chg or 0) < 0 else "#6e7681"

            # Signal style
            _sig_style = SIGNAL_STYLES.get(signal, SIGNAL_STYLES["NEUTRAL"])

            # ── CONDENSED CARD (Bloomberg-style compact + news headline + social bar) ──
            _gauge_score = max(-100, min(100, score))
            _conf_bar_color = "#3fb950" if _adj_conf >= 65 else "#d29922" if _adj_conf >= 40 else "#f85149"
            _score_bar_w = max(0, min(100, (_gauge_score + 100) / 2))  # map -100..100 to 0..100
            _asset_class = _get_asset_class(name, data)
            _class_icon = {"Stocks": "📈", "Crypto": "₿", "Metals": "🥇", "Energy": "⛽",
                           "Indices": "📊", "Forex": "💱", "Agriculture": "🌾"}.get(_asset_class, "📦")

            # ── Load top news headlines for this asset ──
            _card_news_arts = _load_asset_news(name)
            _news_headline_html = ""
            if _card_news_arts:
                _top_art = _card_news_arts[0]
                _art_title = _clean_title(_top_art.get("title", ""))
                _art_source = _extract_source(_top_art.get("title", ""))
                _art_time = _relative_time(_top_art.get("published", ""))
                _art_sent = _top_art.get("sentiment", 0)
                _art_sent_icon = "🟢" if _art_sent > 0.3 else "🔴" if _art_sent < -0.3 else "⚪"
                _art_link = _top_art.get("link", "")
                # Truncate headline to 80 chars
                _art_display = html.escape((_art_title[:77] + "...") if len(_art_title) > 80 else _art_title)
                _art_source_esc = html.escape(_art_source)
                # Make headline clickable
                if _art_link:
                    _art_safe_link = html.escape(_art_link, quote=True)
                    _art_title_el = (
                        f"<a href='{_art_safe_link}' target='_blank' rel='noopener noreferrer' "
                        f"style='color:#c9d1d9;text-decoration:none;font-size:0.72em;flex:1;"
                        f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>"
                        f"{_art_display}</a>"
                    )
                else:
                    _art_title_el = (
                        f"<span style='color:#c9d1d9;font-size:0.72em;flex:1;overflow:hidden;"
                        f"text-overflow:ellipsis;white-space:nowrap;'>{_art_display}</span>"
                    )
                # "more" badge if >2 articles exist
                _more_badge = ""
                if len(_card_news_arts) > 2:
                    _more_badge = (
                        f"<span style='color:#58a6ff;font-size:0.55em;background:rgba(88,166,255,0.1);"
                        f"padding:1px 6px;border-radius:8px;white-space:nowrap;cursor:default;'>"
                        f"+{len(_card_news_arts) - 2} more</span>"
                    )
                _news_headline_html = (
                    f"<div style='display:flex;align-items:center;gap:6px;margin:6px 0 3px 0;"
                    f"padding:5px 10px;background:rgba(88,166,255,0.06);border-radius:6px;"
                    f"border-left:3px solid rgba(88,166,255,0.4);'>"
                    f"<span style='font-size:0.7em;flex-shrink:0;'>{_art_sent_icon}</span>"
                    f"{_art_title_el}"
                    f"<span style='color:#58a6ff;font-size:0.62em;flex-shrink:0;white-space:nowrap;'>"
                    f"{_art_source_esc}</span>"
                    f"<span style='color:#6e7681;font-size:0.62em;flex-shrink:0;'>{_art_time}</span>"
                    f"</div>"
                )
                # Add 2nd headline if available (dimmer, also clickable)
                if len(_card_news_arts) > 1:
                    _art2 = _card_news_arts[1]
                    _art2_title = _clean_title(_art2.get("title", ""))
                    _art2_source = _extract_source(_art2.get("title", ""))
                    _art2_time = _relative_time(_art2.get("published", ""))
                    _art2_sent = _art2.get("sentiment", 0)
                    _art2_icon = "🟢" if _art2_sent > 0.3 else "🔴" if _art2_sent < -0.3 else "⚪"
                    _art2_display = html.escape((_art2_title[:77] + "...") if len(_art2_title) > 80 else _art2_title)
                    _art2_source_esc = html.escape(_art2_source)
                    _art2_link = _art2.get("link", "")
                    if _art2_link:
                        _art2_safe_link = html.escape(_art2_link, quote=True)
                        _art2_title_el = (
                            f"<a href='{_art2_safe_link}' target='_blank' rel='noopener noreferrer' "
                            f"style='color:#8b949e;text-decoration:none;font-size:0.68em;flex:1;"
                            f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>"
                            f"{_art2_display}</a>"
                        )
                    else:
                        _art2_title_el = (
                            f"<span style='color:#8b949e;font-size:0.68em;flex:1;overflow:hidden;"
                            f"text-overflow:ellipsis;white-space:nowrap;'>{_art2_display}</span>"
                        )
                    _news_headline_html += (
                        f"<div style='display:flex;align-items:center;gap:6px;margin:0 0 2px 0;"
                        f"padding:3px 10px;'>"
                        f"<span style='font-size:0.65em;flex-shrink:0;'>{_art2_icon}</span>"
                        f"{_art2_title_el}"
                        f"<span style='color:#58a6ff;font-size:0.58em;flex-shrink:0;opacity:0.7;'>"
                        f"{_art2_source_esc}</span>"
                        f"<span style='color:#6e7681;font-size:0.58em;flex-shrink:0;'>{_art2_time}</span>"
                        f"{_more_badge}"
                        f"</div>"
                    )

            # ── Social sentiment percentage bar (StockTwits-style) ──
            _social_bar_html = ""
            if _card_ss_score != 0 or _card_ss_label not in ("N/A", "NEUTRAL"):
                # Map score from -1..+1 to bull percentage 0..100
                _bull_pct = max(0, min(100, int((_card_ss_score + 1) * 50)))
                _bear_pct = 100 - _bull_pct
                _social_bar_html = (
                    f"<div style='display:flex;align-items:center;gap:6px;margin-top:4px;'>"
                    f"<span style='color:#8b949e;font-size:0.62em;white-space:nowrap;'>Social</span>"
                    f"<div style='flex:1;height:6px;border-radius:3px;background:#21262d;"
                    f"display:flex;overflow:hidden;'>"
                    f"<div style='width:{_bull_pct}%;background:#3fb950;'></div>"
                    f"<div style='width:{_bear_pct}%;background:#f85149;'></div>"
                    f"</div>"
                    f"<span style='color:#3fb950;font-size:0.62em;font-weight:600;'>{_bull_pct}%</span>"
                    f"<span style='color:#6e7681;font-size:0.55em;'>bull</span>"
                )
                # Buzz badge
                if _card_ss_buzz == "HIGH":
                    _social_bar_html += (
                        f"<span style='background:rgba(210,153,34,0.15);color:#d29922;"
                        f"font-size:0.55em;padding:1px 5px;border-radius:8px;font-weight:700;"
                        f"margin-left:4px;'>🔥 HOT</span>"
                    )
                _social_bar_html += "</div>"

            # ── Influencer alert badge (if high-impact influencer activity) ──
            _influencer_html = ""
            _card_inf_signals = _card_social.get("influencer_signals", [])
            _high_inf = [i for i in _card_inf_signals if i.get("alert_level") == "HIGH" and abs(i.get("impact", 0)) >= 1.5]
            if _high_inf:
                _inf_parts = []
                for _inf in _high_inf[:2]:  # max 2 influencers
                    _inf_name = _inf.get("influencer", "")
                    _inf_sent = _inf.get("sentiment", 0)
                    _inf_icon = "📈" if _inf_sent > 0.1 else "📉" if _inf_sent < -0.1 else "➡️"
                    _inf_short = _inf_name.split()[-1] if _inf_name else ""  # Last name
                    _inf_parts.append(f"{_inf_icon} {_inf_short}")
                _influencer_html = (
                    f"<span style='background:rgba(136,98,255,0.12);color:#a78bfa;"
                    f"font-size:0.62em;padding:2px 8px;border-radius:8px;margin-left:4px;"
                    f"border:1px solid rgba(136,98,255,0.25);'>"
                    f"{'  '.join(_inf_parts)}</span>"
                )

            # ── "Why Is It Moving?" — News Impact causal reasoning ──
            _impact_html = ""
            # Try: 1) scan_summary's news_impact, 2) confidence.news_impact, 3) cache file
            _card_impact = data.get("news_impact")
            if not _card_impact and isinstance(conf, dict):
                _card_impact = conf.get("news_impact")
            if not _card_impact:
                _card_impact = _adv_impact_cache.get(name)

            if _card_impact and _card_impact.get("causal_chains"):
                _imp_label = _card_impact.get("impact_label", "NEUTRAL")
                _imp_score = _card_impact.get("impact_score", 0)
                _imp_dir = _card_impact.get("direction", "NEUTRAL")
                _imp_summary = _card_impact.get("driver_summary", "")
                _imp_chains = _card_impact.get("causal_chains", [])
                _imp_regime_ctx = _card_impact.get("regime_context", "")

                # Badge class & icon
                if "TAILWIND" in _imp_label:
                    _imp_badge_cls = "impact-tailwind"
                    _imp_icon = "🔥"
                elif "HEADWIND" in _imp_label:
                    _imp_badge_cls = "impact-headwind"
                    _imp_icon = "⚡"
                else:
                    _imp_badge_cls = "impact-neutral"
                    _imp_icon = "➖"

                # Build chain pills (top 3)
                _chain_pills = ""
                for _ch in _imp_chains[:3]:
                    _ch_text = html.escape(_ch.get("chain", ""))
                    _ch_icon = _ch.get("event_icon", "")
                    _ch_count = _ch.get("article_count", 0)
                    _ch_impact = _ch.get("weighted_impact", 0)
                    _pill_cls = "chain-pill-bull" if _ch_impact > 0 else "chain-pill-bear" if _ch_impact < 0 else ""
                    _chain_pills += (
                        f"<span class='chain-pill {_pill_cls}'>"
                        f"{_ch_icon} {_ch_text}"
                        f"<span style='color:#6e7681;font-size:0.85em;margin-left:4px;'>"
                        f"({_ch_count})</span></span>"
                    )

                # Precedent (from top chain)
                _precedent_html = ""
                if _imp_chains and _imp_chains[0].get("precedent"):
                    _prec_text = html.escape(_imp_chains[0]["precedent"])
                    _precedent_html = (
                        f"<div style='color:#6e7681;font-size:0.62em;margin-top:2px;'>"
                        f"📜 Similar: {_prec_text}</div>"
                    )

                _impact_html = (
                    f"<div style='margin-top:6px;padding:8px 10px;background:rgba(22,27,34,0.6);"
                    f"border-radius:6px;border:1px solid rgba(48,54,61,0.3);'>"
                    # Header: "Why Is It Moving?" + impact badge
                    f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>"
                    f"<span style='color:#e6edf3;font-size:0.72em;font-weight:700;'>Why Is It Moving?</span>"
                    f"<span class='impact-badge {_imp_badge_cls}'>{_imp_icon} {_imp_label}</span>"
                    f"<span style='color:#6e7681;font-size:0.6em;font-family:JetBrains Mono,monospace;'>"
                    f"Impact: {_imp_score:+d}</span>"
                    f"</div>"
                    # Driver summary
                    f"<div style='color:#c9d1d9;font-size:0.7em;margin-bottom:4px;'>"
                    f"{html.escape(_imp_summary)}</div>"
                    # Causal chain pills
                    f"<div style='margin-top:2px;'>{_chain_pills}</div>"
                    # Historical precedent
                    f"{_precedent_html}"
                    # Regime context
                    f"{'<div style=\"color:#58a6ff;font-size:0.6em;margin-top:2px;\">' + html.escape(_imp_regime_ctx) + '</div>' if _imp_regime_ctx else ''}"
                    f"</div>"
                )

            st.markdown(
                f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                f"border-left:4px solid {verdict_color};border-radius:10px;"
                f"padding:14px 18px;margin-bottom:8px;'>"
                # Row 1: Name + Signal + Price (single line)
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='font-size:0.85em;'>{_class_icon}</span>"
                f"<span style='color:#e6edf3;font-size:1.05em;font-weight:700;'>{name}</span>"
                f"<span style='background:{_sig_style['bg']};color:{_sig_style['color']};"
                f"padding:1px 8px;border-radius:10px;font-size:0.68em;font-weight:700;'>{signal}</span>"
                f"<span style='color:{verdict_color};font-family:JetBrains Mono,monospace;"
                f"font-size:0.78em;font-weight:800;'>{verdict}</span>"
                f"{_influencer_html}"
                f"</div>"
                f"<div style='display:flex;align-items:baseline;gap:8px;'>"
                f"<span style='color:#e6edf3;font-family:JetBrains Mono,monospace;"
                f"font-size:1.05em;font-weight:700;'>${price:,.2f}</span>"
                f"<span style='color:{_chg_color};font-size:0.75em;font-family:JetBrains Mono,monospace;'>{_chg_str}</span>"
                f"</div></div>"
                # Row 2: Metrics strip (single line, dense)
                f"<div style='display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:2px;'>"
                f"<span style='color:#8b949e;font-size:0.72em;'>"
                f"Conf <span style='color:{_conf_bar_color};font-weight:700;'>{_adj_conf:.0f}%</span></span>"
                f"<span style='color:#8b949e;font-size:0.72em;'>"
                f"RSI <span style='color:{'#f85149' if rsi > 70 else '#3fb950' if rsi < 30 else '#e6edf3'};'>{rsi:.0f}</span></span>"
                f"<span style='color:#8b949e;font-size:0.72em;'>"
                f"T <span style='color:#3fb950;'>${target:,.0f}</span></span>"
                f"<span style='color:#8b949e;font-size:0.72em;'>"
                f"SL <span style='color:#f85149;'>${stop_loss:,.0f}</span></span>"
                f"<span style='color:#8b949e;font-size:0.72em;'>"
                f"R:R <span style='color:#e6edf3;font-weight:600;'>{rr:.1f}</span></span>"
                f"<span style='color:#8b949e;font-size:0.72em;'>"
                f"News <span style='color:{'#3fb950' if news_sent == 'BULLISH' else '#f85149' if news_sent == 'BEARISH' else '#6e7681'};'>"
                f"{news_sent}</span></span>"
                f"</div>"
                # Row 3: News headline (Benzinga "Why Is It Moving?" style)
                f"{_news_headline_html}"
                # Row 4: Social sentiment bar
                f"{_social_bar_html}"
                # Row 5: News Impact — causal reasoning
                f"{_impact_html}"
                # Row 6: AI Explanation (smart narrative)
                f"<div style='color:#8b949e;font-size:0.72em;margin-top:4px;'>"
                f"💡 {signal_explainer.explain_signal(asset_name=name, signal=signal, score=score, confidence=_adj_conf, price=price, rsi=rsi, target=target, stop_loss=stop_loss, news_sentiment=news_sent, social_score=_card_ss_score, social_buzz=_card_ss_buzz, regime=_regime, geo_risk=_geo_risk, reasoning=reasoning)}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # ── QUICK-TRADE BUTTONS (below each card) ──
            _qt_cols = st.columns([1, 1, 1, 1, 2])
            _qt_direction = "long" if signal in ("BUY", "STRONG BUY") else "short" if signal in ("SELL", "STRONG SELL") else "long"
            _qt_ticker = data.get("ticker", "")
            with _qt_cols[0]:
                if st.button(f"⚡ Quick {_qt_direction.upper()}", key=f"qt_{name}", use_container_width=True):
                    try:
                        _qt_equity = paper_trader.get_portfolio_summary(_adv_prices).get("equity", 1000)
                        _qt_sizing = risk_manager.suggest_position_size(
                            capital=_qt_equity, entry_price=price,
                            trade_history=paper_trader.get_trade_history(),
                        )
                        _qt_amount = min(_qt_sizing["suggested_usd"], _qt_equity * 0.2)
                        _qt_result = paper_trader.open_position(
                            asset=name, ticker=_qt_ticker, direction=_qt_direction,
                            usd_amount=_qt_amount, price=price,
                            stop_loss=stop_loss if stop_loss else None,
                            take_profit=target if target else None,
                            tags=["quick_trade", signal.lower().replace(" ", "_")],
                            signal_hint=signal,
                        )
                        if "error" in _qt_result:
                            st.error(_qt_result["error"])
                        else:
                            st.success(f"Opened {_qt_direction} {name} — ${_qt_amount:,.2f} @ ${price:,.2f}")
                    except Exception as _qt_err:
                        st.error(f"Trade failed: {_qt_err}")
            with _qt_cols[1]:
                if st.button("📈 Chart", key=f"qt_chart_{name}", use_container_width=True):
                    _navigate_to("charts", chart_asset=name)
            with _qt_cols[2]:
                if st.button("📋 Details", key=f"qt_detail_{name}", use_container_width=True):
                    for _f in research_files:
                        if name.lower() in _f.name.lower() and "_signal_" in _f.name.lower():
                            _navigate_to("research", selected_research=str(_f))
            with _qt_cols[3]:
                asset_link_button(name, f"adv_{name}")

            # ── AGREE / DISAGREE BUTTONS (prediction game) ──
            _pg_existing_vote = _pg.get_vote(name)
            if _pg_existing_vote:
                _pg_vote_label = "✅ You Agreed" if _pg_existing_vote["agrees"] else "❌ You Disagreed"
                _pg_vote_color = "#3fb950" if _pg_existing_vote["agrees"] else "#f85149"
                st.markdown(
                    f"<div style='background:rgba({','.join(str(int(_pg_vote_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.08);"
                    f"border:1px solid {_pg_vote_color};border-radius:8px;padding:8px 16px;"
                    f"text-align:center;margin-bottom:16px;'>"
                    f"<span style='color:{_pg_vote_color};font-family:JetBrains Mono,monospace;"
                    f"font-size:0.85em;font-weight:600;'>{_pg_vote_label} with AI's {signal} call</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                _pg_agree_cols = st.columns([1, 1, 4])
                with _pg_agree_cols[0]:
                    if st.button("👍 Agree", key=f"pg_agree_{name}", use_container_width=True):
                        _pg.record_vote(name, signal, agrees=True, ai_confidence=_adj_conf)
                        st.rerun()
                with _pg_agree_cols[1]:
                    if st.button("👎 Disagree", key=f"pg_disagree_{name}", use_container_width=True):
                        _pg.record_vote(name, signal, agrees=False, ai_confidence=_adj_conf)
                        st.rerun()
                with _pg_agree_cols[2]:
                    st.markdown(
                        "<span style='color:#6e7681;font-size:0.78em;'>Do you agree with this signal? "
                        "Vote and see who's right tomorrow!</span>",
                        unsafe_allow_html=True,
                    )

        # ── QUICK SUMMARY BOX ──
        st.divider()
        _buy_now = [n for n, d in _sorted_assets
                    if d.get("signal_label", "") in ("BUY", "STRONG BUY")
                    and (d.get("confidence", {}).get("confidence_pct", 0) if isinstance(d.get("confidence"), dict) else 0) >= 60]
        _consider = [n for n, d in _sorted_assets
                     if d.get("signal_label", "") in ("BUY", "STRONG BUY")
                     and 40 <= (d.get("confidence", {}).get("confidence_pct", 0) if isinstance(d.get("confidence"), dict) else 0) < 60]
        _avoid = [n for n, d in _sorted_assets
                  if d.get("signal_label", "") in ("SELL", "STRONG SELL")]

        st.markdown(
            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
            f"border-radius:10px;padding:18px 22px;'>"
            f"<div style='color:#e6edf3;font-size:1em;font-weight:700;margin-bottom:10px;'>"
            f"Quick Summary</div>"
            f"<div style='color:#3fb950;font-size:0.9em;margin-bottom:6px;'>"
            f"BUY NOW: {', '.join(_buy_now) if _buy_now else 'None — no high-confidence buys today'}</div>"
            f"<div style='color:#3fb950;font-size:0.9em;margin-bottom:6px;'>"
            f"CONSIDER: {', '.join(_consider) if _consider else 'None'}</div>"
            f"<div style='color:#f85149;font-size:0.9em;margin-bottom:6px;'>"
            f"AVOID: {', '.join(_avoid) if _avoid else 'None'}</div>"
            f"<div style='color:#6e7681;font-size:0.78em;margin-top:10px;'>"
            f"Advice is based on technical analysis, news sentiment, social pulse, geopolitical events, and macro regime. "
            f"Always do your own research before trading.</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── SIGNALS YOU IGNORED (regret engine) ──
        _pg_ignored = _pg.get_signals_you_ignored(limit=3)
        if _pg_ignored:
            st.markdown(
                "<div style='background:#161b22;border:1px solid #d29922;border-radius:10px;"
                "padding:18px 22px;margin-top:16px;'>"
                "<div style='color:#d29922;font-size:1em;font-weight:700;margin-bottom:10px;'>"
                "💡 Signals You Ignored That Hit</div>"
                + "".join(
                    f"<div style='color:#8b949e;font-size:0.85em;margin-bottom:6px;'>"
                    f"<span style='color:#e6edf3;font-weight:600;'>{ig['asset']}</span> "
                    f"— {ig['signal']} on {ig['date']} "
                    f"<span style='color:{'#3fb950' if ig['actual_move_pct'] >= 0 else '#f85149'};'>"
                    f"moved {ig['actual_move_pct']:+.1f}%</span> "
                    f"(you didn't vote)</div>"
                    for ig in _pg_ignored
                )
                + "<div style='color:#6e7681;font-size:0.72em;margin-top:8px;'>"
                "Vote on today's signals so you never miss a correct call!</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # ── TODAY'S VOTE SUMMARY ──
        if _pg_today_votes:
            _pg_agree_count = sum(1 for v in _pg_today_votes if v["agrees"])
            _pg_disagree_count = len(_pg_today_votes) - _pg_agree_count
            st.markdown(
                f"<div style='background:#161b22;border:1px solid #58a6ff;border-radius:10px;"
                f"padding:14px 22px;margin-top:12px;'>"
                f"<div style='color:#58a6ff;font-family:JetBrains Mono,monospace;font-size:0.8em;'>"
                f"🎯 TODAY'S VOTES: {len(_pg_today_votes)} signals "
                f"({_pg_agree_count} agree, {_pg_disagree_count} disagree) "
                f"— Check back tomorrow to see who was right!</div></div>",
                unsafe_allow_html=True,
            )

    else:
        st.info("No watchlist data available. Run a scan first to get trading signals.")


# ===========================
# ASSET DETAIL — Single-Asset Deep Dive
# ===========================
elif view == "asset_detail":
    _da_name = st.session_state.get("detail_asset", "")
    if not _da_name:
        st.warning("No asset selected. Go to the Daily Advisor or Watchlist to pick an asset.")
    else:
        _da_watchlist = load_watchlist_summary()
        _da_data = _da_watchlist.get(_da_name, {})
        _da_ticker = _da_data.get("ticker", "")

        # ── Fetch LIVE price (same pattern as Daily Advisor) ──
        _da_live_price = None
        _da_live_change = None
        if _da_ticker:
            try:
                _da_price_dict = fetch_live_prices({_da_name: _da_data})
                if _da_name in _da_price_dict and _da_price_dict[_da_name]:
                    _da_live_price = _da_price_dict[_da_name]
                    # Also compute daily change from live price vs previous close
                    _da_daily_changes = st.session_state.get("_live_daily_changes", {})
                    if _da_name in _da_daily_changes:
                        _da_live_change = _da_daily_changes[_da_name]
            except Exception:
                pass

        render_page_header(f"{_da_name}", view_key="asset_detail", subtitle=f"Ticker: {_da_ticker}")
        render_page_info("asset_detail")

        # ── Signal Header Card ──
        _da_signal = _da_data.get("signal_label", "NEUTRAL")
        _da_score = _da_data.get("signal_score", 0)
        _da_conf_raw = _da_data.get("confidence", {})
        _da_conf_pct = _da_conf_raw.get("confidence_pct", 0) if isinstance(_da_conf_raw, dict) else 0
        _da_price = _da_live_price if _da_live_price else _da_data.get("price", 0)
        _da_change = _da_live_change if _da_live_change is not None else _da_data.get("daily_change_pct", 0)
        _da_ss = SIGNAL_STYLES.get(_da_signal, SIGNAL_STYLES["NEUTRAL"])
        _da_change_color = "#3fb950" if _da_change >= 0 else "#f85149"
        _da_change_icon = "▲" if _da_change >= 0 else "▼"

        st.markdown(
            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
            f"border-left:5px solid {_da_ss['bg']};border-radius:10px;"
            f"padding:20px 24px;margin-bottom:16px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div>"
            f"<span style='background:{_da_ss['bg']};color:{_da_ss['color']};"
            f"padding:6px 16px;border-radius:6px;font-weight:800;font-size:1.1em;'>"
            f"{_da_signal}</span>"
            f"<span style='color:#8b949e;font-size:0.85em;margin-left:14px;'>"
            f"Score: {_da_score}/100 &middot; Confidence: {_da_conf_pct:.0f}%</span>"
            f"</div>"
            f"<div style='text-align:right;'>"
            f"<div style='color:#e6edf3;font-family:JetBrains Mono,monospace;"
            f"font-size:1.4em;font-weight:700;'>${_da_price:,.2f}</div>"
            f"<div style='color:{_da_change_color};font-family:JetBrains Mono,monospace;"
            f"font-size:0.9em;'>{_da_change_icon} {_da_change:+.2f}%</div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )

        # ── Quick-Trade Buttons ──
        _da_dir = "long" if _da_signal in ("BUY", "STRONG BUY") else "short" if _da_signal in ("SELL", "STRONG SELL") else "long"
        _da_qt1, _da_qt2, _da_qt3 = st.columns(3)
        with _da_qt1:
            if st.button(f"⚡ Quick {_da_dir.upper()}", key="da_qt", use_container_width=True):
                try:
                    _da_eq = paper_trader.get_portfolio_summary({}).get("equity", 1000)
                    _da_sizing = risk_manager.suggest_position_size(
                        capital=_da_eq, entry_price=_da_price,
                        trade_history=paper_trader.get_trade_history(),
                    )
                    _da_amt = min(_da_sizing["suggested_usd"], _da_eq * 0.2)
                    _da_sl = _da_data.get("support", None)
                    _da_tp = _da_data.get("target", None)
                    _da_res = paper_trader.open_position(
                        asset=_da_name, ticker=_da_ticker, direction=_da_dir,
                        usd_amount=_da_amt, price=_da_price,
                        stop_loss=_da_sl, take_profit=_da_tp,
                        tags=["quick_trade", _da_signal.lower().replace(" ", "_")],
                        signal_hint=_da_signal,
                    )
                    if "error" in _da_res:
                        st.error(_da_res["error"])
                    else:
                        st.success(f"Opened {_da_dir} {_da_name} — ${_da_amt:,.2f} @ ${_da_price:,.2f}")
                except Exception as _da_err:
                    st.error(f"Trade failed: {_da_err}")
        with _da_qt2:
            if st.button("📈 Full Chart", key="da_chart", use_container_width=True):
                _navigate_to("charts", chart_asset=_da_name)
        with _da_qt3:
            if st.button("📋 Signal Report", key="da_report", use_container_width=True):
                for _f in research_files:
                    if _da_name.lower() in _f.name.lower() and "_signal_" in _f.name.lower():
                        _navigate_to("research", selected_research=str(_f))

        # ── Tabbed Content ──
        _da_tab_chart, _da_tab_news, _da_tab_social, _da_tab_impact, _da_tab_fund, _da_tab_trades = st.tabs(
            ["Chart", "News", "Social", "Impact", "Fundamentals", "Trades"]
        )

        with _da_tab_chart:
            if _da_ticker:
                _da_chart_ok = False
                for _da_chart_attempt in range(2):  # retry once on failure
                    try:
                        _da_df = chart_engine.fetch_ohlcv(_da_ticker, period="3mo", interval="1d")
                        if _da_df is None or _da_df.empty:
                            if _da_chart_attempt == 0:
                                import time as _t; _t.sleep(1)
                                continue  # retry
                            st.info("No chart data available for this asset. yfinance may be temporarily unavailable.")
                            _da_chart_ok = True
                            break
                        _da_df = chart_engine.add_indicators(_da_df)
                        _da_fig = chart_engine.build_candlestick_chart(
                            _da_df, title=f"{_da_name} ({_da_ticker})", height=450
                        )
                        st.plotly_chart(_da_fig, use_container_width=True)
                        _da_macd_fig = chart_engine.build_macd_chart(_da_df)
                        st.plotly_chart(_da_macd_fig, use_container_width=True)
                        _da_chart_ok = True
                        break
                    except Exception as _da_ch_err:
                        if _da_chart_attempt == 0:
                            import time as _t; _t.sleep(1)
                            continue  # retry once
                        st.warning(f"Chart load failed: {_da_ch_err}")
                        _da_chart_ok = True
                        break
                if not _da_chart_ok:
                    st.info("Chart data temporarily unavailable. Please refresh the page.")
            else:
                st.info("No ticker found for this asset.")

        with _da_tab_news:
            _da_news_key = _da_name.lower().replace(" ", "_").replace("/", "_").replace("&", "")
            _da_news = load_news(_da_news_key)
            if _da_news and _da_news.get("articles"):
                _da_articles = _da_news["articles"][:25]
                _da_sent = _da_news.get("sentiment_score", 0)
                _da_sent_color = "#3fb950" if _da_sent > 0.1 else "#f85149" if _da_sent < -0.1 else "#d29922"
                _da_rel_count = _da_news.get("relevant_count", 0)
                _da_art_count = _da_news.get("article_count", 0)
                _da_src_count = _da_news.get("sources_checked", 0)
                # Sentiment bar (bull/bear percentage)
                _da_bull_arts = len([a for a in _da_articles if a.get("sentiment", 0) > 0])
                _da_bear_arts = len([a for a in _da_articles if a.get("sentiment", 0) < 0])
                _da_neut_arts = len(_da_articles) - _da_bull_arts - _da_bear_arts
                _da_bull_pct = int(_da_bull_arts * 100 / max(1, len(_da_articles)))
                _da_bear_pct = int(_da_bear_arts * 100 / max(1, len(_da_articles)))
                st.markdown(
                    f"<div style='background:#161b22;border-radius:8px;padding:14px 16px;margin-bottom:12px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
                    f"<div>"
                    f"<span style='color:#8b949e;font-size:0.8em;'>Sentiment: </span>"
                    f"<span style='color:{_da_sent_color};font-weight:700;font-family:JetBrains Mono,monospace;'>"
                    f"{_da_sent:+.2f}</span></div>"
                    f"<div style='color:#6e7681;font-size:0.7em;'>"
                    f"{_da_src_count} sources · {_da_rel_count} relevant · {_da_art_count} total</div>"
                    f"</div>"
                    # Sentiment percentage bar
                    f"<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<span style='color:#3fb950;font-size:0.7em;font-weight:600;'>{_da_bull_pct}%</span>"
                    f"<div style='flex:1;height:8px;border-radius:4px;background:#21262d;"
                    f"display:flex;overflow:hidden;'>"
                    f"<div style='width:{_da_bull_pct}%;background:#3fb950;'></div>"
                    f"<div style='width:{100 - _da_bull_pct - _da_bear_pct}%;background:#6e7681;opacity:0.3;'></div>"
                    f"<div style='width:{_da_bear_pct}%;background:#f85149;'></div>"
                    f"</div>"
                    f"<span style='color:#f85149;font-size:0.7em;font-weight:600;'>{_da_bear_pct}%</span>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # Group articles by date
                _da_date_groups: dict[str, list] = {}
                for _art in _da_articles:
                    _art_pub_raw = _art.get("published", "")
                    try:
                        from email.utils import parsedate_to_datetime as _da_pdt
                        _art_dt = _da_pdt(_art_pub_raw)
                        _art_date_key = _art_dt.strftime("%b %d, %Y")
                    except Exception:
                        _art_date_key = "Unknown Date"
                    if _art_date_key not in _da_date_groups:
                        _da_date_groups[_art_date_key] = []
                    _da_date_groups[_art_date_key].append(_art)
                # Render date-grouped articles
                for _dg_date, _dg_arts in _da_date_groups.items():
                    st.markdown(
                        f"<div style='color:#58a6ff;font-size:0.72em;font-weight:600;"
                        f"padding:8px 0 4px 0;border-bottom:1px solid #21262d;margin-bottom:4px;'>"
                        f"📅 {_dg_date} ({len(_dg_arts)} articles)</div>",
                        unsafe_allow_html=True,
                    )
                    for _art in _dg_arts:
                        _art_raw_title = _art.get("title", "No title")
                        _art_title_clean = _art_raw_title.rsplit(" - ", 1)[0] if " - " in _art_raw_title else _art_raw_title
                        _art_title_esc = html.escape(_art_title_clean)
                        _art_source_name = _art_raw_title.rsplit(" - ", 1)[-1].strip() if " - " in _art_raw_title else _art.get("source", "")
                        _art_src_esc = html.escape(_art_source_name[:30])
                        _art_link = _art.get("link", "").strip()
                        _art_s = _art.get("sentiment", 0)
                        _art_relevant = _art.get("relevant", False)
                        _art_s_icon = "🟢" if _art_s > 0.3 else "🔴" if _art_s < -0.3 else "⚪"
                        _art_border = "border-left:3px solid #58a6ff;" if _art_relevant else ""
                        _art_pub_str = html.escape(_art.get("published", "")[:25])
                        # Clickable title
                        if _art_link:
                            _safe_link = html.escape(_art_link, quote=True)
                            _art_title_el = (
                                f"<a href='{_safe_link}' target='_blank' rel='noopener noreferrer' "
                                f"style='color:#e6edf3;text-decoration:none;font-size:0.85em;'>"
                                f"{_art_title_esc}</a>"
                            )
                        else:
                            _art_title_el = f"<span style='color:#e6edf3;font-size:0.85em;'>{_art_title_esc}</span>"
                        st.markdown(
                            f"<div style='background:#0d1117;{_art_border}padding:8px 12px;margin-bottom:3px;"
                            f"border-radius:4px;display:flex;align-items:center;gap:8px;'>"
                            f"<span style='font-size:0.72em;flex-shrink:0;'>{_art_s_icon}</span>"
                            f"<div style='flex:1;'>"
                            f"<div>{_art_title_el}</div>"
                            f"<div style='display:flex;gap:8px;align-items:center;margin-top:2px;'>"
                            f"<span style='color:#58a6ff;font-size:0.68em;font-weight:600;'>{_art_src_esc}</span>"
                            f"<span style='color:#484f58;font-size:0.62em;'>{_art_pub_str}</span>"
                            f"</div></div></div>",
                            unsafe_allow_html=True,
                        )
            else:
                st.info(f"No recent news found for {_da_name}. Run a news scan to populate.")

        with _da_tab_social:
            _da_social_file = NEWS_DIR / "social_sentiment.json"
            if _da_social_file.exists():
                try:
                    _da_social_data = json.loads(_da_social_file.read_text(encoding="utf-8"))
                    _da_asset_scores = _da_social_data.get("asset_scores", {})
                    _da_as = _da_asset_scores.get(_da_name, {})
                    if _da_as:
                        _da_soc_score = _da_as.get("social_score", 0)
                        _da_soc_buzz = _da_as.get("buzz_level", "LOW")
                        _da_soc_inf = _da_as.get("influencer_score", 0)
                        _da_soc_reddit = _da_as.get("reddit_score", 0)
                        _da_soc_color = "#3fb950" if _da_soc_score > 0.1 else "#f85149" if _da_soc_score < -0.1 else "#d29922"
                        _da_buzz_color = "#3fb950" if _da_soc_buzz == "HIGH" else "#d29922" if _da_soc_buzz == "MEDIUM" else "#484f58"

                        _sc1, _sc2, _sc3, _sc4 = st.columns(4)
                        with _sc1:
                            st.markdown(
                                f"<div style='background:#161b22;border-radius:8px;padding:14px;text-align:center;'>"
                                f"<div style='color:#8b949e;font-size:0.7em;'>SOCIAL SCORE</div>"
                                f"<div style='color:{_da_soc_color};font-size:1.4em;font-weight:800;"
                                f"font-family:JetBrains Mono,monospace;'>{_da_soc_score:+.2f}</div></div>",
                                unsafe_allow_html=True,
                            )
                        with _sc2:
                            st.markdown(
                                f"<div style='background:#161b22;border-radius:8px;padding:14px;text-align:center;'>"
                                f"<div style='color:#8b949e;font-size:0.7em;'>BUZZ</div>"
                                f"<div style='color:{_da_buzz_color};font-size:1.4em;font-weight:800;'>"
                                f"{_da_soc_buzz}</div></div>",
                                unsafe_allow_html=True,
                            )
                        with _sc3:
                            _inf_color = "#3fb950" if _da_soc_inf > 0 else "#f85149" if _da_soc_inf < 0 else "#484f58"
                            st.markdown(
                                f"<div style='background:#161b22;border-radius:8px;padding:14px;text-align:center;'>"
                                f"<div style='color:#8b949e;font-size:0.7em;'>INFLUENCER</div>"
                                f"<div style='color:{_inf_color};font-size:1.4em;font-weight:800;"
                                f"font-family:JetBrains Mono,monospace;'>{_da_soc_inf:+.2f}</div></div>",
                                unsafe_allow_html=True,
                            )
                        with _sc4:
                            _red_color = "#3fb950" if _da_soc_reddit > 0 else "#f85149" if _da_soc_reddit < 0 else "#484f58"
                            st.markdown(
                                f"<div style='background:#161b22;border-radius:8px;padding:14px;text-align:center;'>"
                                f"<div style='color:#8b949e;font-size:0.7em;'>REDDIT</div>"
                                f"<div style='color:{_red_color};font-size:1.4em;font-weight:800;"
                                f"font-family:JetBrains Mono,monospace;'>{_da_soc_reddit:+.2f}</div></div>",
                                unsafe_allow_html=True,
                            )

                        # Influencer mentions
                        _da_inf_mentions = _da_social_data.get("influencer_mentions", [])
                        _da_my_mentions = [m for m in _da_inf_mentions if _da_name.lower() in str(m.get("assets_affected", [])).lower()]
                        if _da_my_mentions:
                            st.markdown("#### Recent Influencer Mentions")
                            for _m in _da_my_mentions[:5]:
                                _m_who = _m.get("influencer", "")
                                _m_headline = _m.get("headline", "")
                                _m_sent = _m.get("sentiment", "neutral")
                                _m_color = "#3fb950" if _m_sent == "bullish" else "#f85149" if _m_sent == "bearish" else "#d29922"
                                st.markdown(
                                    f"<div style='background:#0d1117;padding:8px 12px;margin-bottom:4px;"
                                    f"border-radius:4px;border-left:3px solid {_m_color};'>"
                                    f"<span style='color:#e6edf3;font-weight:600;'>{_m_who}</span>"
                                    f"<span style='color:#8b949e;'> &middot; </span>"
                                    f"<span style='color:#8b949e;font-size:0.85em;'>{_m_headline}</span></div>",
                                    unsafe_allow_html=True,
                                )
                    else:
                        st.info(f"No social data for {_da_name}. Run a social scan.")
                except Exception:
                    st.info("Social sentiment data unavailable.")
            else:
                st.info("No social sentiment data. Run a social scan from the Advisor page.")

        with _da_tab_impact:
            # ── Impact Analysis — causal news-to-price reasoning ──
            # Load impact data: from scan summary, confidence dict, or cache
            _da_impact = _da_data.get("news_impact")
            if not _da_impact and isinstance(_da_conf_raw, dict):
                _da_impact = _da_conf_raw.get("news_impact")
            if not _da_impact:
                _imp_cache_file = PROJECT_ROOT / "src" / "data" / "news_impact.json"
                if _imp_cache_file.exists():
                    try:
                        _imp_cache_data = json.loads(_imp_cache_file.read_text(encoding="utf-8"))
                        _da_impact = _imp_cache_data.get(_da_name)
                    except Exception:
                        pass

            if _da_impact and _da_impact.get("causal_chains"):
                _dai_score = _da_impact.get("impact_score", 0)
                _dai_label = _da_impact.get("impact_label", "NEUTRAL")
                _dai_dir = _da_impact.get("direction", "NEUTRAL")
                _dai_summary = _da_impact.get("driver_summary", "")
                _dai_chains = _da_impact.get("causal_chains", [])
                _dai_regime_ctx = _da_impact.get("regime_context", "")
                _dai_regime_name = _da_impact.get("regime_name", "NEUTRAL")
                _dai_regime_mult = _da_impact.get("regime_multiplier", 1.0)
                _dai_events = _da_impact.get("events_detected", {})
                _dai_total_arts = _da_impact.get("total_geo_articles", 0)
                _dai_sentiment = _da_impact.get("news_sentiment", 0)

                # Impact Score Gauge (-100 to +100)
                _dai_bar_pct = max(0, min(100, (_dai_score + 100) / 2))  # map to 0..100
                _dai_color = "#3fb950" if _dai_score > 20 else "#f85149" if _dai_score < -20 else "#d29922"
                _dai_bg = "rgba(46,160,67,0.1)" if _dai_score > 20 else "rgba(218,54,51,0.1)" if _dai_score < -20 else "rgba(210,153,34,0.1)"

                st.markdown(
                    f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    f"border-radius:10px;padding:20px;margin-bottom:16px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;'>"
                    f"<div>"
                    f"<span style='color:#e6edf3;font-size:1.1em;font-weight:700;'>News Impact Score</span>"
                    f"<span class='impact-badge {'impact-tailwind' if 'TAILWIND' in _dai_label else 'impact-headwind' if 'HEADWIND' in _dai_label else 'impact-neutral'}'>"
                    f"{'🔥' if 'TAILWIND' in _dai_label else '⚡' if 'HEADWIND' in _dai_label else '➖'} {_dai_label}</span>"
                    f"</div>"
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:1.6em;"
                    f"font-weight:800;color:{_dai_color};'>{_dai_score:+d}</span>"
                    f"</div>"
                    # Gauge bar
                    f"<div style='position:relative;height:12px;background:#21262d;border-radius:6px;overflow:hidden;margin-bottom:8px;'>"
                    f"<div style='position:absolute;left:50%;top:0;bottom:0;width:2px;background:#484f58;'></div>"
                    f"<div style='width:{_dai_bar_pct}%;height:100%;background:linear-gradient(90deg,#f85149,#d29922 40%,#d29922 60%,#3fb950);border-radius:6px;'></div>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;font-size:0.65em;color:#6e7681;margin-bottom:12px;'>"
                    f"<span>-100 HEADWIND</span><span>0 NEUTRAL</span><span>TAILWIND +100</span></div>"
                    # Driver summary
                    f"<div style='color:#c9d1d9;font-size:0.85em;padding:10px;background:{_dai_bg};"
                    f"border-radius:6px;border-left:3px solid {_dai_color};'>"
                    f"{html.escape(_dai_summary)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Active Event Drivers
                if _dai_events:
                    st.markdown("#### Active Event Drivers")
                    _evt_cols = st.columns(min(len(_dai_events), 4))
                    _evt_icons = {
                        "WAR_CONFLICT": "🔴", "SANCTIONS": "🟠", "TARIFFS_TRADE": "🟡",
                        "CENTRAL_BANK": "🏦", "ELECTIONS": "🗳️", "ENERGY_SUPPLY": "⛽",
                        "NATURAL_DISASTER": "🌊", "PANDEMIC_HEALTH": "🦠",
                    }
                    _evt_labels = {
                        "WAR_CONFLICT": "Military Conflict", "SANCTIONS": "Sanctions",
                        "TARIFFS_TRADE": "Trade/Tariffs", "CENTRAL_BANK": "Central Bank",
                        "ELECTIONS": "Political", "ENERGY_SUPPLY": "Energy Supply",
                        "NATURAL_DISASTER": "Natural Disaster", "PANDEMIC_HEALTH": "Health Crisis",
                    }
                    for _ei, (_etype, _ecount) in enumerate(_dai_events.items()):
                        with _evt_cols[_ei % len(_evt_cols)]:
                            _e_icon = _evt_icons.get(_etype, "📌")
                            _e_label = _evt_labels.get(_etype, _etype.replace("_", " ").title())
                            st.markdown(
                                f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                                f"border-radius:8px;padding:12px;text-align:center;'>"
                                f"<div style='font-size:1.6em;'>{_e_icon}</div>"
                                f"<div style='color:#e6edf3;font-weight:600;font-size:0.85em;margin-top:4px;'>{_e_label}</div>"
                                f"<div style='color:#58a6ff;font-family:JetBrains Mono,monospace;"
                                f"font-size:1.2em;font-weight:700;margin-top:4px;'>{_ecount}</div>"
                                f"<div style='color:#6e7681;font-size:0.7em;'>articles</div>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                # Causal Chains
                if _dai_chains:
                    st.markdown("#### Causal Reasoning Chains")
                    for _ci, _chain in enumerate(_dai_chains):
                        _ch_impact = _chain.get("weighted_impact", 0)
                        _ch_icon = _chain.get("event_icon", "📌")
                        _ch_label = _chain.get("event_label", "")
                        _ch_text = _chain.get("chain", "")
                        _ch_count = _chain.get("article_count", 0)
                        _ch_prec = _chain.get("precedent", "")
                        _ch_color = "#3fb950" if _ch_impact > 0 else "#f85149" if _ch_impact < 0 else "#6e7681"
                        _ch_dir = "↑" if _ch_impact > 0 else "↓" if _ch_impact < 0 else "→"

                        st.markdown(
                            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                            f"border-left:4px solid {_ch_color};border-radius:8px;"
                            f"padding:14px 16px;margin-bottom:8px;'>"
                            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                            f"<div style='display:flex;align-items:center;gap:8px;'>"
                            f"<span style='font-size:1.1em;'>{_ch_icon}</span>"
                            f"<span style='color:#e6edf3;font-weight:600;'>{html.escape(_ch_label)}</span>"
                            f"<span style='color:#6e7681;font-size:0.8em;'>({_ch_count} articles)</span>"
                            f"</div>"
                            f"<span style='color:{_ch_color};font-family:JetBrains Mono,monospace;"
                            f"font-size:1.1em;font-weight:700;'>{_ch_dir} {_ch_impact:+.3f}</span>"
                            f"</div>"
                            # Chain explanation
                            f"<div style='color:#c9d1d9;font-size:0.88em;padding:8px 12px;"
                            f"background:rgba(22,27,34,0.8);border-radius:6px;margin-bottom:4px;'>"
                            f"🔗 {html.escape(_ch_text)}</div>"
                            # Precedent
                            f"{'<div style=\"color:#6e7681;font-size:0.75em;margin-top:4px;\">📜 ' + html.escape(_ch_prec) + '</div>' if _ch_prec else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                # Macro Regime Context
                if _dai_regime_ctx:
                    _regime_colors_map = {
                        "RISK_ON": "#3fb950", "RISK_OFF": "#f85149", "INFLATIONARY": "#d29922",
                        "DEFLATIONARY": "#58a6ff", "HIGH_VOLATILITY": "#a371f7", "NEUTRAL": "#6e7681",
                    }
                    _rg_col = _regime_colors_map.get(_dai_regime_name, "#6e7681")
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-radius:8px;padding:14px 16px;margin-top:8px;'>"
                        f"<div style='display:flex;align-items:center;gap:8px;'>"
                        f"<span style='color:#8b949e;font-size:0.85em;'>Macro Regime:</span>"
                        f"<span style='color:{_rg_col};font-weight:700;'>"
                        f"{_dai_regime_name.replace('_', ' ').title()}</span>"
                        f"<span style='color:#6e7681;font-size:0.8em;'>(x{_dai_regime_mult:.2f} multiplier)</span>"
                        f"</div>"
                        f"<div style='color:#c9d1d9;font-size:0.82em;margin-top:6px;'>"
                        f"{html.escape(_dai_regime_ctx)}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            else:
                st.info(
                    f"No impact analysis available for {_da_name}. "
                    "Run a brain scan to generate causal news-to-price reasoning."
                )

        with _da_tab_fund:
            if _da_ticker:
                try:
                    _da_perf = fundamentals.get_price_performance(_da_ticker)
                    if _da_perf:
                        _perf_cols = st.columns(4)
                        _perf_items = [
                            ("1 Week", _da_perf.get("1w", 0)),
                            ("1 Month", _da_perf.get("1m", 0)),
                            ("3 Months", _da_perf.get("3m", 0)),
                            ("1 Year", _da_perf.get("1y", 0)),
                        ]
                        for _pi, (_pl, _pv) in enumerate(_perf_items):
                            with _perf_cols[_pi]:
                                _pc = "#3fb950" if _pv >= 0 else "#f85149"
                                st.markdown(
                                    f"<div style='background:#161b22;border-radius:8px;padding:14px;text-align:center;'>"
                                    f"<div style='color:#8b949e;font-size:0.7em;'>{_pl}</div>"
                                    f"<div style='color:{_pc};font-size:1.3em;font-weight:700;"
                                    f"font-family:JetBrains Mono,monospace;'>{_pv:+.1f}%</div></div>",
                                    unsafe_allow_html=True,
                                )

                    _da_fund = fundamentals.get_fundamentals(_da_ticker)
                    if _da_fund:
                        st.markdown("#### Key Metrics")
                        _fund_rows = []
                        for _fk, _fv in _da_fund.items():
                            if _fk not in ("name", "ticker", "sector", "industry"):
                                _fund_rows.append({"Metric": _fk.replace("_", " ").title(), "Value": str(_fv)})
                        if _fund_rows:
                            st.dataframe(pd.DataFrame(_fund_rows), use_container_width=True, hide_index=True)
                    if not _da_perf and not _da_fund:
                        st.info(f"No fundamental data available for {_da_name}.")
                except Exception as _da_fund_err:
                    st.info(f"Could not load fundamentals: {_da_fund_err}")
            else:
                st.info("No ticker found for this asset.")

        with _da_tab_trades:
            _da_port = paper_trader._load()
            _da_open = [p for p in _da_port.get("open_positions", []) if p.get("asset") == _da_name]
            _da_history = [_tr for _tr in _da_port.get("trade_history", []) if _tr.get("asset") == _da_name]

            if _da_open:
                st.markdown("#### Open Positions")
                for _op in _da_open:
                    _op_dir_icon = "▲" if _op.get("direction") == "long" else "▼"
                    _op_entry = _op.get("entry_price", 0)
                    _op_usd = _op.get("usd_amount", 0)
                    _op_sl = _op.get("stop_loss")
                    _op_tp = _op.get("take_profit")
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-radius:8px;padding:12px 16px;margin-bottom:8px;'>"
                        f"<span style='font-weight:600;color:#e6edf3;'>"
                        f"{_op_dir_icon} {_op.get('direction','').upper()}</span>"
                        f"<span style='color:#8b949e;margin-left:12px;'>"
                        f"Entry: ${_op_entry:,.2f} &middot; Size: ${_op_usd:,.2f}"
                        f"{' &middot; SL: $' + f'{_op_sl:,.2f}' if _op_sl else ''}"
                        f"{' &middot; TP: $' + f'{_op_tp:,.2f}' if _op_tp else ''}"
                        f"</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption(f"No open positions for {_da_name}.")

            if _da_history:
                st.markdown("#### Trade History")
                _da_th_rows = []
                for _t in sorted(_da_history, key=lambda x: x.get("closed_at", ""), reverse=True):
                    _t_pnl = _t.get("pnl", 0)
                    _da_th_rows.append({
                        "Closed": _t.get("closed_at", "")[:16].replace("T", " "),
                        "Direction": _t.get("direction", "").upper(),
                        "Entry": f"${_t.get('entry_price', 0):,.2f}",
                        "Exit": f"${_t.get('exit_price', 0):,.2f}",
                        "P&L": f"${_t_pnl:+,.2f}",
                        "Exit Type": _t.get("exit_reason", "").replace("_", " ").title(),
                    })
                if _da_th_rows:
                    st.dataframe(pd.DataFrame(_da_th_rows), use_container_width=True, hide_index=True)
            else:
                st.caption(f"No trade history for {_da_name}.")


# ===========================
# WATCHLIST OVERVIEW (Bloomberg-style)
# ===========================
elif view == "watchlist":
    _ts_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    render_page_header("Market Watchlist", view_key="watchlist")
    render_page_info("watchlist")

    # Scan button + status
    _wl_btn_col1, _wl_btn_col2 = st.columns([3, 1])
    with _wl_btn_col1:
        st.markdown(
            f"<div class='section-header'><span class='dot' style='background:#3fb950;'></span>"
            f"<span class='label'>Live Signal Cards</span>"
            f"<span style='margin-left:auto;font-family:JetBrains Mono,monospace;font-size:0.7em;color:#8b949e;'>"
            f"Last refresh: {_ts_now}</span></div>",
            unsafe_allow_html=True,
        )
    with _wl_btn_col2:
        _wl_do_scan = st.button("Scan All Assets", key="wl_scan_btn", use_container_width=True)
    if _wl_do_scan:
        from market_scanner import scan_all as _wl_scan_all
        _wl_bar = st.progress(0, text="Initializing scan...")
        _wl_status = st.empty()
        _wl_done = {}

        def _wl_scan_cb(asset_name, index, total, success):
            _wl_done[asset_name] = success
            _wl_bar.progress(index / total, text=f"Scanned {index}/{total} assets...")
            _wl_icons = [f"{'OK' if ok else 'FAIL'} {n}" for n, ok in _wl_done.items()]
            _wl_status.caption(" · ".join(_wl_icons))

        try:
            _wl_scan_all(progress_callback=_wl_scan_cb)
            _wl_bar.progress(1.0, text="Scan complete!")
            _wl_status.empty()
            st.success("Scan complete! All assets updated.")
            import time as _t; _t.sleep(0.5)
            st.rerun()
        except Exception as _scan_err:
            _wl_bar.empty()
            _wl_status.empty()
            st.error(f"Scan failed: {_scan_err}")

    watchlist = load_watchlist_summary()

    # Show banner if some assets are pending scan
    _pending_scan = [n for n, d in watchlist.items() if d.get("_needs_scan")]
    if _pending_scan:
        st.warning(
            f"**{len(_pending_scan)} assets awaiting first scan:** {', '.join(_pending_scan)}. "
            f"Click **Scan All Assets** above to generate signals for all your watchlist assets."
        )

    if watchlist:
        # Fetch live prices and overlay onto cached data
        live_prices = fetch_live_prices(watchlist)
        _live_daily = st.session_state.get("_live_daily_changes", {})
        if live_prices:
            for name, live_price in live_prices.items():
                if name in watchlist:
                    watchlist[name]["price"] = live_price
                    # Use real daily change from yfinance (prev close vs current)
                    if name in _live_daily:
                        watchlist[name]["price_change_pct"] = _live_daily[name]

        # ── CATEGORY TABS (TradingView-style) ──
        # Reuse asset class mapping from advisor
        _WL_CLASS_MAP = {
            "BTC-USD": "Crypto", "ETH-USD": "Crypto", "SOL-USD": "Crypto",
            "XRP-USD": "Crypto", "DOGE-USD": "Crypto", "ADA-USD": "Crypto",
            "AVAX-USD": "Crypto", "LINK-USD": "Crypto", "DOT-USD": "Crypto",
            "LTC-USD": "Crypto",
            "GC=F": "Metals", "SI=F": "Metals", "PL=F": "Metals", "HG=F": "Metals",
            "PA=F": "Metals",
            "CL=F": "Energy", "NG=F": "Energy",
            "^GSPC": "Indices", "^IXIC": "Indices", "^DJI": "Indices", "^RUT": "Indices",
            "EURUSD=X": "Forex", "GBPUSD=X": "Forex", "USDJPY=X": "Forex",
            "AUDUSD=X": "Forex", "USDCHF=X": "Forex",
            "ZW=F": "Agriculture", "ZC=F": "Agriculture",
        }
        _WL_NAME_MAP = {
            "BTC": "Crypto", "ETH": "Crypto", "SOL": "Crypto", "XRP": "Crypto",
            "DOGE": "Crypto", "ADA": "Crypto", "AVAX": "Crypto", "LINK": "Crypto",
            "DOT": "Crypto", "LTC": "Crypto",
            "Gold": "Metals", "Silver": "Metals", "Platinum": "Metals",
            "Copper": "Metals", "Palladium": "Metals",
            "Oil": "Energy", "Natural Gas": "Energy",
            "S&P 500": "Indices", "NASDAQ": "Indices", "Dow Jones": "Indices",
            "Russell 2000": "Indices",
            "EUR/USD": "Forex", "GBP/USD": "Forex", "USD/JPY": "Forex",
            "AUD/USD": "Forex", "USD/CHF": "Forex",
            "Wheat": "Agriculture", "Corn": "Agriculture",
        }

        def _wl_get_class(name, data):
            ticker = data.get("ticker", "")
            cls = _WL_CLASS_MAP.get(ticker)
            if cls:
                return cls
            cls = _WL_NAME_MAP.get(name)
            if cls:
                return cls
            cat = data.get("category", "").lower()
            if "crypto" in cat: return "Crypto"
            if "stock" in cat or "equity" in cat: return "Stocks"
            if "commodity" in cat: return "Metals"
            if "index" in cat: return "Indices"
            if "forex" in cat: return "Forex"
            return "Stocks"

        _wl_classes = sorted(set(_wl_get_class(n, d) for n, d in watchlist.items()))
        _wl_tab_order = ["Stocks", "Crypto", "Metals", "Energy", "Indices", "Forex", "Agriculture"]
        _wl_visible = [c for c in _wl_tab_order if c in _wl_classes]
        _wl_tab_labels = ["🌐 ALL"] + [
            {"Stocks": "📈 Stocks", "Crypto": "₿ Crypto", "Metals": "🥇 Metals",
             "Energy": "⛽ Energy", "Indices": "📊 Indices", "Forex": "💱 Forex",
             "Agriculture": "🌾 Agri"}.get(c, c)
            for c in _wl_visible
        ]
        _wl_sel_tab = st.radio(
            "Category", options=_wl_tab_labels, horizontal=True,
            key="wl_cat_tab", label_visibility="collapsed",
        )
        if _wl_sel_tab == "🌐 ALL":
            _wl_filter_class = None
        else:
            _wl_tab_idx = _wl_tab_labels.index(_wl_sel_tab) - 1
            _wl_filter_class = _wl_visible[_wl_tab_idx] if _wl_tab_idx >= 0 else None

        # ── Sort options ──
        _wl_sort = st.radio(
            "Sort", options=["Signal", "Price ↓", "Change ↓", "Confidence ↓", "Name"],
            horizontal=True, key="wl_sort", label_visibility="collapsed",
        )

        # Filter + sort watchlist items
        _wl_items = list(watchlist.items())
        if _wl_filter_class:
            _wl_items = [(n, d) for n, d in _wl_items if _wl_get_class(n, d) == _wl_filter_class]

        if _wl_sort == "Signal":
            _sig_order = {"STRONG BUY": 0, "BUY": 1, "NEUTRAL": 2, "SELL": 3, "STRONG SELL": 4}
            _wl_items.sort(key=lambda x: _sig_order.get(x[1].get("signal_label", "NEUTRAL"), 2))
        elif _wl_sort == "Price ↓":
            _wl_items.sort(key=lambda x: x[1].get("price", 0), reverse=True)
        elif _wl_sort == "Change ↓":
            _wl_items.sort(key=lambda x: abs(x[1].get("price_change_pct", 0) or 0), reverse=True)
        elif _wl_sort == "Confidence ↓":
            _wl_items.sort(key=lambda x: (x[1].get("confidence", {}).get("confidence_pct", 0)
                           if isinstance(x[1].get("confidence"), dict) else 0), reverse=True)
        elif _wl_sort == "Name":
            _wl_items.sort(key=lambda x: x[0])

        # ── SINGLE TABLE (no cards — TradingView-style) ──
        _uwl_data = load_user_watchlist()
        _sparkline_tickers = []
        _ticker_to_name = {}
        for name, d in watchlist.items():
            tick = d.get("ticker", "")
            if not tick and name in _uwl_data:
                tick = _uwl_data[name].get("ticker", "")
            if tick:
                _sparkline_tickers.append(tick)
                _ticker_to_name[tick] = name
        _sparklines = get_sparklines_batch(_sparkline_tickers) if _sparkline_tickers else {}

        _wl_rows_html = ""
        for name, d in _wl_items:
            conf = d.get("confidence", {})
            conf_pct = conf.get("confidence_pct", 0) if isinstance(conf, dict) else 0
            chg = d.get("price_change_pct")
            chg_str = f"{chg:+.2f}%" if chg is not None else ""
            chg_color = "#3fb950" if (chg or 0) >= 0 else "#f85149"
            signal = d.get("signal_label", "N/A")
            sig_style = SIGNAL_STYLES.get(signal, {"color": "#fff", "bg": "#6c757d"})
            tick = d.get("ticker", "")
            if not tick and name in _uwl_data:
                tick = _uwl_data[name].get("ticker", "")
            spark_svg = _sparklines.get(tick, "")
            _asset_cls = _wl_get_class(name, d)
            _cls_icon = {"Stocks": "📈", "Crypto": "₿", "Metals": "🥇", "Energy": "⛽",
                         "Indices": "📊", "Forex": "💱", "Agriculture": "🌾"}.get(_asset_cls, "📦")
            _rsi_val = d.get("rsi", 0)
            _rsi_color = "#f85149" if _rsi_val > 70 else "#3fb950" if _rsi_val < 30 else "#e6edf3"
            _conf_color = "#3fb950" if conf_pct >= 65 else "#d29922" if conf_pct >= 40 else "#f85149"
            # ── Watchlist NEWS column: colored badge + tooltip headline ──
            _wl_news_val = d.get("news_sentiment", "N/A")
            _wl_news_color = "#3fb950" if _wl_news_val == "BULLISH" else "#f85149" if _wl_news_val == "BEARISH" else "#6e7681"
            _wl_news_bg = "rgba(63,185,80,0.1)" if _wl_news_val == "BULLISH" else "rgba(248,81,73,0.1)" if _wl_news_val == "BEARISH" else "rgba(110,118,129,0.05)"
            # Load top headline for tooltip
            _wl_safe_name = name.lower().replace("/", "_").replace("\\", "_").replace(" ", "_").replace("&", "&")
            _wl_news_tooltip = ""
            for _wl_np in [NEWS_DIR / f"news_{_wl_safe_name}.json", NEWS_DIR / f"news_{name.lower().replace(' ', '_')}.json"]:
                if _wl_np.exists():
                    try:
                        _wl_nd = json.loads(_wl_np.read_text(encoding="utf-8"))
                        _wl_arts = [a for a in _wl_nd.get("articles", []) if a.get("relevant")]
                        if not _wl_arts:
                            _wl_arts = _wl_nd.get("articles", [])[:1]
                        if _wl_arts:
                            _wl_hl = _wl_arts[0].get("title", "")
                            if " - " in _wl_hl:
                                _wl_hl = _wl_hl.rsplit(" - ", 1)[0]
                            _wl_news_tooltip = html.escape(_wl_hl[:100], quote=True)
                        break
                    except Exception:
                        pass

            _wl_rows_html += (
                f"<tr style='border-bottom:1px solid rgba(48,54,61,0.2);'>"
                f"<td style='padding:6px 10px;'>"
                f"<span style='font-size:0.8em;'>{_cls_icon}</span> "
                f"<span style='color:#e6edf3;font-weight:600;font-size:0.88em;'>{name}</span>"
                f"<span style='color:#484f58;font-size:0.65em;margin-left:6px;'>{tick}</span></td>"
                f"<td style='padding:6px 4px;'>{spark_svg}</td>"
                f"<td style='padding:6px 10px;color:#e6edf3;font-family:JetBrains Mono,monospace;"
                f"font-size:0.82em;text-align:right;'>${d.get('price', 0):,.2f}</td>"
                f"<td style='padding:6px 10px;color:{chg_color};font-family:JetBrains Mono,monospace;"
                f"font-size:0.82em;text-align:right;'>{chg_str}</td>"
                f"<td style='padding:6px 10px;text-align:center;'>"
                f"<span style='background:{sig_style['bg']};color:{sig_style['color']};"
                f"padding:1px 8px;border-radius:4px;font-size:0.7em;font-weight:700;'>"
                f"{signal}</span></td>"
                f"<td style='padding:6px 10px;color:{_conf_color};font-family:JetBrains Mono,monospace;"
                f"font-size:0.82em;text-align:right;'>{conf_pct}%</td>"
                f"<td style='padding:6px 10px;text-align:center;' title='{_wl_news_tooltip}'>"
                f"<span style='background:{_wl_news_bg};color:{_wl_news_color};"
                f"padding:2px 8px;border-radius:4px;font-size:0.7em;font-weight:700;"
                f"cursor:help;'>{_wl_news_val}</span></td>"
                f"<td style='padding:6px 10px;color:{_rsi_color};font-family:JetBrains Mono,monospace;"
                f"font-size:0.82em;text-align:right;'>{_rsi_val:.0f}</td>"
                f"</tr>"
            )

        _th_style = ("padding:8px 10px;text-align:left;color:#6e7681;font-size:0.68em;"
                     "letter-spacing:0.1em;font-family:JetBrains Mono,monospace;")
        _th_r = _th_style + "text-align:right;"
        _th_c = _th_style + "text-align:center;"

        st.caption(f"Showing {len(_wl_items)} of {len(watchlist)} assets")

        if _wl_rows_html:
            st.markdown(
                f"<div style='overflow-x:auto;'>"
                f"<table style='width:100%;border-collapse:collapse;background:#0d1117;"
                f"border-radius:10px;overflow:hidden;'>"
                f"<thead><tr style='background:#161b22;border-bottom:2px solid #21262d;'>"
                f"<th style='{_th_style}'>ASSET</th>"
                f"<th style='{_th_style}'>30D</th>"
                f"<th style='{_th_r}'>PRICE</th>"
                f"<th style='{_th_r}'>CHG</th>"
                f"<th style='{_th_c}'>SIGNAL</th>"
                f"<th style='{_th_r}'>CONF</th>"
                f"<th style='{_th_c}'>NEWS</th>"
                f"<th style='{_th_r}'>RSI</th>"
                f"</tr></thead><tbody>{_wl_rows_html}</tbody></table></div>",
                unsafe_allow_html=True,
            )

        # Asset detail links (compact row of buttons)
        _wl_btn_items = _wl_items[:20]  # Limit detail buttons
        if _wl_btn_items:
            _wl_detail_cols = st.columns(min(8, len(_wl_btn_items)))
            for _bi, (_bn, _bd) in enumerate(_wl_btn_items):
                with _wl_detail_cols[_bi % len(_wl_detail_cols)]:
                    asset_link_button(_bn, "wl")
    else:
        st.info("No watchlist data yet. Run a scan to populate the signal cards.")
        st.markdown(
            "The watchlist shows **Signal Trading Cards** for each asset with:\n"
            "- Live price, signal badge, and confidence score\n"
            "- One-line reasoning from the AI agent\n"
            "- Backtest results and news sentiment\n"
            "- Auto-adaptive report depth (brief/standard/deep dive)"
        )

    # ── Manage Watchlist ──
    st.divider()
    with st.expander("Manage Watchlist — Add or Remove Assets", expanded=False):
        _uwl = load_user_watchlist()
        if _uwl:
            st.markdown("#### Current Watchlist Assets")
            _uwl_rows = []
            for name, cfg in _uwl.items():
                _uwl_rows.append({
                    "Asset": name,
                    "Ticker": cfg.get("ticker", ""),
                    "Category": cfg.get("category", ""),
                    "Target": cfg.get("target", ""),
                    "Support": cfg.get("support", ""),
                    "Enabled": cfg.get("enabled", True),
                })
            st.dataframe(pd.DataFrame(_uwl_rows), use_container_width=True, hide_index=True)

        st.markdown("#### Add New Asset")
        _add_col1, _add_col2, _add_col3 = st.columns(3)
        with _add_col1:
            _new_name = st.text_input("Asset Name", placeholder="e.g., Tesla", key="wl_add_name")
        with _add_col2:
            _new_ticker = st.text_input("Yahoo Finance Ticker", placeholder="e.g., TSLA", key="wl_add_ticker")
        with _add_col3:
            _new_cat = st.selectbox("Category", ["crypto", "commodity", "index", "forex", "stock"], key="wl_add_cat")

        _add_col4, _add_col5 = st.columns(2)
        with _add_col4:
            _new_target = st.number_input("Price Target", min_value=0.0, value=0.0, key="wl_add_target")
        with _add_col5:
            _new_support = st.number_input("Support Level", min_value=0.0, value=0.0, key="wl_add_support")

        if st.button("Add to Watchlist", key="wl_add_btn", use_container_width=True):
            if _new_name and _new_ticker:
                _uwl = load_user_watchlist()
                _uwl[_new_name] = {
                    "ticker": _new_ticker,
                    "support": _new_support,
                    "target": _new_target,
                    "stop_pct": 0.05,
                    "macro_bias": "neutral",
                    "category": _new_cat,
                    "enabled": True,
                }
                save_user_watchlist(_uwl)
                st.success(f"Added {_new_name} ({_new_ticker}) to watchlist!")
                st.rerun()
            else:
                st.warning("Please enter both asset name and ticker.")

        # Remove asset
        if _uwl:
            st.markdown("#### Remove Asset")
            _remove_asset = st.selectbox("Select asset to remove", list(_uwl.keys()), key="wl_remove_sel")
            if st.button(f"Remove {_remove_asset}", key="wl_remove_btn"):
                _uwl = load_user_watchlist()
                if _remove_asset in _uwl:
                    del _uwl[_remove_asset]
                    save_user_watchlist(_uwl)
                    st.success(f"Removed {_remove_asset} from watchlist.")
                    st.rerun()


# ===========================
# NEWS INTELLIGENCE — Geopolitical Analysis & Live News Feed
# ===========================
elif view == "news_intel":
    render_page_header("News Intelligence", view_key="news_intel")
    render_page_info("news_intel")

    _ni_tab1, _ni_tab2, _ni_tab3, _ni_tab4, _ni_tab5 = st.tabs([
        "Live News Feed", "Social Pulse", "Geopolitical Radar", "Scenario Playbook", "Analysis History"
    ])

    # ── Load all cached news data ──
    _all_news_articles = []
    _asset_news = {}
    for nf in NEWS_DIR.glob("news_*.json"):
        try:
            data = json.loads(nf.read_text(encoding="utf-8"))
            asset_name = data.get("asset", nf.stem.replace("news_", "").title())
            articles = data.get("articles", [])
            _asset_news[asset_name] = data
            _all_news_articles.extend(articles)
        except Exception:
            pass

    # ── TAB 1: Live News Feed ──
    with _ni_tab1:
        st.markdown("### Live Market News")

        _ni_col1, _ni_col2 = st.columns([3, 1])
        with _ni_col2:
            _ni_filter = st.selectbox("Filter by Asset", ["All Assets"] + sorted(_asset_news.keys()), key="ni_asset_filter")
            _ni_sentiment_filter = st.selectbox("Sentiment", ["All", "Bullish", "Bearish", "Neutral"], key="ni_sent_filter")

        # Filter articles
        if _ni_filter != "All Assets":
            _filtered_articles = _asset_news.get(_ni_filter, {}).get("articles", [])
        else:
            _filtered_articles = _all_news_articles

        if _ni_sentiment_filter == "Bullish":
            _filtered_articles = [a for a in _filtered_articles if a.get("sentiment", 0) > 0]
        elif _ni_sentiment_filter == "Bearish":
            _filtered_articles = [a for a in _filtered_articles if a.get("sentiment", 0) < 0]
        elif _ni_sentiment_filter == "Neutral":
            _filtered_articles = [a for a in _filtered_articles if a.get("sentiment", 0) == 0]

        # Deduplicate by title
        _seen = set()
        _unique_articles = []
        for a in _filtered_articles:
            t = a.get("title", "").strip().lower()
            if t and t not in _seen:
                _seen.add(t)
                _unique_articles.append(a)

        with _ni_col1:
            # Sentiment overview bar
            _bull_count = sum(1 for a in _unique_articles if a.get("sentiment", 0) > 0)
            _bear_count = sum(1 for a in _unique_articles if a.get("sentiment", 0) < 0)
            _neut_count = len(_unique_articles) - _bull_count - _bear_count
            _total = len(_unique_articles) or 1
            _bull_pct_ni = _bull_count * 100 // _total
            _bear_pct_ni = _bear_count * 100 // _total

            st.markdown(
                f"<div style='background:#161b22;border-radius:8px;padding:12px 16px;margin-bottom:12px;'>"
                # Sentiment percentage bar (StockTwits-style)
                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>"
                f"<span style='color:#3fb950;font-size:0.85em;font-weight:700;'>{_bull_pct_ni}% Bull</span>"
                f"<div style='flex:1;height:10px;border-radius:5px;background:#21262d;"
                f"display:flex;overflow:hidden;'>"
                f"<div style='width:{_bull_pct_ni}%;background:linear-gradient(90deg,#2ea043,#3fb950);'></div>"
                f"<div style='width:{100 - _bull_pct_ni - _bear_pct_ni}%;background:#6e7681;opacity:0.2;'></div>"
                f"<div style='width:{_bear_pct_ni}%;background:linear-gradient(90deg,#f85149,#da3633);'></div>"
                f"</div>"
                f"<span style='color:#f85149;font-size:0.85em;font-weight:700;'>{_bear_pct_ni}% Bear</span>"
                f"</div>"
                # Stats row
                f"<div style='display:flex;gap:16px;color:#8b949e;font-size:0.75em;'>"
                f"<span>🟢 {_bull_count} bullish</span>"
                f"<span>⚪ {_neut_count} neutral</span>"
                f"<span>🔴 {_bear_count} bearish</span>"
                f"<span style='margin-left:auto;'>📰 {len(_unique_articles)} total articles</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        # Asset sentiment summary cards (compact grid)
        if _asset_news:
            _sm_cols = st.columns(min(len(_asset_news), 6))
            for idx, (aname, adata) in enumerate(sorted(_asset_news.items())):
                with _sm_cols[idx % min(len(_asset_news), 6)]:
                    _sl = adata.get("sentiment_label", "N/A")
                    _ss = adata.get("sentiment_score", 0)
                    _sc = "#3fb950" if _sl == "BULLISH" else "#f85149" if _sl == "BEARISH" else "#6e7681"
                    _rc = adata.get("relevant_count", 0)
                    _impact_stars = "⭐⭐⭐" if _rc >= 10 else "⭐⭐" if _rc >= 5 else "⭐" if _rc >= 1 else ""
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-left:3px solid {_sc};padding:8px 12px;border-radius:6px;margin-bottom:8px;'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                        f"<span style='color:#e6edf3;font-weight:600;font-size:0.85em;'>{aname}</span>"
                        f"<span style='font-size:0.6em;'>{_impact_stars}</span></div>"
                        f"<div style='color:{_sc};font-family:JetBrains Mono,monospace;font-size:0.95em;"
                        f"font-weight:700;'>{_ss:+.2f}</div>"
                        f"<div style='color:#8b949e;font-size:0.68em;'>{_rc} relevant</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        st.divider()

        # ── Date-grouped news timeline (Finviz-style) ──
        _ni_date_groups: dict[str, list] = {}
        for art in _unique_articles[:80]:
            _art_pub_raw = art.get("published", "")
            try:
                from email.utils import parsedate_to_datetime as _ni_pdt
                _art_dt = _ni_pdt(_art_pub_raw)
                _art_date_key = _art_dt.strftime("%A, %b %d %Y")
            except Exception:
                _art_date_key = "Unknown Date"
            if _art_date_key not in _ni_date_groups:
                _ni_date_groups[_art_date_key] = []
            _ni_date_groups[_art_date_key].append(art)

        for _dg_date, _dg_arts in _ni_date_groups.items():
            # Date header
            _dg_bull = sum(1 for a in _dg_arts if a.get("sentiment", 0) > 0)
            _dg_bear = sum(1 for a in _dg_arts if a.get("sentiment", 0) < 0)
            _dg_mood = "🟢" if _dg_bull > _dg_bear * 1.5 else "🔴" if _dg_bear > _dg_bull * 1.5 else "🟡"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;padding:10px 0 6px 0;"
                f"border-bottom:2px solid #21262d;margin-bottom:6px;'>"
                f"<span style='font-size:0.85em;'>{_dg_mood}</span>"
                f"<span style='color:#58a6ff;font-size:0.82em;font-weight:700;'>{_dg_date}</span>"
                f"<span style='color:#6e7681;font-size:0.68em;'>"
                f"{len(_dg_arts)} articles · {_dg_bull} bull · {_dg_bear} bear</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            for art in _dg_arts:
                _s = art.get("sentiment", 0)
                _raw_title = art.get("title", "No title")
                _clean_t = _raw_title.rsplit(" - ", 1)[0] if " - " in _raw_title else _raw_title
                _src_name = _raw_title.rsplit(" - ", 1)[-1].strip() if " - " in _raw_title else art.get("source", "Unknown")
                _src_esc = html.escape(_src_name[:25])
                _title_esc = html.escape(_clean_t)
                _link = art.get("link", "").strip()
                _rel = art.get("relevant", False)
                # Sentiment badge with color-coded border
                _sent_color = "#3fb950" if _s > 0.3 else "#f85149" if _s < -0.3 else "#6e7681"
                _sent_icon = "🟢" if _s > 0.3 else "🔴" if _s < -0.3 else "⚪"
                _rel_border = f"border-left:3px solid #58a6ff;" if _rel else f"border-left:3px solid {_sent_color};"
                # Time only (no date since we're grouped by date)
                try:
                    from email.utils import parsedate_to_datetime as _ni_pdt2
                    _art_dt2 = _ni_pdt2(art.get("published", ""))
                    _time_str = _art_dt2.strftime("%H:%M")
                except Exception:
                    _time_str = ""
                # Clickable title
                if _link:
                    _safe_link = html.escape(_link, quote=True)
                    _title_el = (
                        f"<a href='{_safe_link}' target='_blank' rel='noopener noreferrer' "
                        f"style='color:#e6edf3;text-decoration:none;font-size:0.82em;'>"
                        f"{_title_esc}</a>"
                    )
                else:
                    _title_el = f"<span style='color:#e6edf3;font-size:0.82em;'>{_title_esc}</span>"
                st.markdown(
                    f"<div style='background:#0d1117;{_rel_border}padding:7px 12px;margin-bottom:3px;"
                    f"border-radius:4px;display:flex;align-items:center;gap:8px;'>"
                    f"<span style='color:#484f58;font-family:JetBrains Mono,monospace;"
                    f"font-size:0.68em;min-width:36px;'>{_time_str}</span>"
                    f"<span style='font-size:0.68em;'>{_sent_icon}</span>"
                    f"<div style='flex:1;overflow:hidden;'>"
                    f"<div style='overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{_title_el}</div>"
                    f"</div>"
                    f"<span style='color:#58a6ff;font-size:0.65em;font-weight:600;white-space:nowrap;'>{_src_esc}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── TAB 2: Social Pulse (Influencer Tracking + Reddit) ──
    with _ni_tab2:
        st.markdown("### Social Pulse")
        st.markdown(
            "<div style='color:#8b949e;font-size:0.85em;margin-bottom:16px;'>"
            "Real-time social sentiment from market-moving influencers (Trump, Musk, Powell, Saylor) "
            "and Reddit communities (r/wallstreetbets, r/CryptoCurrency, r/stocks).</div>",
            unsafe_allow_html=True,
        )

        # Load or scan social sentiment
        _sp_scan_btn = st.button("Scan Social Sentiment Now", key="sp_scan_btn", use_container_width=True, type="primary")
        if _sp_scan_btn:
            with st.spinner("Scanning influencers + Reddit... (this takes 15-30 seconds)"):
                try:
                    import social_sentiment as _ss_mod
                    _ss_engine = _ss_mod.SocialSentimentEngine()
                    _sp_data = _ss_engine.scan_all()
                    st.success(f"Social scan complete! {_sp_data['stats']['total_alerts']} alerts found.")
                    st.rerun()
                except Exception as _sp_err:
                    st.error(f"Social scan failed: {_sp_err}")
                    _sp_data = None
        else:
            try:
                import social_sentiment as _ss_mod
                _sp_data = _ss_mod.SocialSentimentEngine.load_cached()
            except ImportError:
                _sp_data = None

        if _sp_data:
            _sp_ts = _sp_data.get("timestamp", "")[:19].replace("T", " ")
            _sp_stats = _sp_data.get("stats", {})

            # Stats banner
            _sp_sc1, _sp_sc2, _sp_sc3, _sp_sc4 = st.columns(4)
            with _sp_sc1:
                st.metric("Influencers Tracked", _sp_stats.get("influencers_scanned", 0))
            with _sp_sc2:
                st.metric("Subreddits Scanned", _sp_stats.get("subreddits_scanned", 0))
            with _sp_sc3:
                _sp_high = _sp_stats.get("high_alerts", 0)
                st.metric("High Priority Alerts", _sp_high, delta="ACTION" if _sp_high > 0 else "calm")
            with _sp_sc4:
                st.metric("Total Alerts", _sp_stats.get("total_alerts", 0))

            st.caption(f"Last scan: {_sp_ts} | Duration: {_sp_stats.get('scan_duration_s', 0)}s")

            # ── Alerts Banner ──
            _sp_alerts = _sp_data.get("alerts", [])
            if _sp_alerts:
                st.markdown("#### Active Alerts")
                for _alert in _sp_alerts[:10]:
                    _al_type = _alert.get("type", "")
                    _al_asset = html.escape(_alert.get("asset", ""))
                    _al_msg = html.escape(_alert.get("message", ""))
                    _al_level = _alert.get("alert_level", "LOW")
                    if _al_type == "INFLUENCER":
                        _al_icon = "🔔"
                        _al_color = "#f85149" if _al_level == "HIGH" else "#d29922"
                    else:
                        _al_icon = "📢"
                        _al_color = "#a371f7"
                    st.markdown(
                        f"<div style='background:#161b22;border-left:3px solid {_al_color};"
                        f"border-radius:6px;padding:10px 16px;margin-bottom:6px;'>"
                        f"<span style='font-size:1.1em;'>{_al_icon}</span> "
                        f"<span style='color:{_al_color};font-weight:700;font-size:0.85em;'>"
                        f"{_al_asset}</span> "
                        f"<span style='color:#e6edf3;font-size:0.85em;'>{_al_msg}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            # ── Influencer Grid ──
            st.markdown("#### Influencer Tracker")
            _sp_influencers = _sp_data.get("influencers", {})
            _inf_cols = st.columns(3)
            for _idx, (_inf_name, _inf_data) in enumerate(_sp_influencers.items()):
                with _inf_cols[_idx % 3]:
                    _inf_sent = _inf_data.get("sentiment", 0)
                    _inf_alert = _inf_data.get("alert_level", "NONE")
                    _inf_arts = len(_inf_data.get("articles", []))
                    _inf_bull_kw = _inf_data.get("bull_keywords", 0)
                    _inf_bear_kw = _inf_data.get("bear_keywords", 0)
                    _inf_color = "#3fb950" if _inf_sent > 0.1 else ("#f85149" if _inf_sent < -0.1 else "#6e7681")
                    _alert_badge = ""
                    if _inf_alert == "HIGH":
                        _alert_badge = "<span style='background:#f85149;color:#fff;padding:2px 8px;border-radius:10px;font-size:0.65em;margin-left:8px;'>HIGH</span>"
                    elif _inf_alert == "MEDIUM":
                        _alert_badge = "<span style='background:#d29922;color:#fff;padding:2px 8px;border-radius:10px;font-size:0.65em;margin-left:8px;'>MEDIUM</span>"

                    # Top headline from this influencer
                    _inf_headline = ""
                    if _inf_data.get("articles"):
                        _inf_headline = html.escape(_inf_data["articles"][0].get("title", "")[:80])

                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-radius:10px;padding:14px 16px;margin-bottom:10px;min-height:130px;'>"
                        f"<div style='font-size:0.95em;font-weight:700;color:#e6edf3;'>"
                        f"{html.escape(_inf_name)}{_alert_badge}</div>"
                        f"<div style='color:{_inf_color};font-family:JetBrains Mono,monospace;"
                        f"font-size:1.1em;font-weight:700;margin:6px 0;'>"
                        f"Sentiment: {_inf_sent:+.2f}</div>"
                        f"<div style='color:#8b949e;font-size:0.75em;'>"
                        f"{_inf_arts} articles | Bull KW: {_inf_bull_kw} | Bear KW: {_inf_bear_kw}</div>"
                        f"<div style='color:#8b949e;font-size:0.72em;margin-top:6px;"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
                        f"{_inf_headline}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            # ── Reddit Buzz ──
            st.markdown("#### Reddit Buzz")
            _sp_reddit = _sp_data.get("reddit", {})
            _reddit_cols = st.columns(4)
            for _ridx, (_sub_name, _sub_data) in enumerate(_sp_reddit.items()):
                with _reddit_cols[_ridx % 4]:
                    _sub_sent = _sub_data.get("sentiment", 0)
                    _sub_buzz = _sub_data.get("buzz_score", 0)
                    _sub_posts = len(_sub_data.get("posts", []))
                    _sub_upvotes = _sub_data.get("total_upvotes", 0)
                    _sub_comments = _sub_data.get("total_comments", 0)
                    _sub_color = "#3fb950" if _sub_sent > 0.1 else ("#f85149" if _sub_sent < -0.1 else "#6e7681")
                    _buzz_bar_width = min(100, int(_sub_buzz * 10))

                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-radius:8px;padding:12px;margin-bottom:8px;'>"
                        f"<div style='font-size:0.85em;font-weight:700;color:#e6edf3;'>r/{html.escape(_sub_name)}</div>"
                        f"<div style='color:{_sub_color};font-family:JetBrains Mono,monospace;"
                        f"font-size:0.9em;margin:4px 0;'>Sent: {_sub_sent:+.2f}</div>"
                        f"<div style='background:#21262d;border-radius:4px;height:6px;margin:4px 0;'>"
                        f"<div style='background:#58a6ff;width:{_buzz_bar_width}%;height:100%;border-radius:4px;'></div></div>"
                        f"<div style='color:#8b949e;font-size:0.7em;'>"
                        f"Buzz: {_sub_buzz}/10 | {_sub_posts} posts | {_sub_upvotes:,} upvotes</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            # ── Per-Asset Social Scores ──
            st.markdown("#### Asset Social Scores")
            _sp_scores = _sp_data.get("asset_scores", {})
            if _sp_scores:
                _score_rows = []
                for _sas_name, _sas_data in sorted(_sp_scores.items(), key=lambda x: abs(x[1].get("social_score", 0)), reverse=True):
                    _sas_score = _sas_data.get("social_score", 0)
                    _sas_label = _sas_data.get("social_label", "NEUTRAL")
                    _sas_buzz = _sas_data.get("buzz_level", "LOW")
                    _sas_reddit = _sas_data.get("reddit_mentions", 0)
                    _sas_inf_count = len(_sas_data.get("influencer_signals", []))
                    if abs(_sas_score) > 0.01 or _sas_reddit > 0 or _sas_inf_count > 0:
                        _score_rows.append({
                            "Asset": _sas_name,
                            "Social Score": f"{_sas_score:+.2f}",
                            "Label": _sas_label,
                            "Buzz": _sas_buzz,
                            "Reddit Mentions": _sas_reddit,
                            "Influencer Signals": _sas_inf_count,
                        })
                if _score_rows:
                    st.dataframe(pd.DataFrame(_score_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No significant social signals detected.")
        else:
            st.info("No social data yet. Click 'Scan Social Sentiment Now' to start.")

    # ── TAB 3: Geopolitical Radar ──
    with _ni_tab3:
        st.markdown("### Geopolitical Event Radar")
        st.markdown(
            "<div style='color:#8b949e;font-size:0.85em;margin-bottom:16px;'>"
            "Scanning all news sources for geopolitical events and computing asset impact...</div>",
            unsafe_allow_html=True,
        )

        _geo_monitor = geopolitical_monitor.GeopoliticalMonitor()
        _geo_report = _geo_monitor.analyze(_all_news_articles)

        # Risk level banner
        _rl = _geo_report.get("risk_level", "CALM")
        _rl_colors = {
            "EXTREME": "#f85149", "ELEVATED": "#d29922", "MODERATE": "#d29922",
            "LOW": "#3fb950", "CALM": "#6e7681"
        }
        _rl_color = _rl_colors.get(_rl, "#6e7681")
        st.markdown(
            f"<div style='background:#161b22;border:2px solid {_rl_color};border-radius:10px;"
            f"padding:20px;text-align:center;margin-bottom:20px;'>"
            f"<div style='font-size:0.75em;color:#8b949e;letter-spacing:0.15em;'>GEOPOLITICAL RISK LEVEL</div>"
            f"<div style='font-size:2em;color:{_rl_color};font-weight:700;"
            f"font-family:JetBrains Mono,monospace;text-shadow:0 0 20px {_rl_color};'>{_rl}</div>"
            f"<div style='color:#8b949e;font-size:0.8em;'>Severity Score: {_geo_report.get('risk_severity', 0)} | "
            f"{_geo_report.get('geopolitical_articles', 0)} geo-events detected in "
            f"{_geo_report.get('total_articles_scanned', 0)} articles</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Dominant events
        _dom_events = _geo_report.get("dominant_events", {})
        if _dom_events:
            st.markdown("#### Active Geopolitical Themes")
            _ev_cols = st.columns(min(len(_dom_events), 4))
            for idx, (etype, count) in enumerate(sorted(_dom_events.items(), key=lambda x: x[1], reverse=True)):
                _econf = geopolitical_monitor.EVENT_KEYWORDS.get(etype, {})
                with _ev_cols[idx % min(len(_dom_events), 4)]:
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"padding:14px;border-radius:8px;text-align:center;'>"
                        f"<div style='font-size:1.8em;'>{_econf.get('icon', '')}</div>"
                        f"<div style='color:#e6edf3;font-weight:600;font-size:0.9em;'>{_econf.get('label', etype)}</div>"
                        f"<div style='color:#58a6ff;font-family:JetBrains Mono,monospace;font-size:1.2em;"
                        f"font-weight:700;'>{count} articles</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No dominant geopolitical themes detected in current news cycle.")

        # Asset impact heatmap
        _asset_impact = _geo_report.get("asset_impact", {})
        if _asset_impact:
            st.markdown("#### Geopolitical Impact on Assets")
            _impact_rows = []
            for aname, adata in sorted(_asset_impact.items(), key=lambda x: abs(x[1]["total_impact"]), reverse=True):
                _dir = adata.get("direction", "NEUTRAL")
                _imp = adata.get("total_impact", 0)
                _dc = "#3fb950" if _dir == "BULLISH" else "#f85149" if _dir == "BEARISH" else "#6e7681"
                _events_str = ", ".join(e["event"] for e in adata.get("events", []))
                _impact_rows.append({
                    "Asset": aname,
                    "Impact": f"{_imp:+.3f}",
                    "Direction": _dir,
                    "Contributing Events": _events_str,
                })
            if _impact_rows:
                st.dataframe(pd.DataFrame(_impact_rows), use_container_width=True, hide_index=True)

        # Top geopolitical headlines
        _top_events = _geo_report.get("top_events", [])
        if _top_events:
            st.markdown("#### Top Geopolitical Headlines")
            for ev in _top_events[:15]:
                _sev = ev.get("severity", 0)
                _sev_color = "#f85149" if _sev >= 6 else "#d29922" if _sev >= 3 else "#6e7681"
                _ev_title = html.escape(ev.get('title', ''))
                _ev_source = html.escape(ev.get('source', ''))
                _ev_label = html.escape(ev.get('event_label', ''))
                _ev_keywords = ', '.join(html.escape(k) for k in ev.get('keywords', []))
                st.markdown(
                    f"<div style='background:#0d1117;padding:8px 12px;margin-bottom:4px;"
                    f"border-radius:4px;border-left:3px solid {_sev_color};'>"
                    f"<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<span>{ev.get('event_icon', '')}</span>"
                    f"<span style='color:#e6edf3;font-size:0.85em;flex:1;'>{_ev_title}</span>"
                    f"<span style='color:{_sev_color};font-family:JetBrains Mono,monospace;"
                    f"font-size:0.75em;'>{_ev_label} ({_sev:.0f})</span>"
                    f"</div>"
                    f"<div style='color:#8b949e;font-size:0.7em;margin-left:28px;'>"
                    f"{_ev_source} &middot; Keywords: {_ev_keywords}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Historical precedents
        _precedents = _geo_report.get("historical_precedents", [])
        if _precedents:
            st.markdown("#### Historical Precedents")
            st.caption("What happened in similar situations before:")
            for p in _precedents:
                _details = " | ".join(f"{html.escape(str(k))}: {html.escape(str(v))}" for k, v in p.items() if k != "event")
                st.markdown(
                    f"<div style='background:#161b22;padding:8px 14px;margin-bottom:4px;"
                    f"border-radius:4px;'>"
                    f"<span style='color:#58a6ff;font-weight:600;font-size:0.85em;'>{html.escape(p.get('event', ''))}</span>"
                    f"<br><span style='color:#8b949e;font-size:0.78em;font-family:JetBrains Mono,monospace;'>"
                    f"{_details}</span></div>",
                    unsafe_allow_html=True,
                )

    # ── TAB 4: Scenario Playbook ──
    with _ni_tab4:
        st.markdown("### Geopolitical Scenario Playbook")
        st.markdown(
            "<div style='color:#8b949e;font-size:0.85em;margin-bottom:16px;'>"
            "Pre-built scenarios based on historical data. Select a scenario to see "
            "expected asset impact and what happened in the past.</div>",
            unsafe_allow_html=True,
        )

        _geo_m = geopolitical_monitor.GeopoliticalMonitor()
        _scenarios = _geo_m.get_all_scenarios()

        _sc_names = [f"{s['icon']} {s['label']}" for s in _scenarios]
        _sc_selected = st.selectbox("Select Scenario", _sc_names, key="geo_scenario")
        _sc_idx = _sc_names.index(_sc_selected) if _sc_selected in _sc_names else 0
        _sc = _scenarios[_sc_idx]

        # Scenario header
        st.markdown(
            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
            f"padding:20px;border-radius:10px;margin:12px 0;'>"
            f"<div style='font-size:1.5em;'>{_sc['icon']} {_sc['label']}</div>"
            f"<div style='color:#8b949e;font-size:0.85em;margin-top:4px;'>"
            f"Base Severity: {_sc['severity_base']}/10</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Asset impact table
        st.markdown("#### Expected Asset Impact")
        _sc_impacts = _sc.get("asset_impacts", {})
        if _sc_impacts:
            _sc_rows = []
            for aname, impact in sorted(_sc_impacts.items(), key=lambda x: x[1], reverse=True):
                _dir = "BULLISH" if impact > 0 else "BEARISH" if impact < 0 else "NEUTRAL"
                _bar_width = int(abs(impact) * 100)
                _bar_color = "#3fb950" if impact > 0 else "#f85149"
                _sc_rows.append({
                    "Asset": aname,
                    "Direction": _dir,
                    "Impact Score": f"{impact:+.2f}",
                    "Strength": f"{'█' * max(1, int(abs(impact) * 10))} ({abs(impact)*100:.0f}%)",
                })
            st.dataframe(pd.DataFrame(_sc_rows), use_container_width=True, hide_index=True)

        # Historical precedents for this scenario
        _sc_precedents = _sc.get("historical_precedents", [])
        if _sc_precedents:
            st.markdown("#### What Happened Before")
            for p in _sc_precedents:
                _details = " | ".join(f"**{k}**: {v}" for k, v in p.items() if k != "event")
                st.markdown(f"**{p.get('event', '')}**")
                st.markdown(f"  {_details}")
        else:
            st.caption("No historical precedents recorded for this scenario type.")

    # ── TAB 5: Analysis History ──
    with _ni_tab5:
        st.markdown("### Past News Analysis")
        st.caption("Cached analysis from previous scans:")

        _ni_history = []
        for nf in sorted(NEWS_DIR.glob("news_*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(nf.read_text(encoding="utf-8"))
                _ni_history.append({
                    "Asset": data.get("asset", "Unknown"),
                    "Sentiment": data.get("sentiment_label", "N/A"),
                    "Score": f"{data.get('sentiment_score', 0):+.2f}",
                    "Articles": data.get("article_count", 0),
                    "Relevant": data.get("relevant_count", 0),
                    "Sources": data.get("sources_checked", 0),
                    "Timestamp": data.get("timestamp", "")[:19],
                })
            except Exception:
                pass

        if _ni_history:
            st.dataframe(pd.DataFrame(_ni_history), use_container_width=True, hide_index=True)

            # Quick re-scan button
            st.divider()
            st.markdown("#### Refresh News Data")
            _ni_rescan_asset = st.selectbox(
                "Rescan asset", ["All"] + sorted(_asset_news.keys()), key="ni_rescan"
            )
            if st.button("Run News Scan", key="ni_scan_btn", use_container_width=True):
                with st.spinner(f"Scanning news for {_ni_rescan_asset}..."):
                    _nr = NewsResearcher()
                    if _ni_rescan_asset == "All":
                        _wl = load_watchlist_summary()
                        if _wl:
                            _nr.research_all(_wl)
                            st.success(f"Scanned news for {len(_wl)} assets.")
                        else:
                            st.warning("No watchlist loaded.")
                    else:
                        _wl = load_watchlist_summary()
                        _ticker = _wl.get(_ni_rescan_asset, {}).get("ticker", "")
                        if _ticker:
                            _nr.research(_ni_rescan_asset, _ticker)
                            st.success(f"Scanned news for {_ni_rescan_asset}.")
                        else:
                            st.warning(f"No ticker found for {_ni_rescan_asset}.")
                st.rerun()
        else:
            st.info("No analysis history yet. Run a brain cycle to generate news data.")


# ===========================
# RESEARCH REPORT (with charts, news, confidence, backtest)
# ===========================
elif view == "research" and "selected_research" in st.session_state:
    fpath = Path(st.session_state["selected_research"])
    if fpath.exists():
        signal_label = detect_signal_label(fpath)
        badge = signal_badge_html(signal_label) if signal_label else ""
        asset = detect_asset_from_filename(fpath)
        meta = extract_report_meta(fpath)
        is_signal_report = asset is not None

        # ── Header ──
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:space-between;'>"
            f"<h1 style='margin:0;border:none;padding:0;'>{fpath.stem.replace('_', ' ')}</h1>"
            f"<div>{badge}</div></div>",
            unsafe_allow_html=True,
        )

        if is_signal_report:
            # ── Metrics row ──
            metric_cols = st.columns(5)
            if meta["score"] is not None:
                metric_cols[0].metric("Signal Score", f"{meta['score']}/100")
            if meta["label"]:
                metric_cols[1].metric("Signal", meta["label"])
            if meta.get("confidence") is not None:
                conf_val = meta["confidence"]
                metric_cols[2].metric("Confidence", f"{conf_val}%")
            if meta["news_sentiment"]:
                metric_cols[3].metric("News", meta["news_sentiment"])
            if meta["news_score"] is not None:
                metric_cols[4].metric("Sentiment", f"{meta['news_score']:+.2f}")

            # Confidence bar
            if meta.get("confidence") is not None:
                conf_val = meta["confidence"]
                conf_level = meta.get("confidence_level", "LOW")
                conf_color = CONF_COLORS.get(conf_level, "#6e7681")
                st.markdown(
                    f"<div style='margin:8px 0 16px 0;'>"
                    f"<div style='display:flex;justify-content:space-between;font-family:JetBrains Mono,monospace;font-size:0.8em;'>"
                    f"<span style='color:{conf_color};font-weight:700;'>Confidence: {conf_val}%</span>"
                    f"<span style='color:#8b949e;'>{conf_level}</span></div>"
                    f"<div class='conf-bar'><div class='conf-bar-fill' style='width:{conf_val}%;background:{conf_color};'></div></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # ── Tabs: Charts / News / Report ──
            tab_charts, tab_news, tab_report = st.tabs(["Charts", "News", "Full Report"])

            with tab_charts:
                gauge_fig = load_chart(asset, "gauge")
                if gauge_fig:
                    st.plotly_chart(gauge_fig, use_container_width=True, key=f"gauge_{asset}")
                price_fig = load_chart(asset, "price")
                if price_fig:
                    st.plotly_chart(price_fig, use_container_width=True, key=f"price_{asset}")
                rsi_fig = load_chart(asset, "rsi")
                macd_fig = load_chart(asset, "macd")
                if rsi_fig and macd_fig:
                    ch1, ch2 = st.columns(2)
                    with ch1:
                        st.plotly_chart(rsi_fig, use_container_width=True, key=f"rsi_{asset}")
                    with ch2:
                        st.plotly_chart(macd_fig, use_container_width=True, key=f"macd_{asset}")
                elif rsi_fig:
                    st.plotly_chart(rsi_fig, use_container_width=True, key=f"rsi_{asset}")
                elif macd_fig:
                    st.plotly_chart(macd_fig, use_container_width=True, key=f"macd_{asset}")
                vol_fig = load_chart(asset, "volume")
                if vol_fig:
                    st.plotly_chart(vol_fig, use_container_width=True, key=f"vol_{asset}")

            with tab_news:
                news_data = load_news(asset)
                if news_data and news_data.get("articles"):
                    sent_fig = load_chart(asset, "news_sentiment")
                    if sent_fig:
                        st.plotly_chart(sent_fig, use_container_width=True, key=f"sent_{asset}")
                    st.markdown(
                        f"<div style='color:#6e7681;font-size:0.8em;font-family:JetBrains Mono,monospace;margin-bottom:12px;'>"
                        f"{news_data.get('relevant_count', 0)} relevant of {news_data.get('article_count', 0)} total articles "
                        f"&middot; Sentiment: {news_data.get('sentiment_label', 'N/A')} ({news_data.get('sentiment_score', 0):+.2f})"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    relevant_articles = [a for a in news_data["articles"] if a.get("relevant")]
                    for art in relevant_articles[:8]:
                        sent = art.get("sentiment", 0)
                        dot_color = "#3fb950" if sent > 0 else ("#f85149" if sent < 0 else "#6e7681")
                        tag = "BULLISH" if sent > 0 else ("BEARISH" if sent < 0 else "NEUTRAL")
                        source = html.escape(art.get("source", ""))
                        pub = html.escape(art.get("published", "")[:16])
                        link = art.get("link", "")
                        title_text = html.escape(art.get("title", ""))
                        title_html = f"<a href='{html.escape(link, quote=True)}' style='color:#c9d1d9;text-decoration:none;' target='_blank'>{title_text}</a>" if link else title_text
                        st.markdown(
                            f"<div style='display:flex;align-items:flex-start;gap:10px;padding:8px 12px;"
                            f"background:rgba(22,27,34,0.6);border:1px solid rgba(48,54,61,0.3);"
                            f"border-radius:8px;margin-bottom:6px;border-left:3px solid {dot_color};'>"
                            f"<div>"
                            f"<span style='color:{dot_color};font-family:JetBrains Mono,monospace;"
                            f"font-size:0.65em;font-weight:700;'>{tag}</span><br>"
                            f"<span style='font-size:0.85em;color:#c9d1d9;'>{title_html}</span><br>"
                            f"<span style='font-size:0.7em;color:#8b949e;'>{source} &middot; {pub}</span>"
                            f"</div></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("No news data available yet. Run a scan to fetch live news.")

            with tab_report:
                st.markdown(read_file(fpath))
        else:
            st.divider()
            st.markdown(read_file(fpath))
    else:
        st.error(f"File not found: {fpath}")


# ===========================
# SYSTEM EVOLUTION & LEARNING
# ===========================
elif view == "evolution":
    render_page_header("System Evolution & Learning", view_key="evolution")
    render_page_info("evolution")

    # Load data
    try:
        from memory_manager import get_evolution_stats, load_reflections
        evo_stats = get_evolution_stats()
    except Exception:
        evo_stats = {"total_lessons": 0, "by_category": {}, "lessons_per_day": {}, "total_reflections": 0, "latest_reflection": None, "all_rules": []}

    market_lessons = load_market_lessons()

    # Overview metrics
    em1, em2, em3, em4 = st.columns(4)
    em1.metric("Error Lessons", evo_stats["total_lessons"])
    em2.metric("Prevention Rules", len(evo_stats.get("all_rules", [])))
    em3.metric("Reflections", evo_stats.get("total_reflections", 0))
    em4.metric("Market Lessons", len(market_lessons.get("lessons", [])))

    # Active Learning Controls
    st.divider()
    st.markdown("### Active Learning Controls")
    _evo_col1, _evo_col2, _evo_col3 = st.columns(3)
    with _evo_col1:
        if st.button("Validate All Predictions", key="evo_validate", use_container_width=True, type="primary"):
            with st.spinner("Validating predictions against market outcomes..."):
                try:
                    from market_learner import MarketLearner
                    _ml = MarketLearner()
                    _val_results = _ml.validate_all()
                    _val_correct = sum(1 for v in _val_results if v.get("outcome") == "correct")
                    _val_incorrect = sum(1 for v in _val_results if v.get("outcome") == "incorrect")
                    st.success(f"Validated {len(_val_results)} predictions: {_val_correct} correct, {_val_incorrect} incorrect")
                    st.rerun()
                except Exception as _val_err:
                    st.error(f"Validation failed: {_val_err}")

    with _evo_col2:
        if st.button("Run Hindsight Simulator", key="evo_hindsight", use_container_width=True):
            with st.spinner("Running hindsight simulations (48h time-travel)..."):
                try:
                    from hindsight_simulator import HindsightSimulator
                    _hs = HindsightSimulator()
                    _hs_results = _hs.run_all()
                    st.success(f"Ran {len(_hs_results)} hindsight simulations")
                    st.rerun()
                except Exception as _hs_err:
                    st.error(f"Hindsight simulation failed: {_hs_err}")

    with _evo_col3:
        if st.button("Run Chief Monitor Reflection", key="evo_reflect", use_container_width=True):
            with st.spinner("Chief Monitor is reflecting on today's activities..."):
                try:
                    from chief_monitor import ChiefMonitor
                    _cm = ChiefMonitor()
                    _reflection = _cm.daily_reflection()
                    st.success("Reflection saved!")
                    st.rerun()
                except Exception as _ref_err:
                    st.error(f"Reflection failed: {_ref_err}")

    # Bot Performance Summary
    _bot_log_file = PROJECT_ROOT / "memory" / "bot_activity.json"
    if _bot_log_file.exists():
        try:
            _bot_acts = json.loads(_bot_log_file.read_text(encoding="utf-8"))
            if _bot_acts:
                st.divider()
                st.markdown("### Trading Bot Learning Summary")
                _total_bot_trades = sum(len(a.get("trades_opened", [])) for a in _bot_acts)
                _total_bot_closes = sum(len(a.get("exits_closed", [])) for a in _bot_acts)
                _total_bot_pnl = sum(c.get("pnl", 0) for a in _bot_acts for c in a.get("exits_closed", []))
                _total_bot_errors = sum(len(a.get("errors", [])) for a in _bot_acts)

                _bc1, _bc2, _bc3, _bc4 = st.columns(4)
                _bc1.metric("Bot Cycles", len(_bot_acts))
                _bc2.metric("Trades Opened", _total_bot_trades)
                _bc3.metric("Trades Closed", _total_bot_closes)
                _pnl_color = "normal" if _total_bot_pnl >= 0 else "inverse"
                _bc4.metric("Total P&L", f"${_total_bot_pnl:+,.2f}", delta_color=_pnl_color)
        except Exception:
            pass

    st.divider()

    # Today's reflection
    st.markdown("### What I Learned Today")
    reflection = evo_stats.get("latest_reflection")
    if reflection:
        st.markdown(
            f"<div class='reflection-card'>"
            f"<div style='font-family:JetBrains Mono,monospace;font-size:0.75em;color:#58a6ff;margin-bottom:8px;'>"
            f"Chief Monitor Reflection &mdash; {reflection.get('date', 'N/A')}</div>"
            f"<div style='font-size:0.9em;color:#e6edf3;font-weight:600;margin-bottom:10px;'>"
            f"{reflection.get('summary', 'No summary')}</div>"
            f"<div style='font-size:0.8em;color:#8b949e;'>",
            unsafe_allow_html=True,
        )
        for tip in reflection.get("efficiency_tips", []):
            st.markdown(f"- {tip}")
        st.markdown(
            f"<div style='margin-top:10px;font-size:0.75em;color:#8b949e;font-family:JetBrains Mono,monospace;'>"
            f"Budget: {reflection.get('budget_used_pct', 0)}% | Errors: {reflection.get('errors_today', 0)} | "
            f"Warnings: {reflection.get('warning_count', 0)}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info(t("evolution.no_reflection"))

    st.divider()

    # Error lessons by category
    col_cats, col_rules = st.columns(2)

    with col_cats:
        st.markdown("### Lessons by Category")
        by_cat = evo_stats.get("by_category", {})
        if by_cat:
            cat_colors = {"coding": "#58a6ff", "data": "#3fb950", "logic": "#d29922", "infra": "#f85149"}
            for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
                color = cat_colors.get(cat, "#6e7681")
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
                    f"<span style='background:{color};color:#fff;padding:2px 10px;border-radius:4px;"
                    f"font-family:JetBrains Mono,monospace;font-size:0.75em;font-weight:700;'>{cat.upper()}</span>"
                    f"<span style='color:#c9d1d9;font-size:0.85em;'>{count} lesson{'s' if count > 1 else ''}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No lessons recorded yet.")

    with col_rules:
        st.markdown("### Prevention Rules")
        rules = evo_stats.get("all_rules", [])
        if rules:
            for i, rule in enumerate(rules, 1):
                st.markdown(
                    f"<div class='lesson-card'>"
                    f"<span style='color:#58a6ff;font-weight:700;'>Rule #{i}:</span> {rule}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No rules yet.")

    st.divider()

    # Market lessons
    st.markdown("### Market Lessons (Strategy Failures)")
    mkt_lessons = market_lessons.get("lessons", [])
    if mkt_lessons:
        for ml in reversed(mkt_lessons[-10:]):
            pct = ml.get("pct_move", 0)
            color = "#f85149" if pct < 0 else "#3fb950"
            st.markdown(
                f"<div class='lesson-card' style='border-left-color:{color};'>"
                f"<div style='display:flex;justify-content:space-between;'>"
                f"<span style='color:#58a6ff;font-weight:700;'>{ml['id']}</span>"
                f"<span style='color:#8b949e;font-size:0.75em;'>{ml.get('timestamp', '')[:10]}</span></div>"
                f"<div style='margin-top:4px;color:#c9d1d9;'>"
                f"{ml['asset']} — Signal was {ml['signal_was']}, moved {pct:+.1f}%</div>"
                f"<div style='margin-top:4px;color:#8b949e;font-size:0.85em;'>"
                f"Lesson: {ml.get('lesson_learned', 'N/A')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No market lessons yet. These appear when predictions turn out wrong.")

    # Market rules
    mkt_rules = market_lessons.get("rules", [])
    if mkt_rules:
        st.markdown("### Learned Market Rules")
        for rule in mkt_rules:
            st.markdown(f"- {rule}")

    st.divider()

    # ── Hindsight Learning Simulator ──
    st.markdown("### Hindsight Learning Simulator")
    st.caption("The simulator 'travels' 48 hours back, makes a prediction with old data, and compares it with the actual outcome.")

    hs_data = load_hindsight()
    hs_sims = hs_data.get("simulations", [])
    hs_stats = hs_data.get("stats", {})

    if hs_sims:
        # Overview metrics
        hs1, hs2, hs3, hs4, hs5 = st.columns(5)
        hs1.metric("Simulations", hs_stats.get("total", 0))
        hs2.metric("Correct", hs_stats.get("correct", 0))
        hs3.metric("Incorrect", hs_stats.get("incorrect", 0))
        hs4.metric("Accuracy", f"{hs_stats.get('accuracy', 0)}%")
        hs5.metric("Neutral", hs_stats.get("neutral", 0))

        # Accuracy gauge
        acc = hs_stats.get("accuracy", 0)
        if acc > 0:
            acc_color = "#3fb950" if acc >= 60 else ("#d29922" if acc >= 40 else "#f85149")
            fig_hs = go.Figure(go.Indicator(
                mode="gauge+number",
                value=acc,
                title={"text": "Hindsight Accuracy", "font": {"color": "#8b949e", "size": 14}},
                number={"suffix": "%", "font": {"color": "#e6edf3", "size": 28}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#484f58"},
                    "bar": {"color": acc_color},
                    "bgcolor": "rgba(48,54,61,0.3)",
                    "bordercolor": "rgba(48,54,61,0.5)",
                    "steps": [
                        {"range": [0, 40], "color": "rgba(248,81,73,0.1)"},
                        {"range": [40, 60], "color": "rgba(210,153,34,0.1)"},
                        {"range": [60, 100], "color": "rgba(63,185,80,0.1)"},
                    ],
                },
            ))
            fig_hs.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=200, margin=dict(t=30, b=10, l=20, r=20),
                font={"color": "#c9d1d9"},
            )
            st.plotly_chart(fig_hs, use_container_width=True, key="hs_gauge")

        # Recent simulations
        st.markdown("#### Recent Time-Travel Results")
        recent_hs = sorted(hs_sims, key=lambda s: s["timestamp"], reverse=True)[:10]
        for sim in recent_hs:
            outcome = sim["outcome"]
            grade = sim["grade"]
            if outcome == "correct":
                icon, color = "+", "#3fb950"
            elif outcome == "incorrect":
                icon, color = "-", "#f85149"
            else:
                icon, color = "~", "#d29922"

            grade_colors = {"A": "#3fb950", "B": "#58a6ff", "C": "#d29922", "D": "#f85149", "F": "#da3633"}
            gc = grade_colors.get(grade, "#6e7681")

            label = sim["predicted_label"]
            style = SIGNAL_STYLES.get(label, SIGNAL_STYLES["NEUTRAL"])

            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;padding:10px 14px;"
                f"background:rgba(22,27,34,0.6);border:1px solid rgba(48,54,61,0.3);"
                f"border-radius:8px;margin-bottom:6px;border-left:3px solid {color};'>"
                f"<span style='font-size:1.2em;font-weight:700;color:{color};width:20px;text-align:center;'>{icon}</span>"
                f"<div style='flex:1;'>"
                f"<span style='font-weight:600;color:#c9d1d9;'>{sim['asset']}</span> "
                f"<span class='signal-badge' style='background:{style['bg']};color:{style['color']};font-size:0.6em;padding:2px 6px;'>{label}</span>"
                f" <span style='background:{gc};color:#fff;padding:1px 6px;border-radius:3px;"
                f"font-family:JetBrains Mono,monospace;font-size:0.6em;font-weight:700;'>{grade}</span>"
                f"<span style='font-size:0.75em;color:#8b949e;margin-left:8px;'>"
                f"${sim['predicted_price']:,.2f} → ${sim['actual_price']:,.2f} ({sim['pct_change']:+.1f}%)</span>"
                f"<div style='font-size:0.75em;color:#8b949e;margin-top:2px;'>{sim['note']}</div>"
                f"</div>"
                f"<span style='font-size:0.7em;color:#8b949e;font-family:JetBrains Mono,monospace;'>"
                f"⏪ {sim['simulated_date'][:10]}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "Noch keine Hindsight-Simulationen. Starte den Simulator:\n\n"
            "`python src/hindsight_simulator.py`\n\n"
            "Er analysiert alle Assets 48h in der Vergangenheit und vergleicht mit dem echten Ergebnis."
        )


# ===========================
# AGENT PERFORMANCE (Win-Rate)
# ===========================
elif view == "performance":
    render_page_header("Agent Performance", view_key="performance")
    render_page_info("performance")

    pred_data = load_predictions()
    preds = pred_data.get("predictions", [])
    stats = pred_data.get("stats", {})

    all_validated = [p for p in preds if p.get("validated")]
    correct = [p for p in all_validated if p.get("outcome") == "correct"]
    incorrect = [p for p in all_validated if p.get("outcome") == "incorrect"]
    neutral = [p for p in all_validated if p.get("outcome") == "neutral"]
    pending = [p for p in preds if not p.get("validated")]

    total_decisions = len(correct) + len(incorrect)
    win_rate = round(len(correct) / total_decisions * 100, 1) if total_decisions > 0 else 0

    # Overview metrics
    pm1, pm2, pm3, pm4, pm5 = st.columns(5)
    pm1.metric("Total Predictions", len(preds))
    pm2.metric("Validated", len(all_validated))
    pm3.metric("Win Rate", f"{win_rate}%")
    pm4.metric("Correct", len(correct))
    pm5.metric("Pending", len(pending))

    # Win-rate gauge
    if total_decisions > 0:
        gauge_color = "#3fb950" if win_rate >= 60 else ("#d29922" if win_rate >= 40 else "#f85149")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=win_rate,
            title={"text": "Overall Win Rate", "font": {"color": "#8b949e", "size": 16}},
            number={"suffix": "%", "font": {"color": "#e6edf3", "size": 36}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#484f58"},
                "bar": {"color": gauge_color},
                "bgcolor": "rgba(48,54,61,0.3)",
                "bordercolor": "rgba(48,54,61,0.5)",
                "steps": [
                    {"range": [0, 40], "color": "rgba(248,81,73,0.1)"},
                    {"range": [40, 60], "color": "rgba(210,153,34,0.1)"},
                    {"range": [60, 100], "color": "rgba(63,185,80,0.1)"},
                ],
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=250, margin=dict(t=40, b=20, l=30, r=30),
            font={"color": "#c9d1d9"},
        )
        st.plotly_chart(fig_gauge, use_container_width=True, key="perf_gauge")

    st.divider()

    # Per-asset breakdown
    st.markdown("### Per-Asset Performance")
    assets = set(p["asset"] for p in preds)
    if assets:
        asset_data = []
        for asset in sorted(assets):
            ap = [p for p in preds if p["asset"] == asset]
            av = [p for p in ap if p.get("validated")]
            ac = [p for p in av if p.get("outcome") == "correct"]
            ai = [p for p in av if p.get("outcome") == "incorrect"]
            ad = len(ac) + len(ai)
            wr = round(len(ac) / ad * 100, 1) if ad > 0 else 0
            asset_data.append({
                "Asset": asset,
                "Predictions": len(ap),
                "Validated": len(av),
                "Correct": len(ac),
                "Incorrect": len(ai),
                "Win Rate": f"{wr}%",
            })
        df_assets = pd.DataFrame(asset_data)
        st.dataframe(df_assets, use_container_width=True, hide_index=True)

    st.divider()

    # Recent predictions
    st.markdown("### Recent Predictions")
    recent = sorted(preds, key=lambda p: p["timestamp"], reverse=True)[:15]
    if recent:
        for pred in recent:
            outcome = pred.get("outcome", "pending")
            if outcome == "correct":
                icon, color = "+", "#3fb950"
            elif outcome == "incorrect":
                icon, color = "-", "#f85149"
            elif outcome == "neutral":
                icon, color = "~", "#d29922"
            else:
                icon, color = "?", "#6e7681"

            label = pred.get("signal_label", "N/A")
            style = SIGNAL_STYLES.get(label, SIGNAL_STYLES["NEUTRAL"])
            ts = pred.get("timestamp", "")[:16].replace("T", " ")
            note = pred.get("outcome_note", "Awaiting validation...")

            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;padding:10px 14px;"
                f"background:rgba(22,27,34,0.6);border:1px solid rgba(48,54,61,0.3);"
                f"border-radius:8px;margin-bottom:6px;border-left:3px solid {color};'>"
                f"<span style='font-size:1.2em;font-weight:700;color:{color};width:20px;text-align:center;'>{icon}</span>"
                f"<div style='flex:1;'>"
                f"<span style='font-weight:600;color:#c9d1d9;'>{pred['asset']}</span> "
                f"<span class='signal-badge' style='background:{style['bg']};color:{style['color']};font-size:0.6em;padding:2px 6px;'>{label}</span>"
                f"<span style='font-size:0.75em;color:#8b949e;margin-left:8px;'>@ ${pred.get('entry_price', 0):,.2f}</span>"
                f"<div style='font-size:0.75em;color:#8b949e;margin-top:2px;'>{note}</div>"
                f"</div>"
                f"<span style='font-size:0.7em;color:#8b949e;font-family:JetBrains Mono,monospace;'>{ts}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No predictions recorded yet. Predictions are saved automatically during market scans.")


# ===========================
# KANBAN BOARD
# ===========================
elif view == "kanban":
    render_page_header("Kanban Board", view_key="kanban")
    render_page_info("kanban")
    board = load_board()
    if not board:
        st.error("kanban_board.json not found.")
    else:
        columns = st.columns(len(board))
        for col, (status, tickets) in zip(columns, board.items()):
            clr = COLUMN_COLORS.get(status, "#555")
            with col:
                st.markdown(
                    f"<div class='kanban-column-header' style='color:{clr};border-color:{clr};'>"
                    f"{status} <span style='opacity:0.5;font-size:0.8em;'>({len(tickets)})</span></div>",
                    unsafe_allow_html=True,
                )
                if not tickets:
                    st.caption("No tickets")
                for ticket in tickets:
                    tid, title = ticket["id"], ticket["title"]
                    is_alert = title.startswith("TRADE ALERT") or title.startswith("DISCOVERY:")
                    desc = ticket.get("description", "")
                    if is_alert:
                        st.markdown(
                            f"<div class='trade-alert-card'>"
                            f"<span class='ticket-id'>{tid}</span>"
                            f"<div class='ticket-title'>{title}</div>"
                            f"{'<div class=\"ticket-desc\">' + desc + '</div>' if desc else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if st.button(f"Open {tid}", key=f"a_{tid}", use_container_width=True):
                            r = find_report_for_trade_alert(title)
                            if r:
                                st.session_state.update(selected_research=str(r), view="research")
                                st.rerun()
                    else:
                        st.markdown(
                            f"<div class='kanban-ticket'>"
                            f"<span class='ticket-id'>{tid}</span>"
                            f"<div class='ticket-title'>{title}</div>"
                            f"{'<div class=\"ticket-desc\">' + desc + '</div>' if desc else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if status == "Done":
                            if st.button(f"View {tid}", key=f"k_{tid}", use_container_width=True):
                                r = find_report_for_ticket(tid)
                                if r:
                                    st.session_state.update(selected_research=str(r), view="research")
                                    st.rerun()

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Backlog", len(board.get("Backlog", [])))
        m2.metric("To Do", len(board.get("To Do", [])))
        m3.metric("In Progress", len(board.get("In Progress", [])))
        m4.metric("Done", len(board.get("Done", [])))


# ===========================
# AGENT MONITOR
# ===========================
elif view == "monitor":
    render_page_header("Agent Monitor", view_key="monitor")
    render_page_info("monitor")
    monitor = ChiefMonitor()
    report = monitor.run_health_check()

    st.markdown(status_banner_html(report["overall_status"]), unsafe_allow_html=True)

    if report["warnings"]:
        for w in report["warnings"]:
            st.warning(w)

    st.markdown("### Agent Roster")
    agents = report["agents"]
    cols_per_row = 4
    for i in range(0, len(agents), cols_per_row):
        row_agents = agents[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, ag in zip(cols, row_agents):
            with col:
                h = ag["health"].lower()
                st.markdown(
                    f"<div class='agent-card agent-card-{h}'>"
                    f"<span class='agent-icon'>{ag['icon']}</span>"
                    f"<span class='agent-name'>{ag['name']}</span>"
                    f"<div class='agent-role'>{ag['role']}</div>"
                    f"{health_badge(ag['health'])}"
                    f"<div class='agent-meta'>"
                    f"Last seen: {ag['last_seen']}<br>"
                    f"Errors: {ag['errors_today']} &middot; ${ag['cost_today']:.4f}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.markdown("### Cost per Agent (Today)")
    breakdown = report["cost_breakdown"]
    if breakdown:
        df_cost = pd.DataFrame(breakdown)
        df_display = df_cost[["icon", "agent", "role", "cost_usd", "budget_pct", "status"]].copy()
        df_display.columns = ["", "Agent", "Role", "Cost ($)", "Budget %", "Status"]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### Budget Status")
    b = report["budget"]
    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric("Daily Cost", f"${b['daily_cost']:.4f}")
    bc2.metric("Limit", f"${b['limit']:.2f}")
    bc3.metric("Remaining", f"${b['remaining']:.4f}")
    bc4.metric("Mode", b["mode"].replace("_", " ").title())
    pct = b["daily_cost"] / b["limit"] * 100 if b["limit"] > 0 else 0
    st.progress(min(pct / 100, 1.0))

    st.divider()

    # Recent agent_logs.txt entries
    st.markdown("### Recent Activity Log")
    _agent_log_file = PROJECT_ROOT / "agent_logs.txt"
    if _agent_log_file.exists():
        try:
            _log_lines = _agent_log_file.read_text(encoding="utf-8").strip().split("\n")
            _recent_logs = _log_lines[-30:]  # Last 30 lines
            _log_display = ""
            for _ll in reversed(_recent_logs):
                if "[AutoTrader]" in _ll:
                    _ll_color = "#3fb950" if "TRADE OPENED" in _ll else ("#f85149" if "SKIP" in _ll or "ERROR" in _ll else "#58a6ff")
                elif "[ERROR]" in _ll or "ERROR" in _ll:
                    _ll_color = "#f85149"
                else:
                    _ll_color = "#8b949e"
                _log_display += f"<div style='color:{_ll_color};font-family:JetBrains Mono,monospace;font-size:0.72em;padding:2px 0;border-bottom:1px solid rgba(48,54,61,0.2);'>{_ll}</div>"
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid rgba(48,54,61,0.5);border-radius:8px;padding:12px;max-height:400px;overflow-y:auto;'>{_log_display}</div>",
                unsafe_allow_html=True,
            )
        except Exception:
            st.caption("Could not read agent log.")
    else:
        st.caption("No agent log file found. Logs appear after bot/scanner runs.")

    st.divider()
    st.markdown("### Recent Errors")
    errs = report["errors"]["recent"]
    if errs:
        for e in errs:
            st.code(e)
    else:
        st.success("No errors detected.")

    if report["loop_alerts"]:
        st.markdown("### Loop Alerts")
        for la in report["loop_alerts"]:
            st.error(f"**{la['severity'].upper()}**: `{la['message'][:80]}` repeated {la['count']}x")

    st.divider()
    st.markdown("### Autonomous Loop")

    _auto_pid_file = PROJECT_ROOT / "src" / "data" / "autonomous_loop.pid"
    _auto_running = False
    _auto_pid = None
    if _auto_pid_file.exists():
        try:
            _auto_pid = int(_auto_pid_file.read_text().strip())
            import psutil
            _auto_running = psutil.pid_exists(_auto_pid)
        except Exception:
            _auto_running = False

    if _auto_running:
        st.success(f"Autonomous loop is **running** (PID {_auto_pid})")
        _ac1, _ac2 = st.columns(2)
        with _ac1:
            if st.button("Stop Autonomous Loop", type="primary", use_container_width=True):
                try:
                    import psutil
                    proc = psutil.Process(_auto_pid)
                    proc.terminate()
                    _auto_pid_file.unlink(missing_ok=True)
                    st.success("Loop stopped.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not stop: {e}")
    else:
        if _auto_pid_file.exists():
            _auto_pid_file.unlink(missing_ok=True)
        st.info("Autonomous loop is **not running**.")
        _ac1, _ac2 = st.columns(2)
        with _ac1:
            _loop_interval = st.number_input("Interval (minutes)", min_value=1, max_value=60,
                                             value=5, step=1, key="loop_interval")
        with _ac2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Start Autonomous Loop", type="primary", use_container_width=True):
                import subprocess as _sp
                proc = _sp.Popen(
                    [sys.executable, str(PROJECT_ROOT / "src" / "autonomous_manager.py"),
                     "--loop", "--interval", str(_loop_interval)],
                    stdout=open(LOG_FILE, "a"),
                    stderr=open(LOG_FILE, "a"),
                    creationflags=0x00000008,  # DETACHED_PROCESS on Windows
                )
                _auto_pid_file.parent.mkdir(parents=True, exist_ok=True)
                _auto_pid_file.write_text(str(proc.pid))
                st.success(f"Autonomous loop started (PID {proc.pid}, every {_loop_interval} min).")
                st.rerun()

    st.divider()
    st.markdown("### Agent System Prompts")
    for name, profile in AGENT_PROFILES.items():
        with st.expander(f"{profile['icon']} {profile['name']} ({name})"):
            st.caption(profile["role"])
            st.code(profile["system_prompt"], language="text")


# ===========================
# BUDGET & API
# ===========================
elif view == "budget":
    _ts_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    render_page_header("Budget & API Usage", view_key="budget")
    render_page_info("budget")
    st.markdown(
        f"<div class='section-header'><span class='dot' style='background:#3fb950;'></span>"
        f"<span class='label'>Live Activity &mdash; Auto-Refresh every 10s</span>"
        f"<span style='margin-left:auto;font-family:JetBrains Mono,monospace;font-size:0.7em;color:#3fb950;'>"
        f"● LIVE {_ts_now}</span></div>",
        unsafe_allow_html=True,
    )

    # ── Agent Activity Log FIRST — this is what shows ALL work ──
    st.markdown("### Agent Activity Log (Real-Time)")
    if LOG_FILE.exists():
        raw_lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        today_str = time.strftime("%Y-%m-%d")
        today_entries = []
        for line in raw_lines:
            m = re.match(r"\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+)", line.strip())
            if m and m.group(1) == today_str:
                today_entries.append({
                    "Time": m.group(2),
                    "Agent": m.group(3),
                    "Action": m.group(4)[:120],
                })
        if today_entries:
            # Show newest first, last 100 entries
            df_activity = pd.DataFrame(list(reversed(today_entries[-100:])))
            st.dataframe(df_activity, use_container_width=True, hide_index=True, height=400)
            st.caption(f"Showing last {min(100, len(today_entries))} of {len(today_entries)} entries today — updates every 10s")
        else:
            st.caption("No agent activity today. Run a scan to see live agent actions.")
    else:
        st.caption("No log file yet. Agent activity will appear here after the first scan.")

    st.divider()

    # ── Budget Overview ──
    daily_cost = tm.get_daily_cost()
    monthly_cost = tm.get_monthly_cost()
    remaining = tm.budget_remaining()
    budget_limit = tm.max_daily_budget
    budget_pct = (daily_cost / budget_limit * 100) if budget_limit > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Today", f"${daily_cost:.4f}")
    c2.metric("This Month", f"${monthly_cost:.4f}")
    c3.metric("Remaining", f"${remaining:.4f}")
    c4.metric("Used", f"{budget_pct:.1f}%")
    st.progress(min(budget_pct / 100, 1.0))

    if budget_pct >= 100:
        st.error("**BUDGET EXCEEDED** — Agents PAUSED.")
    elif budget_pct >= 80:
        st.warning(f"Budget at {budget_pct:.0f}%.")

    st.divider()
    col_mode, col_budget = st.columns(2)

    with col_mode:
        st.markdown("### Efficiency Mode")
        st.markdown(mode_badge_html(tm.mode), unsafe_allow_html=True)
        st.caption("**Deep Research**: Sonnet ($3/$15/1M) | **Fast Scan**: Haiku ($0.80/$4/1M)")
        opts = {"Fast Scan (Haiku)": "fast_scan", "Deep Research (Sonnet)": "deep_research"}
        sel = st.radio("Mode:", list(opts.keys()), index=0 if tm.mode == "fast_scan" else 1, key="mode_r")
        if opts[sel] != tm.mode:
            tm.mode = opts[sel]
            st.rerun()

    with col_budget:
        st.markdown("### Daily Budget")
        st.caption(f"Current: **${budget_limit:.2f}**")
        nb = st.number_input("Set limit (USD):", min_value=0.50, max_value=100.0, value=budget_limit, step=0.50, key="b_in")
        if st.button("Update", key="b_upd"):
            tm.max_daily_budget = nb
            st.rerun()

    st.divider()
    st.markdown("### Auto-Adaptive Cost Optimization")
    st.markdown(
        "The system automatically adjusts report depth based on confidence:\n"
        "- **Confidence > 80%**: Deep Dive report (full charts, news, backtest)\n"
        "- **Confidence 50-80%**: Standard report (charts + brief analysis)\n"
        "- **Confidence < 50%**: Brief note only (saves tokens)"
    )

    st.divider()
    st.markdown("### Cost by Agent")
    ac = tm.cost_by_agent()
    if ac:
        st.bar_chart(pd.DataFrame([{"Agent": k, "Cost ($)": v} for k, v in sorted(ac.items(), key=lambda x: -x[1])]), x="Agent", y="Cost ($)", color="#3fb950", horizontal=True)

    st.markdown("### Cost by Model")
    mc = tm.cost_by_model()
    if mc:
        st.bar_chart(pd.DataFrame([{"Model": k, "Cost ($)": v} for k, v in sorted(mc.items(), key=lambda x: -x[1])]), x="Model", y="Cost ($)", color="#6f42c1", horizontal=True)

    st.divider()

    # API Token Usage — in collapsible section (these are seed values)
    with st.expander("API Token Usage (Claude API calls)", expanded=False):
        st.caption(
            "This section shows actual Claude API calls. Most agents (Scanner, Analyst, "
            "NewsResearcher, ChartGenerator) run locally using yfinance, RSS feeds, and Python "
            "— they don't make Claude API calls. See the Agent Activity Log above for all agent work."
        )
        if USAGE_FILE.exists():
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            today = time.strftime("%Y-%m-%d")
            te = [e for e in data.get("entries", []) if e.get("date") == today]
            if te:
                df = pd.DataFrame(te)[["timestamp", "agent", "model", "prompt_tokens", "completion_tokens", "cost_usd", "task"]]
                df.columns = ["Time", "Agent", "Model", "In", "Out", "Cost ($)", "Task"]
                df["Time"] = df["Time"].str[11:19]
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.caption("No Claude API calls today.")

    st.divider()
    st.markdown("### Pricing Reference")
    st.table(pd.DataFrame([
        {"Model": "Haiku 4.5", "Input/1M": "$0.80", "Output/1M": "$4.00", "Use": "Fast Scan / Brief"},
        {"Model": "Sonnet 4.5", "Input/1M": "$3.00", "Output/1M": "$15.00", "Use": "Standard / Deep Research"},
        {"Model": "Opus 4.6", "Input/1M": "$15.00", "Output/1M": "$75.00", "Use": "Complex reasoning"},
    ]))


# ===========================
# LIVE LOGS & AGENT ACTIVITY
# ===========================
elif view == "logs":
    _ts_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    render_page_header("Live Agent Activity", view_key="logs")
    render_page_info("logs")
    st.markdown(
        f"<div class='section-header'><span class='dot' style='background:#3fb950;'></span>"
        f"<span class='label'>Real-Time Agent Feed &mdash; Auto-Refresh every 10s</span>"
        f"<span style='margin-left:auto;font-family:JetBrains Mono,monospace;font-size:0.7em;color:#3fb950;'>"
        f"● LIVE {_ts_now}</span></div>",
        unsafe_allow_html=True,
    )

    # ── Monitor status metrics ──
    monitor_status_file = PROJECT_ROOT / "src" / "data" / "monitor_status.json"
    ms = None
    if monitor_status_file.exists():
        try:
            ms = json.loads(monitor_status_file.read_text(encoding="utf-8"))
        except Exception:
            ms = None

    if ms:
        lm1, lm2, lm3, lm4 = st.columns(4)
        lm1.metric("System Status", ms.get("status", "N/A"))
        lm2.metric("Log Entries", ms.get("total_entries_seen", 0))
        lm3.metric("Errors", ms.get("errors_total", 0))
        lm4.metric("Warnings", ms.get("warnings_total", 0))

    # ── What each agent is doing NOW ──
    st.markdown("### Agent Activity")

    # Map agent names to icons and descriptions
    AGENT_ICONS = {
        "Scanner": ("📡", "Market Scanner"),
        "Analyst": ("📊", "Signal Analyst"),
        "Researcher": ("🔬", "Report Writer"),
        "NewsResearcher": ("📰", "News Intelligence"),
        "ChartGenerator": ("📈", "Chart Creator"),
        "Manager": ("🏗️", "Task Manager"),
        "MarketLearner": ("🎓", "Prediction Tracker"),
        "ChiefMonitor": ("🛡️", "System Supervisor"),
        "Discovery": ("🔭", "Market Discovery"),
        "AUTONOMOUS ACTION": ("🤖", "Autonomous Engine"),
        "AegisBrain": ("🧠", "Brain Loop"),
        "Monitor": ("👁️", "Real-Time Monitor"),
        "HindsightSim": ("⏪", "Hindsight Simulator"),
        "Scheduler": ("⏰", "Task Scheduler"),
        "CostGuard": ("💰", "Cost Guard"),
    }

    # Read last entries from log directly for freshest data
    if LOG_FILE.exists():
        raw_lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        # Parse the last 100 lines
        agent_last_action = {}  # agent -> (timestamp, message)
        recent_feed = []

        for line in raw_lines[-100:]:
            m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+)", line.strip())
            if m:
                ts, agent, msg = m.group(1), m.group(2), m.group(3)
                agent_last_action[agent] = (ts, msg)
                recent_feed.append({"ts": ts, "agent": agent, "msg": msg})

        # Show agent cards with last known action
        if agent_last_action:
            agents_sorted = sorted(agent_last_action.items(), key=lambda x: x[1][0], reverse=True)
            cols = st.columns(3)
            for i, (agent, (ts, msg)) in enumerate(agents_sorted[:12]):
                icon_info = AGENT_ICONS.get(agent, ("⚙️", agent))
                icon, display_name = icon_info

                # Determine activity status
                try:
                    from datetime import datetime as dt
                    agent_time = dt.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    now = dt.utcnow()
                    ago_seconds = int((now - agent_time).total_seconds())
                    if ago_seconds < 60:
                        ago_str = f"{ago_seconds}s ago"
                        status_color = "#3fb950"
                        status_dot = "pulse"
                    elif ago_seconds < 300:
                        ago_str = f"{ago_seconds // 60}m ago"
                        status_color = "#3fb950"
                        status_dot = "solid"
                    elif ago_seconds < 3600:
                        ago_str = f"{ago_seconds // 60}m ago"
                        status_color = "#d29922"
                        status_dot = "solid"
                    else:
                        ago_str = f"{ago_seconds // 3600}h ago"
                        status_color = "#6e7681"
                        status_dot = "solid"
                except Exception:
                    ago_str = ts
                    status_color = "#6e7681"
                    status_dot = "solid"

                is_error = "ERROR" in msg.upper()
                msg_color = "#f85149" if is_error else "#8b949e"
                border_color = "#f85149" if is_error else status_color

                with cols[i % 3]:
                    st.markdown(
                        f"<div style='background:rgba(22,27,34,0.7);border:1px solid rgba(48,54,61,0.4);"
                        f"border-left:3px solid {border_color};border-radius:10px;padding:12px 14px;"
                        f"margin-bottom:8px;'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                        f"<span style='font-size:1.2em;'>{icon}</span>"
                        f"<span style='font-size:0.65em;color:{status_color};font-family:JetBrains Mono,monospace;'>"
                        f"{'●' if status_dot == 'solid' else '◉'} {ago_str}</span></div>"
                        f"<div style='font-weight:600;font-size:0.85em;color:#e6edf3;margin:4px 0 2px 0;'>"
                        f"{display_name}</div>"
                        f"<div style='font-size:0.72em;color:{msg_color};line-height:1.4;'>"
                        f"{msg[:100]}{'...' if len(msg) > 100 else ''}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    st.divider()

    # ── Live Activity Feed (like a Twitter timeline) ──
    st.markdown("### Live Feed")
    if LOG_FILE.exists():
        raw_lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        for line in reversed(raw_lines[-30:]):
            m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+)", line.strip())
            if m:
                ts, agent, msg = m.group(1), m.group(2), m.group(3)
                icon_info = AGENT_ICONS.get(agent, ("⚙️", agent))
                icon, display_name = icon_info

                is_error = "ERROR" in msg.upper()
                is_auto = "AUTONOMOUS" in agent.upper()

                if is_error:
                    border = "#f85149"
                    bg = "rgba(248,81,73,0.05)"
                elif is_auto:
                    border = "#a371f7"
                    bg = "rgba(163,113,247,0.05)"
                elif "BUY" in msg.upper() or "STRONG BUY" in msg.upper():
                    border = "#3fb950"
                    bg = "rgba(63,185,80,0.05)"
                elif "SELL" in msg.upper():
                    border = "#f85149"
                    bg = "rgba(248,81,73,0.03)"
                else:
                    border = "rgba(48,54,61,0.5)"
                    bg = "rgba(22,27,34,0.5)"

                st.markdown(
                    f"<div style='display:flex;gap:10px;padding:8px 12px;background:{bg};"
                    f"border:1px solid rgba(48,54,61,0.3);border-left:3px solid {border};"
                    f"border-radius:6px;margin-bottom:4px;'>"
                    f"<span style='font-size:1em;min-width:22px;'>{icon}</span>"
                    f"<div style='flex:1;'>"
                    f"<span style='font-weight:600;font-size:0.8em;color:#e6edf3;'>{display_name}</span> "
                    f"<span style='font-size:0.7em;color:#8b949e;font-family:JetBrains Mono,monospace;'>{ts[11:]}</span>"
                    f"<div style='font-size:0.78em;color:#8b949e;margin-top:2px;'>{msg}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Alerts ──
    if ms and ms.get("recent_alerts"):
        st.divider()
        st.markdown("### Error Alerts")
        for alert in reversed(ms["recent_alerts"][-5:]):
            st.markdown(
                f"<div style='padding:8px 12px;background:rgba(248,81,73,0.08);"
                f"border-left:3px solid #f85149;border-radius:6px;margin-bottom:4px;'>"
                f"<span style='color:#f85149;font-weight:700;font-size:0.8em;'>[{alert['agent']}]</span> "
                f"<span style='font-size:0.8em;color:#c9d1d9;'>{alert['message']}</span>"
                f"<span style='float:right;color:#8b949e;font-size:0.7em;'>{alert['timestamp']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Raw log (collapsible) ──
    with st.expander("Raw Log Stream (last 50 entries)"):
        st.code(read_log_tail(50), language="log")


# ===========================
# PAPER TRADING SIMULATOR (Enhanced with Risk Management)
# ===========================
elif view == "paper_trading":
    _ts_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    render_page_header("Paper Trading Simulator", view_key="paper_trading")
    render_page_info("paper_trading")
    st.markdown(
        f"<div class='section-header'><span class='dot' style='background:#3fb950;'></span>"
        f"<span class='label'>Virtual Portfolio &mdash; Auto-Refresh every 10s</span>"
        f"<span style='margin-left:auto;font-family:JetBrains Mono,monospace;font-size:0.7em;color:#3fb950;'>"
        f"● LIVE {_ts_now}</span></div>",
        unsafe_allow_html=True,
    )

    _pt_watchlist = load_watchlist_summary()
    _pt_live_prices = fetch_live_prices(_pt_watchlist) if _pt_watchlist else {}
    paper_trader.record_equity_snapshot(_pt_live_prices)

    # Check automated exits (stop-loss / take-profit / trailing stop)
    _auto_closed = paper_trader.check_automated_exits(_pt_live_prices)
    for _ac in _auto_closed:
        st.toast(f"Auto-closed {_ac['asset']} ({_ac.get('exit_reason','')}) — P&L: ${_ac['pnl']:+,.2f}")
    # Check pending limit orders
    _filled = paper_trader.check_pending_orders(_pt_live_prices)
    for _fl in _filled:
        st.toast(f"Limit order filled: {_fl['asset']} @ ${_fl.get('entry_price',0):,.2f}")

    summary = paper_trader.get_portfolio_summary(_pt_live_prices)

    # ══════════════════════════════════════════════════════════════
    # RISK GUARDIAN — 3Commas-inspired real-time risk monitoring
    # ══════════════════════════════════════════════════════════════
    _rg_open_pos = paper_trader.get_open_positions_with_pnl(_pt_live_prices)
    _rg_eq_curve = paper_trader.get_equity_curve()
    _rg_dd_info = risk_manager.max_drawdown(_rg_eq_curve)
    _rg_current_return = summary.get("total_return_pct", 0)
    _rg_regime_file = PROJECT_ROOT / "src" / "data" / "macro_regime.json"
    _rg_regime_data = None
    if _rg_regime_file.exists():
        try:
            _rg_regime_data = json.loads(_rg_regime_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    _rg_geo_file = PROJECT_ROOT / "src" / "data" / "geopolitical_analysis.json"
    _rg_geo_data = None
    if _rg_geo_file.exists():
        try:
            _rg_geo_data = json.loads(_rg_geo_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    _rg_corr_groups = {"metals": ["Gold", "Silver", "Platinum", "Copper"], "crypto": ["BTC", "ETH"], "indices": ["S&P 500", "NASDAQ"], "energy": ["Oil", "Natural Gas"]}
    _rg_open_assets = [p["asset"] for p in _rg_open_pos]
    _rg_max_corr = 0
    _rg_corr_counts = {}
    for _gn, _ga in _rg_corr_groups.items():
        _cc = sum(1 for a in _rg_open_assets if a in _ga)
        _rg_corr_counts[_gn] = _cc
        if _cc > _rg_max_corr:
            _rg_max_corr = _cc
    _rg_exp_usd = sum(p.get("usd_amount", p.get("position_usd", 0)) for p in _rg_open_pos)
    _rg_exp_pct = (_rg_exp_usd / summary["starting_balance"] * 100) if summary["starting_balance"] > 0 else 0
    _rg_danger = []
    _rg_caution = []
    _rg_cb_on = False
    _rg_cb_reason = ""
    if _rg_current_return < AutoTradeConfig.DRAWDOWN_PAUSE_PCT:
        _rg_cb_on = True
        _rg_cb_reason = f"Portfolio down {_rg_current_return:.1f}% (limit: {AutoTradeConfig.DRAWDOWN_PAUSE_PCT}%)"
        _rg_danger.append("Circuit breaker triggered")
    elif _rg_current_return < AutoTradeConfig.DRAWDOWN_REDUCED_PCT:
        _rg_caution.append(f"Graduated drawdown active ({_rg_current_return:.1f}%)")
    _rg_geo_risk = _rg_geo_data.get("risk_level", "CALM") if _rg_geo_data else "CALM"
    if _rg_geo_risk == "EXTREME":
        _rg_danger.append("EXTREME geopolitical risk")
    elif _rg_geo_risk == "ELEVATED":
        _rg_caution.append("Elevated geopolitical risk")
    if _rg_max_corr >= AutoTradeConfig.MAX_CORRELATED_POSITIONS:
        _rg_caution.append(f"Max correlated positions reached ({_rg_max_corr})")
    if len(_rg_open_pos) >= AutoTradeConfig.MAX_CONCURRENT_POSITIONS:
        _rg_caution.append(f"Max positions reached ({len(_rg_open_pos)}/{AutoTradeConfig.MAX_CONCURRENT_POSITIONS})")
    if _rg_exp_pct > 80:
        _rg_caution.append(f"High exposure: {_rg_exp_pct:.0f}% of portfolio")
    if _rg_danger:
        _rg_sc = "#f85149"; _rg_sbg = "rgba(248,81,73,0.08)"; _rg_sb = "rgba(248,81,73,0.4)"; _rg_sl = "GUARDIAN: DANGER"; _rg_si = "&#9632;"
    elif _rg_caution:
        _rg_sc = "#d29922"; _rg_sbg = "rgba(210,153,34,0.08)"; _rg_sb = "rgba(210,153,34,0.4)"; _rg_sl = "GUARDIAN: CAUTION"; _rg_si = "&#9650;"
    else:
        _rg_sc = "#3fb950"; _rg_sbg = "rgba(63,185,80,0.06)"; _rg_sb = "rgba(63,185,80,0.4)"; _rg_sl = "GUARDIAN: ALL CLEAR"; _rg_si = "&#10003;"
    _rg_dd_val = abs(_rg_current_return) if _rg_current_return < 0 else 0
    _rg_dd_lim = abs(AutoTradeConfig.DRAWDOWN_PAUSE_PCT)
    _rg_dd_pct = min(_rg_dd_val / _rg_dd_lim * 100, 100) if _rg_dd_lim > 0 else 0
    _rg_ddc = "#3fb950" if _rg_dd_pct < 40 else ("#d29922" if _rg_dd_pct < 70 else "#f85149")
    _rg_cbc = "#f85149" if _rg_cb_on else "#3fb950"
    _rg_cbl = "TRIGGERED" if _rg_cb_on else "STANDBY"
    _rg_cbd = _rg_cb_reason if _rg_cb_on else "No drawdown breach"
    _rg_exc = "#d29922" if _rg_exp_pct > 60 else "#e6edf3"
    _rg_rhtml = ""
    for _r in _rg_danger + _rg_caution:
        _rc = "#f85149" if _r in _rg_danger else "#d29922"
        _rg_rhtml += f"<div style='color:{_rc};font-size:0.78em;margin-top:2px;font-family:JetBrains Mono,monospace;'>  {_r}</div>"
    st.markdown(
        f"<div style='background:{_rg_sbg};border:1px solid {_rg_sb};border-radius:10px;padding:18px 24px;margin-bottom:16px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;'>"
        f"<div><div style='font-size:1.3em;font-weight:800;color:{_rg_sc};font-family:JetBrains Mono,monospace;letter-spacing:1px;'>"
        f"<span style='font-size:0.8em;'>{_rg_si}</span> {_rg_sl}</div>{_rg_rhtml}</div>"
        f"<div style='display:flex;gap:28px;align-items:flex-start;'>"
        f"<div style='text-align:center;'><div style='color:#8b949e;font-size:0.7em;text-transform:uppercase;letter-spacing:0.5px;'>Drawdown</div>"
        f"<div style='color:{_rg_ddc};font-size:1.1em;font-weight:700;font-family:JetBrains Mono,monospace;'>{_rg_dd_val:.1f}%</div>"
        f"<div style='background:rgba(48,54,61,0.6);border-radius:4px;width:120px;height:6px;margin-top:4px;'>"
        f"<div style='background:{_rg_ddc};width:{_rg_dd_pct:.0f}%;height:100%;border-radius:4px;transition:width 0.3s ease;'></div></div>"
        f"<div style='color:#8b949e;font-size:0.6em;margin-top:2px;'>limit: {_rg_dd_lim:.0f}%</div></div>"
        f"<div style='text-align:center;'><div style='color:#8b949e;font-size:0.7em;text-transform:uppercase;letter-spacing:0.5px;'>Positions</div>"
        f"<div style='color:#e6edf3;font-size:1.1em;font-weight:700;font-family:JetBrains Mono,monospace;'>{len(_rg_open_pos)}/{AutoTradeConfig.MAX_CONCURRENT_POSITIONS}</div></div>"
        f"<div style='text-align:center;'><div style='color:#8b949e;font-size:0.7em;text-transform:uppercase;letter-spacing:0.5px;'>Exposure</div>"
        f"<div style='color:{_rg_exc};font-size:1.1em;font-weight:700;font-family:JetBrains Mono,monospace;'>{_rg_exp_pct:.0f}%</div></div>"
        f"<div style='text-align:center;'><div style='color:#8b949e;font-size:0.7em;text-transform:uppercase;letter-spacing:0.5px;'>Circuit Breaker</div>"
        f"<div style='color:{_rg_cbc};font-size:0.9em;font-weight:700;font-family:JetBrains Mono,monospace;'>{_rg_cbl}</div>"
        f"<div style='color:#8b949e;font-size:0.6em;margin-top:1px;'>{_rg_cbd}</div></div>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )
    # --- Gate Status Panel ---
    with st.expander("Gate Status Panel -- Auto-Trader Gate Diagnostics", expanded=False):
        _rg_gates = []
        _rg_gates.append({"name": "Gate 0: Master Switch", "desc": "Auto-trading enabled", "current": "ON" if AutoTradeConfig.ENABLED else "OFF", "threshold": "ON", "status": "PASS" if AutoTradeConfig.ENABLED else "FAIL"})
        _rg_gates.append({"name": "Gate 1: Signal Strength", "desc": "Signal must be actionable", "current": ", ".join(AutoTradeConfig.ALLOWED_SIGNALS), "threshold": "BUY/SELL signals only", "status": "PASS"})
        _rg_gates.append({"name": "Gate 2: Min Confidence", "desc": "Confidence must exceed threshold", "current": f"{AutoTradeConfig.MIN_CONFIDENCE_PCT:.0f}%", "threshold": f"{AutoTradeConfig.MIN_CONFIDENCE_PCT:.0f}% (regime-adjusted)", "status": "PASS"})
        _rg_gates.append({"name": "Gate 2b: Geo Risk", "desc": "Geopolitical risk overlay", "current": _rg_geo_risk, "threshold": "< EXTREME", "status": "PASS" if _rg_geo_risk != "EXTREME" else "FAIL"})
        _rg_gates.append({"name": "Gate 3: Risk/Reward", "desc": "Minimum risk/reward ratio", "current": f"{AutoTradeConfig.MIN_RISK_REWARD}:1", "threshold": f"{AutoTradeConfig.MIN_RISK_REWARD}:1", "status": "PASS"})
        _rg_gates.append({"name": "Gate 4: Lesson Filter", "desc": "Consults past trading mistakes", "current": "ACTIVE" if AutoTradeConfig.USE_LESSONS_FILTER else "OFF", "threshold": "Active", "status": "PASS" if AutoTradeConfig.USE_LESSONS_FILTER else "WARN"})
        _g5p = len(_rg_open_pos) < AutoTradeConfig.MAX_CONCURRENT_POSITIONS
        _rg_gates.append({"name": "Gate 5: Max Positions", "desc": "Position limit check", "current": str(len(_rg_open_pos)), "threshold": f"< {AutoTradeConfig.MAX_CONCURRENT_POSITIONS}", "status": "PASS" if _g5p else "FAIL"})
        _g5cp = _rg_max_corr < AutoTradeConfig.MAX_CORRELATED_POSITIONS
        _g5cd = ", ".join(f"{g}:{c}" for g, c in _rg_corr_counts.items() if c > 0) or "none"
        _rg_gates.append({"name": "Gate 5c: Correlation Guard", "desc": "Limits correlated positions per group", "current": f"max {_rg_max_corr} ({_g5cd})", "threshold": f"< {AutoTradeConfig.MAX_CORRELATED_POSITIONS} per group", "status": "PASS" if _g5cp else "FAIL"})
        _rg_gates.append({"name": "Gate 6: Cooldown Timer", "desc": "Prevents re-trading same asset too quickly", "current": f"{AutoTradeConfig.COOLDOWN_HOURS}h", "threshold": f"{AutoTradeConfig.COOLDOWN_HOURS}h between trades", "status": "PASS"})
        _g6ba = _rg_current_return < AutoTradeConfig.DRAWDOWN_REDUCED_PCT
        _rg_gates.append({"name": "Gate 6b: Graduated Drawdown", "desc": "50% size reduction at threshold", "current": f"{_rg_current_return:.1f}%", "threshold": f"> {AutoTradeConfig.DRAWDOWN_REDUCED_PCT}%", "status": "WARN" if _g6ba else "PASS"})
        _g7p = _rg_current_return >= AutoTradeConfig.DRAWDOWN_PAUSE_PCT
        _rg_gates.append({"name": "Gate 7: Drawdown Halt", "desc": "Full trading halt at max drawdown", "current": f"{_rg_current_return:.1f}%", "threshold": f"> {AutoTradeConfig.DRAWDOWN_PAUSE_PCT}%", "status": "PASS" if _g7p else "FAIL"})
        _rg_rn = _rg_regime_data.get("regime", "N/A") if _rg_regime_data else "N/A"
        _rg_gates.append({"name": "Gate 8: Regime Check", "desc": "Macro regime awareness", "current": _rg_rn, "threshold": "Adjusts sizing per regime", "status": "WARN" if _rg_rn == "HIGH_VOLATILITY" else "PASS"})
        _rg_gates.append({"name": "Gate 9: Dynamic Confidence", "desc": "Adapts confidence per-asset based on history", "current": "ACTIVE" if AutoTradeConfig.USE_DYNAMIC_CONFIDENCE else "OFF", "threshold": "Active (per-asset win rate)", "status": "PASS"})
        _rg_gr = ""
        for _gate in _rg_gates:
            if _gate["status"] == "PASS":
                _gd = '<span style="color:#3fb950;font-size:1.1em;">&#9679;</span>'; _gb = "rgba(63,185,80,0.15)"; _gc = "#3fb950"; _gt = "PASS"
            elif _gate["status"] == "FAIL":
                _gd = '<span style="color:#f85149;font-size:1.1em;">&#9679;</span>'; _gb = "rgba(248,81,73,0.15)"; _gc = "#f85149"; _gt = "FAIL"
            else:
                _gd = '<span style="color:#d29922;font-size:1.1em;">&#9679;</span>'; _gb = "rgba(210,153,34,0.15)"; _gc = "#d29922"; _gt = "WARN"
            _rg_gr += (f"<div style='display:flex;align-items:center;gap:10px;padding:7px 12px;border-bottom:1px solid rgba(48,54,61,0.3);'>"
                f"<div style='flex:0 0 20px;text-align:center;'>{_gd}</div>"
                f"<div style='flex:1;min-width:0;'><div style='color:#e6edf3;font-size:0.82em;font-weight:600;'>{_gate['name']}</div>"
                f"<div style='color:#8b949e;font-size:0.7em;'>{_gate['desc']}</div></div>"
                f"<div style='flex:0 0 auto;text-align:right;'><div style='color:#8b949e;font-size:0.75em;font-family:JetBrains Mono,monospace;'>{_gate['current']}</div>"
                f"<div style='color:#8b949e;font-size:0.65em;'>{_gate['threshold']}</div></div>"
                f"<div style='flex:0 0 55px;text-align:center;'><span style='background:{_gb};color:{_gc};font-size:0.7em;font-weight:700;padding:2px 8px;border-radius:4px;font-family:JetBrains Mono,monospace;'>{_gt}</span></div></div>")
        _rg_pc = sum(1 for g in _rg_gates if g["status"] == "PASS"); _rg_fc = sum(1 for g in _rg_gates if g["status"] == "FAIL"); _rg_wc = sum(1 for g in _rg_gates if g["status"] == "WARN")
        _rg_hc = "#3fb950" if _rg_fc == 0 else "#f85149"
        st.markdown(
            f"<div style='background:#0d1117;border:1px solid rgba(48,54,61,0.5);border-radius:8px;overflow:hidden;'>"
            f"<div style='background:rgba(22,27,34,0.9);padding:10px 16px;border-bottom:1px solid rgba(48,54,61,0.5);display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='color:#58a6ff;font-size:0.85em;font-weight:700;font-family:JetBrains Mono,monospace;'>AUTO-TRADER GATE DIAGNOSTICS</span>"
            f"<span style='color:{_rg_hc};font-size:0.78em;font-family:JetBrains Mono,monospace;'>{_rg_pc} PASS &middot; {_rg_fc} FAIL &middot; {_rg_wc} WARN</span></div>"
            f"{_rg_gr}</div>",
            unsafe_allow_html=True,
        )
    # --- Position Risk Cards ---
    if _rg_open_pos:
        st.markdown("<div style='color:#58a6ff;font-size:0.85em;font-weight:700;font-family:JetBrains Mono,monospace;margin-top:8px;margin-bottom:8px;letter-spacing:0.5px;'>POSITION RISK MONITOR</div>", unsafe_allow_html=True)
        _rg_nc = min(len(_rg_open_pos), 4)
        _rg_pcols = st.columns(_rg_nc)
        for _ix, _pos in enumerate(_rg_open_pos):
            with _rg_pcols[_ix % _rg_nc]:
                _pc = _pos.get("current_price", _pos["entry_price"]); _ppnl = _pos.get("unrealized_pnl", 0); _ppnlp = _pos.get("unrealized_pnl_pct", 0); _pdir = _pos["direction"]
                _psl = _pos.get("stop_loss"); _psl_dp = 0; _psl_du = 0; _hsl = _psl is not None and _psl > 0
                if _hsl:
                    _psl_du = (_pc - _psl) if _pdir == "long" else (_psl - _pc)
                    _psl_dp = (_psl_du / _pc * 100) if _pc > 0 else 0
                _ptp = _pos.get("take_profit"); _ptp_dp = 0; _ptp_du = 0; _htp = _ptp is not None and _ptp > 0
                if _htp:
                    _ptp_du = (_ptp - _pc) if _pdir == "long" else (_pc - _ptp)
                    _ptp_dp = (_ptp_du / _pc * 100) if _pc > 0 else 0
                _po_at = _pos.get("opened_at", ""); _ptm = "N/A"
                if _po_at:
                    try:
                        _po_dt = datetime.fromisoformat(_po_at); _el = datetime.now(timezone.utc) - _po_dt
                        _eh = int(_el.total_seconds() // 3600); _em = int((_el.total_seconds() % 3600) // 60)
                        _ptm = f"{_eh // 24}d {_eh % 24}h" if _eh > 24 else (f"{_eh}h {_em}m" if _eh > 0 else f"{_em}m")
                    except Exception:
                        pass
                if _hsl and _psl_dp > 0:
                    _rl = "HIGH" if _psl_dp < 2 else ("MEDIUM" if _psl_dp < 5 else "LOW")
                    _rlc = "#f85149" if _psl_dp < 2 else ("#d29922" if _psl_dp < 5 else "#3fb950")
                    _rlb = "rgba(248,81,73,0.15)" if _psl_dp < 2 else ("rgba(210,153,34,0.15)" if _psl_dp < 5 else "rgba(63,185,80,0.15)")
                elif _hsl and _psl_dp <= 0:
                    _rl = "CRITICAL"; _rlc = "#f85149"; _rlb = "rgba(248,81,73,0.25)"
                else:
                    _rl = "UNSET"; _rlc = "#6e7681"; _rlb = "rgba(110,118,129,0.15)"
                _ppc = "#3fb950" if _ppnl >= 0 else "#f85149"
                _pdi = "&#9650;" if _pdir == "long" else "&#9660;"
                _pdc = "#3fb950" if _pdir == "long" else "#f85149"
                if _hsl:
                    _sic = "#3fb950" if _psl_dp > 3 else ("#d29922" if _psl_dp > 1 else "#f85149")
                    _slr = f"<div style='display:flex;justify-content:space-between;margin-top:4px;'><span style='color:#8b949e;font-size:0.72em;'>Stop-Loss</span><span style='color:{_sic};font-size:0.72em;font-family:JetBrains Mono,monospace;'>{_psl_dp:.1f}% (${abs(_psl_du):,.2f})</span></div>"
                else:
                    _slr = "<div style='display:flex;justify-content:space-between;margin-top:4px;'><span style='color:#8b949e;font-size:0.72em;'>Stop-Loss</span><span style='color:#6e7681;font-size:0.72em;font-style:italic;'>none</span></div>"
                if _htp:
                    _tpr = f"<div style='display:flex;justify-content:space-between;margin-top:2px;'><span style='color:#8b949e;font-size:0.72em;'>Take-Profit</span><span style='color:#58a6ff;font-size:0.72em;font-family:JetBrains Mono,monospace;'>{_ptp_dp:.1f}% (${abs(_ptp_du):,.2f})</span></div>"
                else:
                    _tpr = "<div style='display:flex;justify-content:space-between;margin-top:2px;'><span style='color:#8b949e;font-size:0.72em;'>Take-Profit</span><span style='color:#6e7681;font-size:0.72em;font-style:italic;'>none</span></div>"
                st.markdown(
                    f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);border-radius:8px;padding:12px 14px;margin-bottom:8px;border-left:3px solid {_rlc};'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<span style='color:{_pdc};font-size:0.8em;'>{_pdi}</span>"
                    f"<span style='color:#e6edf3;font-weight:700;font-size:0.9em;'>{_pos['asset']}</span>"
                    f"<span style='background:{_rlb};color:{_rlc};font-size:0.65em;font-weight:700;padding:2px 6px;border-radius:3px;font-family:JetBrains Mono,monospace;'>{_rl}</span></div>"
                    f"<div style='display:flex;justify-content:space-between;margin-top:8px;'><span style='color:#8b949e;font-size:0.72em;'>P&L</span>"
                    f"<span style='color:{_ppc};font-size:0.85em;font-weight:700;font-family:JetBrains Mono,monospace;'>${_ppnl:+,.2f} ({_ppnlp:+.2f}%)</span></div>"
                    f"{_slr}{_tpr}"
                    f"<div style='display:flex;justify-content:space-between;margin-top:4px;padding-top:4px;border-top:1px solid rgba(48,54,61,0.3);'>"
                    f"<span style='color:#8b949e;font-size:0.68em;'>Time in trade</span>"
                    f"<span style='color:#8b949e;font-size:0.68em;font-family:JetBrains Mono,monospace;'>{_ptm}</span></div></div>",
                    unsafe_allow_html=True,
                )
    st.divider()
    # ── END RISK GUARDIAN ──

    # ── Section A: Portfolio Metrics ──
    pm1, pm2, pm3, pm4, pm5 = st.columns(5)
    with pm1:
        st.metric("Cash", f"${summary['cash']:,.2f}")
    with pm2:
        st.metric("Equity", f"${summary['equity']:,.2f}", delta=f"{summary['total_return_pct']:+.2f}%")
    with pm3:
        st.metric("Open P&L", f"${summary['open_pnl']:,.2f}",
                  delta=f"${summary['open_pnl']:+,.2f}",
                  delta_color="normal" if summary["open_pnl"] >= 0 else "inverse")
    with pm4:
        _wr = f"{summary['win_rate']}%" if summary["total_trades"] > 0 else "N/A"
        st.metric("Win Rate", _wr, delta=f"{summary['total_trades']} trades")
    with pm5:
        _dd = risk_manager.max_drawdown(paper_trader.get_equity_curve())
        st.metric("Max Drawdown", f"{_dd['max_drawdown_pct']:.1f}%")

    st.divider()

    # ── Section B: Trade Form + Open Positions ──
    col_form, col_positions = st.columns([1, 2])

    with col_form:
        st.markdown("### New Trade")
        _asset_options = {}
        for name, d in _pt_watchlist.items():
            live_p = _pt_live_prices.get(name, d.get("price", 0))
            _asset_options[name] = {"ticker": d.get("ticker", ""), "price": live_p,
                                    "signal": d.get("signal_label", "N/A")}

        if not _asset_options:
            st.info("No assets in watchlist. Run a scan first.")
        else:
            with st.form("paper_trade_form", clear_on_submit=True):
                asset_choice = st.selectbox("Asset", list(_asset_options.keys()))
                _sel = _asset_options.get(asset_choice, {})
                _sel_price = _sel.get("price", 0)
                _sel_signal = _sel.get("signal", "N/A")

                st.caption(f"Live: **${_sel_price:,.2f}** | Signal: **{_sel_signal}**")
                direction = st.radio("Direction", ["Long", "Short"], horizontal=True)

                _order_type = st.selectbox("Order Type", ["Market", "Limit", "Stop-Limit"])
                _limit_p = None
                if _order_type != "Market":
                    _limit_p = st.number_input("Limit Price", min_value=0.01, value=float(_sel_price) if _sel_price else 1.0, step=0.01)

                usd_amount = st.number_input("Amount (USD)", min_value=1.0,
                                             max_value=float(summary["cash"]) if summary["cash"] > 0 else 1.0,
                                             value=min(100.0, summary["cash"]) if summary["cash"] > 0 else 1.0,
                                             step=10.0)

                # Risk management fields
                st.caption("Risk Management (optional)")
                _rc1, _rc2 = st.columns(2)
                with _rc1:
                    _sl_pct = st.number_input("Stop-Loss %", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="sl_pct")
                with _rc2:
                    _tp_pct = st.number_input("Take-Profit %", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="tp_pct")
                _trail = st.number_input("Trailing Stop %", min_value=0.0, max_value=20.0, value=0.0, step=0.5)

                submitted = st.form_submit_button("Open Position", use_container_width=True)

                if submitted and _sel_price > 0:
                    # Calculate SL/TP prices
                    _sl_price = None
                    _tp_price = None
                    if _sl_pct > 0:
                        st_data = risk_manager.calculate_stop_take(_sel_price, direction.lower(), _sl_pct, _tp_pct if _tp_pct > 0 else None)
                        _sl_price = st_data["stop_loss"]
                        if _tp_pct > 0:
                            _tp_price = st_data["take_profit"]
                    elif _tp_pct > 0:
                        st_data = risk_manager.calculate_stop_take(_sel_price, direction.lower(), None, _tp_pct)
                        _tp_price = st_data["take_profit"]

                    result = paper_trader.open_position(
                        asset=asset_choice, ticker=_sel.get("ticker", ""),
                        direction=direction.lower(), usd_amount=usd_amount,
                        price=_sel_price, stop_loss=_sl_price, take_profit=_tp_price,
                        trailing_stop_pct=_trail if _trail > 0 else None,
                        order_type=_order_type.lower().replace("-", "_"),
                        limit_price=_limit_p, signal_hint=_sel_signal,
                    )
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(f"{'Queued' if _limit_p else 'Opened'} {direction} {asset_choice}")
                        st.rerun()
                elif submitted:
                    st.warning("Cannot open trade — price unavailable.")

    with col_positions:
        st.markdown("### Open Positions")
        open_pos = paper_trader.get_open_positions_with_pnl(_pt_live_prices)
        if not open_pos:
            st.caption("No open positions.")
        else:
            for pos in open_pos:
                _dir_icon = "▲" if pos["direction"] == "long" else "▼"
                _pnl_color = "#3fb950" if pos["unrealized_pnl"] >= 0 else "#f85149"
                _risk_info = ""
                if pos.get("stop_loss"):
                    _risk_info += f" | SL: ${pos['stop_loss']:,.2f}"
                if pos.get("take_profit"):
                    _risk_info += f" | TP: ${pos['take_profit']:,.2f}"
                if pos.get("trailing_stop_pct"):
                    _risk_info += f" | Trail: {pos['trailing_stop_pct']}%"
                _pos_size_str = f"${pos['usd_amount']:,.2f}" if pos.get("usd_amount") else ""
                st.markdown(
                    f"<div style='background:rgba(22,27,34,0.9);border:1px solid rgba(48,54,61,0.5);"
                    f"border-radius:8px;padding:12px 16px;margin-bottom:8px;'>"
                    f"<span style='font-weight:600;color:#e6edf3;'>{_dir_icon} {pos['asset']}</span>"
                    f" <span style='color:#8b949e;font-size:0.85em;'>"
                    f"{pos['direction'].upper()} | {pos['quantity']:.4f} units | {_pos_size_str}</span><br>"
                    f"<span style='color:#8b949e;font-size:0.85em;'>Entry: ${pos['entry_price']:,.2f}"
                    f" &rarr; Now: ${pos['current_price']:,.2f}{_risk_info}</span>"
                    f" <span style='color:{_pnl_color};font-weight:600;'>"
                    f"${pos['unrealized_pnl']:+,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # Action buttons row: Asset Link + Close Position
                _pt_pos_c1, _pt_pos_c2 = st.columns([1, 1])
                with _pt_pos_c1:
                    asset_link_button(pos["asset"], f"pt_{pos['id']}")
                with _pt_pos_c2:
                    if st.button(f"Close ({pos['id'][:6]})", key=f"close_{pos['id']}", use_container_width=True):
                        close_price = _pt_live_prices.get(pos["asset"], pos["current_price"])
                        result = paper_trader.close_position(pos["id"], close_price)
                        if "error" not in result:
                            st.success(f"Closed {pos['asset']} -- P&L: ${result['pnl']:+,.2f}")
                            st.rerun()

                # Position Modification expander
                with st.expander(f"Modify {pos['asset']} ({pos['id'][:6]})", expanded=False):
                    _mod_tab1, _mod_tab2, _mod_tab3 = st.tabs(["Stop-Loss / Take-Profit", "Partial Close", "Notes"])

                    with _mod_tab1:
                        _mod_sl_col, _mod_tp_col = st.columns(2)
                        with _mod_sl_col:
                            _cur_sl = pos.get("stop_loss") or 0.0
                            _new_sl = st.number_input(
                                "Stop-Loss Price",
                                min_value=0.0,
                                value=float(_cur_sl),
                                step=0.01,
                                format="%.2f",
                                key=f"mod_sl_{pos['id']}",
                                help="Set to 0 to remove stop-loss.",
                            )
                            if st.button("Update SL", key=f"upd_sl_{pos['id']}", use_container_width=True):
                                _sl_val = _new_sl if _new_sl > 0 else None
                                _sl_res = paper_trader.update_stop_loss(pos["id"], _sl_val)
                                if "error" not in _sl_res:
                                    _sl_msg = f"${_new_sl:,.2f}" if _sl_val else "removed"
                                    st.success(f"Stop-loss updated to {_sl_msg}")
                                    st.rerun()
                                else:
                                    st.error(_sl_res["error"])

                        with _mod_tp_col:
                            _cur_tp = pos.get("take_profit") or 0.0
                            _new_tp = st.number_input(
                                "Take-Profit Price",
                                min_value=0.0,
                                value=float(_cur_tp),
                                step=0.01,
                                format="%.2f",
                                key=f"mod_tp_{pos['id']}",
                                help="Set to 0 to remove take-profit.",
                            )
                            if st.button("Update TP", key=f"upd_tp_{pos['id']}", use_container_width=True):
                                _tp_val = _new_tp if _new_tp > 0 else None
                                _tp_res = paper_trader.update_take_profit(pos["id"], _tp_val)
                                if "error" not in _tp_res:
                                    _tp_msg = f"${_new_tp:,.2f}" if _tp_val else "removed"
                                    st.success(f"Take-profit updated to {_tp_msg}")
                                    st.rerun()
                                else:
                                    st.error(_tp_res["error"])

                    with _mod_tab2:
                        st.caption("Close a portion of this position at the current market price.")
                        _partial_pct = st.select_slider(
                            "Close Percentage",
                            options=[25, 50, 75],
                            value=50,
                            key=f"partial_pct_{pos['id']}",
                        )
                        _partial_qty = pos["quantity"] * _partial_pct / 100
                        _partial_usd = pos.get("usd_amount", 0) * _partial_pct / 100
                        st.caption(
                            f"Will close {_partial_pct}% = {_partial_qty:.4f} units "
                            f"(~${_partial_usd:,.2f}) at ${pos['current_price']:,.2f}"
                        )
                        if st.button(f"Close {_partial_pct}%", key=f"partial_close_{pos['id']}", use_container_width=True):
                            _pc_price = _pt_live_prices.get(pos["asset"], pos["current_price"])
                            _pc_res = paper_trader.partial_close(pos["id"], _partial_pct, _pc_price)
                            if "error" not in _pc_res:
                                st.success(
                                    f"Closed {_partial_pct}% of {pos['asset']} -- "
                                    f"P&L: ${_pc_res['pnl']:+,.2f}"
                                )
                                st.rerun()
                            else:
                                st.error(_pc_res["error"])

                    with _mod_tab3:
                        _pos_note_existing = pos.get("notes", "")
                        _pos_note_val = st.text_area(
                            "Position Note",
                            value=_pos_note_existing,
                            key=f"pos_note_{pos['id']}",
                            height=80,
                            placeholder="Add a note to this position...",
                            label_visibility="collapsed",
                        )
                        if st.button("Save Note", key=f"pos_note_save_{pos['id']}", use_container_width=True):
                            if paper_trader.save_position_note(pos["id"], _pos_note_val):
                                st.success(f"Note saved for {pos['asset']}.")
                                st.rerun()
                            else:
                                st.error("Failed to save note.")

        # Correlation risk warning
        if len(open_pos) >= 2:
            _corr_pairs = {
                frozenset(["Gold", "Silver"]): "Gold & Silver are highly correlated — both react to same macro forces",
                frozenset(["BTC", "ETH"]): "BTC & ETH are highly correlated — crypto moves together",
                frozenset(["S&P 500", "NASDAQ"]): "S&P 500 & NASDAQ overlap heavily — concentrated equity exposure",
                frozenset(["Gold", "Platinum"]): "Gold & Platinum share precious metals dynamics",
                frozenset(["Oil", "Natural Gas"]): "Oil & Natural Gas are both energy commodities",
                frozenset(["Copper", "Silver"]): "Copper & Silver share industrial metal characteristics",
            }
            _open_assets = {p["asset"] for p in open_pos}
            _corr_warnings = []
            for _pair, _msg in _corr_pairs.items():
                if _pair.issubset(_open_assets):
                    _corr_warnings.append(_msg)

            if _corr_warnings:
                _corr_html = "".join(
                    f"<div style='color:#d29922;font-size:0.82em;margin-top:4px;'>⚠️ {w}</div>"
                    for w in _corr_warnings
                )
                st.markdown(
                    f"<div style='background:rgba(210,153,34,0.08);border:1px solid #d29922;"
                    f"border-radius:8px;padding:12px 16px;margin-top:8px;margin-bottom:8px;'>"
                    f"<div style='color:#d29922;font-weight:700;font-size:0.85em;'>"
                    f"⚠️ CORRELATION RISK DETECTED</div>"
                    f"{_corr_html}"
                    f"<div style='color:#8b949e;font-size:0.75em;margin-top:6px;'>"
                    f"Holding correlated positions amplifies both gains and losses. "
                    f"Consider reducing position sizes or closing one side.</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Pending orders
        _pending = paper_trader.get_pending_orders()
        if _pending:
            st.markdown("### Pending Orders")
            for po in _pending:
                st.markdown(
                    f"<div style='background:rgba(22,27,34,0.7);border:1px dashed rgba(255,166,87,0.4);"
                    f"border-radius:8px;padding:10px 16px;margin-bottom:6px;'>"
                    f"<span style='color:#ffa657;'>{po['order_type'].upper()}</span>"
                    f" {po['direction'].upper()} {po['asset']} @ ${po['limit_price']:,.2f}"
                    f" — ${po['usd_amount']:,.2f}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Cancel ({po['id']})", key=f"cancel_{po['id']}", use_container_width=True):
                    paper_trader.cancel_order(po["id"])
                    st.rerun()

    st.divider()

    # ── Section C: Autonomous Trading Bot ──
    st.markdown("### Autonomous Trading Bot")
    st.markdown(
        "<div style='color:#8b949e;font-size:0.85em;margin-bottom:12px;'>"
        "The bot scans all assets, evaluates signals against 8+ gates (confidence, regime, geo risk, "
        "lessons learned, position limits), and automatically opens/closes paper trades.</div>",
        unsafe_allow_html=True,
    )

    # ── Auto-Scheduler ──
    _sched_file = PROJECT_ROOT / "memory" / "bot_schedule.json"
    _sched_cfg = {"enabled": False, "interval_min": 30, "last_auto_run": ""}
    if _sched_file.exists():
        try:
            _sched_cfg = json.loads(_sched_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    _sched_c1, _sched_c2, _sched_c3, _sched_c4 = st.columns([1.5, 1, 1, 1.5])
    with _sched_c1:
        _sched_on = st.toggle(
            "Auto-Schedule Bot",
            value=_sched_cfg.get("enabled", False),
            key="bot_auto_sched_toggle",
            help="When enabled, the bot runs automatically every N minutes while this page is open.",
        )
    with _sched_c2:
        _sched_interval = st.selectbox(
            "Every",
            [5, 10, 15, 30, 60],
            index=[5, 10, 15, 30, 60].index(_sched_cfg.get("interval_min", 30)),
            key="bot_sched_interval",
            disabled=not _sched_on,
        )
    with _sched_c3:
        _sched_last_str = _sched_cfg.get("last_auto_run", "")
        if _sched_last_str:
            try:
                _sched_last_dt = datetime.fromisoformat(_sched_last_str)
                _sched_ago = (datetime.now(timezone.utc) - _sched_last_dt).total_seconds()
                _sched_ago_fmt = f"{int(_sched_ago // 60)}m {int(_sched_ago % 60)}s ago"
            except Exception:
                _sched_ago_fmt = "N/A"
                _sched_ago = 9999
        else:
            _sched_ago_fmt = "Never"
            _sched_ago = 9999
        st.metric("Last Auto-Run", _sched_ago_fmt)
    with _sched_c4:
        if _sched_on:
            _next_in = max(0, _sched_interval * 60 - _sched_ago) if _sched_last_str else 0
            _next_fmt = f"{int(_next_in // 60)}m {int(_next_in % 60)}s" if _next_in > 0 else "NOW"
            _sched_status_color = "#3fb950"
            _sched_status_text = f"ACTIVE — next in {_next_fmt}"
        else:
            _sched_status_color = "#6e7681"
            _sched_status_text = "PAUSED"
        st.markdown(
            f"<div style='padding:8px 0;'>"
            f"<span style='color:{_sched_status_color};font-family:JetBrains Mono,monospace;"
            f"font-size:0.85em;font-weight:700;'>● {_sched_status_text}</span></div>",
            unsafe_allow_html=True,
        )

    # Save schedule config if changed
    _new_sched = {"enabled": _sched_on, "interval_min": _sched_interval, "last_auto_run": _sched_cfg.get("last_auto_run", "")}
    if _new_sched["enabled"] != _sched_cfg.get("enabled") or _new_sched["interval_min"] != _sched_cfg.get("interval_min"):
        _sched_file.parent.mkdir(parents=True, exist_ok=True)
        _sched_file.write_text(json.dumps(_new_sched, indent=2), encoding="utf-8")

    # Auto-run logic: if schedule is ON and enough time has passed, run a cycle
    _auto_ran = False
    if _sched_on and _sched_ago >= _sched_interval * 60:
        try:
            from auto_trader import AutoTrader as _AT_auto
            _bot_auto = _AT_auto()
            _auto_cycle = _bot_auto.run_autonomous_cycle(_pt_watchlist)
            _auto_opened = len(_auto_cycle.get("trades_opened", []))
            _auto_closed = len(_auto_cycle.get("exits_closed", []))
            _auto_errors = len(_auto_cycle.get("errors", []))
            # Update last_auto_run timestamp
            _new_sched["last_auto_run"] = datetime.now(timezone.utc).isoformat()
            _sched_file.write_text(json.dumps(_new_sched, indent=2), encoding="utf-8")
            _auto_ran = True
            if _auto_opened or _auto_closed:
                st.toast(f"Auto-cycle: Opened {_auto_opened} | Closed {_auto_closed} | Errors {_auto_errors}")
        except Exception as _auto_err:
            st.toast(f"Auto-cycle error: {_auto_err}", icon="⚠️")

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    # ── Manual Controls ──
    _bot_col1, _bot_col2, _bot_col3 = st.columns(3)
    with _bot_col1:
        if st.button("Run Bot Cycle Now", key="run_bot_cycle", use_container_width=True, type="primary"):
            with st.spinner("Running autonomous trading cycle... (scanning + evaluating + trading)"):
                try:
                    from auto_trader import AutoTrader as _AT
                    _bot = _AT()
                    _cycle = _bot.run_autonomous_cycle(_pt_watchlist)
                    _n_opened = len(_cycle.get("trades_opened", []))
                    _n_closed = len(_cycle.get("exits_closed", []))
                    _n_skip = len(_cycle.get("trades_skipped", []))
                    _n_err = len(_cycle.get("errors", []))
                    st.success(
                        f"Cycle complete! Opened: {_n_opened} | Closed: {_n_closed} | "
                        f"Skipped: {_n_skip} | Errors: {_n_err}"
                    )
                    st.rerun()
                except Exception as _bot_err:
                    st.error(f"Bot cycle failed: {_bot_err}")

    with _bot_col2:
        if st.button("Check Exits Only", key="check_exits", use_container_width=True):
            with st.spinner("Checking stop-loss / take-profit / trailing stops..."):
                try:
                    from auto_trader import AutoTrader as _AT2
                    _bot2 = _AT2()
                    _closed2 = _bot2.check_exits(_pt_live_prices)
                    if _closed2:
                        for _c2 in _closed2:
                            st.info(f"Closed {_c2['asset']}: {_c2.get('exit_reason', '')} | P&L: ${_c2['pnl']:+,.2f}")
                        st.rerun()
                    else:
                        st.info("No exits triggered.")
                except Exception as _ex_err:
                    st.error(f"Exit check failed: {_ex_err}")

    with _bot_col3:
        if st.button("View Bot Activity Log", key="view_bot_log", use_container_width=True):
            st.session_state["_show_bot_log"] = not st.session_state.get("_show_bot_log", False)

    # Bot activity log display
    if st.session_state.get("_show_bot_log"):
        _bot_log_file = PROJECT_ROOT / "memory" / "bot_activity.json"
        if _bot_log_file.exists():
            try:
                _bot_activities = json.loads(_bot_log_file.read_text(encoding="utf-8"))
                _recent_acts = list(reversed(_bot_activities[-10:]))
                for _act in _recent_acts:
                    _act_ts = _act.get("timestamp", "")[:19].replace("T", " ")
                    _act_regime = _act.get("regime", "N/A")
                    _act_geo = _act.get("geo_risk", "N/A")
                    _act_opened = len(_act.get("trades_opened", []))
                    _act_closed = len(_act.get("exits_closed", []))
                    _act_equity = _act.get("portfolio_equity", 0)
                    _act_ret = _act.get("portfolio_return_pct", 0)
                    _act_ret_color = "#3fb950" if _act_ret >= 0 else "#f85149"

                    _opened_items = ""
                    for _o in _act.get("trades_opened", []):
                        _opened_items += f"<div style='color:#3fb950;font-size:0.78em;margin-left:16px;'>+ {_o['asset']} {_o.get('direction','').upper()} ${_o.get('amount',0):,.0f}</div>"
                    _closed_items = ""
                    for _c in _act.get("exits_closed", []):
                        _c_color = "#3fb950" if _c.get("pnl", 0) >= 0 else "#f85149"
                        _closed_items += f"<div style='color:{_c_color};font-size:0.78em;margin-left:16px;'>x {_c['asset']} ${_c.get('pnl',0):+,.2f} ({_c.get('reason','')})</div>"

                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);border-radius:8px;"
                        f"padding:12px 16px;margin-bottom:6px;'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                        f"<span style='color:#58a6ff;font-size:0.8em;font-family:JetBrains Mono,monospace;'>{_act_ts}</span>"
                        f"<span style='color:{_act_ret_color};font-weight:700;font-size:0.85em;'>"
                        f"${_act_equity:,.2f} ({_act_ret:+.2f}%)</span></div>"
                        f"<div style='color:#8b949e;font-size:0.78em;margin-top:4px;'>"
                        f"Regime: {_act_regime} | Geo: {_act_geo} | Opened: {_act_opened} | Closed: {_act_closed}</div>"
                        f"{_opened_items}{_closed_items}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            except Exception:
                st.caption("No bot activity log found.")
        else:
            st.caption("No bot activity log found. Run a bot cycle to start.")

    # Trade Decision Log
    _decisions_file = PROJECT_ROOT / "memory" / "trade_decisions.json"
    if _decisions_file.exists():
        try:
            _all_decisions = json.loads(_decisions_file.read_text(encoding="utf-8"))
            _recent_decisions = list(reversed(_all_decisions[-15:]))
            if _recent_decisions:
                with st.expander(f"Recent Trade Decisions ({len(_all_decisions)} total)"):
                    for _d in _recent_decisions:
                        _d_action = _d.get("action", "SKIP")
                        _d_color = "#3fb950" if _d_action == "TRADE" else ("#f85149" if _d_action == "CLOSE" else "#6e7681")
                        _d_ts = _d.get("timestamp", "")[:19].replace("T", " ")
                        st.markdown(
                            f"<div style='padding:6px 12px;margin-bottom:4px;border-left:3px solid {_d_color};"
                            f"background:rgba(22,27,34,0.5);border-radius:4px;'>"
                            f"<span style='color:{_d_color};font-weight:700;font-size:0.8em;'>{_d_action}</span>"
                            f" <span style='color:#e6edf3;font-size:0.85em;'>{_d.get('asset', '')}</span>"
                            f" <span style='color:#8b949e;font-size:0.75em;'>{_d.get('signal_label', '')}</span>"
                            f"<div style='color:#8b949e;font-size:0.72em;'>{_d_ts} — {_d.get('reason', '')[:120]}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
        except Exception:
            pass

    st.divider()

    # ── Section D: Equity Curve ──
    st.markdown("### Equity Curve")
    eq_curve = paper_trader.get_equity_curve()
    if len(eq_curve) >= 2:
        _eq_fig = performance_analytics.equity_drawdown_chart(eq_curve, summary["starting_balance"])
        st.plotly_chart(_eq_fig, use_container_width=True)
    else:
        st.caption("Equity curve will appear after a few refreshes.")

    st.divider()

    # ── Section E: Trade History ──
    st.markdown("### Trade History")
    history = paper_trader.get_trade_history()
    if history:
        hist_rows = []
        for _htrade in history:
            hist_rows.append({
                "Asset": _htrade["asset"], "Dir": _htrade["direction"].upper(),
                "Entry": f"${_htrade['entry_price']:,.2f}", "Exit": f"${_htrade['exit_price']:,.2f}",
                "Amount": f"${_htrade['usd_amount']:,.2f}", "P&L": f"${_htrade['pnl']:+,.2f}",
                "P&L %": f"{_htrade['pnl_pct']:+.2f}%", "Exit Reason": _htrade.get("exit_reason", "manual"),
                "Closed": _htrade["closed_at"][:16].replace("T", " "),
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)

        _ws1, _ws2, _ws3, _ws4 = st.columns(4)
        _total_rpnl = sum(_htrade["pnl"] for _htrade in history)
        _best = max(history, key=lambda _htrade: _htrade["pnl"])
        _worst = min(history, key=lambda t: t["pnl"])
        with _ws1:
            st.metric("Realized P&L", f"${_total_rpnl:+,.2f}")
        with _ws2:
            st.metric("Wins / Losses", f"{summary['wins']}W / {summary['losses']}L")
        with _ws3:
            st.metric("Best Trade", f"${_best['pnl']:+,.2f}", delta=_best["asset"])
        with _ws4:
            st.metric("Worst Trade", f"${_worst['pnl']:+,.2f}", delta=_worst["asset"])

        # CSV Export
        _csv_data = paper_trader.export_trades_csv()
        if _csv_data:
            st.download_button("Export Trade History (CSV)", _csv_data, "aegis_trades.csv", "text/csv")
    else:
        st.caption("No closed trades yet. Run the bot or open manual trades above.")

    # ── Section F: Reset Portfolio ──
    with st.expander("Reset Portfolio"):
        st.warning("This will delete all positions and trade history.")
        _reset_bal = st.number_input("Starting balance", min_value=100.0, value=1000.0, step=100.0, key="reset_bal")
        if st.button("Reset to Fresh Start", type="primary", key="reset_portfolio"):
            paper_trader.reset_portfolio(_reset_bal)
            st.success(f"Portfolio reset with ${_reset_bal:,.2f}")
            st.rerun()


# ===========================
# ADVANCED CHARTS
# ===========================
elif view == "charts":
    render_page_header("Advanced Charts", view_key="charts")
    render_page_info("charts")
    _ch_watchlist = load_watchlist_summary()
    if not _ch_watchlist:
        st.info("No assets in watchlist. Run a scan first.")
    else:
        _ch_cols = st.columns([2, 1, 1, 1, 1])
        with _ch_cols[0]:
            _ch_asset = st.selectbox("Asset", list(_ch_watchlist.keys()), key="chart_asset")
        with _ch_cols[1]:
            _ch_tf = st.selectbox("Timeframe", ["1D (5m)", "1W (15m)", "1M", "3M", "6M", "1Y"], index=4, key="chart_tf")
        with _ch_cols[2]:
            _ch_patterns = st.checkbox("Show Patterns", value=True, key="chart_pat")
        with _ch_cols[3]:
            _ch_sr = st.checkbox("Support/Resistance", value=True, key="chart_sr")
        with _ch_cols[4]:
            _ch_trendlines = st.checkbox("Auto-Trendlines", value=True, key="chart_trendlines")

        _ch_ticker = _ch_watchlist[_ch_asset].get("ticker", "")
        if _ch_ticker:
            _tf_map = {"1D (5m)": ("1d", "5m"), "1W (15m)": ("5d", "15m"), "1M": ("1mo", "1d"),
                       "3M": ("3mo", "1d"), "6M": ("6mo", "1d"), "1Y": ("1y", "1d")}
            _period, _interval = _tf_map.get(_ch_tf, ("6mo", "1d"))
            _ch_df = chart_engine.fetch_ohlcv(_ch_ticker, period=_period, interval=_interval)
            if not _ch_df.empty:
                _ch_fig = chart_engine.build_candlestick_chart(
                    _ch_df, title=f"{_ch_asset} ({_ch_ticker})",
                    show_patterns=_ch_patterns, show_sr=_ch_sr,
                )

                # ── Auto-Trendline Overlay (TrendSpider-style) ──
                _tl_sr_data = None
                _tl_trend_data = None
                if _ch_trendlines:
                    try:
                        _tl_sr_data = chart_engine.detect_support_resistance(_ch_df, window=20, num_levels=3)
                        _tl_trend_data = chart_engine.detect_trendlines(_ch_df, window=20)
                    except Exception:
                        _tl_sr_data = None
                        _tl_trend_data = None
                    if _tl_sr_data:
                        for _sr_s in _tl_sr_data.get("support", []):
                            _sr_lvl, _sr_lo, _sr_hi, _sr_touches = _sr_s["level"], _sr_s["zone_lo"], _sr_s["zone_hi"], _sr_s["touches"]
                            if _sr_lo != _sr_hi:
                                _ch_fig.add_hrect(y0=_sr_lo, y1=_sr_hi, fillcolor="rgba(63,185,80,0.07)", line_width=0, row=1, col=1)
                            _ch_fig.add_hline(y=_sr_lvl, line_dash="dash", line_color="rgba(63,185,80,0.6)", line_width=1.5, annotation_text=f"S {_sr_lvl:,.2f} ({_sr_touches}x)", annotation_font_color="#3fb950", annotation_font_size=10, annotation_position="bottom left", row=1, col=1)
                        for _sr_r in _tl_sr_data.get("resistance", []):
                            _sr_lvl, _sr_lo, _sr_hi, _sr_touches = _sr_r["level"], _sr_r["zone_lo"], _sr_r["zone_hi"], _sr_r["touches"]
                            if _sr_lo != _sr_hi:
                                _ch_fig.add_hrect(y0=_sr_lo, y1=_sr_hi, fillcolor="rgba(248,81,73,0.07)", line_width=0, row=1, col=1)
                            _ch_fig.add_hline(y=_sr_lvl, line_dash="dash", line_color="rgba(248,81,73,0.6)", line_width=1.5, annotation_text=f"R {_sr_lvl:,.2f} ({_sr_touches}x)", annotation_font_color="#f85149", annotation_font_size=10, annotation_position="top left", row=1, col=1)
                    if _tl_trend_data:
                        for _tl in _tl_trend_data:
                            _tl_color = "#3fb950" if _tl["direction"] == "up" else "#f85149"
                            _tl_name = "Uptrend" if _tl["direction"] == "up" else "Downtrend"
                            _ch_fig.add_trace(go.Scatter(x=[_tl["start_date"], _tl["end_date"]], y=[_tl["start_price"], _tl["end_price"]], mode="lines", line=dict(color=_tl_color, width=2, dash="solid"), name=f"{_tl_name} (R\u00b2={_tl['r_squared']:.2f})", showlegend=True, hoverinfo="name+y"), row=1, col=1)

                st.plotly_chart(_ch_fig, use_container_width=True)

                # ── Key Levels Summary Card ──
                if _ch_trendlines and _tl_sr_data and (_tl_sr_data.get("support") or _tl_sr_data.get("resistance")):
                    _ch_df_kl = chart_engine.add_indicators(_ch_df)
                    _kl_current = float(_ch_df_kl["Close"].iloc[-1])
                    _kl_supports = sorted(_tl_sr_data.get("support", []), key=lambda x: x["level"], reverse=True)
                    _kl_resists = sorted(_tl_sr_data.get("resistance", []), key=lambda x: x["level"])
                    _kl_near_sup = next((_s for _s in _kl_supports if _s["level"] < _kl_current), None)
                    _kl_near_res = next((_r for _r in _kl_resists if _r["level"] > _kl_current), None)
                    _kl_sup_text = ""
                    if _kl_near_sup:
                        _kl_sd = round((_kl_near_sup["level"] - _kl_current) / _kl_current * 100, 2)
                        _kl_sup_text = f"<span style='color:#3fb950;font-weight:700;font-family:JetBrains Mono,monospace;'>${_kl_near_sup['level']:,.2f}</span> <span style='color:#8b949e;'>({_kl_sd:+.2f}%)</span>"
                    _kl_res_text = ""
                    if _kl_near_res:
                        _kl_rd = round((_kl_near_res["level"] - _kl_current) / _kl_current * 100, 2)
                        _kl_res_text = f"<span style='color:#f85149;font-weight:700;font-family:JetBrains Mono,monospace;'>${_kl_near_res['level']:,.2f}</span> <span style='color:#8b949e;'>({_kl_rd:+.2f}%)</span>"
                    _kl_rows = ""
                    for _s in sorted(_tl_sr_data.get("support", []), key=lambda x: x["level"], reverse=True):
                        _d = round((_s["level"] - _kl_current) / _kl_current * 100, 2)
                        _z = f"${_s['zone_lo']:,.2f} - ${_s['zone_hi']:,.2f}" if _s["zone_lo"] != _s["zone_hi"] else "-"
                        _dc = "#3fb950" if _d >= 0 else "#f85149"
                        _kl_rows += f"<tr style='border-bottom:1px solid rgba(48,54,61,0.3);'><td style='padding:8px 12px;color:#3fb950;font-weight:600;'>SUPPORT</td><td style='padding:8px 12px;font-family:JetBrains Mono,monospace;'>${_s['level']:,.2f}</td><td style='padding:8px 12px;color:#8b949e;font-family:JetBrains Mono,monospace;'>{_z}</td><td style='padding:8px 12px;font-family:JetBrains Mono,monospace;color:{_dc};'>{_d:+.2f}%</td><td style='padding:8px 12px;text-align:center;'>{_s['touches']}</td></tr>"
                    for _r in sorted(_tl_sr_data.get("resistance", []), key=lambda x: x["level"]):
                        _d = round((_r["level"] - _kl_current) / _kl_current * 100, 2)
                        _z = f"${_r['zone_lo']:,.2f} - ${_r['zone_hi']:,.2f}" if _r["zone_lo"] != _r["zone_hi"] else "-"
                        _dc = "#3fb950" if _d >= 0 else "#f85149"
                        _kl_rows += f"<tr style='border-bottom:1px solid rgba(48,54,61,0.3);'><td style='padding:8px 12px;color:#f85149;font-weight:600;'>RESISTANCE</td><td style='padding:8px 12px;font-family:JetBrains Mono,monospace;'>${_r['level']:,.2f}</td><td style='padding:8px 12px;color:#8b949e;font-family:JetBrains Mono,monospace;'>{_z}</td><td style='padding:8px 12px;font-family:JetBrains Mono,monospace;color:{_dc};'>{_d:+.2f}%</td><td style='padding:8px 12px;text-align:center;'>{_r['touches']}</td></tr>"
                    _kl_tl_html = ""
                    if _tl_trend_data:
                        for _tl in _tl_trend_data:
                            _dlbl = "UPTREND" if _tl["direction"] == "up" else "DOWNTREND"
                            _dclr = "#3fb950" if _tl["direction"] == "up" else "#f85149"
                            _dbg = "63,185,80" if _tl["direction"] == "up" else "248,81,73"
                            _kl_tl_html += f"<div style='display:inline-block;background:rgba({_dbg},0.1);border:1px solid {_dclr};border-radius:8px;padding:8px 14px;margin-right:10px;margin-top:8px;'><span style='color:{_dclr};font-weight:700;font-size:0.82em;'>{_dlbl}</span> <span style='color:#8b949e;font-size:0.78em;'>R\u00b2={_tl['r_squared']:.2f}</span> <span style='color:#c9d1d9;font-size:0.78em;font-family:JetBrains Mono,monospace;'>${_tl['start_price']:,.2f} &rarr; ${_tl['end_price']:,.2f}</span></div>"
                    _kl_tl_sec = ""
                    if _kl_tl_html:
                        _kl_tl_sec = f"<div style='margin-top:14px;border-top:1px solid rgba(48,54,61,0.3);padding-top:12px;'><span style='color:#8b949e;font-size:0.78em;'>Detected Trendlines:</span>{_kl_tl_html}</div>"
                    _kl_sup_display = _kl_sup_text if _kl_sup_text else "<span style='color:#6e7681;'>None detected</span>"
                    _kl_res_display = _kl_res_text if _kl_res_text else "<span style='color:#6e7681;'>None detected</span>"
                    st.markdown(
                        f"<div style='background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid rgba(88,166,255,0.2);border-radius:12px;padding:18px 22px;margin-top:16px;margin-bottom:8px;'>"
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:14px;'><span style='color:#58a6ff;font-size:0.82em;font-weight:700;letter-spacing:0.1em;'>KEY LEVELS</span></div>"
                        f"<div style='display:flex;gap:24px;margin-bottom:16px;flex-wrap:wrap;'>"
                        f"<div><span style='color:#8b949e;font-size:0.78em;'>Nearest Support:</span><br>{_kl_sup_display}</div>"
                        f"<div><span style='color:#8b949e;font-size:0.78em;'>Current Price:</span><br><span style='color:#e6edf3;font-weight:700;font-family:JetBrains Mono,monospace;'>${_kl_current:,.2f}</span></div>"
                        f"<div><span style='color:#8b949e;font-size:0.78em;'>Nearest Resistance:</span><br>{_kl_res_display}</div>"
                        f"</div>"
                        f"<table style='width:100%;border-collapse:collapse;font-size:0.82em;color:#c9d1d9;'>"
                        f"<thead><tr style='border-bottom:2px solid rgba(88,166,255,0.3);'>"
                        f"<th style='padding:8px 12px;text-align:left;color:#8b949e;font-weight:600;'>Type</th>"
                        f"<th style='padding:8px 12px;text-align:left;color:#8b949e;font-weight:600;'>Level</th>"
                        f"<th style='padding:8px 12px;text-align:left;color:#8b949e;font-weight:600;'>Zone</th>"
                        f"<th style='padding:8px 12px;text-align:left;color:#8b949e;font-weight:600;'>Distance</th>"
                        f"<th style='padding:8px 12px;text-align:center;color:#8b949e;font-weight:600;'>Touches</th>"
                        f"</tr></thead><tbody>{_kl_rows}</tbody></table>"
                        f"{_kl_tl_sec}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # ── Human-Readable Chart Summary ──
                # Auto-generate a plain-language explanation of what the chart shows
                _ch_df_explain = chart_engine.add_indicators(_ch_df)
                _ch_close = _ch_df_explain["Close"]
                _ch_current = float(_ch_close.iloc[-1])
                _ch_start = float(_ch_close.iloc[0])
                _ch_change_pct = round((_ch_current - _ch_start) / _ch_start * 100, 1)
                _ch_high = float(_ch_close.max())
                _ch_low = float(_ch_close.min())

                # RSI interpretation
                _ch_rsi = float(_ch_df_explain["RSI"].iloc[-1]) if "RSI" in _ch_df_explain.columns else 50
                if _ch_rsi > 70:
                    _rsi_text = f"<b style='color:#f85149;'>RSI is at {_ch_rsi:.0f} — overbought territory.</b> The asset may be due for a pullback."
                elif _ch_rsi < 30:
                    _rsi_text = f"<b style='color:#3fb950;'>RSI is at {_ch_rsi:.0f} — oversold territory.</b> This could signal a buying opportunity."
                elif _ch_rsi > 60:
                    _rsi_text = f"RSI is at {_ch_rsi:.0f} — showing <b style='color:#3fb950;'>bullish momentum</b> but not yet overbought."
                elif _ch_rsi < 40:
                    _rsi_text = f"RSI is at {_ch_rsi:.0f} — showing <b style='color:#f85149;'>bearish momentum</b> but not yet oversold."
                else:
                    _rsi_text = f"RSI is at {_ch_rsi:.0f} — in <b>neutral zone</b>. No strong momentum signal."

                # SMA interpretation
                _ch_sma50 = float(_ch_df_explain["SMA_50"].iloc[-1]) if "SMA_50" in _ch_df_explain.columns and not pd.isna(_ch_df_explain["SMA_50"].iloc[-1]) else None
                _ch_sma200 = float(_ch_df_explain["SMA_200"].iloc[-1]) if "SMA_200" in _ch_df_explain.columns and not pd.isna(_ch_df_explain["SMA_200"].iloc[-1]) else None
                _sma_text = ""
                if _ch_sma50 and _ch_sma200:
                    if _ch_sma50 > _ch_sma200:
                        _sma_text = "<b style='color:#3fb950;'>Golden Cross active</b> (50-day MA above 200-day MA) — historically a bullish long-term signal."
                    else:
                        _sma_text = "<b style='color:#f85149;'>Death Cross active</b> (50-day MA below 200-day MA) — historically a bearish long-term signal."
                    if _ch_current > _ch_sma50:
                        _sma_text += f" Price is <b>above</b> the 50-day moving average (${_ch_sma50:,.2f})."
                    else:
                        _sma_text += f" Price is <b>below</b> the 50-day moving average (${_ch_sma50:,.2f})."

                # Trend direction
                if _ch_change_pct > 5:
                    _trend_icon = "📈"
                    _trend_text = f"{_trend_icon} <b style='color:#3fb950;'>Strong uptrend</b>: {_ch_asset} is up <b>{_ch_change_pct}%</b> in this period."
                elif _ch_change_pct > 0:
                    _trend_icon = "↗️"
                    _trend_text = f"{_trend_icon} <b style='color:#3fb950;'>Mild uptrend</b>: {_ch_asset} is up <b>{_ch_change_pct}%</b> in this period."
                elif _ch_change_pct > -5:
                    _trend_icon = "↘️"
                    _trend_text = f"{_trend_icon} <b style='color:#f85149;'>Mild downtrend</b>: {_ch_asset} is down <b>{abs(_ch_change_pct)}%</b> in this period."
                else:
                    _trend_icon = "📉"
                    _trend_text = f"{_trend_icon} <b style='color:#f85149;'>Strong downtrend</b>: {_ch_asset} is down <b>{abs(_ch_change_pct)}%</b> in this period."

                # Volatility
                _ch_vol_pct = round((_ch_high - _ch_low) / _ch_current * 100, 1)
                if _ch_vol_pct > 20:
                    _vol_text = f"⚠️ <b>High volatility</b> ({_ch_vol_pct}% range) — wider stop-losses recommended."
                elif _ch_vol_pct > 10:
                    _vol_text = f"Moderate volatility ({_ch_vol_pct}% range)."
                else:
                    _vol_text = f"Low volatility ({_ch_vol_pct}% range) — tight price action."

                st.markdown(
                    f"<div style='background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid rgba(88,166,255,0.2);"
                    f"border-radius:12px;padding:18px 22px;margin-top:12px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px;'>"
                    f"<span style='font-size:1.1em;'>📖</span>"
                    f"<span style='color:#58a6ff;font-size:0.82em;font-weight:700;"
                    f"letter-spacing:0.1em;'>CHART READING GUIDE</span></div>"
                    f"<div style='color:#e6edf3;font-size:0.88em;line-height:1.8;'>"
                    f"<div style='margin-bottom:6px;'>{_trend_text}</div>"
                    f"<div style='margin-bottom:6px;color:#8b949e;'>Price range: ${_ch_low:,.2f} — ${_ch_high:,.2f} (current: <b style=\"color:#e6edf3;\">${_ch_current:,.2f}</b>)</div>"
                    f"<div style='margin-bottom:6px;'>{_rsi_text}</div>"
                    f"<div style='margin-bottom:6px;'>{_sma_text}</div>"
                    f"<div>{_vol_text}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

                # MACD sub-chart
                with st.expander("MACD Chart"):
                    st.plotly_chart(chart_engine.build_macd_chart(_ch_df, height=250), use_container_width=True)
                    st.markdown(
                        "<div style='color:#8b949e;font-size:0.82em;padding:8px 0;'>"
                        "<strong>How to read MACD:</strong> When the blue MACD line crosses ABOVE the "
                        "orange signal line, it's a bullish signal (consider buying). When it crosses BELOW, "
                        "it's bearish (consider selling). The histogram bars show the strength of the signal — "
                        "bigger bars = stronger momentum.</div>",
                        unsafe_allow_html=True,
                    )

                # ── Multi-Timeframe Analysis ──
                with st.expander("Multi-Timeframe Analysis (4H / Daily)"):
                    _ch_data = _ch_watchlist.get(_ch_asset, {})
                    _ch_conf = _ch_data.get("confidence", {})
                    _mtf = _ch_conf.get("mtf_data", {}) if isinstance(_ch_conf, dict) else {}
                    if _mtf and _mtf.get("available"):
                        _mtf_rsi = _mtf.get("rsi_4h", 50)
                        _mtf_macd = _mtf.get("macd_4h_bullish", False)
                        _mtf_sma = _mtf.get("price_above_sma20_4h", False)
                        _mtf_bull = _mtf.get("bullish_confirms", 0)
                        _mtf_bear = _mtf.get("bearish_confirms", 0)
                        _mtf_total = _mtf_bull + _mtf_bear
                        _mtf_label = "BULLISH" if _mtf_bull > _mtf_bear else "BEARISH" if _mtf_bear > _mtf_bull else "MIXED"
                        _mtf_color = "#3fb950" if _mtf_label == "BULLISH" else "#f85149" if _mtf_label == "BEARISH" else "#d29922"
                        _mtf_agree = max(_mtf_bull, _mtf_bear)

                        st.markdown(
                            f"<div style='text-align:center;padding:16px;background:#161b22;"
                            f"border:2px solid {_mtf_color};border-radius:12px;margin-bottom:16px;'>"
                            f"<div style='color:{_mtf_color};font-size:1.8em;font-weight:800;"
                            f"font-family:JetBrains Mono,monospace;'>{_mtf_agree}/{_mtf_total} {_mtf_label}</div>"
                            f"<div style='color:#8b949e;font-size:0.82em;margin-top:4px;'>"
                            f"Timeframe Agreement Score</div></div>",
                            unsafe_allow_html=True,
                        )
                        _mtf_c1, _mtf_c2, _mtf_c3 = st.columns(3)
                        with _mtf_c1:
                            _mtf_rsi_delta = "Oversold" if _mtf_rsi < 30 else "Overbought" if _mtf_rsi > 70 else "Neutral"
                            st.metric("4H RSI", f"{_mtf_rsi:.1f}", delta=_mtf_rsi_delta)
                        with _mtf_c2:
                            st.metric("4H MACD", "Bullish" if _mtf_macd else "Bearish")
                        with _mtf_c3:
                            st.metric("4H SMA-20", "Above" if _mtf_sma else "Below")
                    else:
                        st.info("Multi-timeframe data not yet available. Run a full scan to generate it.")

                # Detected patterns list
                if _ch_patterns:
                    _pats = chart_engine.detect_patterns(_ch_df_explain)
                    if _pats:
                        with st.expander(f"Detected Patterns ({len(_pats)})"):
                            st.markdown(
                                "<div style='color:#8b949e;font-size:0.82em;margin-bottom:8px;'>"
                                "<strong>What are patterns?</strong> Candlestick patterns are visual formations "
                                "that traders use to predict future price movement. <span style='color:#3fb950;'>"
                                "Bullish</span> patterns suggest prices may rise, while <span style='color:#f85149;'>"
                                "bearish</span> patterns suggest prices may fall.</div>",
                                unsafe_allow_html=True,
                            )
                            _pat_rows = [{"Date": str(p["date"])[:10], "Pattern": p["pattern"],
                                          "Type": p["type"].title()} for p in _pats[-20:]]
                            st.dataframe(pd.DataFrame(_pat_rows), use_container_width=True, hide_index=True)
            else:
                st.warning(f"Could not fetch data for {_ch_ticker}")


# ===========================
# PERFORMANCE ANALYTICS
# ===========================
elif view == "analytics":
    render_page_header("Performance Analytics", view_key="analytics")
    render_page_info("analytics")

    _an_watchlist = load_watchlist_summary()
    _an_prices = fetch_live_prices(_an_watchlist) if _an_watchlist else {}
    _an_history = paper_trader.get_trade_history()
    _an_curve = paper_trader.get_equity_curve()
    _an_summary = paper_trader.get_portfolio_summary(_an_prices)

    if not _an_history:
        st.info("No trades yet. Open and close some paper trades to see analytics.")
    else:
        _an_report = performance_analytics.generate_report(
            _an_history, _an_curve, _an_summary["starting_balance"])

        # Key metrics row 1
        _am1, _am2, _am3, _am4, _am5, _am6 = st.columns(6)
        with _am1:
            st.metric("Sharpe Ratio", _an_report["sharpe_ratio"])
        with _am2:
            st.metric("Sortino Ratio", _an_report["sortino_ratio"])
        with _am3:
            st.metric("Profit Factor", _an_report["profit_factor"])
        with _am4:
            st.metric("Expectancy", f"${_an_report['expectancy']:,.2f}")
        with _am5:
            st.metric("Max Drawdown", f"{_an_report['max_drawdown_pct']}%")
        with _am6:
            st.metric("Avg Hold Time", _an_report["avg_holding_time"])

        # Key metrics row 2
        _am7, _am8, _am9, _am10 = st.columns(4)
        with _am7:
            st.metric("Total Return", f"{_an_report['total_return_pct']:+.2f}%")
        with _am8:
            st.metric("Win Rate", f"{_an_report['win_rate']}%", delta=f"{_an_report['wins']}W/{_an_report['losses']}L")
        with _am9:
            st.metric("Best Trade", f"${_an_report['best_trade']:+,.2f}")
        with _am10:
            st.metric("Worst Trade", f"${_an_report['worst_trade']:+,.2f}")

        st.divider()

        # ── 9 Charts in 3 Tabs ──
        _an_tab1, _an_tab2, _an_tab3 = st.tabs(["Equity & Returns", "Trade Analysis", "Timing & Streaks"])

        with _an_tab1:
            st.markdown("### Equity & Drawdown")
            if len(_an_curve) >= 2:
                st.plotly_chart(
                    performance_analytics.equity_drawdown_chart(_an_curve, _an_summary["starting_balance"]),
                    use_container_width=True)
            st.divider()
            _dc1, _dc2 = st.columns(2)
            with _dc1:
                st.markdown("### Cumulative P&L")
                if _an_history:
                    st.plotly_chart(performance_analytics.cumulative_pnl_chart(_an_history), use_container_width=True)
                else:
                    st.caption("No closed trades yet.")
            with _dc2:
                st.markdown("### P&L Distribution")
                if _an_history:
                    st.plotly_chart(performance_analytics.pnl_distribution_chart(_an_history), use_container_width=True)
                else:
                    st.caption("Close a few trades to see P&L distribution.")

        with _an_tab2:
            st.markdown("### P&L by Asset")
            if _an_history:
                st.plotly_chart(performance_analytics.pnl_by_asset_chart(_an_history), use_container_width=True)
            else:
                st.caption("Close at least one trade to see per-asset breakdown.")
            st.divider()
            st.markdown("### Trade Timeline")
            st.caption("Every trade plotted over time. Green = wins, red = losses.")
            try:
                st.plotly_chart(performance_analytics.trade_timeline_chart(_an_history), use_container_width=True)
            except Exception:
                st.caption("Need more trades to generate timeline.")
            st.divider()
            st.markdown("### P&L by Day of Week")
            if _an_history:
                st.plotly_chart(performance_analytics.performance_by_day_chart(_an_history), use_container_width=True)
            else:
                st.caption("Need trade history to analyze day-of-week performance.")

        with _an_tab3:
            _rc1, _rc2 = st.columns(2)
            with _rc1:
                st.markdown("### Rolling Win Rate (5-Trade Window)")
                if len(_an_history) >= 5:
                    st.plotly_chart(performance_analytics.rolling_win_rate_chart(_an_history, window=5), use_container_width=True)
                else:
                    st.caption("Need at least 5 closed trades.")
            with _rc2:
                st.markdown("### Win/Loss Streaks")
                try:
                    st.plotly_chart(performance_analytics.win_loss_streak_chart(_an_history), use_container_width=True)
                except Exception:
                    st.caption("Need more trades to show streaks.")
            # Streak metrics
            _streaks = performance_analytics.consecutive_wins_losses(_an_history)
            _sk1, _sk2 = st.columns(2)
            with _sk1:
                st.metric("Max Consecutive Wins", _streaks["max_consecutive_wins"])
            with _sk2:
                st.metric("Max Consecutive Losses", _streaks["max_consecutive_losses"])
            st.divider()
            st.markdown("### Performance by Hour of Day")
            st.caption("Best and worst trading hours.")
            try:
                st.plotly_chart(performance_analytics.hourly_performance_chart(_an_history), use_container_width=True)
            except Exception:
                st.caption("Need more trades for hourly analysis.")

        # Bot intelligence summary
        _bot_log = PROJECT_ROOT / "memory" / "bot_activity.json"
        if _bot_log.exists():
            try:
                _bot_acts = json.loads(_bot_log.read_text(encoding="utf-8"))
                if _bot_acts:
                    st.divider()
                    st.markdown("### Bot Trading Intelligence")
                    _bot_total_cycles = len(_bot_acts)
                    _bot_total_opened = sum(len(a.get("trades_opened", [])) for a in _bot_acts)
                    _bot_total_closed = sum(len(a.get("exits_closed", [])) for a in _bot_acts)
                    _bot_total_errors = sum(len(a.get("errors", [])) for a in _bot_acts)
                    _bot_total_pnl = sum(c.get("pnl", 0) for a in _bot_acts for c in a.get("exits_closed", []))

                    _bi1, _bi2, _bi3, _bi4, _bi5 = st.columns(5)
                    with _bi1:
                        st.metric("Bot Cycles", _bot_total_cycles)
                    with _bi2:
                        st.metric("Trades Opened", _bot_total_opened)
                    with _bi3:
                        st.metric("Trades Closed", _bot_total_closed)
                    with _bi4:
                        _pnl_color = "normal" if _bot_total_pnl >= 0 else "inverse"
                        st.metric("Total P&L", f"${_bot_total_pnl:+,.2f}", delta_color=_pnl_color)
                    with _bi5:
                        st.metric("Errors", _bot_total_errors, delta_color="inverse" if _bot_total_errors > 0 else "normal")
            except Exception:
                pass


# ===========================
# STRATEGY LAB
# ===========================
elif view == "strategy_lab":
    render_page_header("Strategy Lab", view_key="strategy_lab")
    render_page_info("strategy_lab")

    _sl_tab1, _sl_tab2, _sl_tab3 = st.tabs(["Natural Language Builder", "Templates", "Optimizer"])

    _sl_watchlist = load_watchlist_summary()

    with _sl_tab1:
        st.markdown("### Describe Your Strategy")
        st.caption("Example: *Buy when RSI < 30 and MACD crosses above signal line. Sell when RSI > 70. Stop-loss 5%.*")
        _nl_input = st.text_area("Strategy Description", height=100, key="nl_strategy")
        _nl_asset = st.selectbox("Test on Asset", list(_sl_watchlist.keys()) if _sl_watchlist else ["BTC-USD"], key="nl_asset")
        _nl_period = st.selectbox("Backtest Period", ["3mo", "6mo", "1y", "2y"], index=1, key="nl_period")

        if st.button("Parse & Backtest", type="primary", key="nl_run") and _nl_input:
            _parsed = strategy_builder.parse_strategy(_nl_input)

            st.markdown("**Parsed Conditions:**")
            if _parsed.buy_conditions:
                st.success("BUY when: " + " AND ".join(c.label for c in _parsed.buy_conditions))
            if _parsed.sell_conditions:
                st.error("SELL when: " + " AND ".join(c.label for c in _parsed.sell_conditions))
            st.caption(f"SL: {_parsed.stop_loss_pct}% | TP: {_parsed.take_profit_pct}%")

            _ticker = _sl_watchlist.get(_nl_asset, {}).get("ticker", _nl_asset)
            _df = chart_engine.fetch_ohlcv(_ticker, period=_nl_period)
            if not _df.empty:
                _bt_result = strategy_builder.backtest_strategy(_parsed, _df)
                _br1, _br2, _br3, _br4 = st.columns(4)
                with _br1:
                    st.metric("Return", f"{_bt_result['total_return_pct']:+.2f}%")
                with _br2:
                    st.metric("Trades", _bt_result["total_trades"])
                with _br3:
                    st.metric("Win Rate", f"{_bt_result['win_rate']}%")
                with _br4:
                    st.metric("Final Equity", f"${_bt_result['final_equity']:,.2f}")

                if _bt_result["equity_curve"]:
                    _eq_dates = [e["date"] for e in _bt_result["equity_curve"]]
                    _eq_vals = [e["equity"] for e in _bt_result["equity_curve"]]
                    _fig_bt = go.Figure(go.Scatter(x=_eq_dates, y=_eq_vals, mode="lines",
                                                   line={"color": "#58a6ff", "width": 2}, fill="tozeroy",
                                                   fillcolor="rgba(88,166,255,0.1)"))
                    _fig_bt.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                          height=300, margin=dict(t=20, b=30, l=50, r=20),
                                          font={"color": "#c9d1d9"}, yaxis_title="Equity ($)")
                    st.plotly_chart(_fig_bt, use_container_width=True)
            else:
                st.warning("Could not fetch price data.")

    with _sl_tab2:
        st.markdown("### Pre-Built Strategy Templates")
        for tpl_name, tpl in strategy_builder.TEMPLATES.items():
            with st.expander(tpl_name):
                if tpl.buy_conditions:
                    st.markdown("**BUY:** " + " AND ".join(c.label for c in tpl.buy_conditions))
                if tpl.sell_conditions:
                    st.markdown("**SELL:** " + " AND ".join(c.label for c in tpl.sell_conditions))
                st.caption(f"SL: {tpl.stop_loss_pct}% | TP: {tpl.take_profit_pct}%")

                _tpl_asset = st.selectbox("Asset", list(_sl_watchlist.keys()) if _sl_watchlist else ["BTC-USD"],
                                          key=f"tpl_asset_{tpl_name}")
                if st.button("Backtest", key=f"tpl_run_{tpl_name}"):
                    _ticker = _sl_watchlist.get(_tpl_asset, {}).get("ticker", _tpl_asset)
                    _df = chart_engine.fetch_ohlcv(_ticker, period="6mo")
                    if not _df.empty:
                        _res = strategy_builder.backtest_strategy(tpl, _df)
                        st.metric("Return", f"{_res['total_return_pct']:+.2f}%")
                        st.metric("Win Rate", f"{_res['win_rate']}% ({_res['wins']}W/{_res['losses']}L)")

    with _sl_tab3:
        st.markdown("### Hyperparameter Optimizer")
        st.caption("Finds optimal RSI thresholds, SMA periods, and SL/TP using Optuna.")

        _ho_asset = st.selectbox("Asset", list(_sl_watchlist.keys()) if _sl_watchlist else ["BTC-USD"], key="ho_asset")
        _ho_trials = st.slider("Optimization Trials", 20, 200, 50, step=10, key="ho_trials")

        if st.button("Run Optimization", type="primary", key="ho_run"):
            _ticker = _sl_watchlist.get(_ho_asset, {}).get("ticker", _ho_asset)
            _df = chart_engine.fetch_ohlcv(_ticker, period="1y")
            if not _df.empty:
                with st.spinner(f"Running {_ho_trials} trials..."):
                    _opt = hyperopt_engine.optimize_strategy(_df, n_trials=_ho_trials)

                st.success(f"Best Sharpe: {_opt['best_value']}")
                st.json(_opt["best_params"])

                _br = _opt["best_result"]
                _oc1, _oc2, _oc3 = st.columns(3)
                with _oc1:
                    st.metric("Return", f"{_br['total_return']:+.2f}%")
                with _oc2:
                    st.metric("Win Rate", f"{_br['win_rate']}%")
                with _oc3:
                    st.metric("Trades", _br["total_trades"])

                st.plotly_chart(hyperopt_engine.plot_optimization_results(_opt), use_container_width=True)
                st.plotly_chart(hyperopt_engine.plot_param_importance(_opt), use_container_width=True)
            else:
                st.warning("Could not fetch price data.")


# ===========================
# ALERTS
# ===========================
elif view == "alerts":
    render_page_header("Price & Signal Alerts", view_key="alerts")
    render_page_info("alerts")

    _al_tab1, _al_tab2, _al_tab3 = st.tabs(["Active Alerts", "Create Alert", "Settings"])
    _al_watchlist = load_watchlist_summary()

    with _al_tab1:
        # Check alerts on each refresh
        _al_prices = fetch_live_prices(_al_watchlist) if _al_watchlist else {}
        _triggered = alert_manager.check_alerts(_al_prices, _al_watchlist)
        if _triggered:
            for _tr in _triggered:
                st.warning(f"TRIGGERED: {_tr['message']} — Price: ${_tr.get('current_price', 0):,.2f}")
            alert_manager.send_notifications(_triggered)

        alerts = alert_manager.get_alerts()
        if alerts:
            for a in alerts:
                _ac1, _ac2 = st.columns([4, 1])
                with _ac1:
                    _status = "Active" if a.get("active") else "Triggered"
                    st.markdown(
                        f"**{a['asset']}** — {a['alert_type']} {a['condition']} {a['threshold']} "
                        f"({_status})")
                with _ac2:
                    if st.button("Delete", key=f"del_alert_{a['id']}"):
                        alert_manager.delete_alert(a["id"])
                        st.rerun()
        else:
            st.caption("No active alerts. Create one in the next tab.")

        # Alert history
        _al_hist = alert_manager.get_alert_history(20)
        if _al_hist:
            with st.expander(f"Alert History ({len(_al_hist)})"):
                for ah in _al_hist:
                    st.caption(f"{ah.get('triggered_at', '')[:16]} — {ah['message']} @ ${ah.get('current_price', 0):,.2f}")

    with _al_tab2:
        st.markdown("### Create New Alert")
        with st.form("create_alert_form", clear_on_submit=True):
            _al_asset = st.selectbox("Asset", list(_al_watchlist.keys()) if _al_watchlist else ["Gold"])
            _al_type = st.selectbox("Alert Type", ["price", "rsi", "pct_change"])
            _al_cond = st.selectbox("Condition", ["above", "below"])
            _al_thresh = st.number_input("Threshold", min_value=0.0, value=100.0, step=1.0)
            _al_msg = st.text_input("Custom Message (optional)")

            if st.form_submit_button("Create Alert", use_container_width=True):
                _ticker = _al_watchlist.get(_al_asset, {}).get("ticker", "")
                alert_manager.add_alert(_al_asset, _ticker, _al_type, _al_cond, _al_thresh, _al_msg)
                st.success(f"Alert created: {_al_asset} {_al_type} {_al_cond} {_al_thresh}")
                st.rerun()

    with _al_tab3:
        st.markdown("### Notification Settings")
        _al_cfg = alert_manager.get_config()
        with st.form("alert_settings"):
            st.markdown("**Discord**")
            _discord = st.text_input("Discord Webhook URL", value=_al_cfg.get("discord_webhook", ""))
            st.markdown("**Telegram**")
            _tg_token = st.text_input("Bot Token", value=_al_cfg.get("telegram_bot_token", ""))
            _tg_chat = st.text_input("Chat ID", value=_al_cfg.get("telegram_chat_id", ""))
            st.markdown("**Email**")
            _em_enabled = st.checkbox("Enable Email", value=_al_cfg.get("email_enabled", False))
            _em_smtp = st.text_input("SMTP Server", value=_al_cfg.get("email_smtp", ""))
            _em_user = st.text_input("Email User", value=_al_cfg.get("email_user", ""))
            _em_pass = st.text_input("Email Password", type="password", value=_al_cfg.get("email_pass", ""))
            _em_to = st.text_input("Send To", value=_al_cfg.get("email_to", ""))

            if st.form_submit_button("Save Settings"):
                alert_manager.save_notification_config({
                    "discord_webhook": _discord, "telegram_bot_token": _tg_token,
                    "telegram_chat_id": _tg_chat, "email_enabled": _em_enabled,
                    "email_smtp": _em_smtp, "email_user": _em_user,
                    "email_pass": _em_pass, "email_to": _em_to,
                    "email_port": 587,
                })
                st.success("Settings saved.")


# ===========================
# SIGNAL REPORT CARD — AI Accountability & Prediction Tracking
# ===========================
elif view == "report_card":
    render_page_header("Signal Report Card", view_key="report_card")
    render_page_info("report_card")

    # Load predictions
    _rc_preds = []
    _rc_stats = {"total": 0, "validated": 0, "correct": 0}
    if PREDICTIONS_FILE.exists():
        try:
            _rc_data = json.loads(PREDICTIONS_FILE.read_text(encoding="utf-8"))
            _rc_preds = _rc_data.get("predictions", [])
            _rc_stats = _rc_data.get("stats", _rc_stats)
        except Exception:
            pass

    # Load hindsight simulations
    _rc_sims = []
    if HINDSIGHT_FILE.exists():
        try:
            _rc_sim_data = json.loads(HINDSIGHT_FILE.read_text(encoding="utf-8"))
            _rc_sims = _rc_sim_data.get("simulations", [])
        except Exception:
            pass

    # Load market lessons
    _rc_lessons = []
    if MARKET_LESSONS_FILE.exists():
        try:
            _rc_lesson_data = json.loads(MARKET_LESSONS_FILE.read_text(encoding="utf-8"))
            _rc_lessons = _rc_lesson_data.get("lessons", [])
        except Exception:
            pass

    # ── Overall Accuracy Banner ──
    _total = _rc_stats.get("total", 0)
    _validated = _rc_stats.get("validated", 0)
    _correct = _rc_stats.get("correct", 0)
    _accuracy = round(_correct / _validated * 100, 1) if _validated > 0 else 0
    _acc_color = "#3fb950" if _accuracy >= 60 else "#d29922" if _accuracy >= 40 else "#f85149"

    _grade = "A+" if _accuracy >= 80 else "A" if _accuracy >= 70 else "B" if _accuracy >= 60 else "C" if _accuracy >= 50 else "D" if _accuracy >= 40 else "F"
    _grade_color = "#3fb950" if _grade in ("A+", "A") else "#3fb950" if _grade == "B" else "#d29922" if _grade == "C" else "#f85149"

    _mc1, _mc2, _mc3, _mc4 = st.columns(4)
    with _mc1:
        st.markdown(
            f"<div style='background:#161b22;border:2px solid {_acc_color};border-radius:12px;"
            f"padding:20px;text-align:center;'>"
            f"<div style='color:#8b949e;font-size:0.7em;letter-spacing:0.1em;'>OVERALL ACCURACY</div>"
            f"<div style='color:{_acc_color};font-size:2.5em;font-weight:800;"
            f"font-family:JetBrains Mono,monospace;'>{_accuracy}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _mc2:
        st.markdown(
            f"<div style='background:#161b22;border:2px solid {_grade_color};border-radius:12px;"
            f"padding:20px;text-align:center;'>"
            f"<div style='color:#8b949e;font-size:0.7em;letter-spacing:0.1em;'>GRADE</div>"
            f"<div style='color:{_grade_color};font-size:2.5em;font-weight:800;"
            f"font-family:JetBrains Mono,monospace;'>{_grade}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _mc3:
        st.markdown(
            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);border-radius:12px;"
            f"padding:20px;text-align:center;'>"
            f"<div style='color:#8b949e;font-size:0.7em;letter-spacing:0.1em;'>PREDICTIONS</div>"
            f"<div style='color:#e6edf3;font-size:2.5em;font-weight:800;"
            f"font-family:JetBrains Mono,monospace;'>{_total}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _mc4:
        st.markdown(
            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);border-radius:12px;"
            f"padding:20px;text-align:center;'>"
            f"<div style='color:#8b949e;font-size:0.7em;letter-spacing:0.1em;'>CORRECT / VALIDATED</div>"
            f"<div style='color:#e6edf3;font-size:2.5em;font-weight:800;"
            f"font-family:JetBrains Mono,monospace;'>{_correct}/{_validated}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    _rc_tab1, _rc_tab2, _rc_tab3 = st.tabs(["Prediction History", "Hindsight Simulations", "Lessons Learned"])

    # ── TAB 1: Prediction History ──
    with _rc_tab1:
        st.markdown("### All Predictions — Full Transparency")

        # Per-asset accuracy breakdown
        if _rc_preds:
            _asset_acc = {}
            for p in _rc_preds:
                a = p.get("asset", "Unknown")
                if a not in _asset_acc:
                    _asset_acc[a] = {"total": 0, "validated": 0, "correct": 0}
                _asset_acc[a]["total"] += 1
                if p.get("validated"):
                    _asset_acc[a]["validated"] += 1
                    if p.get("outcome") == "correct":
                        _asset_acc[a]["correct"] += 1

            st.markdown("#### Per-Asset Accuracy")
            _acc_rows = []
            for aname, astats in sorted(_asset_acc.items()):
                _a_validated = astats["validated"]
                _a_correct = astats["correct"]
                _a_pct = round(_a_correct / _a_validated * 100, 1) if _a_validated > 0 else 0
                _acc_rows.append({
                    "Asset": aname,
                    "Total Signals": astats["total"],
                    "Validated": _a_validated,
                    "Correct": _a_correct,
                    "Accuracy": f"{_a_pct}%",
                })
            st.dataframe(pd.DataFrame(_acc_rows), use_container_width=True, hide_index=True)

            st.divider()

            # Recent predictions table
            st.markdown("#### Recent Predictions")
            _recent = sorted(_rc_preds, key=lambda p: p.get("timestamp", ""), reverse=True)[:30]
            _pred_rows = []
            for p in _recent:
                _outcome = p.get("outcome") or "pending"
                _oc = "#3fb950" if _outcome == "correct" else "#f85149" if _outcome == "incorrect" else "#d29922"
                _pred_rows.append({
                    "Date": p.get("timestamp", "")[:10],
                    "Asset": p.get("asset", ""),
                    "Signal": p.get("signal_label", ""),
                    "Score": p.get("signal_score", 0),
                    "Entry": f"${p.get('entry_price', 0):,.2f}",
                    "Target": f"${p.get('target_price', 0):,.2f}",
                    "Stop": f"${p.get('stop_loss', 0):,.2f}",
                    "R:R": f"{p.get('risk_reward', 0):.1f}",
                    "Outcome": _outcome.upper(),
                    "Note": (p.get("outcome_note", "") or "")[:60],
                })
            st.dataframe(pd.DataFrame(_pred_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No predictions recorded yet. Run a scan to generate signals.")

    # ── TAB 2: Hindsight Simulations ──
    with _rc_tab2:
        st.markdown("### Hindsight Simulator — Time-Travel Grading")
        st.caption("The AI goes back 48 hours and makes predictions, then we check how they turned out.")

        if _rc_sims:
            # Grade distribution
            _grade_dist = {}
            for s in _rc_sims:
                g = s.get("grade", "?")
                _grade_dist[g] = _grade_dist.get(g, 0) + 1

            _gd_cols = st.columns(len(_grade_dist) if _grade_dist else 1)
            for idx, (g, count) in enumerate(sorted(_grade_dist.items())):
                _gc = "#3fb950" if g in ("A", "A+") else "#3fb950" if g == "B" else "#d29922" if g == "C" else "#f85149"
                with _gd_cols[idx % len(_gd_cols)]:
                    st.metric(f"Grade {g}", count)

            st.divider()

            # Simulation table
            _sim_rows = []
            for s in sorted(_rc_sims, key=lambda x: x.get("timestamp", ""), reverse=True):
                _sim_rows.append({
                    "Date": s.get("simulated_date", ""),
                    "Asset": s.get("asset", ""),
                    "Predicted": s.get("predicted_label", ""),
                    "Score": s.get("predicted_score", 0),
                    "Entry": f"${s.get('predicted_price', 0):,.2f}",
                    "Actual": f"${s.get('actual_price', 0):,.2f}",
                    "Move": f"{s.get('pct_change', 0):+.1f}%",
                    "Max Up": f"{s.get('max_upside', 0):+.1f}%",
                    "Max Down": f"{s.get('max_drawdown', 0):.1f}%",
                    "Grade": s.get("grade", "?"),
                    "Outcome": s.get("outcome", ""),
                })
            st.dataframe(pd.DataFrame(_sim_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No hindsight simulations yet. The system runs these automatically.")

    # ── TAB 3: Lessons Learned ──
    with _rc_tab3:
        st.markdown("### Lessons From Failures")
        st.caption("When predictions fail, the AI records what went wrong and creates prevention rules.")

        if _rc_lessons:
            for lesson in sorted(_rc_lessons, key=lambda l: l.get("timestamp", ""), reverse=True)[:20]:
                _ls_cat = lesson.get("category", "general")
                _ls_color = "#f85149" if _ls_cat == "missed_move" else "#d29922"
                st.markdown(
                    f"<div style='background:#161b22;border-left:3px solid {_ls_color};"
                    f"padding:12px 16px;margin-bottom:8px;border-radius:4px;'>"
                    f"<div style='color:#e6edf3;font-weight:600;font-size:0.9em;'>"
                    f"{lesson.get('asset', '')} — {lesson.get('signal_label', '')}</div>"
                    f"<div style='color:#f85149;font-size:0.82em;margin-top:4px;'>"
                    f"What happened: {lesson.get('what_happened', '')}</div>"
                    f"<div style='color:#d29922;font-size:0.82em;margin-top:4px;'>"
                    f"Root cause: {lesson.get('root_cause', '')}</div>"
                    f"<div style='color:#3fb950;font-size:0.82em;margin-top:4px;'>"
                    f"Prevention: {lesson.get('prevention_rule', '')}</div>"
                    f"<div style='color:#8b949e;font-size:0.7em;margin-top:6px;'>"
                    f"{lesson.get('timestamp', '')[:19]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No market lessons recorded yet. Lessons are generated when predictions fail.")


# ===========================
# FUNDAMENTALS
# ===========================
elif view == "fundamentals":
    render_page_header("Fundamentals & Earnings", view_key="fundamentals")
    render_page_info("fundamentals")

    _fu_watchlist = load_watchlist_summary()
    _fu_tab1, _fu_tab2 = st.tabs(["Key Metrics", "Earnings Calendar"])

    with _fu_tab1:
        _fu_asset = st.selectbox("Asset", list(_fu_watchlist.keys()) if _fu_watchlist else ["BTC-USD"], key="fu_asset")
        _fu_ticker = _fu_watchlist.get(_fu_asset, {}).get("ticker", _fu_asset)
        _fu_category = _fu_watchlist.get(_fu_asset, {}).get("category", "")

        if _fu_ticker:
            with st.spinner(f"Fetching fundamentals for {_fu_ticker}..."):
                _fdata = fundamentals.get_fundamentals(_fu_ticker)

            _fu_asset_type = _fdata.get("asset_type", "stock")
            st.markdown(f"### {_fdata['name']}")

            # Show asset type badge
            _type_labels = {"commodity": "Commodity", "crypto": "Cryptocurrency", "forex": "Forex", "index": "Index", "stock": "Stock"}
            _type_colors = {"commodity": "#d29922", "crypto": "#a371f7", "forex": "#58a6ff", "index": "#3fb950", "stock": "#6e7681"}
            _fu_type_label = _type_labels.get(_fu_asset_type, "Asset")
            _fu_type_color = _type_colors.get(_fu_asset_type, "#6e7681")
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>"
                f"<span style='background:{_fu_type_color};color:#fff;padding:3px 10px;border-radius:6px;"
                f"font-size:0.75em;font-weight:700;'>{_fu_type_label.upper()}</span>"
                f"<span style='color:#8b949e;font-size:0.85em;'>{_fdata['sector']} — {_fdata['industry']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # For NON-STOCK assets: show price performance view
            if _fu_asset_type in ("commodity", "crypto", "forex", "index"):
                _pp = _fdata.get("price_performance", {})

                if _fu_asset_type != "stock":
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);border-radius:10px;"
                        f"padding:14px 18px;margin-bottom:16px;'>"
                        f"<div style='color:#8b949e;font-size:0.75em;letter-spacing:0.1em;margin-bottom:6px;'>"
                        f"WHY NO P/E OR EPS?</div>"
                        f"<div style='color:#c9d1d9;font-size:0.85em;line-height:1.5;'>"
                        f"{_fu_type_label}s don't have earnings, revenue, or P/E ratios like stocks. "
                        f"Instead, we show <b>price performance, volatility, and trading volume</b> — "
                        f"the metrics that matter for {_fu_type_label.lower()} analysis.</div></div>",
                        unsafe_allow_html=True,
                    )

                # Price Performance
                st.markdown("### Price Performance")
                _pp1, _pp2, _pp3, _pp4, _pp5 = st.columns(5)
                with _pp1:
                    st.metric("Current Price", f"${_pp.get('current_price', 'N/A')}")
                with _pp2:
                    st.metric("Day Change", _pp.get("day_change_pct", "N/A"))
                with _pp3:
                    st.metric("Week", _pp.get("week_change_pct", "N/A"))
                with _pp4:
                    st.metric("Month", _pp.get("month_change_pct", "N/A"))
                with _pp5:
                    st.metric("YTD", _pp.get("ytd_pct", "N/A"))

                st.divider()

                # Longer-term performance
                st.markdown("### Returns & Risk")
                _pr1, _pr2, _pr3, _pr4 = st.columns(4)
                with _pr1:
                    st.metric("3 Month", _pp.get("three_month_pct", "N/A"))
                with _pr2:
                    st.metric("6 Month", _pp.get("six_month_pct", "N/A"))
                with _pr3:
                    st.metric("1 Year", _pp.get("year_change_pct", "N/A"))
                with _pr4:
                    st.metric("30D Volatility", _pp.get("volatility_30d", "N/A"))

                st.divider()

                # 52-week range + volume
                st.markdown("### Trading Range")
                _ptr1, _ptr2, _ptr3 = st.columns(3)
                with _ptr1:
                    st.metric("52W High", f"${_pp.get('52w_high', 'N/A')}")
                with _ptr2:
                    st.metric("52W Low", f"${_pp.get('52w_low', 'N/A')}")
                with _ptr3:
                    st.metric("Avg Volume (30D)", _pp.get("avg_volume_fmt", "N/A"))

                # 52-week range bar
                _pp_hi = _pp.get("52w_high", 0)
                _pp_lo = _pp.get("52w_low", 0)
                _pp_cur = _pp.get("current_price", 0)
                if isinstance(_pp_hi, (int, float)) and isinstance(_pp_lo, (int, float)) and _pp_hi > _pp_lo:
                    _pp_pct = min(max((_pp_cur - _pp_lo) / (_pp_hi - _pp_lo) * 100, 0), 100)
                    st.markdown(
                        f"<div style='margin:8px 0 16px 0;'>"
                        f"<div style='display:flex;justify-content:space-between;font-family:JetBrains Mono,monospace;font-size:0.75em;color:#8b949e;'>"
                        f"<span>${_pp_lo}</span><span>Current: ${_pp_cur}</span><span>${_pp_hi}</span></div>"
                        f"<div style='background:rgba(48,54,61,0.5);border-radius:4px;height:8px;margin-top:4px;position:relative;'>"
                        f"<div style='background:linear-gradient(90deg,#f85149,#d29922,#3fb950);border-radius:4px;height:100%;width:100%;opacity:0.3;'></div>"
                        f"<div style='position:absolute;top:-2px;left:{_pp_pct}%;width:4px;height:12px;background:#e6edf3;border-radius:2px;transform:translateX(-50%);'></div>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
            else:
                # STOCK VIEW — original layout
                st.markdown("### Valuation")
                _fv1, _fv2, _fv3, _fv4, _fv5 = st.columns(5)
                with _fv1:
                    st.metric("P/E Ratio", _fdata["pe_ratio"])
                with _fv2:
                    st.metric("Forward P/E", _fdata["forward_pe"])
                with _fv3:
                    st.metric("P/B Ratio", _fdata["pb_ratio"])
                with _fv4:
                    st.metric("PEG", _fdata["peg_ratio"])
                with _fv5:
                    st.metric("Market Cap", _fdata["market_cap_fmt"])

                st.divider()

                st.markdown("### Profitability")
                _fp1, _fp2, _fp3, _fp4 = st.columns(4)
                with _fp1:
                    st.metric("EPS", _fdata["eps"])
                with _fp2:
                    st.metric("Revenue", _fdata["revenue_fmt"])
                with _fp3:
                    st.metric("Profit Margin", _fdata["profit_margin"])
                with _fp4:
                    st.metric("ROE", _fdata["roe"])

                st.divider()

                st.markdown("### Financial Health")
                _fh1, _fh2, _fh3, _fh4 = st.columns(4)
                with _fh1:
                    st.metric("D/E Ratio", _fdata["debt_to_equity"])
                with _fh2:
                    st.metric("Current Ratio", _fdata["current_ratio"])
                with _fh3:
                    st.metric("Beta", _fdata["beta"])
                with _fh4:
                    st.metric("Dividend Yield", _fdata["dividend_yield"])

                st.divider()

                st.markdown("### Analyst Targets")
                _fa1, _fa2, _fa3, _fa4 = st.columns(4)
                with _fa1:
                    st.metric("Recommendation", _fdata["recommendation"].upper() if _fdata["recommendation"] != "N/A" else "N/A")
                with _fa2:
                    st.metric("Target (Mean)", f"${_fdata['target_mean']}" if _fdata["target_mean"] != "N/A" else "N/A")
                with _fa3:
                    st.metric("Target (High)", f"${_fdata['target_high']}" if _fdata["target_high"] != "N/A" else "N/A")
                with _fa4:
                    st.metric("# Analysts", _fdata["num_analysts"])

                st.markdown("### Price Range")
                _fr1, _fr2 = st.columns(2)
                with _fr1:
                    st.metric("52W High", f"${_fdata['52w_high']}" if _fdata["52w_high"] != "N/A" else "N/A")
                with _fr2:
                    st.metric("52W Low", f"${_fdata['52w_low']}" if _fdata["52w_low"] != "N/A" else "N/A")

    with _fu_tab2:
        st.markdown("### Upcoming Earnings")
        _fu_tickers = [d.get("ticker", "") for d in _fu_watchlist.values() if d.get("ticker")]
        if _fu_tickers:
            with st.spinner("Fetching earnings calendar..."):
                _earnings = fundamentals.get_earnings_calendar(_fu_tickers)
            if _earnings:
                _er = [{"Ticker": e["ticker"], "Date": e["earnings_date"],
                        "EPS Est.": e.get("eps_estimate", "N/A"),
                        "Rev. Est.": e.get("revenue_estimate", "N/A")} for e in _earnings]
                st.dataframe(pd.DataFrame(_er), use_container_width=True, hide_index=True)
            else:
                st.caption("No upcoming earnings found.")
        else:
            st.caption("No tickers in watchlist.")


# ===========================
# MARKET OVERVIEW (Sectors + Correlation + Breadth)
# ===========================
elif view == "market_overview":
    render_page_header("Market Overview", view_key="market_overview")
    render_page_info("market_overview")

    _mo_tab1, _mo_tab2, _mo_tab3 = st.tabs(["Sector Heatmap", "Correlation Matrix", "Market Breadth"])

    with _mo_tab1:
        st.markdown("### Sector Performance")
        _mo_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=2, key="sector_period")
        with st.spinner("Fetching sector data..."):
            _sectors = sector_analysis.get_sector_performance(_mo_period)
        if _sectors:
            st.plotly_chart(sector_analysis.build_sector_treemap(_sectors), use_container_width=True)
            _sec_rows = [{"Sector": s["sector"], "Ticker": s["ticker"],
                          "Price": f"${s['price']:,.2f}", "Change": f"{s['change_pct']:+.2f}%"}
                         for s in sorted(_sectors, key=lambda x: x["change_pct"], reverse=True)]
            st.dataframe(pd.DataFrame(_sec_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("Could not fetch sector data.")

    with _mo_tab2:
        st.markdown("### Asset Correlation Matrix")
        _mo_watchlist = load_watchlist_summary()
        _mo_tickers = {name: d.get("ticker", "") for name, d in _mo_watchlist.items() if d.get("ticker")}
        if len(_mo_tickers) >= 2:
            _corr_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1, key="corr_period")
            with st.spinner("Computing correlations..."):
                _corr = sector_analysis.get_correlation_matrix(_mo_tickers, _corr_period)
            if not _corr.empty:
                st.plotly_chart(sector_analysis.build_correlation_heatmap(_corr), use_container_width=True)
            else:
                st.warning("Not enough data for correlation.")
        else:
            st.info("Need at least 2 assets in watchlist for correlation.")

    with _mo_tab3:
        st.markdown("### Market Breadth (S&P 500 Sample)")
        with st.spinner("Analyzing market breadth..."):
            _breadth = sector_analysis.get_market_breadth()
        if _breadth:
            _mb1, _mb2, _mb3, _mb4 = st.columns(4)
            with _mb1:
                st.metric("Above SMA 50", f"{_breadth['above_sma50_pct']}%",
                          delta=f"{_breadth['above_sma50']}/{_breadth['total_stocks']}")
            with _mb2:
                st.metric("Above SMA 200", f"{_breadth['above_sma200_pct']}%",
                          delta=f"{_breadth['above_sma200']}/{_breadth['total_stocks']}")
            with _mb3:
                st.metric("Advancing", _breadth["advancing"])
            with _mb4:
                st.metric("A/D Ratio", _breadth["adv_dec_ratio"])
        else:
            st.warning("Could not fetch breadth data.")


# ===========================
# MORNING BRIEF — One-page daily market snapshot
# ===========================
elif view == "morning_brief":
    render_page_header("Morning Brief", view_key="morning_brief")
    render_page_info("morning_brief")

    _mb_gen = morning_brief_mod.MorningBrief()

    # Generate or load cached
    if st.button("Generate Fresh Brief", key="mb_refresh_btn"):
        with st.spinner("Generating morning brief..."):
            _mb_data = _mb_gen.generate()
    else:
        _mb_data = _mb_gen.load_cached()
        if not _mb_data:
            with st.spinner("Generating your first morning brief..."):
                _mb_data = _mb_gen.generate()

    if _mb_data:
        # -- Detect stale brief (> 6 hours old) --
        _mb_is_stale = False
        _mb_age_hours = 0
        _mb_ts_raw = _mb_data.get("timestamp", "")
        if _mb_ts_raw:
            try:
                _mb_gen_time = datetime.fromisoformat(_mb_ts_raw)
                if _mb_gen_time.tzinfo is None:
                    _mb_gen_time = _mb_gen_time.replace(tzinfo=timezone.utc)
                _mb_age_hours = (datetime.now(timezone.utc) - _mb_gen_time).total_seconds() / 3600
                _mb_is_stale = _mb_age_hours > 6
            except Exception:
                _mb_is_stale = True
                _mb_age_hours = 0

        # -- Stale warning badge --
        if _mb_is_stale:
            _stale_age_str = f"{_mb_age_hours:.0f}h ago" if _mb_age_hours > 0 else "unknown age"
            st.markdown(
                f"<div style='background:rgba(210,153,34,0.15);border:1px solid rgba(210,153,34,0.5);"
                f"border-radius:8px;padding:10px 16px;margin-bottom:12px;"
                f"display:flex;align-items:center;gap:10px;'>"
                f"<span style='font-size:1.2em;'>&#9888;&#65039;</span>"
                f"<div>"
                f"<span style='color:#d29922;font-weight:700;font-size:0.9em;'>STALE BRIEF</span>"
                f"<span style='color:#8b949e;font-size:0.82em;'> &mdash; "
                f"Generated {_stale_age_str}. Watchlist table below uses live scan data. "
                f"Click <b>Generate Fresh Brief</b> for a full update.</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        # -- Date & Headline Banner --
        _mb_headline = _mb_data.get("headline", "Markets Overview")
        _mb_date = _mb_data.get("date_display", "")
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#161b22,#1c2333);"
            f"border:1px solid rgba(48,54,61,0.6);border-radius:12px;"
            f"padding:20px 24px;margin-bottom:16px;'>"
            f"<div style='color:#8b949e;font-size:0.8em;margin-bottom:6px;'>"
            f"{_mb_date}</div>"
            f"<div style='color:#e6edf3;font-size:1.3em;font-weight:700;'>"
            f"{_mb_headline}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # -- Top Row: Regime + Risk + Signal Overview --
        _mb_c1, _mb_c2, _mb_c3 = st.columns(3)

        with _mb_c1:
            _mb_regime = _mb_data.get("regime", {})
            _mb_r_icon = _mb_regime.get("icon", "⚪")
            _mb_r_name = _mb_regime.get("name", "NEUTRAL")
            _mb_r_desc = _mb_regime.get("description", "")
            _mb_r_conf = _mb_regime.get("confidence", 0)
            st.markdown(
                f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                f"border-radius:10px;padding:16px;height:140px;'>"
                f"<div style='color:#8b949e;font-size:0.75em;letter-spacing:0.1em;margin-bottom:8px;'>"
                f"MACRO REGIME</div>"
                f"<div style='font-size:1.5em;'>{_mb_r_icon} {_mb_r_name}</div>"
                f"<div style='color:#8b949e;font-size:0.78em;margin-top:4px;'>{_mb_r_desc}</div>"
                f"<div style='color:#8b949e;font-size:0.7em;margin-top:4px;'>"
                f"Confidence: {int(_mb_r_conf*100)}%</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with _mb_c2:
            _mb_risk = _mb_data.get("risk", {})
            _mb_ri_icon = _mb_risk.get("icon", "🟢")
            _mb_ri_level = _mb_risk.get("level", "CALM")
            _mb_ri_events = _mb_risk.get("geo_events", 0)
            _mb_ri_dominant = _mb_risk.get("dominant_events", [])
            _mb_ri_color = {"EXTREME": "#f85149", "ELEVATED": "#d29922", "MODERATE": "#d29922", "LOW": "#58a6ff", "CALM": "#3fb950"}.get(_mb_ri_level, "#6e7681")
            st.markdown(
                f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                f"border-radius:10px;padding:16px;height:140px;'>"
                f"<div style='color:#8b949e;font-size:0.75em;letter-spacing:0.1em;margin-bottom:8px;'>"
                f"GEOPOLITICAL RISK</div>"
                f"<div style='font-size:1.5em;'>{_mb_ri_icon} "
                f"<span style='color:{_mb_ri_color};'>{_mb_ri_level}</span></div>"
                f"<div style='color:#8b949e;font-size:0.78em;margin-top:4px;'>"
                f"{_mb_ri_events} geo events detected</div>"
                f"<div style='color:#8b949e;font-size:0.7em;margin-top:4px;'>"
                f"{', '.join(_mb_ri_dominant[:3]) if _mb_ri_dominant else 'No dominant themes'}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with _mb_c3:
            _mb_sigs = _mb_data.get("signals_overview", {})
            _mb_s_total = _mb_sigs.get("total", 0)
            _mb_s_buy = _mb_sigs.get("buy", 0)
            _mb_s_sell = _mb_sigs.get("sell", 0)
            _mb_s_neutral = _mb_sigs.get("neutral", 0)
            st.markdown(
                f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                f"border-radius:10px;padding:16px;height:140px;'>"
                f"<div style='color:#8b949e;font-size:0.75em;letter-spacing:0.1em;margin-bottom:8px;'>"
                f"SIGNAL OVERVIEW</div>"
                f"<div style='font-size:1.5em;'>{_mb_data.get('tone_emoji', '↔️')} "
                f"{_mb_data.get('market_tone', 'Mixed')}</div>"
                f"<div style='margin-top:8px;'>"
                f"<span style='color:#3fb950;font-size:0.85em;'>Buy: {_mb_s_buy}</span>"
                f" &middot; "
                f"<span style='color:#f85149;font-size:0.85em;'>Sell: {_mb_s_sell}</span>"
                f" &middot; "
                f"<span style='color:#6e7681;font-size:0.85em;'>Neutral: {_mb_s_neutral}</span>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # -- Top Picks --
        _mb_picks = _mb_data.get("top_picks", [])
        if _mb_picks:
            st.markdown(f"### Top Trading Opportunities ({len(_mb_picks)} assets)")
            for _pick in _mb_picks:
                _p_emoji = _pick.get("emoji", "⚪")
                _p_verdict = _pick.get("verdict", "WAIT")
                _p_asset = _pick.get("asset", "")
                _p_signal = _pick.get("signal", "")
                _p_conf = _pick.get("confidence", 0)
                _p_price = _pick.get("price", 0)
                _p_change = _pick.get("change_pct", 0)
                _p_reason = _pick.get("reason", "")
                _p_v_color = _pick.get("color", "#6e7681")
                _p_chg_color = "#3fb950" if _p_change >= 0 else "#f85149"
                _p_chg_str = f"+{_p_change:.1f}%" if _p_change >= 0 else f"{_p_change:.1f}%"

                st.markdown(
                    f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    f"border-left:4px solid {_p_v_color};"
                    f"border-radius:10px;padding:14px 18px;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:12px;'>"
                    f"<span style='font-size:1.6em;'>{_p_emoji}</span>"
                    f"<div style='flex:1;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<span style='color:#e6edf3;font-size:1.05em;font-weight:700;'>{_p_asset}</span>"
                    f"<span style='background:{_p_v_color};color:#fff;padding:3px 10px;"
                    f"border-radius:6px;font-size:0.8em;font-weight:700;'>{_p_verdict}</span>"
                    f"</div>"
                    f"<div style='color:#8b949e;font-size:0.82em;margin-top:4px;'>"
                    f"Signal: {_p_signal} &middot; Confidence: {_p_conf}% &middot; "
                    f"Price: ${_p_price:,.2f} "
                    f"(<span style='color:{_p_chg_color};'>{_p_chg_str}</span>)</div>"
                    f"<div style='color:#6e7681;font-size:0.78em;font-style:italic;margin-top:4px;'>"
                    f"{_p_reason}</div>"
                    f"</div></div></div>",
                    unsafe_allow_html=True,
                )
                if _p_asset:
                    asset_link_button(_p_asset, f"mb_{_p_asset}")

        # -- Upcoming Events --
        _mb_cal = _mb_data.get("calendar", [])
        if _mb_cal:
            st.divider()
            st.markdown("### Upcoming High-Impact Events")
            for _ev in _mb_cal:
                _ev_impact_stars = "⭐" * _ev.get("impact", 1)
                _ev_assets_str = ", ".join(_ev.get("assets", [])[:4])
                st.markdown(
                    f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    f"border-radius:8px;padding:10px 16px;margin-bottom:6px;"
                    f"display:flex;align-items:center;gap:12px;'>"
                    f"<span style='font-size:1.2em;'>{_ev.get('icon', '📅')}</span>"
                    f"<div style='flex:1;'>"
                    f"<span style='color:#e6edf3;font-weight:600;'>{_ev.get('name', '')}</span>"
                    f" <span style='color:#8b949e;font-size:0.8em;'>{_ev_impact_stars}</span>"
                    f"<div style='color:#8b949e;font-size:0.78em;'>"
                    f"{_ev.get('date', '')} &middot; Affects: {_ev_assets_str}</div>"
                    f"</div>"
                    f"<span style='color:#58a6ff;font-weight:600;font-size:0.9em;'>"
                    f"{_ev.get('countdown', '')}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # -- Social Pulse --
        _mb_social = _mb_data.get("social_pulse", {})
        if _mb_social.get("available"):
            st.divider()
            st.markdown("### Social Pulse")
            _mb_sp_movers = _mb_social.get("movers", [])
            _mb_sp_inf = _mb_social.get("influencer_alerts", [])

            if _mb_sp_movers:
                _sp_cols = st.columns(min(len(_mb_sp_movers), 5))
                for _spi, _spm in enumerate(_mb_sp_movers):
                    with _sp_cols[_spi % 5]:
                        _spm_score = _spm.get("score", 0)
                        _spm_color = "#3fb950" if _spm_score > 0.1 else "#f85149" if _spm_score < -0.1 else "#6e7681"
                        _spm_label = _spm.get("label", "NEUTRAL").replace("_", " ")
                        _spm_buzz = _spm.get("buzz", "LOW")
                        _buzz_icon = "🔥" if _spm_buzz == "HIGH" else "📊" if _spm_buzz == "MEDIUM" else "💤"
                        st.markdown(
                            f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                            f"border-radius:8px;padding:12px;text-align:center;'>"
                            f"<div style='color:#e6edf3;font-weight:700;font-size:0.9em;'>{_spm.get('asset', '')}</div>"
                            f"<div style='color:{_spm_color};font-family:JetBrains Mono,monospace;"
                            f"font-size:1.1em;font-weight:700;margin:4px 0;'>{_spm_score:+.2f}</div>"
                            f"<div style='font-size:0.75em;color:#8b949e;'>{_spm_label} {_buzz_icon}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            if _mb_sp_inf:
                for _inf_a in _mb_sp_inf:
                    _inf_msg = html.escape(_inf_a.get("message", "")[:100])
                    st.markdown(
                        f"<div style='background:#161b22;border-left:3px solid #d29922;"
                        f"border-radius:6px;padding:8px 14px;margin-top:6px;'>"
                        f"<span style='color:#d29922;font-size:0.82em;font-weight:600;'>🔔 INFLUENCER:</span> "
                        f"<span style='color:#e6edf3;font-size:0.82em;'>{_inf_msg}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        # -- Key Takeaway --
        st.divider()
        _mb_takeaway = _mb_data.get("key_takeaway", "")
        if _mb_takeaway:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#0d2818,#161b22);"
                f"border:1px solid rgba(63,185,80,0.3);border-radius:12px;"
                f"padding:18px 22px;'>"
                f"<div style='color:#3fb950;font-size:0.8em;font-weight:700;"
                f"letter-spacing:0.1em;margin-bottom:8px;'>KEY TAKEAWAY</div>"
                f"<div style='color:#e6edf3;font-size:1em;line-height:1.5;'>"
                f"{_mb_takeaway}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # -- Watchlist Summary Table --
        # When brief is stale, use LIVE data from watchlist_summary.json
        # instead of the cached brief's watchlist_summary section.
        _mb_wl = _mb_data.get("watchlist_summary", [])
        _mb_wl_source = "brief"

        if _mb_is_stale:
            # Fall back to live watchlist_summary.json (same source as Daily Advisor)
            _mb_live_raw = _load_raw_watchlist_summary()
            if _mb_live_raw:
                _mb_wl_live = []
                for _asset_name, _info in _mb_live_raw.items():
                    _conf_raw = _info.get("confidence", {})
                    _conf_pct = _conf_raw.get("confidence_pct", 0) if isinstance(_conf_raw, dict) else _conf_raw
                    _sig_label = _info.get("signal_label", _info.get("signal", "NEUTRAL"))
                    _classified = _mb_gen._classify_signal(_sig_label, _conf_pct)
                    _mb_wl_live.append({
                        "asset": _asset_name,
                        "signal": _sig_label,
                        "confidence": _conf_pct,
                        "verdict": _classified["verdict"],
                        "emoji": _classified["emoji"],
                        "price": _info.get("price", 0),
                        "change_pct": _info.get("daily_change_pct", _info.get("price_change_pct", 0)),
                    })
                # Sort by confidence descending
                _mb_wl_live.sort(key=lambda s: abs(s["confidence"]), reverse=True)
                if _mb_wl_live:
                    _mb_wl = _mb_wl_live
                    _mb_wl_source = "live"

        if _mb_wl:
            st.divider()
            if _mb_wl_source == "live":
                st.markdown(
                    "### Full Watchlist Status "
                    "<span style='background:#d29922;color:#000;padding:2px 8px;"
                    "border-radius:4px;font-size:0.55em;font-weight:700;"
                    "vertical-align:middle;margin-left:8px;'>LIVE DATA</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown("### Full Watchlist Status")
            _mb_tbl = []
            for _w in _mb_wl:
                _w_chg = _w.get("change_pct", 0)
                _mb_tbl.append({
                    "": _w.get("emoji", ""),
                    "Asset": _w.get("asset", ""),
                    "Verdict": _w.get("verdict", ""),
                    "Signal": _w.get("signal", ""),
                    "Confidence": f"{_w.get('confidence', 0)}%",
                    "Price": f"${_w.get('price', 0):,.2f}",
                    "Change": f"{_w_chg:+.1f}%" if _w_chg else "",
                })
            st.dataframe(pd.DataFrame(_mb_tbl), use_container_width=True, hide_index=True)

        # Timestamp
        _mb_ts = _mb_data.get("timestamp", "")
        if _mb_ts:
            st.markdown(
                f"<div style='text-align:center;color:#8b949e;font-size:0.72em;"
                f"font-family:JetBrains Mono,monospace;margin-top:16px;'>"
                f"Brief generated: {_mb_ts}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Could not generate morning brief. Run a market scan first to populate data.")


# ===========================
# ECONOMIC CALENDAR — Event countdown and impact tracking
# ===========================
elif view == "econ_calendar":
    render_page_header("Economic Calendar", view_key="econ_calendar")
    render_page_info("econ_calendar")

    _ec = econ_cal_mod.EconomicCalendar()
    _ec_events = _ec.get_upcoming_events(limit=40)

    if _ec_events:
        # -- Next Event Banner --
        _ec_next = _ec_events[0]
        _ec_urgency_colors = {
            "imminent": "#f85149", "today": "#d29922", "tomorrow": "#d29922",
            "this_week": "#58a6ff", "later": "#6e7681", "past": "#484f58",
        }
        _ec_next_color = _ec_urgency_colors.get(_ec_next.get("urgency", "later"), "#6e7681")
        _ec_next_stars = "⭐" * _ec_next.get("impact", 1)

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#161b22,#1a1f2e);"
            f"border:1px solid {_ec_next_color};border-radius:12px;"
            f"padding:20px 24px;margin-bottom:20px;'>"
            f"<div style='color:#8b949e;font-size:0.75em;letter-spacing:0.1em;margin-bottom:6px;'>"
            f"NEXT EVENT</div>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div>"
            f"<div style='color:#e6edf3;font-size:1.3em;font-weight:700;'>"
            f"{_ec_next.get('icon', '')} {_ec_next.get('name', '')}</div>"
            f"<div style='color:#8b949e;font-size:0.85em;margin-top:4px;'>"
            f"{_ec_next.get('date_display', '')} &middot; Impact: {_ec_next_stars}</div>"
            f"</div>"
            f"<div style='text-align:right;'>"
            f"<div style='color:{_ec_next_color};font-size:2em;font-weight:800;'>"
            f"{_ec_next.get('countdown', '')}</div>"
            f"<div style='color:#8b949e;font-size:0.75em;'>until event</div>"
            f"</div></div>"
            f"<div style='color:#6e7681;font-size:0.82em;margin-top:10px;'>"
            f"{_ec_next.get('description', '')}</div>"
            f"<div style='color:#8b949e;font-size:0.78em;margin-top:6px;'>"
            f"Typical move: {_ec_next.get('typical_move', '')}</div>"
            f"<div style='color:#58a6ff;font-size:0.78em;margin-top:4px;'>"
            f"Affects: {', '.join(_ec_next.get('assets_affected', []))}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # -- Filter Tabs --
        _ec_tab1, _ec_tab2, _ec_tab3 = st.tabs([
            "All Upcoming Events", "High Impact Only", "By Category"
        ])

        with _ec_tab1:
            # Group events by urgency
            _ec_groups = {}
            for ev in _ec_events:
                urgency = ev.get("urgency", "later")
                urgency_labels = {
                    "imminent": "HAPPENING NOW", "today": "TODAY",
                    "tomorrow": "TOMORROW", "this_week": "THIS WEEK",
                    "later": "COMING UP", "past": "JUST PASSED",
                }
                group_label = urgency_labels.get(urgency, "COMING UP")
                if group_label not in _ec_groups:
                    _ec_groups[group_label] = []
                _ec_groups[group_label].append(ev)

            for group_label, group_events in _ec_groups.items():
                _ec_gl_color = _ec_urgency_colors.get(
                    group_events[0].get("urgency", "later"), "#6e7681"
                )
                st.markdown(
                    f"<div style='color:{_ec_gl_color};font-size:0.82em;font-weight:700;"
                    f"letter-spacing:0.1em;margin:16px 0 8px 0;'>{group_label}</div>",
                    unsafe_allow_html=True,
                )
                for ev in group_events:
                    _ev_stars = "⭐" * ev.get("impact", 1)
                    _ev_color = _ec_urgency_colors.get(ev.get("urgency", "later"), "#6e7681")
                    _ev_assets = ", ".join(ev.get("assets_affected", [])[:5])
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-left:3px solid {_ev_color};"
                        f"border-radius:8px;padding:12px 16px;margin-bottom:6px;"
                        f"display:flex;justify-content:space-between;align-items:center;'>"
                        f"<div style='display:flex;align-items:center;gap:10px;'>"
                        f"<span style='font-size:1.3em;'>{ev.get('icon', '📅')}</span>"
                        f"<div>"
                        f"<div style='color:#e6edf3;font-weight:600;'>"
                        f"{ev.get('name', '')} {_ev_stars}</div>"
                        f"<div style='color:#8b949e;font-size:0.78em;'>"
                        f"{ev.get('date_display', '')} &middot; {_ev_assets}</div>"
                        f"</div></div>"
                        f"<div style='color:{_ev_color};font-weight:700;font-size:0.9em;"
                        f"white-space:nowrap;'>{ev.get('countdown', '')}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        with _ec_tab2:
            _ec_high = [e for e in _ec_events if e.get("impact", 0) >= 3]
            if _ec_high:
                st.markdown(f"**{len(_ec_high)} high-impact events** in the pipeline:")
                for ev in _ec_high:
                    _ev_color = _ec_urgency_colors.get(ev.get("urgency", "later"), "#6e7681")
                    st.markdown(
                        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                        f"border-left:4px solid {_ev_color};"
                        f"border-radius:10px;padding:14px 18px;margin-bottom:8px;'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                        f"<div>"
                        f"<div style='color:#e6edf3;font-size:1.05em;font-weight:700;'>"
                        f"{ev.get('icon', '')} {ev.get('name', '')}</div>"
                        f"<div style='color:#8b949e;font-size:0.82em;margin-top:4px;'>"
                        f"{ev.get('date_display', '')}</div>"
                        f"</div>"
                        f"<div style='color:{_ev_color};font-size:1.5em;font-weight:800;'>"
                        f"{ev.get('countdown', '')}</div>"
                        f"</div>"
                        f"<div style='color:#6e7681;font-size:0.82em;margin-top:8px;'>"
                        f"{ev.get('description', '')}</div>"
                        f"<div style='color:#8b949e;font-size:0.78em;margin-top:6px;'>"
                        f"Typical move: {ev.get('typical_move', '')}</div>"
                        f"<div style='color:#58a6ff;font-size:0.78em;margin-top:4px;'>"
                        f"Affects: {', '.join(ev.get('assets_affected', []))}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No high-impact events upcoming.")

        with _ec_tab3:
            # Group by category
            _ec_cats = {}
            for ev in _ec_events:
                cat = ev.get("category", "other")
                if cat not in _ec_cats:
                    _ec_cats[cat] = []
                _ec_cats[cat].append(ev)

            _cat_icons = {
                "central_bank": "🏦", "employment": "👷", "inflation": "📊",
                "energy": "⛽", "growth": "📈", "manufacturing": "🔧",
                "consumer": "🛒", "bonds": "📜",
            }

            for cat, cat_events in _ec_cats.items():
                cat_icon = _cat_icons.get(cat, "📅")
                st.markdown(f"#### {cat_icon} {cat.replace('_', ' ').title()} ({len(cat_events)} events)")
                for ev in cat_events[:8]:
                    _ev_color = _ec_urgency_colors.get(ev.get("urgency", "later"), "#6e7681")
                    st.markdown(
                        f"<div style='background:#0d1117;border:1px solid rgba(48,54,61,0.3);"
                        f"border-radius:6px;padding:8px 14px;margin-bottom:4px;"
                        f"display:flex;justify-content:space-between;align-items:center;'>"
                        f"<span style='color:#e6edf3;font-size:0.88em;'>"
                        f"{ev.get('icon', '')} {ev.get('short', ev.get('name', ''))}"
                        f" — {ev.get('date_display', '')}</span>"
                        f"<span style='color:{_ev_color};font-weight:600;font-size:0.85em;'>"
                        f"{ev.get('countdown', '')}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        # -- Event Type Reference --
        st.divider()
        with st.expander("Event Type Reference — What Each Event Means", expanded=False):
            _ec_types = _ec.get_event_types()
            for et in _ec_types:
                _et_stars = "⭐" * et.get("impact", 1)
                st.markdown(
                    f"**{et.get('icon', '')} {et.get('name', '')}** {_et_stars}\n\n"
                    f"{et.get('description', '')}\n\n"
                    f"*Typical move:* {et.get('typical_move', '')}\n\n"
                    f"*Assets affected:* {', '.join(et.get('assets_affected', []))}\n\n"
                    f"---"
                )
    else:
        st.info("No economic events available.")


# ===========================
# TRADE JOURNAL — Complete Trade History & Analysis
# ===========================
elif view == "trade_journal":
    render_page_header("Trade Journal", view_key="trade_journal")
    render_page_info("trade_journal")

    _tj_history = paper_trader.get_trade_history()
    _tj_open = paper_trader._load().get("open_positions", [])

    if not _tj_history and not _tj_open:
        st.info("No trades yet. Open some paper trades to start building your journal.")
    else:
        # ── Summary Metrics ──
        _tj_wins = [t for t in _tj_history if t.get("pnl", 0) > 0]
        _tj_losses = [t for t in _tj_history if t.get("pnl", 0) < 0]
        _tj_total_pnl = sum(t.get("pnl", 0) for t in _tj_history)
        _tj_best = max((t.get("pnl", 0) for t in _tj_history), default=0)
        _tj_worst = min((t.get("pnl", 0) for t in _tj_history), default=0)
        _tj_wr = round(len(_tj_wins) / len(_tj_history) * 100, 1) if _tj_history else 0
        _tj_streaks = performance_analytics.consecutive_wins_losses(_tj_history)
        _tj_avg_hold = performance_analytics.avg_holding_time(_tj_history)

        _tjm1, _tjm2, _tjm3, _tjm4, _tjm5, _tjm6 = st.columns(6)
        with _tjm1:
            st.metric("Total Trades", len(_tj_history))
        with _tjm2:
            _pnl_color = "normal" if _tj_total_pnl >= 0 else "inverse"
            st.metric("Total P&L", f"${_tj_total_pnl:+,.2f}", delta_color=_pnl_color)
        with _tjm3:
            st.metric("Win Rate", f"{_tj_wr}%", delta=f"{len(_tj_wins)}W/{len(_tj_losses)}L")
        with _tjm4:
            st.metric("Best Trade", f"${_tj_best:+,.2f}")
        with _tjm5:
            st.metric("Worst Trade", f"${_tj_worst:+,.2f}")
        with _tjm6:
            st.metric("Avg Hold Time", _tj_avg_hold)

        # Streak badges
        _tjsk1, _tjsk2, _tjsk3 = st.columns(3)
        with _tjsk1:
            st.metric("Max Win Streak", f"{_tj_streaks['max_consecutive_wins']} trades")
        with _tjsk2:
            st.metric("Max Loss Streak", f"{_tj_streaks['max_consecutive_losses']} trades")
        with _tjsk3:
            st.metric("Open Positions", len(_tj_open))

        st.divider()

        # ── Filters ──
        st.markdown("### Filter Trades")
        _tj_fc1, _tj_fc2, _tj_fc3 = st.columns(3)
        with _tj_fc1:
            _tj_all_assets = sorted(set(t.get("asset", "?") for t in _tj_history)) if _tj_history else []
            _tj_filter_asset = st.selectbox("Asset", ["All"] + _tj_all_assets, key="tj_asset")
        with _tj_fc2:
            _tj_filter_dir = st.selectbox("Direction", ["All", "Long", "Short"], key="tj_dir")
        with _tj_fc3:
            _tj_filter_outcome = st.selectbox("Outcome", ["All", "Winners", "Losers"], key="tj_outcome")

        # Apply filters
        _tj_filtered = _tj_history.copy()
        if _tj_filter_asset != "All":
            _tj_filtered = [t for t in _tj_filtered if t.get("asset") == _tj_filter_asset]
        if _tj_filter_dir != "All":
            _tj_filtered = [t for t in _tj_filtered if t.get("direction", "").lower() == _tj_filter_dir.lower()]
        if _tj_filter_outcome == "Winners":
            _tj_filtered = [t for t in _tj_filtered if t.get("pnl", 0) > 0]
        elif _tj_filter_outcome == "Losers":
            _tj_filtered = [t for t in _tj_filtered if t.get("pnl", 0) < 0]

        st.caption(f"Showing {len(_tj_filtered)} of {len(_tj_history)} trades")

        # ── Charts ──
        if _tj_filtered:
            st.divider()
            _tjc1, _tjc2 = st.columns(2)
            with _tjc1:
                st.markdown("### Trade Timeline")
                try:
                    st.plotly_chart(performance_analytics.trade_timeline_chart(_tj_filtered), use_container_width=True)
                except Exception:
                    st.info("Need at least 2 closed trades with timestamps for timeline.")
            with _tjc2:
                st.markdown("### Win/Loss Streaks")
                try:
                    st.plotly_chart(performance_analytics.win_loss_streak_chart(_tj_filtered), use_container_width=True)
                except Exception:
                    st.info("Need more trades to calculate win/loss streaks.")

            # Hourly performance
            st.markdown("### Performance by Hour of Day")
            st.caption("Which hours produce the best trades? Use this to optimize your trading schedule.")
            try:
                st.plotly_chart(performance_analytics.hourly_performance_chart(_tj_filtered), use_container_width=True)
            except Exception:
                st.info("Need at least 3 trades across different hours for hourly analysis.")
        else:
            st.info("No trades match current filters. Adjust your filters above to see results.")

        # ── Trade Table ──
        st.divider()
        st.markdown("### Trade History")
        # Quick asset links for filtered trades
        _tj_unique_assets = sorted(set(t.get("asset", "?") for t in _tj_filtered))
        if _tj_unique_assets:
            _tj_link_cols = st.columns(min(len(_tj_unique_assets), 6))
            for _tj_i, _tj_a in enumerate(_tj_unique_assets):
                with _tj_link_cols[_tj_i % min(len(_tj_unique_assets), 6)]:
                    asset_link_button(_tj_a, "tj")
        _tj_sorted = sorted(_tj_filtered, key=lambda x: x.get("closed_at", ""), reverse=True)
        _tj_rows = []
        for t in _tj_sorted:
            _t_pnl = t.get("pnl", 0)
            _t_pct_return = 0
            _t_usd = t.get("usd_amount", 0)
            if _t_usd > 0:
                _t_pct_return = round(_t_pnl / _t_usd * 100, 2)
            _t_exit_reason = t.get("exit_reason", "manual")
            _t_hold = ""
            try:
                _t_opened = datetime.fromisoformat(t.get("opened_at", ""))
                _t_closed = datetime.fromisoformat(t.get("closed_at", ""))
                _t_dur = _t_closed - _t_opened
                _t_secs = _t_dur.total_seconds()
                if _t_secs < 3600:
                    _t_hold = f"{_t_secs / 60:.0f}m"
                elif _t_secs < 86400:
                    _t_hold = f"{_t_secs / 3600:.1f}h"
                else:
                    _t_hold = f"{_t_secs / 86400:.1f}d"
            except (ValueError, TypeError):
                pass

            _t_note_raw = t.get("notes", "")
            _t_note_preview = ""
            if _t_note_raw:
                _t_note_trunc = (_t_note_raw[:40] + "...") if len(_t_note_raw) > 40 else _t_note_raw
                _t_note_preview = _t_note_trunc

            _tj_rows.append({
                "Closed": t.get("closed_at", "")[:16].replace("T", " "),
                "Asset": t.get("asset", ""),
                "Dir": t.get("direction", "").upper()[:1],
                "Entry": f"${t.get('entry_price', 0):,.2f}",
                "Exit": f"${t.get('exit_price', 0):,.2f}",
                "Size": f"${_t_usd:,.0f}",
                "P&L": f"${_t_pnl:+,.2f}",
                "Return": f"{_t_pct_return:+.1f}%",
                "Exit Type": _t_exit_reason.replace("_", " ").title(),
                "Hold": _t_hold,
                "Signal": t.get("signal_hint", ""),
                "Notes": _t_note_preview,
            })

        if _tj_rows:
            st.dataframe(pd.DataFrame(_tj_rows), use_container_width=True, hide_index=True)

        # ── Trade Notes / Annotations ──
        st.divider()
        st.markdown("### Trade Notes")
        st.caption("Attach notes to any trade. Click to expand and add or edit your annotation.")
        for _tn_trade in _tj_sorted:
            _tn_id = _tn_trade.get("id", "")
            _tn_asset = _tn_trade.get("asset", "?")
            _tn_pnl = _tn_trade.get("pnl", 0)
            _tn_closed = _tn_trade.get("closed_at", "")[:16].replace("T", " ")
            _tn_existing_note = _tn_trade.get("notes", "")
            _tn_has_note = bool(_tn_existing_note)
            _tn_note_icon = " [has note]" if _tn_has_note else ""
            _tn_label = f"{_tn_asset} | {_tn_closed} | P&L: ${_tn_pnl:+,.2f}{_tn_note_icon}"
            with st.expander(_tn_label, expanded=False):
                _tn_note_val = st.text_area(
                    "Note",
                    value=_tn_existing_note,
                    key=f"tn_note_{_tn_id}",
                    height=100,
                    placeholder="e.g. Entered on FOMC dip, strong RSI divergence signal...",
                    label_visibility="collapsed",
                )
                if st.button("Save Note", key=f"tn_save_{_tn_id}", use_container_width=True):
                    if paper_trader.save_trade_note(_tn_id, _tn_note_val):
                        st.success(f"Note saved for {_tn_asset} trade.")
                        st.rerun()
                    else:
                        st.error("Failed to save note -- trade not found.")

        # ── CSV Export ──
        if _tj_history:
            st.divider()
            _csv_data = pd.DataFrame([{
                "opened_at": t.get("opened_at", ""),
                "closed_at": t.get("closed_at", ""),
                "asset": t.get("asset", ""),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price", 0),
                "exit_price": t.get("exit_price", 0),
                "usd_amount": t.get("usd_amount", 0),
                "pnl": t.get("pnl", 0),
                "exit_reason": t.get("exit_reason", ""),
                "signal_hint": t.get("signal_hint", ""),
                "notes": t.get("notes", ""),
            } for t in _tj_history])
            _csv_bytes = _csv_data.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Export Trade History (CSV)",
                data=_csv_bytes,
                file_name="aegis_trade_history.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # ── Open Positions ──
        if _tj_open:
            st.divider()
            st.markdown("### Currently Open Positions")
            _tj_open_rows = []
            for pos in _tj_open:
                _tj_open_rows.append({
                    "Opened": pos.get("opened_at", "")[:16].replace("T", " "),
                    "Asset": pos.get("asset", ""),
                    "Dir": pos.get("direction", "").upper(),
                    "Entry": f"${pos.get('entry_price', 0):,.2f}",
                    "Size": f"${pos.get('usd_amount', 0):,.0f}",
                    "Stop Loss": f"${pos.get('stop_loss', 0):,.2f}" if pos.get("stop_loss") else "None",
                    "Take Profit": f"${pos.get('take_profit', 0):,.2f}" if pos.get("take_profit") else "None",
                    "Signal": pos.get("signal_hint", ""),
                })
            st.dataframe(pd.DataFrame(_tj_open_rows), use_container_width=True, hide_index=True)


# ===========================
# RISK DASHBOARD — Portfolio Risk Intelligence
# ===========================
elif view == "risk_dashboard":
    render_page_header("Risk Dashboard", view_key="risk_dashboard")
    render_page_info("risk_dashboard")

    _rd_watchlist = load_watchlist_summary()
    _rd_prices = fetch_live_prices(_rd_watchlist) if _rd_watchlist else {}
    _rd_portfolio = paper_trader._load()
    _rd_open = _rd_portfolio.get("open_positions", [])
    _rd_history = paper_trader.get_trade_history()
    _rd_summary = paper_trader.get_portfolio_summary(_rd_prices)
    _rd_curve = paper_trader.get_equity_curve()

    # ── Section 1: Position Sizing Recommendation ──
    st.markdown("## Smart Position Sizing")
    st.caption("Based on your trading history, here's how much to risk on your next trade.")

    _rd_sizing = risk_manager.suggest_position_size(
        capital=_rd_summary["equity"],
        entry_price=1.0,  # generic
        trade_history=_rd_history,
    )

    _sz1, _sz2, _sz3, _sz4 = st.columns(4)
    with _sz1:
        _sz_method_label = "Half-Kelly" if _rd_sizing["method"] == "half_kelly" else "Fixed Fractional"
        st.metric("Method", _sz_method_label)
    with _sz2:
        st.metric("Suggested Size", f"${_rd_sizing['suggested_usd']:,.2f}")
    with _sz3:
        st.metric("Risk Fraction", f"{_rd_sizing['fraction']*100:.1f}%")
    with _sz4:
        st.metric("Max Position", f"${_rd_sizing['max_usd']:,.2f}")

    # Kelly Criterion breakdown
    st.markdown(f"### {gtip('Kelly Criterion')} Breakdown", unsafe_allow_html=True)
    if _rd_history:
        _kw = [t for t in _rd_history if t.get("pnl", 0) > 0]
        _kl = [t for t in _rd_history if t.get("pnl", 0) < 0]
        if _kw and _kl:
            _k_wr = len(_kw) / (len(_kw) + len(_kl))
            _k_avgw = sum(t["pnl"] for t in _kw) / len(_kw)
            _k_avgl = abs(sum(t["pnl"] for t in _kl) / len(_kl))
            _full_kelly = risk_manager.kelly_criterion(_k_wr, _k_avgw, _k_avgl) * 2  # show full kelly (we use half)
            st.markdown(
                f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                f"border-radius:10px;padding:14px 18px;margin-top:8px;'>"
                f"<div style='color:#8b949e;font-size:0.75em;letter-spacing:0.1em;margin-bottom:8px;'>"
                f"KELLY CRITERION BREAKDOWN</div>"
                f"<div style='color:#c9d1d9;font-size:0.85em;line-height:1.8;'>"
                f"Win Rate: <span style='color:#3fb950;font-weight:600;'>{_k_wr*100:.1f}%</span> &middot; "
                f"Avg Win: <span style='color:#3fb950;font-weight:600;'>${_k_avgw:.2f}</span> &middot; "
                f"Avg Loss: <span style='color:#f85149;font-weight:600;'>${_k_avgl:.2f}</span><br>"
                f"Full Kelly: <span style='color:#d29922;font-weight:600;'>{_full_kelly*100:.1f}%</span> &middot; "
                f"Half Kelly (safer): <span style='color:#3fb950;font-weight:600;'>"
                f"{_rd_sizing['fraction']*100:.1f}%</span> = "
                f"<span style='color:#58a6ff;font-weight:700;'>${_rd_sizing['suggested_usd']:,.2f}</span> per trade"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Section 2: Portfolio Exposure ──
    st.markdown("## Portfolio Exposure")

    if _rd_open:
        _rd_exposure = risk_manager.portfolio_exposure(_rd_open, _rd_prices, _rd_summary["equity"])

        # Concentration warning
        if _rd_exposure.get("concentration_warning"):
            _lg = _rd_exposure.get("largest_position", {})
            st.markdown(
                f"<div style='background:rgba(253,126,20,0.08);border:1px solid #d29922;"
                f"border-radius:8px;padding:12px 18px;margin-bottom:16px;'>"
                f"<span style='color:#d29922;font-weight:700;'>⚠️ CONCENTRATION WARNING</span>"
                f"<span style='color:#c9d1d9;font-size:0.85em;margin-left:12px;'>"
                f"{_lg.get('name', '')} is {_lg.get('pct', 0):.1f}% of your portfolio. "
                f"Consider diversifying to reduce single-asset risk.</span></div>",
                unsafe_allow_html=True,
            )

        # Exposure metrics
        _re1, _re2, _re3 = st.columns(3)
        with _re1:
            _long_pct = _rd_exposure.get("by_direction", {}).get("long", 0)
            _short_pct = _rd_exposure.get("by_direction", {}).get("short", 0)
            st.metric("Long Exposure", f"{_long_pct:.1f}%")
            st.metric("Short Exposure", f"{_short_pct:.1f}%")
        with _re2:
            st.metric("Open Positions", len(_rd_open))
            _lg = _rd_exposure.get("largest_position", {})
            st.metric("Largest Position", f"{_lg.get('name', 'N/A')} ({_lg.get('pct', 0):.1f}%)")
        with _re3:
            # Asset class donut
            _ac = _rd_exposure.get("by_asset_class", {})
            if any(v > 0 for v in _ac.values()):
                st.markdown("**Asset Class Allocation**")
                _pie_fig = risk_manager.exposure_pie_chart(_ac, height=220)
                st.plotly_chart(_pie_fig, use_container_width=True)

        # Per-position table
        st.markdown("### Position Breakdown")
        _pos_rows = []
        _by_asset = _rd_exposure.get("by_asset", {})
        for _pa_name, _pa_data in sorted(_by_asset.items(), key=lambda x: x[1].get("pct", 0), reverse=True):
            _pos_rows.append({
                "Asset": _pa_name,
                "Direction": _pa_data.get("direction", "").upper(),
                "Value": f"${_pa_data.get('usd_value', 0):,.2f}",
                "% of Portfolio": f"{_pa_data.get('pct', 0):.1f}%",
            })
        if _pos_rows:
            st.dataframe(pd.DataFrame(_pos_rows), use_container_width=True, hide_index=True)
            _rd_asset_names = list(_by_asset.keys())
            _rd_link_cols = st.columns(min(len(_rd_asset_names), 6))
            for _ri, _ra in enumerate(_rd_asset_names):
                with _rd_link_cols[_ri % min(len(_rd_asset_names), 6)]:
                    asset_link_button(_ra, "rd")
    else:
        st.info("No open positions. Portfolio exposure analysis requires active trades.")

    st.divider()

    # ── Section 3: Interactive Correlation Matrix (90-day, all 12 assets) ──
    st.markdown("## Cross-Asset Correlation Matrix")
    st.caption("90-day Pearson correlation of daily returns across all 12 watchlist assets. "
               "Green = positive correlation, Red = negative correlation.")

    _corr_90d_prices = _fetch_correlation_data_90d()

    if len(_corr_90d_prices) >= 2:
        # Build correlation matrix from daily returns
        _corr_df = pd.DataFrame(_corr_90d_prices)
        _corr_returns = _corr_df.pct_change().dropna()
        _corr_matrix = _corr_returns.corr().round(3)
        _corr_labels = list(_corr_matrix.columns)
        _corr_z = _corr_matrix.values.tolist()

        # Build Plotly heatmap with text annotations
        _corr_text = []
        for _ci_row in range(len(_corr_labels)):
            _row_text = []
            for _ci_col in range(len(_corr_labels)):
                _row_text.append(str(round(_corr_z[_ci_row][_ci_col], 2)))
            _corr_text.append(_row_text)

        _corr_fig = go.Figure(
            data=go.Heatmap(
                z=_corr_z,
                x=_corr_labels,
                y=_corr_labels,
                text=_corr_text,
                texttemplate="%{text}",
                textfont=dict(size=11, color="#ffffff"),
                colorscale=[
                    [0.0, "#da3633"],
                    [0.25, "#f85149"],
                    [0.5, "#1a1e2e"],
                    [0.75, "#2ea043"],
                    [1.0, "#3fb950"],
                ],
                zmin=-1,
                zmax=1,
                colorbar=dict(
                    title=dict(text="Correlation", font=dict(size=11, color="#8b949e")),
                    tickvals=[-1, -0.5, 0, 0.5, 1],
                    ticktext=["-1.0", "-0.5", "0.0", "+0.5", "+1.0"],
                    tickfont=dict(color="#8b949e", size=10),
                    len=0.8,
                    thickness=12,
                    outlinewidth=0,
                    bgcolor="rgba(0,0,0,0)",
                ),
                hovertemplate="%{y} vs %{x}<br>Correlation: %{z:.3f}<extra></extra>",
            )
        )
        _corr_fig.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#c9d1d9", family="Inter, sans-serif"),
            height=520,
            xaxis=dict(
                side="bottom",
                tickfont=dict(size=11, color="#e6edf3"),
                tickangle=-45,
                gridcolor="rgba(48,54,61,0.3)",
            ),
            yaxis=dict(
                tickfont=dict(size=11, color="#e6edf3"),
                autorange="reversed",
                gridcolor="rgba(48,54,61,0.3)",
            ),
            margin=dict(l=90, r=50, t=20, b=80),
        )
        st.plotly_chart(_corr_fig, use_container_width=True, key="corr_heatmap_interactive")

        # ── Key Insights Box ──
        # Extract all unique pairs (upper triangle, excluding diagonal)
        _corr_pairs = []
        for _ci in range(len(_corr_labels)):
            for _cj in range(_ci + 1, len(_corr_labels)):
                _corr_pairs.append((_corr_labels[_ci], _corr_labels[_cj], _corr_z[_ci][_cj]))

        if _corr_pairs:
            # Sort for most positively correlated
            _sorted_pos = sorted(_corr_pairs, key=lambda x: x[2], reverse=True)
            # Sort for most negatively correlated
            _sorted_neg = sorted(_corr_pairs, key=lambda x: x[2])
            # Average correlation (absolute values of off-diagonal)
            _all_corr_vals = [abs(p[2]) for p in _corr_pairs]
            _avg_corr = sum(_all_corr_vals) / len(_all_corr_vals) if _all_corr_vals else 0

            # Build Top 3 Most Correlated HTML
            _top_pos_html = ""
            for _tp in _sorted_pos[:3]:
                _tp_color = "#3fb950" if _tp[2] > 0.5 else "#d29922" if _tp[2] > 0.3 else "#8b949e"
                _tp_a = _tp[0]
                _tp_b = _tp[1]
                _tp_v = _tp[2]
                _top_pos_html += (
                    "<div style='display:flex;justify-content:space-between;align-items:center;"
                    "padding:6px 0;border-bottom:1px solid rgba(48,54,61,0.3);'>"
                    "<span style='color:#e6edf3;font-size:0.88em;'>"
                    + _tp_a + " <span style='color:#6e7681;'>&harr;</span> " + _tp_b + "</span>"
                    "<span style='color:" + _tp_color + ";font-weight:700;font-family:JetBrains Mono,monospace;"
                    "font-size:0.9em;'>" + format(_tp_v, "+.3f") + "</span></div>"
                )

            # Build Top 3 Most Negatively Correlated HTML
            _top_neg_html = ""
            for _tn in _sorted_neg[:3]:
                _tn_color = "#f85149" if _tn[2] < -0.3 else "#d29922" if _tn[2] < -0.1 else "#8b949e"
                _tn_a = _tn[0]
                _tn_b = _tn[1]
                _tn_v = _tn[2]
                _top_neg_html += (
                    "<div style='display:flex;justify-content:space-between;align-items:center;"
                    "padding:6px 0;border-bottom:1px solid rgba(48,54,61,0.3);'>"
                    "<span style='color:#e6edf3;font-size:0.88em;'>"
                    + _tn_a + " <span style='color:#6e7681;'>&harr;</span> " + _tn_b + "</span>"
                    "<span style='color:" + _tn_color + ";font-weight:700;font-family:JetBrains Mono,monospace;"
                    "font-size:0.9em;'>" + format(_tn_v, "+.3f") + "</span></div>"
                )

            # Average correlation risk rating
            if _avg_corr > 0.6:
                _risk_label = "HIGH"
                _risk_color = "#f85149"
                _risk_msg = "Portfolio assets are highly correlated. Consider adding uncorrelated hedges."
            elif _avg_corr > 0.4:
                _risk_label = "MODERATE"
                _risk_color = "#d29922"
                _risk_msg = "Average diversification. Some asset pairs move together."
            else:
                _risk_label = "LOW"
                _risk_color = "#3fb950"
                _risk_msg = "Good diversification. Assets have relatively low average correlation."

            _insight_c1, _insight_c2, _insight_c3 = st.columns(3)
            with _insight_c1:
                st.markdown(
                    "<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    "border-radius:10px;padding:16px 18px;height:100%;'>"
                    "<div style='color:#3fb950;font-size:0.72em;letter-spacing:0.1em;"
                    "font-weight:700;margin-bottom:10px;'>TOP CORRELATED PAIRS</div>"
                    + _top_pos_html + "</div>",
                    unsafe_allow_html=True,
                )
            with _insight_c2:
                st.markdown(
                    "<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    "border-radius:10px;padding:16px 18px;height:100%;'>"
                    "<div style='color:#f85149;font-size:0.72em;letter-spacing:0.1em;"
                    "font-weight:700;margin-bottom:10px;'>TOP HEDGING PAIRS (Negative)</div>"
                    + _top_neg_html + "</div>",
                    unsafe_allow_html=True,
                )
            with _insight_c3:
                _avg_corr_str = format(_avg_corr, ".2f")
                st.markdown(
                    "<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    "border-radius:10px;padding:16px 18px;height:100%;'>"
                    "<div style='color:#58a6ff;font-size:0.72em;letter-spacing:0.1em;"
                    "font-weight:700;margin-bottom:10px;'>PORTFOLIO CORRELATION RISK</div>"
                    "<div style='text-align:center;margin:12px 0;'>"
                    "<span style='color:" + _risk_color + ";font-size:2.2em;font-weight:800;"
                    "font-family:JetBrains Mono,monospace;'>" + _avg_corr_str + "</span>"
                    "<div style='color:" + _risk_color + ";font-size:0.82em;font-weight:700;"
                    "margin-top:4px;'>" + _risk_label + " RISK</div></div>"
                    "<div style='color:#8b949e;font-size:0.78em;line-height:1.5;"
                    "margin-top:8px;'>" + _risk_msg + "</div></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("Fetching correlation data... If this persists, check your internet connection.")

    st.divider()

    # ── Section 4: Value at Risk ──
    st.markdown(f"## {gtip('VaR')} — Value at Risk", unsafe_allow_html=True)
    st.caption("Estimated worst-case daily loss at 95% confidence level.")

    if len(_rd_curve) >= 5:
        _rd_daily_returns = []
        _rd_starting = _rd_summary.get("starting_balance", 1000)
        for i in range(1, len(_rd_curve)):
            _prev = _rd_curve[i-1].get("equity", _rd_starting)
            _curr = _rd_curve[i].get("equity", _rd_starting)
            if _prev > 0:
                _rd_daily_returns.append((_curr - _prev) / _prev * 100)

        if len(_rd_daily_returns) >= 5:
            _var_95 = risk_manager.portfolio_var(_rd_daily_returns, 0.95)
            _var_99 = risk_manager.portfolio_var(_rd_daily_returns, 0.99)
            _var_95_usd = abs(_var_95) / 100 * _rd_summary["equity"]
            _var_99_usd = abs(_var_99) / 100 * _rd_summary["equity"]

            _vr1, _vr2, _vr3, _vr4 = st.columns(4)
            with _vr1:
                st.metric("VaR (95%)", f"{_var_95:+.2f}%")
            with _vr2:
                st.metric("VaR (95%) $", f"${_var_95_usd:,.2f}")
            with _vr3:
                st.metric("VaR (99%)", f"{_var_99:+.2f}%")
            with _vr4:
                st.metric("VaR (99%) $", f"${_var_99_usd:,.2f}")

            st.markdown(
                "<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                "border-radius:8px;padding:12px 18px;margin-top:8px;'>"
                "<div style='color:#8b949e;font-size:0.82em;line-height:1.6;'>"
                "<b>What is VaR?</b> Value at Risk estimates the maximum loss your portfolio "
                "might experience on a given day. A VaR(95%) of -2% means: "
                "on 95 out of 100 trading days, your loss should not exceed 2%. "
                "The remaining 5 days could be worse.</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Need more equity data points for VaR calculation. Keep trading!")
    else:
        st.info("Insufficient equity history for VaR analysis. The system needs at least 5 daily snapshots.")

    st.divider()

    # ── Section 5: Benchmark Comparison ──
    st.markdown("## Benchmark Comparison")
    st.caption("How does your portfolio perform versus buying and holding benchmarks?")

    _bench_returns = _fetch_benchmark_returns()
    _port_ret = _rd_summary.get("total_return_pct", 0)

    if _bench_returns:
        _bench_items = [{"name": k, "return": v} for k, v in _bench_returns.items()]
        _bc_cols = st.columns(len(_bench_items) + 1)
        with _bc_cols[0]:
            _port_c = "#3fb950" if _port_ret >= 0 else "#f85149"
            st.markdown(
                f"<div style='background:#161b22;border:2px solid {_port_c};"
                f"border-radius:10px;padding:16px;text-align:center;'>"
                f"<div style='color:#8b949e;font-size:0.72em;letter-spacing:0.1em;'>YOUR PORTFOLIO</div>"
                f"<div style='color:{_port_c};font-size:2em;font-weight:800;"
                f"font-family:JetBrains Mono,monospace;'>{_port_ret:+.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        for idx, _bi in enumerate(_bench_items):
            with _bc_cols[idx + 1]:
                _bi_c = "#3fb950" if _bi["return"] >= 0 else "#f85149"
                _beat = _port_ret > _bi["return"]
                _beat_icon = "✅" if _beat else "❌"
                st.markdown(
                    f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
                    f"border-radius:10px;padding:16px;text-align:center;'>"
                    f"<div style='color:#8b949e;font-size:0.72em;letter-spacing:0.1em;'>"
                    f"{_bi['name'].upper()} {_beat_icon}</div>"
                    f"<div style='color:{_bi_c};font-size:2em;font-weight:800;"
                    f"font-family:JetBrains Mono,monospace;'>{_bi['return']:+.2f}%</div></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("Benchmark data unavailable.")

    # ── Max Drawdown ──
    st.divider()
    _rd_dd = risk_manager.max_drawdown(_rd_curve)
    st.markdown("## Drawdown Analysis")
    _dd1, _dd2, _dd3, _dd4 = st.columns(4)
    with _dd1:
        st.metric("Max Drawdown", f"{_rd_dd['max_drawdown_pct']:.2f}%")
    with _dd2:
        st.metric("Max Drawdown ($)", f"${_rd_dd['max_drawdown_usd']:,.2f}")
    with _dd3:
        st.metric("Peak Equity", f"${_rd_dd['peak']:,.2f}")
    with _dd4:
        st.metric("Trough Equity", f"${_rd_dd['trough']:,.2f}")

    # Circuit breaker status
    _cb_active = risk_manager.check_circuit_breaker(_rd_curve)
    if _cb_active:
        st.markdown(
            "<div style='background:rgba(248,81,73,0.1);border:1px solid #f85149;"
            "border-radius:8px;padding:12px 18px;'>"
            "<span style='color:#f85149;font-weight:700;'>🚨 CIRCUIT BREAKER TRIGGERED</span>"
            "<span style='color:#c9d1d9;font-size:0.85em;margin-left:12px;'>"
            "Drawdown exceeds safety threshold. Auto-trading is paused until equity recovers.</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background:rgba(63,185,80,0.08);border:1px solid rgba(63,185,80,0.3);"
            "border-radius:8px;padding:12px 18px;'>"
            "<span style='color:#3fb950;font-weight:700;'>✅ CIRCUIT BREAKER: CLEAR</span>"
            "<span style='color:#8b949e;font-size:0.85em;margin-left:12px;'>"
            "Drawdown within acceptable limits. Auto-trading active.</span></div>",
            unsafe_allow_html=True,
        )


# ===========================
# WATCHLIST MANAGER — Multiple Named Watchlists
# ===========================
elif view == "watchlist_mgr":
    render_page_header("Watchlist Manager", view_key="watchlist_mgr")
    render_page_info("watchlist_mgr")

    _wm = WatchlistManager()
    _wm_lists = _wm.list_watchlists()
    _wm_active = _wm.get_active_name()

    # ── Active watchlist selector ──
    st.markdown("## Active Watchlist")
    _wm_sel_cols = st.columns([3, 1, 1])
    with _wm_sel_cols[0]:
        _wm_selected = st.selectbox(
            "Select watchlist",
            _wm_lists,
            index=_wm_lists.index(_wm_active) if _wm_active in _wm_lists else 0,
            key="wm_select",
        )
    with _wm_sel_cols[1]:
        if st.button("Activate", key="wm_activate", use_container_width=True):
            if _wm_selected and _wm_selected != _wm_active:
                _wm.set_active(_wm_selected)
                st.success(f"Switched to '{_wm_selected}'")
                st.rerun()
            elif _wm_selected == _wm_active:
                st.info("Already active.")
    with _wm_sel_cols[2]:
        if st.button("Delete", key="wm_delete", use_container_width=True):
            if _wm_selected and len(_wm_lists) > 1:
                _wm.delete_watchlist(_wm_selected)
                st.success(f"Deleted '{_wm_selected}'")
                st.rerun()
            else:
                st.warning("Cannot delete the only watchlist.")

    # Show active badge
    st.markdown(
        f"<div style='background:rgba(63,185,80,0.08);border:1px solid rgba(63,185,80,0.3);"
        f"border-radius:8px;padding:10px 16px;margin:8px 0 16px 0;'>"
        f"<span style='color:#3fb950;font-weight:700;'>Active:</span> "
        f"<span style='color:#e6edf3;font-family:JetBrains Mono,monospace;'>{_wm_active}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Show assets in selected watchlist ──
    _wm_data = _wm.load_watchlist(_wm_selected)
    if _wm_data:
        st.markdown(f"### Assets in **{_wm_selected}** ({len(_wm_data)} assets)")
        _wm_rows = ""
        for _wm_name, _wm_asset in _wm_data.items():
            _wm_cat = _wm_asset.get("category", "unknown")
            _wm_tick = _wm_asset.get("ticker", "")
            _wm_sup = _wm_asset.get("support", 0)
            _wm_tgt = _wm_asset.get("target", 0)
            _wm_bias = _wm_asset.get("macro_bias", "neutral")
            _wm_bias_c = "#3fb950" if _wm_bias == "bullish" else "#f85149" if _wm_bias == "bearish" else "#6e7681"
            _wm_cat_colors = {"commodity": "#d29922", "crypto": "#a371f7", "index": "#58a6ff", "forex": "#3fb950"}
            _wm_cc = _wm_cat_colors.get(_wm_cat, "#6e7681")
            _wm_cc_hex = _wm_cc.lstrip("#")
            _wm_cc_rgb = f"{int(_wm_cc_hex[0:2],16)},{int(_wm_cc_hex[2:4],16)},{int(_wm_cc_hex[4:6],16)}"
            _wm_rows += (
                f"<tr style='border-bottom:1px solid rgba(48,54,61,0.3);'>"
                f"<td style='padding:8px 12px;color:#e6edf3;font-weight:600;'>{_wm_name}</td>"
                f"<td style='padding:8px 12px;color:#8b949e;font-family:JetBrains Mono,monospace;font-size:0.85em;'>{_wm_tick}</td>"
                f"<td style='padding:8px 12px;'><span style='background:rgba({_wm_cc_rgb},0.15);"
                f"color:{_wm_cc};padding:2px 8px;border-radius:10px;font-size:0.75em;'>{_wm_cat}</span></td>"
                f"<td style='padding:8px 12px;color:#3fb950;font-family:JetBrains Mono,monospace;font-size:0.85em;'>${_wm_tgt:,.2f}</td>"
                f"<td style='padding:8px 12px;color:#f85149;font-family:JetBrains Mono,monospace;font-size:0.85em;'>${_wm_sup:,.2f}</td>"
                f"<td style='padding:8px 12px;color:{_wm_bias_c};font-size:0.85em;font-weight:600;'>{_wm_bias.upper()}</td>"
                f"</tr>"
            )
        st.markdown(
            f"<div style='overflow-x:auto;'>"
            f"<table style='width:100%;border-collapse:collapse;background:#161b22;border-radius:10px;overflow:hidden;'>"
            f"<thead><tr style='background:#0d1117;border-bottom:2px solid rgba(48,54,61,0.5);'>"
            f"<th style='padding:10px 12px;color:#8b949e;font-size:0.75em;letter-spacing:0.08em;text-align:left;'>ASSET</th>"
            f"<th style='padding:10px 12px;color:#8b949e;font-size:0.75em;letter-spacing:0.08em;text-align:left;'>TICKER</th>"
            f"<th style='padding:10px 12px;color:#8b949e;font-size:0.75em;letter-spacing:0.08em;text-align:left;'>CATEGORY</th>"
            f"<th style='padding:10px 12px;color:#8b949e;font-size:0.75em;letter-spacing:0.08em;text-align:left;'>TARGET</th>"
            f"<th style='padding:10px 12px;color:#8b949e;font-size:0.75em;letter-spacing:0.08em;text-align:left;'>SUPPORT</th>"
            f"<th style='padding:10px 12px;color:#8b949e;font-size:0.75em;letter-spacing:0.08em;text-align:left;'>BIAS</th>"
            f"</tr></thead><tbody>{_wm_rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )

        # Remove asset
        st.markdown("#### Remove Asset")
        _wm_rm_cols = st.columns([3, 1])
        with _wm_rm_cols[0]:
            _wm_rm_asset = st.selectbox("Select asset to remove", list(_wm_data.keys()), key="wm_rm_asset")
        with _wm_rm_cols[1]:
            if st.button("Remove", key="wm_rm_btn", use_container_width=True):
                if _wm_rm_asset:
                    _wm.remove_asset(_wm_rm_asset, _wm_selected)
                    st.success(f"Removed {_wm_rm_asset} from {_wm_selected}")
                    st.rerun()
    else:
        st.info("This watchlist is empty.")

    st.divider()

    # ── Create new watchlist ──
    st.markdown("## Create New Watchlist")
    _wm_cr_tabs = st.tabs(["From Scratch", "From Preset", "Duplicate Existing"])

    with _wm_cr_tabs[0]:
        _wm_new_name = st.text_input("Watchlist name", key="wm_new_name", placeholder="e.g. My Metals")
        if st.button("Create Empty", key="wm_create_empty", use_container_width=True):
            if _wm_new_name and _wm_new_name.strip():
                ok = _wm.create_watchlist(_wm_new_name.strip())
                if ok:
                    st.success(f"Created '{_wm_new_name.strip()}'")
                    st.rerun()
                else:
                    st.warning("A watchlist with that name already exists.")
            else:
                st.warning("Enter a name first.")

    with _wm_cr_tabs[1]:
        _wm_presets = _wm.get_presets()
        _wm_preset_name = st.selectbox("Choose preset", list(_wm_presets.keys()), key="wm_preset_sel")
        if _wm_preset_name:
            _wm_preset_assets = _wm_presets[_wm_preset_name]
            st.caption(f"Includes: {', '.join(_wm_preset_assets)}")
        _wm_preset_custom_name = st.text_input("Save as (leave blank = preset name)", key="wm_preset_name")
        if st.button("Create from Preset", key="wm_create_preset", use_container_width=True):
            _save_name = _wm_preset_custom_name.strip() if _wm_preset_custom_name.strip() else _wm_preset_name
            ok = _wm.create_from_preset(_wm_preset_name, _save_name)
            if ok:
                st.success(f"Created '{_save_name}' from {_wm_preset_name} preset")
                st.rerun()
            else:
                st.warning("Watchlist already exists or preset not found.")

    with _wm_cr_tabs[2]:
        _wm_dup_src = st.selectbox("Source watchlist", _wm_lists, key="wm_dup_src")
        _wm_dup_name = st.text_input("New name", key="wm_dup_name", placeholder="e.g. Copy of Default")
        if st.button("Duplicate", key="wm_dup_btn", use_container_width=True):
            if _wm_dup_name and _wm_dup_name.strip() and _wm_dup_src:
                ok = _wm.duplicate_watchlist(_wm_dup_src, _wm_dup_name.strip())
                if ok:
                    st.success(f"Duplicated '{_wm_dup_src}' to '{_wm_dup_name.strip()}'")
                    st.rerun()
                else:
                    st.warning("Target name already exists or source is empty.")
            else:
                st.warning("Enter a name for the duplicate.")

    st.divider()

    # ── Add asset to selected watchlist ──
    st.markdown(f"## Add Asset to **{_wm_selected}**")
    _wm_add_cols = st.columns(3)
    with _wm_add_cols[0]:
        _wm_add_name = st.text_input("Asset name", key="wm_add_name", placeholder="e.g. Tesla")
    with _wm_add_cols[1]:
        _wm_add_ticker = st.text_input("Yahoo ticker", key="wm_add_ticker", placeholder="e.g. TSLA")
    with _wm_add_cols[2]:
        _wm_add_cat = st.selectbox("Category", ["commodity", "crypto", "index", "forex", "stock", "etf"], key="wm_add_cat")

    _wm_add_cols2 = st.columns(4)
    with _wm_add_cols2[0]:
        _wm_add_support = st.number_input("Support", min_value=0.0, value=0.0, key="wm_add_sup")
    with _wm_add_cols2[1]:
        _wm_add_target = st.number_input("Target", min_value=0.0, value=0.0, key="wm_add_tgt")
    with _wm_add_cols2[2]:
        _wm_add_stop = st.number_input("Stop %", min_value=0.01, max_value=0.50, value=0.05, step=0.01, key="wm_add_stop")
    with _wm_add_cols2[3]:
        _wm_add_bias = st.selectbox("Macro bias", ["neutral", "bullish", "bearish"], key="wm_add_bias")

    if st.button("Add Asset", key="wm_add_btn", use_container_width=True):
        if _wm_add_name.strip() and _wm_add_ticker.strip():
            _wm.add_asset(
                _wm_add_name.strip(),
                {
                    "ticker": _wm_add_ticker.strip(),
                    "support": _wm_add_support,
                    "target": _wm_add_target,
                    "stop_pct": _wm_add_stop,
                    "macro_bias": _wm_add_bias,
                    "category": _wm_add_cat,
                    "enabled": True,
                },
                _wm_selected,
            )
            st.success(f"Added {_wm_add_name.strip()} to {_wm_selected}")
            st.rerun()
        else:
            st.warning("Asset name and ticker are required.")


# ===========================
# PORTFOLIO OPTIMIZER — Efficient Frontier + Allocation
# ===========================
elif view == "optimizer":
    render_page_header("Portfolio Optimizer", view_key="optimizer")
    render_page_info("optimizer")

    st.markdown(
        "<div style='color:#8b949e;font-size:0.85em;margin-top:-10px;margin-bottom:16px;'>"
        "Mean-variance optimization across your watchlist assets. Uses historical data to find optimal allocation.</div>",
        unsafe_allow_html=True,
    )

    _opt_period = st.selectbox("Historical Period", ["3mo", "6mo", "1y", "2y"], index=1, key="opt_period")

    if st.button("Run Optimization", key="opt_run", use_container_width=True):
        with st.spinner("Fetching historical returns and running optimization..."):
            try:
                _opt_result = portfolio_optimizer.optimize_from_watchlist(period=_opt_period)
                if _opt_result:
                    st.session_state["opt_result"] = _opt_result
                    st.success("Optimization complete!")
                else:
                    st.error("Optimization failed. Could not fetch enough data. Try again or check internet connection.")
            except Exception as _opt_err:
                st.error(f"Optimization error: {_opt_err}")

    _opt_result = st.session_state.get("opt_result")
    if _opt_result:
        _opt_ms = _opt_result["max_sharpe"]
        _opt_mv = _opt_result["min_variance"]
        _opt_ew = _opt_result["equal_weight"]
        _opt_kl = _opt_result["half_kelly"]

        # ── Strategy comparison cards ──
        st.markdown("## Strategy Comparison")
        _opt_strat_cols = st.columns(4)
        _opt_strategies = [
            ("Max Sharpe", _opt_ms, "#3fb950", "star"),
            ("Min Variance", _opt_mv, "#d29922", "shield"),
            ("Equal Weight", _opt_ew, "#6e7681", "balance"),
            ("Half-Kelly", _opt_kl, "#a371f7", "target"),
        ]
        _opt_icons = {"star": "\u2b50", "shield": "\U0001f6e1\ufe0f", "balance": "\u2696\ufe0f", "target": "\U0001f3af"}
        for _oc_idx, (_oc_name, _oc_data, _oc_color, _oc_icon_key) in enumerate(_opt_strategies):
            with _opt_strat_cols[_oc_idx]:
                _oc_ret = _oc_data["annual_return"]
                _oc_vol = _oc_data["annual_volatility"]
                _oc_sh = _oc_data["sharpe_ratio"]
                _oc_ret_c = "#3fb950" if _oc_ret >= 0 else "#f85149"
                _oc_icon = _opt_icons.get(_oc_icon_key, "")
                st.markdown(
                    f"<div style='background:#161b22;border:2px solid {_oc_color};"
                    f"border-radius:10px;padding:16px;text-align:center;'>"
                    f"<div style='font-size:1.5em;margin-bottom:4px;'>{_oc_icon}</div>"
                    f"<div style='color:{_oc_color};font-size:0.78em;font-weight:700;"
                    f"letter-spacing:0.08em;margin-bottom:8px;'>{_oc_name.upper()}</div>"
                    f"<div style='color:{_oc_ret_c};font-family:JetBrains Mono,monospace;"
                    f"font-size:1.5em;font-weight:800;'>{_oc_ret:+.1f}%</div>"
                    f"<div style='color:#8b949e;font-size:0.78em;margin-top:4px;'>Annual Return</div>"
                    f"<div style='display:flex;justify-content:space-around;margin-top:10px;'>"
                    f"<div><span style='color:#e6edf3;font-weight:700;'>{_oc_vol:.1f}%</span>"
                    f"<div style='color:#8b949e;font-size:0.7em;'>Volatility</div></div>"
                    f"<div><span style='color:#e6edf3;font-weight:700;'>{_oc_sh:.3f}</span>"
                    f"<div style='color:#8b949e;font-size:0.7em;'>Sharpe</div></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

        st.divider()

        # ── Efficient Frontier Chart ──
        st.markdown("## Efficient Frontier")
        _opt_frontier = _opt_result.get("frontier", [])
        _opt_portfolios = {
            "Max Sharpe": _opt_ms,
            "Min Variance": _opt_mv,
            "Equal Weight": _opt_ew,
            "Half-Kelly": _opt_kl,
        }
        try:
            _opt_ef_chart = portfolio_optimizer.efficient_frontier_chart(
                _opt_frontier, _opt_portfolios, height=500
            )
            st.plotly_chart(_opt_ef_chart, use_container_width=True)
        except Exception as _ef_err:
            st.error(f"Chart error: {_ef_err}")

        st.divider()

        # ── Allocation comparison ──
        st.markdown("## Optimal Allocations")
        _opt_alloc_tabs = st.tabs(["Max Sharpe", "Min Variance", "Half-Kelly", "Equal Weight"])
        _opt_alloc_list = [_opt_ms, _opt_mv, _opt_kl, _opt_ew]
        _opt_alloc_names = ["Max Sharpe", "Min Variance", "Half-Kelly", "Equal Weight"]

        for _oa_idx, _oa_tab in enumerate(_opt_alloc_tabs):
            with _oa_tab:
                _oa_data = _opt_alloc_list[_oa_idx]
                _oa_alloc = _oa_data.get("allocations", {})
                if _oa_alloc:
                    _oa_c1, _oa_c2 = st.columns([2, 1])
                    with _oa_c1:
                        try:
                            _oa_bar = portfolio_optimizer.allocation_bar_chart(
                                _oa_alloc, title=f"{_opt_alloc_names[_oa_idx]} Allocation", height=350
                            )
                            st.plotly_chart(_oa_bar, use_container_width=True)
                        except Exception:
                            st.info("Chart unavailable.")
                    with _oa_c2:
                        try:
                            _oa_pie = portfolio_optimizer.allocation_pie_chart(
                                _oa_alloc, title="Breakdown", height=350
                            )
                            st.plotly_chart(_oa_pie, use_container_width=True)
                        except Exception:
                            st.info("Chart unavailable.")

                    # Allocation table
                    _oa_sorted = sorted(_oa_alloc.items(), key=lambda x: x[1], reverse=True)
                    _oa_rows_html = ""
                    for _oa_aname, _oa_pct in _oa_sorted:
                        _oa_bar_w = min(_oa_pct, 100)
                        _oa_rows_html += (
                            f"<tr style='border-bottom:1px solid rgba(48,54,61,0.3);'>"
                            f"<td style='padding:6px 12px;color:#e6edf3;font-weight:600;'>{_oa_aname}</td>"
                            f"<td style='padding:6px 12px;width:50%;'>"
                            f"<div style='background:rgba(88,166,255,0.1);border-radius:4px;height:20px;width:100%;'>"
                            f"<div style='background:#58a6ff;border-radius:4px;height:100%;width:{_oa_bar_w}%;'></div>"
                            f"</div></td>"
                            f"<td style='padding:6px 12px;color:#e6edf3;font-family:JetBrains Mono,monospace;"
                            f"text-align:right;'>{_oa_pct:.1f}%</td></tr>"
                        )
                    st.markdown(
                        f"<table style='width:100%;border-collapse:collapse;background:#161b22;"
                        f"border-radius:8px;overflow:hidden;margin-top:10px;'>"
                        f"<thead><tr style='background:#0d1117;'>"
                        f"<th style='padding:8px 12px;color:#8b949e;font-size:0.72em;text-align:left;'>ASSET</th>"
                        f"<th style='padding:8px 12px;color:#8b949e;font-size:0.72em;text-align:left;'>WEIGHT</th>"
                        f"<th style='padding:8px 12px;color:#8b949e;font-size:0.72em;text-align:right;'>%</th>"
                        f"</tr></thead><tbody>{_oa_rows_html}</tbody></table>",
                        unsafe_allow_html=True,
                    )
                    # Asset links for allocated assets
                    _oa_link_names = [n for n, p in _oa_sorted if p > 0]
                    if _oa_link_names:
                        _oa_lc = st.columns(min(len(_oa_link_names), 6))
                        for _oli, _oln in enumerate(_oa_link_names):
                            with _oa_lc[_oli % min(len(_oa_link_names), 6)]:
                                asset_link_button(_oln, f"opt_{_oa_idx}")
                else:
                    st.info("No allocation data for this strategy.")

        # ── Timestamp ──
        _opt_ts = _opt_result.get("timestamp", "")[:19].replace("T", " ")
        _opt_assets_str = ", ".join(_opt_result.get("asset_names", []))
        st.caption(f"Optimization run at {_opt_ts} UTC | Assets: {_opt_assets_str}")
    else:
        st.markdown(
            "<div style='background:#161b22;border:1px dashed rgba(88,166,255,0.3);"
            "border-radius:12px;padding:40px;text-align:center;margin-top:20px;'>"
            "<div style='font-size:2.5em;margin-bottom:12px;'>&#9878;&#65039;</div>"
            "<div style='color:#e6edf3;font-size:1.1em;font-weight:600;margin-bottom:8px;'>"
            "Click <b>Run Optimization</b> to analyze your watchlist</div>"
            "<div style='color:#8b949e;font-size:0.85em;'>"
            "The optimizer will fetch historical price data and compute the optimal allocation "
            "using Max Sharpe, Min Variance, Equal Weight, and Half-Kelly strategies.</div>"
            "</div>",
            unsafe_allow_html=True,
        )


# ===========================
# SETTINGS — Terminal Configuration
# ===========================
elif view == "settings":
    render_page_header("Settings", view_key="settings")
    render_page_info("settings")

    SETTINGS_FILE = PROJECT_ROOT / "src" / "data" / "settings_override.json"

    def _load_settings() -> dict:
        defaults = {
            "confidence_weight_technical": SignalConfig.CONFIDENCE_WEIGHT_TECHNICAL,
            "confidence_weight_news": SignalConfig.CONFIDENCE_WEIGHT_NEWS,
            "confidence_weight_historical": SignalConfig.CONFIDENCE_WEIGHT_HISTORICAL,
            "max_position_pct": RiskConfig.MAX_POSITION_PCT * 100,
            "max_drawdown_pct": RiskConfig.MAX_DRAWDOWN_PCT * 100,
            "default_stop_loss_pct": RiskConfig.DEFAULT_STOP_LOSS_PCT,
            "default_take_profit_pct": RiskConfig.DEFAULT_TAKE_PROFIT_PCT,
            "auto_enabled": AutoTradeConfig.ENABLED,
            "auto_min_confidence": AutoTradeConfig.MIN_CONFIDENCE_PCT,
            "auto_max_positions": AutoTradeConfig.MAX_CONCURRENT_POSITIONS,
            "auto_cooldown_hours": AutoTradeConfig.COOLDOWN_HOURS,
            "auto_min_rr": AutoTradeConfig.MIN_RISK_REWARD,
            "live_refresh_s": DashboardConfig.LIVE_REFRESH_MS // 1000,
            "slow_refresh_s": DashboardConfig.SLOW_REFRESH_MS // 1000,
        }
        if SETTINGS_FILE.exists():
            try:
                overrides = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                defaults.update(overrides)
            except Exception:
                pass
        return defaults

    _settings = _load_settings()

    # ── Section 1: Signal Weights ──
    st.markdown("## Signal Confidence Weights")
    st.caption("How much each factor contributes to the overall confidence score. Should sum to 1.0.")
    _sw1, _sw2, _sw3 = st.columns(3)
    with _sw1:
        _w_tech = st.slider("Technical", 0.0, 1.0, float(_settings["confidence_weight_technical"]), 0.05, key="s_w_tech")
    with _sw2:
        _w_news = st.slider("News", 0.0, 1.0, float(_settings["confidence_weight_news"]), 0.05, key="s_w_news")
    with _sw3:
        _w_hist = st.slider("Historical", 0.0, 1.0, float(_settings["confidence_weight_historical"]), 0.05, key="s_w_hist")
    _w_sum = _w_tech + _w_news + _w_hist
    if abs(_w_sum - 1.0) > 0.01:
        st.warning(f"Weights sum to {_w_sum:.2f} — they should sum to 1.00 for balanced scoring.")
    else:
        st.success(f"Weights sum to {_w_sum:.2f}")

    st.divider()

    # ── Section 2: Risk Thresholds ──
    st.markdown("## Risk Thresholds")
    _rk1, _rk2, _rk3, _rk4 = st.columns(4)
    with _rk1:
        _r_max_pos = st.number_input("Max Position %", 1.0, 100.0, float(_settings["max_position_pct"]), 1.0, key="s_max_pos")
    with _rk2:
        _r_max_dd = st.number_input("Max Drawdown %", 1.0, 50.0, float(_settings["max_drawdown_pct"]), 1.0, key="s_max_dd")
    with _rk3:
        _r_sl = st.number_input("Default Stop-Loss %", 0.5, 20.0, float(_settings["default_stop_loss_pct"]), 0.5, key="s_sl")
    with _rk4:
        _r_tp = st.number_input("Default Take-Profit %", 1.0, 50.0, float(_settings["default_take_profit_pct"]), 1.0, key="s_tp")

    st.divider()

    # ── Section 3: Auto-Trader Gates ──
    st.markdown("## Auto-Trader Gates")
    _at_enabled = st.checkbox("Enable Auto-Trading", bool(_settings["auto_enabled"]), key="s_at_en")
    _at1, _at2, _at3, _at4 = st.columns(4)
    with _at1:
        _at_conf = st.number_input("Min Confidence %", 30.0, 100.0, float(_settings["auto_min_confidence"]), 5.0, key="s_at_conf")
    with _at2:
        _at_max = st.number_input("Max Positions", 1, 20, int(_settings["auto_max_positions"]), 1, key="s_at_max")
    with _at3:
        _at_cool = st.number_input("Cooldown Hours", 1, 48, int(_settings["auto_cooldown_hours"]), 1, key="s_at_cool")
    with _at4:
        _at_rr = st.number_input("Min Risk/Reward", 0.5, 5.0, float(_settings["auto_min_rr"]), 0.5, key="s_at_rr")

    st.divider()

    # ── Section 3b: Intelligence Toggles ──
    st.markdown("## Intelligence Modules")
    st.caption("Toggle the AI intelligence layers that influence auto-trading decisions.")
    _it1, _it2, _it3, _it4 = st.columns(4)
    with _it1:
        _s_regime = st.checkbox("Macro Regime Awareness", bool(_settings.get("use_regime_awareness", True)), key="s_regime")
    with _it2:
        _s_geo = st.checkbox("Geopolitical Risk Overlay", bool(_settings.get("use_geo_risk_overlay", True)), key="s_geo")
    with _it3:
        _s_dynconf = st.checkbox("Dynamic Confidence (per-asset learning)", bool(_settings.get("use_dynamic_confidence", True)), key="s_dynconf")
    with _it4:
        _s_lessons = st.checkbox("Lesson-Based Trade Filter", bool(_settings.get("use_lessons_filter", True)), key="s_lessons")

    _it5, _it6, _it7 = st.columns(3)
    with _it5:
        _s_trailing = st.number_input("Default Trailing Stop %", 0.5, 15.0, float(_settings.get("default_trailing_stop_pct", 3.0)), 0.5, key="s_trailing")
    with _it6:
        _s_dd_reduce = st.number_input("Drawdown Reduce Size %", -30.0, -1.0, float(_settings.get("drawdown_reduced_pct", -10.0)), 1.0, key="s_dd_reduce")
    with _it7:
        _s_dd_pause = st.number_input("Drawdown Full Pause %", -50.0, -5.0, float(_settings.get("drawdown_pause_pct", -15.0)), 1.0, key="s_dd_pause")

    st.divider()

    # ── Section 3c: Technical Indicator Params ──
    st.markdown("## Technical Indicators")
    st.caption("Tune the indicator periods used by the market scanner.")
    _tp1, _tp2, _tp3, _tp4 = st.columns(4)
    with _tp1:
        _s_sma_short = st.number_input("SMA Short", 5, 100, int(_settings.get("sma_short", TechnicalParams.SMA_SHORT)), 5, key="s_sma_s")
    with _tp2:
        _s_sma_long = st.number_input("SMA Long", 50, 500, int(_settings.get("sma_long", TechnicalParams.SMA_LONG)), 10, key="s_sma_l")
    with _tp3:
        _s_rsi_period = st.number_input("RSI Period", 5, 30, int(_settings.get("rsi_period", TechnicalParams.RSI_PERIOD)), 1, key="s_rsi_p")
    with _tp4:
        _s_bb_std = st.number_input("Bollinger Std Dev", 1.0, 4.0, float(_settings.get("bb_std", TechnicalParams.BB_STD)), 0.5, key="s_bb_std")
    _tp5, _tp6, _tp7, _tp8 = st.columns(4)
    with _tp5:
        _s_rsi_os = st.number_input("RSI Oversold", 10, 40, int(_settings.get("rsi_oversold", TechnicalParams.RSI_OVERSOLD)), 5, key="s_rsi_os")
    with _tp6:
        _s_rsi_ob = st.number_input("RSI Overbought", 60, 95, int(_settings.get("rsi_overbought", TechnicalParams.RSI_OVERBOUGHT)), 5, key="s_rsi_ob")
    with _tp7:
        _s_risk_free = st.number_input("Risk-Free Rate", 0.0, 0.15, float(_settings.get("risk_free_rate", 0.04)), 0.01, format="%.2f", key="s_rfr")
    with _tp8:
        _s_pos_method = st.selectbox("Position Size Method", ["fixed_fractional", "kelly"], index=0 if _settings.get("position_size_method", "fixed_fractional") == "fixed_fractional" else 1, key="s_pos_m")

    st.divider()

    # ── Section 4: Refresh Intervals ──
    st.markdown("## Dashboard Refresh")
    _rf1, _rf2 = st.columns(2)
    _live_opts = [5, 10, 15, 30, 60]
    _slow_opts = [15, 30, 60, 120]
    with _rf1:
        _cur_live = int(_settings.get("live_refresh_s", 10))
        _live_idx = _live_opts.index(_cur_live) if _cur_live in _live_opts else 1
        _rf_live = st.selectbox("Trading Views (seconds)", _live_opts, index=_live_idx, key="s_rf_live")
    with _rf2:
        _cur_slow = int(_settings.get("slow_refresh_s", 30))
        _slow_idx = _slow_opts.index(_cur_slow) if _cur_slow in _slow_opts else 1
        _rf_slow = st.selectbox("Analytics Views (seconds)", _slow_opts, index=_slow_idx, key="s_rf_slow")

    st.divider()

    # ── Save / Reset ──
    _save_col, _reset_col = st.columns(2)
    with _save_col:
        if st.button("Save Settings", type="primary", use_container_width=True, key="save_settings"):
            new_settings = {
                "confidence_weight_technical": _w_tech,
                "confidence_weight_news": _w_news,
                "confidence_weight_historical": _w_hist,
                "max_position_pct": _r_max_pos,
                "max_drawdown_pct": _r_max_dd,
                "default_stop_loss_pct": _r_sl,
                "default_take_profit_pct": _r_tp,
                "auto_enabled": _at_enabled,
                "auto_min_confidence": _at_conf,
                "auto_max_positions": _at_max,
                "auto_cooldown_hours": _at_cool,
                "auto_min_rr": _at_rr,
                "use_regime_awareness": _s_regime,
                "use_geo_risk_overlay": _s_geo,
                "use_dynamic_confidence": _s_dynconf,
                "use_lessons_filter": _s_lessons,
                "default_trailing_stop_pct": _s_trailing,
                "drawdown_reduced_pct": _s_dd_reduce,
                "drawdown_pause_pct": _s_dd_pause,
                "sma_short": _s_sma_short,
                "sma_long": _s_sma_long,
                "rsi_period": _s_rsi_period,
                "rsi_oversold": _s_rsi_os,
                "rsi_overbought": _s_rsi_ob,
                "bb_std": _s_bb_std,
                "risk_free_rate": _s_risk_free,
                "position_size_method": _s_pos_method,
                "live_refresh_s": _rf_live,
                "slow_refresh_s": _rf_slow,
            }
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps(new_settings, indent=2), encoding="utf-8")
            st.success("Settings saved! Changes take effect on next page refresh.")
            st.rerun()
    with _reset_col:
        if st.button("Reset to Defaults", use_container_width=True, key="reset_settings"):
            if SETTINGS_FILE.exists():
                SETTINGS_FILE.unlink()
            st.success("Settings reset to defaults.")
            st.rerun()

    # Current values summary
    st.divider()
    st.markdown("### Current Configuration")
    st.markdown(
        f"<div style='background:#161b22;border:1px solid rgba(48,54,61,0.5);"
        f"border-radius:10px;padding:16px 20px;font-family:JetBrains Mono,monospace;"
        f"font-size:0.8em;color:#8b949e;'>"
        f"Signal Weights: Tech {_w_tech:.0%} + News {_w_news:.0%} + History {_w_hist:.0%}<br>"
        f"Risk: Max Position {_r_max_pos:.0f}% | Max Drawdown {_r_max_dd:.0f}% | SL {_r_sl:.1f}% | TP {_r_tp:.1f}%<br>"
        f"Auto-Trader: {'ON' if _at_enabled else 'OFF'} | Min Conf {_at_conf:.0f}% | Max {_at_max} pos | "
        f"Cooldown {_at_cool}h | Min R:R {_at_rr:.1f}<br>"
        f"Intelligence: Regime {'ON' if _s_regime else 'OFF'} | Geo {'ON' if _s_geo else 'OFF'} | "
        f"Dynamic {'ON' if _s_dynconf else 'OFF'} | Lessons {'ON' if _s_lessons else 'OFF'}<br>"
        f"Indicators: SMA {_s_sma_short}/{_s_sma_long} | RSI-{_s_rsi_period} ({_s_rsi_os}/{_s_rsi_ob}) | "
        f"BB std={_s_bb_std} | Sizing: {_s_pos_method}<br>"
        f"Refresh: Trading {_rf_live}s | Analytics {_rf_slow}s"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Fallback: unknown view — graceful recovery
# ---------------------------------------------------------------------------
else:
    st.warning(f"Unknown view: **{view}**. Redirecting to Daily Advisor.")
    st.session_state["view"] = "advisor"
    st.rerun()


# ---------------------------------------------------------------------------
# GLOBAL FOOTER — Legal disclaimer on every page
# ---------------------------------------------------------------------------
st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
st.markdown(
    f"<div style='border-top:1px solid rgba(48,54,61,0.4);padding:12px 0 4px 0;"
    f"text-align:center;'>"
    f"<span style='color:#8b949e;font-size:0.65em;font-family:Inter,sans-serif;'>"
    f"{DISCLAIMER_SHORT}</span><br>"
    f"<span style='color:#30363d;font-size:0.58em;font-family:Inter,sans-serif;'>"
    f"Project Aegis v7.0 | Not registered as investment adviser | "
    f"Publisher&#39;s exclusion, Investment Advisers Act 1940</span>"
    f"</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Auto-refresh handled by st_autorefresh at top of page — no sleep needed
# ---------------------------------------------------------------------------
