# QA Audit: Landing Pages, Authentication & i18n

**Auditor:** Landing Page & Auth QA Agent
**Date:** 2026-02-27
**Files Tested:**
- `landing/index.html` (1076 lines)
- `landing/pricing.html` (309 lines)
- `src/auth_manager.py` (658 lines)
- `src/i18n.py` (618 lines)

**Severity Guide:**
- **P0 CRITICAL** -- Security vulnerability, data loss, or legal liability
- **P1 HIGH** -- Broken functionality, misleading claims, or significant UX failure
- **P2 MEDIUM** -- Incorrect data, usability issue, or moderate concern
- **P3 LOW** -- Minor polish, best-practice deviation, or cosmetic issue

---

## Summary

| Severity | Count |
|----------|-------|
| P0 CRITICAL | 5 |
| P1 HIGH | 9 |
| P2 MEDIUM | 12 |
| P3 LOW | 8 |
| **TOTAL** | **34** |

---

## 1. landing/index.html

### F-01: OG Image Does Not Exist (P1 HIGH)

**Lines 12, 17:** `og:image` and `twitter:image` point to `/assets/og-preview.png`. No `assets/` directory exists anywhere in the project. Social media shares will show a broken image or no preview.

**Fix:** Create an OG preview image (1200x630px recommended) and place it at `landing/assets/og-preview.png`, or update the meta tags to a valid path/URL.

---

### F-02: Hardcoded "Live" Scoreboard Is Misleading (P0 CRITICAL)

**Lines 183-263:** The section is labeled "LIVE PREDICTION SCOREBOARD" but the data is entirely hardcoded HTML. The dates ("Feb 26", "Feb 25", "Feb 24"), assets, signals, outcomes, and accuracy figures (63%, 81%, 58%) are all static. This will become stale within days of deployment.

**Legal risk:** Presenting fabricated/stale prediction data as "live" could constitute misleading advertising. The 63% accuracy claim appears in the hero stats (line 159) and the scoreboard (line 249). If actual system accuracy diverges from 63%, this is a material misrepresentation.

**Fix:** Either (a) make it truly dynamic by fetching from `market_predictions.json` via a lightweight API, or (b) remove the word "LIVE" and add a clear disclaimer like "Sample data. Actual performance available inside the app." Also add a "last updated" timestamp.

---

### F-03: Hero Stats Are Fabricated (P1 HIGH)

**Lines 152-172:** The hero section shows "347 Predictions Tracked", "63% Avg Accuracy", "12 Assets Covered", "$0 Forever Free". These are static numbers that may not reflect actual system state. The `id="stat-predictions"` on line 154 suggests dynamic population was intended but never wired up.

**Fix:** Either pull these from actual data or add clear context (e.g., "as of Feb 2026") and keep them manually updated.

---

### F-04: "What We Learned" Box Contains Fabricated Analysis (P2 MEDIUM)

**Lines 267-277:** The "Oil BUY call on Feb 25 was wrong" narrative, including the specific RSI value (72) and the "WEIGHT UPDATED: opec_impact +15%" claim, is hardcoded fiction. If someone checks the actual system and finds no such adjustment, it undermines trust.

**Fix:** Either pull this from `memory/market_lessons.json` dynamically or label it as "Example of how the system learns."

---

### F-05: Dead Link -- Changelog (P2 MEDIUM)

**Line 963:** Footer link `<a href="#">Changelog</a>` points to `#` which scrolls to page top. No changelog page exists.

**Fix:** Create a changelog page or remove the link.

---

### F-06: GitHub Link May Be Invalid (P2 MEDIUM)

**Line 969:** Footer link points to `https://github.com/aegis-terminal`. This GitHub organization/repo may not exist. If it does not exist, visitors land on a 404.

**Fix:** Verify the GitHub URL exists or remove/update the link.

---

### F-07: /app Links Assume Specific Routing (P2 MEDIUM)

**Lines 105-106, 143, 253, 280, 937, 970:** Multiple CTAs link to `/app`. This assumes a specific deployment topology where the Streamlit dashboard is served at `/app`. In development or many deployment configs, this will 404.

**Fix:** Make the URL configurable or add a comment documenting the expected deployment setup. At minimum, ensure the landing page deploy has a redirect or proxy rule for `/app`.

---

### F-08: TradingView Widget Potential Issues (P2 MEDIUM)

