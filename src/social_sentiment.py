"""Social Sentiment Engine — Tracks influencers, Reddit, and social buzz.

Monitors real-time social sources for market-moving signals:
- Influencer tracking (Trump, Elon Musk, Michael Saylor, etc.) via Google News
- Reddit: r/wallstreetbets, r/CryptoCurrency, r/stocks, r/investing
- StockTwits trending (via RSS fallback)
- Buzz velocity: how fast mentions are accelerating

No paid API keys required. All free sources.

Usage:
    from social_sentiment import SocialSentimentEngine
    engine = SocialSentimentEngine()
    report = engine.scan_all()
"""

import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import feedparser
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
CACHE_DIR = PROJECT_ROOT / "src" / "data"
SOCIAL_CACHE = CACHE_DIR / "social_sentiment.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Aegis-Terminal/3.0"
}
REQUEST_TIMEOUT = 10


def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [SocialSentiment] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Influencer Configuration
# ---------------------------------------------------------------------------

# Key market-moving individuals and what assets they affect
INFLUENCERS = {
    "Donald Trump": {
        "search_names": ["Trump", "Donald Trump", "POTUS"],
        "affects": {
            "BTC": 3.0,        # Very high impact on crypto
            "ETH": 2.0,
            "SP500": 2.5,      # Tariffs, policy
            "NASDAQ": 2.5,
            "Gold": 2.0,       # Safe haven during uncertainty
            "Oil": 1.5,        # Energy policy
            "EUR_USD": 1.5,    # Trade war / dollar policy
        },
        "keywords_bullish": ["pro-crypto", "bitcoin reserve", "strategic reserve",
                             "tax cut", "deregulation", "digital asset", "innovation"],
        "keywords_bearish": ["tariff", "trade war", "ban", "sanction", "restrict",
                             "executive order against", "crackdown"],
    },
    "Elon Musk": {
        "search_names": ["Elon Musk", "Musk"],
        "affects": {
            "BTC": 2.5,
            "ETH": 1.5,
            "NASDAQ": 2.0,     # Tesla, tech
            "SP500": 1.0,
        },
        "keywords_bullish": ["bitcoin", "doge", "accepts crypto", "buy", "support",
                             "ai", "innovation", "growth"],
        "keywords_bearish": ["sell", "dump", "suspend", "pause", "scam",
                             "overvalued", "bubble"],
    },
    "Michael Saylor": {
        "search_names": ["Michael Saylor", "Saylor", "MicroStrategy"],
        "affects": {
            "BTC": 3.0,       # Saylor = BTC maximalist
            "ETH": 0.5,
        },
        "keywords_bullish": ["buy", "purchase", "acquire", "accumulate", "hodl",
                             "billion", "treasury", "strategy"],
        "keywords_bearish": ["sell", "liquidate", "margin call", "debt"],
    },
    "Jerome Powell": {
        "search_names": ["Jerome Powell", "Fed Chair Powell", "Powell"],
        "affects": {
            "Gold": 3.0,
            "SP500": 2.5,
            "NASDAQ": 2.5,
            "BTC": 2.0,
            "EUR_USD": 2.0,
            "Silver": 2.0,
            "Oil": 1.5,
        },
        "keywords_bullish": ["rate cut", "dovish", "pause", "easing", "support",
                             "patient", "gradual"],
        "keywords_bearish": ["rate hike", "hawkish", "inflation persistent",
                             "tightening", "restrictive", "higher for longer"],
    },
    "Janet Yellen": {
        "search_names": ["Janet Yellen", "Treasury Secretary Yellen"],
        "affects": {
            "Gold": 2.0,
            "SP500": 2.0,
            "EUR_USD": 1.5,
        },
        "keywords_bullish": ["strong economy", "growth", "stable"],
        "keywords_bearish": ["debt ceiling", "default", "recession risk", "crisis"],
    },
    "Larry Fink": {
        "search_names": ["Larry Fink", "BlackRock"],
        "affects": {
            "BTC": 2.5,       # BlackRock BTC ETF
            "ETH": 2.0,
            "SP500": 1.5,
            "Gold": 1.0,
        },
        "keywords_bullish": ["etf", "approval", "institutional", "allocate",
                             "bullish", "opportunity"],
        "keywords_bearish": ["risk", "overheated", "bubble", "concern"],
    },
}

