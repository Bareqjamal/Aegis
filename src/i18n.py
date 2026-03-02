"""
Project Aegis - Internationalization (i18n) System
Lightweight multi-language support for the Streamlit dashboard.
Supports: English (en), German (de), Arabic (ar)

LANGUAGE STRATEGY — What stays English vs gets translated:
────────────────────────────────────────────────────────────
ALWAYS ENGLISH (industry standard, universal in trading):
  - Signal labels: BUY, SELL, STRONG BUY, NEUTRAL, etc.
  - Technical indicators: RSI, MACD, SMA, Bollinger Bands
  - Financial terms: Stop-Loss, Take-Profit, R:R, Sharpe, VaR
  - Asset names: Gold, BTC, S&P 500, EUR/USD
  - Ticker symbols: GC=F, BTC-USD, ^GSPC
  - Chart labels and axis titles
  - Data values and numbers (always Western digits)

TRANSLATED (user-facing UI text):
  - Page titles / section headers ("Daily Advisor" → "Tagesberater")
  - Button labels ("Scan Now" → "Jetzt scannen")
  - Status messages ("Loading..." → "Laden...")
  - Navigation items in sidebar
  - Form labels ("Email", "Password")
  - Tooltips and help text
  - Empty state messages ("No data available")
  - Settings page labels

MIXED (keep English term + translated context):
  - "RSI: Oversold" → "RSI: Überverkauft" (indicator English, interpretation translated)
  - "Confidence: 72%" → stays English (it's a metric)
  - "Regime: RISK_ON" → stays English (system label)
────────────────────────────────────────────────────────────
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------

LANGUAGES = {
    "en": {"name": "English", "native_name": "English", "rtl": False, "flag_emoji": "\U0001f1ec\U0001f1e7"},
    "de": {"name": "German", "native_name": "Deutsch", "rtl": False, "flag_emoji": "\U0001f1e9\U0001f1ea"},
    "ar": {"name": "Arabic", "native_name": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "rtl": True, "flag_emoji": "\U0001f1f8\U0001f1e6"},
}

# ---------------------------------------------------------------------------
# Translation dictionaries
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    "nav.daily_advisor": {
        "en": "Daily Advisor",
        "de": "Tagesberater",
        "ar": "\u0627\u0644\u0645\u0633\u062a\u0634\u0627\u0631 \u0627\u0644\u064a\u0648\u0645\u064a",
    },
    "nav.morning_brief": {
        "en": "Morning Brief",
        "de": "Morgen\u00fcbersicht",
        "ar": "\u0645\u0644\u062e\u0635 \u0627\u0644\u0635\u0628\u0627\u062d",
    },
    "nav.watchlist_overview": {
        "en": "Watchlist Overview",
        "de": "Watchlist \u00dcbersicht",
        "ar": "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629 \u0639\u0644\u0649 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0631\u0627\u0642\u0628\u0629",
    },
    "nav.advanced_charts": {
        "en": "Advanced Charts",
        "de": "Erweiterte Charts",
        "ar": "\u0631\u0633\u0648\u0645 \u0628\u064a\u0627\u0646\u064a\u0629 \u0645\u062a\u0642\u062f\u0645\u0629",
    },
    "nav.paper_trading": {
        "en": "Paper Trading",
        "de": "Papierhandel",
        "ar": "\u0627\u0644\u062a\u062f\u0627\u0648\u0644 \u0627\u0644\u0648\u0631\u0642\u064a",
    },
    "nav.trade_journal": {
        "en": "Trade Journal",
        "de": "Handelsjournal",
        "ar": "\u0633\u062c\u0644 \u0627\u0644\u0635\u0641\u0642\u0627\u062a",
    },
    "nav.watchlist_manager": {
        "en": "Watchlist Manager",
        "de": "Watchlist-Verwaltung",
        "ar": "\u0645\u062f\u064a\u0631 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0631\u0627\u0642\u0628\u0629",
    },
    "nav.alerts": {
        "en": "Alerts",
        "de": "Benachrichtigungen",
        "ar": "\u0627\u0644\u062a\u0646\u0628\u064a\u0647\u0627\u062a",
    },
    "nav.news_intelligence": {
        "en": "News Intelligence",
        "de": "Nachrichtenanalyse",
        "ar": "\u0627\u0633\u062a\u062e\u0628\u0627\u0631\u0627\u062a \u0627\u0644\u0623\u062e\u0628\u0627\u0631",
    },
    "nav.economic_calendar": {
        "en": "Economic Calendar",
        "de": "Wirtschaftskalender",
        "ar": "\u0627\u0644\u062a\u0642\u0648\u064a\u0645 \u0627\u0644\u0627\u0642\u062a\u0635\u0627\u062f\u064a",
    },
    "nav.signal_report_card": {
        "en": "Signal Report Card",
        "de": "Signal-Zeugnis",
        "ar": "\u0628\u0637\u0627\u0642\u0629 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0625\u0634\u0627\u0631\u0627\u062a",
    },
    "nav.fundamentals": {
        "en": "Fundamentals",
        "de": "Fundamentaldaten",
        "ar": "\u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0627\u062a",
    },
    "nav.strategy_lab": {
        "en": "Strategy Lab",
        "de": "Strategie-Labor",
        "ar": "\u0645\u062e\u062a\u0628\u0631 \u0627\u0644\u0627\u0633\u062a\u0631\u0627\u062a\u064a\u062c\u064a\u0627\u062a",
    },
    "nav.analytics": {
        "en": "Analytics",
        "de": "Analysen",
        "ar": "\u0627\u0644\u062a\u062d\u0644\u064a\u0644\u0627\u062a",
    },
    "nav.risk_dashboard": {
        "en": "Risk Dashboard",
        "de": "Risiko-Dashboard",
        "ar": "\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u062e\u0627\u0637\u0631",
    },
    "nav.optimizer": {
        "en": "Optimizer",
        "de": "Optimierer",
        "ar": "\u0627\u0644\u0645\u064f\u062d\u0633\u0651\u0650\u0646",
    },
    "nav.market_overview": {
        "en": "Market Overview",
        "de": "Markt\u00fcbersicht",
        "ar": "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629 \u0639\u0644\u0649 \u0627\u0644\u0633\u0648\u0642",
    },
    "nav.settings": {
        "en": "Settings",
        "de": "Einstellungen",
        "ar": "\u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a",
    },
    "nav.live_logs": {
        "en": "Live Logs",
        "de": "Live-Protokolle",
        "ar": "\u0627\u0644\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u0645\u0628\u0627\u0634\u0631\u0629",
    },
    "nav.agent_performance": {
        "en": "Agent Performance",
        "de": "Agentenleistung",
        "ar": "\u0623\u062f\u0627\u0621 \u0627\u0644\u0648\u0643\u064a\u0644",
    },
    "nav.group_trading": {
        "en": "TRADING",
        "de": "HANDEL",
        "ar": "\u0627\u0644\u062a\u062f\u0627\u0648\u0644",
    },
    "nav.group_intelligence": {
        "en": "INTELLIGENCE",
        "de": "ANALYSEN",
        "ar": "\u0627\u0644\u0627\u0633\u062a\u062e\u0628\u0627\u0631\u0627\u062a",
    },
    "nav.group_system": {
        "en": "SYSTEM",
        "de": "SYSTEM",
        "ar": "\u0627\u0644\u0646\u0638\u0627\u0645",
    },
    "nav.group_research": {
        "en": "RESEARCH",
        "de": "FORSCHUNG",
        "ar": "\u0627\u0644\u0623\u0628\u062d\u0627\u062b",
    },
    "nav.group_account": {
        "en": "ACCOUNT",
        "de": "KONTO",
        "ar": "\u0627\u0644\u062d\u0633\u0627\u0628",
    },

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    "signal.strong_buy": {
        "en": "STRONG BUY",
        "de": "STARKER KAUF",
        "ar": "\u0634\u0631\u0627\u0621 \u0642\u0648\u064a",
    },
    "signal.buy": {
        "en": "BUY",
        "de": "KAUF",
        "ar": "\u0634\u0631\u0627\u0621",
    },
    "signal.neutral": {
        "en": "NEUTRAL",
        "de": "NEUTRAL",
        "ar": "\u0645\u062d\u0627\u064a\u062f",
    },
    "signal.sell": {
        "en": "SELL",
        "de": "VERKAUF",
        "ar": "\u0628\u064a\u0639",
    },
    "signal.strong_sell": {
        "en": "STRONG SELL",
        "de": "STARKER VERKAUF",
        "ar": "\u0628\u064a\u0639 \u0642\u0648\u064a",
    },
    "signal.confidence": {
        "en": "Confidence",
        "de": "Konfidenz",
        "ar": "\u0627\u0644\u062b\u0642\u0629",
    },
    "signal.signal": {
        "en": "Signal",
        "de": "Signal",
        "ar": "\u0625\u0634\u0627\u0631\u0629",
    },

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    "action.scan_now": {
        "en": "Scan Now",
        "de": "Jetzt scannen",
        "ar": "\u0627\u0641\u062d\u0635 \u0627\u0644\u0622\u0646",
    },
    "action.quick_long": {
        "en": "Quick LONG",
        "de": "Schnell LONG",
        "ar": "\u0634\u0631\u0627\u0621 \u0633\u0631\u064a\u0639",
    },
    "action.quick_short": {
        "en": "Quick SHORT",
        "de": "Schnell SHORT",
        "ar": "\u0628\u064a\u0639 \u0633\u0631\u064a\u0639",
    },
    "action.save": {
        "en": "Save",
        "de": "Speichern",
        "ar": "\u062d\u0641\u0638",
    },
    "action.reset_defaults": {
        "en": "Reset to Defaults",
        "de": "Auf Standard zur\u00fccksetzen",
        "ar": "\u0625\u0639\u0627\u062f\u0629 \u062a\u0639\u064a\u064a\u0646 \u0627\u0644\u0627\u0641\u062a\u0631\u0627\u0636\u064a\u0627\u062a",
    },
    "action.back": {
        "en": "Back",
        "de": "Zur\u00fcck",
        "ar": "\u0631\u062c\u0648\u0639",
    },
    "action.sign_out": {
        "en": "Sign Out",
        "de": "Abmelden",
        "ar": "\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062e\u0631\u0648\u062c",
    },
    "action.login": {
        "en": "Login",
        "de": "Anmelden",
        "ar": "\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644",
    },
    "action.register": {
        "en": "Register",
        "de": "Registrieren",
        "ar": "\u062a\u0633\u062c\u064a\u0644",
    },
    "action.continue": {
        "en": "Continue",
        "de": "Weiter",
        "ar": "\u0645\u062a\u0627\u0628\u0639\u0629",
    },

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------
    "label.price": {
        "en": "Price",
        "de": "Preis",
        "ar": "\u0627\u0644\u0633\u0639\u0631",
    },
    "label.change": {
        "en": "Change",
        "de": "\u00c4nderung",
        "ar": "\u0627\u0644\u062a\u063a\u064a\u064a\u0631",
    },
    "label.target": {
        "en": "Target",
        "de": "Ziel",
        "ar": "\u0627\u0644\u0647\u062f\u0641",
    },
    "label.support": {
        "en": "Support",
        "de": "Unterst\u00fctzung",
        "ar": "\u0627\u0644\u062f\u0639\u0645",
    },
    "label.assets": {
        "en": "Assets",
        "de": "Verm\u00f6genswerte",
        "ar": "\u0627\u0644\u0623\u0635\u0648\u0644",
    },
    "label.open_positions": {
        "en": "Open Positions",
        "de": "Offene Positionen",
        "ar": "\u0627\u0644\u0645\u0631\u0627\u0643\u0632 \u0627\u0644\u0645\u0641\u062a\u0648\u062d\u0629",
    },
    "label.closed_trades": {
        "en": "Closed Trades",
        "de": "Geschlossene Trades",
        "ar": "\u0627\u0644\u0635\u0641\u0642\u0627\u062a \u0627\u0644\u0645\u063a\u0644\u0642\u0629",
    },
    "label.win_rate": {
        "en": "Win Rate",
        "de": "Gewinnquote",
        "ar": "\u0645\u0639\u062f\u0644 \u0627\u0644\u0631\u0628\u062d",
    },
    "label.total_return": {
        "en": "Total Return",
        "de": "Gesamtrendite",
        "ar": "\u0627\u0644\u0639\u0627\u0626\u062f \u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a",
    },
    "label.equity": {
        "en": "Equity",
        "de": "Eigenkapital",
        "ar": "\u0627\u0644\u0645\u0644\u0643\u064a\u0629",
    },
    "label.cash": {
        "en": "Cash",
        "de": "Bargeld",
        "ar": "\u0627\u0644\u0646\u0642\u062f",
    },
    "label.portfolio": {
        "en": "Portfolio",
        "de": "Portfolio",
        "ar": "\u0627\u0644\u0645\u062d\u0641\u0638\u0629",
    },
    "label.risk": {
        "en": "Risk",
        "de": "Risiko",
        "ar": "\u0627\u0644\u0645\u062e\u0627\u0637\u0631",
    },
    "label.regime": {
        "en": "Regime",
        "de": "Marktregime",
        "ar": "\u0627\u0644\u0646\u0638\u0627\u0645",
    },
    "label.volume": {
        "en": "Volume",
        "de": "Volumen",
        "ar": "\u0627\u0644\u062d\u062c\u0645",
    },
    "label.high": {
        "en": "High",
        "de": "Hoch",
        "ar": "\u0623\u0639\u0644\u0649",
    },
    "label.low": {
        "en": "Low",
        "de": "Tief",
        "ar": "\u0623\u062f\u0646\u0649",
    },
    "label.market_cap": {
        "en": "Market Cap",
        "de": "Marktkapitalisierung",
        "ar": "\u0627\u0644\u0642\u064a\u0645\u0629 \u0627\u0644\u0633\u0648\u0642\u064a\u0629",
    },
    "label.sentiment": {
        "en": "Sentiment",
        "de": "Stimmung",
        "ar": "\u0627\u0644\u0645\u0639\u0646\u0648\u064a\u0627\u062a",
    },
    "label.accuracy": {
        "en": "Accuracy",
        "de": "Genauigkeit",
        "ar": "\u0627\u0644\u062f\u0642\u0629",
    },
    "label.date": {
        "en": "Date",
        "de": "Datum",
        "ar": "\u0627\u0644\u062a\u0627\u0631\u064a\u062e",
    },
    "label.time": {
        "en": "Time",
        "de": "Uhrzeit",
        "ar": "\u0627\u0644\u0648\u0642\u062a",
    },
    "label.type": {
        "en": "Type",
        "de": "Typ",
        "ar": "\u0627\u0644\u0646\u0648\u0639",
    },
    "label.status": {
        "en": "Status",
        "de": "Status",
        "ar": "\u0627\u0644\u062d\u0627\u0644\u0629",
    },
    "label.description": {
        "en": "Description",
        "de": "Beschreibung",
        "ar": "\u0627\u0644\u0648\u0635\u0641",
    },

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    "section.market_regime": {
        "en": "Market Regime",
        "de": "Marktregime",
        "ar": "\u0646\u0638\u0627\u0645 \u0627\u0644\u0633\u0648\u0642",
    },
    "section.top_picks": {
        "en": "Top Picks",
        "de": "Top-Auswahl",
        "ar": "\u0623\u0641\u0636\u0644 \u0627\u0644\u0627\u062e\u062a\u064a\u0627\u0631\u0627\u062a",
    },
    "section.social_pulse": {
        "en": "Social Pulse",
        "de": "Social-Puls",
        "ar": "\u0646\u0628\u0636 \u0627\u0644\u062a\u0648\u0627\u0635\u0644 \u0627\u0644\u0627\u062c\u062a\u0645\u0627\u0639\u064a",
    },
    "section.geopolitical_radar": {
        "en": "Geopolitical Radar",
        "de": "Geopolitischer Radar",
        "ar": "\u0631\u0627\u062f\u0627\u0631 \u062c\u064a\u0648\u0633\u064a\u0627\u0633\u064a",
    },
    "section.multi_timeframe": {
        "en": "Multi-Timeframe",
        "de": "Multi-Zeitrahmen",
        "ar": "\u0623\u0637\u0631 \u0632\u0645\u0646\u064a\u0629 \u0645\u062a\u0639\u062f\u062f\u0629",
    },
    "section.alerts": {
        "en": "Alerts",
        "de": "Alarme",
        "ar": "\u0627\u0644\u062a\u0646\u0628\u064a\u0647\u0627\u062a",
    },

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    "settings.language": {
        "en": "Language",
        "de": "Sprache",
        "ar": "\u0627\u0644\u0644\u063a\u0629",
    },
    "settings.theme": {
        "en": "Theme",
        "de": "Design",
        "ar": "\u0627\u0644\u0645\u0638\u0647\u0631",
    },
    "settings.refresh_interval": {
        "en": "Refresh Interval",
        "de": "Aktualisierungsintervall",
        "ar": "\u0641\u062a\u0631\u0629 \u0627\u0644\u062a\u062d\u062f\u064a\u062b",
    },

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    "auth.email": {
        "en": "Email",
        "de": "E-Mail",
        "ar": "\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a",
    },
    "auth.password": {
        "en": "Password",
        "de": "Passwort",
        "ar": "\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
    },
    "auth.name": {
        "en": "Name",
        "de": "Name",
        "ar": "\u0627\u0644\u0627\u0633\u0645",
    },
    "auth.verify_email": {
        "en": "Verify Email",
        "de": "E-Mail best\u00e4tigen",
        "ar": "\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a",
    },
    "auth.verification_code": {
        "en": "Verification Code",
        "de": "Best\u00e4tigungscode",
        "ar": "\u0631\u0645\u0632 \u0627\u0644\u062a\u062d\u0642\u0642",
    },
    "auth.guest_mode": {
        "en": "Guest Mode",
        "de": "Gastmodus",
        "ar": "\u0648\u0636\u0639 \u0627\u0644\u0636\u064a\u0641",
    },

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    "status.loading": {
        "en": "Loading...",
        "de": "Laden...",
        "ar": "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0645\u064a\u0644...",
    },
    "status.no_data": {
        "en": "No data available",
        "de": "Keine Daten verf\u00fcgbar",
        "ar": "\u0644\u0627 \u062a\u0648\u062c\u062f \u0628\u064a\u0627\u0646\u0627\u062a \u0645\u062a\u0627\u062d\u0629",
    },
    "status.scan_complete": {
        "en": "Scan complete",
        "de": "Scan abgeschlossen",
        "ar": "\u0627\u0643\u062a\u0645\u0644 \u0627\u0644\u0641\u062d\u0635",
    },
    "status.error": {
        "en": "Error",
        "de": "Fehler",
        "ar": "\u062e\u0637\u0623",
    },
    # ------------------------------------------------------------------
    # Evolution / Monitor
    # ------------------------------------------------------------------
    "evolution.no_reflection": {
        "en": "No reflection yet. The Chief Monitor generates a daily summary.",
        "de": "Noch keine Reflection vorhanden. Der Chief Monitor erstellt täglich eine Zusammenfassung.",
        "ar": "\u0644\u0627 \u064a\u0648\u062c\u062f \u062a\u0642\u064a\u064a\u0645 \u0628\u0639\u062f. \u064a\u0642\u0648\u0645 \u0627\u0644\u0645\u0631\u0627\u0642\u0628 \u0627\u0644\u0631\u0626\u064a\u0633\u064a \u0628\u0625\u0646\u0634\u0627\u0621 \u0645\u0644\u062e\u0635 \u064a\u0648\u0645\u064a.",
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_language() -> str:
    """Return the current language code from session state (default: 'en')."""
    return st.session_state.get("language", "en")


def set_language(lang: str) -> None:
    """Set the active language. Accepts 'en', 'de', or 'ar'."""
    if lang in LANGUAGES:
        st.session_state["language"] = lang


def is_rtl() -> bool:
    """Return True if the current language is right-to-left."""
    lang = get_language()
    return LANGUAGES.get(lang, {}).get("rtl", False)


# ---------------------------------------------------------------------------
# Main translation function
# ---------------------------------------------------------------------------

def t(key: str) -> str:
    """
    Translate *key* into the active language.

    Lookup order:
      1. TRANSLATIONS[key][current_language]
      2. TRANSLATIONS[key]["en"]          (English fallback)
      3. key itself                       (ultimate fallback)
    """
    lang = get_language()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))


# ---------------------------------------------------------------------------
# RTL CSS
# ---------------------------------------------------------------------------

def get_rtl_css() -> str:
    """
    Return a CSS block that switches the main content area to RTL.
    The sidebar is kept LTR because Streamlit does not support RTL sidebars.
    Returns an empty string when the active language is LTR.
    """
    if not is_rtl():
        return ""

    return """
