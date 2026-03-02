# PROFI REVIEW: Sprint 11 — The Hard Questions

**Reviewer:** The Profi (adversarial QA agent)
**Date:** 2026-02-26
**Sprint Features:** Email verification, i18n, persistent login, feature gating, social pulse unlock, advanced settings, MTF badges, auto-trader fixes, social pulse summary bar

---

## 1. EMAIL VERIFICATION (auth_manager.py lines 117-270)

### 1.1 Verification code is only 6 digits = 1,000,000 combinations. [CRITICAL]
There is zero rate limiting on `verify_email()`. An attacker who registers an account can brute-force all 1M codes in minutes with automated HTTP requests against the Streamlit endpoint. Where is the lockout after N failed attempts? There is none. The `hmac.compare_digest` on line 387 prevents timing attacks but does nothing against volume attacks.

### 1.2 The verification code is printed to stdout when SMTP is not configured (line 227). [HIGH]
In dev mode, `_send_verification_email` prints the raw verification code to the console: `print(f"[Aegis Auth] SMTP not configured. Verification code for <{email}>: {code}")`. In production, if the SMTP env vars are not set (which is the default), every user's verification code is dumped to server logs. If Streamlit Cloud logs are accessible, this is an information leak. What prevents this print statement from firing in production?

### 1.3 SMTP credentials live in environment variables with no validation. [MEDIUM]
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` are read once at module import time (lines 121-124). If the env vars change after the process starts, the old values persist. More critically: if `AEGIS_SMTP_PORT` is set to a non-integer value, line 122 raises an unhandled `ValueError` at import time and crashes the entire auth module.

### 1.4 The email subject line leaks the verification code (line 232). [MEDIUM]
`msg["Subject"] = f"Your Aegis Verification Code: {code}"` -- the 6-digit code is right in the subject line. Email subjects are displayed in notification banners, lock screen previews, and logged by email providers. This defeats the purpose of requiring the user to open the email. The code should only appear inside the email body.

### 1.5 Resend verification has no cooldown or rate limit (line 399-427). [HIGH]
`resend_verification()` generates a fresh code and sends a new email every time it is called, with no throttle. An attacker can hit the "Resend Code" button (or its endpoint) thousands of times, flooding a victim's inbox and potentially getting the SMTP account flagged for spam or suspended. There is no `last_resend_at` timestamp tracked.

### 1.6 Registration accepts literally any string with an `@` in it (line 279). [MEDIUM]
`if not email or "@" not in email:` is the entire email validation. `a@b` passes. `@` alone passes. `test@.@.@` passes. No domain check, no MX lookup, no format regex. You are sending SMTP emails to garbage addresses.

### 1.7 The HTML email template has no `name` sanitization (line 170). [MEDIUM]
`Hello{(' ' + name) if name else ''}` injects the user-provided name directly into an HTML template. If someone registers with name `<script>alert(1)</script>`, that string goes straight into the HTML email body. Most email clients strip scripts, but some older clients or webmail interfaces may not. This is an HTML injection vector.

### 1.8 What happens when email bounces? [LOW]
`_send_verification_email` returns True/False but the caller (line 332) ignores the return value. If the SMTP server accepts the message but the recipient's server bounces it later (non-existent mailbox, full inbox), the user never gets the code and has no feedback. The only option is "Resend Code" which hits the same dead address.

### 1.9 Verification is skippable (line 1244-1247). [QUESTION]
The "Skip for Now" button lets unverified users proceed to the full dashboard. What is the enforcement of email verification? Currently nothing. An attacker can register with `fake@fake.fake`, skip verification, and use the entire free tier. What is the point of email verification if it is optional?

---

## 2. INTERNATIONALIZATION / i18n (i18n.py, 618 lines)

### 2.1 Only 81 translation keys exist, but the dashboard is ~7,784 lines of UI text. [CRITICAL]
Count the hardcoded English strings in `app.py` that are NOT using `t()`. Grep for any `st.markdown`, `st.error`, `st.warning`, `st.success`, `st.info`, `st.caption`, `st.subheader` call. The vast majority contain raw English strings. The `t()` function is only used for navigation labels and a handful of generic terms. The upgrade prompt (lines 1954-1977) is entirely English. The settings page (lines 7546-7753) is entirely English. The auth page (lines 1103-1171) is entirely English ("Sign In", "Create Account", "Email", "Password"). Is this i18n or is this a language selector that translates the sidebar?

### 2.2 The `t()` function falls back to the raw key string (line 527). [MEDIUM]
`return entry.get(lang, entry.get("en", key))` -- if someone calls `t("nonexistent.key")`, the user sees "nonexistent.key" in the UI. There is no logging of missing translations. There is no dev-mode warning. How do you even know when a translation key is missing?

### 2.3 Signal labels are translated in i18n.py but the scanner outputs English constants. [HIGH]
`i18n.py` defines `signal.strong_buy` -> "STARKER KAUF" (German) and "STRONG BUY" (English). But the actual signal logic throughout the codebase compares against literal English strings: `signal["label"] in ("BUY", "STRONG BUY")` in `auto_trader.py` line 261, the `SIGNAL_STYLES` dict in `config.py` uses English keys. If anyone actually uses the translated signal labels for display AND those get fed back into logic, it breaks. Are translated signal labels ever used as data, or are they display-only? The CLAUDE.md says "Signal labels: BUY, SELL, STRONG BUY, NEUTRAL -- ALWAYS ENGLISH", but then why translate them in i18n.py?

### 2.4 RTL support excludes the sidebar (line 569). [MEDIUM]
The CSS comment says: `/* Keep sidebar LTR (Streamlit limitation) */`. So Arabic users get RTL main content but an LTR sidebar. This means navigation items, the language selector, the user badge, the portfolio ticker, and the logout button are all left-aligned while the main content is right-aligned. This is a disorienting split-brain layout. Has anyone actually tested this with a native Arabic speaker?

### 2.5 Language selector causes a full `st.rerun()` (line 615). [LOW]
Changing the language triggers `st.rerun()`, which re-executes the entire 7,784-line app.py from the top. This nukes all ephemeral state: any form inputs, any expanded expanders, any scroll position. If a user is mid-way through configuring advanced settings (30+ fields) and accidentally changes the language, they lose all unsaved work.

### 2.6 Language preference is stored in `st.session_state` only (line 502). [MEDIUM]
`set_language` writes to `st.session_state["language"]`. This is lost when the session expires or the user opens a new tab. The language preference is not persisted to the user profile in `_profiles.json`. Every new session defaults to English. Why not store it in the user profile alongside `tier`, `email`, etc.?

### 2.7 The Arabic translations were not verified by a native speaker (assumption). [QUESTION]
Who wrote the Arabic translations? Machine-translated Arabic for financial terms is notoriously bad. Are terms like "STARKER KAUF" correct German financial terminology, or is it a literal translation that sounds unnatural? Does "Eigenkapital" mean "Equity" in the trading context or "shareholders' equity" (which is a different concept)?

### 2.8 Number formatting is not locale-aware. [MEDIUM]
Prices display as `${price:,.2f}` throughout the dashboard (US format: comma thousand separator, dot decimal). In German, `1.234,56` is the correct format. In Arabic, Eastern Arabic numerals are sometimes used. The i18n system translates labels but ignores number formatting entirely.

---

## 3. PERSISTENT LOGIN / SESSION TOKENS (auth_manager.py lines 510-581)

### 3.1 Session token is exposed in the URL query string (line 1127). [CRITICAL]
`st.query_params["session"] = _token` puts the 43-character session token directly in the browser URL bar: `https://aegis.example.com/?session=abcdef123...`. This token is:
- Visible in browser history
- Logged in web server access logs (Nginx, Apache, Cloudflare)
- Sent in the Referer header when users click any external link
- Visible to anyone who looks at the user's screen
- Shared if the user copies and pastes the URL to someone
- Indexed by browser extensions that read URLs

