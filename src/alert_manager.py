"""Alert Manager — Price alerts, signal alerts, and multi-channel notifications.

Supports:
- Price threshold alerts (above/below/% change)
- Technical indicator alerts (RSI, MACD crossover)
- Signal change alerts (when Aegis signal flips)
- Notification channels: Email (SMTP), Discord/Telegram webhooks
"""

import json
import re
import smtplib
import ssl
import time
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from urllib.request import Request, urlopen

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
ALERTS_PATH = MEMORY_DIR / "alerts.json"
ALERT_HISTORY_PATH = MEMORY_DIR / "alert_history.json"

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

_last_notification: dict[str, float] = {}  # channel -> last send timestamp
NOTIFICATION_COOLDOWN = 60  # seconds between notifications per channel

# ---------------------------------------------------------------------------
# Helpers — validation & sanitization
# ---------------------------------------------------------------------------

def _validate_webhook_url(url: str) -> bool:
    """Validate that a webhook URL uses http(s) scheme."""
    return bool(re.match(r'^https?://', url)) if url else False


def _sanitize_message(text: str) -> str:
    """Sanitize user-supplied alert messages to prevent injection.

    Strips HTML/script tags and limits length.
    """
    if not text:
        return text
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', '', text)
    # Remove common injection patterns (JS event handlers, script URIs)
    cleaned = re.sub(r'(?i)(javascript|on\w+)\s*[:=]', '', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Limit length to prevent abuse
    return cleaned[:500]


def _rate_limit_ok(channel: str) -> bool:
    """Return True if enough time has passed since the last notification on *channel*."""
    now = time.monotonic()
    last = _last_notification.get(channel, 0.0)
    if now - last < NOTIFICATION_COOLDOWN:
        return False
    _last_notification[channel] = now
    return True


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _load_alerts() -> dict:
    if not ALERTS_PATH.exists():
        return {"alerts": [], "config": _default_config()}
    try:
        return json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"alerts": [], "config": _default_config()}


