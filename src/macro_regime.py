"""Macro Regime Detector — classifies the current market environment.

Fetches macro indicators (VIX, Treasury yields, DXY, Gold/SPX ratio) and
classifies the market into regimes: RISK_ON, RISK_OFF, INFLATIONARY,
DEFLATIONARY, HIGH_VOLATILITY. Adjusts signal confidence accordingly.

Usage:
    from macro_regime import MacroRegimeDetector
    detector = MacroRegimeDetector()
    regime = detector.detect()
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
REGIME_CACHE_FILE = DATA_DIR / "macro_regime.json"


# ---------------------------------------------------------------------------
# Regime definitions and thresholds
# ---------------------------------------------------------------------------

REGIME_MULTIPLIERS = {
    "RISK_ON": {
        "description": "Markets are confident. Equities favored, safe havens less attractive.",
        "icon": "🟢",
        "Gold": 0.85, "Silver": 0.90, "Oil": 1.05, "BTC": 1.10, "ETH": 1.15,
        "S&P 500": 1.20, "NASDAQ": 1.25, "Natural Gas": 1.0, "Copper": 1.15,
        "Platinum": 1.05, "Wheat": 0.95, "EUR/USD": 1.05,
    },
    "RISK_OFF": {
        "description": "Fear dominates. Safe havens surge, risk assets decline.",
        "icon": "🔴",
        "Gold": 1.30, "Silver": 1.15, "Oil": 0.90, "BTC": 1.10, "ETH": 0.95,
        "S&P 500": 0.75, "NASDAQ": 0.70, "Natural Gas": 1.05, "Copper": 0.85,
        "Platinum": 1.05, "Wheat": 1.10, "EUR/USD": 0.90,
    },
    "INFLATIONARY": {
        "description": "Inflation rising. Commodities and real assets outperform.",
        "icon": "🔥",
        "Gold": 1.25, "Silver": 1.20, "Oil": 1.20, "BTC": 1.15, "ETH": 1.05,
        "S&P 500": 0.90, "NASDAQ": 0.85, "Natural Gas": 1.15, "Copper": 1.20,
        "Platinum": 1.15, "Wheat": 1.25, "EUR/USD": 0.90,
    },
    "DEFLATIONARY": {
        "description": "Deflation risk. Cash is king, bonds rally, commodities fall.",
        "icon": "❄️",
        "Gold": 1.05, "Silver": 0.85, "Oil": 0.75, "BTC": 0.80, "ETH": 0.75,
        "S&P 500": 0.85, "NASDAQ": 0.80, "Natural Gas": 0.80, "Copper": 0.70,
        "Platinum": 0.80, "Wheat": 0.90, "EUR/USD": 1.10,
    },
    "HIGH_VOLATILITY": {
        "description": "Extreme uncertainty. All signals less reliable, widen stops.",
        "icon": "⚡",
        "Gold": 1.10, "Silver": 1.05, "Oil": 0.95, "BTC": 0.85, "ETH": 0.80,
        "S&P 500": 0.80, "NASDAQ": 0.75, "Natural Gas": 0.95, "Copper": 0.90,
        "Platinum": 0.95, "Wheat": 1.00, "EUR/USD": 0.95,
    },
    "NEUTRAL": {
        "description": "No strong macro signal. Trust asset-level analysis.",
        "icon": "⚪",
        "Gold": 1.0, "Silver": 1.0, "Oil": 1.0, "BTC": 1.0, "ETH": 1.0,
        "S&P 500": 1.0, "NASDAQ": 1.0, "Natural Gas": 1.0, "Copper": 1.0,
        "Platinum": 1.0, "Wheat": 1.0, "EUR/USD": 1.0,
    },
}


class MacroRegimeDetector:
    """Detects the current macro regime from market indicators."""

    def _fetch_indicator(self, ticker: str, period: str = "3mo") -> dict:
        """Fetch current value and trend for a macro indicator."""
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
            if df.empty:
                return {"value": None, "trend": "flat", "change_pct": 0}
            current = float(df["Close"].iloc[-1])
            prev_20d = float(df["Close"].iloc[-20]) if len(df) >= 20 else current
            change_pct = round((current - prev_20d) / prev_20d * 100, 2)
            if change_pct > 2:
                trend = "rising"
            elif change_pct < -2:
                trend = "falling"
            else:
                trend = "flat"
            return {"value": round(current, 2), "trend": trend, "change_pct": change_pct}
        except Exception:
            return {"value": None, "trend": "unknown", "change_pct": 0}

    def detect(self) -> dict:
        """Detect the current macro regime.

        Returns:
            {
                "regime": str,
                "confidence": float,
                "description": str,
                "icon": str,
                "indicators": {...},
                "multipliers": {...},
                "timestamp": str,
            }
        """
        # Fetch macro indicators
        vix = self._fetch_indicator("^VIX", "3mo")
        treasury_10y = self._fetch_indicator("^TNX", "3mo")
        dxy = self._fetch_indicator("DX-Y.NYB", "3mo")
        gold = self._fetch_indicator("GC=F", "3mo")
        spx = self._fetch_indicator("^GSPC", "3mo")

        indicators = {
            "VIX": vix,
            "10Y_Treasury": treasury_10y,
            "DXY_Dollar": dxy,
            "Gold": gold,
            "SP500": spx,
        }

        # Scoring: each regime gets points based on indicator alignment
        scores = {
            "RISK_ON": 0,
            "RISK_OFF": 0,
            "INFLATIONARY": 0,
            "DEFLATIONARY": 0,
            "HIGH_VOLATILITY": 0,
        }

        vix_val = vix.get("value") or 20
        vix_trend = vix.get("trend", "flat")
        gold_trend = gold.get("trend", "flat")
        spx_trend = spx.get("trend", "flat")
        dxy_trend = dxy.get("trend", "flat")
        treasury_trend = treasury_10y.get("trend", "flat")

        # HIGH VOLATILITY
        if vix_val >= 30:
            scores["HIGH_VOLATILITY"] += 4
        elif vix_val >= 25:
            scores["HIGH_VOLATILITY"] += 2
        if vix_trend == "rising":
            scores["HIGH_VOLATILITY"] += 1

        # RISK ON
        if vix_val < 18:
            scores["RISK_ON"] += 2
        if spx_trend == "rising":
            scores["RISK_ON"] += 2
        if dxy_trend == "falling":
            scores["RISK_ON"] += 1
        if gold_trend == "falling":
            scores["RISK_ON"] += 1

        # RISK OFF
        if vix_val >= 25:
            scores["RISK_OFF"] += 2
        if spx_trend == "falling":
            scores["RISK_OFF"] += 2
        if gold_trend == "rising":
            scores["RISK_OFF"] += 1
        if dxy_trend == "rising":
            scores["RISK_OFF"] += 1

        # INFLATIONARY
        if gold_trend == "rising":
            scores["INFLATIONARY"] += 2
        if treasury_trend == "rising":
            scores["INFLATIONARY"] += 1
        if dxy_trend == "falling":
            scores["INFLATIONARY"] += 1

        # DEFLATIONARY
        if gold_trend == "falling":
            scores["DEFLATIONARY"] += 1
        if treasury_trend == "falling":
            scores["DEFLATIONARY"] += 2
        if spx_trend == "falling" and vix_val < 25:
            scores["DEFLATIONARY"] += 1

        # Determine winner
        max_score = max(scores.values())
        if max_score < 3:
            regime = "NEUTRAL"
        else:
            regime = max(scores, key=scores.get)

        confidence = min(max_score / 6.0, 1.0)

        regime_info = REGIME_MULTIPLIERS.get(regime, REGIME_MULTIPLIERS["NEUTRAL"])

        result = {
            "regime": regime,
            "confidence": round(confidence, 2),
            "description": regime_info.get("description", ""),
            "icon": regime_info.get("icon", ""),
            "scores": scores,
            "indicators": indicators,
            "multipliers": {
                k: v for k, v in regime_info.items()
                if k not in ("description", "icon")
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Cache
        REGIME_CACHE_FILE.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return result

    def get_multiplier(self, regime: str, asset_name: str) -> float:
        """Get confidence multiplier for a given regime and asset."""
        regime_info = REGIME_MULTIPLIERS.get(regime, REGIME_MULTIPLIERS["NEUTRAL"])
        return regime_info.get(asset_name, 1.0)

    def load_cached(self) -> dict | None:
        """Load cached regime data if available."""
        if REGIME_CACHE_FILE.exists():
            try:
                return json.loads(REGIME_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None