This is a session fixation vector. Anyone with that URL string can hijack the session. HTTP-only cookies exist for exactly this reason.

### 3.2 `_sessions.json` is a single JSON file for ALL session tokens of ALL users. [HIGH]
`_load_sessions()` reads the entire sessions file, `_save_sessions()` writes the entire file. With 1,000 users each having 1 session, this is a 1,000-entry JSON dict loaded and written on every login, every session validation, and every page load (since `validate_session` is called on every request at line 1177). This is O(N) reads and writes where N is total active sessions.

### 3.3 Race condition on `_sessions.json` writes. [HIGH]
`_save_sessions` uses `path.write_text()` directly (line 532) -- there is no file lock, no atomic write, no temp-file-then-rename pattern. The `DataStore._write_json` method uses locks and atomic writes, but `_save_sessions` bypasses DataStore entirely. If two users log in simultaneously, one session token gets lost. This is a data corruption vector.

### 3.4 Session cleanup only happens during `create_session()` (line 540-543). [MEDIUM]
Expired sessions (older than 30 days) are purged only when a new session is created. If no one logs in for months, expired sessions accumulate forever. There is no background cleanup, no cron, no periodic garbage collection. The sessions file grows monotonically.

### 3.5 Session validation loads the full profiles file (line 571). [MEDIUM]
`validate_session` calls `data_store.get_profile(user_id)` which calls `load_profiles()` which reads the entire `_profiles.json`. So every page load reads both `_sessions.json` AND `_profiles.json` in full. These are unbounded JSON files. At scale, this is two full-file-parse disk I/O operations per request.

