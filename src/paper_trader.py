"""Paper Trading Simulator for Project Aegis.

Simulates trading with virtual cash. Positions are opened/closed against
live market prices fetched by the dashboard.  State persists to a
per-user JSON file when ``set_user()`` has been called, or falls back to
the legacy ``memory/paper_portfolio.json`` for headless/default mode.

Enhanced with:
- Stop-loss / take-profit / trailing stop
- Advanced order types (limit, stop-limit)
- Trade journal with tags
- CSV export
- Per-user data isolation via set_user()
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = _PROJECT_ROOT / "memory"
_USERS_DIR = _PROJECT_ROOT / "users"

# Default (legacy) path — used by headless brain loop & guests
_DEFAULT_PORTFOLIO_PATH = MEMORY_DIR / "paper_portfolio.json"

# Active portfolio path — changed by set_user()
PORTFOLIO_PATH = _DEFAULT_PORTFOLIO_PATH

_DEFAULT_BALANCE = 1000.0


# ---------------------------------------------------------------------------
# Per-user routing
# ---------------------------------------------------------------------------

def set_user(user_id: str = "default") -> None:
    """Switch the active portfolio to the given user's data directory.

    Call this once per session (e.g. after authentication in the dashboard)
    to ensure all paper_trader operations read/write the correct file.

    Args:
        user_id: The authenticated user's ID, or ``"default"`` for
                 the legacy global portfolio in ``memory/``.
    """
    global PORTFOLIO_PATH
    if user_id and user_id != "default":
        user_dir = _USERS_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        PORTFOLIO_PATH = user_dir / "paper_portfolio.json"
    else:
        PORTFOLIO_PATH = _DEFAULT_PORTFOLIO_PATH


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    if not PORTFOLIO_PATH.exists():
        return _blank_portfolio(_DEFAULT_BALANCE)
    try:
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _blank_portfolio(_DEFAULT_BALANCE)


def _save(data: dict) -> bool:
    """Persist portfolio data to disk.

    Returns True on success, False on failure.
    """
    _target = PORTFOLIO_PATH
    try:
        _target.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file first, then rename for atomicity.
        tmp_path = _target.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(_target)
        return True
    except OSError:
        # Fall back to direct write if rename fails (e.g. cross-device).
        try:
            with open(_target, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False


def _blank_portfolio(balance: float) -> dict:
    return {
        "starting_balance": balance,
        "cash": balance,
        "open_positions": [],
        "trade_history": [],
        "equity_curve": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def open_position(
    asset: str,
    ticker: str,
    direction: str,
    usd_amount: float,
    price: float,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    trailing_stop_pct: float | None = None,
    order_type: str = "market",
    limit_price: float | None = None,
    tags: list[str] | None = None,
    signal_hint: str = "",
) -> dict:
    """Open a new paper position.

    Args:
        asset: Human name (e.g. "Gold").
        ticker: Yahoo Finance ticker (e.g. "GC=F").
        direction: "long" or "short".
        usd_amount: Dollar amount to invest.
        price: Current market price used as entry.
        stop_loss: Stop-loss price (optional).
        take_profit: Take-profit price (optional).
        trailing_stop_pct: Trailing stop percentage (optional).
        order_type: "market", "limit", or "stop_limit".
        limit_price: Price for limit/stop-limit orders.
        tags: Journal tags (e.g. ["momentum", "rsi_oversold"]).
        signal_hint: Aegis signal that suggested this trade.

    Returns:
        The created position dict, or an error dict.
    """
    data = _load()

    if usd_amount <= 0:
        return {"error": "Amount must be positive."}
    if usd_amount > data["cash"]:
        return {"error": f"Insufficient cash. Available: ${data['cash']:.2f}"}
    if price <= 0:
        return {"error": "Price must be positive."}

    # For limit orders, queue as pending — RESERVE cash to prevent overspending
    if order_type in ("limit", "stop_limit") and limit_price:
        pending = {
            "id": uuid.uuid4().hex[:8],
            "asset": asset,
            "ticker": ticker,
            "direction": direction,
            "usd_amount": round(usd_amount, 2),
            "order_type": order_type,
            "limit_price": limit_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "trailing_stop_pct": trailing_stop_pct,
            "tags": tags or [],
            "signal_hint": signal_hint,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data["cash"] = round(data["cash"] - usd_amount, 2)  # Reserve cash
        data.setdefault("pending_orders", []).append(pending)
        _save(data)
        return {**pending, "message": f"Limit order queued at ${limit_price:,.2f} (${usd_amount:.2f} reserved)"}

    quantity = usd_amount / price
    position = {
        "id": uuid.uuid4().hex[:8],
        "asset": asset,
        "ticker": ticker,
        "direction": direction,
        "quantity": quantity,
        "entry_price": price,
        "usd_amount": round(usd_amount, 2),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "trailing_stop_pct": trailing_stop_pct,
        "highest_price": price,
        "lowest_price": price,
        "order_type": order_type,
        "tags": tags or [],
        "signal_hint": signal_hint,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }

    data["cash"] = round(data["cash"] - usd_amount, 2)
    data["open_positions"].append(position)
    _save(data)
    return position


def close_position(position_id: str, price: float, exit_reason: str = "manual") -> dict:
    """Close an open position at *price*.

    Args:
        position_id: The position ID.
        price: Exit price.
        exit_reason: "manual", "stop_loss", "take_profit", "trailing_stop".

    Returns:
        The closed trade record, or an error dict.
    """
    data = _load()
    pos = None
    for p in data["open_positions"]:
        if p["id"] == position_id:
            pos = p
            break
    if pos is None:
        return {"error": "Position not found."}

    if pos["direction"] == "long":
        pnl = (price - pos["entry_price"]) * pos["quantity"]
    else:
        pnl = (pos["entry_price"] - price) * pos["quantity"]

    cash_returned = pos["usd_amount"] + pnl

    trade = {
        "id": pos["id"],
        "asset": pos["asset"],
        "ticker": pos["ticker"],
        "direction": pos["direction"],
        "quantity": pos["quantity"],
        "entry_price": pos["entry_price"],
        "exit_price": price,
        "usd_amount": pos["usd_amount"],
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl / pos["usd_amount"] * 100, 2) if pos["usd_amount"] else 0,
        "exit_reason": exit_reason,
        "tags": pos.get("tags", []),
        "signal_hint": pos.get("signal_hint", ""),
        "opened_at": pos["opened_at"],
        "closed_at": datetime.now(timezone.utc).isoformat(),
    }
    # Carry over notes from position to closed trade
    if pos.get("notes"):
        trade["notes"] = pos["notes"]

    data["open_positions"] = [p for p in data["open_positions"] if p["id"] != position_id]
    data["cash"] = round(data["cash"] + cash_returned, 2)
    # Cash floor: never allow negative cash (can happen on large short losses)
    if data["cash"] < 0:
        import logging
        logging.getLogger("aegis.paper_trader").warning(
            "Cash went negative ($%.2f) after closing %s %s — clamped to $0 (margin call).",
            data["cash"], pos["direction"], pos["asset"],
        )
        data["cash"] = 0.0
    data["trade_history"].append(trade)
    _save(data)
    return trade


def get_open_positions_with_pnl(live_prices: dict) -> list[dict]:
    """Return open positions enriched with current price & unrealized P&L.

    Args:
        live_prices: ``{asset_name: current_price}`` dict from dashboard.
    """
    data = _load()
    enriched = []
    for pos in data["open_positions"]:
        current = live_prices.get(pos["asset"], pos["entry_price"])
        if pos["direction"] == "long":
            pnl = (current - pos["entry_price"]) * pos["quantity"]
        else:
            pnl = (pos["entry_price"] - current) * pos["quantity"]
        enriched.append({
            **pos,
            "current_price": current,
            "unrealized_pnl": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl / pos["usd_amount"] * 100, 2) if pos["usd_amount"] else 0,
        })
    return enriched


def get_portfolio_summary(live_prices: dict) -> dict:
    """Compute portfolio metrics using live prices."""
    data = _load()
    positions = get_open_positions_with_pnl(live_prices)
    open_pnl = sum(p["unrealized_pnl"] for p in positions)
    positions_value = sum(p["usd_amount"] + p["unrealized_pnl"] for p in positions)
    equity = data["cash"] + positions_value

    history = data["trade_history"]
    # Exclude contaminated trades from stats (flagged by migration script)
    clean_history = [t for t in history if t.get("data_quality") != "contaminated"]
    wins = sum(1 for t in clean_history if t["pnl"] > 0)
    losses = sum(1 for t in clean_history if t["pnl"] < 0)
    total_closed = wins + losses
    win_rate = round(wins / total_closed * 100, 1) if total_closed else 0
    realized_pnl = sum(t["pnl"] for t in clean_history)

    starting = data.get("starting_balance", _DEFAULT_BALANCE)
    total_return = round((equity - starting) / starting * 100, 2) if starting else 0

    return {
        "cash": data["cash"],
        "equity": round(equity, 2),
        "open_pnl": round(open_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "total_return_pct": total_return,
        "starting_balance": starting,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_trades": len(history),
        "open_count": len(positions),
    }


def get_trade_history(include_contaminated: bool = False) -> list[dict]:
    """Return closed trades, most recent first.

    Args:
        include_contaminated: If False (default), excludes trades flagged
            with ``data_quality == "contaminated"`` from price contamination.
    """
    data = _load()
    history = data["trade_history"]
    if not include_contaminated:
        history = [t for t in history if t.get("data_quality") != "contaminated"]
    return list(reversed(history))


def record_equity_snapshot(live_prices: dict) -> None:
    """Append an equity data-point (throttled to at most once per minute)."""
    data = _load()
    curve = data.get("equity_curve", [])
    now = datetime.now(timezone.utc)

    # Throttle: skip if last snapshot < 60 s ago
    if curve:
        last_ts = curve[-1].get("t", "")
        try:
            last_dt = datetime.fromisoformat(last_ts)
            if (now - last_dt).total_seconds() < 60:
                return
        except (ValueError, TypeError):
            pass

    summary = get_portfolio_summary(live_prices)
    curve.append({
        "t": now.isoformat(),
        "equity": summary["equity"],
        "cash": summary["cash"],
    })

    # Keep last 1440 points (~24 h at 1/min)
    data["equity_curve"] = curve[-1440:]
    _save(data)


def get_equity_curve() -> list[dict]:
    """Return equity curve data for charting."""
    return _load().get("equity_curve", [])


def reset_portfolio(balance: float | None = None) -> dict:
    """Wipe everything and start fresh.

    Args:
        balance: Starting cash (defaults to 1000).

    Returns:
        The fresh portfolio dict.
    """
    bal = balance if balance and balance > 0 else _DEFAULT_BALANCE
    data = _blank_portfolio(bal)
    _save(data)
    return data


def get_cash() -> float:
    """Return current cash balance."""
    return _load()["cash"]


# ---------------------------------------------------------------------------
# Risk management: automated exits
# ---------------------------------------------------------------------------

def check_automated_exits(live_prices: dict) -> list[dict]:
    """Check all open positions for stop-loss/take-profit/trailing stop triggers.

    Automatically closes triggered positions. Returns list of closed trades.

    This function performs all operations on a single loaded copy of the
    portfolio data to avoid stale-read issues that occur when close_position
    re-loads from disk.  highest_price / lowest_price are updated in-place
    and persisted so trailing-stop state survives across Streamlit refreshes.
    """
    data = _load()
    closed = []
    remaining_positions = []

    for pos in data["open_positions"]:
        price = live_prices.get(pos["asset"])
        if not price:
            remaining_positions.append(pos)
            continue

        direction = pos.get("direction", "long")

        # ------------------------------------------------------------------
        # Persist highest/lowest price for trailing stop tracking.
        # These values are written back to the JSON so they survive between
        # Streamlit page refreshes and server restarts.
        # ------------------------------------------------------------------
        if direction == "long":
            pos["highest_price"] = max(pos.get("highest_price", pos["entry_price"]), price)
        else:
            pos["lowest_price"] = min(pos.get("lowest_price", pos["entry_price"]), price)

        sl = pos.get("stop_loss")
        tp = pos.get("take_profit")
        trail_pct = pos.get("trailing_stop_pct")

        exit_reason = None

        if direction == "long":
            if sl and price <= sl:
                exit_reason = "stop_loss"
            elif tp and price >= tp:
                exit_reason = "take_profit"
            elif trail_pct:
                trail_price = pos["highest_price"] * (1 - trail_pct / 100)
                if price <= trail_price:
                    exit_reason = "trailing_stop"
        else:  # short
            if sl and price >= sl:
                exit_reason = "stop_loss"
            elif tp and price <= tp:
                exit_reason = "take_profit"
            elif trail_pct:
                trail_price = pos["lowest_price"] * (1 + trail_pct / 100)
                if price >= trail_price:
                    exit_reason = "trailing_stop"

        if exit_reason:
            # ---- inline close: operate on the same `data` dict ----
            if direction == "long":
                pnl = (price - pos["entry_price"]) * pos["quantity"]
            else:
                pnl = (pos["entry_price"] - price) * pos["quantity"]

            cash_returned = pos["usd_amount"] + pnl

            trade = {
                "id": pos["id"],
                "asset": pos["asset"],
                "ticker": pos["ticker"],
                "direction": pos["direction"],
                "quantity": pos["quantity"],
                "entry_price": pos["entry_price"],
                "exit_price": price,
                "usd_amount": pos["usd_amount"],
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / pos["usd_amount"] * 100, 2) if pos["usd_amount"] else 0,
                "exit_reason": exit_reason,
                "tags": pos.get("tags", []),
                "signal_hint": pos.get("signal_hint", ""),
                "opened_at": pos["opened_at"],
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }
            data["cash"] = round(data["cash"] + cash_returned, 2)
            data["trade_history"].append(trade)
            closed.append(trade)
            # Position is NOT added to remaining_positions -> removed.
        else:
            remaining_positions.append(pos)

    # Write back all mutations in one atomic save: updated high/low prices
    # for surviving positions AND any closed trades.
    data["open_positions"] = remaining_positions
    _save(data)

    return closed


def check_pending_orders(live_prices: dict) -> list[dict]:
    """Check pending limit/stop-limit orders and fill them if price matches."""
    data = _load()
    pending = data.get("pending_orders", [])
    filled = []

    remaining = []
    for order in pending:
        price = live_prices.get(order["asset"])
        if not price:
            remaining.append(order)
            continue

        should_fill = False
        if order["order_type"] == "limit":
            if order["direction"] == "long" and price <= order["limit_price"]:
                should_fill = True
            elif order["direction"] == "short" and price >= order["limit_price"]:
                should_fill = True
        elif order["order_type"] == "stop_limit":
            if order["direction"] == "long" and price >= order["limit_price"]:
                should_fill = True
            elif order["direction"] == "short" and price <= order["limit_price"]:
                should_fill = True

        if should_fill:
            # ---- inline fill: operate on the same `data` dict ----
            # Cash was already reserved (deducted) when the limit order was
            # placed (see open_position, line 140), so we do NOT deduct again.
            usd_amount = order["usd_amount"]
            if price <= 0:
                remaining.append(order)
                continue

            quantity = usd_amount / price
            position = {
                "id": uuid.uuid4().hex[:8],
                "asset": order["asset"],
                "ticker": order["ticker"],
                "direction": order["direction"],
                "quantity": quantity,
                "entry_price": price,
                "usd_amount": round(usd_amount, 2),
                "stop_loss": order.get("stop_loss"),
                "take_profit": order.get("take_profit"),
                "trailing_stop_pct": order.get("trailing_stop_pct"),
                "highest_price": price,
                "lowest_price": price,
                "order_type": "filled_limit",
                "tags": order.get("tags", []),
                "signal_hint": order.get("signal_hint", ""),
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }

            data["open_positions"].append(position)

            # Record the fill in trade history as an informational entry
            data["trade_history"].append({
                "id": position["id"],
                "asset": order["asset"],
                "ticker": order["ticker"],
                "direction": order["direction"],
                "quantity": quantity,
                "entry_price": price,
                "usd_amount": round(usd_amount, 2),
                "order_type": order["order_type"],
                "limit_price": order.get("limit_price"),
                "filled_at": datetime.now(timezone.utc).isoformat(),
                "event": "limit_order_filled",
                "tags": order.get("tags", []),
                "signal_hint": order.get("signal_hint", ""),
            })

            filled.append(position)
        else:
            remaining.append(order)

    data["pending_orders"] = remaining
    _save(data)
    return filled


def get_pending_orders() -> list[dict]:
    """Return pending limit/stop-limit orders."""
    return _load().get("pending_orders", [])


def cancel_order(order_id: str) -> bool:
    """Cancel a pending order and refund reserved cash."""
    data = _load()
    pending = data.get("pending_orders", [])
    cancelled = None
    remaining = []
    for o in pending:
        if o["id"] == order_id and cancelled is None:
            cancelled = o
        else:
            remaining.append(o)
    if cancelled:
        data["pending_orders"] = remaining
        data["cash"] = round(data["cash"] + cancelled["usd_amount"], 2)  # Refund reserved cash
        _save(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Trade journal
# ---------------------------------------------------------------------------

def add_journal_note(trade_id: str, note: str) -> bool:
    """Add a journal note to a closed trade."""
    data = _load()
    for t in data["trade_history"]:
        if t["id"] == trade_id:
            t.setdefault("journal_notes", []).append({
                "note": note,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            _save(data)
            return True
    return False


def add_trade_tags(trade_id: str, tags: list[str]) -> bool:
    """Add tags to a closed trade."""
    data = _load()
    for t in data["trade_history"]:
        if t["id"] == trade_id:
            existing = set(t.get("tags", []))
            existing.update(tags)
            t["tags"] = sorted(existing)
            _save(data)
            return True
    return False


def save_trade_note(trade_id: str, note: str) -> bool:
    """Save or update a note on a closed trade (single note per trade).

    Args:
        trade_id: The trade ID.
        note: The note text. Empty string clears the note.

    Returns:
        True on success, False if trade not found.
    """
    data = _load()
    for t in data["trade_history"]:
        if t["id"] == trade_id:
            t["notes"] = note.strip()
            _save(data)
            return True
    return False


def save_position_note(position_id: str, note: str) -> bool:
    """Save or update a note on an open position.

    Args:
        position_id: The position ID.
        note: The note text. Empty string clears the note.

    Returns:
        True on success, False if position not found.
    """
    data = _load()
    for p in data["open_positions"]:
        if p["id"] == position_id:
            p["notes"] = note.strip()
            _save(data)
            return True
    return False


# ---------------------------------------------------------------------------
# Position modification
# ---------------------------------------------------------------------------

def update_stop_loss(position_id: str, new_stop_loss: float | None) -> dict:
    """Update the stop-loss price for an open position.

    Args:
        position_id: The position ID.
        new_stop_loss: New stop-loss price, or None to remove.

    Returns:
        Updated position dict, or error dict.
    """
    data = _load()
    for p in data["open_positions"]:
        if p["id"] == position_id:
            p["stop_loss"] = new_stop_loss
            _save(data)
            return p
    return {"error": "Position not found."}


def update_take_profit(position_id: str, new_take_profit: float | None) -> dict:
    """Update the take-profit price for an open position.

    Args:
        position_id: The position ID.
        new_take_profit: New take-profit price, or None to remove.

    Returns:
        Updated position dict, or error dict.
    """
    data = _load()
    for p in data["open_positions"]:
        if p["id"] == position_id:
            p["take_profit"] = new_take_profit
            _save(data)
            return p
    return {"error": "Position not found."}


def partial_close(position_id: str, close_pct: float, price: float) -> dict:
    """Close a portion of an open position.

    Creates a closed trade entry for the closed portion and reduces the
    remaining position size proportionally.

    Args:
        position_id: The position ID.
        close_pct: Percentage to close (0-100 exclusive; use close_position for 100%).
        price: Current market price for the closed portion.

    Returns:
        The closed trade record for the portion, or an error dict.
    """
    if close_pct <= 0 or close_pct >= 100:
        return {"error": "Percentage must be between 0 and 100 (exclusive)."}

    data = _load()
    pos = None
    pos_idx = None
    for i, p in enumerate(data["open_positions"]):
        if p["id"] == position_id:
            pos = p
            pos_idx = i
            break
    if pos is None:
        return {"error": "Position not found."}

    fraction = close_pct / 100.0
    closed_qty = pos["quantity"] * fraction
    closed_usd = pos["usd_amount"] * fraction
    remaining_qty = pos["quantity"] - closed_qty
    remaining_usd = pos["usd_amount"] - closed_usd

    # Calculate P&L for the closed portion
    if pos["direction"] == "long":
        pnl = (price - pos["entry_price"]) * closed_qty
    else:
        pnl = (pos["entry_price"] - price) * closed_qty

    cash_returned = closed_usd + pnl

    # Build the closed trade record
    trade = {
        "id": uuid.uuid4().hex[:8],
        "asset": pos["asset"],
        "ticker": pos["ticker"],
        "direction": pos["direction"],
        "quantity": closed_qty,
        "entry_price": pos["entry_price"],
        "exit_price": price,
        "usd_amount": round(closed_usd, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl / closed_usd * 100, 2) if closed_usd else 0,
        "exit_reason": f"partial_close_{int(close_pct)}pct",
        "tags": pos.get("tags", []),
        "signal_hint": pos.get("signal_hint", ""),
        "opened_at": pos["opened_at"],
        "closed_at": datetime.now(timezone.utc).isoformat(),
    }
    # Carry over notes if present
    if pos.get("notes"):
        trade["notes"] = pos["notes"]

    # Update the remaining position in-place
    data["open_positions"][pos_idx]["quantity"] = remaining_qty
    data["open_positions"][pos_idx]["usd_amount"] = round(remaining_usd, 2)

    # Return cash and record the trade
    data["cash"] = round(data["cash"] + cash_returned, 2)
    data["trade_history"].append(trade)
    _save(data)
    return trade


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_trades_csv() -> str:
    """Export trade history as CSV string."""
    history = get_trade_history()
    if not history:
        return ""

    output = io.StringIO()
    fields = [
        "id", "asset", "ticker", "direction", "quantity",
        "entry_price", "exit_price", "usd_amount", "pnl", "pnl_pct",
        "exit_reason", "tags", "signal_hint", "notes", "opened_at", "closed_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for trade in history:
        row = {**trade}
        row["tags"] = "; ".join(trade.get("tags", []))
        writer.writerow(row)

    return output.getvalue()


def export_equity_csv() -> str:
    """Export equity curve as CSV string."""
    curve = get_equity_curve()
    if not curve:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["t", "equity", "cash"])
    writer.writeheader()
    writer.writerows(curve)
    return output.getvalue()
