"""News Impact Engine — causal news-to-price reasoning.

Maps news events to per-asset price impacts using existing geopolitical and macro
infrastructure. Generates human-readable causal chains explaining WHY an asset is
moving (e.g., "Military conflict -> safe-haven demand -> Gold rises").

Combines:
- geopolitical_monitor.py  ->  EVENT_KEYWORDS, IMPACT_MATRIX, HISTORICAL_PRECEDENTS
- macro_regime.py          ->  REGIME_MULTIPLIERS (amplifies/dampens by market context)
- news_researcher.py       ->  article data (titles, sentiment, relevance)

Usage:
    from news_impact import NewsImpactEngine
    engine = NewsImpactEngine()
    result = engine.analyze("Gold", news_articles, news_sentiment=0.45)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from geopolitical_monitor import (
    GeopoliticalMonitor,
    EVENT_KEYWORDS,
    IMPACT_MATRIX,
    HISTORICAL_PRECEDENTS,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
NEWS_DIR = DATA_DIR
IMPACT_CACHE_FILE = DATA_DIR / "news_impact.json"
CACHE_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Causal chain templates — (event_type, asset_name) -> human explanation
# ---------------------------------------------------------------------------

CAUSAL_CHAINS: dict[tuple[str, str], str] = {
    # WAR_CONFLICT
    ("WAR_CONFLICT", "Gold"):        "Military conflict \u2192 safe-haven demand surges \u2192 Gold price rises",
    ("WAR_CONFLICT", "Silver"):      "Military conflict \u2192 safe-haven spillover \u2192 Silver follows Gold higher",
    ("WAR_CONFLICT", "Oil"):         "Military conflict \u2192 supply disruption fears \u2192 Oil price spikes",
    ("WAR_CONFLICT", "Natural Gas"): "Military conflict \u2192 energy supply risk \u2192 Natural Gas rises",
    ("WAR_CONFLICT", "BTC"):         "Military conflict \u2192 currency debasement fears \u2192 crypto benefits",
    ("WAR_CONFLICT", "ETH"):         "Military conflict \u2192 risk-off but digital-gold narrative \u2192 ETH mixed",
    ("WAR_CONFLICT", "S&P 500"):     "Military conflict \u2192 risk-off sentiment \u2192 equities sell off",
    ("WAR_CONFLICT", "NASDAQ"):      "Military conflict \u2192 growth stocks hit hardest \u2192 tech sells off",
    ("WAR_CONFLICT", "Wheat"):       "Military conflict \u2192 grain export disruption \u2192 Wheat price surges",
    ("WAR_CONFLICT", "Copper"):      "Military conflict \u2192 industrial demand fears \u2192 Copper falls",
    ("WAR_CONFLICT", "EUR/USD"):     "Military conflict \u2192 flight to dollar safety \u2192 EUR weakens",
    ("WAR_CONFLICT", "Platinum"):    "Military conflict \u2192 safe-haven demand \u2192 Platinum benefits",

    # SANCTIONS
    ("SANCTIONS", "Gold"):           "Sanctions imposed \u2192 central banks diversify reserves \u2192 Gold rises",
    ("SANCTIONS", "Oil"):            "Sanctions \u2192 supply removed from market \u2192 Oil price rises",
    ("SANCTIONS", "Natural Gas"):    "Sanctions \u2192 energy supply squeeze \u2192 Natural Gas spikes",
    ("SANCTIONS", "BTC"):            "Sanctions \u2192 alternative payment channels sought \u2192 crypto interest up",
    ("SANCTIONS", "S&P 500"):        "Sanctions \u2192 global trade friction \u2192 corporate earnings risk",
    ("SANCTIONS", "NASDAQ"):         "Sanctions \u2192 tech supply chain disruption \u2192 NASDAQ weakens",
    ("SANCTIONS", "Wheat"):          "Sanctions \u2192 grain export blocked \u2192 Wheat supply squeeze",
    ("SANCTIONS", "Silver"):         "Sanctions \u2192 safe-haven spillover \u2192 Silver gains",
    ("SANCTIONS", "EUR/USD"):        "Sanctions \u2192 European economy exposed \u2192 EUR weakens",
    ("SANCTIONS", "Copper"):         "Sanctions \u2192 industrial metals supply risk \u2192 mixed impact",

    # TARIFFS_TRADE
    ("TARIFFS_TRADE", "Gold"):       "Trade war escalation \u2192 uncertainty hedge \u2192 Gold gains",
    ("TARIFFS_TRADE", "S&P 500"):    "Trade war escalation \u2192 corporate earnings risk \u2192 stocks fall",
    ("TARIFFS_TRADE", "NASDAQ"):     "Trade war \u2192 tech sector tariff exposure \u2192 NASDAQ drops",
    ("TARIFFS_TRADE", "Copper"):     "Trade war \u2192 global growth slowdown fears \u2192 Copper drops",
    ("TARIFFS_TRADE", "Wheat"):      "Trade war \u2192 agricultural export disruption \u2192 Wheat volatile",
    ("TARIFFS_TRADE", "EUR/USD"):    "Trade war \u2192 dollar strengthens as safe haven \u2192 EUR falls",
    ("TARIFFS_TRADE", "Oil"):        "Trade war \u2192 demand destruction fears \u2192 Oil weakens",
    ("TARIFFS_TRADE", "BTC"):        "Trade war \u2192 fiat uncertainty \u2192 crypto narrative strengthens",

    # CENTRAL_BANK (dovish bias — rate cut / easing)
    ("CENTRAL_BANK", "Gold"):        "Rate cut expectations \u2192 weaker dollar + lower yields \u2192 Gold benefits",
    ("CENTRAL_BANK", "BTC"):         "Dovish Fed \u2192 liquidity flood \u2192 crypto rallies",
    ("CENTRAL_BANK", "ETH"):         "Dovish central bank \u2192 risk appetite returns \u2192 ETH rallies",
    ("CENTRAL_BANK", "S&P 500"):     "Rate cut \u2192 cheaper borrowing \u2192 equities rally",
    ("CENTRAL_BANK", "NASDAQ"):      "Rate cut \u2192 growth stocks repriced higher \u2192 tech surges",
    ("CENTRAL_BANK", "Silver"):      "Rate cut \u2192 precious metals benefit \u2192 Silver rises",
    ("CENTRAL_BANK", "Oil"):         "Rate cut \u2192 economic optimism \u2192 Oil demand expectations rise",
    ("CENTRAL_BANK", "Copper"):      "Rate cut \u2192 growth outlook improves \u2192 industrial metals up",
    ("CENTRAL_BANK", "EUR/USD"):     "Fed cuts vs ECB holds \u2192 dollar weakens \u2192 EUR/USD rises",

    # ENERGY_SUPPLY
    ("ENERGY_SUPPLY", "Oil"):        "OPEC production cut \u2192 lower supply \u2192 Oil price spikes",
    ("ENERGY_SUPPLY", "Natural Gas"): "Pipeline disruption \u2192 supply squeeze \u2192 Natural Gas surges",
    ("ENERGY_SUPPLY", "Gold"):       "Energy crisis \u2192 inflation fears \u2192 Gold rises as hedge",
    ("ENERGY_SUPPLY", "S&P 500"):    "Energy supply shock \u2192 input costs rise \u2192 margins compressed",
    ("ENERGY_SUPPLY", "NASDAQ"):     "Energy crisis \u2192 operating costs up \u2192 tech margins hit",
    ("ENERGY_SUPPLY", "Copper"):     "Energy crisis \u2192 industrial slowdown \u2192 Copper weakens",
    ("ENERGY_SUPPLY", "Wheat"):      "Energy costs up \u2192 farming/transport costs rise \u2192 Wheat up",

    # ELECTIONS
    ("ELECTIONS", "Gold"):           "Political uncertainty \u2192 safe-haven demand \u2192 Gold rises",
    ("ELECTIONS", "S&P 500"):        "Election uncertainty \u2192 policy risk \u2192 equities volatile",
    ("ELECTIONS", "NASDAQ"):         "Election results \u2192 regulatory outlook shift \u2192 tech volatile",
    ("ELECTIONS", "BTC"):            "Political instability \u2192 decentralization narrative \u2192 crypto interest",
    ("ELECTIONS", "EUR/USD"):        "European election uncertainty \u2192 EUR weakens",

    # NATURAL_DISASTER
    ("NATURAL_DISASTER", "Wheat"):   "Natural disaster \u2192 crop destruction \u2192 Wheat price surges",
    ("NATURAL_DISASTER", "Oil"):     "Disaster hits refinery region \u2192 supply disruption \u2192 Oil spikes",
    ("NATURAL_DISASTER", "Natural Gas"): "Disaster \u2192 infrastructure damage \u2192 Gas supply disrupted",
    ("NATURAL_DISASTER", "Gold"):    "Disaster \u2192 economic disruption fears \u2192 Gold rises",
    ("NATURAL_DISASTER", "S&P 500"): "Natural disaster \u2192 economic damage \u2192 equities fall",
    ("NATURAL_DISASTER", "Copper"):  "Disaster \u2192 construction demand or supply disruption \u2192 mixed",

    # PANDEMIC_HEALTH
    ("PANDEMIC_HEALTH", "Gold"):     "Health crisis \u2192 flight to safety \u2192 Gold surges",
    ("PANDEMIC_HEALTH", "Oil"):      "Pandemic \u2192 travel shutdown \u2192 Oil demand collapses",
    ("PANDEMIC_HEALTH", "S&P 500"):  "Pandemic fears \u2192 economic shutdown risk \u2192 equities crash",
    ("PANDEMIC_HEALTH", "NASDAQ"):   "Pandemic \u2192 initial crash then WFH tech boom \u2192 volatile",
    ("PANDEMIC_HEALTH", "BTC"):      "Pandemic \u2192 money printing response \u2192 crypto benefits long-term",
    ("PANDEMIC_HEALTH", "Copper"):   "Pandemic \u2192 industrial shutdown \u2192 Copper demand collapses",
    ("PANDEMIC_HEALTH", "Natural Gas"): "Pandemic \u2192 reduced commercial demand \u2192 Gas falls",
}

# Generic fallback template per event type
_GENERIC_CHAINS: dict[str, str] = {
    "WAR_CONFLICT":    "Military conflict \u2192 market uncertainty \u2192 {asset} {dir}",
    "SANCTIONS":       "Sanctions imposed \u2192 trade disruption \u2192 {asset} {dir}",
    "TARIFFS_TRADE":   "Trade war \u2192 economic friction \u2192 {asset} {dir}",
    "CENTRAL_BANK":    "Monetary policy shift \u2192 liquidity change \u2192 {asset} {dir}",
    "ELECTIONS":       "Political uncertainty \u2192 market volatility \u2192 {asset} {dir}",
    "ENERGY_SUPPLY":   "Energy supply disruption \u2192 price pressure \u2192 {asset} {dir}",
    "NATURAL_DISASTER": "Natural disaster \u2192 supply disruption \u2192 {asset} {dir}",
    "PANDEMIC_HEALTH": "Health crisis \u2192 demand shock \u2192 {asset} {dir}",
}

# Impact label thresholds
_IMPACT_LABELS = [
    (60,  "STRONG TAILWIND"),
    (20,  "TAILWIND"),
    (-20, "NEUTRAL"),
    (-60, "HEADWIND"),
    (-100, "STRONG HEADWIND"),
]

# Driver summary templates
_DRIVER_TEMPLATES = {
    "WAR_CONFLICT":    "military tensions",
    "SANCTIONS":       "sanctions activity",
    "TARIFFS_TRADE":   "trade war developments",
    "CENTRAL_BANK":    "central bank policy signals",
    "ELECTIONS":       "political/election events",
    "ENERGY_SUPPLY":   "energy supply disruptions",
    "NATURAL_DISASTER": "natural disaster impacts",
    "PANDEMIC_HEALTH": "health crisis concerns",
}


def _get_impact_label(score: float) -> str:
    """Convert numeric impact score to human label."""
    for threshold, label in _IMPACT_LABELS:
        if score >= threshold:
            return label
    return "STRONG HEADWIND"


def _load_cache() -> dict:
    """Load cached impact analysis."""
    if IMPACT_CACHE_FILE.exists():
        try:
            return json.loads(IMPACT_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    """Persist impact cache."""
    try:
        IMPACT_CACHE_FILE.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _load_news_for_asset(asset_name: str) -> list[dict]:
    """Load cached news articles for an asset."""
    safe = asset_name.lower().replace("/", "_").replace("\\", "_").replace(" ", "_").replace("&", "&")
    candidates = [
        NEWS_DIR / f"news_{safe}.json",
        NEWS_DIR / f"news_{asset_name.lower().replace(' ', '_')}.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                articles = data if isinstance(data, list) else data.get("articles", [])
                return articles
            except Exception:
                continue
    return []


def _load_regime() -> dict:
    """Load cached macro regime data."""
    regime_file = DATA_DIR / "macro_regime.json"
    if regime_file.exists():
        try:
            return json.loads(regime_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class NewsImpactEngine:
    """Maps news events to per-asset price impacts with causal reasoning."""

    def __init__(self):
        self._geo = GeopoliticalMonitor()

    def analyze(
        self,
        asset_name: str,
        news_data: Optional[dict] = None,
        news_sentiment: float = 0.0,
    ) -> dict:
        """Run full impact analysis for a single asset.

        Args:
            asset_name: Asset name (e.g., "Gold", "Oil", "S&P 500").
            news_data: News research dict from news_researcher (has sentiment_score, articles, etc.).
            news_sentiment: Fallback sentiment score if news_data not provided.

        Returns:
            Impact analysis dict with score, chains, summary, etc.
        """
        # Check cache first
        cache = _load_cache()
        cached = cache.get(asset_name)
        if cached and time.time() - cached.get("_cache_ts", 0) < CACHE_TTL:
            return cached

        # Gather articles
        articles = _load_news_for_asset(asset_name)
        sentiment = news_sentiment
        if news_data:
            sentiment = news_data.get("sentiment_score", news_sentiment)

        # Step 1: Classify all articles into event types
        event_articles: dict[str, list[dict]] = {}
        event_counts: dict[str, int] = {}

        for art in articles:
            title = art.get("title", "")
            if not title:
                continue
            classifications = self._geo.classify_headline(title)
            if classifications:
                top = classifications[0]
                etype = top["event_type"]
                event_counts[etype] = event_counts.get(etype, 0) + 1
                if etype not in event_articles:
                    event_articles[etype] = []
                event_articles[etype].append({
                    "title": title,
                    "event_type": etype,
                    "confidence": top["confidence"],
                    "severity": top["severity"],
                })

        # Step 2: Per-asset impact calculation using IMPACT_MATRIX
        regime_data = _load_regime()
        regime_name = regime_data.get("regime", "NEUTRAL")

        # Get regime multiplier for this asset
        try:
            from macro_regime import REGIME_MULTIPLIERS
            regime_mult = REGIME_MULTIPLIERS.get(regime_name, {}).get(asset_name, 1.0)
            regime_desc = REGIME_MULTIPLIERS.get(regime_name, {}).get("description", "")
        except ImportError:
            regime_mult = 1.0
            regime_desc = ""

        # Calculate weighted impact per event type
        impact_components: list[dict] = []
        raw_impact = 0.0

        for etype, count in event_counts.items():
            base_impact = IMPACT_MATRIX.get(etype, {}).get(asset_name, 0.0)
            if base_impact == 0.0:
                continue

            # Strength: more articles = more conviction (caps at 5 articles)
            strength = min(count / 5.0, 1.0)
            weighted = base_impact * strength * regime_mult
            raw_impact += weighted

            # Get causal chain
            chain_key = (etype, asset_name)
            if chain_key in CAUSAL_CHAINS:
                chain_text = CAUSAL_CHAINS[chain_key]
            else:
                direction = "rises" if base_impact > 0 else "falls"
                template = _GENERIC_CHAINS.get(etype, "{asset} affected by event")
                chain_text = template.format(asset=asset_name, dir=direction)

            # Get historical precedent
            precedent = None
            precs = HISTORICAL_PRECEDENTS.get(etype, [])
            if precs:
                precedent = precs[0].get("event", "")
                # Extract relevant asset moves from precedent
                prec_data = precs[0]
                asset_key_map = {
                    "Gold": "gold", "Oil": "oil", "S&P 500": "sp500",
                    "NASDAQ": "sp500", "Natural Gas": "natgas", "BTC": "btc",
                    "Wheat": "wheat", "EUR/USD": "eur_usd",
                }
                ak = asset_key_map.get(asset_name, asset_name.lower())
                move = prec_data.get(ak)
                if move:
                    precedent = f"{precedent} \u2192 {asset_name} {move}"

            impact_components.append({
                "event_type": etype,
                "event_label": EVENT_KEYWORDS.get(etype, {}).get("label", etype),
                "event_icon": EVENT_KEYWORDS.get(etype, {}).get("icon", ""),
                "chain": chain_text,
                "base_impact": base_impact,
                "article_count": count,
                "strength": round(strength, 2),
                "regime_multiplier": regime_mult,
                "weighted_impact": round(weighted, 3),
                "precedent": precedent,
            })

        # Sort by absolute weighted impact (strongest driver first)
        impact_components.sort(key=lambda c: abs(c["weighted_impact"]), reverse=True)

        # Step 3: Compute net impact score (-100 to +100)
        # raw_impact is typically -2.0 to +2.0 range, scale to -100..+100
        net_score = max(-100, min(100, round(raw_impact * 60)))

        # Blend with news sentiment (60% impact, 40% sentiment)
        blended_score = round(net_score * 0.6 + (sentiment * 100) * 0.4)
        blended_score = max(-100, min(100, blended_score))

        # Step 4: Generate labels and summary
        impact_label = _get_impact_label(blended_score)

        if blended_score > 0:
            direction = "BULLISH"
        elif blended_score < 0:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Build driver summary
        driver_summary = ""
        if impact_components:
            top = impact_components[0]
            driver_desc = _DRIVER_TEMPLATES.get(top["event_type"], "macro events")
            article_info = f"({top['article_count']} article{'s' if top['article_count'] != 1 else ''})"
            direction_word = "higher" if top["weighted_impact"] > 0 else "lower"

            driver_summary = (
                f"{asset_name} is being driven {direction_word} by "
                f"{driver_desc} {article_info}."
            )
            if top.get("precedent"):
                driver_summary += f" Historical: {top['precedent']}."
        else:
            driver_summary = f"No significant macro drivers detected for {asset_name}."

        # Regime context
        regime_context = ""
        if regime_name != "NEUTRAL" and regime_desc:
            pct_change = round((regime_mult - 1.0) * 100)
            amp_word = "amplifies" if pct_change > 0 else "dampens"
            regime_context = (
                f"{regime_name.replace('_', ' ').title()} regime "
                f"{amp_word} {asset_name} signals ({pct_change:+d}%)"
            )

        result = {
            "impact_score": blended_score,
            "impact_label": impact_label,
            "direction": direction,
            "causal_chains": impact_components[:5],  # top 5 drivers
            "driver_summary": driver_summary,
            "regime_context": regime_context,
            "regime_name": regime_name,
            "regime_multiplier": regime_mult,
            "events_detected": event_counts,
            "total_geo_articles": sum(event_counts.values()),
            "news_sentiment": round(sentiment, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Cache
        result["_cache_ts"] = time.time()
        cache[asset_name] = result
        _save_cache(cache)

        return result

    def analyze_all(self, asset_names: list[str], news_data_map: Optional[dict] = None) -> dict:
        """Run impact analysis for multiple assets.

        Args:
            asset_names: List of asset names.
            news_data_map: Optional dict mapping asset_name -> news_data dict.

        Returns:
            Dict mapping asset_name -> impact analysis dict.
        """
        results = {}
        for name in asset_names:
            nd = (news_data_map or {}).get(name)
            try:
                results[name] = self.analyze(name, news_data=nd)
            except Exception:
                continue
        return results
