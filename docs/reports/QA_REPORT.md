# Project Aegis -- Quality Assurance & Testing Strategy Report

**Version:** 1.0
**Date:** 2026-02-28
**Scope:** Full platform QA assessment and roadmap to production-grade quality for a Top-10 trading terminal

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Testing Strategy for Top-10 Platform](#2-testing-strategy-for-top-10-platform)
3. [QA Team Structure](#3-qa-team-structure)
4. [Test Automation Roadmap](#4-test-automation-roadmap)
5. [Quality Metrics & KPIs](#5-quality-metrics--kpis)
6. [Risk Register](#6-risk-register)

---

## 1. Current State Assessment

### 1.1 Existing Test Infrastructure

| Item | Status | Location |
|------|--------|----------|
| Test directory | Exists | `tests/` |
| Test runner config | pytest via `pyproject.toml` | `[tool.pytest.ini_options]` |
| Smoke tests | 1 file, ~15 tests | `tests/test_smoke.py` |
| conftest.py | Missing | -- |
| CI/CD pipeline | GitHub Actions stub | `.github/workflows/deploy.yml` |
| Linter | Ruff configured (lenient) | `pyproject.toml [tool.ruff]` |
| Type checking | None | -- |
| Code coverage | Not configured | -- |

### 1.2 Existing Test Coverage Breakdown

`tests/test_smoke.py` contains five categories of tests:

1. **Import Tests** -- Parametrized across 24 modules (`src.config`, `src.market_scanner`, `src.auto_trader`, etc.). Verifies each module loads without crashing. This is valuable but only catches import-time errors (missing dependencies, syntax errors).

2. **Config Path Tests** -- Validates `PROJECT_ROOT`, `DATA_DIR`, `MEMORY_DIR` exist on disk.

3. **Config Watchlist Tests** -- Asserts `CORE_WATCHLIST` has >= 4 assets and every asset has a non-empty `ticker` string.

4. **Data Integrity Tests** -- Parametrized across all `*.json` files in `src/data/` and `memory/`. Validates each file parses as valid JSON. Also checks `user_watchlist.json` structure.

5. **Signal Scoring Sanity** -- Validates `SignalConfig` weights sum to 1.0, score range is symmetric, and `RiskConfig` values are within sane bounds.

**What is NOT tested (critical gaps):**

| Module | Lines | Test Coverage | Risk |
|--------|-------|--------------|------|
| `market_scanner.py` | 1200+ | 0% functional | **CRITICAL** -- Signal scoring drives all trading decisions |
| `auto_trader.py` | ~400+ | 0% functional | **CRITICAL** -- 12+ gate system untested, trades execute on paper money |
| `paper_trader.py` | ~300+ | 0% functional | **HIGH** -- P&L calculations, position management |
| `risk_manager.py` | ~545 | 0% functional | **CRITICAL** -- Kelly sizing, VaR, circuit breaker logic |
| `news_researcher.py` | ~500+ | 0% functional | **HIGH** -- Sentiment scoring drives 20% of confidence |
| `auth_manager.py` | ~620 | 0% functional | **CRITICAL** -- Password hashing, session management, tier gating |
| `social_sentiment.py` | ~400+ | 0% functional | **HIGH** -- Influencer impact weights, Reddit parsing |
| `signal_explainer.py` | ~250 | 0% functional | MEDIUM -- Template + LLM explanations |
| `market_learner.py` | ~300+ | 0% functional | **HIGH** -- Prediction validation, win-rate tracking |
| `macro_regime.py` | ~200+ | 0% functional | **HIGH** -- Regime multipliers affect all position sizing |
| `portfolio_optimizer.py` | 553 | 0% functional | HIGH -- Scipy optimization, efficient frontier |
| `dashboard/app.py` | ~8630 | 0% | **CRITICAL** -- Entire UI, 28 views, all user interaction |
| `data_store.py` | ~200+ | 0% functional | HIGH -- Atomic writes, user isolation, file locking |

**Estimated overall functional test coverage: less than 2%**

### 1.3 Code Quality Observations

**Positive patterns found in source files:**

- Atomic writes with temp file + rename in `paper_trader.py` `_save()` and `market_learner.py` `_save_predictions()`
- Thread-safe file locking in `data_store.py` using `threading.Lock` per path
- Constant-time password comparison via `hmac.compare_digest()` in `auth_manager.py`
- PBKDF2-HMAC-SHA256 with 100K iterations and random salt for password hashing
- Price sanity bounds in `market_scanner.py` to catch yfinance garbage data
- Graceful degradation when `scipy` is not installed (`portfolio_optimizer.py`)
- Fallback patterns throughout (e.g., `ImportError` catches in `auto_trader.py`, `market_scanner.py`)

**Concerns identified:**

- **Single-file dashboard** (`app.py` at 8630 lines) -- extremely difficult to test, review, or maintain
- **No input validation on watchlist asset data** -- `_load_watchlist()` in `market_scanner.py` trusts JSON structure without schema validation
- **No rate limiting on yfinance API calls** beyond cache TTL -- risk of IP bans under load
- **Global mutable state** -- `WATCHLIST = _load_watchlist()` at module level in `market_scanner.py` means the watchlist is fixed at import time
- **File-based sessions** (`users/_active_session.json`) without expiry garbage collection
- **No CSRF protection** in auth flow (Streamlit limitation but important for production)
- **Social sentiment engine** uses browser User-Agent spoofing (`HEADERS` in `social_sentiment.py`) -- fragile, may break if Reddit/Google change their bot detection
- **No retry logic** for network calls in `news_researcher.py` or `social_sentiment.py` -- single failures cause silent data gaps
- **Division by zero risk** in `kelly_criterion()` when `avg_win == 0` causes `b = 0`, then `(win_rate * 0 - q) / 0` crashes
- **`paper_trader.py` uses `_DEFAULT_BALANCE = 1000.0`** as a constant -- no mechanism to reset or configure per user in the module itself
- **Trailing stop logic** in `risk_manager.py` `check_exits()` only updates `highest_price` within the check but never persists it back to the position

### 1.4 Top Bugs/Risks Found

| # | Bug/Risk | Severity | Location |
|---|----------|----------|----------|
| 1 | `kelly_criterion()` guards `avg_loss <= 0` but not `avg_win == 0` -- if `avg_win` is 0, `b = 0/avg_loss = 0`, then division `(win_rate * b - q) / b` divides by zero | HIGH | `risk_manager.py:63-68` |
| 2 | Trailing stop `highest_price` is computed in `check_exits()` but never written back to the position dict in storage -- trailing stops never ratchet up between check cycles | HIGH | `risk_manager.py:192` |
| 3 | `_has_negation_before()` uses `text.find()` which returns the FIRST occurrence -- if a keyword appears twice, negation check may apply to the wrong instance | MEDIUM | `news_researcher.py:119` |
| 4 | Social sentiment data accessed with `.get()` but values can be strings not dicts -- inconsistent type handling across consumers | MEDIUM | `social_sentiment.py` consumers |
| 5 | `auto_trader.py` Gate 5c correlation groups are hardcoded -- adding new assets requires code change, not config | LOW | `auto_trader.py` |
| 6 | No request timeout in `MacroRegimeDetector._fetch_indicator()` -- `yf.download()` can hang indefinitely | HIGH | `macro_regime.py:80` |
| 7 | `_save_decision()` in `auto_trader.py` uses non-atomic write (`DECISIONS_FILE.write_text()`) unlike `paper_trader.py` which uses temp+rename | MEDIUM | `auto_trader.py:202` |
| 8 | Signal explainer LLM mode catches all exceptions silently (`except Exception: return None`) -- API key misconfigurations will never surface | LOW | `signal_explainer.py:244` |
| 9 | `data_store.py` file locks are thread-local -- multi-process Streamlit (workers > 1) can still corrupt files | HIGH | `data_store.py:24` |
| 10 | No upper bound on `equity_curve` list growth in `paper_portfolio.json` -- long-running portfolios will grow unbounded | MEDIUM | `paper_trader.py` |

---

## 2. Testing Strategy for Top-10 Platform

### 2.1 Unit Tests per Module

#### market_scanner.py (Priority: P0)
```
test_analyze_asset_returns_all_fields()
test_analyze_asset_handles_multiindex_columns()
test_sanity_check_price_valid()
test_sanity_check_price_rejects_garbage()
test_sanity_check_price_falls_back_to_median()
test_score_signal_bullish_near_support()
test_score_signal_bearish_overbought()
test_score_signal_score_range_minus100_to_plus100()
test_score_signal_golden_cross_bonus()
test_score_signal_macd_bullish_bonus()
test_generate_confidence_weights_sum()
test_generate_confidence_news_integration()
test_analyze_multi_timeframe_insufficient_data()
test_scan_asset_full_pipeline()
test_scan_all_parallel_execution()
test_load_watchlist_missing_file_uses_defaults()
test_load_watchlist_corrupted_file_uses_defaults()
test_load_watchlist_disabled_assets_filtered()
```

#### auto_trader.py (Priority: P0)
```
test_gate0_disabled_skips()
test_gate1_neutral_signal_skips()
test_gate2_low_confidence_skips()
test_gate2_regime_adjusted_threshold()
test_gate2b_extreme_geo_risk_halts_all()
test_gate3_max_positions_enforced()
test_gate4_cooldown_respected()
test_gate5_lesson_filter()
test_gate5c_correlation_guard()
test_gate6_drawdown_pause()
test_gate6_graduated_drawdown_half_size()
test_regime_adjustment_risk_off_long()
test_regime_adjustment_risk_on_short()
test_regime_adjustment_high_volatility()
test_geo_risk_extreme_returns_zero_multiplier()
test_geo_risk_moderate_returns_08()
test_position_sizing_kelly_vs_fixed()
test_decision_audit_trail_persisted()
test_evaluate_and_trade_full_flow_buy()
test_evaluate_and_trade_full_flow_sell()
```

#### paper_trader.py (Priority: P0)
```
test_open_position_long()
test_open_position_short()
test_open_position_insufficient_cash()
test_close_position_pnl_long_profit()
test_close_position_pnl_long_loss()
test_close_position_pnl_short_profit()
test_partial_close_half()
test_update_stop_loss()
test_update_take_profit()
test_save_trade_note()
test_equity_curve_appended_on_close()
test_blank_portfolio_structure()
test_atomic_save_survives_crash()
test_csv_export_format()
test_concurrent_open_close()
```

#### risk_manager.py (Priority: P0)
```
test_kelly_criterion_positive_edge()
test_kelly_criterion_negative_edge_returns_zero()
test_kelly_criterion_zero_loss_guard()
test_kelly_half_kelly_cap()
test_fixed_fractional_size_basic()
test_fixed_fractional_size_capped_at_max_position()
test_fixed_fractional_size_stop_equals_entry()
test_calculate_stop_take_long()
test_calculate_stop_take_short()
test_calculate_trailing_stop()
test_check_exits_stop_loss_long()
test_check_exits_take_profit_long()
test_check_exits_trailing_stop()
test_check_exits_stop_loss_short()
test_max_drawdown_calculation()
test_max_drawdown_empty_curve()
test_circuit_breaker_triggers()
test_suggest_position_size_kelly_path()
test_suggest_position_size_fixed_fractional_path()
test_portfolio_var_calculation()
test_correlation_matrix()
```

#### news_researcher.py (Priority: P1)
```
test_score_headline_bullish()
test_score_headline_bearish()
test_score_headline_neutral()
test_score_headline_negation_flips()
test_score_headline_double_negation()
test_score_headline_failure_words_always_bearish()
test_score_headline_weighted_strong_vs_mild()
test_keyword_match_word_boundary()
test_keyword_match_no_partial()
test_has_negation_before_within_3_words()
test_has_negation_before_too_far()
test_research_returns_structured_report()
test_asset_keyword_mapping_complete()
test_rss_feed_timeout_handling()
```

#### auth_manager.py (Priority: P0)
```
test_hash_password_returns_hex()
test_hash_password_salt_uniqueness()
test_verify_password_correct()
test_verify_password_wrong()
test_verify_password_timing_safe()
test_register_user_creates_profile()
test_register_user_duplicate_rejected()
test_login_valid_credentials()
test_login_invalid_password()
test_login_nonexistent_user()
test_tier_gating_free_user()
test_tier_gating_pro_user()
test_trial_expiry_downgrade()
test_generate_verification_code_length()
test_generate_verification_code_randomness()
test_email_verification_rate_limit()
test_resend_verification_rate_limit()
test_session_creation_and_validation()
test_guest_mode_backward_compat()
```

#### social_sentiment.py (Priority: P1)
```
test_influencer_config_all_have_affects()
test_influencer_config_all_have_keywords()
test_scan_influencer_bullish_detection()
test_scan_influencer_bearish_detection()
test_scan_reddit_subreddit_parsing()
test_engagement_weighted_scoring()
test_social_score_blend_60_40()
test_buzz_level_thresholds()
test_cache_save_and_load()
test_cache_expiry()
test_request_timeout_handling()
```

#### signal_explainer.py (Priority: P2)
```
test_template_explanation_buy_signal()
test_template_explanation_sell_signal()
test_template_explanation_neutral_signal()
test_template_explanation_includes_rsi_context()
test_template_explanation_includes_regime()
test_template_explanation_includes_geo_risk()
test_llm_explanation_no_api_key_returns_none()
test_cache_save_and_load()
test_cache_ttl_expiry()
```

#### market_learner.py (Priority: P1)
```
test_record_prediction_structure()
test_record_prediction_persists()
test_validate_buy_correct_target_hit()
test_validate_buy_incorrect_stop_hit()
test_validate_sell_correct()
test_validate_time_expired_48h()
test_validate_skips_recent_predictions()
test_learn_from_failure_creates_lesson()
test_get_performance_stats_accuracy()
test_get_performance_stats_per_asset()
test_concurrent_write_safety()
```

#### macro_regime.py (Priority: P1)
```
test_detect_risk_on()
test_detect_risk_off()
test_detect_inflationary()
test_detect_deflationary()
test_detect_high_volatility()
test_detect_neutral()
test_regime_multipliers_all_assets_present()
test_fetch_indicator_timeout_handling()
test_regime_cache_write_and_read()
```

#### config.py (Priority: P0)
```
test_apply_settings_override_patches_config()
test_apply_settings_override_missing_file()
test_apply_settings_override_corrupted_file()
test_price_sanity_bounds_all_tickers()
test_signal_config_weights()
test_technical_params_defaults()
test_risk_config_defaults()
test_auto_trade_config_defaults()
```

### 2.2 Integration Tests

| Test Suite | Modules Tested | What It Validates |
|-----------|---------------|-------------------|
| **Signal Pipeline** | `market_scanner` -> `news_researcher` -> `social_sentiment` -> `signal_explainer` | Full scan produces signal + explanation with correct data flow |
| **Trade Pipeline** | `market_scanner` -> `auto_trader` -> `paper_trader` -> `risk_manager` | Signal triggers trade, position opens with correct sizing, SL/TP set |
| **Learning Loop** | `market_scanner` -> `market_learner` -> `auto_trader` | Prediction recorded, validated, lessons affect future confidence thresholds |
| **Settings Pipeline** | `config` -> `auto_trader` + `market_scanner` | `settings_override.json` changes propagate to trading behavior |
| **Auth + Data Isolation** | `auth_manager` -> `data_store` | User A's portfolio is isolated from User B |
| **Regime Cascade** | `macro_regime` -> `auto_trader` -> `paper_trader` | Risk-Off regime reduces position sizes and raises confidence bar |
| **Alert System** | `alert_manager` -> `aegis_brain` -> notification | Price alerts fire when conditions met |
| **Watchlist Sync** | `watchlist_manager` -> `market_scanner` | Named watchlist changes reflect in next scan cycle |

### 2.3 End-to-End Testing (Streamlit UI with Playwright)

```
E2E Test Scenarios:
---

1. AUTH FLOW
   - Guest login -> dashboard loads -> Advisor page visible
   - Register -> email verification -> login -> dashboard
   - Login -> wrong password -> error displayed
   - Tier gating: free user -> optimizer page -> upgrade prompt shown

2. TRADING FLOW
   - Load Advisor -> verify 12 asset cards render
   - Click "Scan Now" -> signals refresh with loading indicator
   - Click LONG quick-trade -> Paper Trading page -> position opened
   - Verify P&L updates when mock price changes
   - Close position -> verify in trade history

3. NAVIGATION
   - All 28 sidebar links navigate to correct views
   - Back button returns to previous view
   - Asset link buttons navigate to Asset Detail page
   - Breadcrumbs show correct path

4. WATCHLIST MANAGEMENT
   - Add asset via Manage Watchlist -> appears in scan
   - Remove asset -> disappears from scan
   - Create named watchlist -> switch -> correct assets shown

5. SETTINGS
   - Change confidence threshold -> verify auto-trader respects it
   - Change risk parameters -> verify position sizing changes
   - Settings persist across page refresh

6. CHARTS
   - Charts page loads Plotly chart for selected asset
   - Auto-trendlines display support/resistance lines
   - Multi-timeframe panel shows 4H data

7. RESPONSIVE LAYOUT
   - Mobile viewport (375px) -> sidebar collapses
   - Tablet viewport (768px) -> layout adjusts
   - Desktop (1280px) -> full layout
```

### 2.4 Financial Accuracy Tests

These tests validate correctness of financial calculations with known expected values:

```python
# Signal Scoring Accuracy
test_gold_near_support_scores_above_50()       # Gold at $4410 (0.1% above $4405) -> score >= 50
test_btc_overbought_rsi_scores_negative()      # BTC with RSI 82 -> score includes -10 from RSI
test_confidence_weights_40_20_40()             # Tech=80, News=0.5, Hist=60 -> 0.4*80+0.2*50+0.4*60 = 66%

# P&L Calculations
test_long_pnl_10_pct_gain()                   # Buy $100, sell $110 -> P&L = +$10 per unit
test_short_pnl_10_pct_gain()                  # Short $100, cover $90 -> P&L = +$10 per unit
test_position_value_calculation()             # 0.5 BTC at $80K -> value = $40K
test_equity_curve_accuracy()                  # Starting $1000 + $50 profit -> equity $1050

# Position Sizing
test_kelly_known_values()                     # WR=0.6, avg_win=$100, avg_loss=$80 -> known fraction
test_fixed_fractional_2pct_risk()             # $10K capital, 2% risk, $5 stop -> $4000 position
test_position_cap_at_max_pct()               # Position size never exceeds 20% of capital

# Risk Metrics
test_max_drawdown_known_sequence()            # [100, 110, 90, 95, 105] -> DD = 18.18%
test_var_95_normal_distribution()             # Known returns -> VaR matches analytical solution
test_trailing_stop_calculation()              # Entry $100, highest $120, trail 3% -> stop at $116.40

# Sentiment Scoring
test_headline_scoring_known_inputs()          # "Gold surges to all-time high" -> score >= 0.5
test_negation_flips_sentiment()              # "Gold not likely to rally" -> negative score
```

### 2.5 Performance Testing (10K Concurrent Users)

| Test | Tool | Target | Current Estimate |
|------|------|--------|------------------|
| Dashboard page load | Locust/k6 | < 2s at P95 | ~5-8s (yfinance calls) |
| Concurrent scan requests | k6 | 100 RPS | ~2-3 RPS (yfinance bottleneck) |
| WebSocket refresh (10K users) | k6 | < 500ms latency | N/A (HTTP polling) |
| JSON file I/O under load | Custom | No corruption | Thread locks only (not multi-process safe) |
| Memory per session | Streamlit profiler | < 50MB | ~100-200MB (pandas DataFrames cached) |
| Scan cycle completion | Timing harness | < 30s for 12 assets | ~40s (parallelized, was 130s) |

**Key bottlenecks for scale:**
- JSON file storage will not survive 10K concurrent users (need PostgreSQL + Redis)
- yfinance rate limits at ~2000 requests/hour (need Polygon.io or Twelve Data)
- Streamlit single-process model requires horizontal scaling (Streamlit Cloud or Kubernetes)
- No connection pooling for external API calls

### 2.6 Security Testing

| Test Category | Specific Tests | Priority |
|-------------|---------------|----------|
| **Authentication Bypass** | Forge session token, skip login, manipulate `st.session_state` | P0 |
| **Password Security** | Verify PBKDF2 with 100K iterations, salt uniqueness, constant-time compare | P0 |
| **Session Hijacking** | File-based session token in `_active_session.json` -- check for predictable tokens | P0 |
| **Path Traversal** | `data_store.py` user_id parameter -> `../../etc/passwd` injection | P0 |
| **XSS in Streamlit** | HTML injection via asset names, trade notes, research reports | P1 |
| **Rate Limiting** | Brute-force login attempts (no rate limit beyond email verification) | P0 |
| **Tier Bypass** | Manipulate `session_state["tier"]` to access pro features | P1 |
| **IDOR** | Access other user's portfolio by guessing user_id in `data_store` | P0 |
| **Denial of Service** | Trigger simultaneous scans to exhaust yfinance quota | P1 |
| **Secrets in Logs** | Check `agent_logs.txt` for API keys, passwords, session tokens | P1 |
| **SMTP Injection** | Malicious email address in registration -> SMTP header injection | P1 |
| **JSON Injection** | Malformed JSON in `settings_override.json` -> code execution via deserialization | P2 |

---

## 3. QA Team Structure (40-Person QA Team)

### 3.1 Organizational Chart

```
VP of Quality Engineering (1)
|
+-- Manual QA Lead (1)
|   +-- Trading Flow QA (4) -- Advisor, Paper Trading, Trade Journal, Asset Detail
|   +-- Intelligence Flow QA (3) -- News Intel, Econ Calendar, Analytics, Risk Dashboard
|   +-- System & Settings QA (2) -- Auth, Settings, Watchlist Mgr, Monitor, Logs
|   +-- Regression QA (2) -- Full regression suite, cross-browser, mobile
|
+-- Automation Lead (1)
|   +-- Backend Test Engineers (4) -- Unit + integration tests (pytest)
|   +-- Frontend Test Engineers (3) -- Playwright E2E, visual regression
|   +-- API Test Engineers (2) -- yfinance mocks, RSS feed mocks, LLM API tests
|   +-- CI/CD Engineer (1) -- GitHub Actions, test infrastructure, reporting
|
+-- Performance Engineering Lead (1)
|   +-- Load Test Engineers (3) -- k6/Locust scripts, scalability tests
|   +-- Profiling Engineer (1) -- Memory, CPU, network profiling
|   +-- Data Pipeline QA (2) -- JSON integrity, data flow validation, cache testing
|
+-- Security & Compliance Lead (1)
|   +-- AppSec Engineers (2) -- OWASP, penetration testing, auth security
|   +-- Financial Compliance QA (2) -- Regulatory testing, disclaimer verification
|   +-- Data Privacy QA (1) -- User isolation, PII handling, GDPR compliance
|
+-- QA Operations (3)
    +-- Test Environment Manager (1) -- Docker, staging, data fixtures
    +-- Metrics & Reporting Analyst (1) -- Dashboards, defect tracking, KPI reporting
    +-- QA Process Coach (1) -- Standards, training, best practices
```

**Headcount Summary:**
| Sub-team | Count |
|----------|-------|
| Leadership | 5 |
| Manual QA | 11 |
| Automation | 10 |
| Performance | 7 |
| Security & Compliance | 5 |
| QA Operations | 3 |
| **Total** | **41** |

### 3.2 Sub-team Responsibilities

**Manual QA (11):**
- Exploratory testing of all 28 dashboard views
- New feature acceptance testing per sprint
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Mobile responsive testing (iOS Safari, Android Chrome)
- Accessibility testing (WCAG 2.1 AA)
- User acceptance testing with trading domain experts

**Automation (10):**
- Unit test development and maintenance (target: 2000+ tests)
- Integration test suites for all data pipelines
- Playwright E2E scripts for all critical user journeys
- Visual regression tests (Percy or Chromatic)
- Test data fixture generation and management
- CI/CD pipeline optimization (target: < 15 min full suite)

**Performance (7):**
- Load testing (Locust/k6) for 10K concurrent user target
- Database migration performance benchmarks (JSON -> PostgreSQL)
- yfinance API call optimization and caching validation
- Memory leak detection in long-running Streamlit sessions
- Real-time data pipeline latency testing (future Kafka/WebSocket)
- Scan cycle performance regression tracking

**Security & Compliance (5):**
- Quarterly penetration testing
- OWASP Top 10 vulnerability scanning
- Authentication and session security audits
- Financial regulatory compliance verification (disclaimers, not-advice)
- GDPR/CCPA data handling compliance
- Secrets scanning in codebase and logs

---

## 4. Test Automation Roadmap (6 Months)

### Phase 1: Foundation (Weeks 1-4)

**Goal:** Establish test infrastructure and cover critical financial logic

| Task | Details |
|------|---------|
| Set up `conftest.py` with fixtures | Mock yfinance responses, sample portfolio data, test user profiles |
| Set up pytest-cov | Target: measure baseline coverage |
| Create mock data factory | Deterministic market data for reproducible tests |
| Unit tests: `risk_manager.py` | All position sizing, Kelly, stop/take calculations (21 tests) |
| Unit tests: `paper_trader.py` | Open/close/partial, P&L, atomic save (15 tests) |
| Unit tests: `auth_manager.py` | Password hashing, login/register, tier gating (18 tests) |
| Unit tests: `news_researcher.py` | `score_headline()`, negation, keyword matching (14 tests) |
| Unit tests: `config.py` | Settings override pipeline, price sanity bounds (8 tests) |
| CI integration | GitHub Actions runs pytest on every PR |

**Deliverable:** ~76 new unit tests, CI pipeline, coverage reporting
**Target coverage:** 15% -> 35%

### Phase 2: Core Logic (Weeks 5-10)

**Goal:** Cover signal generation, auto-trading, and learning pipelines

| Task | Details |
|------|---------|
| Unit tests: `market_scanner.py` | `analyze_asset()`, `score_signal()`, multi-timeframe (17 tests) |
| Unit tests: `auto_trader.py` | All 12+ gates, regime adjustment, geo risk (20 tests) |
| Unit tests: `market_learner.py` | Prediction recording, validation, learning (11 tests) |
| Unit tests: `macro_regime.py` | Regime detection, multipliers (9 tests) |
| Unit tests: `social_sentiment.py` | Influencer, Reddit, scoring (11 tests) |
| Integration tests | Signal pipeline, trade pipeline, learning loop, settings pipeline (8 suites) |
| Mock infrastructure | VCR.py or responses library for HTTP call recording/playback |
| Financial accuracy suite | Known-value tests for all monetary calculations (20 tests) |

**Deliverable:** ~96 new unit tests, 8 integration suites, HTTP mocking
**Target coverage:** 35% -> 60%

### Phase 3: E2E & Performance (Weeks 11-18)

**Goal:** UI testing, performance baselines, security hardening

| Task | Details |
|------|---------|
| Playwright setup | Streamlit test server, page object models for 28 views |
| E2E: Auth flow | Login, register, guest, tier gating (4 scenarios) |
| E2E: Trading flow | Scan, quick-trade, close, journal (5 scenarios) |
| E2E: Navigation | All 28 views, back button, asset links (3 scenarios) |
| E2E: Settings | Change settings, verify persistence (2 scenarios) |
| Performance baselines | k6 scripts for dashboard load, scan cycle, concurrent users |
| Security scan | OWASP ZAP automated scan, auth bypass tests |
| Visual regression | Percy snapshots for all 28 views |
| Load test: 100 users | Identify bottlenecks, establish baseline metrics |

**Deliverable:** 14 E2E scenarios, performance baselines, security report
**Target coverage:** 60% -> 75%

### Phase 4: Scale & Polish (Weeks 19-26)

**Goal:** 10K user readiness, mutation testing, chaos engineering

| Task | Details |
|------|---------|
| Load test: 1K users | With PostgreSQL backend (post-migration) |
| Load test: 10K users | Full scale test with Redis caching |
| Mutation testing | mutmut/cosmic-ray to validate test quality |
| Chaos testing | Kill yfinance, corrupt JSON, timeout APIs -- verify graceful degradation |
| Contract testing | Pact tests for yfinance, RSS feed, and LLM API interfaces |
| Accessibility audit | WCAG 2.1 AA compliance across all views |
| Test data management | Seed scripts for staging environments |
| Documentation | Test plan, runbooks, on-call playbooks |

**Deliverable:** Scale-ready test suite, chaos resilience, accessibility compliance
**Target coverage:** 75% -> 85%

---

## 5. Quality Metrics & KPIs

### 5.1 Coverage Targets

| Metric | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|---------|---------|---------|---------|
| Line coverage | 35% | 60% | 75% | 85% |
| Branch coverage | 25% | 50% | 65% | 75% |
| Financial logic coverage | 80% | 95% | 98% | 99% |
| E2E scenario coverage | 0% | 0% | 70% | 90% |
| Critical path coverage | 50% | 85% | 95% | 99% |

### 5.2 Defect Density

| Metric | Target | Measurement |
|--------|--------|-------------|
| Defects per KLOC | < 5.0 | After Phase 2 |
| Defects per KLOC | < 2.0 | After Phase 4 |
| P0 defects in production | 0 | Always |
| P1 defects in production | < 2 per month | After Phase 3 |
| Mean time to detect (MTTD) | < 4 hours | CI pipeline |
| Mean time to resolve (MTTR) | < 24h P0, < 72h P1 | SLA |

### 5.3 Release Gates

Every release must pass:

| Gate | Criteria |
|------|----------|
| Unit tests | 100% pass, 0 failures |
| Integration tests | 100% pass |
| E2E tests | >= 95% pass (flaky tolerance: 5%) |
| Code coverage | >= 75% lines (Phase 3+) |
| Financial accuracy tests | 100% pass (ZERO tolerance) |
| Security scan | 0 critical/high findings |
| Performance regression | < 10% degradation from baseline |
| Lint | 0 Ruff errors (ratchet-only: new code must pass) |
| Type check | 0 mypy errors on new/modified files (Phase 2+) |

### 5.4 Test Execution Metrics

| Metric | Target |
|--------|--------|
| Full CI suite runtime | < 15 minutes |
| Unit test suite runtime | < 3 minutes |
| E2E suite runtime | < 10 minutes |
| Test flake rate | < 2% |
| Tests per developer per sprint | >= 5 new tests |

---

## 6. Risk Register

| # | Risk | Severity | Likelihood | Impact | Mitigation |
|---|------|----------|------------|--------|------------|
| 1 | **Financial calculation error causes incorrect P&L display** -- user makes real decisions based on wrong paper-trading results | CRITICAL | HIGH | Users lose trust, potential legal liability | Financial accuracy test suite with 100% pass gate. Known-value tests for every monetary calculation. Peer review for all `paper_trader.py` and `risk_manager.py` changes |
| 2 | **JSON file corruption under concurrent access** -- Streamlit multi-worker or simultaneous browser tabs corrupt `paper_portfolio.json` | CRITICAL | HIGH | Data loss, ghost positions, wrong equity | Migrate to PostgreSQL (Phase 4). Short-term: add file-level OS locks (`fcntl`/`msvcrt`), write integrity checks on load |
| 3 | **yfinance returns garbage data (BTC at $64.97)** -- price sanity bounds miss edge cases or new assets without bounds | HIGH | MEDIUM | Wrong signals, auto-trader opens bad trades | Expand `PRICE_SANITY_BOUNDS` to all assets. Add moving-average sanity check (not just static bounds). Alert on sanity failures |
| 4 | **Authentication bypass via session manipulation** -- file-based sessions in `_active_session.json` could be forged | CRITICAL | MEDIUM | Unauthorized access to other users' data | Add session token entropy check, implement session expiry, migrate to signed JWT tokens |
| 5 | **Auto-trader opens positions during data outage** -- yfinance timeout returns stale cached price, auto-trader does not know | HIGH | MEDIUM | Trades at wrong prices, unexpected losses | Add data freshness check (reject prices older than 5 minutes). Add health check gate in auto-trader |
| 6 | **Sentiment scoring false positive from keyword matching** -- "Goldman Sachs" matches "Gold", "support level" matches "support" (bullish keyword) | HIGH | HIGH | Incorrect sentiment -> wrong signal confidence | Implement phrase-level NLP (bigrams minimum). Add negative test cases for known false positives. Migrate to FinBERT |
| 7 | **Single-file dashboard (8630 lines) becomes unmaintainable** -- new features increase bug density, testing becomes impractical | MEDIUM | CERTAIN | Slower development, more bugs, developer burnout | Refactor into page modules (28 files). Add Streamlit multipage app pattern. Gate refactoring behind feature flags |
| 8 | **Rate limiting by yfinance/Reddit/Google News causes silent data gaps** -- RSS feeds return empty, social scan returns stale data | MEDIUM | HIGH | Incomplete market intelligence, stale signals | Add data freshness indicators on dashboard. Implement exponential backoff retry. Add "Data Quality" status panel |
| 9 | **Memory leak in long-running Streamlit sessions** -- cached DataFrames, Plotly figures, and session state grow unbounded | MEDIUM | MEDIUM | Server OOM after hours/days of operation | Profile memory per view. Implement cache eviction policies. Add memory monitoring to health checks |
| 10 | **Dependency on free APIs limits scaling** -- yfinance, RSS feeds, Reddit JSON are all rate-limited and unreliable | HIGH | CERTAIN | Cannot serve 10K users without paid data sources | Build abstraction layer for data providers. Plan migration to Polygon.io / Twelve Data. Budget $500-2000/month for data |

---

*Report generated 2026-02-28. Next review: Sprint 15 kickoff.*