### 3.6 The session token has no IP binding or user-agent fingerprint. [MEDIUM]
The session dict stores only `user_id` and `created` (line 544-547). If a token is stolen (trivially, since it is in the URL), it works from any device, any IP, any browser. No anomaly detection. No "new device" warning.

### 3.7 `st.query_params.clear()` on logout (line 1326) clears ALL query params. [LOW]
This destroys any non-session query params the app might use (e.g., deep links, asset selection, view routing). Is that intentional?

### 3.8 No session revocation mechanism beyond logout. [MEDIUM]
There is no "sign out all devices" feature. If a user's session is compromised (very easy given issue 3.1), they cannot invalidate all existing sessions. They can only destroy the one they are currently using.

---

## 4. FEATURE GATING (auth_manager.py lines 84-95, app.py lines 1950-1977)

### 4.1 Only 2 pages are gated: `optimizer` and `strategy_lab`. [CRITICAL — BUSINESS]
`PRO_VIEWS = {"optimizer", "strategy_lab"}` -- out of 26+ views, only 2 require Pro. Everything else is free: the Daily Advisor, Paper Trading, News Intelligence, Risk Dashboard, Trade Journal, Economic Calendar, Watchlist Manager, Morning Brief, Charts, Analytics, Fundamentals, Market Overview... plus the Social Pulse tab that was explicitly unlocked. What is the value proposition for $29/month? A free user gets 24 out of 26 pages. The Pro features (autopilot, export reports, backtesting) are inline feature gates, but the major pages are all free. Is this a viable business model or a charity?

### 4.2 Feature checks are tier-name string comparisons, not capability-based. [MEDIUM]
`can_access_view` checks `if tier in ("pro", "enterprise")`. If you add a new tier (e.g., "starter" at $9), you have to update every string comparison. The `TIERS` dict defines capabilities per tier, but `can_access_view` ignores it entirely.

### 4.3 Free tier gets `max_scans_per_day: 3` but who enforces it? [HIGH]
`check_scan_limit` exists but does the dashboard actually call it before running a scan? Grep for `check_scan_limit` in `app.py` -- is it enforced? If not, the limit is decorative. A free user can click "Scan Now" unlimited times.

### 4.4 The upgrade prompt shows a "Start 14-Day Trial" button (observed in code). [QUESTION]
`start_trial` sets `tier = "pro"` with a 14-day expiry. But `check_trial_expiry` is called once per page load (line 1193). If the trial expires while the user is actively on a Pro page, the next rerun downgrades them mid-session. What happens to in-progress work? Auto-trader positions opened during the trial?

### 4.5 Guest mode bypasses all gating (line 1160-1165). [MEDIUM]
Guest users get `tier: "free"` and `disclaimer_accepted: True` and `onboarding_complete: True`. But guests also use `user_id: "default"` which maps to the shared `memory/` directory. Multiple simultaneous guests share the same paper portfolio, predictions, bot activity, and settings. Two guests trading simultaneously corrupt each other's data.

---

## 5. SOCIAL PULSE UNLOCKED

### 5.1 Why was it locked in the first place if it is the "killer feature"? [QUESTION]
The code comment says `# Social sentiment is FREE (it's our killer feature -- hooks users)`. If you already decided this, why was it ever gated? Was this a product decision or an accidental gate that got fixed?

### 5.2 Social Pulse still reads from the shared `social_sentiment.json` (line 2388). [LOW]
All users (free, pro, guest) read the same social sentiment data. This is shared market intelligence, not per-user. That is fine, but it means the "free for all" decision costs nothing in terms of data isolation. Was it ever truly gated at the data layer?

---

