"""Project Aegis — Central Configuration Module.

All configurable parameters in one place. Import this module
instead of hardcoding values across the codebase.

Settings override: The dashboard Settings page writes user preferences to
settings_override.json. Call apply_settings_override() to load those values
into the config classes at runtime. Backend engines (auto_trader, market_scanner)
call this on initialization so user settings actually take effect.
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
MEMORY_DIR = PROJECT_ROOT / "memory"
RESEARCH_DIR = PROJECT_ROOT / "research_outputs"
DOCS_DIR = PROJECT_ROOT / "docs"

# Data files
KANBAN_PATH = PROJECT_ROOT / "kanban_board.json"
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
USAGE_FILE = PROJECT_ROOT / "token_usage.json"
CHART_DIR = DATA_DIR / "charts"
NEWS_DIR = DATA_DIR
WATCHLIST_FILE = DATA_DIR / "watchlist_summary.json"
PREDICTIONS_FILE = MEMORY_DIR / "market_predictions.json"
MARKET_LESSONS_FILE = MEMORY_DIR / "market_lessons.json"
HINDSIGHT_FILE = MEMORY_DIR / "hindsight_simulations.json"
PAPER_PORTFOLIO_FILE = MEMORY_DIR / "paper_portfolio.json"
ERROR_LESSONS_FILE = MEMORY_DIR / "error_lessons.json"
REFLECTIONS_FILE = MEMORY_DIR / "daily_reflections.json"
MONITOR_STATUS_FILE = DATA_DIR / "monitor_status.json"
AUTO_PID_FILE = DATA_DIR / "autonomous_loop.pid"
BRAIN_REPORT_FILE = DATA_DIR / "brain_cycle_report.json"

# ---------------------------------------------------------------------------
# Watchlist & Assets
# ---------------------------------------------------------------------------
CORE_WATCHLIST = {
    "Gold": {"ticker": "GC=F", "support": 4405, "target": 5400, "category": "commodity"},
    "BTC": {"ticker": "BTC-USD", "support": 62000, "target": 95000, "category": "crypto"},
    "ETH": {"ticker": "ETH-USD", "support": 2200, "target": 4500, "category": "crypto"},
    "Silver": {"ticker": "SI=F", "support": 62, "target": 95, "category": "commodity"},
}

DISCOVERY_ASSETS = {
    "Oil": {"ticker": "CL=F", "category": "commodity"},
    "Natural Gas": {"ticker": "NG=F", "category": "commodity"},
    "S&P 500": {"ticker": "^GSPC", "category": "index"},
    "NASDAQ": {"ticker": "^IXIC", "category": "index"},
    "Copper": {"ticker": "HG=F", "category": "commodity"},
    "Platinum": {"ticker": "PL=F", "category": "commodity"},
    "Wheat": {"ticker": "ZW=F", "category": "commodity"},
    "EUR/USD": {"ticker": "EURUSD=X", "category": "forex"},
}

KNOWN_SIGNAL_ASSETS = {
    "gold": "gold", "btc": "btc", "eth": "eth", "silver": "silver",
    "oil": "oil", "natgas": "natgas", "sp500": "sp500", "nasdaq": "nasdaq",
    "copper": "copper", "platinum": "platinum", "wheat": "wheat", "eur_usd": "eur_usd",
}

# ---------------------------------------------------------------------------
# Technical Analysis Parameters
# ---------------------------------------------------------------------------
class TechnicalParams:
    SMA_SHORT = 50
    SMA_LONG = 200
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    BB_STD = 2.0

# ---------------------------------------------------------------------------
# Signal Scoring & Confidence
# ---------------------------------------------------------------------------
class SignalConfig:
    CONFIDENCE_WEIGHT_TECHNICAL = 0.40
    CONFIDENCE_WEIGHT_NEWS = 0.20
    CONFIDENCE_WEIGHT_HISTORICAL = 0.40

    SCORE_MIN = -100
    SCORE_MAX = 100

    CONFIDENCE_HIGH = 70
    CONFIDENCE_MEDIUM = 50
    CONFIDENCE_LOW = 30

    BACKTEST_THRESHOLD = 40

    DEEP_DIVE_THRESHOLD = 80
    STANDARD_THRESHOLD = 50

# ---------------------------------------------------------------------------
# Prediction Validation
# ---------------------------------------------------------------------------
class ValidationConfig:
    MIN_VALIDATION_HOURS = 1
    MAX_VALIDATION_HOURS = 48
    BUY_SUCCESS_PCT = 1.0
    BUY_FAILURE_PCT = -3.0
    SELL_SUCCESS_PCT = -1.0
    SELL_FAILURE_PCT = 3.0
    NEUTRAL_THRESHOLD_PCT = 3.0

# ---------------------------------------------------------------------------
# Risk Management
# ---------------------------------------------------------------------------
class RiskConfig:
    MAX_POSITION_PCT = 0.20
    MAX_DRAWDOWN_PCT = 0.15
    DEFAULT_STOP_LOSS_PCT = 5.0
    DEFAULT_TAKE_PROFIT_PCT = 10.0
    RISK_PER_TRADE_PCT = 2.0
    RISK_FREE_RATE = 0.04

# ---------------------------------------------------------------------------
# Budget & Token Management
# ---------------------------------------------------------------------------
class BudgetConfig:
    MAX_DAILY_BUDGET = 5.00
    FULL_AUTONOMY_THRESHOLD = 0.60
    CONSERVATIVE_THRESHOLD = 0.40
    MINIMAL_THRESHOLD = 0.20

# ---------------------------------------------------------------------------
# Autonomous Manager
# ---------------------------------------------------------------------------
class AutonomousConfig:
    STALE_SIGNAL_HOURS = 6
    CYCLE_SLEEP_MINUTES = 5
    BRAIN_CYCLE_MINUTES = 30
    SCANNER_TIMEOUT_SECONDS = 120

# ---------------------------------------------------------------------------
# News Researcher
# ---------------------------------------------------------------------------
class NewsConfig:
    RSS_TIMEOUT_SECONDS = 8
    MAX_ARTICLES_PER_FEED = 12
    CACHE_TTL_SECONDS = 300

# ---------------------------------------------------------------------------
# Chief Monitor
# ---------------------------------------------------------------------------
class MonitorConfig:
    LOOP_DETECTION_THRESHOLD = 10
    MAX_REFLECTIONS = 30
    ALERT_HISTORY_MAX = 500

# ---------------------------------------------------------------------------
# Hindsight Simulator
# ---------------------------------------------------------------------------
class HindsightConfig:
    LOOKBACK_HOURS = 48

# ---------------------------------------------------------------------------
# Auto-Trading Engine
# ---------------------------------------------------------------------------
class AutoTradeConfig:
    ENABLED = True                       # Master switch for auto-trading
    MIN_CONFIDENCE_PCT = 65.0            # Minimum confidence to open a trade
    MAX_CONCURRENT_POSITIONS = 5         # Max open positions at once
    MAX_POSITION_PCT = 20.0              # Max % of portfolio in one position
    MIN_RISK_REWARD = 1.5                # Minimum risk/reward ratio
    ALLOWED_SIGNALS = ["BUY", "STRONG BUY", "SELL", "STRONG SELL"]
    COOLDOWN_HOURS = 6                   # Don't re-trade same asset within N hours
    USE_LESSONS_FILTER = True            # Consult market lessons before trading
    DEFAULT_TRAILING_STOP_PCT = 3.0      # Default trailing stop %
    TRADE_DECISIONS_MAX = 500            # Max entries in trade_decisions.json
    POSITION_SIZE_METHOD = "fixed_fractional"  # "kelly" or "fixed_fractional"
    # Sprint 4: Regime & intelligence integration
    USE_REGIME_AWARENESS = True          # Adjust confidence/sizing based on macro regime
    USE_GEO_RISK_OVERLAY = True          # Reduce exposure during elevated geopolitical risk
    USE_DYNAMIC_CONFIDENCE = True        # Adapt confidence thresholds per-asset based on history
    MAX_CORRELATED_POSITIONS = 3         # Max positions in correlated assets
    DRAWDOWN_PAUSE_PCT = -15.0           # Pause all trading if portfolio down this much
    DRAWDOWN_REDUCED_PCT = -10.0         # Reduce position sizes if portfolio down this much

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardConfig:
    VERSION = "6.0"
    APP_TITLE = "Aegis Terminal"
    LIVE_REFRESH_MS = 30_000      # Was 10s → 30s (logs/monitor) — reduces rerun spam
    SLOW_REFRESH_MS = 60_000      # Was 30s → 60s (advisor/watchlist/trading) — eliminates flicker
    LOG_TAIL_LINES = 50
    MAX_ACTIVITY_ENTRIES = 100
    MAX_RECENT_PREDICTIONS = 15
    MAX_NEWS_ARTICLES = 8

# ---------------------------------------------------------------------------
# UI Theme Colors
# ---------------------------------------------------------------------------
class ThemeColors:
    BG_PRIMARY = "#080b12"
    BG_SECONDARY = "#0d1117"
    BG_CARD = "#161b22"
    BORDER = "rgba(48, 54, 61, 0.5)"
    ACCENT_BLUE = "#58a6ff"
    ACCENT_PURPLE = "#a371f7"
    SUCCESS = "#3fb950"
    WARNING = "#d29922"
    ERROR = "#f85149"
    TEXT_PRIMARY = "#e6edf3"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#484f58"
    TEXT_FAINT = "#6e7681"

SIGNAL_STYLES = {
    "STRONG BUY": {"color": "#fff", "bg": "#198754", "glow": "rgba(25,135,84,0.5)"},
    "BUY":        {"color": "#fff", "bg": "#20c997", "glow": "rgba(32,201,151,0.5)"},
    "NEUTRAL":    {"color": "#fff", "bg": "#6c757d", "glow": "rgba(108,117,125,0.3)"},
    "SELL":       {"color": "#fff", "bg": "#fd7e14", "glow": "rgba(253,126,20,0.5)"},
    "STRONG SELL":{"color": "#fff", "bg": "#dc3545", "glow": "rgba(220,53,69,0.5)"},
}

COLUMN_COLORS = {"Backlog": "#6c757d", "To Do": "#0d6efd", "In Progress": "#ffc107", "Done": "#198754"}
PRIORITY_COLORS = {"high": "#f85149", "medium": "#d29922", "low": "#3fb950"}
HEALTH_COLORS = {"HEALTHY": "#198754", "DEGRADED": "#ffc107", "UNHEALTHY": "#dc3545"}
CONF_COLORS = {"HIGH": "#3fb950", "MEDIUM": "#d29922", "LOW": "#f85149", "VERY LOW": "#6e7681"}

# ---------------------------------------------------------------------------
# Agent Icons
# ---------------------------------------------------------------------------
AGENT_ICONS = {
    "Scanner": ("\U0001f4e1", "Market Scanner"),
    "Analyst": ("\U0001f4ca", "Signal Analyst"),
    "Researcher": ("\U0001f52c", "Report Writer"),
    "NewsResearcher": ("\U0001f4f0", "News Intelligence"),
    "ChartGenerator": ("\U0001f4c8", "Chart Creator"),
    "Manager": ("\U0001f3d7\ufe0f", "Task Manager"),
    "MarketLearner": ("\U0001f393", "Prediction Tracker"),
    "ChiefMonitor": ("\U0001f6e1\ufe0f", "System Supervisor"),
    "Discovery": ("\U0001f52d", "Market Discovery"),
    "AUTONOMOUS ACTION": ("\U0001f916", "Autonomous Engine"),
    "AegisBrain": ("\U0001f9e0", "Brain Loop"),
    "Monitor": ("\U0001f441\ufe0f", "Real-Time Monitor"),
    "HindsightSim": ("\u23ea", "Hindsight Simulator"),
    "Scheduler": ("\u23f0", "Task Scheduler"),
    "CostGuard": ("\U0001f4b0", "Cost Guard"),
    "AutoTrader": ("\U0001f4b9", "Auto-Trading Engine"),
}

# ---------------------------------------------------------------------------
# Price Sanity Bounds — catch garbage data from yfinance
# ---------------------------------------------------------------------------
# If a fetched price falls outside these bounds, it's likely a data error.
# Bounds are generous (10x below to 10x above recent expected ranges).
PRICE_SANITY_BOUNDS = {
    # ── Original 12 assets ──
    "BTC-USD":   (1_000, 1_000_000),    # BTC: $1K - $1M
    "ETH-USD":   (50, 25_000),           # ETH: $50 - $25K (tightened — was 100K, BTC price slipped through)
    "GC=F":      (500, 50_000),          # Gold: $500 - $50K per oz
    "SI=F":      (5, 200),               # Silver: $5 - $200 per oz (tightened — was 5K, Gold price slipped through)
    "CL=F":      (5, 500),               # Oil: $5 - $500 per barrel
    "NG=F":      (0.5, 50),              # NatGas: $0.50 - $50
    "^GSPC":     (1_000, 50_000),        # S&P 500: 1K - 50K
    "^IXIC":     (2_000, 100_000),       # NASDAQ: 2K - 100K
    "HG=F":      (0.5, 50),              # Copper: $0.50 - $50/lb
    "PL=F":      (100, 50_000),          # Platinum: $100 - $50K
    "ZW=F":      (100, 5_000),           # Wheat: $100 - $5K per bushel
    "EURUSD=X":  (0.5, 2.0),            # EUR/USD: 0.50 - 2.00
    # ── US Stocks (20) ──
    "AAPL":      (30, 1_000),            # Apple: $30 - $1K
    "MSFT":      (70, 2_500),            # Microsoft: $70 - $2.5K
    "NVDA":      (15, 800),              # NVIDIA: $15 - $800
    "GOOGL":     (30, 1_000),            # Google: $30 - $1K
    "AMZN":      (30, 1_200),            # Amazon: $30 - $1.2K
    "META":      (80, 3_000),            # Meta: $80 - $3K
    "TSLA":      (30, 2_000),            # Tesla: $30 - $2K
    "JPM":       (40, 1_300),            # JPMorgan: $40 - $1.3K
    "BRK-B":     (80, 2_500),            # Berkshire: $80 - $2.5K
    "UNH":       (90, 3_000),            # UnitedHealth: $90 - $3K
    "V":         (50, 1_700),            # Visa: $50 - $1.7K
    "JNJ":       (30, 900),              # J&J: $30 - $900
    "WMT":       (15, 500),              # Walmart: $15 - $500
    "MA":        (90, 2_800),            # Mastercard: $90 - $2.8K
    "XOM":       (20, 650),              # ExxonMobil: $20 - $650
    "AMD":       (20, 900),              # AMD: $20 - $900
    "NFLX":      (100, 5_000),           # Netflix: $100 - $5K
    "INTC":      (3, 150),               # Intel: $3 - $150
    "KO":        (10, 350),              # Coca-Cola: $10 - $350
    "DIS":       (15, 650),              # Disney: $15 - $650
    # ── Crypto (8) ──
    "SOL-USD":   (1, 5_000),             # Solana: $1 - $5K
    "XRP-USD":   (0.05, 100),            # XRP: $0.05 - $100
    "DOGE-USD":  (0.001, 10),            # Dogecoin: $0.001 - $10
    "ADA-USD":   (0.01, 50),             # Cardano: $0.01 - $50
    "AVAX-USD":  (0.5, 1_000),           # Avalanche: $0.50 - $1K
    "LINK-USD":  (0.5, 500),             # Chainlink: $0.50 - $500
    "DOT-USD":   (0.5, 300),             # Polkadot: $0.50 - $300
    "LTC-USD":   (5, 3_000),             # Litecoin: $5 - $3K
    # ── Commodities (2) ──
    "PA=F":      (100, 50_000),          # Palladium: $100 - $50K
    "ZC=F":      (100, 2_000),           # Corn: $100 - $2K per bushel
    # ── Indices (2) ──
    "^DJI":      (5_000, 200_000),       # Dow Jones: 5K - 200K
    "^RUT":      (500, 10_000),          # Russell 2000: 500 - 10K
    # ── Forex (4) ──
    "GBPUSD=X":  (0.5, 2.5),            # GBP/USD: 0.50 - 2.50
    "JPY=X":     (50, 300),              # USD/JPY: 50 - 300
    "AUDUSD=X":  (0.3, 1.5),            # AUD/USD: 0.30 - 1.50
    "CHF=X":     (0.3, 2.0),            # USD/CHF: 0.30 - 2.00
}

SETTINGS_OVERRIDE_FILE = DATA_DIR / "settings_override.json"


# ---------------------------------------------------------------------------
# Settings Override Loader — wires dashboard Settings into backend engines
# ---------------------------------------------------------------------------

def load_settings_override(user_id: str = None) -> dict:
    """Load settings from settings_override.json (or per-user file).

    Returns the raw dict of overrides, or {} if file missing/corrupt.
    """
    if user_id and user_id != "default":
        user_file = PROJECT_ROOT / "users" / user_id / "settings_override.json"
        if user_file.exists():
            try:
                return json.loads(user_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

    # Fall back to global settings file
    if SETTINGS_OVERRIDE_FILE.exists():
        try:
            return json.loads(SETTINGS_OVERRIDE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def apply_settings_override(user_id: str = None) -> dict:
    """Load user settings and apply them to config classes.

    This is the key function that makes the Settings page actually work.
    Called by auto_trader.py and market_scanner.py at initialization.

    Returns the loaded overrides dict for reference.
    """
    overrides = load_settings_override(user_id)
    if not overrides:
        return {}

    # --- Signal Confidence Weights ---
    if "confidence_weight_technical" in overrides:
        SignalConfig.CONFIDENCE_WEIGHT_TECHNICAL = float(overrides["confidence_weight_technical"])
    if "confidence_weight_news" in overrides:
        SignalConfig.CONFIDENCE_WEIGHT_NEWS = float(overrides["confidence_weight_news"])
    if "confidence_weight_historical" in overrides:
        SignalConfig.CONFIDENCE_WEIGHT_HISTORICAL = float(overrides["confidence_weight_historical"])

    # --- Risk Thresholds ---
    if "max_position_pct" in overrides:
        RiskConfig.MAX_POSITION_PCT = float(overrides["max_position_pct"]) / 100.0
    if "max_drawdown_pct" in overrides:
        RiskConfig.MAX_DRAWDOWN_PCT = float(overrides["max_drawdown_pct"]) / 100.0
    if "default_stop_loss_pct" in overrides:
        RiskConfig.DEFAULT_STOP_LOSS_PCT = float(overrides["default_stop_loss_pct"])
    if "default_take_profit_pct" in overrides:
        RiskConfig.DEFAULT_TAKE_PROFIT_PCT = float(overrides["default_take_profit_pct"])
    if "risk_free_rate" in overrides:
        RiskConfig.RISK_FREE_RATE = float(overrides["risk_free_rate"])

    # --- Auto-Trader Gates ---
    if "auto_enabled" in overrides:
        AutoTradeConfig.ENABLED = bool(overrides["auto_enabled"])
    if "auto_min_confidence" in overrides:
        AutoTradeConfig.MIN_CONFIDENCE_PCT = float(overrides["auto_min_confidence"])
    if "auto_max_positions" in overrides:
        AutoTradeConfig.MAX_CONCURRENT_POSITIONS = int(overrides["auto_max_positions"])
    if "auto_cooldown_hours" in overrides:
        AutoTradeConfig.COOLDOWN_HOURS = int(overrides["auto_cooldown_hours"])
    if "auto_min_rr" in overrides:
        AutoTradeConfig.MIN_RISK_REWARD = float(overrides["auto_min_rr"])
    if "position_size_method" in overrides:
        AutoTradeConfig.POSITION_SIZE_METHOD = str(overrides["position_size_method"])
    if "default_trailing_stop_pct" in overrides:
        AutoTradeConfig.DEFAULT_TRAILING_STOP_PCT = float(overrides["default_trailing_stop_pct"])

    # --- Intelligence Toggles ---
    if "use_regime_awareness" in overrides:
        AutoTradeConfig.USE_REGIME_AWARENESS = bool(overrides["use_regime_awareness"])
    if "use_geo_risk_overlay" in overrides:
        AutoTradeConfig.USE_GEO_RISK_OVERLAY = bool(overrides["use_geo_risk_overlay"])
    if "use_dynamic_confidence" in overrides:
        AutoTradeConfig.USE_DYNAMIC_CONFIDENCE = bool(overrides["use_dynamic_confidence"])
    if "use_lessons_filter" in overrides:
        AutoTradeConfig.USE_LESSONS_FILTER = bool(overrides["use_lessons_filter"])

    # --- Drawdown Thresholds ---
    if "drawdown_reduced_pct" in overrides:
        AutoTradeConfig.DRAWDOWN_REDUCED_PCT = float(overrides["drawdown_reduced_pct"])
    if "drawdown_pause_pct" in overrides:
        AutoTradeConfig.DRAWDOWN_PAUSE_PCT = float(overrides["drawdown_pause_pct"])

    # --- Technical Indicator Params ---
    if "sma_short" in overrides:
        TechnicalParams.SMA_SHORT = int(overrides["sma_short"])
    if "sma_long" in overrides:
        TechnicalParams.SMA_LONG = int(overrides["sma_long"])
    if "rsi_period" in overrides:
        TechnicalParams.RSI_PERIOD = int(overrides["rsi_period"])
    if "rsi_oversold" in overrides:
        TechnicalParams.RSI_OVERSOLD = int(overrides["rsi_oversold"])
    if "rsi_overbought" in overrides:
        TechnicalParams.RSI_OVERBOUGHT = int(overrides["rsi_overbought"])
    if "bb_std" in overrides:
        TechnicalParams.BB_STD = float(overrides["bb_std"])

    # --- Dashboard Refresh ---
    if "live_refresh_s" in overrides:
        DashboardConfig.LIVE_REFRESH_MS = int(overrides["live_refresh_s"]) * 1000
    if "slow_refresh_s" in overrides:
        DashboardConfig.SLOW_REFRESH_MS = int(overrides["slow_refresh_s"]) * 1000

    return overrides
