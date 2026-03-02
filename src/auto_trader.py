"""Auto-Trading Engine — the bridge between signals and paper trades.

This is the module that makes Aegis actually trade while you sleep.
It receives scan results from the market scanner and decides whether
to open or skip a position, based on:

1. Signal strength (BUY/SELL + score)
2. Confidence level (must exceed threshold)
3. Lesson filter (consults past mistakes)
4. Risk limits (max positions, max exposure, drawdown)
5. Position sizing (Kelly or fixed-fractional)
6. Macro regime awareness (new: adjusts behavior by market regime)
7. Geopolitical risk overlay (new: reduces exposure during high-risk events)
8. Dynamic confidence thresholds (new: adapts per-asset based on history)

All trades are PAPER trades — no real money is ever at risk.

Usage:
    from auto_trader import AutoTrader
    trader = AutoTrader()
    decision = trader.evaluate_and_trade(scan_result, live_prices)
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "agent_logs.txt"
DECISIONS_FILE = PROJECT_ROOT / "memory" / "trade_decisions.json"
BOT_LOG_FILE = PROJECT_ROOT / "memory" / "bot_activity.json"

# Imports — we use existing modules, no reinventing
import paper_trader
import risk_manager
from market_learner import MarketLearner

try:
    from config import AutoTradeConfig, apply_settings_override
    # Apply user settings so AutoTradeConfig reflects settings_override.json
    apply_settings_override()
except ImportError:
    apply_settings_override = None
    class AutoTradeConfig:
        ENABLED = True
        MIN_CONFIDENCE_PCT = 65.0
        MAX_CONCURRENT_POSITIONS = 5
        MAX_POSITION_PCT = 20.0
        MIN_RISK_REWARD = 1.5
        ALLOWED_SIGNALS = ["BUY", "STRONG BUY", "SELL", "STRONG SELL"]
        COOLDOWN_HOURS = 6
        USE_LESSONS_FILTER = True
        DEFAULT_TRAILING_STOP_PCT = 3.0
        TRADE_DECISIONS_MAX = 500
        POSITION_SIZE_METHOD = "fixed_fractional"
        USE_REGIME_AWARENESS = True
        USE_GEO_RISK_OVERLAY = True
        USE_DYNAMIC_CONFIDENCE = True
        MAX_CORRELATED_POSITIONS = 3
        DRAWDOWN_PAUSE_PCT = -15.0
        DRAWDOWN_REDUCED_PCT = -10.0


# ---------------------------------------------------------------------------
# Regime & Geopolitical Intelligence
# ---------------------------------------------------------------------------

def _load_macro_regime() -> dict | None:
    """Load cached macro regime data."""
    regime_file = PROJECT_ROOT / "src" / "data" / "macro_regime.json"
    if regime_file.exists():
        try:
            return json.loads(regime_file.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"WARNING: macro_regime.json corrupted: {e} — proceeding without regime data")
    return None


def _load_geo_analysis() -> dict | None:
    """Load cached geopolitical analysis."""
    geo_file = PROJECT_ROOT / "src" / "data" / "geopolitical_analysis.json"
    if geo_file.exists():
        try:
            return json.loads(geo_file.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"WARNING: geopolitical_analysis.json corrupted: {e} — proceeding without geo data")
    return None


def _get_regime_adjustment(regime: dict | None, asset_name: str, direction: str) -> dict:
    """Get regime-based trading adjustment.

    Returns dict with:
        - confidence_boost: int (-20 to +20) adjustment to confidence threshold
        - size_multiplier: float (0.5 to 1.5) position size adjustment
        - skip_reason: str or None if regime says skip this trade
    """
    if not regime:
        return {"confidence_boost": 0, "size_multiplier": 1.0, "skip_reason": None}

    regime_name = regime.get("regime", "NEUTRAL")
    multipliers = regime.get("multipliers", {})
    asset_mult = multipliers.get(asset_name, 1.0)

    result = {"confidence_boost": 0, "size_multiplier": 1.0, "skip_reason": None}

    # Regime-specific logic
    if regime_name == "RISK_OFF":
        if direction == "long" and asset_name not in ("Gold", "Silver"):
            result["confidence_boost"] = 10  # Require higher confidence for longs in risk-off
            result["size_multiplier"] = 0.6  # Smaller positions
        elif direction == "short":
            result["confidence_boost"] = -5  # Lower bar for shorts in risk-off
            result["size_multiplier"] = 1.2

    elif regime_name == "RISK_ON":
        if direction == "long":
            result["confidence_boost"] = -5  # Lower bar for longs
            result["size_multiplier"] = 1.2
        elif direction == "short":
            result["confidence_boost"] = 10  # Higher bar for shorts in risk-on
            result["size_multiplier"] = 0.7

    elif regime_name == "HIGH_VOLATILITY":
        result["size_multiplier"] = 0.5  # Half size in volatile markets
        result["confidence_boost"] = 10  # Need high conviction

    elif regime_name == "INFLATIONARY":
        if asset_name in ("Gold", "Silver", "Copper", "Oil"):
            result["confidence_boost"] = -5  # Commodities favored
            result["size_multiplier"] = 1.3
        else:
            result["confidence_boost"] = 5

    elif regime_name == "DEFLATIONARY":
        if asset_name in ("Gold", "Silver", "Copper", "Oil"):
            result["confidence_boost"] = 10  # Commodities headwind
            result["size_multiplier"] = 0.7

    # Apply asset-specific multiplier from regime detector
    if asset_mult > 1.1:
        result["confidence_boost"] -= 3  # Regime favors this asset
    elif asset_mult < 0.9:
        result["confidence_boost"] += 5  # Regime is headwind

    return result


def _get_geo_risk_adjustment(geo: dict | None) -> dict:
    """Get geopolitical risk-based adjustment.

    Returns dict with:
        - size_multiplier: float (0.3 to 1.0)
        - skip_all: bool — if risk is extreme, skip all trades
    """
    if not geo:
        return {"size_multiplier": 1.0, "skip_all": False}

    risk_level = geo.get("risk_level", "CALM")

    if risk_level == "EXTREME":
        return {"size_multiplier": 0.0, "skip_all": True}
    elif risk_level == "ELEVATED":
        return {"size_multiplier": 0.5, "skip_all": False}
    elif risk_level == "MODERATE":
        return {"size_multiplier": 0.8, "skip_all": False}
    else:
        return {"size_multiplier": 1.0, "skip_all": False}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [AutoTrader] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Decision audit trail
# ---------------------------------------------------------------------------

def _load_decisions() -> list[dict]:
    if DECISIONS_FILE.exists():
        try:
            return json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_decision(decision: dict) -> None:
    DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    decisions = _load_decisions()
    decisions.append(decision)
    # Keep last N decisions
    decisions = decisions[-AutoTradeConfig.TRADE_DECISIONS_MAX:]
    DECISIONS_FILE.write_text(
        json.dumps(decisions, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Auto-Trading Engine
# ---------------------------------------------------------------------------

class AutoTrader:
    """Evaluates scan results and auto-executes paper trades.

    Now with macro regime awareness, geopolitical risk overlay,
    and dynamic confidence thresholds based on learning history.
    """

    def __init__(self):
        self.learner = MarketLearner()
        self._regime = _load_macro_regime() if AutoTradeConfig.USE_REGIME_AWARENESS else None
        self._geo = _load_geo_analysis() if AutoTradeConfig.USE_GEO_RISK_OVERLAY else None

    def evaluate_and_trade(self, scan_result: dict, live_prices: dict) -> dict:
        """Evaluate a scan result and decide whether to trade.

        Args:
            scan_result: Output from market_scanner.scan_asset()
                         Contains: name, signal, tech, news, confidence, backtest
            live_prices: {asset_name: current_price} dict

        Returns:
            Decision dict with action, reason, and details.
        """
        name = scan_result["name"]
        signal = scan_result["signal"]
        tech = scan_result["tech"]
        confidence = scan_result.get("confidence", {})
        execution = signal.get("execution", {})

        decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset": name,
            "signal_label": signal["label"],
            "signal_score": signal["score"],
            "confidence_pct": confidence.get("confidence_pct", 0),
            "action": "SKIP",
            "reason": "",
            "position_id": None,
            "amount_usd": 0,
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
        }

        # Gate 0: Is auto-trading enabled?
        if not AutoTradeConfig.ENABLED:
            decision["reason"] = "Auto-trading is disabled"
            log(f"{name}: SKIP — auto-trading disabled")
            _save_decision(decision)
            return decision

        # Gate 1: Signal must be actionable
        if signal["label"] not in AutoTradeConfig.ALLOWED_SIGNALS:
            decision["reason"] = f"Signal '{signal['label']}' not in allowed list"
            log(f"{name}: SKIP — signal {signal['label']} not actionable")
            _save_decision(decision)
            return decision

        # Gate 2: Confidence must meet threshold (adjusted by regime)
        conf_pct = confidence.get("confidence_pct", 0)
        direction_hint = "long" if signal["label"] in ("BUY", "STRONG BUY") else "short"
        regime_adj = _get_regime_adjustment(self._regime, name, direction_hint)
        effective_threshold = AutoTradeConfig.MIN_CONFIDENCE_PCT + regime_adj["confidence_boost"]

        # Dynamic confidence: adjust based on asset's historical accuracy
        if AutoTradeConfig.USE_DYNAMIC_CONFIDENCE:
            stats = self.learner.get_performance_stats()
            asset_stats = stats.get("per_asset", {}).get(name, {})
            asset_wr = asset_stats.get("win_rate", 50)
            if asset_wr >= 70:
                effective_threshold -= 5  # Asset has proven itself — lower bar
            elif asset_wr < 40 and asset_stats.get("total", 0) >= 3:
                effective_threshold += 10  # Asset has bad track record — higher bar

        if conf_pct < effective_threshold:
            decision["reason"] = f"Confidence {conf_pct}% < {effective_threshold:.0f}% threshold (regime-adjusted)"
            log(f"{name}: SKIP — confidence {conf_pct}% < {effective_threshold:.0f}% (base={AutoTradeConfig.MIN_CONFIDENCE_PCT}, regime_adj={regime_adj['confidence_boost']:+d})")
            _save_decision(decision)
            return decision

        # Gate 2b: Geopolitical risk overlay
        geo_adj = _get_geo_risk_adjustment(self._geo)
        if geo_adj["skip_all"]:
            decision["reason"] = f"EXTREME geopolitical risk — all trading paused"
            log(f"{name}: SKIP — extreme geo risk, all trading halted")
            _save_decision(decision)
            return decision

        # Gate 2c: Regime skip check
        if regime_adj.get("skip_reason"):
            decision["reason"] = f"Regime filter: {regime_adj['skip_reason']}"
            log(f"{name}: SKIP — regime: {regime_adj['skip_reason']}")
            _save_decision(decision)
            return decision

        # Gate 3: Risk/reward must be acceptable
        rr = execution.get("risk_reward", 0)
        if rr < AutoTradeConfig.MIN_RISK_REWARD:
            decision["reason"] = f"Risk/reward {rr}:1 < {AutoTradeConfig.MIN_RISK_REWARD}:1 minimum"
            log(f"{name}: SKIP — R:R {rr}:1 too low")
            _save_decision(decision)
            return decision

        # Gate 4: Lesson filter
        if AutoTradeConfig.USE_LESSONS_FILTER:
            should, lesson_reason = self.learner.should_trade(name, signal["label"], tech)
            if not should:
                decision["reason"] = f"Lesson filter: {lesson_reason}"
                log(f"{name}: SKIP — lesson veto: {lesson_reason[:80]}")
                _save_decision(decision)
                return decision
            elif "overridden" in lesson_reason.lower():
                log(f"{name}: WARN — {lesson_reason[:80]}")

        # Gate 5: Position limits
        open_positions = paper_trader.get_open_positions_with_pnl(live_prices)
        if len(open_positions) >= AutoTradeConfig.MAX_CONCURRENT_POSITIONS:
            decision["reason"] = f"Max positions ({AutoTradeConfig.MAX_CONCURRENT_POSITIONS}) already open"
            log(f"{name}: SKIP — max positions reached ({len(open_positions)})")
            _save_decision(decision)
            return decision

        # Gate 5b: Already have a position in this asset?
        for pos in open_positions:
            if pos["asset"] == name:
                decision["reason"] = f"Already have an open position in {name}"
                log(f"{name}: SKIP — already holding {name}")
                _save_decision(decision)
                return decision

        # Gate 5c: Correlation guard — limit positions in correlated asset groups
        # Use EXACT asset names matching user_watchlist.json keys
        _CORRELATION_GROUPS = {
            "metals": ["Gold", "Silver", "Platinum", "Copper", "Palladium"],
            "crypto_major": ["BTC", "ETH"],
            "indices": ["S&P 500", "NASDAQ", "Dow Jones", "Russell 2000"],
            "energy": ["Oil", "Natural Gas"],
            "tech_stocks": ["Apple", "Microsoft", "NVIDIA", "Google", "Amazon", "Meta", "AMD", "Intel", "Netflix"],
            "finance_stocks": ["JPMorgan", "Berkshire", "Visa", "Mastercard", "UnitedHealth"],
            "consumer_stocks": ["Walmart", "Coca-Cola", "Disney", "Johnson & Johnson", "ExxonMobil", "Tesla"],
            "altcoins": ["Solana", "XRP", "Dogecoin", "Cardano", "Avalanche", "Chainlink", "Polkadot", "Litecoin"],
            "forex_majors": ["GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "EUR/USD"],
            "agriculture": ["Wheat", "Corn"],
        }
        for group_name, group_assets in _CORRELATION_GROUPS.items():
            if name in group_assets:
                correlated_count = sum(1 for pos in open_positions if pos["asset"] in group_assets)
                if correlated_count >= AutoTradeConfig.MAX_CORRELATED_POSITIONS:
                    decision["reason"] = f"Gate 5c FAIL: {correlated_count} correlated positions in {group_name}"
                    log(f"{name}: SKIP — Gate 5c FAIL: {correlated_count} correlated positions in {group_name}")
                    _save_decision(decision)
                    return decision
                break  # Asset found in a group, no need to check others

        # Gate 6: Cooldown check — don't re-trade same asset too quickly
        recent_decisions = _load_decisions()
        cooldown_cutoff = datetime.now(timezone.utc) - timedelta(hours=AutoTradeConfig.COOLDOWN_HOURS)
        for d in reversed(recent_decisions):
            if d["asset"] == name and d["action"] == "TRADE":
                try:
                    d_time = datetime.fromisoformat(d["timestamp"])
                    if d_time > cooldown_cutoff:
                        decision["reason"] = f"Cooldown: traded {name} less than {AutoTradeConfig.COOLDOWN_HOURS}h ago"
                        log(f"{name}: SKIP — cooldown active")
                        _save_decision(decision)
                        return decision
                except (ValueError, TypeError) as e:
                    log(f"WARNING: Invalid cooldown timestamp: {e} — skipping cooldown check")

        # Gate 6b: Graduated drawdown response — use peak-based drawdown, not total return
        summary = paper_trader.get_portfolio_summary(live_prices)
        equity_curve = paper_trader.get_equity_curve()
        dd_info = risk_manager.max_drawdown(equity_curve)
        current_dd = -dd_info["max_drawdown_pct"]  # negative number (e.g. -12.5 for 12.5% dd)
        drawdown_reduced = False
        if current_dd < AutoTradeConfig.DRAWDOWN_REDUCED_PCT and current_dd >= AutoTradeConfig.DRAWDOWN_PAUSE_PCT:
            drawdown_reduced = True
            log(f"{name}: WARN — peak drawdown {current_dd:.1f}% (>{AutoTradeConfig.DRAWDOWN_REDUCED_PCT}%), reducing position size by 50%")

        # Gate 7: Drawdown circuit breaker (peak-based)
        if current_dd < AutoTradeConfig.DRAWDOWN_PAUSE_PCT:
            decision["reason"] = f"Circuit breaker: peak drawdown {current_dd:.1f}%"
            log(f"{name}: SKIP — circuit breaker (peak drawdown {current_dd:.1f}%)")
            _save_decision(decision)
            return decision

        # ===== ALL GATES PASSED — EXECUTE TRADE =====

        price = live_prices.get(name, execution.get("entry", 0))
        if not price or price <= 0:
            decision["reason"] = "No live price available"
            log(f"{name}: SKIP — no live price")
            _save_decision(decision)
            return decision

        # Determine direction
        direction = "long" if signal["label"] in ("BUY", "STRONG BUY") else "short"

        # Position sizing
        cash = paper_trader.get_cash()
        max_amount = cash * (AutoTradeConfig.MAX_POSITION_PCT / 100)

        if AutoTradeConfig.POSITION_SIZE_METHOD == "kelly":
            stats = self.learner.get_performance_stats()
            asset_stats = stats.get("per_asset", {}).get(name, {})
            win_rate = asset_stats.get("win_rate", 50) / 100
            # Estimate avg win/loss from risk/reward
            # Use percentage-based win/loss (not absolute dollars) so Kelly is asset-agnostic
            target_price = execution.get("target", price * 1.08)
            sl_price_k = execution.get("stop_loss", price * 0.95)
            avg_win = abs(target_price - price) / price if price > 0 else 0.01
            avg_loss = abs(price - sl_price_k) / price if price > 0 else 0.05
            kelly_f = risk_manager.kelly_criterion(win_rate, max(avg_win, 0.01), max(avg_loss, 0.01))
            amount = min(cash * kelly_f, max_amount)
        else:
            # Fixed fractional: risk 2% of capital per trade
            risk_pct = 2.0 / 100
            sl_price = execution.get("stop_loss", price * 0.95)
            risk_per_unit = abs(price - sl_price)
            if risk_per_unit > 0:
                sizing = risk_manager.fixed_fractional_size(cash, risk_pct * 100, price, sl_price)
                amount = min(sizing.get("usd_amount", max_amount * 0.5), max_amount)
            else:
                amount = max_amount * 0.5

        # Apply regime & geo multipliers to position size
        amount *= regime_adj["size_multiplier"]
        amount *= geo_adj["size_multiplier"]

        # Apply graduated drawdown reduction (50% size cut)
        if drawdown_reduced:
            amount *= 0.5

        # Minimum trade size
        amount = max(amount, 10.0)
        amount = min(amount, cash - 1.0)  # keep $1 buffer
        if amount < 10:
            decision["reason"] = f"Insufficient cash (${cash:.2f})"
            log(f"{name}: SKIP — insufficient cash")
            _save_decision(decision)
            return decision

        # Stop-loss, take-profit, trailing stop
        sl = execution.get("stop_loss")
        tp = execution.get("target")
        trail_pct = AutoTradeConfig.DEFAULT_TRAILING_STOP_PCT

        # Resolve ticker from WATCHLIST
        try:
            from market_scanner import WATCHLIST
            ticker = WATCHLIST.get(name, {}).get("ticker", "")
        except ImportError:
            ticker = ""

        # Execute the paper trade!
        result = paper_trader.open_position(
            asset=name,
            ticker=ticker,
            direction=direction,
            usd_amount=round(amount, 2),
            price=price,
            stop_loss=sl,
            take_profit=tp,
            trailing_stop_pct=trail_pct,
            tags=["auto_trade", f"conf_{int(conf_pct)}"],
            signal_hint=signal["label"],
        )

        if "error" in result:
            decision["reason"] = f"Trade failed: {result['error']}"
            log(f"{name}: TRADE FAILED — {result['error']}")
            _save_decision(decision)
            return decision

        # SUCCESS!
        decision["action"] = "TRADE"
        _regime_name = self._regime.get("regime", "N/A") if self._regime else "N/A"
        _geo_risk = self._geo.get("risk_level", "N/A") if self._geo else "N/A"
        decision["reason"] = (
            f"Signal={signal['label']} score={signal['score']} "
            f"conf={conf_pct}% R:R={rr}:1 | Regime={_regime_name} Geo={_geo_risk} — all gates passed"
        )
        decision["regime"] = _regime_name
        decision["geo_risk"] = _geo_risk
        decision["regime_size_mult"] = regime_adj["size_multiplier"]
        decision["geo_size_mult"] = geo_adj["size_multiplier"]
        decision["position_id"] = result.get("id")
        decision["amount_usd"] = round(amount, 2)
        decision["entry_price"] = price
        decision["stop_loss"] = sl
        decision["take_profit"] = tp
        decision["direction"] = direction
        decision["trailing_stop_pct"] = trail_pct

        sl_str = f"${sl:,.2f}" if sl is not None else "N/A"
        tp_str = f"${tp:,.2f}" if tp is not None else "N/A"
        log(
            f"{name}: TRADE OPENED — {direction.upper()} ${amount:.2f} @ ${price:,.2f} "
            f"| SL={sl_str} TP={tp_str} Trail={trail_pct}% "
            f"| Confidence={conf_pct}% Signal={signal['label']}"
        )

        _save_decision(decision)
        return decision

    def evaluate_all(self, scan_results: list[dict], live_prices: dict) -> list[dict]:
        """Evaluate all scan results and trade where appropriate.

        Args:
            scan_results: List of scan_asset() outputs
            live_prices: {asset_name: current_price}

        Returns:
            List of decision dicts
        """
        decisions = []
        for result in scan_results:
            try:
                decision = self.evaluate_and_trade(result, live_prices)
                decisions.append(decision)
            except Exception as e:
                log(f"ERROR evaluating {result.get('name', '?')}: {e}")
                decisions.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "asset": result.get("name", "unknown"),
                    "action": "ERROR",
                    "reason": str(e),
                })
        return decisions

    def check_exits(self, live_prices: dict) -> list[dict]:
        """Check all open positions for automated exits.

        This wraps paper_trader.check_automated_exits() and adds logging.
        """
        closed = paper_trader.check_automated_exits(live_prices)
        for trade in closed:
            pnl_emoji = "+" if trade["pnl"] >= 0 else ""
            log(
                f"{trade['asset']}: POSITION CLOSED — {trade['exit_reason']} "
                f"| {pnl_emoji}${trade['pnl']:.2f} ({pnl_emoji}{trade['pnl_pct']:.1f}%) "
                f"| Entry=${trade['entry_price']:,.2f} Exit=${trade['exit_price']:,.2f}"
            )

            # Record the close as a decision
            _save_decision({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "asset": trade["asset"],
                "action": "CLOSE",
                "reason": trade["exit_reason"],
                "position_id": trade["id"],
                "pnl": trade["pnl"],
                "pnl_pct": trade["pnl_pct"],
                "entry_price": trade["entry_price"],
                "exit_price": trade["exit_price"],
            })

            # Record prediction outcome for learning
            # Note: validate_all() handles bulk validation; log individual trade outcome
            try:
                outcome = "correct" if trade["pnl"] >= 0 else "incorrect"
                log(f"Trade outcome for {trade['asset']}: {outcome} (PnL: {trade.get('pnl_pct', 0):.2f}%)")
            except Exception as e:
                log(f"WARNING: Prediction validation failed for {trade['asset']}: {e}")

        return closed

    def run_autonomous_cycle(self, watchlist: dict = None) -> dict:
        """Run one full autonomous trading cycle.

        This is the CEO-level method that:
        1. Refreshes regime & geo data
        2. Fetches live prices
        3. Checks exits on open positions
        4. Scans all assets
        5. Evaluates trades
        6. Records everything for learning

        Returns a summary dict of what happened.
        """
        log("=== AUTONOMOUS CYCLE START ===")
        cycle_start = datetime.now(timezone.utc)
        summary = {
            "timestamp": cycle_start.isoformat(),
            "exits_closed": [],
            "trades_opened": [],
            "trades_skipped": [],
            "errors": [],
            "regime": "N/A",
            "geo_risk": "N/A",
            "portfolio_equity": 0,
            "portfolio_return_pct": 0,
        }

        try:
            # 1. Refresh intelligence
            self._regime = _load_macro_regime()
            self._geo = _load_geo_analysis()
            summary["regime"] = self._regime.get("regime", "N/A") if self._regime else "N/A"
            summary["geo_risk"] = self._geo.get("risk_level", "N/A") if self._geo else "N/A"
            log(f"Regime: {summary['regime']} | Geo Risk: {summary['geo_risk']}")

            # 2. Load watchlist & fetch prices
            if watchlist is None:
                try:
                    from market_scanner import WATCHLIST
                    watchlist = WATCHLIST
                except ImportError:
                    log("ERROR: Cannot import WATCHLIST")
                    summary["errors"].append("Cannot import WATCHLIST")
                    return summary

            live_prices = fetch_live_prices(watchlist)
            log(f"Fetched prices for {len(live_prices)} assets")

            # 3. Check exits first
            closed = self.check_exits(live_prices)
            summary["exits_closed"] = [
                {"asset": c["asset"], "pnl": c["pnl"], "reason": c["exit_reason"]}
                for c in closed
            ]
            if closed:
                log(f"Closed {len(closed)} positions")

            # 4. Record equity snapshot
            paper_trader.record_equity_snapshot(live_prices)
            port_summary = paper_trader.get_portfolio_summary(live_prices)
            summary["portfolio_equity"] = port_summary.get("equity", 0)
            summary["portfolio_return_pct"] = port_summary.get("total_return_pct", 0)

            # 5. Scan & evaluate trades
            try:
                from market_scanner import scan_all
                scan_results = scan_all()
                log(f"Scanned {len(scan_results)} assets")
            except Exception as e:
                log(f"Scan failed: {e}")
                summary["errors"].append(f"Scan failed: {str(e)[:100]}")
                scan_results = []

            # 6. Evaluate each scan result
            for result in scan_results:
                try:
                    decision = self.evaluate_and_trade(result, live_prices)
                    if decision["action"] == "TRADE":
                        summary["trades_opened"].append({
                            "asset": decision["asset"],
                            "signal": decision["signal_label"],
                            "amount": decision["amount_usd"],
                            "direction": decision.get("direction", ""),
                            "reason": decision["reason"],
                        })
                    else:
                        summary["trades_skipped"].append({
                            "asset": decision["asset"],
                            "signal": decision["signal_label"],
                            "reason": decision["reason"],
                        })
                except Exception as e:
                    log(f"ERROR evaluating {result.get('name', '?')}: {e}")
                    summary["errors"].append(f"{result.get('name', '?')}: {str(e)[:100]}")

        except Exception as e:
            log(f"CYCLE ERROR: {e}")
            summary["errors"].append(f"Cycle error: {str(e)[:200]}")

        # Save cycle summary to bot activity log
        _save_bot_activity(summary)

        duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        log(
            f"=== CYCLE COMPLETE ({duration:.1f}s) === "
            f"Closed: {len(summary['exits_closed'])} | "
            f"Opened: {len(summary['trades_opened'])} | "
            f"Skipped: {len(summary['trades_skipped'])} | "
            f"Errors: {len(summary['errors'])} | "
            f"Equity: ${summary['portfolio_equity']:,.2f} ({summary['portfolio_return_pct']:+.2f}%)"
        )

        return summary

    def get_bot_status(self) -> dict:
        """Get the bot's current status for dashboard display."""
        activities = _load_bot_activities()
        recent = activities[-20:] if activities else []

        total_trades = sum(len(a.get("trades_opened", [])) for a in recent)
        total_closed = sum(len(a.get("exits_closed", [])) for a in recent)
        total_pnl = sum(
            c.get("pnl", 0) for a in recent for c in a.get("exits_closed", [])
        )
        total_errors = sum(len(a.get("errors", [])) for a in recent)

        return {
            "total_cycles": len(activities),
            "recent_cycles": len(recent),
            "trades_opened_recent": total_trades,
            "trades_closed_recent": total_closed,
            "recent_pnl": total_pnl,
            "errors_recent": total_errors,
            "last_cycle": activities[-1] if activities else None,
            "regime": self._regime.get("regime", "N/A") if self._regime else "N/A",
            "geo_risk": self._geo.get("risk_level", "N/A") if self._geo else "N/A",
        }