# ---------------------------------------------------------------------------
# Reddit Configuration
# ---------------------------------------------------------------------------

REDDIT_SUBS = {
    "wallstreetbets": {
        "url": "https://www.reddit.com/r/wallstreetbets/hot.json?limit=25",
        "assets": ["SP500", "NASDAQ", "BTC", "Gold",
                   "Apple", "Microsoft", "NVIDIA", "Google", "Amazon", "Meta",
                   "Tesla", "JPMorgan", "Berkshire", "UnitedHealth", "Visa",
                   "Johnson & Johnson", "Walmart", "Mastercard", "ExxonMobil",
                   "AMD", "Netflix", "Intel", "Coca-Cola", "Disney"],
        "weight": 2.0,   # WSB has high meme energy but real impact
    },
    "CryptoCurrency": {
        "url": "https://www.reddit.com/r/CryptoCurrency/hot.json?limit=25",
        "assets": ["BTC", "ETH", "Solana", "XRP", "Dogecoin", "Cardano",
                   "Avalanche", "Chainlink", "Polkadot", "Litecoin"],
        "weight": 1.5,
    },
    "stocks": {
        "url": "https://www.reddit.com/r/stocks/hot.json?limit=20",
        "assets": ["SP500", "NASDAQ",
                   "Apple", "Microsoft", "NVIDIA", "Google", "Amazon", "Meta",
                   "Tesla", "JPMorgan", "Berkshire", "UnitedHealth", "Visa",
                   "Johnson & Johnson", "Walmart", "Mastercard", "ExxonMobil",
                   "AMD", "Netflix", "Intel", "Coca-Cola", "Disney"],
        "weight": 1.0,
    },
    "investing": {
        "url": "https://www.reddit.com/r/investing/hot.json?limit=20",
        "assets": ["SP500", "NASDAQ", "Dow_Jones", "Russell_2000",
                   "Apple", "Microsoft", "NVIDIA", "Google", "Amazon", "Meta",
                   "Tesla", "JPMorgan", "Berkshire", "UnitedHealth", "Visa",
                   "Johnson & Johnson", "Walmart", "Mastercard", "ExxonMobil",
                   "AMD", "Netflix", "Intel", "Coca-Cola", "Disney",
                   "Gold", "Oil"],
        "weight": 1.0,
    },
    "Gold": {
        "url": "https://www.reddit.com/r/Gold/hot.json?limit=15",
        "assets": ["Gold", "Silver"],
        "weight": 1.5,
    },
    "Bitcoin": {
        "url": "https://www.reddit.com/r/Bitcoin/hot.json?limit=20",
        "assets": ["BTC"],
        "weight": 1.5,
    },
    "ethereum": {
        "url": "https://www.reddit.com/r/ethereum/hot.json?limit=15",
        "assets": ["ETH"],
        "weight": 1.5,
    },
    "Commodities": {
        "url": "https://www.reddit.com/r/Commodities/hot.json?limit=15",
        "assets": ["Gold", "Silver", "Oil", "Copper", "Wheat", "Platinum",
                   "Palladium", "Corn", "Natural Gas"],
        "weight": 1.0,
    },
    "technology": {
        "url": "https://www.reddit.com/r/technology/hot.json?limit=20",
        "assets": ["Apple", "Microsoft", "NVIDIA", "Google", "Amazon", "Meta",
                   "Tesla", "AMD", "Netflix", "Intel"],
        "weight": 1.0,
    },
    "solana": {
        "url": "https://www.reddit.com/r/solana/hot.json?limit=15",
        "assets": ["Solana"],
        "weight": 1.5,
    },
    "dogecoin": {
        "url": "https://www.reddit.com/r/dogecoin/hot.json?limit=15",
        "assets": ["Dogecoin"],
        "weight": 1.5,
    },
}

