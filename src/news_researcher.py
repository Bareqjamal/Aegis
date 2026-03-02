"""News Research Agent v2 — fetches from newspapers, financial media, and social feeds.

Sources:
- yfinance ticker news
- Financial: CNBC, MarketWatch, Reuters, Bloomberg, Financial Times, WSJ
- Newspapers: NYT, BBC, The Guardian
- Crypto: CoinDesk, CoinTelegraph
- Commodities: Kitco
- Social: Google News (as X/Twitter proxy — real-time trending)

Usage:
    from news_researcher import NewsResearcher
    researcher = NewsResearcher()
    report = researcher.research("Gold", "GC=F")
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
import yfinance as yf

try:
    from config import NewsConfig
    RSS_TIMEOUT = NewsConfig.RSS_TIMEOUT_SECONDS
    MAX_ARTICLES = NewsConfig.MAX_ARTICLES_PER_FEED
except ImportError:
    RSS_TIMEOUT = 8
    MAX_ARTICLES = 12

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
NEWS_CACHE_DIR = PROJECT_ROOT / "src" / "data"
NEWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [NewsResearcher] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Sentiment keyword scoring
# ---------------------------------------------------------------------------

# Weighted sentiment: (keyword, weight). Higher weight = stronger signal.
# Weight 1.0 = mild, 2.0 = moderate, 3.0 = strong
BULLISH_WORDS_WEIGHTED = [
    # Strong bullish (3.0)
    ("surge", 3.0), ("soar", 3.0), ("skyrocket", 3.0), ("all-time high", 3.0),
    ("ath", 3.0), ("breakout", 3.0), ("boom", 3.0), ("strong buy", 3.0),
    # Moderate bullish (2.0)
    ("rally", 2.0), ("jump", 2.0), ("bull", 2.0), ("record", 2.0),
    ("outperform", 2.0), ("beat", 2.0), ("upgrade", 2.0), ("accumulation", 2.0),
    ("inflows", 2.0), ("dovish", 2.0), ("rate cut", 2.0), ("easing", 2.0),
    ("safe haven", 2.0), ("institutional", 2.0), ("adoption", 2.0),
    ("recover", 2.0), ("rebound", 2.0),
    # Mild bullish (1.0)
    ("gain", 1.0), ("up", 1.0), ("high", 1.0), ("buy", 1.0), ("optimistic", 1.0),
    ("positive", 1.0), ("growth", 1.0), ("strong", 1.0), ("rise", 1.0),
    ("climbs", 1.0), ("advances", 1.0), ("momentum", 1.0), ("demand", 1.0),
    ("green", 1.0), ("profit", 1.0), ("revenue", 1.0), ("innovation", 1.0),
    ("partnership", 1.0), ("support", 1.0),
]

BEARISH_WORDS_WEIGHTED = [
    # Strong bearish (3.0)
    ("crash", 3.0), ("plunge", 3.0), ("collapse", 3.0), ("panic", 3.0),
    ("bankruptcy", 3.0), ("default", 3.0), ("crisis", 3.0), ("selloff", 3.0),
    ("sell-off", 3.0), ("liquidation", 3.0), ("recession", 3.0),
    # Moderate bearish (2.0)
    ("bear", 2.0), ("dump", 2.0), ("fear", 2.0), ("warning", 2.0),
    ("correction", 2.0), ("bubble", 2.0), ("outflow", 2.0), ("hawkish", 2.0),
    ("rate hike", 2.0), ("tightening", 2.0), ("overvalued", 2.0),
    ("slump", 2.0), ("tumble", 2.0), ("layoff", 2.0), ("sanction", 2.0),
    ("tariff", 2.0), ("war", 2.0), ("shutdown", 2.0),
    # Mild bearish (1.0)
    ("drop", 1.0), ("fall", 1.0), ("down", 1.0), ("low", 1.0), ("decline", 1.0),
    ("sell", 1.0), ("weak", 1.0), ("loss", 1.0), ("risk", 1.0),
    ("resistance", 1.0), ("inflation", 1.0),
]

# Flat lists kept for backward compatibility
BULLISH_WORDS = [w for w, _ in BULLISH_WORDS_WEIGHTED]
BEARISH_WORDS = [w for w, _ in BEARISH_WORDS_WEIGHTED]

# Negation words that flip sentiment (only pure negators, not verbs)
NEGATION_WORDS = ["not", "no", "never", "neither", "without", "unlikely",
                  "unable", "don't", "doesn't", "didn't", "won't", "can't",
                  "cannot", "hardly", "barely", "nor"]

# Words that are bearish on their own (not negators)
FAILURE_WORDS_BEARISH = [
    ("fail", 2.0), ("failed", 2.0), ("fails", 2.0), ("failing", 2.0),
    ("halt", 1.5), ("halts", 1.5), ("halted", 1.5),
    ("stall", 1.5), ("stalls", 1.5), ("stalled", 1.5),
    ("reject", 1.5), ("rejected", 1.5), ("rejects", 1.5),
]

def _keyword_match(text: str, keyword: str) -> bool:
    """Check if keyword appears in text at a word boundary (avoids false positives)."""
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))


def _has_negation_before(text: str, keyword: str) -> bool:
    """Check if a negation word appears within 3 words before the keyword."""
    text_lower = text.lower()
    kw_pos = text_lower.find(keyword.lower())
    if kw_pos < 0:
        return False
    # Get the 30 chars before the keyword
    prefix = text_lower[max(0, kw_pos - 30):kw_pos]
    words = prefix.split()
    # Check last 3 words for negation
    check_words = words[-3:] if len(words) >= 3 else words
    return any(neg in check_words for neg in NEGATION_WORDS)


def score_headline(headline: str) -> float:
    """Score a headline from -1.0 (very bearish) to +1.0 (very bullish).

    Uses weighted keywords and negation detection for improved accuracy.
    """
    text = headline.lower()
    bull_score = 0.0
    bear_score = 0.0

    for word, weight in BULLISH_WORDS_WEIGHTED:
        if _keyword_match(text, word):
            if _has_negation_before(text, word):
                bear_score += weight * 0.5  # Negated bullish = mild bearish
            else:
                bull_score += weight

    for word, weight in BEARISH_WORDS_WEIGHTED:
        if _keyword_match(text, word):
            if _has_negation_before(text, word):
                bull_score += weight * 0.5  # Negated bearish = mild bullish
            else:
                bear_score += weight

    # Failure words are always bearish (never used as negators)
    for word, weight in FAILURE_WORDS_BEARISH:
        if _keyword_match(text, word):
            bear_score += weight

    total = bull_score + bear_score
    if total == 0:
        return 0.0
    # Normalize to [-1.0, 1.0]
    raw = (bull_score - bear_score) / total
    return round(max(-1.0, min(1.0, raw)), 2)


# ---------------------------------------------------------------------------
# Asset keyword mapping for filtering relevant news
# ---------------------------------------------------------------------------

ASSET_KEYWORDS = {
    # ── Original 12 assets ──
    "Gold": ["gold", "xau", "precious metal", "bullion", "safe haven", "gc=f", "goldpreis"],
    "BTC": ["bitcoin", "btc", "crypto", "cryptocurrency", "satoshi", "halving", "digital asset"],
    "ETH": ["ethereum", "eth", "ether", "defi", "layer 2", "staking", "smart contract"],
    "Silver": ["silver", "xag", "precious metal", "si=f", "industrial metal"],
    "Oil": ["oil", "crude", "wti", "brent", "opec", "petroleum", "barrel", "cl=f", "energy"],
    "NatGas": ["natural gas", "lng", "gas prices", "ng=f", "henry hub"],
    "SP500": ["s&p 500", "s&p500", "sp500", "spy", "wall street", "stock market", "equities"],
    "NASDAQ": ["nasdaq", "tech stocks", "qqq", "big tech", "growth stocks", "silicon valley"],
    "Copper": ["copper", "hg=f", "base metal", "industrial metal"],
    "Platinum": ["platinum", "pl=f", "pgm", "catalytic"],
    "Wheat": ["wheat", "grain", "zw=f", "crop", "agriculture"],
    "EUR_USD": ["eur/usd", "eurusd", "euro", "dollar", "forex", "currency", "ecb"],
    # ── US Stocks (20) ──
    "Apple": ["apple", "aapl", "iphone", "tim cook", "mac", "app store"],
    "Microsoft": ["microsoft", "msft", "azure", "satya nadella", "windows", "copilot"],
    "NVIDIA": ["nvidia", "nvda", "jensen huang", "gpu", "cuda", "ai chip"],
    "Google": ["google", "googl", "alphabet", "sundar pichai", "youtube", "search"],
    "Amazon": ["amazon", "amzn", "andy jassy", "aws", "prime", "e-commerce"],
    "Meta": ["meta", "meta platforms", "facebook", "zuckerberg", "instagram", "whatsapp"],
    "Tesla": ["tesla", "tsla", "elon musk", "ev", "electric vehicle", "cybertruck"],
    "JPMorgan": ["jpmorgan", "jpm", "jamie dimon", "chase", "investment bank"],
    "Berkshire": ["berkshire", "brk", "warren buffett", "charlie munger", "omaha"],
    "UnitedHealth": ["unitedhealth", "unh", "optum", "health insurance", "managed care"],
    "Visa": ["visa", "visa inc", "payment network", "card network"],
    "Johnson & Johnson": ["johnson & johnson", "jnj", "j&j", "pharma", "medical devices"],
    "Walmart": ["walmart", "wmt", "retail", "doug mcmillon", "sam walton"],
    "Mastercard": ["mastercard", "ma", "payment processing", "card network"],
    "ExxonMobil": ["exxonmobil", "exxon", "xom", "oil major", "upstream", "refinery"],
    "AMD": ["amd", "advanced micro devices", "lisa su", "ryzen", "epyc", "radeon"],
    "Netflix": ["netflix", "nflx", "streaming", "subscriber", "ted sarandos"],
    "Intel": ["intel", "intc", "pat gelsinger", "semiconductor", "foundry", "x86"],
    "Coca-Cola": ["coca-cola", "coke", "ko", "beverage", "soft drink"],
    "Disney": ["disney", "dis", "bob iger", "disney+", "theme park", "pixar"],
    # ── Crypto (8) ──
    "Solana": ["solana", "sol", "sol-usd", "solana blockchain", "sol token"],
    "XRP": ["xrp", "ripple", "xrp-usd", "ripple labs", "cross-border payment"],
    "Dogecoin": ["dogecoin", "doge", "doge-usd", "meme coin", "shiba"],
    "Cardano": ["cardano", "ada", "ada-usd", "charles hoskinson", "ouroboros"],
    "Avalanche": ["avalanche", "avax", "avax-usd", "avax blockchain", "subnet"],
    "Chainlink": ["chainlink", "link", "link-usd", "oracle", "sergey nazarov"],
    "Polkadot": ["polkadot", "dot", "dot-usd", "parachain", "gavin wood"],
    "Litecoin": ["litecoin", "ltc", "ltc-usd", "digital silver", "charlie lee"],
    # ── Commodities (2) ──
    "Palladium": ["palladium", "pa=f", "pgm", "catalytic converter", "precious metal"],
    "Corn": ["corn", "zc=f", "maize", "grain", "agriculture", "ethanol"],
    # ── Indices (2) ──
    "Dow_Jones": ["dow jones", "dow", "djia", "dji", "blue chip", "industrial average"],
    "Russell_2000": ["russell 2000", "russell", "rut", "small cap", "iwm"],
    # ── Forex (4) ──
    "GBP_USD": ["gbp/usd", "gbpusd", "pound", "sterling", "bank of england", "boe"],
    "USD_JPY": ["usd/jpy", "usdjpy", "yen", "bank of japan", "boj", "japanese yen"],
    "AUD_USD": ["aud/usd", "audusd", "australian dollar", "aussie", "rba"],
    "USD_CHF": ["usd/chf", "usdchf", "swiss franc", "snb", "swissie"],
}

def is_relevant(headline: str, asset: str) -> bool:
    """Check if a headline is relevant to the given asset."""
    text = headline.lower()
    keywords = ASSET_KEYWORDS.get(asset, [asset.lower()])
    return any(_keyword_match(text, kw) for kw in keywords)


# ---------------------------------------------------------------------------
# News sources — financial media, newspapers, social, crypto, commodities
# ---------------------------------------------------------------------------

RSS_FEEDS = {
    # ── Financial Media ──
    "financial": [
        ("CNBC Markets", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
        ("MarketWatch Top", "https://feeds.marketwatch.com/marketwatch/topstories/"),
        ("MarketWatch Markets", "https://feeds.marketwatch.com/marketwatch/marketpulse/"),
        ("Reuters Business", "https://www.reutersagency.com/feed/?best-topics=business-finance"),
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ("Investing.com", "https://www.investing.com/rss/news.rss"),
    ],
    # ── Major Newspapers ──
    "newspapers": [
        ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
        ("NYT Economy", "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml"),
        ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("The Guardian Business", "https://www.theguardian.com/uk/business/rss"),
        ("Financial Times", "https://www.ft.com/rss/home"),
        ("WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
        ("WSJ World", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ],
    # ── Social/Trending (Google News = real-time proxy for X/Twitter trends) ──
    "social_trending": [
        ("Google News Business", "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB"),
        ("Google News Markets", "https://news.google.com/rss/search?q=stock+market+today&hl=en-US&gl=US&ceid=US:en"),
        ("Google News Crypto", "https://news.google.com/rss/search?q=cryptocurrency+bitcoin+ethereum&hl=en-US&gl=US&ceid=US:en"),
        ("Google News Gold", "https://news.google.com/rss/search?q=gold+price+today&hl=en-US&gl=US&ceid=US:en"),
        ("Reddit Finance (via Google)", "https://news.google.com/rss/search?q=site:reddit.com+wallstreetbets+OR+investing&hl=en-US&gl=US&ceid=US:en"),
    ],
    # ── Crypto-specific ──
    "crypto": [
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("CoinTelegraph", "https://cointelegraph.com/rss"),
        ("The Block", "https://www.theblock.co/rss.xml"),
        ("Decrypt", "https://decrypt.co/feed"),
    ],
    # ── Commodities ──
    "commodities": [
        ("Kitco Gold", "https://www.kitco.com/rss/gold.xml"),
        ("Kitco Silver", "https://www.kitco.com/rss/silver.xml"),
        ("Oilprice.com", "https://oilprice.com/rss/main"),
    ],
    # ── Central Banks & Macro ──
    "macro": [
        ("Fed RSS", "https://www.federalreserve.gov/feeds/press_all.xml"),
        ("ECB Press", "https://www.ecb.europa.eu/rss/press.html"),
        ("IMF News", "https://www.imf.org/en/News/rss"),
    ],
}

# Which feed categories to use per asset type
ASSET_FEED_MAP = {
    # ── Original 12 assets ──
    "Gold": ["financial", "newspapers", "social_trending", "commodities", "macro"],
    "Silver": ["financial", "newspapers", "commodities", "macro"],
    "BTC": ["financial", "newspapers", "social_trending", "crypto"],
    "ETH": ["financial", "newspapers", "social_trending", "crypto"],
    "Oil": ["financial", "newspapers", "commodities", "macro"],
    "NatGas": ["financial", "commodities", "macro"],
    "SP500": ["financial", "newspapers", "social_trending", "macro"],
    "NASDAQ": ["financial", "newspapers", "social_trending", "macro"],
    "Copper": ["financial", "commodities"],
    "Platinum": ["financial", "commodities"],
    "Wheat": ["financial", "commodities"],
    "EUR_USD": ["financial", "newspapers", "macro"],
    # ── US Stocks (20) ──
    "Apple": ["financial", "newspapers"],
    "Microsoft": ["financial", "newspapers"],
    "NVIDIA": ["financial", "newspapers"],
    "Google": ["financial", "newspapers"],
    "Amazon": ["financial", "newspapers"],
    "Meta": ["financial", "newspapers"],
    "Tesla": ["financial", "newspapers"],
    "JPMorgan": ["financial", "newspapers"],
    "Berkshire": ["financial", "newspapers"],
    "UnitedHealth": ["financial", "newspapers"],
    "Visa": ["financial", "newspapers"],
    "Johnson & Johnson": ["financial", "newspapers"],
    "Walmart": ["financial", "newspapers"],
    "Mastercard": ["financial", "newspapers"],
    "ExxonMobil": ["financial", "newspapers"],
    "AMD": ["financial", "newspapers"],
    "Netflix": ["financial", "newspapers"],
    "Intel": ["financial", "newspapers"],
    "Coca-Cola": ["financial", "newspapers"],
    "Disney": ["financial", "newspapers"],
    # ── Crypto (8) ──
    "Solana": ["crypto", "social_trending"],
    "XRP": ["crypto", "social_trending"],
    "Dogecoin": ["crypto", "social_trending"],
    "Cardano": ["crypto", "social_trending"],
    "Avalanche": ["crypto", "social_trending"],
    "Chainlink": ["crypto", "social_trending"],
    "Polkadot": ["crypto", "social_trending"],
    "Litecoin": ["crypto", "social_trending"],
    # ── Commodities (2) ──
    "Palladium": ["financial", "commodities"],
    "Corn": ["financial", "commodities"],
    # ── Indices (2) ──
    "Dow_Jones": ["financial", "newspapers", "macro"],
    "Russell_2000": ["financial", "newspapers"],
    # ── Forex (4) ──
    "GBP_USD": ["financial", "newspapers", "macro"],
    "USD_JPY": ["financial", "newspapers", "macro"],
    "AUD_USD": ["financial", "newspapers", "macro"],
    "USD_CHF": ["financial", "newspapers", "macro"],
}


def _fetch_rss(url: str, timeout: int = RSS_TIMEOUT) -> list[dict]:
    """Fetch and parse an RSS feed, return list of article dicts."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Aegis-Scanner/2.0"
        })
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries[:MAX_ARTICLES]:  # limit per feed
            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            elif hasattr(entry, "updated"):
                published = entry.updated
            articles.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": published,
                "source": feed.feed.get("title", "Unknown")[:50],
            })
        return articles
    except Exception as e:
        log(f"WARNING: RSS fetch failed ({url[:60]}): {e}")
        return []