# ---------------------------------------------------------------------------
# Bot activity persistence
# ---------------------------------------------------------------------------

def _load_bot_activities() -> list[dict]:
    """Load bot activity log."""
    if BOT_LOG_FILE.exists():
        try:
            return json.loads(BOT_LOG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_bot_activity(summary: dict) -> None:
    """Append a cycle summary to bot activity log."""
    BOT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    activities = _load_bot_activities()
    activities.append(summary)
    # Keep last 200 cycles
    activities = activities[-200:]
    BOT_LOG_FILE.write_text(
        json.dumps(activities, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Utility: fetch live prices for the watchlist
# ---------------------------------------------------------------------------

def fetch_live_prices(watchlist: dict) -> dict:
    """Fetch current prices for all assets in the watchlist.

    Returns: {asset_name: current_price}
    """
    import yfinance as yf

    prices = {}
    tickers = {name: config["ticker"] for name, config in watchlist.items()}

    # Batch download for efficiency (with timeout protection)
    ticker_str = " ".join(tickers.values())
    try:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(yf.download, ticker_str, period="1d", interval="1d", progress=False)
            data = future.result(timeout=15)
        del future
        if not data.empty:
            import pandas as pd
            if isinstance(data.columns, pd.MultiIndex):
                # Multiple tickers
                for name, ticker in tickers.items():
                    try:
                        close = data["Close"][ticker].iloc[-1]
                        if pd.notna(close):
                            prices[name] = float(close)
                    except (KeyError, IndexError):
                        pass
            else:
                # Single ticker
                name = list(tickers.keys())[0]
                try:
                    prices[name] = float(data["Close"].iloc[-1])
                except (KeyError, IndexError):
                    pass
    except Exception as e:
        log(f"Batch price fetch failed: {e} — falling back to individual")

    # Fallback: fetch missing prices individually
    for name, ticker in tickers.items():
        if name not in prices:
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="1d")
                if not hist.empty:
                    prices[name] = float(hist["Close"].iloc[-1])
            except Exception:
                pass

    return prices


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from market_scanner import WATCHLIST

    print("Fetching live prices...")
    live_prices = fetch_live_prices(WATCHLIST)
    print(f"Prices: {live_prices}")

    trader = AutoTrader()

    # Check exits first
    closed = trader.check_exits(live_prices)
    if closed:
        print(f"\nClosed {len(closed)} positions:")
        for t in closed:
            print(f"  {t['asset']}: {t['exit_reason']} | PnL: ${t['pnl']:.2f}")

    print(f"\nAuto-trader ready. Run via aegis_brain.py for full integration.")