# Asset mention patterns for Reddit title scanning
ASSET_MENTION_PATTERNS = {
    # ── Original 12 assets ──
    "BTC": [r"\bbitcoin\b", r"\bbtc\b", r"\bcrypto\b", r"\bsatoshi\b"],
    "ETH": [r"\bethereum\b", r"\beth\b", r"\bether\b", r"\bdefi\b"],
    "Gold": [r"\bgold\b", r"\bxau\b", r"\bbullion\b", r"\bprecious\s*metal"],
    "Silver": [r"\bsilver\b", r"\bxag\b"],
    "Oil": [r"\boil\b", r"\bcrude\b", r"\bwti\b", r"\bbrent\b", r"\bopec\b"],
    "SP500": [r"\bs&?p\s*500\b", r"\bspy\b", r"\bstock\s*market\b", r"\bwall\s*street\b"],
    "NASDAQ": [r"\bnasdaq\b", r"\bqqq\b", r"\btech\s*stocks?\b", r"\bbig\s*tech\b"],
    "Copper": [r"\bcopper\b"],
    "Wheat": [r"\bwheat\b", r"\bgrain\b"],
    "Platinum": [r"\bplatinum\b"],
    "EUR_USD": [r"\beur/?usd\b", r"\beuro\b.*\bdollar\b", r"\bforex\b"],
    "Natural Gas": [r"\bnatural\s*gas\b", r"\blng\b"],
    # ── US Stocks (20) ──
    "Apple": [r"\bapple\b", r"\baapl\b", r"\biphone\b", r"\btim\s*cook\b"],
    "Microsoft": [r"\bmicrosoft\b", r"\bmsft\b", r"\bazure\b", r"\bnadella\b"],
    "NVIDIA": [r"\bnvidia\b", r"\bnvda\b", r"\bjensen\s*huang\b", r"\bgpu\b"],
    "Google": [r"\bgoogle\b", r"\bgoogl\b", r"\balphabet\b", r"\byoutube\b"],
    "Amazon": [r"\bamazon\b", r"\bamzn\b", r"\baws\b", r"\bjassy\b"],
    "Meta": [r"\bmeta\b", r"\bfacebook\b", r"\bzuckerberg\b", r"\binstagram\b"],
    "Tesla": [r"\btesla\b", r"\btsla\b", r"\bmusk\b", r"\bcybertruck\b"],
    "JPMorgan": [r"\bjpmorgan\b", r"\bjpm\b", r"\bjamie\s*dimon\b", r"\bchase\b"],
    "Berkshire": [r"\bberkshire\b", r"\bbrk\b", r"\bbuffett\b"],
    "UnitedHealth": [r"\bunitedhealth\b", r"\bunh\b", r"\boptum\b"],
    "Visa": [r"\bvisa\b"],
    "Johnson & Johnson": [r"\bjohnson\s*&?\s*johnson\b", r"\bjnj\b", r"\bj&j\b"],
    "Walmart": [r"\bwalmart\b", r"\bwmt\b"],
    "Mastercard": [r"\bmastercard\b"],
    "ExxonMobil": [r"\bexxon\b", r"\bxom\b", r"\bexxonmobil\b"],
    "AMD": [r"\bamd\b", r"\blisa\s*su\b", r"\bryzen\b", r"\bepyc\b"],
    "Netflix": [r"\bnetflix\b", r"\bnflx\b", r"\bstreaming\b"],
    "Intel": [r"\bintel\b", r"\bintc\b", r"\bgelsinger\b"],
    "Coca-Cola": [r"\bcoca[\-\s]?cola\b", r"\bcoke\b"],
    "Disney": [r"\bdisney\b", r"\bdis\b", r"\bbob\s*iger\b"],
    # ── Crypto (8) ──
    "Solana": [r"\bsolana\b", r"\bsol\b"],
    "XRP": [r"\bxrp\b", r"\bripple\b"],
    "Dogecoin": [r"\bdogecoin\b", r"\bdoge\b"],
    "Cardano": [r"\bcardano\b", r"\bada\b"],
    "Avalanche": [r"\bavalanche\b", r"\bavax\b"],
    "Chainlink": [r"\bchainlink\b", r"\blink\b"],
    "Polkadot": [r"\bpolkadot\b", r"\bdot\b"],
    "Litecoin": [r"\blitecoin\b", r"\bltc\b"],
    # ── Commodities (2) ──
    "Palladium": [r"\bpalladium\b"],
    "Corn": [r"\bcorn\b", r"\bmaize\b"],
    # ── Indices (2) ──
    "Dow_Jones": [r"\bdow\s*jones\b", r"\bdjia\b", r"\bdow\b"],
    "Russell_2000": [r"\brussell\s*2000\b", r"\biwm\b", r"\bsmall\s*cap\b"],
    # ── Forex (4) ──
    "GBP_USD": [r"\bgbp/?usd\b", r"\bpound\b", r"\bsterling\b"],
    "USD_JPY": [r"\busd/?jpy\b", r"\byen\b", r"\bjapanese\s*yen\b"],
    "AUD_USD": [r"\baud/?usd\b", r"\baustralian\s*dollar\b", r"\baussie\b"],
    "USD_CHF": [r"\busd/?chf\b", r"\bswiss\s*franc\b"],
}


