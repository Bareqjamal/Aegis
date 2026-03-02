# Project Aegis — QA Master Summary
## Sprint 15 Week 2 — Full Product Audit
**Date:** 2026-02-27 | **Agents:** 6 | **Files Audited:** 25+ | **Lines Reviewed:** ~15,000+

---

## EXECUTIVE SUMMARY

| Severity | Count | Status |
|----------|-------|--------|
| **P0 CRITICAL** | 19 | 🔴 FIX IMMEDIATELY |
| **P1 HIGH** | 34 | 🟠 Fix this sprint |
| **P2 MEDIUM** | 50 | 🟡 Backlog |
| **P3 LOW** | 32 | 🔵 Nice-to-have |
| **TOTAL** | **135** | |

### THE BIG PICTURE
The product has a **systemic data contract problem**. Modules were built independently and communicate via JSON files, but field names don't match between producers and consumers. This means:

1. **The entire adaptive learning system is dead code** (key mismatch: `"tech"` vs `"technical"`)
2. **The prediction game never validates outcomes** (reads `"date"/"correct"` but data has `"timestamp"/"outcome"`)
3. **Morning Brief shows NEUTRAL/0% for everything** (reads `"signal"` but data has `"signal_label"`)
4. **The landing page "Live Scoreboard" is 100% fabricated** (hardcoded, not connected to real data)

These 4 issues alone mean the product's core value proposition — *transparent, self-grading AI* — is non-functional.

---

## P0 CRITICAL FINDINGS (Fix Before Any User Sees This)

### Data Contract Bugs (6 findings — THE ROOT CAUSE)
| ID | Source | Bug | Impact |
|----|--------|-----|--------|
| SIG-01 | market_learner → scanner | `get_adaptive_weights()` returns `"tech"/"history"` but scanner reads `"technical"/"historical"` | Adaptive learning = dead code |
| SIG-02 | scanner → morning_brief | Scanner writes `"signal_label"` but brief reads `"signal"` | All signals show NEUTRAL |
| SIG-03 | scanner → morning_brief | Scanner writes `"confidence"` (dict) but brief reads `"confidence_pct"` (number) | All confidence = 0% |
| ENG-01 | market_learner → prediction_game | Predictions have `"timestamp"` but game reads `"date"` | Outcome validation broken |
| ENG-02 | market_learner → prediction_game | Predictions have `"outcome"` (string) but game reads `"correct"` (boolean) | Never validates |
| INT-07 | auto_trader → paper_trader | Auto-trader sends `"position_usd"` but paper_trader reads `"usd_amount"` | Oversized trades |

### Crash Bugs (4 findings)
| ID | Source | Bug | Impact |
|----|--------|-----|--------|
| SIG-04 | morning_brief.py | `log()` function called but never defined | NameError crash on any JSON error |
| INT-04 | auto_trader.py | Calls `validate_prediction_by_asset()` which doesn't exist in MarketLearner | AttributeError crash |
| DASH-01 | app.py L1131 | `signal_card_html()` formats `entry` as `${entry:,.2f}` but entry can be None | TypeError crash |
| DASH-10 | app.py L5312 | `p["usd_amount"]` without `.get()` in Risk Guardian | KeyError crash |

### Security (3 findings)
| ID | Source | Bug | Impact |
|----|--------|-----|--------|
| AUTH-23 | auth_manager.py | No brute-force protection on login (unlimited attempts) | Account takeover risk |
| AUTH-22 | auth_manager.py | Verification codes logged at DEBUG level | Code exposure |
| LAND-02 | landing/index.html | "LIVE PREDICTION SCOREBOARD" is 100% hardcoded fake data | Legal liability (false advertising) |

### Signal Accuracy (3 findings)
| ID | Source | Bug | Impact |
|----|--------|-----|--------|
| SIG-07 | market_scanner.py | Confidence inflation: `(raw_score + 10) * 1.1` adds +11 points to every BUY | Inflated signals |
| INT-08 | morning_brief.py | `_get_predictions()` checks `isinstance(data, list)` but data is a dict | Predictions never loaded |
| SIG-RSI | market_scanner.py | RSI `gain/loss` division: flat market → NaN propagation | Potential NaN in signals |

### Tier Contradiction (1 finding)
| ID | Source | Bug | Impact |
|----|--------|-----|--------|
| LAND-18 | pricing.html vs auth_manager.py | Pricing page promises 12+ assets free, code blocks at 5 | User trust destruction |

---

## AGENT REPORTS (Individual)

| # | Agent | Report | Findings |
|---|-------|--------|----------|
| 1 | Signal & Data Accuracy | `docs/QA_SIGNAL_ACCURACY.md` | 33 (7 P0, 9 P1, 11 P2, 6 P3) |
| 2 | Dashboard Features | `docs/QA_DASHBOARD_FEATURES.md` | 21 (0 P0, 2 P1, 10 P2, 8 P3) |
| 3 | Engagement Mechanics | `docs/QA_ENGAGEMENT_MECHANICS.md` | 19 (3 P0, 5 P1, 7 P2, 4 P3) |
| 4 | Landing Page & Auth | `docs/QA_LANDING_AUTH.md` | 34 (5 P0, 9 P1, 12 P2, 8 P3) |
| 5 | Backend Integration | `docs/QA_BACKEND_INTEGRATION.md` | 28 (4 P0, 7 P1, 11 P2, 6 P3) |
| 6 | Security & Integrity | `docs/QA_SECURITY_AUDIT.md` | 35 (7 P0, 11 P1, 9 P2, 8 P3) |

---

## FIX PRIORITY (CEO Decision)

### PHASE 1 — "Make It Not Lie" (TODAY)
1. Fix all 6 data contract mismatches (field name alignment)
2. Fix 4 crash bugs (None checks, missing methods)
3. Fix morning_brief `log()` → `logger.warning()`
4. Fix prediction game to read actual field names
5. Add login rate limiting

### PHASE 2 — "Make It Trustworthy" (This Week)
6. Remove/replace hardcoded landing page scoreboard with real data
7. Resolve tier contradiction (pricing.html vs code)
8. Fix confidence inflation formula
9. Add webhook SSRF protection
10. Fix dashboard crash bugs

### PHASE 3 — "Harden" (Next Sprint)
11. Address 160 `unsafe_allow_html` XSS surface
12. Add resource limits (alerts, watchlists)
13. Session token encryption
14. Thread safety for paper_trader
15. Settings weight validation
