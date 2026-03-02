"""Aegis Brain — the main autonomous loop that ties everything together.

This is the "living brain" of Project Aegis. It runs on a configurable
interval and orchestrates:

1. Budget check → determine operational mode
2. Pre-task memory check → load error lessons
3. Market scan → signals + news + charts + confidence + backtest
3.5. AUTO-TRADE → evaluate signals, open/close paper positions
3.75. ALERT CHECK → check price/signal alerts, send notifications
4. Prediction validation → check past predictions
5. Market discovery → scan non-core assets
6. Chief Monitor reflection → daily learning summary
7. Self-improvement → create improvement tickets

Usage:
    python aegis_brain.py                   # Run one full cycle
    python aegis_brain.py --loop            # Run continuously (30-min interval)
    python aegis_brain.py --loop --interval 15  # Custom interval in minutes
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "memory"))

LOG_FILE = PROJECT_ROOT / "agent_logs.txt"


def log(message: str, autonomous: bool = False) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[AUTONOMOUS ACTION]" if autonomous else "[AegisBrain]"
    line = f"[{ts}] {prefix} {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def run_brain_cycle() -> dict:
    """Execute one full brain cycle."""
    from autonomous_manager import AutonomousManager, BudgetGuard
    from memory_manager import pre_task_check, get_evolution_stats

    cycle_start = time.time()
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps_completed": [],
        "errors": [],
    }

    log("=== AEGIS BRAIN CYCLE STARTING ===")

    # Step 1: Budget check
    budget = BudgetGuard()
    budget_info = budget.report()
    mode = budget_info["mode"]
    log(f"Budget: {budget_info['remaining_pct']:.1f}% remaining, mode={mode}")
    report["budget"] = budget_info

    if mode == "paused":
        log("Budget exhausted — cycle aborted.")
        report["steps_completed"].append("budget_check_paused")
        return report

    # Step 2: Pre-task memory check
    memory = pre_task_check("AegisBrain", "full system cycle scan validate learn")
    log(f"Memory: {memory['total_rules']} prevention rules loaded.")
    report["steps_completed"].append("memory_check")

    # Step 3: Market scan (core assets)
    scan_results = []
    if mode in ("full_autonomy", "conservative"):
        try:
            from market_scanner import scan_all, WATCHLIST
            log("Running core market scan (Gold, BTC, ETH, Silver)...", autonomous=True)
            scan_results = scan_all()
            log(f"Core scan complete: {len(scan_results)} assets scanned.", autonomous=True)
            report["steps_completed"].append("core_scan")
            report["scan_results"] = len(scan_results)
        except Exception as e:
            log(f"Core scan error: {e}")
            report["errors"].append(f"core_scan: {e}")

    # Step 3.25: Social sentiment scan
    if mode in ("full_autonomy", "conservative"):
        try:
            from social_sentiment import SocialSentimentEngine
            log("Running social sentiment scan (influencers + Reddit)...", autonomous=True)
            _ss = SocialSentimentEngine()
            _ss_result = _ss.scan_all()
            _ss_alerts = _ss_result.get("stats", {}).get("total_alerts", 0)
            log(f"Social scan complete: {_ss_alerts} alerts found.", autonomous=True)
            report["steps_completed"].append("social_sentiment")
            report["social_alerts"] = _ss_alerts
        except Exception as e:
            log(f"Social sentiment error: {e}")
            report["errors"].append(f"social_sentiment: {e}")

    # Step 3.35: News Impact analysis (causal reasoning on all scanned assets)
    if scan_results:
        try:
            from news_impact import NewsImpactEngine
            log("Running news impact analysis (causal reasoning)...", autonomous=True)
            _nie = NewsImpactEngine()
            _impact_count = 0
            for _sr in scan_results:
                _sr_name = _sr.get("name", "")
                _sr_news = _sr.get("news")
                try:
                    _nie.analyze(_sr_name, news_data=_sr_news)
                    _impact_count += 1
                except Exception:
                    pass
            log(f"News impact analysis complete: {_impact_count} assets analyzed.", autonomous=True)
            report["steps_completed"].append("news_impact")
        except Exception as e:
            log(f"News impact analysis error: {e}")
            report["errors"].append(f"news_impact: {e}")

    # Step 3.5: AUTO-TRADE on scan results
    live_prices = {}  # Will be populated by auto-trade step, reused by alert check
    if scan_results and mode in ("full_autonomy", "conservative"):
        try:
            from auto_trader import AutoTrader, fetch_live_prices
            from market_scanner import WATCHLIST

            log("Fetching live prices for auto-trading...", autonomous=True)
            live_prices = fetch_live_prices(WATCHLIST)

            # First: check exits on existing positions
            trader = AutoTrader()
            closed = trader.check_exits(live_prices)
            if closed:
                log(f"Auto-closed {len(closed)} positions.", autonomous=True)
                report["auto_closed"] = len(closed)

            # Then: evaluate new trades from scan results
            decisions = trader.evaluate_all(scan_results, live_prices)
            trades_opened = [d for d in decisions if d.get("action") == "TRADE"]
            trades_skipped = [d for d in decisions if d.get("action") == "SKIP"]

            if trades_opened:
                for t in trades_opened:
                    log(
                        f"AUTO-TRADE: {t['asset']} {t.get('direction', '?')} "
                        f"${t.get('amount_usd', 0):.2f}",
                        autonomous=True,
                    )
            log(
                f"Auto-trader: {len(trades_opened)} trades opened, "
                f"{len(trades_skipped)} skipped.",
                autonomous=True,
            )
            report["steps_completed"].append("auto_trade")
            report["trades_opened"] = len(trades_opened)
            report["trades_skipped"] = len(trades_skipped)
            report["trade_decisions"] = [
                {"asset": d["asset"], "action": d["action"], "reason": d["reason"][:100]}
                for d in decisions
            ]
        except Exception as e:
            log(f"Auto-trade error: {e}")
            report["errors"].append(f"auto_trade: {e}")

    # Step 3.75: Check price/signal alerts
    if scan_results:
        try:
            from alert_manager import check_alerts, send_notifications, get_alerts

            # Only run if there are active alerts configured
            active_alerts = get_alerts(active_only=True)
            if active_alerts:
                # Build live_prices dict from scan results: {asset_name: current_price}
                alert_prices = {}
                alert_watchlist = {}
                for sr in scan_results:
                    aname = sr.get("name", "")
                    tech = sr.get("tech", {})
                    sig = sr.get("signal", {})
                    cprice = tech.get("current_price", 0)
                    if aname and cprice:
                        alert_prices[aname] = cprice
                        alert_watchlist[aname] = {
                            "signal_label": sig.get("label", ""),
                            "rsi": tech.get("rsi_14", 50),
                            "price_change_pct": tech.get("price_change_pct", 0),
                        }

                # Also merge live_prices from auto-trade step if available (more tickers)
                if live_prices:
                    for k, v in live_prices.items():
                        if k not in alert_prices and v:
                            alert_prices[k] = v

                triggered = check_alerts(alert_prices, alert_watchlist)
                if triggered:
                    log(f"ALERTS: {len(triggered)} alert(s) triggered!", autonomous=True)
                    for ta in triggered:
                        log(
                            f"  ALERT FIRED: {ta['asset']} — {ta['message']} "
                            f"(price=${ta.get('current_price', 0):,.2f})",
                            autonomous=True,
                        )
                    # Send notifications (email, Discord, Telegram)
                    notif_results = send_notifications(triggered)
                    for nr in notif_results:
                        log(f"  Notification: {nr}")
                    report["alerts_triggered"] = len(triggered)
                else:
                    log(f"Alerts: {len(active_alerts)} active, none triggered.")
                report["steps_completed"].append("alert_check")
            else:
                log("Alerts: no active alerts configured, skipping.")
                report["steps_completed"].append("alert_check_skipped")
        except Exception as e:
            log(f"Alert check error: {e}")
            report["errors"].append(f"alert_check: {e}")

    # Step 4: Prediction validation
    try:
        from market_learner import MarketLearner
        learner = MarketLearner()
        validated = learner.validate_all()
        if validated:
            log(f"Validated {len(validated)} predictions.", autonomous=True)
        report["steps_completed"].append("prediction_validation")
        report["predictions_validated"] = len(validated) if validated else 0
    except Exception as e:
        log(f"Prediction validation error: {e}")
        report["errors"].append(f"validation: {e}")

    # Step 5: Market discovery (only in full_autonomy)
    if mode == "full_autonomy":
        try:
            from market_discovery import discover_all
            log("Running market discovery (8 assets)...", autonomous=True)
            disc_results = discover_all()
            log(f"Discovery complete: {len(disc_results)} assets scanned.", autonomous=True)
            report["steps_completed"].append("discovery_scan")
        except Exception as e:
            log(f"Discovery error: {e}")
            report["errors"].append(f"discovery: {e}")

    # Step 6: Chief Monitor reflection (once per day)
    try:
        from memory_manager import get_todays_reflection
        if not get_todays_reflection():
            mgr = AutonomousManager()
            mgr.executor.run_reflection()
            log("Daily reflection completed.", autonomous=True)
            report["steps_completed"].append("daily_reflection")
        else:
            log("Daily reflection already done today.")
    except Exception as e:
        log(f"Reflection error: {e}")
        report["errors"].append(f"reflection: {e}")

    # Step 7: Self-improvement check
    if mode == "full_autonomy":
        try:
            mgr = AutonomousManager()
            improvements = mgr.improver.identify_improvements()
            if improvements:
                log(f"Found {len(improvements)} improvement opportunities.", autonomous=True)
                # Execute the top one
                top = improvements[0]
                action = top.get("action", "")
                if action == "run_scanner":
                    pass  # Already done in Step 3
                elif action == "validate_predictions":
                    pass  # Already done in Step 4
                elif action == "run_reflection":
                    pass  # Already done in Step 6
                else:
                    log(f"Improvement queued: {top.get('reason', 'unknown')}")
            report["steps_completed"].append("self_improvement")
        except Exception as e:
            log(f"Self-improvement error: {e}")
            report["errors"].append(f"improvement: {e}")

    # Step 8: Performance summary
    try:
        from market_learner import MarketLearner as _ML
        _learner = _ML()
        stats = _learner.get_performance_stats()
        report["performance"] = {
            "total_predictions": stats["total_predictions"],
            "win_rate": stats["win_rate"],
            "lessons_count": stats["lessons_count"],
        }
    except Exception:
        pass

    elapsed = round(time.time() - cycle_start, 1)
    report["elapsed_seconds"] = elapsed
    log(f"=== BRAIN CYCLE COMPLETE ({elapsed}s, {len(report['steps_completed'])} steps, {len(report['errors'])} errors) ===")

    # Save cycle report
    report_file = PROJECT_ROOT / "src" / "data" / "brain_cycle_report.json"
    report_file.write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False), encoding="utf-8")

    # Step 8: Telegram summary (send brief after brain cycle if configured)
    try:
        from telegram_notifier import get_notifier
        _tg = get_notifier()
        if _tg.is_configured():
            _tg_summary = {
                "headline": f"Brain cycle completed in {elapsed}s — {len(report['steps_completed'])} steps, {len(report['errors'])} errors.",
                "top_picks": report.get("top_signals", [])[:3],
                "regime": report.get("regime", {}),
            }
            _tg.send_brief_summary(_tg_summary)
            log("Telegram summary sent.", autonomous=True)
            report["steps_completed"].append("telegram_summary")
    except Exception as e:
        log(f"Telegram summary skipped: {e}")
        report["errors"].append(f"telegram: {e}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Brain — Autonomous Decision Loop")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval in minutes (default: 30)")
    args = parser.parse_args()

    if args.loop:
        log(f"Starting continuous brain loop (every {args.interval} minutes)...")
        while True:
            try:
                report = run_brain_cycle()
                errors = report.get("errors", [])
                if errors:
                    log(f"Cycle had {len(errors)} errors: {errors}")
            except Exception as e:
                log(f"CRITICAL: Brain cycle crashed: {e}")

            log(f"Sleeping {args.interval} minutes until next cycle...")
            time.sleep(args.interval * 60)
    else:
        report = run_brain_cycle()
        print(json.dumps(report, indent=2, default=str))
