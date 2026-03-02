"""Morning Email Sender — wires MorningBrief + MarketLearner to send a daily scorecard email.

Combines the morning brief data with yesterday's prediction accuracy into a
professionally styled dark-terminal HTML email.

Usage:
    from morning_email import send_morning_email
    success = send_morning_email("trader@example.com")

    # Or use the class directly for more control:
    from morning_email import MorningEmailSender
    sender = MorningEmailSender()
    html = sender.build_html()        # preview without sending
    sender.send("trader@example.com") # send via SMTP
"""

import json
import logging
import os
import smtplib
import ssl
import time
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
DATA_DIR = PROJECT_ROOT / "src" / "data"

PREDICTIONS_FILE = MEMORY_DIR / "market_predictions.json"

# SMTP config from environment (same vars as auth_manager.py)
SMTP_HOST = os.environ.get("AEGIS_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("AEGIS_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AEGIS_SMTP_USER")
SMTP_PASS = os.environ.get("AEGIS_SMTP_PASS")
SMTP_FROM = os.environ.get("AEGIS_SMTP_FROM", "noreply@aegis-terminal.com")

# Rate limiting — prevent duplicate sends within a cooldown window
_last_send_ts: float = 0.0
SEND_COOLDOWN_SECONDS = 300  # 5 minutes between sends

logger = logging.getLogger("aegis.morning_email")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Safely load a JSON file, returning None on any error."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path.name, exc)
        return None


def _load_predictions_data() -> dict:
    """Load prediction data from market_predictions.json."""
    data = _load_json(PREDICTIONS_FILE)
    if not data or not isinstance(data, dict):
        return {"predictions": [], "stats": {"total": 0, "validated": 0, "correct": 0}}
    return data


def _get_yesterday_scorecard(predictions_data: dict) -> dict:
    """Compute yesterday's prediction accuracy scorecard.

    Looks at predictions that were validated in the last 48 hours and
    computes correct/incorrect/neutral counts.
    """
    predictions = predictions_data.get("predictions", [])
    now = datetime.now(timezone.utc)
    yesterday_start = (now - timedelta(hours=48))

    # Gather predictions validated recently
    validated_recent = []
    for p in predictions:
        if not p.get("validated"):
            continue
        outcome_date = p.get("outcome_date")
        if not outcome_date:
            continue
        try:
            odate = datetime.fromisoformat(outcome_date)
            if odate >= yesterday_start:
                validated_recent.append(p)
        except (ValueError, TypeError):
            continue

    correct = sum(1 for p in validated_recent if p.get("outcome") == "correct")
    incorrect = sum(1 for p in validated_recent if p.get("outcome") == "incorrect")
    neutral = sum(1 for p in validated_recent if p.get("outcome") == "neutral")
    total = correct + incorrect + neutral
    decisions = correct + incorrect  # exclude neutral from accuracy calc
    accuracy = round((correct / decisions * 100), 1) if decisions > 0 else 0.0

    # Overall lifetime stats
    all_validated = [p for p in predictions if p.get("validated")]
    all_correct = sum(1 for p in all_validated if p.get("outcome") == "correct")
    all_decisions = sum(1 for p in all_validated if p.get("outcome") in ("correct", "incorrect"))
    lifetime_accuracy = round((all_correct / all_decisions * 100), 1) if all_decisions > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "neutral": neutral,
        "accuracy": accuracy,
        "lifetime_accuracy": lifetime_accuracy,
        "lifetime_total": len(all_validated),
        "recent_predictions": validated_recent[:5],
    }


# ---------------------------------------------------------------------------
# HTML email builder
# ---------------------------------------------------------------------------

