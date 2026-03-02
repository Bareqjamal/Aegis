"""Signal Explainer — LLM-powered narrative explanations for trading signals.

Generates Bloomberg-style plain-English explanations for each signal,
combining technical analysis, news sentiment, social sentiment, macro regime,
and geopolitical context into a coherent story.

Supports two modes:
1. LLM mode (OpenAI/Anthropic) — rich narrative explanations
2. Template mode (fallback) — rule-based sentence generation (no API needed)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Cache directory
_CACHE_DIR = Path(__file__).parent / "data"
_CACHE_FILE = _CACHE_DIR / "signal_explanations.json"
_CACHE_TTL = 1800  # 30 minutes


def _load_cache() -> dict:
    """Load explanation cache from disk."""
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    """Persist explanation cache."""
    try:
        _CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


def _is_cached(cache: dict, asset_name: str) -> Optional[str]:
    """Return cached explanation if still valid."""
    entry = cache.get(asset_name, {})
    if not entry:
        return None
    ts = entry.get("timestamp", 0)
    if time.time() - ts < _CACHE_TTL:
        return entry.get("explanation", "")
    return None


def generate_template_explanation(
    asset_name: str,
    signal: str,
    score: float,
    confidence: float,
    price: float,
    rsi: float,
    target: float,
    stop_loss: float,
    news_sentiment: str = "NEUTRAL",
    social_score: float = 0.0,
    social_buzz: str = "LOW",
    regime: str = "NEUTRAL",
    geo_risk: str = "LOW",
    reasoning: str = "",
) -> str:
    """Generate a template-based explanation (no LLM needed).

    Returns a 2-3 sentence Bloomberg-style narrative.
    """
    parts = []

    # Opening: What is the signal?
    if signal in ("STRONG BUY", "BUY"):
        strength = "strongly" if signal == "STRONG BUY" else ""
        parts.append(
            f"{asset_name} is {strength} bullish at ${price:,.2f} "
            f"with a confidence of {confidence:.0f}%."
        )
    elif signal in ("STRONG SELL", "SELL"):
        strength = "strongly" if signal == "STRONG SELL" else ""
        parts.append(
            f"{asset_name} is {strength} bearish at ${price:,.2f} "
            f"with a confidence of {confidence:.0f}%."
        )
    else:
        parts.append(
            f"{asset_name} shows mixed signals at ${price:,.2f} "
            f"with {confidence:.0f}% confidence."
        )

    # Technical context
    tech_parts = []
    if rsi < 30:
        tech_parts.append(f"RSI at {rsi:.0f} indicates oversold conditions")
    elif rsi > 70:
        tech_parts.append(f"RSI at {rsi:.0f} signals overbought territory")
    elif rsi < 45:
        tech_parts.append(f"RSI at {rsi:.0f} leans bearish")
    elif rsi > 55:
        tech_parts.append(f"RSI at {rsi:.0f} leans bullish")

    if score > 50:
        tech_parts.append("technical indicators are aligned bullish")
    elif score < -50:
        tech_parts.append("technical indicators are aligned bearish")
    elif abs(score) < 20:
        tech_parts.append("technical indicators are mixed")

    if tech_parts:
        parts.append(" ".join(t.capitalize() if i == 0 else t for i, t in enumerate(tech_parts)) + ".")

    # News + Social context
    context_parts = []
    if news_sentiment == "BULLISH":
        context_parts.append("news flow is positive")
    elif news_sentiment == "BEARISH":
        context_parts.append("news sentiment is negative")

    if social_score > 0.15:
        context_parts.append("social media is bullish")
    elif social_score < -0.15:
        context_parts.append("social media is bearish")

    if social_buzz == "HIGH":
        context_parts.append("with elevated social buzz")

    if context_parts:
        parts.append(", ".join(context_parts).capitalize() + ".")

    # Macro + Geo context
    if regime not in ("NEUTRAL", "UNKNOWN"):
        regime_desc = {
            "RISK_ON": "Risk-on macro environment supports growth assets",
            "RISK_OFF": "Risk-off conditions favor safe-haven assets",
            "INFLATIONARY": "Inflationary pressure favors commodities and hard assets",
            "DEFLATIONARY": "Deflationary signals favor bonds and defensive plays",
            "HIGH_VOLATILITY": "High market volatility calls for smaller position sizes",
        }.get(regime, "")
        if regime_desc:
            parts.append(regime_desc + ".")

    if geo_risk in ("EXTREME", "ELEVATED"):
        parts.append(f"Geopolitical risk is {geo_risk.lower()}, adding uncertainty.")

    # Target/SL
    if target and stop_loss and price > 0:
        upside = ((target - price) / price * 100) if target > price else 0
        downside = ((price - stop_loss) / price * 100) if stop_loss < price else 0
        if upside > 0 and downside > 0:
            parts.append(
                f"Target ${target:,.0f} ({upside:+.1f}%), "
                f"stop-loss ${stop_loss:,.0f} ({-downside:.1f}%)."
            )

    return " ".join(parts).replace("  ", " ").strip()


def generate_llm_explanation(
    asset_name: str,
    signal: str,
    score: float,
    confidence: float,
    price: float,
    rsi: float,
    target: float,
    stop_loss: float,
    news_sentiment: str = "NEUTRAL",
    social_score: float = 0.0,
    social_buzz: str = "LOW",
    regime: str = "NEUTRAL",
    geo_risk: str = "LOW",
    reasoning: str = "",
) -> Optional[str]:
    """Generate LLM-powered explanation using OpenAI or Anthropic API.

    Returns None if no API key is configured.
    """
    # Try OpenAI first
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not openai_key and not anthropic_key:
        return None

    prompt = (
        f"You are a Bloomberg Terminal analyst. Write a concise 2-3 sentence "
        f"market analysis for {asset_name}.\n\n"
        f"Current data:\n"
        f"- Signal: {signal} (score: {score:.0f}/100)\n"
        f"- Price: ${price:,.2f}\n"
        f"- Confidence: {confidence:.0f}%\n"
        f"- RSI: {rsi:.0f}\n"
        f"- Target: ${target:,.0f} | Stop-Loss: ${stop_loss:,.0f}\n"
        f"- News: {news_sentiment}\n"
        f"- Social sentiment: {social_score:+.2f} (buzz: {social_buzz})\n"
        f"- Macro regime: {regime}\n"
        f"- Geopolitical risk: {geo_risk}\n"
        f"- AI reasoning: {reasoning}\n\n"
        f"Write a professional, actionable 2-3 sentence analysis. "
        f"Include the key driver (what's making this signal bullish/bearish). "
        f"Mention the risk. Be specific with numbers."
    )

    try:
        if openai_key:
            import requests
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()

        if anthropic_key and not openai_key:
            import requests
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["content"][0]["text"].strip()
    except Exception:
        return None

    return None


def explain_signal(
    asset_name: str,
    signal: str,
    score: float = 0,
    confidence: float = 0,
    price: float = 0,
    rsi: float = 50,
    target: float = 0,
    stop_loss: float = 0,
    news_sentiment: str = "NEUTRAL",
    social_score: float = 0.0,
    social_buzz: str = "LOW",
    regime: str = "NEUTRAL",
    geo_risk: str = "LOW",
    reasoning: str = "",
    use_llm: bool = True,
) -> str:
    """Generate a signal explanation — tries LLM first, falls back to template.

    Args:
        use_llm: If True, attempt LLM generation. Falls back to template if no API key.

    Returns:
        2-3 sentence narrative explanation.
    """
    # Check cache
    cache = _load_cache()
    cached = _is_cached(cache, asset_name)
    if cached:
        return cached

    kwargs = dict(
        asset_name=asset_name, signal=signal, score=score, confidence=confidence,
        price=price, rsi=rsi, target=target, stop_loss=stop_loss,
        news_sentiment=news_sentiment, social_score=social_score,
        social_buzz=social_buzz, regime=regime, geo_risk=geo_risk,
        reasoning=reasoning,
    )

    explanation = None
    if use_llm:
        explanation = generate_llm_explanation(**kwargs)

    if not explanation:
        explanation = generate_template_explanation(**kwargs)

    # Cache result
    cache[asset_name] = {
        "explanation": explanation,
        "timestamp": time.time(),
        "source": "llm" if (use_llm and explanation != generate_template_explanation(**kwargs)) else "template",
    }
    _save_cache(cache)

    return explanation


def explain_all_signals(watchlist_summary: dict, regime: str = "NEUTRAL", geo_risk: str = "LOW") -> dict:
    """Generate explanations for all assets in the watchlist.

    Returns dict: {asset_name: explanation_string}
    """
    results = {}
    for name, data in watchlist_summary.items():
        conf = data.get("confidence", {})
        conf_pct = conf.get("confidence_pct", 0) if isinstance(conf, dict) else 0
        results[name] = explain_signal(
            asset_name=name,
            signal=data.get("signal_label", "NEUTRAL"),
            score=data.get("signal_score", 0),
            confidence=conf_pct,
            price=data.get("price", 0),
            rsi=data.get("rsi", 50),
            target=data.get("target", 0),
            stop_loss=data.get("stop_loss", 0),
            news_sentiment=data.get("news_sentiment", "NEUTRAL"),
            regime=regime,
            geo_risk=geo_risk,
            reasoning=data.get("reasoning_short", ""),
        )
    return results