def _fetch_yfinance_news(ticker: str) -> list[dict]:
    """Fetch news from yfinance for a specific ticker."""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        articles = []
        for item in news[:10]:
            title = item.get("title", "")
            link = item.get("link", "")
            publisher = item.get("publisher", "Unknown")
            pub_time = item.get("providerPublishTime", 0)
            published = ""
            if pub_time:
                published = datetime.fromtimestamp(pub_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            articles.append({
                "title": title,
                "link": link,
                "published": published,
                "source": publisher,
            })
        return articles
    except Exception as e:
        log(f"yfinance news failed ({ticker}): {e}")
        return []


# ---------------------------------------------------------------------------
# Main researcher class
# ---------------------------------------------------------------------------

class NewsResearcher:
    """Fetches, filters, and scores news for a given asset."""

    def research(self, asset_name: str, ticker: str) -> dict:
        """Run a full news research cycle for one asset.

        Returns:
            {
                "asset": str,
                "ticker": str,
                "timestamp": str,
                "sentiment_score": float,
                "sentiment_label": str,
                "article_count": int,
                "relevant_count": int,
                "sources_checked": int,
                "articles": [...],
                "top_bullish": [...],
                "top_bearish": [...],
                "summary": str,
            }
        """
        log(f"Researching news for {asset_name} ({ticker})...")
        all_articles = []
        sources_checked = 0

        # 1. yfinance built-in news (most reliable)
        yf_news = _fetch_yfinance_news(ticker)
        all_articles.extend(yf_news)
        sources_checked += 1

        # 2. RSS feeds — select categories for this asset
        failed_feeds = []
        feed_categories = ASSET_FEED_MAP.get(asset_name, ["financial", "newspapers"])
        for category in feed_categories:
            feeds = RSS_FEEDS.get(category, [])
            for feed_name, feed_url in feeds:
                try:
                    rss_articles = _fetch_rss(feed_url)
                    if rss_articles:
                        # Tag source category
                        for art in rss_articles:
                            art["feed_category"] = category
                        all_articles.extend(rss_articles)
                except Exception as e:
                    failed_feeds.append(feed_name)
                    log(f"RSS feed failed: {feed_name} ({feed_url}): {e}")
                sources_checked += 1

        if failed_feeds:
            log(f"Warning: {len(failed_feeds)} feed(s) failed: {', '.join(failed_feeds)}")

        # 3. Score and filter
        seen_titles = set()
        scored_articles = []
        for art in all_articles:
            title = art["title"].strip()
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())

            sentiment = score_headline(title)
            relevant = is_relevant(title, asset_name)
            scored_articles.append({
                **art,
                "sentiment": sentiment,
                "relevant": relevant,
            })

        # Sort: relevant first, then by absolute sentiment
        scored_articles.sort(key=lambda a: (a["relevant"], abs(a["sentiment"])), reverse=True)

        # 4. Compute aggregate sentiment (only from relevant articles)
        relevant_articles = [a for a in scored_articles if a["relevant"]]
        if relevant_articles:
            avg_sentiment = sum(a["sentiment"] for a in relevant_articles) / len(relevant_articles)
            avg_sentiment = round(avg_sentiment, 2)
            if avg_sentiment >= 0.2:
                sentiment_label = "BULLISH"
            elif avg_sentiment <= -0.2:
                sentiment_label = "BEARISH"
            else:
                sentiment_label = "NEUTRAL"
        else:
            avg_sentiment = 0.0
            sentiment_label = "UNKNOWN"

        # 5. Top headlines
        top_bullish = sorted(
            [a for a in scored_articles if a["sentiment"] > 0],
            key=lambda a: a["sentiment"], reverse=True
        )[:5]
        top_bearish = sorted(
            [a for a in scored_articles if a["sentiment"] < 0],
            key=lambda a: a["sentiment"]
        )[:5]

        # 6. Source breakdown
        source_counts = {}
        for art in scored_articles:
            cat = art.get("feed_category", "yfinance")
            source_counts[cat] = source_counts.get(cat, 0) + 1

        # 7. Social sentiment overlay (if available)
        social_score = 0.0
        social_label = "N/A"
        social_alerts = []
        try:
            from social_sentiment import SocialSentimentEngine
            _social_cached = SocialSentimentEngine.load_cached()
            if _social_cached:
                _asset_social = _social_cached.get("asset_scores", {}).get(asset_name, {})
                social_score = _asset_social.get("social_score", 0.0)
                social_label = _asset_social.get("social_label", "N/A")
                # Merge social alerts for this asset
                for _alert in _social_cached.get("alerts", []):
                    if _alert.get("asset") == asset_name:
                        social_alerts.append(_alert)
        except ImportError:
            pass

        # 8. Blended sentiment: news 70% + social 30% (when social data available)
        if social_label != "N/A" and social_score != 0.0:
            blended = avg_sentiment * 0.7 + social_score * 0.3
            blended = round(max(-1.0, min(1.0, blended)), 2)
        else:
            blended = avg_sentiment

        # Recalculate label based on blended score
        if blended >= 0.2:
            blended_label = "BULLISH"
        elif blended <= -0.2:
            blended_label = "BEARISH"
        else:
            blended_label = "NEUTRAL"

        # 9. Summary
        n_relevant = len(relevant_articles)
        _social_note = f" Social: {social_label} ({social_score:+.2f})." if social_label != "N/A" else ""
        summary = (
            f"Scanned {sources_checked} sources, found {len(scored_articles)} articles "
            f"({n_relevant} relevant) for {asset_name}. "
            f"News: {sentiment_label} ({avg_sentiment:+.2f}).{_social_note} "
            f"Blended: {blended_label} ({blended:+.2f}). "
            f"{len(top_bullish)} bullish, {len(top_bearish)} bearish."
        )

        result = {
            "asset": asset_name,
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sentiment_score": blended,
            "news_sentiment": avg_sentiment,
            "social_sentiment": social_score,
            "social_label": social_label,
            "sentiment_label": blended_label,
            "article_count": len(scored_articles),
            "relevant_count": n_relevant,
            "sources_checked": sources_checked,
            "source_breakdown": source_counts,
            "articles": scored_articles[:30],  # cap at 30
            "top_bullish": top_bullish,
            "top_bearish": top_bearish,
            "social_alerts": social_alerts,
            "failed_feeds": failed_feeds,
            "summary": summary,
        }

        # Cache result
        # Sanitize asset name for filesystem (e.g., "EUR/USD" -> "eur_usd")
        _safe_name = asset_name.lower().replace("/", "_").replace("\\", "_").replace(" ", "_")
        cache_path = NEWS_CACHE_DIR / f"news_{_safe_name}.json"
        cache_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"News research complete: {sources_checked} sources, {n_relevant} relevant articles, sentiment={avg_sentiment:+.2f} ({sentiment_label})")

        return result

    def research_all(self, watchlist: dict) -> dict[str, dict]:
        """Research news for all assets in the watchlist."""
        results = {}
        for name, config in watchlist.items():
            try:
                results[name] = self.research(name, config["ticker"])
            except Exception as e:
                log(f"ERROR researching {name}: {e}")
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    researcher = NewsResearcher()

    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from market_scanner import WATCHLIST

    results = researcher.research_all(WATCHLIST)
    for name, data in results.items():
        print(f"\n{'='*60}")
        print(f"  {name}: {data['sentiment_label']} ({data['sentiment_score']:+.2f})")
        print(f"  {data['sources_checked']} sources, {data['relevant_count']} relevant / {data['article_count']} total")
        print(f"  Sources: {data.get('source_breakdown', {})}")
        print(f"{'='*60}")
        for art in data["articles"][:8]:
            tag = "+" if art["sentiment"] > 0 else "-" if art["sentiment"] < 0 else "~"
            rel = "*" if art["relevant"] else " "
            src = art.get("source", "?")[:20]
            print(f"  [{tag}][{rel}] {art['title'][:65]}")
            print(f"       {src} | {art.get('published', '')[:20]}")