## 6. ADVANCED SETTINGS (app.py lines 7546-7753)

### 6.1 Settings are saved but never consumed by the backend. [CRITICAL]
`settings_override.json` is written by the dashboard (line 7725) but `auto_trader.py` reads from `AutoTradeConfig` class attributes (lines 39-58), which are hardcoded Python values in `config.py`. The auto_trader never reads `settings_override.json`. The market scanner uses `TechnicalParams` class attributes, not the settings file. Grep for `settings_override` in the `src/` directory returns exactly one hit: the data_store key definition. The settings page is cosmetic. Changing "Min Confidence %" in the UI does absolutely nothing to the actual auto-trader's behavior. This is a placebo dashboard.

### 6.2 No input validation beyond Streamlit widget constraints. [MEDIUM]
The sliders and number inputs have min/max ranges, but there is no cross-field validation. A user can set stop-loss at 20% and take-profit at 1%, creating a risk/reward ratio below 0.05. They can set confidence weights to 0.0 + 0.0 + 0.0 = 0.0 (the warning only shows for sum != 1.0). They can set drawdown_reduced_pct to -1.0 and drawdown_pause_pct to -50.0, which is backwards (reduced should be less severe than pause).

### 6.3 Settings are written to a global file, not per-user (line 7550). [HIGH]
`SETTINGS_FILE = PROJECT_ROOT / "src" / "data" / "settings_override.json"` -- this is a single global file. The `data_store` has per-user settings support (`USER_DATA_KEYS["settings"]`), but the settings page ignores it and writes to a shared location. If User A changes confidence weights, User B sees those changes. This contradicts the multi-user architecture.

### 6.4 No "unsaved changes" warning. [LOW]
If a user changes 15 sliders and then navigates away without clicking "Save Settings", all changes are lost silently. There is no dirty state tracking, no confirmation dialog, no auto-save.

### 6.5 The Reset button deletes the file entirely (line 7730-7731). [LOW]
`SETTINGS_FILE.unlink()` removes the file. This is fine, but what if a concurrent process is reading it at that exact moment? There is no lock, and the read logic (line 7569-7574) catches all exceptions, so it would silently fall back to defaults. Acceptable but fragile.

### 6.6 Every visit to the settings page reads `settings_override.json` from disk (line 7569). [LOW]
Not cached, read every render. On auto-refresh (every 10-60 seconds), this file is re-read. Marginal cost but pointless I/O.

---

## 7. MTF (MULTI-TIMEFRAME) BADGES ON ADVISOR (app.py lines 2545-2563)

### 7.1 Where does `mtf_data` actually come from? [HIGH]
The badge reads `_card_conf.get("mtf_data", {})` from the confidence object in `watchlist_summary.json`. But which module populates `mtf_data`? It is not in `market_scanner.py` based on the existing architecture. If the scanner does not produce this field, the badge never appears and this feature is dead code.

### 7.2 The MTF badge operator precedence bug (line 2555). [HIGH]
```python
_mtf_agrees = signal in ("BUY", "STRONG BUY") and _mtf_lbl == "BULLISH" or signal in ("SELL", "STRONG SELL") and _mtf_lbl == "BEARISH"
```
This relies on Python's operator precedence: `and` binds tighter than `or`, so it evaluates as `(A and B) or (C and D)`. This happens to be correct, but it is fragile and unclear. One refactor that adds a condition could break it. Should have explicit parentheses.

### 7.3 The badge shows "4H" but what timeframe data is actually used? [MEDIUM]
The badge displays "4H: X/Y BULLISH" but the underlying data fields are `bullish_confirms` and `bearish_confirms` without specifying what they are confirming against. Is this 4-hour RSI, MACD, SMA? All three? Is the daily timeframe included? The user sees "4H" but has no way to know what that means.

### 7.4 The MTF badge is rendered inside an f-string HTML blob. [LOW]
`_mtf_badge` is assembled as a raw HTML string (lines 2557-2563) and then injected into a larger HTML card (line 2617). If any of the MTF values contain HTML-special characters, this is an injection risk. Unlikely with numeric data, but architecturally unsound.

### 7.5 No fallback or explanation when MTF data is unavailable. [LOW]
If `_card_mtf` is empty or `available` is False, `_mtf_badge` stays as an empty string and the badge silently disappears. The user has no indication that MTF analysis was skipped or is loading. An asset card with a badge next to one without creates visual inconsistency with no explanation.

