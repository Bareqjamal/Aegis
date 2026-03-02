"""Telegram Signal Notifier — sends trading alerts via Telegram bot.

Sends formatted trading signals, trade alerts, and morning brief summaries
to a Telegram chat via the Bot API using the requests library (no extra deps).

Config priority:
    1. Constructor args (bot_token, chat_id)
    2. Environment variables (AEGIS_TELEGRAM_BOT_TOKEN, AEGIS_TELEGRAM_CHAT_ID)
    3. JSON file (src/data/telegram_config.json) for Settings page persistence

Usage:
    from telegram_notifier import TelegramNotifier
    notifier = TelegramNotifier(bot_token="...", chat_id="...")
    notifier.send_signal_alert("Gold", "STRONG BUY", 78, 2846.50, "+1.2%")
    notifier.send_trade_alert("Gold", "LONG", 2846.50, "opened")
    notifier.send_brief_summary({"headline": "...", "top_picks": [...]})
"""

import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
TELEGRAM_CONFIG_FILE = DATA_DIR / "telegram_config.json"

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"

# Rate limiting: max 30 messages per hour (Telegram bot limit is 30/sec for
# groups but we keep it conservative for a personal alerting channel)
MAX_MESSAGES_PER_HOUR = 30

logger = logging.getLogger("aegis.telegram")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json_config() -> dict:
    """Load Telegram config from the JSON file (Settings page persistence)."""
    if not TELEGRAM_CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(TELEGRAM_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load telegram config: %s", exc)
        return {}


def _save_json_config(config: dict) -> None:
    """Persist Telegram config to JSON for the Settings page."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        TELEGRAM_CONFIG_FILE.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Failed to save telegram config: %s", exc)


def _escape_markdown(text: str) -> str:
    """Escape special Markdown characters for Telegram MarkdownV1.

    Telegram's Markdown parse mode requires escaping of _ * [ ` characters
    inside non-formatting text.  We escape conservatively — only within
    user-supplied strings, not our own formatting.
    """
    for ch in ("_", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


# ---------------------------------------------------------------------------
# TelegramNotifier
# ---------------------------------------------------------------------------

class TelegramNotifier:
    """Send trading alerts to a Telegram chat via the Bot API."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        # Resolve config: constructor > env vars > JSON file
        json_cfg = _load_json_config()

        self.bot_token: str = (
            bot_token
            or os.environ.get("AEGIS_TELEGRAM_BOT_TOKEN", "")
            or json_cfg.get("bot_token", "")
        )
        self.chat_id: str = (
            chat_id
            or os.environ.get("AEGIS_TELEGRAM_CHAT_ID", "")
            or json_cfg.get("chat_id", "")
        )

        # Rate limiter: deque of monotonic timestamps for the last hour
        self._send_timestamps: deque[float] = deque(maxlen=MAX_MESSAGES_PER_HOUR)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True if both bot_token and chat_id are set."""
        return bool(self.bot_token and self.chat_id)

    def save_config(self) -> None:
        """Persist current bot_token and chat_id to the JSON config file."""
        _save_json_config({
            "bot_token": self.bot_token,
            "chat_id": self.chat_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _rate_limit_ok(self) -> bool:
        """Return True if we haven't exceeded MAX_MESSAGES_PER_HOUR."""
        now = time.monotonic()
        # Purge timestamps older than 1 hour
        while self._send_timestamps and (now - self._send_timestamps[0]) > 3600:
            self._send_timestamps.popleft()
        if len(self._send_timestamps) >= MAX_MESSAGES_PER_HOUR:
            logger.warning(
                "Telegram rate limit reached (%d messages in the last hour).",
                MAX_MESSAGES_PER_HOUR,
            )
            return False
        return True

    def _record_send(self) -> None:
        """Record a successful send timestamp for rate limiting."""
        self._send_timestamps.append(time.monotonic())

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def send_raw(self, text: str) -> bool:
        """Send any text message to the configured Telegram chat.

        Returns True on success, False on any failure. Never raises.
        """
        if not self.is_configured():
            logger.warning("Telegram not configured — skipping message.")
            return False

        if not self._rate_limit_ok():
            return False

        url = TELEGRAM_API_BASE.format(token=self.bot_token)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                self._record_send()
                return True
            else:
                logger.error(
                    "Telegram API error %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
        except requests.RequestException as exc:
            logger.error("Telegram send failed: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected Telegram error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Formatted messages
    # ------------------------------------------------------------------

    def send_signal_alert(
        self,
        asset: str,
        signal: str,
        confidence: int | float,
        price: float,
        change_pct: str,
        rsi_note: str = "",
        macd_note: str = "",
    ) -> bool:
        """Send a formatted signal alert card.

        Args:
            asset:       Asset name (e.g. "Gold").
            signal:      Signal label (e.g. "STRONG BUY").
            confidence:  Confidence score 0-100.
            price:       Current price.
            change_pct:  Price change string (e.g. "+1.2%").
            rsi_note:    Optional RSI note (e.g. "Oversold").
            macd_note:   Optional MACD note (e.g. "Bullish Cross").

        Returns True on success, False on failure. Never raises.
        """
        sig_upper = signal.upper()
        if "BUY" in sig_upper:
            icon = "\U0001f7e2"  # green circle
        elif "SELL" in sig_upper:
            icon = "\U0001f534"  # red circle
        else:
            icon = "\u26aa"      # white circle

        safe_asset = _escape_markdown(asset)
        indicator_parts = []
        if rsi_note:
            indicator_parts.append(f"RSI: {_escape_markdown(rsi_note)}")
        if macd_note:
            indicator_parts.append(f"MACD: {_escape_markdown(macd_note)}")
        indicators_line = " | ".join(indicator_parts) if indicator_parts else ""

        text = (
            f"{icon} *{sig_upper}* \u2014 {safe_asset}\n"
            f"Price: ${price:,.2f} ({_escape_markdown(change_pct)})\n"
            f"Confidence: {int(confidence)}%"
        )
        if indicators_line:
            text += f"\n{indicators_line}"
        text += "\n\n_Aegis Signal Alert_"

        return self.send_raw(text)

    def send_trade_alert(
        self,
        asset: str,
        direction: str,
        price: float,
        action: str,
        pnl_pct: float | None = None,
    ) -> bool:
        """Send a trade notification (opened / closed).

        Args:
            asset:     Asset name.
            direction: "LONG" or "SHORT".
            price:     Entry or exit price.
            action:    "opened" or "closed".
            pnl_pct:  Realized P&L percentage (for closed trades).

        Returns True on success, False on failure. Never raises.
        """
        if action.lower() == "opened":
            icon = "\U0001f4c8"  # chart increasing
        else:
            icon = "\U0001f4c9"  # chart decreasing

        safe_asset = _escape_markdown(asset)
        text = (
            f"{icon} *Trade {action.capitalize()}*\n"
            f"{safe_asset} \u2014 {direction.upper()} @ ${price:,.2f}"
        )
        if pnl_pct is not None:
            pnl_icon = "\u2705" if pnl_pct >= 0 else "\u274c"
            text += f"\nP&L: {pnl_icon} {pnl_pct:+.2f}%"
        text += "\n\n_Aegis Auto-Trader_"

        return self.send_raw(text)

    def send_brief_summary(self, brief_data: dict[str, Any]) -> bool:
        """Send a condensed morning brief digest.

        Args:
            brief_data: Dict with keys: headline, top_picks (list), regime (dict).
                        Matches the output of MorningBrief.generate().

        Returns True on success, False on failure. Never raises.
        """
        headline = brief_data.get("headline", "No headline available.")
        top_picks = brief_data.get("top_picks", [])[:3]
        regime = brief_data.get("regime", {})
        regime_name = regime.get("name", "NEUTRAL") if isinstance(regime, dict) else "NEUTRAL"

        lines = [
            "\u2600\ufe0f *Aegis Morning Brief*",
            f"_{_escape_markdown(headline)}_",
            "",
            f"Regime: *{_escape_markdown(regime_name)}*",
            "",
        ]

        if top_picks:
            lines.append("*Top Signals:*")
            for i, pick in enumerate(top_picks[:3]):
                asset = pick.get("asset", "?")
                signal = pick.get("signal", "NEUTRAL")
                confidence = pick.get("confidence", 0)
                price = pick.get("price", 0)
                lines.append(
                    f"  {i + 1}. {_escape_markdown(asset)}: "
                    f"{signal} ({int(confidence)}%) @ ${price:,.2f}"
                )
        else:
            lines.append("No signals available. Run a scan first.")

        lines.append("")
        lines.append("_Open Aegis Terminal for full analysis_")

        return self.send_raw("\n".join(lines))


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def get_notifier() -> TelegramNotifier:
    """Return a TelegramNotifier pre-loaded from env / config file.

    Convenience function so callers don't need to manage config resolution:
        from telegram_notifier import get_notifier
        notifier = get_notifier()
        if notifier.is_configured():
            notifier.send_signal_alert(...)
    """
    return TelegramNotifier()