# Color palette — matches Project Aegis terminal theme
_BG_PRIMARY = "#0d1117"
_BG_SECONDARY = "#161b22"
_BG_CARD = "#1c2128"
_TEXT_PRIMARY = "#e6edf3"
_TEXT_SECONDARY = "#8b949e"
_TEXT_MUTED = "#6e7681"
_GREEN = "#3fb950"
_RED = "#f85149"
_BLUE = "#58a6ff"
_YELLOW = "#d29922"
_ORANGE = "#fd7e14"
_BORDER = "#30363d"
_FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Courier New', monospace"
_FONT_UI = "'Inter', 'Segoe UI', Arial, sans-serif"


def _signal_color(signal: str) -> str:
    """Return the color for a signal label."""
    sig = signal.upper()
    if sig in ("STRONG BUY", "BUY"):
        return _GREEN
    elif sig in ("STRONG SELL", "SELL"):
        return _RED
    elif sig == "NEUTRAL":
        return _TEXT_MUTED
    return _TEXT_SECONDARY


def _accuracy_color(accuracy: float) -> str:
    """Return color based on accuracy percentage."""
    if accuracy >= 65:
        return _GREEN
    elif accuracy >= 50:
        return _YELLOW
    else:
        return _RED


def _build_scorecard_html(scorecard: dict) -> str:
    """Build the Yesterday's Scorecard section."""
    if scorecard["total"] == 0:
        return f"""
        <div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:8px;padding:20px;margin-bottom:20px;">
            <h2 style="color:{_BLUE};font-family:{_FONT_UI};font-size:16px;margin:0 0 12px 0;text-transform:uppercase;letter-spacing:1px;">
                Yesterday's Scorecard
            </h2>
            <p style="color:{_TEXT_SECONDARY};font-family:{_FONT_UI};font-size:14px;margin:0;">
                No predictions were validated yesterday. Run a market scan to generate signals.
            </p>
        </div>
        """

    acc_color = _accuracy_color(scorecard["accuracy"])
    correct = scorecard["correct"]
    incorrect = scorecard["incorrect"]
    neutral = scorecard["neutral"]
    total = scorecard["total"]
    accuracy = scorecard["accuracy"]

    # Build individual prediction result rows
    pred_rows = ""
    for p in scorecard.get("recent_predictions", [])[:5]:
        outcome = p.get("outcome", "pending")
        if outcome == "correct":
            dot = f'<span style="color:{_GREEN};">&#9679;</span>'
            label = "CORRECT"
            lbl_color = _GREEN
        elif outcome == "incorrect":
            dot = f'<span style="color:{_RED};">&#9679;</span>'
            label = "WRONG"
            lbl_color = _RED
        else:
            dot = f'<span style="color:{_TEXT_MUTED};">&#9679;</span>'
            label = "NEUTRAL"
            lbl_color = _TEXT_MUTED

        asset = p.get("asset", "?")
        signal = p.get("signal_label", "?")
        note = p.get("outcome_note", "")[:60]

        pred_rows += f"""
        <tr>
            <td style="padding:6px 8px;border-bottom:1px solid {_BORDER};font-family:{_FONT_MONO};font-size:12px;color:{_TEXT_PRIMARY};">
                {dot} {asset}
            </td>
            <td style="padding:6px 8px;border-bottom:1px solid {_BORDER};font-family:{_FONT_MONO};font-size:12px;color:{_signal_color(signal)};">
                {signal}
            </td>
            <td style="padding:6px 8px;border-bottom:1px solid {_BORDER};font-family:{_FONT_MONO};font-size:12px;color:{lbl_color};">
                {label}
            </td>
            <td style="padding:6px 8px;border-bottom:1px solid {_BORDER};font-family:{_FONT_UI};font-size:11px;color:{_TEXT_SECONDARY};">
                {note}
            </td>
        </tr>
        """

    pred_table = ""
    if pred_rows:
        pred_table = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:14px;">
            <tr>
                <th style="text-align:left;padding:6px 8px;border-bottom:2px solid {_BORDER};font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;">Asset</th>
                <th style="text-align:left;padding:6px 8px;border-bottom:2px solid {_BORDER};font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;">Signal</th>
                <th style="text-align:left;padding:6px 8px;border-bottom:2px solid {_BORDER};font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;">Result</th>
                <th style="text-align:left;padding:6px 8px;border-bottom:2px solid {_BORDER};font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;">Note</th>
            </tr>
            {pred_rows}
        </table>
        """

    return f"""
    <div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:8px;padding:20px;margin-bottom:20px;">
        <h2 style="color:{_BLUE};font-family:{_FONT_UI};font-size:16px;margin:0 0 16px 0;text-transform:uppercase;letter-spacing:1px;">
            Yesterday's Scorecard
        </h2>
        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="text-align:center;padding:12px;width:25%;">
                    <div style="font-family:{_FONT_MONO};font-size:28px;font-weight:bold;color:{acc_color};">{accuracy}%</div>
                    <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;margin-top:4px;">Accuracy</div>
                </td>
                <td style="text-align:center;padding:12px;width:25%;">
                    <div style="font-family:{_FONT_MONO};font-size:28px;font-weight:bold;color:{_GREEN};">{correct}</div>
                    <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;margin-top:4px;">Correct</div>
                </td>
                <td style="text-align:center;padding:12px;width:25%;">
                    <div style="font-family:{_FONT_MONO};font-size:28px;font-weight:bold;color:{_RED};">{incorrect}</div>
                    <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;margin-top:4px;">Wrong</div>
                </td>
                <td style="text-align:center;padding:12px;width:25%;">
                    <div style="font-family:{_FONT_MONO};font-size:28px;font-weight:bold;color:{_TEXT_PRIMARY};">{total}</div>
                    <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;margin-top:4px;">Total</div>
                </td>
            </tr>
        </table>
        <div style="margin-top:8px;padding:8px 12px;background:{_BG_SECONDARY};border-radius:4px;font-family:{_FONT_UI};font-size:12px;color:{_TEXT_SECONDARY};">
            Lifetime accuracy: <span style="color:{_accuracy_color(scorecard['lifetime_accuracy'])};font-weight:bold;">{scorecard['lifetime_accuracy']}%</span> across {scorecard['lifetime_total']} validated predictions
        </div>
        {pred_table}
    </div>
    """


def _build_top_signals_html(top_picks: list[dict]) -> str:
    """Build the Top 3 Signals section."""
    picks = top_picks[:3]
    if not picks:
        return f"""
        <div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:8px;padding:20px;margin-bottom:20px;">
            <h2 style="color:{_GREEN};font-family:{_FONT_UI};font-size:16px;margin:0 0 12px 0;text-transform:uppercase;letter-spacing:1px;">
                Today's Top Signals
            </h2>
            <p style="color:{_TEXT_SECONDARY};font-family:{_FONT_UI};font-size:14px;margin:0;">
                No signals available. Run a market scan to generate today's signals.
            </p>
        </div>
        """

    cards = ""
    for i, pick in enumerate(picks):
        asset = pick.get("asset", "Unknown")
        signal = pick.get("signal", "NEUTRAL")
        confidence = pick.get("confidence", 0)
        price = pick.get("price", 0)
        change_pct = pick.get("change_pct", 0)
        reason = pick.get("reason", "")
        verdict = pick.get("verdict", "WAIT")

        sig_color = _signal_color(signal)
        change_color = _GREEN if change_pct >= 0 else _RED
        change_arrow = "+" if change_pct >= 0 else ""
        rank = i + 1

        # Confidence bar (visual inline bar)
        bar_width = min(max(int(confidence), 0), 100)
        bar_color = _GREEN if confidence >= 60 else (_YELLOW if confidence >= 40 else _RED)

        cards += f"""
        <div style="background:{_BG_SECONDARY};border:1px solid {_BORDER};border-left:3px solid {sig_color};border-radius:6px;padding:14px 16px;margin-bottom:10px;">
            <table style="width:100%;border-collapse:collapse;">
                <tr>
                    <td style="vertical-align:top;width:auto;">
                        <span style="font-family:{_FONT_MONO};font-size:11px;color:{_TEXT_MUTED};">#{rank}</span>
                        <span style="font-family:{_FONT_UI};font-size:15px;font-weight:bold;color:{_TEXT_PRIMARY};margin-left:6px;">{asset}</span>
                        <span style="display:inline-block;background:{sig_color};color:{_BG_PRIMARY};font-family:{_FONT_MONO};font-size:10px;font-weight:bold;padding:2px 8px;border-radius:3px;margin-left:8px;">{signal}</span>
                    </td>
                    <td style="text-align:right;vertical-align:top;">
                        <span style="font-family:{_FONT_MONO};font-size:14px;color:{_TEXT_PRIMARY};">${price:,.2f}</span>
                        <span style="font-family:{_FONT_MONO};font-size:12px;color:{change_color};margin-left:6px;">{change_arrow}{change_pct:.1f}%</span>
                    </td>
                </tr>
            </table>
            <div style="margin-top:8px;">
                <span style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;">Confidence</span>
                <span style="font-family:{_FONT_MONO};font-size:12px;color:{bar_color};margin-left:6px;font-weight:bold;">{confidence}%</span>
                <div style="background:{_BORDER};border-radius:3px;height:4px;margin-top:4px;overflow:hidden;">
                    <div style="background:{bar_color};width:{bar_width}%;height:100%;border-radius:3px;"></div>
                </div>
            </div>
            <div style="margin-top:8px;font-family:{_FONT_UI};font-size:12px;color:{_TEXT_SECONDARY};line-height:1.4;">
                {reason}
            </div>
        </div>
        """

    return f"""
    <div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:8px;padding:20px;margin-bottom:20px;">
        <h2 style="color:{_GREEN};font-family:{_FONT_UI};font-size:16px;margin:0 0 16px 0;text-transform:uppercase;letter-spacing:1px;">
            Today's Top Signals
        </h2>
        {cards}
    </div>
    """


def _build_regime_risk_html(brief: dict) -> str:
    """Build the Market Regime + Risk Level section."""
    regime = brief.get("regime", {})
    risk = brief.get("risk", {})

    regime_name = regime.get("name", "NEUTRAL")
    regime_desc = regime.get("description", "No regime data available.")
    regime_confidence = regime.get("confidence", 0)

    risk_level = risk.get("level", "CALM")
    risk_map = {"EXTREME": _RED, "ELEVATED": _ORANGE, "MODERATE": _YELLOW, "LOW": _BLUE, "CALM": _GREEN}
    risk_color = risk_map.get(risk_level, _TEXT_MUTED)

    regime_map = {
        "RISK-ON": _GREEN, "RISK-OFF": _RED, "INFLATIONARY": _ORANGE,
        "DEFLATIONARY": _BLUE, "VOLATILE": _YELLOW, "NEUTRAL": _TEXT_MUTED,
    }
    regime_color = regime_map.get(regime_name, _TEXT_MUTED)

    signals_overview = brief.get("signals_overview", {})
    buy_count = signals_overview.get("buy", 0)
    sell_count = signals_overview.get("sell", 0)
    neutral_count = signals_overview.get("neutral", 0)

    return f"""
    <div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:8px;padding:20px;margin-bottom:20px;">
        <h2 style="color:{_TEXT_SECONDARY};font-family:{_FONT_UI};font-size:16px;margin:0 0 16px 0;text-transform:uppercase;letter-spacing:1px;">
            Market Conditions
        </h2>
        <table style="width:100%;border-collapse:collapse;">
            <tr>
                <td style="padding:10px;width:50%;vertical-align:top;">
                    <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;margin-bottom:6px;">Macro Regime</div>
                    <div style="font-family:{_FONT_MONO};font-size:18px;font-weight:bold;color:{regime_color};">{regime_name}</div>
                    <div style="font-family:{_FONT_UI};font-size:12px;color:{_TEXT_SECONDARY};margin-top:4px;">{regime_desc[:80]}</div>
                </td>
                <td style="padding:10px;width:50%;vertical-align:top;">
                    <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;margin-bottom:6px;">Geopolitical Risk</div>
                    <div style="font-family:{_FONT_MONO};font-size:18px;font-weight:bold;color:{risk_color};">{risk_level}</div>
                    <div style="font-family:{_FONT_UI};font-size:12px;color:{_TEXT_SECONDARY};margin-top:4px;">
                        Signals: <span style="color:{_GREEN};">{buy_count} BUY</span> /
                        <span style="color:{_RED};">{sell_count} SELL</span> /
                        <span style="color:{_TEXT_MUTED};">{neutral_count} NEUTRAL</span>
                    </div>
                </td>
            </tr>
        </table>
    </div>
    """


# ---------------------------------------------------------------------------
# MorningEmailSender
# ---------------------------------------------------------------------------

class MorningEmailSender:
    """Builds and sends the Aegis morning email with scorecard + brief data."""

    def __init__(self):
        self._brief_data: dict | None = None
        self._scorecard: dict | None = None

    def _load_brief(self) -> dict:
        """Load morning brief data — try cache first, then generate fresh."""
        if self._brief_data:
            return self._brief_data

        try:
            from morning_brief import MorningBrief
            mb = MorningBrief()

            # Try cached first (avoid expensive generation if recent)
            cached = mb.load_cached()
            if cached:
                ts = cached.get("timestamp", "")
                try:
                    cache_time = datetime.fromisoformat(ts)
                    age_hours = (datetime.now(timezone.utc) - cache_time).total_seconds() / 3600
                    if age_hours < 6:
                        self._brief_data = cached
                        return cached
                except (ValueError, TypeError):
                    pass

            # Generate fresh
            self._brief_data = mb.generate()
            return self._brief_data

        except Exception as exc:
            logger.error("Failed to load morning brief: %s", exc)
            return {
                "date_display": datetime.now(timezone.utc).strftime("%A, %B %d, %Y"),
                "headline": "Morning brief unavailable",
                "regime": {"name": "UNKNOWN", "description": "", "confidence": 0},
                "risk": {"level": "UNKNOWN"},
                "signals_overview": {"total": 0, "buy": 0, "sell": 0, "neutral": 0},
                "top_picks": [],
                "key_takeaway": "Run a market scan to generate today's brief.",
            }

    def _load_scorecard(self) -> dict:
        """Load yesterday's prediction scorecard."""
        if self._scorecard:
            return self._scorecard

        predictions_data = _load_predictions_data()
        self._scorecard = _get_yesterday_scorecard(predictions_data)
        return self._scorecard

    def build_subject(self) -> str:
        """Build the email subject line."""
        brief = self._load_brief()
        date_str = brief.get("date_display", datetime.now(timezone.utc).strftime("%A, %B %d, %Y"))
        return f"Aegis Morning Brief \u2014 {date_str} | Were You Right?"

    def build_html(self) -> str:
        """Build the full HTML email body.

        Returns a self-contained HTML string with all inline CSS.
        """
        brief = self._load_brief()
        scorecard = self._load_scorecard()

        date_display = brief.get("date_display", datetime.now(timezone.utc).strftime("%A, %B %d, %Y"))
        headline = brief.get("headline", "")
        key_takeaway = brief.get("key_takeaway", "")
        top_picks = brief.get("top_picks", [])

        # Build sections
        scorecard_html = _build_scorecard_html(scorecard)
        signals_html = _build_top_signals_html(top_picks)
        regime_html = _build_regime_risk_html(brief)

        # Assemble full email
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aegis Morning Brief</title>
</head>
<body style="margin:0;padding:0;background-color:{_BG_PRIMARY};font-family:{_FONT_UI};">
    <!-- Wrapper -->
    <table role="presentation" style="width:100%;background-color:{_BG_PRIMARY};margin:0;padding:0;" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center" style="padding:20px 10px;">
                <!-- Container -->
                <table role="presentation" style="width:100%;max-width:640px;margin:0 auto;" cellpadding="0" cellspacing="0">

                    <!-- Header -->
                    <tr>
                        <td style="padding:24px 0;text-align:center;border-bottom:1px solid {_BORDER};">
                            <div style="font-family:{_FONT_MONO};font-size:22px;font-weight:bold;color:{_GREEN};letter-spacing:2px;">
                                AEGIS
                            </div>
                            <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;letter-spacing:3px;margin-top:4px;">
                                Morning Intelligence Brief
                            </div>
                            <div style="font-family:{_FONT_UI};font-size:13px;color:{_TEXT_SECONDARY};margin-top:8px;">
                                {date_display}
                            </div>
                        </td>
                    </tr>

                    <!-- Headline -->
                    <tr>
                        <td style="padding:20px 0 12px 0;">
                            <div style="font-family:{_FONT_UI};font-size:17px;color:{_TEXT_PRIMARY};line-height:1.5;text-align:center;">
                                {headline}
                            </div>
                        </td>
                    </tr>

                    <!-- Scorecard Section -->
                    <tr>
                        <td style="padding:0;">
                            {scorecard_html}
                        </td>
                    </tr>

                    <!-- Top Signals Section -->
                    <tr>
                        <td style="padding:0;">
                            {signals_html}
                        </td>
                    </tr>

                    <!-- Regime + Risk Section -->
                    <tr>
                        <td style="padding:0;">
                            {regime_html}
                        </td>
                    </tr>

                    <!-- Key Takeaway -->
                    <tr>
                        <td style="padding:0 0 20px 0;">
                            <div style="background:{_BG_CARD};border:1px solid {_BORDER};border-left:3px solid {_BLUE};border-radius:8px;padding:16px 20px;">
                                <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
                                    Bottom Line
                                </div>
                                <div style="font-family:{_FONT_UI};font-size:14px;color:{_TEXT_PRIMARY};line-height:1.5;">
                                    {key_takeaway}
                                </div>
                            </div>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding:10px 0 30px 0;text-align:center;">
                            <a href="http://localhost:8501"
                               style="display:inline-block;background:{_GREEN};color:{_BG_PRIMARY};font-family:{_FONT_UI};font-size:14px;font-weight:bold;text-decoration:none;padding:12px 32px;border-radius:6px;letter-spacing:0.5px;">
                                Open Aegis Terminal
                            </a>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding:20px 0;border-top:1px solid {_BORDER};text-align:center;">
                            <div style="font-family:{_FONT_UI};font-size:11px;color:{_TEXT_MUTED};line-height:1.8;">
                                Project Aegis &mdash; AI Trading Intelligence<br>
                                Signals are for informational purposes only. Not financial advice.<br>
                                <a href="#unsubscribe" style="color:{_BLUE};text-decoration:underline;">Unsubscribe</a>
                                &nbsp;&bull;&nbsp;
                                <a href="#preferences" style="color:{_BLUE};text-decoration:underline;">Email Preferences</a>
                            </div>
                        </td>
                    </tr>

                </table>
                <!-- /Container -->
            </td>
        </tr>
    </table>
    <!-- /Wrapper -->
