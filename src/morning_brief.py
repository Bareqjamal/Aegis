"""Morning Brief Generator — auto-generates a concise daily market summary.

Combines: macro regime, geopolitical risk, top signals, economic calendar,
and news sentiment into a single readable brief.

Usage:
    from morning_brief import MorningBrief
    brief = MorningBrief()
    report = brief.generate()
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
MEMORY_DIR = PROJECT_ROOT / "memory"
WATCHLIST_FILE = DATA_DIR / "user_watchlist.json"
BRIEF_CACHE_FILE = DATA_DIR / "morning_brief.json"


class MorningBrief:
    """Generates a concise morning brief from all available data sources."""

    def _load_json(self, path: Path) -> dict | list | None:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f" Failed to load JSON {path.name}: {e}")
        return None

    def _get_watchlist_signals(self) -> list[dict]:
        """Load latest watchlist signals."""
        data = self._load_json(DATA_DIR / "watchlist_summary.json")
        if not data:
            return []
        signals = []
        for asset_name, info in data.items():
            # Extract confidence_pct from nested confidence dict or flat field
            conf = info.get("confidence", {})
            conf_pct = conf.get("confidence_pct", 0) if isinstance(conf, dict) else conf
            signals.append({
                "asset": asset_name,
                "signal": info.get("signal_label", info.get("signal", "NEUTRAL")),
                "confidence": conf_pct,
                "score": info.get("signal_score", 0),
                "price": info.get("price", 0),
                "change_pct": info.get("daily_change_pct", info.get("price_change_pct", 0)),
            })
        # Sort by absolute confidence descending
        signals.sort(key=lambda s: abs(s["confidence"]), reverse=True)
        return signals

    def _get_regime(self) -> dict | None:
        """Load cached macro regime."""
        return self._load_json(DATA_DIR / "macro_regime.json")

    def _get_geo_analysis(self) -> dict | None:
        """Load cached geopolitical analysis."""
        return self._load_json(DATA_DIR / "geopolitical_analysis.json")

    def _get_predictions(self) -> list[dict]:
        """Load recent predictions for accountability."""
        data = self._load_json(MEMORY_DIR / "market_predictions.json")
        if not data:
            return []
        # Handle both dict format {"predictions": [...]} and raw list format
        if isinstance(data, dict):
            preds = data.get("predictions", [])
        elif isinstance(data, list):
            preds = data
        else:
            return []
        return preds[-10:]  # Last 10

    def _get_calendar_events(self) -> list[dict]:
        """Get upcoming high-impact economic events."""
        try:
            from economic_calendar import EconomicCalendar
            cal = EconomicCalendar()
            return cal.get_high_impact_upcoming()[:5]
        except Exception as e:
            logger.warning(f"Calendar events load failed: {e}")
            return []

    def _get_social_data(self) -> dict | None:
        """Load cached social sentiment data."""
        return self._load_json(DATA_DIR / "social_sentiment.json")

    def _classify_signal(self, signal: str, confidence: float) -> dict:
        """Classify a signal into user-friendly verdict."""
        sig_upper = signal.upper()
        # Threshold aligned with Daily Advisor adjusted threshold = 60
        if sig_upper in ("STRONG BUY", "BUY") and confidence >= 60:
            return {"verdict": "BUY NOW", "color": "#3fb950", "emoji": "🟢"}
        elif sig_upper in ("STRONG BUY", "BUY"):
            return {"verdict": "LEANING BUY", "color": "#20c997", "emoji": "🔵"}
        elif sig_upper in ("STRONG SELL", "SELL") and confidence >= 60:
            return {"verdict": "AVOID", "color": "#f85149", "emoji": "🔴"}
        elif sig_upper in ("STRONG SELL", "SELL"):
            return {"verdict": "CAUTION", "color": "#fd7e14", "emoji": "🟠"}
        else:
            return {"verdict": "WAIT", "color": "#6e7681", "emoji": "⚪"}

    def generate(self) -> dict:
        """Generate the full morning brief.

        Returns a dict with sections:
            - headline: One-line market summary
            - regime: Current macro regime info
            - risk_level: Geopolitical risk assessment
            - top_picks: Top 3 actionable assets
            - watchlist_summary: Quick overview of all signals
            - calendar: Next key events
            - key_takeaway: One sentence bottom line
        """
        now = datetime.now(timezone.utc)
        signals = self._get_watchlist_signals()
        regime = self._get_regime()
        geo = self._get_geo_analysis()
        calendar_events = self._get_calendar_events()
        social = self._get_social_data()

        # -- Headline --
        regime_name = regime.get("regime", "NEUTRAL") if regime else "NEUTRAL"
        regime_icon = regime.get("icon", "⚪") if regime else "⚪"
        regime_desc = regime.get("description", "") if regime else ""

        buy_count = sum(1 for s in signals if s["signal"].upper() in ("BUY", "STRONG BUY"))
        sell_count = sum(1 for s in signals if s["signal"].upper() in ("SELL", "STRONG SELL"))
        neutral_count = len(signals) - buy_count - sell_count

        if buy_count > sell_count * 2:
            market_tone = "Bullish"
            tone_emoji = "📈"
        elif sell_count > buy_count * 2:
            market_tone = "Bearish"
            tone_emoji = "📉"
        elif buy_count > sell_count:
            market_tone = "Cautiously Bullish"
            tone_emoji = "↗️"
        elif sell_count > buy_count:
            market_tone = "Cautiously Bearish"
            tone_emoji = "↘️"
        else:
            market_tone = "Mixed/Neutral"
            tone_emoji = "↔️"

        headline = f"{tone_emoji} Markets are {market_tone} — {regime_icon} {regime_name} regime active"

        # -- Risk level --
        risk_level = "CALM"
        risk_icon = "🟢"
        if geo:
            risk_level = geo.get("risk_level", "CALM")
            risk_map = {
                "EXTREME": "🔴", "ELEVATED": "🟠",
                "MODERATE": "🟡", "LOW": "🔵", "CALM": "🟢",
            }
            risk_icon = risk_map.get(risk_level, "🟢")

        # -- Top picks (ALL signals, sorted by conviction strength) --
        top_picks = []
        for s in signals:
            verdict = self._classify_signal(s["signal"], s["confidence"])
            top_picks.append({
                **s,
                **verdict,
                "reason": self._build_reason(s, regime, geo),
            })

        # -- Watchlist summary --
        watchlist_summary = []
        for s in signals:
            verdict = self._classify_signal(s["signal"], s["confidence"])
            watchlist_summary.append({
                "asset": s["asset"],
                "signal": s["signal"],
                "confidence": s["confidence"],
                "verdict": verdict["verdict"],
                "emoji": verdict["emoji"],
                "price": s["price"],
                "change_pct": s["change_pct"],
            })

        # -- Calendar section --
        calendar_section = []
        for ev in calendar_events:
            calendar_section.append({
                "name": ev.get("name", ""),
                "icon": ev.get("icon", ""),
                "countdown": ev.get("countdown", ""),
                "date": ev.get("date_display", ""),
                "impact": ev.get("impact", 0),
                "assets": ev.get("assets_affected", []),
            })

        # -- Key takeaway --
        if top_picks:
            best = top_picks[0]
            if best["verdict"] == "BUY NOW":
                takeaway = (
                    f"Strongest signal: {best['emoji']} {best['asset']} "
                    f"({best['signal']}, {best['confidence']}% confidence). "
                    f"Consider entering if your risk tolerance allows."
                )
            elif best["verdict"] == "AVOID":
                takeaway = (
                    f"Warning: {best['emoji']} {best['asset']} showing "
                    f"{best['signal']} signal. Avoid new positions."
                )
            else:
                takeaway = (
                    f"No strong conviction trades today. "
                    f"Best opportunity: {best['asset']} ({best['signal']}, "
                    f"{best['confidence']}%). Wait for confirmation."
                )
        else:
            takeaway = "No signal data available. Run a market scan first."

        # -- Build final brief --
        brief = {
            "timestamp": now.isoformat(),
            "date_display": now.strftime("%A, %B %d, %Y"),
            "headline": headline,
            "market_tone": market_tone,
            "tone_emoji": tone_emoji,
            "regime": {
                "name": regime_name,
                "icon": regime_icon,
                "description": regime_desc,
                "confidence": regime.get("confidence", 0) if regime else 0,
            },
            "risk": {
                "level": risk_level,
                "icon": risk_icon,
                "geo_events": geo.get("geopolitical_articles", 0) if geo else 0,
                "dominant_events": list((geo or {}).get("dominant_events", {}).keys()),
            },
            "signals_overview": {
                "total": len(signals),
                "buy": buy_count,
                "sell": sell_count,
                "neutral": neutral_count,
            },
            "top_picks": top_picks,
            "watchlist_summary": watchlist_summary,
            "calendar": calendar_section,
            "social_pulse": self._build_social_section(social),
            "key_takeaway": takeaway,
        }

        # Cache
        BRIEF_CACHE_FILE.write_text(
            json.dumps(brief, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return brief

    def _build_social_section(self, social: dict | None) -> dict:
        """Build social pulse section for the brief."""
        if not social:
            return {"available": False, "summary": "No social data. Run a social scan."}

        asset_scores = social.get("asset_scores", {})
        alerts = social.get("alerts", [])
        stats = social.get("stats", {})

        # Top movers by social sentiment
        social_movers = sorted(
            [(name, data) for name, data in asset_scores.items() if abs(data.get("social_score", 0)) > 0.1],
            key=lambda x: abs(x[1].get("social_score", 0)),
            reverse=True,
        )[:5]

        movers = []
        for name, data in social_movers:
            movers.append({
                "asset": name,
                "score": data.get("social_score", 0),
                "label": data.get("social_label", "NEUTRAL"),
                "buzz": data.get("buzz_level", "LOW"),
                "reddit_mentions": data.get("reddit_mentions", 0),
            })

        # Top influencer alerts
        inf_alerts = [a for a in alerts if a.get("type") == "INFLUENCER"][:3]

        return {
            "available": True,
            "movers": movers,
            "influencer_alerts": inf_alerts,
            "total_alerts": len(alerts),
            "high_alerts": stats.get("high_alerts", 0),
            "summary": social.get("summary", ""),
        }

    def _build_reason(self, signal: dict, regime: dict | None, geo: dict | None) -> str:
        """Build a plain-language reason for a signal."""
        parts = []
        asset = signal["asset"]
        sig = signal["signal"]
        conf = signal["confidence"]

        # Technical
        if conf >= 70:
            parts.append(f"Strong technical setup ({conf}% confidence)")
        elif conf >= 50:
            parts.append(f"Moderate technical signal ({conf}%)")
        else:
            parts.append(f"Weak/uncertain signal ({conf}%)")

        # Regime context
        if regime:
            regime_name = regime.get("regime", "NEUTRAL")
            multipliers = regime.get("multipliers", {})
            mult = multipliers.get(asset, 1.0)
            if mult > 1.1:
                parts.append(f"{regime_name} regime favors {asset}")
            elif mult < 0.9:
                parts.append(f"{regime_name} regime is headwind for {asset}")

        # Geo context
        if geo:
            asset_impact = geo.get("asset_impact", {}).get(asset, {})
            direction = asset_impact.get("direction", "NEUTRAL")
            if direction == "BULLISH":
                parts.append("Geopolitical events are supportive")
            elif direction == "BEARISH":
                parts.append("Geopolitical headwinds present")

        # Price action
        change = signal.get("change_pct", 0)
        if change > 2:
            parts.append(f"Already up {change:.1f}% today — momentum")
        elif change < -2:
            parts.append(f"Down {abs(change):.1f}% today — possible dip buy" if "BUY" in sig else f"Down {abs(change):.1f}% — weakness confirmed")

        return ". ".join(parts) + "."

    def load_cached(self) -> dict | None:
        """Load last generated brief."""
        if BRIEF_CACHE_FILE.exists():
            try:
                return json.loads(BRIEF_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f" Failed to load cached brief: {e}")
        return None