**Lines 62-86:** The TradingView ticker tape widget uses `async` script loading with inline JSON configuration. Issues:
1. The widget uses PEPPERSTONE:NATGAS which may not resolve on all TradingView plans.
2. Ticker symbols may differ from what the actual app uses (yfinance tickers vs TV tickers).
3. The container height is fixed at 46px which may clip on some browsers.

**Fix:** Verify all TV symbols render correctly. Add a CSS fallback if the widget fails to load (currently shows empty space).

---

### F-09: No Skip-to-Content or ARIA Landmarks (P2 MEDIUM)

The page lacks:
- Skip-to-content link for keyboard navigation
- `role="main"` on the main content area
- `aria-label` on the nav element (line 89)
- `alt` text on any images (though the page uses SVGs inline)
- The scoreboard table uses `div` grids instead of semantic `<table>` markup, making it inaccessible to screen readers

**Fix:** Add `<a href="#main" class="sr-only">Skip to content</a>`, add `role` attributes, and consider using semantic table markup for the scoreboard.

---

### F-10: Tailwind CDN in Production (P3 LOW)

**Line 23:** `<script src="https://cdn.tailwindcss.com"></script>` is the development CDN which Tailwind explicitly warns against using in production. It adds ~300KB of JS that runs client-side to generate CSS.

**Fix:** For production, use Tailwind CLI to generate a static CSS file. This will dramatically improve FCP (First Contentful Paint).

---

### F-11: render-blocking Google Fonts (P3 LOW)

**Lines 20-22:** Google Fonts loaded with `<link>` are render-blocking. Two font families (Inter + JetBrains Mono) with multiple weights means significant blocking time.

**Fix:** Add `display=swap` (already present in URL) but also consider `<link rel="preload" as="style">` pattern or async loading.

---

### F-12: No Structured Data / Schema.org (P3 LOW)

No JSON-LD structured data for SoftwareApplication, Organization, or Product schema. This hurts SEO rich snippets.

**Fix:** Add `<script type="application/ld+json">` with Organization + SoftwareApplication schema.

---

### F-13: Scroll Animation JS -- No Reduced Motion Respect (P3 LOW)

**Lines 992-1001:** The IntersectionObserver fade-in animations do not respect `prefers-reduced-motion: reduce`. Users with vestibular disorders may experience discomfort.

**Fix:** Add `@media (prefers-reduced-motion: reduce) { .fade-in { opacity: 1; transform: none; transition: none; } }` to the CSS.

---

### F-14: Mobile Menu Links Lack Keyboard Accessibility (P3 LOW)

**Lines 114-124:** The mobile menu uses `onclick="closeMobileMenu()"` on anchor tags. The hamburger button (line 108) has `aria-label="Menu"` which is good, but does not have `aria-expanded` attribute to indicate menu state.

**Fix:** Add `aria-expanded="false"` to the button and toggle it in the JS click handler.

---

### F-15: Auto-Rotate Causes Multiple setTimeout Stacking (P2 MEDIUM)

**Lines 1039-1044:** When a user manually clicks a tab, the code clears the interval but then sets a `setTimeout` of 10s to restart. If the user clicks multiple tabs rapidly, multiple `setTimeout` callbacks will fire, each calling `startAutoRotate()`, resulting in multiple overlapping intervals.

**Fix:** Store the timeout ID and clear it before setting a new one:
```js
let resumeTimeout;
btn.addEventListener('click', () => {
    clearInterval(showcaseInterval);
    clearTimeout(resumeTimeout);
    currentTabIdx = tabOrder.indexOf(btn.dataset.tab);
    resumeTimeout = setTimeout(startAutoRotate, 10000);
});
```

---

## 2. landing/pricing.html

### F-16: Annual Price Math Is Wrong (P1 HIGH)

**Line 289:** Annual toggle sets Pro price to `$22/mo (billed $264/yr)`.

$29/mo with 25% discount = $21.75/mo = $261/yr. The page shows $22/mo billed $264/yr. $22 x 12 = $264, so the per-month price is rounded UP but the yearly total is consistent with $22. However, STRATEGY.md (line 15) says the annual price is $249/yr, which would be $20.75/mo. The landing page, pricing page, and strategy doc all disagree.

| Source | Monthly | Annual/yr |
|--------|---------|-----------|
| STRATEGY.md | $29 | $249 |
| pricing.html | $29 -> $22 | $264 |
| 25% of $29*12 = $348 | $21.75 | $261 |