# ---------------------------------------------------------------------------
# Sentiment scoring (reuse from news_researcher but lighter)
# ---------------------------------------------------------------------------

SOCIAL_BULLISH = [
    ("moon", 3.0), ("rocket", 3.0), ("🚀", 3.0), ("diamond hands", 3.0),
    ("ath", 3.0), ("all time high", 3.0), ("breakout", 3.0), ("bullish", 3.0),
    ("to the moon", 3.0), ("rally", 2.0), ("buy", 2.0), ("long", 2.0),
    ("pump", 2.0), ("green", 1.5), ("calls", 1.5), ("yolo", 1.5),
    ("undervalued", 2.0), ("accumulate", 2.0), ("hold", 1.0), ("hodl", 1.5),
    ("gain", 1.0), ("up", 0.5), ("bull", 1.5), ("surge", 2.5),
]

SOCIAL_BEARISH = [
    ("crash", 3.0), ("dump", 3.0), ("sell", 2.0), ("short", 2.0),
    ("puts", 2.0), ("bear", 2.0), ("dead", 2.5), ("rug pull", 3.0),
    ("scam", 3.0), ("ponzi", 3.0), ("overvalued", 2.0), ("bubble", 2.5),
    ("red", 1.0), ("pain", 1.5), ("rekt", 2.0), ("loss", 1.5),
    ("fear", 2.0), ("panic", 2.5), ("capitulation", 3.0), ("bagholding", 2.0),
    ("paper hands", 1.5), ("plunge", 2.5), ("collapse", 3.0),
]


def _score_social_text(text: str) -> float:
    """Score social media text from -1.0 to +1.0.

    Uses word-boundary matching (regex \\b) to avoid false positives
    like 'up' matching 'setup' or 'update'.
    """
    import re
    text_lower = text.lower()
    bull_score = 0.0
    bear_score = 0.0

    for word, weight in SOCIAL_BULLISH:
        # Emoji and special chars: use substring match; regular words: use word boundary
        if len(word) <= 2 or not word.isascii():
            if word in text_lower:
                bull_score += weight
        else:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                bull_score += weight

    for word, weight in SOCIAL_BEARISH:
        if len(word) <= 2 or not word.isascii():
            if word in text_lower:
                bear_score += weight
        else:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                bear_score += weight

    total = bull_score + bear_score
    if total == 0:
        return 0.0
    raw = (bull_score - bear_score) / total
    return round(max(-1.0, min(1.0, raw)), 2)


def _mentions_asset(text: str, asset: str) -> bool:
    """Check if text mentions a specific asset."""
    patterns = ASSET_MENTION_PATTERNS.get(asset, [])
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def fetch_influencer_news(influencer_name: str, config: dict) -> list[dict]:
    """Fetch recent news mentioning an influencer via Google News RSS."""
    articles = []
    for search_name in config["search_names"][:2]:  # Limit to avoid rate limiting
        query = search_name.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en&when=7d"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:8]:
                title = entry.get("title", "")
                published = getattr(entry, "published", "")
                articles.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": published,
                    "source": "Google News",
                    "influencer": influencer_name,
                    "sentiment": _score_social_text(title),
                })
        except Exception as e:
            log(f"Failed to fetch news for {influencer_name}: {e}")
        time.sleep(1.5)  # Google News rate limit: ~30 req/min safe

    return articles