---

## 8. AUTO-TRADER BUG FIXES (auto_trader.py)

### 8.1 Drawdown thresholds from config vs. from settings page. [CRITICAL]
Gate 6b (line 374) reads `AutoTradeConfig.DRAWDOWN_REDUCED_PCT` and `AutoTradeConfig.DRAWDOWN_PAUSE_PCT`. These are Python class attributes set at -10.0 and -15.0. The settings page lets users change these values (lines 7643-7645), but those changes go to `settings_override.json`, which the auto_trader **never reads** (see issue 6.1). The "config-based drawdown" fix is based on hardcoded config, not user-configurable settings. The settings page is lying about what it controls.

### 8.2 Graduated drawdown response has a gap at exactly DRAWDOWN_PAUSE_PCT. [LOW]
Line 374: `if summary["total_return_pct"] < AutoTradeConfig.DRAWDOWN_REDUCED_PCT and summary["total_return_pct"] >= AutoTradeConfig.DRAWDOWN_PAUSE_PCT:` -- What happens at exactly -15.0%? It falls through to Gate 7 (line 379) which checks `< AutoTradeConfig.DRAWDOWN_PAUSE_PCT`, so -15.0% exactly is NOT paused (it is `<`, not `<=`). At -15.0%, the portfolio is neither in reduced mode nor paused mode. This is an off-by-one at a critical safety boundary.

### 8.3 Correlation guard uses hardcoded asset groups (lines 340-345). [MEDIUM]
`_CORRELATION_GROUPS` is defined inside `evaluate_and_trade` as a static dict. If a user adds "Palladium" to their watchlist, it is not in any correlation group and will never be correlation-guarded against other metals. The correlation groups do not dynamically update based on the actual watchlist.

### 8.4 The auto-trader does not read the same settings the user configures. [CRITICAL]
(Reiteration for emphasis.) `AutoTradeConfig.MIN_CONFIDENCE_PCT` is 65.0 (line 165, config.py). The settings page default is also 65.0 (line 7562). If the user changes it to 80.0 on the settings page, the auto-trader still uses 65.0. This is not a "bug fix" -- it is a new bug. Users think they are controlling the bot; they are not.

### 8.5 `_load_decisions()` reads the full decisions file on every gate check (line 357). [LOW]
Gate 6 loads all trade decisions to check cooldowns. This file can hold up to 500 entries (line 198). Every `evaluate_and_trade()` call reads this file. With 12 assets per cycle, that is 12 full file reads per autonomous cycle.

### 8.6 The auto-trader still writes directly to files, not through DataStore. [MEDIUM]
`_save_decision()` uses `DECISIONS_FILE.write_text()` (line 199), not `data_store.save_user_data()`. `_save_bot_activity()` uses `BOT_LOG_FILE.write_text()` (line 720). These bypass the atomic write protection and file locking in DataStore. In a multi-user world, multiple users' auto-traders could write to the same files simultaneously.

---

## 9. SOCIAL PULSE SUMMARY BAR ON ADVISOR (app.py lines 2401-2425)

### 9.1 The summary bar reads `social_sentiment.json` directly from disk (line 2388-2391). [MEDIUM]
This bypasses `data_store.load_shared("social_sentiment")` and instead does `json.loads(path.read_text())`. No lock, no atomic read, no DataStore abstraction. If the social scanner is writing to this file at the same time, you get a partial read.

### 9.2 What does "High Buzz" actually mean to a user? [LOW]
The bar shows "High Buzz: 3" but does not explain what constitutes HIGH buzz. Is it 5 mentions? 50? 500? The threshold is buried in `social_sentiment.py` and the user has no context for what the number means.

### 9.3 Social pulse data staleness is not indicated clearly. [MEDIUM]
The scan timestamp is shown in tiny gray text (`font-size:0.65em;color:#484f58`) at the far right. If the last scan was 8 hours ago, the data is stale but still presented with full confidence. There is no "stale data" warning, no color change, no expiry. Users may trade on social signals from yesterday.

### 9.4 The bar is only shown when `_adv_social_scores` is truthy (line 2402). [LOW]
If the social sentiment file does not exist or has no `asset_scores`, the entire bar disappears silently. First-time users who have not run a social scan see no indication that this feature exists. No "Run social scan to see data" prompt.

---

## 10. CROSS-CUTTING CONCERNS