**Fix:** Decide on the canonical annual price and make all sources agree. If 25% off: $261/yr ($21.75/mo). If $249/yr per STRATEGY.md: that is ~28.4% off, not 25%.

---

### F-17: Enterprise Annual Price Not From Strategy Doc (P2 MEDIUM)

**Line 291:** Annual toggle sets Enterprise to `$149/seat/mo (billed yearly)`. STRATEGY.md says $199/seat/mo with no annual discount mentioned. $149 represents a 25% discount applied, but billed yearly amount is not shown (would be $149 x 12 = $1,788/seat/yr). The vague "(billed yearly)" text gives no actual annual total.

**Fix:** Show the actual yearly total per seat, and verify the discount matches strategy docs.

---

### F-18: Free Tier Feature List Conflicts With TIERS Dict (P1 HIGH)

**auth_manager.py lines 33-48 (TIERS["free"]):**
- `max_assets: 5` -- but pricing page says "AI signals for 12+ assets" (line 102)
- `social_sentiment: False` -- but pricing page says "Social sentiment tracking" (line 106)
- `risk_dashboard: False` -- but pricing page says "Risk dashboard" (line 110)
- `autopilot: False` -- but pricing page says "Paper trading bot (13 gates)" (line 105)
- `max_scans_per_day: 3` -- not mentioned on pricing page
- `chart_indicators: 3` -- not mentioned on pricing page

The TIERS dict severely restricts free users, but the pricing page promises nearly everything for free. This is a MAJOR discrepancy. Either the code will block users from features the pricing page promised, causing rage, or the TIERS dict is outdated.

**Also:** STRATEGY.md says free tier gets "5 assets, 3 scans/day, basic signals only, confidence as Low/Medium/High (no numeric %), manual paper trading only (10 positions max), headlines only (no sentiment scores), 3 chart indicators." This matches the TIERS dict but CONTRADICTS the pricing page.

**Fix:** Reconcile. If the product intent is to give most features free (as stated in CLAUDE.md: "PRO_VIEWS to only optimizer + strategy_lab"), then update the TIERS dict to match the pricing page. Currently the TIERS dict would block features the pricing page explicitly promises as free.

---

### F-19: Pro Feature Claims Not Fully Implemented (P2 MEDIUM)

**Pricing page Pro tier lists:**
- "Priority signal updates" (line 136) -- No implementation found for priority signals
- "Email morning brief" (line 137) -- Morning brief exists in code but email delivery is not implemented beyond SMTP verification
- "Telegram notifications" (line 138) -- No Telegram integration code found
- "Webhook integrations" (line 139) -- Marked "soon" which is fine
- "Broker integration (Alpaca)" (line 140) -- Marked "soon" which is fine

**Fix:** Mark unimplemented features with "soon" labels like the last two, or implement them. Listing undeliverable features as included (without "soon") is misleading.

---

### F-20: FAQ Accordion Uses Native `<details>` -- Good But Inconsistent (P3 LOW)

The FAQ uses native HTML `<details>/<summary>` elements, which is excellent for accessibility. However, the first FAQ (line 202) has the `open` attribute, which is fine UX but means it starts expanded. No issues here, just noting good practice.

---

### F-21: No Privacy Policy or Terms of Service Links (P1 HIGH)

Neither the landing page nor the pricing page links to a Privacy Policy or Terms of Service. For a financial product that collects email addresses and tracks user data, this is a legal requirement in most jurisdictions (GDPR, CCPA, etc.).

**Fix:** Create Privacy Policy and Terms of Service pages and link them from the footer of both pages.

---

## 3. src/auth_manager.py -- Security Audit

### F-22: Verification Code Logged to Debug Output (P0 CRITICAL)

**Lines 222-226, 260-269:** When SMTP is not configured, the verification code is logged via `logger.debug()`. In production with DEBUG log level enabled (common in early deployments), this exposes verification codes in log files. Even worse, lines 260-269 log codes on SMTP failures.

The comment on line 227 says "Code intentionally NOT printed to stdout in production" but `logger.debug()` still writes to log files/handlers.

**Fix:** Never log verification codes, even at DEBUG level. Log only that a code was generated, not the code itself. Use a separate, secured audit log if code debugging is needed.

---

### F-23: No Brute-Force Protection on Login (P0 CRITICAL)