<style>
    /* RTL: main content area */
    .main .block-container {
        direction: rtl;
        text-align: right;
    }
    /* RTL: metric labels and values */
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"] {
        direction: rtl;
        text-align: right;
    }
    /* RTL: markdown blocks */
    .main .block-container .stMarkdown {
        direction: rtl;
        text-align: right;
    }
    /* RTL: table cells */
    .main .block-container td,
    .main .block-container th {
        text-align: right;
    }
    /* Keep sidebar LTR (Streamlit limitation) */
    [data-testid="stSidebar"] {
        direction: ltr;
        text-align: left;
    }
</style>
"""


# ---------------------------------------------------------------------------
# Language selector widget
# ---------------------------------------------------------------------------

def language_selector(sidebar: bool = True) -> str:
    """
    Render a Streamlit selectbox for language selection.

    Parameters
    ----------
    sidebar : bool
        If True (default), render in the sidebar. Otherwise render in
        the main content area.

    Returns
    -------
    str
        The selected language code ('en', 'de', or 'ar').
    """
    codes = list(LANGUAGES.keys())
    display_names = [
        f"{LANGUAGES[c]['flag_emoji']} {LANGUAGES[c]['native_name']}"
        for c in codes
    ]

    current = get_language()
    current_index = codes.index(current) if current in codes else 0

    container = st.sidebar if sidebar else st
    selected_display = container.selectbox(
        t("settings.language"),
        options=display_names,
        index=current_index,
        key="i18n_language_selector",
    )

    selected_code = codes[display_names.index(selected_display)]
    if selected_code != current:
        set_language(selected_code)
        st.rerun()

    return selected_code