def _save_alerts(data: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _default_config() -> dict:
    return {
        "email_enabled": False,
        "email_smtp": "",
        "email_port": 587,
        "email_user": "",
        "email_pass": "",
        "email_to": "",
        "discord_webhook": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
    }


# ---------------------------------------------------------------------------
# Alert CRUD
# ---------------------------------------------------------------------------

def add_alert(
    asset: str,
    ticker: str,
    alert_type: str,
    condition: str,
    threshold: float,
    message: str = "",
    repeat: bool = False,
) -> dict:
    """Create a new alert.

    Args:
        asset: Asset name (e.g. "Gold").
        ticker: Yahoo ticker.
        alert_type: "price", "rsi", "signal_change", "pct_change".
        condition: "above", "below", "crosses_above", "crosses_below".
        threshold: Trigger value.
        message: Custom message.
        repeat: If True the alert stays active after triggering.
    """
    data = _load_alerts()
    safe_message = _sanitize_message(message) or f"{asset} {alert_type} {condition} {threshold}"
    alert = {
        "id": uuid.uuid4().hex[:8],
        "asset": asset,
        "ticker": ticker,
        "alert_type": alert_type,
        "condition": condition,
        "threshold": threshold,
        "message": safe_message,
        "active": True,
        "repeat": repeat,
        "triggered_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_triggered": None,
    }
    data["alerts"].append(alert)
    _save_alerts(data)
    return alert


def get_alerts(active_only: bool = True) -> list[dict]:
    """Get all alerts."""
    data = _load_alerts()
    alerts = data["alerts"]
    if active_only:
        alerts = [a for a in alerts if a.get("active", True)]
    return alerts


def delete_alert(alert_id: str) -> bool:
    """Delete an alert by ID."""
    data = _load_alerts()
    original_len = len(data["alerts"])
    data["alerts"] = [a for a in data["alerts"] if a["id"] != alert_id]
    if len(data["alerts"]) < original_len:
        _save_alerts(data)
        return True
    return False


def toggle_alert(alert_id: str) -> bool:
    """Toggle alert active/inactive."""
    data = _load_alerts()
    for a in data["alerts"]:
        if a["id"] == alert_id:
            a["active"] = not a.get("active", True)
            _save_alerts(data)
            return True
    return False


def get_config() -> dict:
    return _load_alerts().get("config", _default_config())


def save_notification_config(config: dict) -> None:
    data = _load_alerts()
    data["config"] = config
    _save_alerts(data)


# ---------------------------------------------------------------------------
# Alert checking
# ---------------------------------------------------------------------------

def check_alerts(live_prices: dict, watchlist: dict | None = None) -> list[dict]:
    """Check all active alerts against current data.

    Args:
        live_prices: {asset_name: current_price}
        watchlist: Optional watchlist dict with signal_label, rsi, etc.

    Returns:
        List of triggered alert dicts.
    """
    data = _load_alerts()
    triggered = []
    now = datetime.now(timezone.utc).isoformat()

    for alert in data["alerts"]:
        if not alert.get("active", True):
            continue

        asset = alert["asset"]
        price = live_prices.get(asset, 0)
        if not price:
            continue

        fire = False
        atype = alert["alert_type"]
        cond = alert["condition"]
        thresh = alert["threshold"]

        if atype == "price":
            if cond == "above" and price >= thresh:
                fire = True
            elif cond == "below" and price <= thresh:
                fire = True

        elif atype == "rsi" and watchlist:
            rsi = watchlist.get(asset, {}).get("rsi", 50)
            if cond == "above" and rsi >= thresh:
                fire = True
            elif cond == "below" and rsi <= thresh:
                fire = True

        elif atype == "pct_change":
            chg = watchlist.get(asset, {}).get("price_change_pct", 0) if watchlist else 0
            if cond == "above" and chg >= thresh:
                fire = True
            elif cond == "below" and chg <= thresh:
                fire = True

        elif atype == "signal_change" and watchlist:
            signal = watchlist.get(asset, {}).get("signal_label", "")
            # threshold stores the signal we're watching for (encoded as string)
            if signal and str(thresh).upper() in signal.upper():
                fire = True

        if fire:
            alert["triggered_count"] = alert.get("triggered_count", 0) + 1
            alert["last_triggered"] = now
            # Deactivate only if the alert is not set to repeat
            if not alert.get("repeat", False):
                alert["active"] = False
            triggered.append({
                **alert,
                "current_price": price,
                "triggered_at": now,
            })

    if triggered:
        _save_alerts(data)
        _record_history(triggered)

    return triggered


def _record_history(triggered: list[dict]) -> None:
    """Append triggered alerts to history."""
    history = []
    if ALERT_HISTORY_PATH.exists():
        try:
            history = json.loads(ALERT_HISTORY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    history.extend(triggered)
    history = history[-500:]  # keep last 500
    ALERT_HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def get_alert_history(limit: int = 50) -> list[dict]:
    """Get recent alert history."""
    if not ALERT_HISTORY_PATH.exists():
        return []
    try:
        history = json.loads(ALERT_HISTORY_PATH.read_text(encoding="utf-8"))
        return list(reversed(history[-limit:]))
    except (json.JSONDecodeError, OSError):
        return []


# ---------------------------------------------------------------------------
# Notification dispatch
# ---------------------------------------------------------------------------

def send_notifications(triggered: list[dict]) -> list[str]:
    """Send notifications for triggered alerts. Returns list of status messages."""
    config = get_config()
    results = []

    for alert in triggered:
        msg = f"AEGIS ALERT: {alert['message']} | Price: ${alert.get('current_price', 0):,.2f}"

        # Email
        if config.get("email_enabled") and config.get("email_smtp"):
            if not _rate_limit_ok("email"):
                results.append(f"Email skipped (rate limited) for {alert['asset']}")
            else:
                try:
                    _send_email(config, msg)
                    results.append(f"Email sent for {alert['asset']}")
                except Exception as e:
                    results.append(f"Email failed: {e}")

        # Discord
        if config.get("discord_webhook"):
            webhook = config["discord_webhook"]
            if not _validate_webhook_url(webhook):
                results.append("Discord skipped: invalid webhook URL")
            elif not _rate_limit_ok("discord"):
                results.append(f"Discord skipped (rate limited) for {alert['asset']}")
            else:
                try:
                    _send_discord(webhook, msg)
                    results.append(f"Discord sent for {alert['asset']}")
                except Exception as e:
                    results.append(f"Discord failed: {e}")

        # Telegram
        if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
            if not _rate_limit_ok("telegram"):
                results.append(f"Telegram skipped (rate limited) for {alert['asset']}")
            else:
                try:
                    _send_telegram(config["telegram_bot_token"], config["telegram_chat_id"], msg)
                    results.append(f"Telegram sent for {alert['asset']}")
                except Exception as e:
                    results.append(f"Telegram failed: {e}")

    return results


def _send_email(config: dict, message: str) -> None:
    msg = MIMEText(message)
    msg["Subject"] = "Aegis Trading Alert"
    msg["From"] = config["email_user"]
    msg["To"] = config["email_to"]
    context = ssl.create_default_context()
    with smtplib.SMTP(config["email_smtp"], config.get("email_port", 587)) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(config["email_user"], config["email_pass"])
        server.send_message(msg)


def _send_discord(webhook_url: str, message: str) -> None:
    payload = json.dumps({"content": message}).encode()
    req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=10)


def _send_telegram(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    urlopen(req, timeout=10)