### 10.1 No HTTPS enforcement anywhere. [HIGH]
Streamlit can run over HTTP. The session token in the URL (issue 3.1) combined with no HTTPS means the token is transmitted in plaintext. Any network observer (public WiFi, ISP, corporate proxy) can steal sessions.

### 10.2 No CSRF protection on form submissions. [MEDIUM]
Streamlit's form submission mechanism does not include CSRF tokens. Since the session token is in the URL, an attacker who knows the URL structure could craft malicious links that trigger actions.

### 10.3 Password policy is "6+ characters" (line 282). [HIGH]
`if len(password) < 6:` -- that is the entire password policy. "123456", "aaaaaa", "password" all pass. No uppercase requirement, no digit requirement, no check against common password lists. For a platform that handles (paper) trading decisions, this is inadequate.

### 10.4 The `name` field in user registration is not sanitized. [MEDIUM]
The name from registration (`_reg_name` on line 1133) flows into: (a) the profile dict, (b) the verification email HTML template, (c) the sidebar display (`_user_display` on line 1300 via `unsafe_allow_html=True`). If the name contains HTML, it could be rendered as HTML in the sidebar.

### 10.5 `save_profile` is a read-modify-write with no transactional guarantee. [HIGH]
`save_profile()` (data_store.py line 209-213) does: `profiles = load_profiles()` then `profiles[user_id] = profile` then `save_profiles(profiles)`. If two users register simultaneously, one profile overwrites the other. The `_write_json` lock protects the file write itself, but the read-modify-write cycle is not atomic. User A reads profiles, User B reads profiles, User A writes, User B writes -- User A's profile is gone.

### 10.6 PBKDF2 with 100,000 iterations is below OWASP 2024 recommendation. [MEDIUM]
Line 103: `hashlib.pbkdf2_hmac("sha256", ..., 100_000)`. OWASP recommends 600,000 iterations for PBKDF2-HMAC-SHA256 as of 2024. The current setting is ~6x weaker than recommended. For a trading platform, even a paper one, this is a reputation risk.

### 10.7 No audit log for security events. [MEDIUM]
There is no persistent log of: failed login attempts, password changes, session creation/destruction, email verification attempts, tier changes. Only `agent_logs.txt` has auto-trader events. If an account is compromised, there is no forensic trail.

### 10.8 The entire user data directory (`users/`) is not in `.gitignore`. [QUESTION]
Is `users/` in `.gitignore`? If not, `_profiles.json` (containing password hashes and salts), `_sessions.json` (containing active session tokens), and all user data could be committed to the repository.

---

## SEVERITY SUMMARY

| Severity | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 5 | No brute-force protection on verification, session token in URL, settings page is a placebo (3 instances), only 2 gated pages |
| HIGH | 8 | Verification code in logs/subject, no resend rate limit, race condition on sessions, scan limit not enforced, settings not per-user, save_profile race condition, PBKDF2 too weak, MTF data source unknown |
| MEDIUM | 14 | SMTP crash on bad port, email validation trivial, HTML injection in name, language not persisted, number formatting, no IP binding, string-based tier checks, correlation groups static, no audit log, no HTTPS, no CSRF, staleness warning, direct file I/O bypassing DataStore, sidebar display injection |
| LOW | 8 | Bounce handling, rerun destroys state, cleanup only on create, query params cleared, no unsaved changes warning, file delete race, decisions file re-read, no MTF unavailable indicator |
| QUESTION | 5 | Why is verification skippable? Who wrote Arabic translations? Why was social pulse ever locked? Is users/ in .gitignore? What about trial expiry mid-session? |

**Total: 40 findings across 10 categories.**

---

## THE BOTTOM LINE

Sprint 11 shipped a lot of surface area but the foundation under it is hollow. The settings page is the most concerning: it gives users 30+ knobs that control absolutely nothing because the backend never reads the file. That is worse than not having settings at all -- it actively deceives users into thinking they have control. The session token in the URL is a textbook security mistake that would fail any security review. The i18n covers roughly 10% of the actual UI text. And the business model gates 2 out of 26 pages behind a paywall while giving away everything else for free.

The auto-trader bug fixes (graduated drawdown, correlation guard) are genuinely good engineering, but they are undermined by the settings page that claims to expose these parameters without actually wiring them through. Fix the settings-to-backend pipeline, move the session token into a cookie, add rate limiting on auth endpoints, and wire up the i18n to the rest of the dashboard. Until then, Sprint 11 is a facade.