</body>
</html>"""
        return html

    def build_plain_text(self) -> str:
        """Build a plain-text fallback for the email."""
        brief = self._load_brief()
        scorecard = self._load_scorecard()

        date_display = brief.get("date_display", "")
        headline = brief.get("headline", "")
        key_takeaway = brief.get("key_takeaway", "")
        top_picks = brief.get("top_picks", [])[:3]

        regime = brief.get("regime", {})
        risk = brief.get("risk", {})

        lines = [
            f"AEGIS MORNING BRIEF -- {date_display}",
            "=" * 50,
            "",
            headline,
            "",
            "--- YESTERDAY'S SCORECARD ---",
        ]

        if scorecard["total"] > 0:
            lines.append(f"Accuracy: {scorecard['accuracy']}%  |  "
                         f"Correct: {scorecard['correct']}  |  "
                         f"Wrong: {scorecard['incorrect']}  |  "
                         f"Total: {scorecard['total']}")
            lines.append(f"Lifetime: {scorecard['lifetime_accuracy']}% across {scorecard['lifetime_total']} predictions")
        else:
            lines.append("No predictions validated yesterday.")

        lines.append("")
        lines.append("--- TODAY'S TOP SIGNALS ---")
        for i, pick in enumerate(top_picks):
            asset = pick.get("asset", "?")
            signal = pick.get("signal", "?")
            confidence = pick.get("confidence", 0)
            price = pick.get("price", 0)
            lines.append(f"  #{i+1}  {asset}: {signal} ({confidence}%) @ ${price:,.2f}")

        lines.append("")
        lines.append("--- MARKET CONDITIONS ---")
        lines.append(f"Regime: {regime.get('name', 'UNKNOWN')}  |  "
                     f"Risk: {risk.get('level', 'UNKNOWN')}")

        lines.append("")
        lines.append(f"Bottom Line: {key_takeaway}")
        lines.append("")
        lines.append("Open Aegis: http://localhost:8501")
        lines.append("")
        lines.append("-" * 50)
        lines.append("Project Aegis -- AI Trading Intelligence")
        lines.append("Signals are for informational purposes only. Not financial advice.")

        return "\n".join(lines)

    def send(self, to_address: str) -> bool:
        """Send the morning email via SMTP.

        Args:
            to_address: Recipient email address.

        Returns:
            True if sent successfully, False otherwise.
            Never raises — all errors are caught and logged.
        """
        global _last_send_ts

        # Rate limiting
        now = time.monotonic()
        if now - _last_send_ts < SEND_COOLDOWN_SECONDS:
            elapsed = int(now - _last_send_ts)
            logger.warning(
                "Morning email rate limited. Last sent %ds ago (cooldown: %ds).",
                elapsed,
                SEND_COOLDOWN_SECONDS,
            )
            return False

        if not to_address or "@" not in to_address:
            logger.error("Invalid recipient address: %s", to_address)
            return False

        # Check SMTP config
        if not SMTP_USER or not SMTP_PASS:
            logger.warning(
                "SMTP not configured. Set AEGIS_SMTP_HOST, AEGIS_SMTP_USER, "
                "AEGIS_SMTP_PASS, AEGIS_SMTP_FROM env vars. "
                "Morning email NOT sent to <%s>.",
                to_address,
            )
            return False

        try:
            subject = self.build_subject()
            html_body = self.build_html()
            plain_body = self.build_plain_text()

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = to_address

            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, [to_address], msg.as_string())

            _last_send_ts = time.monotonic()
            logger.info("Morning email sent to <%s>: %s", to_address, subject)
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check AEGIS_SMTP_USER / AEGIS_SMTP_PASS.")
        except smtplib.SMTPException as exc:
            logger.error("SMTP error sending morning email to <%s>: %s", to_address, exc)
        except OSError as exc:
            logger.error("Network error sending morning email to <%s>: %s", to_address, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error sending morning email: %s", exc)

        return False


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def send_morning_email(to_address: str) -> bool:
    """Send the Aegis morning brief + scorecard email to the given address.

    This is the main entry point for easy calling:
        from morning_email import send_morning_email
        success = send_morning_email("trader@example.com")

    Returns True if the email was sent successfully, False otherwise.
    """
    sender = MorningEmailSender()
    return sender.send(to_address)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aegis Morning Email Sender")
    parser.add_argument("--to", type=str, help="Recipient email address")
    parser.add_argument("--preview", action="store_true", help="Print HTML to stdout instead of sending")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    sender = MorningEmailSender()

    if args.preview:
        print(sender.build_html())
    elif args.to:
        ok = sender.send(args.to)
        print(f"Sent: {ok}")
    else:
        print("Usage: python morning_email.py --to trader@example.com")
        print("       python morning_email.py --preview")