**Lines 337-354:** The `login()` method has ZERO rate limiting. An attacker can make unlimited login attempts with no lockout, delay, or rate limit. The verify_email method has rate limiting (5 attempts/15 min) but login does not.

This is trivially exploitable. With a 6-character minimum password, a brute-force attack is feasible.

**Fix:** Add rate limiting similar to verify_email: track failed login attempts per email, lock account after N failures, require CAPTCHA or delay after M failures.

---

### F-24: Session Tokens Stored in Plain JSON File (P1 HIGH)

**Lines 557-562:** Session tokens are stored in `users/_sessions.json` as plain text JSON. Any process with file read access can steal all active sessions. The file is not encrypted, has no file permissions set, and is in a predictable location.

**Fix:** At minimum:
1. Set restrictive file permissions (0600) on the sessions file
2. Store hashed session tokens (hash the token, store the hash; compare hashes on validation)
3. Long-term: Move to server-side session store (Redis) with encrypted tokens

---

### F-25: Active Session File Enables Session Hijacking (P1 HIGH)

**Lines 619-624:** `save_active_session()` writes the raw session token to `users/_active_session.json`. This file is a single-token storage that ANY user on the same machine can read. If the machine is shared, any user can steal the session.

Also: `load_active_session()` on line 638 injects the token into the profile dict as `_session_token`, which then travels through the application and could be logged or exposed.

**Fix:** Encrypt the session file or use OS-level credential storage. Remove the `_session_token` injection into the profile dict.

---

### F-26: Timing Attack on Login -- Different Error Messages (P1 HIGH)

**Lines 351-354:** Login returns "Invalid password." when the email exists but password is wrong, and "No account found with that email." when the email does not exist. This allows user enumeration -- an attacker can determine which emails have accounts.

**Fix:** Return a single generic message for both cases: "Invalid email or password." The `_verify_password` function correctly uses `hmac.compare_digest` (line 111) which prevents timing-based password comparison attacks, but the error message differentiation undermines this.

---

### F-27: Registration Allows User Enumeration (P2 MEDIUM)

**Lines 288-289:** Registration returns "Email already registered." when a duplicate email is found. This confirms to an attacker that a specific email has an account.

**Fix:** Always return success (or a generic message like "If this email is not already registered, you will receive a verification email.") and silently skip duplicate registration. Send a "someone tried to register with your email" notification to the existing user.

---

### F-28: No Password Complexity Requirements (P2 MEDIUM)

**Line 283:** Only check is `len(password) < 6`. No requirements for uppercase, lowercase, numbers, or special characters. A password like "aaaaaa" is accepted.

**Fix:** Add minimum complexity requirements or use a password strength library (e.g., zxcvbn). At minimum require 8+ characters.

---

### F-29: Session Cleanup Race Condition (P2 MEDIUM)

**Lines 567-577:** `create_session()` loads all sessions, filters expired ones, adds the new one, and saves. If two sessions are created concurrently, one write will overwrite the other. The `_save_sessions` method has no file locking (unlike the DataStore which uses threading.Lock).

**Fix:** Use the same `_get_lock()` mechanism from data_store.py for the sessions file, or use DataStore for session storage.

---

### F-30: Trial System Can Be Exploited (P2 MEDIUM)

**Lines 512-520:** `start_trial()` only checks `profile.get("tier") == "free"`. After a trial expires and the user is downgraded back to "free" (line 533), they could potentially trigger `start_trial()` again for another 14-day Pro trial. There is no check for `trial_started` being already set.

**Fix:** Add a check: `if profile.get("trial_started") is not None: return "Trial already used."` before starting a new trial.

---

### F-31: Guest Mode Shares Data With All Guests (P2 MEDIUM)

**data_store.py lines 86-87:** The default user ID maps to the `memory/` directory. All guest users share the same data directory, meaning one guest can see another guest's paper trades, predictions, and settings.

This is documented ("backward compat") but is still a privacy issue in a multi-user deployment.

**Fix:** Generate ephemeral user IDs for guest sessions, or clearly warn users that guest data is shared/public.

---

## 4. src/i18n.py -- Translation & RTL Audit

### F-32: Missing Translation Keys for Auth Error Messages (P1 HIGH)

Auth error messages in `auth_manager.py` are all English-only hardcoded strings:
- "Invalid email address." (line 281)
- "Password must be at least 6 characters." (line 283)
- "Email already registered." (line 289)
- "Invalid password." (line 352)
- "No account found with that email." (line 354)
- "Too many verification attempts..." (line 381)
- "Incorrect verification code." (line 403)
- All other error strings

