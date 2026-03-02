"""Geopolitical Event Monitor — detects geopolitical events from news and maps asset impact.

Scans news headlines for geopolitical keywords (war, sanctions, tariffs, elections, etc.),
classifies events, and computes expected directional impact on watchlist assets using a
rule-based impact matrix derived from historical precedent.

Usage:
    from geopolitical_monitor import GeopoliticalMonitor
    monitor = GeopoliticalMonitor()
    report = monitor.analyze(all_news_articles)
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
GEO_CACHE_FILE = DATA_DIR / "geopolitical_analysis.json"

# ---------------------------------------------------------------------------
# Event taxonomy — keywords that identify geopolitical events
# ---------------------------------------------------------------------------

EVENT_KEYWORDS = {
    "WAR_CONFLICT": {
        "keywords": [
            "war", "military", "invasion", "missile", "airstrike", "bombing",
            "troops", "army", "navy", "combat", "conflict", "escalation",
            "ceasefire", "nuclear", "drone strike", "offensive", "casualties",
            "strait of hormuz", "red sea", "houthi", "hezbollah", "hamas",
            "nato", "defense", "weapons", "ammunition", "battleground",
        ],
        "label": "Military Conflict",
        "severity_base": 8,
        "icon": "🔴",
    },
    "SANCTIONS": {
        "keywords": [
            "sanction", "embargo", "trade ban", "asset freeze", "blacklist",
            "export control", "import ban", "economic penalty", "restrict",
            "ofac", "sanctions list", "financial penalty", "blocked entity",
        ],
        "label": "Sanctions",
        "severity_base": 6,
        "icon": "🟠",
    },
    "TARIFFS_TRADE": {
        "keywords": [
            "tariff", "trade war", "import duty", "export tax", "trade deal",
            "trade agreement", "trade deficit", "protectionism", "customs",
            "wto", "trade dispute", "anti-dumping", "retaliatory tariff",
        ],
        "label": "Trade/Tariffs",
        "severity_base": 5,
        "icon": "🟡",
    },
    "CENTRAL_BANK": {
        "keywords": [
            "fed rate", "interest rate", "rate cut", "rate hike", "fomc",
            "federal reserve", "ecb", "bank of england", "bank of japan",
            "monetary policy", "quantitative easing", "tightening",
            "dovish", "hawkish", "inflation target", "basis points",
            "powell", "lagarde", "yield curve",
        ],
        "label": "Central Bank",
        "severity_base": 7,
        "icon": "🏦",
    },
    "ELECTIONS": {
        "keywords": [
            "election", "vote", "referendum", "inauguration", "president",
            "prime minister", "parliament", "coalition", "campaign",
            "political crisis", "impeachment", "coup", "regime change",
        ],
        "label": "Political/Elections",
        "severity_base": 5,
        "icon": "🗳️",
    },
    "ENERGY_SUPPLY": {
        "keywords": [
            "opec", "oil supply", "production cut", "pipeline", "refinery",
            "lng", "energy crisis", "oil embargo", "gas supply", "fuel shortage",
            "oil rig", "shale", "drilling", "petroleum reserve",
            "strategic reserve", "spr", "barrel",
        ],
        "label": "Energy Supply",
        "severity_base": 6,
        "icon": "⛽",
    },
    "NATURAL_DISASTER": {
        "keywords": [
            "earthquake", "tsunami", "hurricane", "typhoon", "flood",
            "drought", "wildfire", "volcano", "climate emergency",
            "supply disruption", "crop failure",
        ],
        "label": "Natural Disaster",
        "severity_base": 4,
        "icon": "🌊",
    },
    "PANDEMIC_HEALTH": {
        "keywords": [
            "pandemic", "epidemic", "virus", "outbreak", "lockdown",
            "quarantine", "vaccine", "who emergency", "health crisis",
        ],
        "label": "Health Crisis",
        "severity_base": 7,
        "icon": "🦠",
    },
}

# ---------------------------------------------------------------------------
# Impact matrix — how each event type historically affects asset classes
# Values: -1.0 (very bearish) to +1.0 (very bullish)
# ---------------------------------------------------------------------------

IMPACT_MATRIX = {
    "WAR_CONFLICT": {
        "Gold":    +0.80,  "Silver":  +0.50,  "Oil":     +0.70,
        "BTC":     +0.30,  "ETH":     +0.20,  "S&P 500": -0.50,
        "NASDAQ":  -0.55,  "Natural Gas": +0.40, "Copper": -0.20,
        "Platinum": +0.30, "Wheat":   +0.50,  "EUR/USD": -0.30,
    },
    "SANCTIONS": {
        "Gold":    +0.50,  "Silver":  +0.30,  "Oil":     +0.60,
        "BTC":     +0.20,  "ETH":     +0.15,  "S&P 500": -0.30,
        "NASDAQ":  -0.25,  "Natural Gas": +0.50, "Copper": -0.10,
        "Platinum": +0.20, "Wheat":   +0.30,  "EUR/USD": -0.20,
    },
    "TARIFFS_TRADE": {
        "Gold":    +0.30,  "Silver":  +0.15,  "Oil":     -0.10,
        "BTC":     +0.10,  "ETH":     +0.05,  "S&P 500": -0.40,
        "NASDAQ":  -0.35,  "Natural Gas": 0.00, "Copper": -0.30,
        "Platinum": -0.15, "Wheat":   +0.20,  "EUR/USD": +0.10,
    },
    "CENTRAL_BANK": {
        # Impact depends on dovish vs hawkish — default is rate CUT (dovish)
        "Gold":    +0.60,  "Silver":  +0.40,  "Oil":     +0.20,
        "BTC":     +0.50,  "ETH":     +0.45,  "S&P 500": +0.40,
        "NASDAQ":  +0.50,  "Natural Gas": +0.10, "Copper": +0.30,
        "Platinum": +0.30, "Wheat":   +0.10,  "EUR/USD": -0.20,
    },
    "ELECTIONS": {
        "Gold":    +0.20,  "Silver":  +0.10,  "Oil":     +0.10,
        "BTC":     +0.15,  "ETH":     +0.10,  "S&P 500": -0.15,
        "NASDAQ":  -0.10,  "Natural Gas": 0.00, "Copper": -0.05,
        "Platinum": 0.00,  "Wheat":   0.00,   "EUR/USD": -0.10,
    },
    "ENERGY_SUPPLY": {
        "Gold":    +0.20,  "Silver":  +0.10,  "Oil":     +0.80,
        "BTC":     0.00,   "ETH":     0.00,   "S&P 500": -0.25,
        "NASDAQ":  -0.15,  "Natural Gas": +0.70, "Copper": -0.10,
        "Platinum": +0.10, "Wheat":   +0.10,  "EUR/USD": -0.10,
    },
    "NATURAL_DISASTER": {
        "Gold":    +0.15,  "Silver":  +0.05,  "Oil":     +0.20,
        "BTC":     0.00,   "ETH":     0.00,   "S&P 500": -0.20,
        "NASDAQ":  -0.15,  "Natural Gas": +0.30, "Copper": -0.10,
        "Platinum": 0.00,  "Wheat":   +0.60,  "EUR/USD": 0.00,
    },
    "PANDEMIC_HEALTH": {
        "Gold":    +0.50,  "Silver":  +0.20,  "Oil":     -0.60,
        "BTC":     +0.30,  "ETH":     +0.25,  "S&P 500": -0.50,
        "NASDAQ":  -0.30,  "Natural Gas": -0.30, "Copper": -0.40,
        "Platinum": -0.30, "Wheat":   +0.20,  "EUR/USD": +0.10,
    },
}

# ---------------------------------------------------------------------------
# Historical precedents for context
# ---------------------------------------------------------------------------

HISTORICAL_PRECEDENTS = {
    "WAR_CONFLICT": [
        {"event": "Russia-Ukraine Invasion (Feb 2022)", "oil": "+25%", "gold": "+8%", "sp500": "-10%"},
        {"event": "US-Iran Soleimani Strike (Jan 2020)", "oil": "+4%", "gold": "+1.5%", "sp500": "-0.7%"},
        {"event": "Gulf War (1990)", "oil": "+130%", "gold": "+7%", "sp500": "-15%"},
        {"event": "Saudi Aramco Attack (Sep 2019)", "oil": "+15%", "gold": "+1%", "sp500": "-0.4%"},
    ],
    "SANCTIONS": [
        {"event": "Russia Sanctions Package (2022)", "oil": "+30%", "gold": "+10%", "natgas": "+60%"},
        {"event": "Iran Nuclear Sanctions (2012)", "oil": "+15%", "gold": "+5%", "sp500": "-3%"},
    ],
    "TARIFFS_TRADE": [
        {"event": "US-China Tariffs Round 1 (2018)", "sp500": "-6%", "gold": "+2%", "copper": "-8%"},
        {"event": "US-China Tariffs Round 2 (2019)", "sp500": "-7%", "gold": "+5%", "copper": "-12%"},
        {"event": "Trump Steel Tariffs (2025)", "gold": "+3%", "sp500": "-2%", "copper": "-4%"},
    ],
    "CENTRAL_BANK": [
        {"event": "Fed Emergency Rate Cut (Mar 2020)", "gold": "+5%", "sp500": "+9%", "btc": "+15%"},
        {"event": "Fed 75bp Hike (Jun 2022)", "gold": "-3%", "sp500": "-6%", "btc": "-15%"},
        {"event": "ECB Rate Cut Cycle (2024)", "gold": "+8%", "eur_usd": "-5%", "sp500": "+4%"},
    ],
    "ENERGY_SUPPLY": [
        {"event": "OPEC+ Production Cut (2023)", "oil": "+8%", "sp500": "-1%", "natgas": "+5%"},
        {"event": "Nord Stream Sabotage (Sep 2022)", "natgas": "+20%", "gold": "+3%", "eur_usd": "-4%"},
    ],
    "NATURAL_DISASTER": [
        {"event": "Japan Earthquake/Tsunami (2011)", "sp500": "-2%", "gold": "+2%", "oil": "-3%"},
        {"event": "Australia Wildfires (2020)", "wheat": "+5%", "sp500": "flat", "gold": "+1%"},
    ],
    "PANDEMIC_HEALTH": [
        {"event": "COVID-19 Crash (Mar 2020)", "sp500": "-35%", "oil": "-65%", "gold": "+10%", "btc": "-40% then +300%"},
    ],
}


# ---------------------------------------------------------------------------
# Main monitor class
# ---------------------------------------------------------------------------

class GeopoliticalMonitor:
    """Detects geopolitical events from news headlines and computes asset impact."""

    def classify_headline(self, headline: str) -> list[dict]:
        """Classify a single headline into geopolitical event categories.

        Returns list of matched categories with confidence scores.
        """
        text = headline.lower()
        matches = []

        for event_type, config in EVENT_KEYWORDS.items():
            keyword_hits = []
            for kw in config["keywords"]:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    keyword_hits.append(kw)

            if keyword_hits:
                # Confidence based on how many keywords matched
                confidence = min(len(keyword_hits) / 3.0, 1.0)
                severity = config["severity_base"] * confidence
                matches.append({
                    "event_type": event_type,
                    "label": config["label"],
                    "icon": config["icon"],
                    "keywords_matched": keyword_hits,
                    "confidence": round(confidence, 2),
                    "severity": round(severity, 1),
                })

        # Sort by severity descending
        matches.sort(key=lambda m: m["severity"], reverse=True)
        return matches

    def analyze(self, news_articles: list[dict]) -> dict:
        """Analyze a collection of news articles for geopolitical events.

        Args:
            news_articles: List of article dicts with 'title', 'source', 'published', 'sentiment' keys.

        Returns:
            Full geopolitical analysis report dict.
        """
        event_counts = {}
        detected_events = []
        geo_articles = []

        for art in news_articles:
            title = art.get("title", "")
            classifications = self.classify_headline(title)
            if classifications:
                top_event = classifications[0]
                event_type = top_event["event_type"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

                geo_articles.append({
                    "title": title,
                    "source": art.get("source", "Unknown"),
                    "published": art.get("published", ""),
                    "sentiment": art.get("sentiment", 0),
                    "event_type": event_type,
                    "event_label": top_event["label"],
                    "event_icon": top_event["icon"],
                    "confidence": top_event["confidence"],
                    "severity": top_event["severity"],
                    "keywords": top_event["keywords_matched"],
                })

        # Determine dominant events (events with 3+ articles)
        dominant_events = {
            etype: count for etype, count in event_counts.items() if count >= 2
        }

        # Compute aggregate asset impact from dominant events
        asset_impact = {}
        for event_type, count in dominant_events.items():
            impact_map = IMPACT_MATRIX.get(event_type, {})
            weight = min(count / 5.0, 1.0)  # More articles = stronger signal, caps at 5
            for asset_name, impact in impact_map.items():
                if asset_name not in asset_impact:
                    asset_impact[asset_name] = {"total_impact": 0.0, "events": []}
                weighted_impact = impact * weight
                asset_impact[asset_name]["total_impact"] += weighted_impact
                asset_impact[asset_name]["events"].append({
                    "event": event_type,
                    "base_impact": impact,
                    "weighted_impact": round(weighted_impact, 3),
                    "article_count": count,
                })

        # Normalize and label
        for asset_name in asset_impact:
            total = asset_impact[asset_name]["total_impact"]
            asset_impact[asset_name]["total_impact"] = round(total, 3)
            if total >= 0.3:
                asset_impact[asset_name]["direction"] = "BULLISH"
            elif total <= -0.3:
                asset_impact[asset_name]["direction"] = "BEARISH"
            else:
                asset_impact[asset_name]["direction"] = "NEUTRAL"

        # Sort geo articles by severity
        geo_articles.sort(key=lambda a: a["severity"], reverse=True)

        # Get relevant historical precedents
        precedents = []
        for event_type in dominant_events:
            if event_type in HISTORICAL_PRECEDENTS:
                precedents.extend(HISTORICAL_PRECEDENTS[event_type])

        # Overall risk level
        total_severity = sum(
            EVENT_KEYWORDS.get(et, {}).get("severity_base", 0) * min(count / 3, 1.0)
            for et, count in dominant_events.items()
        )
        if total_severity >= 12:
            risk_level = "EXTREME"
        elif total_severity >= 8:
            risk_level = "ELEVATED"
        elif total_severity >= 4:
            risk_level = "MODERATE"
        elif total_severity > 0:
            risk_level = "LOW"
        else:
            risk_level = "CALM"

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_articles_scanned": len(news_articles),
            "geopolitical_articles": len(geo_articles),
            "risk_level": risk_level,
            "risk_severity": round(total_severity, 1),
            "event_counts": event_counts,
            "dominant_events": dominant_events,
            "asset_impact": asset_impact,
            "top_events": geo_articles[:20],
            "historical_precedents": precedents,
        }

        # Cache
        GEO_CACHE_FILE.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return report

    def get_scenario(self, event_type: str) -> dict:
        """Get a pre-built scenario for a specific event type."""
        config = EVENT_KEYWORDS.get(event_type, {})
        impacts = IMPACT_MATRIX.get(event_type, {})
        precedents = HISTORICAL_PRECEDENTS.get(event_type, [])

        return {
            "event_type": event_type,
            "label": config.get("label", event_type),
            "icon": config.get("icon", ""),
            "severity_base": config.get("severity_base", 0),
            "asset_impacts": impacts,
            "historical_precedents": precedents,
        }

    def get_all_scenarios(self) -> list[dict]:
        """Get all pre-built geopolitical scenarios."""
        return [self.get_scenario(et) for et in EVENT_KEYWORDS]