def fetch_reddit_posts(subreddit: str, config: dict) -> list[dict]:
    """Fetch hot posts from a subreddit using Reddit's JSON API."""
    try:
        resp = requests.get(
            config["url"],
            timeout=REQUEST_TIMEOUT,
            headers={**HEADERS, "Accept": "application/json"},
        )
        if resp.status_code != 200:
            log(f"Reddit r/{subreddit} returned {resp.status_code}")
            return []

        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)
            created_utc = post.get("created_utc", 0)

            # Engagement weight: high-upvote posts matter more
            engagement = min(score / 100, 5.0) if score > 0 else 0.5

            posts.append({
                "title": title,
                "subreddit": subreddit,
                "score": score,
                "comments": num_comments,
                "created_utc": created_utc,
                "created": datetime.fromtimestamp(created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if created_utc else "",
                "sentiment": _score_social_text(title),
                "engagement": engagement,
                "permalink": f"https://reddit.com{post.get('permalink', '')}",
            })

        return posts
    except Exception as e:
        log(f"Reddit r/{subreddit} fetch failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class SocialSentimentEngine:
    """Aggregate social sentiment from influencers, Reddit, and trends."""

    def scan_influencers(self) -> dict:
        """Scan all influencers for recent market-moving statements.

        Returns:
            {
                "influencer_name": {
                    "articles": [...],
                    "sentiment": float,
                    "impact": {asset: impact_score},
                    "alert_level": "HIGH" | "MEDIUM" | "LOW" | "NONE",
                    "summary": str,
                }
            }
        """
        log("Scanning influencers...")
        results = {}

        for name, config in INFLUENCERS.items():
            articles = fetch_influencer_news(name, config)
            if not articles:
                results[name] = {
                    "articles": [],
                    "sentiment": 0.0,
                    "impact": {},
                    "alert_level": "NONE",
                    "summary": f"No recent news for {name}",
                }
                continue

            # Score articles and detect which assets are affected
            asset_impacts = {}
            avg_sent = sum(a["sentiment"] for a in articles) / len(articles) if articles else 0.0

            # Check for influencer-specific keywords
            bull_kw_hits = 0
            bear_kw_hits = 0
            for art in articles:
                title_lower = art["title"].lower()
                for kw in config.get("keywords_bullish", []):
                    if kw.lower() in title_lower:
                        bull_kw_hits += 1
                for kw in config.get("keywords_bearish", []):
                    if kw.lower() in title_lower:
                        bear_kw_hits += 1

            # Calculate asset-specific impact
            for asset, base_weight in config["affects"].items():
                # Impact = base_weight * sentiment magnitude * article count factor
                article_factor = min(len(articles) / 3, 2.0)  # More articles = more relevant
                impact = avg_sent * base_weight * article_factor

                # Boost if influencer-specific keywords found
                if bull_kw_hits > 0:
                    impact += 0.2 * bull_kw_hits * base_weight
                if bear_kw_hits > 0:
                    impact -= 0.2 * bear_kw_hits * base_weight

                asset_impacts[asset] = round(max(-5.0, min(5.0, impact)), 2)

            # Alert level based on activity volume and sentiment extremes
            max_impact = max(abs(v) for v in asset_impacts.values()) if asset_impacts else 0
            if max_impact >= 3.0 or len(articles) >= 8:
                alert_level = "HIGH"
            elif max_impact >= 1.5 or len(articles) >= 4:
                alert_level = "MEDIUM"
            elif len(articles) >= 1:
                alert_level = "LOW"
            else:
                alert_level = "NONE"

            # Summary
            top_headline = articles[0]["title"][:100] if articles else ""
            kw_note = ""
            if bull_kw_hits:
                kw_note += f" | {bull_kw_hits} bullish keyword(s)"
            if bear_kw_hits:
                kw_note += f" | {bear_kw_hits} bearish keyword(s)"

            results[name] = {
                "articles": articles[:10],
                "sentiment": round(avg_sent, 2),
                "impact": asset_impacts,
                "alert_level": alert_level,
                "bull_keywords": bull_kw_hits,
                "bear_keywords": bear_kw_hits,
                "summary": f"{len(articles)} articles, sentiment={avg_sent:+.2f}{kw_note}. Latest: {top_headline}",
            }

            log(f"  {name}: {len(articles)} articles, sent={avg_sent:+.2f}, alert={alert_level}")

        return results

    def scan_reddit(self) -> dict:
        """Scan Reddit for social sentiment.

        Returns:
            {
                "subreddit_name": {
                    "posts": [...],
                    "sentiment": float,
                    "buzz_score": float,
                    "asset_mentions": {asset: count},
                    "top_posts": [...],
                }
            }
        """
        log("Scanning Reddit...")
        results = {}

        for sub_name, config in REDDIT_SUBS.items():
            posts = fetch_reddit_posts(sub_name, config)
            if not posts:
                results[sub_name] = {
                    "posts": [],
                    "sentiment": 0.0,
                    "buzz_score": 0.0,
                    "asset_mentions": {},
                    "top_posts": [],
                }
                continue

            # Count asset mentions across post titles
            asset_mentions = {}
            for post in posts:
                for asset in ASSET_MENTION_PATTERNS:
                    if _mentions_asset(post["title"], asset):
                        asset_mentions[asset] = asset_mentions.get(asset, 0) + 1

            # Weighted sentiment (high-engagement posts count more)
            total_weight = sum(p["engagement"] for p in posts) or 1.0
            weighted_sent = sum(p["sentiment"] * p["engagement"] for p in posts) / total_weight

            # Buzz score: combination of total engagement and post count
            total_score = sum(p["score"] for p in posts)
            total_comments = sum(p["comments"] for p in posts)
            buzz_score = round(min(10.0, (total_score / 500 + total_comments / 200 + len(posts) / 5)), 1)

            # Top posts by engagement
            top_posts = sorted(posts, key=lambda p: p["score"], reverse=True)[:5]

            results[sub_name] = {
                "posts": posts,
                "sentiment": round(weighted_sent, 2),
                "buzz_score": buzz_score,
                "asset_mentions": asset_mentions,
                "top_posts": top_posts,
                "total_upvotes": total_score,
                "total_comments": total_comments,
            }

            log(f"  r/{sub_name}: {len(posts)} posts, sent={weighted_sent:+.2f}, buzz={buzz_score}")
            time.sleep(1.0)  # Reddit: 60 req/min safe limit

        return results

    def compute_social_scores(self, influencer_data: dict, reddit_data: dict) -> dict:
        """Aggregate social data into per-asset social sentiment scores.

        Returns:
            {
                asset_name: {
                    "social_score": float (-1.0 to 1.0),
                    "social_label": "VERY_BULLISH" | "BULLISH" | "NEUTRAL" | "BEARISH" | "VERY_BEARISH",
                    "buzz_level": "HIGH" | "MEDIUM" | "LOW",
                    "influencer_signals": [...],
                    "reddit_mentions": int,
                    "top_social_headlines": [...],
                }
            }
        """
        assets = list(ASSET_MENTION_PATTERNS.keys())
        scores = {}

        for asset in assets:
            # Influencer contribution
            inf_impacts = []
            inf_signals = []
            for inf_name, inf_data in influencer_data.items():
                impact = inf_data.get("impact", {}).get(asset, 0)
                if abs(impact) > 0.1:
                    inf_impacts.append(impact)
                    inf_signals.append({
                        "influencer": inf_name,
                        "impact": impact,
                        "alert_level": inf_data["alert_level"],
                        "sentiment": inf_data["sentiment"],
                    })

            # Reddit contribution
            reddit_mentions = 0
            reddit_sentiments = []
            reddit_headlines = []
            for sub_name, sub_data in reddit_data.items():
                mentions = sub_data.get("asset_mentions", {}).get(asset, 0)
                reddit_mentions += mentions
                if mentions > 0:
                    sub_weight = REDDIT_SUBS.get(sub_name, {}).get("weight", 1.0)
                    reddit_sentiments.append(sub_data["sentiment"] * sub_weight * (mentions / 3))
                    for post in sub_data.get("top_posts", []):
                        if _mentions_asset(post["title"], asset):
                            reddit_headlines.append({
                                "title": post["title"][:120],
                                "subreddit": sub_name,
                                "score": post["score"],
                                "sentiment": post["sentiment"],
                            })

            # Combine: influencer signals (60%) + Reddit buzz (40%)
            inf_score = sum(inf_impacts) / max(len(inf_impacts), 1) if inf_impacts else 0
            reddit_score = sum(reddit_sentiments) / max(len(reddit_sentiments), 1) if reddit_sentiments else 0

            # Normalize each to [-1, 1]
            inf_score = max(-1.0, min(1.0, inf_score / 3))
            reddit_score = max(-1.0, min(1.0, reddit_score / 2))

            # Weighted combination
            if inf_impacts and reddit_sentiments:
                social_score = inf_score * 0.6 + reddit_score * 0.4
            elif inf_impacts:
                social_score = inf_score
            elif reddit_sentiments:
                social_score = reddit_score
            else:
                social_score = 0.0

            social_score = round(max(-1.0, min(1.0, social_score)), 2)

            # Label
            if social_score >= 0.4:
                label = "VERY_BULLISH"
            elif social_score >= 0.15:
                label = "BULLISH"
            elif social_score <= -0.4:
                label = "VERY_BEARISH"
            elif social_score <= -0.15:
                label = "BEARISH"
            else:
                label = "NEUTRAL"

            # Buzz level
            total_buzz = reddit_mentions + len(inf_impacts) * 3
            if total_buzz >= 15:
                buzz = "HIGH"
            elif total_buzz >= 5:
                buzz = "MEDIUM"
            else:
                buzz = "LOW"

            # Sort reddit headlines by score
            reddit_headlines.sort(key=lambda x: x["score"], reverse=True)

            scores[asset] = {
                "social_score": social_score,
                "social_label": label,
                "buzz_level": buzz,
                "influencer_signals": inf_signals,
                "reddit_mentions": reddit_mentions,
                "reddit_sentiment": round(reddit_score, 2),
                "influencer_score": round(inf_score, 2),
                "top_social_headlines": reddit_headlines[:5],
            }

        return scores

    def scan_all(self) -> dict:
        """Run a full social sentiment scan.

        Returns:
            {
                "timestamp": str,
                "influencers": {...},
                "reddit": {...},
                "asset_scores": {...},
                "alerts": [...],
                "summary": str,
            }
        """
        log("=== SOCIAL SENTIMENT SCAN START ===")
        start = time.time()

        influencer_data = self.scan_influencers()
        reddit_data = self.scan_reddit()
        asset_scores = self.compute_social_scores(influencer_data, reddit_data)

        # Generate alerts for high-impact signals
        alerts = []
        for asset, score_data in asset_scores.items():
            if score_data["buzz_level"] == "HIGH":
                alerts.append({
                    "asset": asset,
                    "type": "HIGH_BUZZ",
                    "message": f"{asset} has high social buzz ({score_data['reddit_mentions']} Reddit mentions)",
                    "score": score_data["social_score"],
                    "label": score_data["social_label"],
                })
            for sig in score_data["influencer_signals"]:
                if sig["alert_level"] in ("HIGH", "MEDIUM"):
                    direction = "bullish" if sig["impact"] > 0 else "bearish"
                    alerts.append({
                        "asset": asset,
                        "type": "INFLUENCER",
                        "influencer": sig["influencer"],
                        "message": f"{sig['influencer']} activity detected — {direction} for {asset} (impact: {sig['impact']:+.2f})",
                        "score": sig["impact"],
                        "alert_level": sig["alert_level"],
                    })

        # Summary stats
        high_alerts = [a for a in alerts if a.get("alert_level") == "HIGH" or a.get("type") == "HIGH_BUZZ"]
        duration = time.time() - start

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "influencers": influencer_data,
            "reddit": reddit_data,
            "asset_scores": asset_scores,
            "alerts": alerts,
            "stats": {
                "influencers_scanned": len(influencer_data),
                "subreddits_scanned": len(reddit_data),
                "total_alerts": len(alerts),
                "high_alerts": len(high_alerts),
                "scan_duration_s": round(duration, 1),
            },
            "summary": (
                f"Scanned {len(INFLUENCERS)} influencers + {len(REDDIT_SUBS)} subreddits in {duration:.1f}s. "
                f"{len(alerts)} alerts ({len(high_alerts)} high priority)."
            ),
        }

        # Cache result
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        SOCIAL_CACHE.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log(f"=== SOCIAL SCAN COMPLETE ({duration:.1f}s) — {len(alerts)} alerts ===")

        return result

    @staticmethod
    def load_cached() -> dict | None:
        """Load cached social sentiment data."""
        if SOCIAL_CACHE.exists():
            try:
                return json.loads(SOCIAL_CACHE.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None
