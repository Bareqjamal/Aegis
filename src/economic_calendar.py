"""Economic Calendar — tracks upcoming market-moving events with countdowns.

Provides a schedule of key economic events (FOMC, NFP, CPI, earnings, etc.)
with countdown timers, expected impact ratings, and historical context.

Usage:
    from economic_calendar import EconomicCalendar
    cal = EconomicCalendar()
    events = cal.get_upcoming_events()
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
CALENDAR_CACHE_FILE = DATA_DIR / "economic_calendar.json"

# ---------------------------------------------------------------------------
# Recurring economic events — dates are generated dynamically
# ---------------------------------------------------------------------------

# Impact levels: 1=low, 2=medium, 3=high
RECURRING_EVENTS = [
    {
        "name": "FOMC Interest Rate Decision",
        "short": "FOMC",
        "icon": "🏦",
        "impact": 3,
        "category": "central_bank",
        "description": "Federal Reserve rate decision. Moves everything — equities, bonds, gold, crypto, dollar.",
        "assets_affected": ["Gold", "Silver", "BTC", "S&P 500", "NASDAQ", "EUR/USD"],
        "typical_move": "High volatility 30min before/after. Gold and USD move inversely.",
        "frequency": "8x/year",
    },
    {
        "name": "Non-Farm Payrolls (NFP)",
        "short": "NFP",
        "icon": "👷",
        "impact": 3,
        "category": "employment",
        "description": "US jobs report — first Friday of every month. Strongest single-day volatility catalyst.",
        "assets_affected": ["Gold", "S&P 500", "EUR/USD", "BTC"],
        "typical_move": "Strong jobs = USD up, Gold down. Weak jobs = opposite.",
        "frequency": "Monthly (1st Friday)",
    },
    {
        "name": "Consumer Price Index (CPI)",
        "short": "CPI",
        "icon": "📊",
        "impact": 3,
        "category": "inflation",
        "description": "US inflation data. Key driver for Fed rate expectations.",
        "assets_affected": ["Gold", "Silver", "S&P 500", "NASDAQ", "BTC", "EUR/USD"],
        "typical_move": "Hot CPI = Gold up, Stocks down. Cool CPI = risk-on rally.",
        "frequency": "Monthly (mid-month)",
    },
    {
        "name": "Producer Price Index (PPI)",
        "short": "PPI",
        "icon": "🏭",
        "impact": 2,
        "category": "inflation",
        "description": "Wholesale inflation — leading indicator for CPI.",
        "assets_affected": ["Gold", "S&P 500", "Oil"],
        "typical_move": "Moves markets less than CPI but confirms inflation trends.",
        "frequency": "Monthly",
    },
    {
        "name": "ECB Interest Rate Decision",
        "short": "ECB",
        "icon": "🇪🇺",
        "impact": 3,
        "category": "central_bank",
        "description": "European Central Bank rate decision. Major EUR/USD and European equity mover.",
        "assets_affected": ["EUR/USD", "Gold", "S&P 500"],
        "typical_move": "Hawkish = EUR up, Gold mixed. Dovish = EUR down, Gold up.",
        "frequency": "6x/year",
    },
    {
        "name": "OPEC+ Meeting",
        "short": "OPEC",
        "icon": "⛽",
        "impact": 3,
        "category": "energy",
        "description": "OPEC production decision. Directly impacts oil and energy sector.",
        "assets_affected": ["Oil", "Natural Gas", "S&P 500"],
        "typical_move": "Cuts = Oil up. Increases = Oil down. Surprise decisions cause 5-10% moves.",
        "frequency": "~Monthly",
    },
    {
        "name": "US GDP (Advance Estimate)",
        "short": "GDP",
        "icon": "📈",
        "impact": 2,
        "category": "growth",
        "description": "Quarterly GDP first estimate. Broad market impact.",
        "assets_affected": ["S&P 500", "NASDAQ", "EUR/USD", "Gold"],
        "typical_move": "Strong GDP = risk-on. Negative GDP = recession fears, gold up.",
        "frequency": "Quarterly",
    },
    {
        "name": "Initial Jobless Claims",
        "short": "Claims",
        "icon": "📋",
        "impact": 1,
        "category": "employment",
        "description": "Weekly unemployment claims. High-frequency labor market pulse.",
        "assets_affected": ["S&P 500", "Gold", "EUR/USD"],
        "typical_move": "Rising claims = risk-off. Low claims = risk-on.",
        "frequency": "Weekly (Thursday)",
    },
    {
        "name": "ISM Manufacturing PMI",
        "short": "ISM",
        "icon": "🔧",
        "impact": 2,
        "category": "manufacturing",
        "description": "Manufacturing activity index. Above 50 = expansion, below = contraction.",
        "assets_affected": ["S&P 500", "Copper", "Oil"],
        "typical_move": "Strong ISM = industrial commodities up. Weak = risk-off.",
        "frequency": "Monthly (1st business day)",
    },
    {
        "name": "Retail Sales",
        "short": "Retail",
        "icon": "🛒",
        "impact": 2,
        "category": "consumer",
        "description": "US consumer spending data. Consumer = 70% of US GDP.",
        "assets_affected": ["S&P 500", "NASDAQ", "EUR/USD"],
        "typical_move": "Strong retail = stocks up, USD up. Weak = recession fears.",
        "frequency": "Monthly",
    },
    {
        "name": "PCE Price Index",
        "short": "PCE",
        "icon": "🎯",
        "impact": 3,
        "category": "inflation",
        "description": "The Fed's PREFERRED inflation gauge. More important than CPI for rate decisions.",
        "assets_affected": ["Gold", "S&P 500", "BTC", "EUR/USD"],
        "typical_move": "Hot PCE = hawkish Fed expectations. Cool = dovish pivot hopes.",
        "frequency": "Monthly (last Friday)",
    },
    {
        "name": "Michigan Consumer Sentiment",
        "short": "UMich",
        "icon": "🏠",
        "impact": 1,
        "category": "consumer",
        "description": "Consumer confidence survey. Forward-looking sentiment indicator.",
        "assets_affected": ["S&P 500", "Gold"],
        "typical_move": "Low sentiment = consumer pullback risk. High = bullish spending.",
        "frequency": "Monthly (mid-month, prelim & final)",
    },
    {
        "name": "Bank of Japan Rate Decision",
        "short": "BOJ",
        "icon": "🇯🇵",
        "impact": 2,
        "category": "central_bank",
        "description": "BOJ policy decision. Impacts yen carry trade and global flows.",
        "assets_affected": ["Gold", "S&P 500", "EUR/USD", "BTC"],
        "typical_move": "Surprise tightening = global risk-off. Dovish = carry trade continues.",
        "frequency": "8x/year",
    },
    {
        "name": "China PMI (Official)",
        "short": "CN PMI",
        "icon": "🇨🇳",
        "impact": 2,
        "category": "manufacturing",
        "description": "China manufacturing index. Key driver for commodities and global growth.",
        "assets_affected": ["Copper", "Oil", "Platinum", "S&P 500"],
        "typical_move": "Strong PMI = commodities rally (especially copper). Weak = risk-off.",
        "frequency": "Monthly (last day)",
    },
    {
        "name": "US Treasury Auction (10Y/30Y)",
        "short": "Auction",
        "icon": "📜",
        "impact": 2,
        "category": "bonds",
        "description": "Major treasury auctions affect yield curve and risk appetite.",
        "assets_affected": ["Gold", "S&P 500", "EUR/USD"],
        "typical_move": "Weak demand = yields spike, stocks dip. Strong = yields fall, risk-on.",
        "frequency": "Multiple/month",
    },
]

# ---------------------------------------------------------------------------
# Known upcoming dates (manually curated — update periodically)
# This is the key value-add: accurate dates for upcoming events
# ---------------------------------------------------------------------------

def _generate_event_schedule():
    """Generate upcoming event schedule.

    Uses a combination of known dates and estimated dates based on patterns.
    In production, this would pull from an API like Trading Economics or Forex Factory.
    """
    now = datetime.now(timezone.utc)
    events = []

    # -- 2026 FOMC Meeting Dates (Federal Reserve published schedule) --
    fomc_dates = [
        datetime(2026, 1, 28, 19, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 18, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 6, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 17, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 12, 16, 19, 0, tzinfo=timezone.utc),
    ]
    fomc_template = next(e for e in RECURRING_EVENTS if e["short"] == "FOMC")
    for dt in fomc_dates:
        events.append({**fomc_template, "datetime": dt.isoformat(), "date_obj": dt})

    # -- NFP dates (first Friday of each month, 8:30 AM ET = 13:30 UTC) --
    for month in range(1, 13):
        first_day = datetime(2026, month, 1, 13, 30, tzinfo=timezone.utc)
        # Find first Friday (weekday 4)
        days_until_friday = (4 - first_day.weekday()) % 7
        nfp_date = first_day + timedelta(days=days_until_friday)
        nfp_template = next(e for e in RECURRING_EVENTS if e["short"] == "NFP")
        events.append({**nfp_template, "datetime": nfp_date.isoformat(), "date_obj": nfp_date})

    # -- CPI dates (typically 2nd or 3rd Tuesday of month, 8:30 AM ET) --
    for month in range(1, 13):
        # Approximate: 12th-15th of month
        cpi_date = datetime(2026, month, 13, 13, 30, tzinfo=timezone.utc)
        # Adjust to nearest Tuesday
        days_until_tue = (1 - cpi_date.weekday()) % 7
        if days_until_tue > 3:
            days_until_tue -= 7
        cpi_date = cpi_date + timedelta(days=days_until_tue)
        cpi_template = next(e for e in RECURRING_EVENTS if e["short"] == "CPI")
        events.append({**cpi_template, "datetime": cpi_date.isoformat(), "date_obj": cpi_date})

    # -- PCE dates (last Friday of month, 8:30 AM ET) --
    for month in range(1, 13):
        if month == 12:
            last_day = datetime(2026, 12, 31, 13, 30, tzinfo=timezone.utc)
        else:
            last_day = datetime(2026, month + 1, 1, 13, 30, tzinfo=timezone.utc) - timedelta(days=1)
        days_back_to_fri = (last_day.weekday() - 4) % 7
        pce_date = last_day - timedelta(days=days_back_to_fri)
        pce_template = next(e for e in RECURRING_EVENTS if e["short"] == "PCE")
        events.append({**pce_template, "datetime": pce_date.isoformat(), "date_obj": pce_date})

    # -- ECB dates (approximate — every 6 weeks) --
    ecb_dates = [
        datetime(2026, 1, 30, 13, 15, tzinfo=timezone.utc),
        datetime(2026, 3, 12, 13, 15, tzinfo=timezone.utc),
        datetime(2026, 4, 17, 12, 15, tzinfo=timezone.utc),
        datetime(2026, 6, 5, 12, 15, tzinfo=timezone.utc),
        datetime(2026, 7, 17, 12, 15, tzinfo=timezone.utc),
        datetime(2026, 9, 11, 12, 15, tzinfo=timezone.utc),
        datetime(2026, 10, 29, 13, 15, tzinfo=timezone.utc),
        datetime(2026, 12, 17, 13, 15, tzinfo=timezone.utc),
    ]
    ecb_template = next(e for e in RECURRING_EVENTS if e["short"] == "ECB")
    for dt in ecb_dates:
        events.append({**ecb_template, "datetime": dt.isoformat(), "date_obj": dt})

    # -- OPEC+ meetings (approximate quarterly) --
    opec_dates = [
        datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc),
    ]
    opec_template = next(e for e in RECURRING_EVENTS if e["short"] == "OPEC")
    for dt in opec_dates:
        events.append({**opec_template, "datetime": dt.isoformat(), "date_obj": dt})

    # -- ISM Manufacturing (1st business day of month) --
    for month in range(1, 13):
        ism_date = datetime(2026, month, 1, 15, 0, tzinfo=timezone.utc)
        # Skip weekends
        while ism_date.weekday() >= 5:
            ism_date += timedelta(days=1)
        ism_template = next(e for e in RECURRING_EVENTS if e["short"] == "ISM")
        events.append({**ism_template, "datetime": ism_date.isoformat(), "date_obj": ism_date})

    # -- Weekly Jobless Claims (every Thursday, 8:30 AM ET) --
    # Generate for next 12 weeks from now
    current_thurs = now
    days_until_thurs = (3 - now.weekday()) % 7
    if days_until_thurs == 0 and now.hour >= 14:
        days_until_thurs = 7
    current_thurs = datetime(now.year, now.month, now.day, 13, 30, tzinfo=timezone.utc) + timedelta(days=days_until_thurs)
    claims_template = next(e for e in RECURRING_EVENTS if e["short"] == "Claims")
    for i in range(12):
        dt = current_thurs + timedelta(weeks=i)
        events.append({**claims_template, "datetime": dt.isoformat(), "date_obj": dt})

    # Filter to upcoming events only (past events dropped)
    events = [e for e in events if e["date_obj"] >= now - timedelta(hours=4)]

    # Sort by date
    events.sort(key=lambda e: e["date_obj"])

    return events


class EconomicCalendar:
    """Provides upcoming economic events with countdowns and impact ratings."""

    def get_upcoming_events(self, limit: int = 30) -> list[dict]:
        """Get upcoming economic events sorted by date.

        Returns list of event dicts with countdown info added.
        """
        now = datetime.now(timezone.utc)
        events = _generate_event_schedule()

        result = []
        for ev in events[:limit]:
            dt = ev["date_obj"]
            delta = dt - now
            total_hours = delta.total_seconds() / 3600

            # Build countdown string
            if total_hours < 0:
                countdown = "JUST PASSED"
                urgency = "past"
            elif total_hours < 1:
                minutes = int(delta.total_seconds() / 60)
                countdown = f"{minutes}m"
                urgency = "imminent"
            elif total_hours < 24:
                hours = int(total_hours)
                minutes = int((total_hours - hours) * 60)
                countdown = f"{hours}h {minutes}m"
                urgency = "today"
            elif total_hours < 48:
                countdown = "Tomorrow"
                urgency = "tomorrow"
            elif total_hours < 168:  # 7 days
                days = int(total_hours / 24)
                countdown = f"{days} days"
                urgency = "this_week"
            else:
                days = int(total_hours / 24)
                countdown = f"{days} days"
                urgency = "later"

            entry = {
                "name": ev["name"],
                "short": ev["short"],
                "icon": ev["icon"],
                "impact": ev["impact"],
                "category": ev["category"],
                "description": ev["description"],
                "assets_affected": ev["assets_affected"],
                "typical_move": ev["typical_move"],
                "datetime": ev["datetime"],
                "date_display": dt.strftime("%a %b %d, %H:%M UTC"),
                "countdown": countdown,
                "urgency": urgency,
                "hours_away": round(total_hours, 1),
            }
            result.append(entry)

        return result

    def get_this_week(self) -> list[dict]:
        """Get events happening this week."""
        events = self.get_upcoming_events(limit=50)
        return [e for e in events if e["urgency"] in ("imminent", "today", "tomorrow", "this_week")]

    def get_high_impact_upcoming(self) -> list[dict]:
        """Get only high-impact events (impact >= 3) in next 14 days."""
        events = self.get_upcoming_events(limit=50)
        return [e for e in events if e["impact"] >= 3 and e["hours_away"] <= 336]

    def get_next_event(self) -> dict | None:
        """Get the very next upcoming event."""
        events = self.get_upcoming_events(limit=1)
        return events[0] if events else None

    def get_events_for_asset(self, asset_name: str) -> list[dict]:
        """Get upcoming events that affect a specific asset."""
        events = self.get_upcoming_events(limit=50)
        return [e for e in events if asset_name in e.get("assets_affected", [])]

    def get_event_types(self) -> list[dict]:
        """Get list of all recurring event types with descriptions."""
        return RECURRING_EVENTS
