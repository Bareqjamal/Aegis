"""
Project Aegis — Smoke Tests
============================
Minimum viable test suite. These MUST pass before any deploy.
Run: pytest tests/ -v
"""

import importlib
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 1. IMPORT TESTS — Can every module load without crashing?
# ---------------------------------------------------------------------------

MODULES = [
    "src.config",
    "src.market_scanner",
    "src.news_researcher",
    "src.auto_trader",
    "src.paper_trader",
    "src.risk_manager",
    "src.chart_engine",
    "src.market_learner",
    "src.strategy_builder",
    "src.alert_manager",
    "src.agents",
    "src.token_manager",
    "src.chief_monitor",
    "src.performance_analytics",
    "src.fundamentals",
    "src.sector_analysis",
    "src.market_discovery",
    "src.hindsight_simulator",
    "src.geopolitical_monitor",
    "src.macro_regime",
    "src.economic_calendar",
    "src.morning_brief",
    "src.social_sentiment",
    "src.portfolio_optimizer",
    "src.watchlist_manager",
    "src.report_generator",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    """Every backend module must import without errors."""
    mod = importlib.import_module(module_name)
    assert mod is not None


# ---------------------------------------------------------------------------
# 2. CONFIG TESTS — Are critical settings sane?
# ---------------------------------------------------------------------------


def test_config_paths_exist():
    """Config paths must point to real directories."""
    from src.config import DATA_DIR, MEMORY_DIR, PROJECT_ROOT

    assert PROJECT_ROOT.exists(), f"PROJECT_ROOT missing: {PROJECT_ROOT}"
    assert DATA_DIR.exists(), f"DATA_DIR missing: {DATA_DIR}"
    assert MEMORY_DIR.exists(), f"MEMORY_DIR missing: {MEMORY_DIR}"


def test_config_watchlist_not_empty():
    """Must have assets to scan."""
    from src.config import CORE_WATCHLIST, DISCOVERY_ASSETS

    assert len(CORE_WATCHLIST) >= 4, "Need at least 4 core assets"
    assert len(DISCOVERY_ASSETS) >= 4, "Need at least 4 discovery assets"


def test_config_tickers_valid():
    """Every asset must have a ticker string."""
    from src.config import CORE_WATCHLIST, DISCOVERY_ASSETS

    for name, info in {**CORE_WATCHLIST, **DISCOVERY_ASSETS}.items():
        assert "ticker" in info, f"{name} missing ticker"
        assert isinstance(info["ticker"], str), f"{name} ticker not a string"
        assert len(info["ticker"]) > 0, f"{name} ticker is empty"


# ---------------------------------------------------------------------------
# 3. DATA INTEGRITY TESTS — Are JSON files valid?
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "src" / "data"
MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"


def _find_json_files():
    """Collect all JSON files that exist."""
    files = []
    for d in [DATA_DIR, MEMORY_DIR]:
        if d.exists():
            files.extend(d.glob("*.json"))
    return files


@pytest.mark.parametrize("json_path", _find_json_files(), ids=lambda p: p.name)
def test_json_files_are_valid(json_path):
    """Every JSON file must parse without errors."""
    content = json_path.read_text(encoding="utf-8")
    if content.strip():  # Skip empty files
        data = json.loads(content)  # Will raise on invalid JSON
        assert data is not None


def test_user_watchlist_structure():
    """user_watchlist.json must have the expected shape."""
    path = DATA_DIR / "user_watchlist.json"
    if not path.exists():
        pytest.skip("user_watchlist.json not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Must be a dict"
    assert "assets" in data, "Must have 'assets' key"
    assert len(data["assets"]) >= 1, "Must have at least 1 asset"


# ---------------------------------------------------------------------------
# 4. SIGNAL SCORING SANITY — Does the math make sense?
# ---------------------------------------------------------------------------


def test_signal_config_weights_sum_to_one():
    """Confidence weights must sum to 1.0."""
    from src.config import SignalConfig

    total = (
        SignalConfig.CONFIDENCE_WEIGHT_TECHNICAL
        + SignalConfig.CONFIDENCE_WEIGHT_NEWS
        + SignalConfig.CONFIDENCE_WEIGHT_HISTORICAL
    )
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, not 1.0"


def test_signal_score_range():
    """Score range must be symmetric."""
    from src.config import SignalConfig

    assert SignalConfig.SCORE_MIN == -SignalConfig.SCORE_MAX


# ---------------------------------------------------------------------------
# 5. RISK CONFIG SANITY
# ---------------------------------------------------------------------------


def test_risk_config_values():
    """Risk parameters must be within sane bounds."""
    from src.config import RiskConfig

    assert 0 < RiskConfig.MAX_POSITION_PCT <= 1.0
    assert 0 < RiskConfig.MAX_DRAWDOWN_PCT <= 1.0
    assert 0 < RiskConfig.DEFAULT_STOP_LOSS_PCT <= 50
    assert 0 < RiskConfig.DEFAULT_TAKE_PROFIT_PCT <= 100