These are user-facing messages that will appear in English regardless of language setting.

**Fix:** Add i18n keys for all auth error messages and use `t()` in auth_manager (requires importing i18n or passing error keys back to the dashboard layer).

---

### F-33: No i18n for Landing Pages (P2 MEDIUM)

Both `landing/index.html` and `landing/pricing.html` are English-only with no language switcher or detection. Users who set their language to German or Arabic in the app will see a fully English landing page.

**Fix:** For MVP this is acceptable, but add `hreflang` meta tags at minimum. Long-term, create localized landing pages or implement client-side i18n.

---

### F-34: RTL CSS Does Not Cover All Streamlit Components (P3 LOW)

**Lines 544-573:** The RTL CSS targets `.main .block-container`, `stMetricValue`, `stMetricLabel`, `.stMarkdown`, and table cells. But it does not cover:
- `st.selectbox` dropdown alignment
- `st.tabs` tab labels
- `st.expander` headers
- `st.dataframe` / `st.data_editor`
- Toast/notification messages
- Sidebar content (documented as "Streamlit limitation" on line 567)

**Fix:** Expand RTL CSS selectors as Streamlit components are identified. This is an ongoing effort.

---

## Cross-Cutting Issues

### F-18 Expanded: The Great Tier Contradiction (P0 CRITICAL)

This is the single most dangerous issue across the entire public-facing surface. Three sources define the free tier differently:

| Feature | STRATEGY.md | TIERS dict (auth_manager) | Pricing Page |
|---------|-------------|---------------------------|--------------|
| Assets | 5 | 5 | 12+ |
| Scans/day | 3 | 3 | Not mentioned |
| Social Sentiment | No | No | YES |
| Risk Dashboard | No | No | YES |
| Autopilot Bot | No | No | YES (13 gates) |
| Chart Indicators | 3 | 3 | Not mentioned |
| Confidence Display | Low/Med/High | Not gated | 0-100% implied |

The pricing page promises a lavish free tier. The code enforces a restricted one. Users who sign up based on the pricing page will immediately hit walls. This is a conversion killer and potential legal issue (false advertising).

**Resolution needed:** Product decision. Pick ONE source of truth and update the others.

### F-35: No HTTPS Enforcement or CSP Headers (P0 CRITICAL)

Neither landing page has:
- Content Security Policy headers (allows XSS via injected scripts)
- No `X-Frame-Options` or `frame-ancestors` CSP (allows clickjacking)
- No `X-Content-Type-Options: nosniff`
- No Strict-Transport-Security header

These are deployment-level concerns but MUST be addressed before going public with an auth system.

**Fix:** Configure web server (Nginx/Cloudflare) with appropriate security headers. Add `<meta http-equiv="Content-Security-Policy">` as a fallback for the landing pages.

---

## Recommendations by Priority

### Immediate (Before Launch)

1. **F-02/F-03:** Remove "LIVE" label from scoreboard, add disclaimer, or make it truly dynamic
2. **F-18:** Reconcile free tier definition across STRATEGY.md, TIERS dict, and pricing page
3. **F-22:** Stop logging verification codes at any log level
4. **F-23:** Add login brute-force protection (rate limiting + account lockout)
5. **F-35:** Add security headers before deploying auth system publicly

### High Priority (First Week)

6. **F-01:** Create OG preview image
7. **F-16:** Fix annual pricing math discrepancy
8. **F-21:** Add Privacy Policy and Terms of Service
9. **F-24/F-25:** Secure session storage (at minimum hash tokens)
10. **F-26:** Use generic login error message to prevent user enumeration
11. **F-32:** Add i18n keys for auth error messages

### Medium Priority (First Sprint)

12. **F-04/F-05/F-06/F-07:** Fix dead links, fake content, /app routing
13. **F-19:** Mark unimplemented Pro features as "coming soon"
14. **F-28:** Strengthen password requirements
15. **F-29:** Add file locking to session operations
16. **F-30:** Prevent trial re-use exploit

### Low Priority (Backlog)

17. **F-10:** Replace Tailwind CDN with static build
18. **F-09/F-13/F-14:** Accessibility improvements
19. **F-12:** Add structured data for SEO
20. **F-34:** Expand RTL CSS coverage
