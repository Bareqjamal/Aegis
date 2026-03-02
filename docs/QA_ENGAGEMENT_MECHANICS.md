# QA Report: Engagement Mechanics (Prediction Game, Morning Email, Scorecard)

**Date:** 2026-02-27
**Scope:** `src/prediction_game.py`, `src/morning_email.py`, dashboard integration in `dashboard/app.py`
**Status:** 19 findings (3 P0 CRITICAL, 5 P1 HIGH, 7 P2 MEDIUM, 4 P3 LOW)

---

## P0 CRITICAL (3 findings) -- System is fundamentally broken

### P0-1: `_check_outcome()` reads wrong field names -- validation NEVER matches

**File:** `src/prediction_game.py`, lines 128-144
**Impact:** Outcome validation is completely non-functional. No votes will ever be validated.

The `_check_outcome()` function expects these fields in `market_predictions.json`:
- `pred.get("date", "")` -- **DOES NOT EXIST**. The actual field is `"timestamp"`.
- `pred.get("correct", False)` -- **DOES NOT EXIST**. The actual field is `"outcome"` (string: `"correct"`, `"incorrect"`, `"neutral"`).
- `pred.get("actual_move_pct", 0)` -- **DOES NOT EXIST** in predictions data.

Actual prediction schema (from `market_learner.py` and live `market_predictions.json`):
```json
{
  "timestamp": "2026-02-08T21:48:07.087407+00:00",
  "asset": "Gold",
  "signal_label": "NEUTRAL",
  "validated": true,
  "outcome": "correct",
  "outcome_price": 5008.5,
  "outcome_date": "2026-02-19T13:46:12.641944+00:00"
}
```

What the code expects:
```python
pred_date = pred.get("date", "")[:10]         # WRONG: should be "timestamp"
correct = pred.get("correct", False)           # WRONG: should be pred.get("outcome") == "correct"
actual_move = pred.get("actual_move_pct", 0)   # WRONG: field doesn't exist
```

**Result:** `pred_date` is always `""`, so the date match `pred_date == vote_date` never succeeds. The function always returns `None`. Every vote stays permanently in "pending" state. The entire scorecard, streak system, and user-vs-AI comparison are dead features.

**Fix:**
```python
pred_date = pred.get("timestamp", "")[:10]  # Extract date from timestamp
# ...
signal_correct = (pred.get("outcome") == "correct")
# actual_move_pct can be computed from entry_price + outcome_price
```

---

### P0-2: `get_signals_you_ignored()` reads wrong field names -- always returns empty

**File:** `src/prediction_game.py`, lines 435-463
**Impact:** "Signals You Ignored" section (the regret engine) never shows anything.

Four field name mismatches:
1. `pred.get("correct")` on line 450 -- **DOES NOT EXIST**. Should check `pred.get("outcome") == "correct"`.
2. `pred.get("date", "")[:10]` on line 452 -- **DOES NOT EXIST**. Should be `pred.get("timestamp", "")[:10]`.
3. `pred.get("signal", "")` on line 457 -- **DOES NOT EXIST**. Should be `pred.get("signal_label", "")`.
4. `pred.get("actual_move_pct", 0)` on line 458 -- **DOES NOT EXIST**. No equivalent field in predictions data.

**Result:** Line 450's `pred.get("correct")` is always `None` (falsy), so the `continue` fires for every prediction. The loop always returns an empty list. The regret engine is dead.

**Fix:** Map all field names to actual `market_predictions.json` schema: `timestamp` for dates, `outcome` for correctness, `signal_label` for signal, compute actual_move_pct from entry_price/outcome_price.

---

### P0-3: `validate_outcomes()` inherits the broken `_check_outcome()` -- user stats never update

**File:** `src/prediction_game.py`, lines 237-283
**Impact:** Because `_check_outcome()` (P0-1) always returns `None`, `validate_outcomes()` never finds validated outcomes. The entire stats pipeline is dead:
- `correct_agrees` stays at 0
- `correct_disagrees` stays at 0
- `current_streak` stays at 0
- `best_streak` stays at 0
- `user_accuracy` is always 0%
- `ai_accuracy` is always 0%
- `user_beat_ai` is always `None`

The scorecard at the top of the Advisor page will never show meaningful results. Users see "Pending..." forever. This breaks the core engagement loop: users vote, but never get feedback. They will stop voting within days.

---

## P1 HIGH (5 findings) -- Significant functional or UX issues

### P1-1: No HTML escaping in morning email -- XSS vector in email clients

**File:** `src/morning_email.py`, lines 200-221 (scorecard rows), 286-330 (signal cards)
**Impact:** User-controlled or prediction-generated data is injected directly into HTML without escaping.

Fields at risk:
- `asset` name (line 209): `{asset}` rendered raw in `<td>` tags
- `signal` label (line 212): `{signal}` rendered raw
- `note` text (line 218): `{note}` rendered raw (from `outcome_note`)
- `reason` text (line 327): `{reason}` rendered raw in signal cards
- `headline` and `key_takeaway` (lines 510, 544): rendered raw in email body

While current data sources are internal (market scanner, AI predictions), if any prediction note or headline contains `<script>` or malformed HTML, it could:
1. Break email rendering in certain clients
2. Pose an XSS risk in webmail clients that don't strip HTML

**Fix:** Use `html.escape()` from the standard library on all interpolated text values.

---

### P1-2: Race condition on `record_vote()` -- concurrent votes can lose data

**File:** `src/prediction_game.py`, lines 158-211
**Impact:** In Streamlit, if a user clicks Agree/Disagree quickly on two different assets, two concurrent `record_vote()` calls race:
1. Both call `_load_game()` and get the same snapshot
2. Both append their vote
3. Both call `_save_game()`
4. The second write overwrites the first -- one vote is lost

The atomic write (tempfile + replace) protects against partial writes but not against concurrent read-modify-write cycles. There is no file locking.

**Likelihood:** Medium in Streamlit (each rerun is sequential per user session), but possible with auto-refresh + simultaneous button clicks, or with multiple browser tabs.

**Fix:** Add a file lock (`fcntl.flock` on Linux, `msvcrt.locking` on Windows, or use `portalocker` library). Alternatively, use a retry-with-compare-and-swap pattern.

---

### P1-3: "Can You Beat the AI?" callout logic gap -- hidden state between first vote and first scorecard

**File:** `dashboard/app.py`, lines 2236-2297
**Impact:** The display logic is:
```python
if _pg_scorecard["total_votes"] > 0:
    # Show yesterday's scorecard
elif _pg_streak["total_votes"] == 0:
    # Show "Can You Beat the AI?" callout
```

There is a gap: When the user has voted today (so `total_votes > 0` in streak stats), but there is nothing to show for yesterday (`_pg_scorecard["total_votes"] == 0`), NEITHER branch renders. The user sees an empty space -- no scorecard, no callout. This happens every day until yesterday's votes get validated (which per P0-1 is never).

Even if P0-1 is fixed, on the first day after voting the user gets no visual feedback. The callout should persist until there is actually a scorecard to show.

**Fix:** Change the elif to:
```python
elif _pg_streak["total_votes"] == 0 or _pg_scorecard["total_votes"] == 0:
```

---

### P1-4: `total_votes` stat counter inflates on vote updates

**File:** `src/prediction_game.py`, lines 176-211
**Impact:** When a user changes their vote (clicking Disagree after initially clicking Agree), the code finds the existing vote and updates it in-place (line 183-187). This is correct. But the first time they vote, `total_votes` is incremented (line 203). If they then change their vote, the early return at line 187 means `total_votes` is NOT incremented again. This part is fine.

However, there is a subtlety: the `total_votes` stat is never decremented or reconciled. If the votes list is truncated to 500 (line 208), `total_votes` can be (say) 600 while only 500 votes exist. The stat counter diverges from the actual vote list length over time.

**Result:** `get_streak()` returns `total_votes: 600` but only 500 votes are in the data. The "Can You Beat the AI?" callout uses `_pg_streak["total_votes"] == 0` which works correctly (only 0 is the threshold), but any UI showing lifetime vote count will display an inflated number.

**Fix:** Either reconcile `total_votes` with `len(data["votes"])` after truncation, or compute it dynamically from the list.

---

### P1-5: Morning email CTA links to `localhost:8501` -- broken in production

**File:** `src/morning_email.py`, lines 553, 631
**Impact:** The "Open Aegis Terminal" button and the plain-text link both point to `http://localhost:8501`. In any deployment scenario (cloud, VPS, shared hosting), this link is useless. Users clicking the CTA will see a connection error.

**Fix:** Make the URL configurable via environment variable (e.g., `AEGIS_APP_URL`), defaulting to `http://localhost:8501` for local dev.

---

## P2 MEDIUM (7 findings) -- Edge cases and robustness issues

### P2-1: No input sanitization on `user_id` in `_get_game_path()` -- path traversal risk

**File:** `src/prediction_game.py`, lines 47-54
**Impact:** `user_id` is used directly in a file path: `USERS_DIR / user_id / "prediction_game.json"`. If `user_id` contains `../` or other path traversal sequences, it could read/write files outside the intended directory.

Current mitigation: `user_id` comes from `st.session_state["user_id"]` which is set by `auth_manager.py` during login. The auth manager likely generates safe IDs. But if any code path allows arbitrary user_id values, this is exploitable.

**Fix:** Validate `user_id` against a safe pattern (alphanumeric + underscore only) or use `Path.resolve()` and verify it stays within `USERS_DIR`.

---

### P2-2: `get_yesterday_scorecard()` calls `validate_outcomes()` which triggers disk I/O on every page load

**File:** `src/prediction_game.py`, lines 305-380
**Impact:** Every time the Advisor page renders, `get_yesterday_scorecard()` is called (line 2232 of app.py), which internally calls `self.validate_outcomes()` (line 330). This:
1. Loads the game data (disk read)
2. Loads ALL market predictions (disk read of potentially large file)
3. Iterates all votes checking for unvalidated outcomes
4. Saves game data if any validated (disk write)
5. Then loads game data AGAIN (line 332)

With Streamlit's 10-second auto-refresh, this runs 6 times per minute per user. It reads the predictions file from disk every time without caching.

**Fix:** Cache the scorecard result with a short TTL (e.g., 60s). Only run validation once per session or on explicit action.

---

### P2-3: Streak calculation uses `created_at` sort but votes may share timestamps

**File:** `src/prediction_game.py`, lines 285-303
**Impact:** `_update_streak()` sorts by `created_at` (ISO timestamp string) in reverse order, then counts consecutive "correct" outcomes. If two votes have identical `created_at` values (possible if recorded in the same second), the sort order between them is arbitrary. A "wrong" vote could sort before a "correct" one, prematurely breaking the streak.

Additionally, the streak spans ALL time, not just recent days. A user who had 50 correct votes 6 months ago but got 1 wrong today still shows streak = 0. This is correct but may feel discouraging.

**Fix:** Add a secondary sort key (e.g., asset name) for deterministic ordering. Consider whether streak should be date-based (consecutive correct days) rather than vote-based.

---

### P2-4: Morning email rate limiting is per-process, not per-user

**File:** `src/morning_email.py`, lines 42-43, 649-660
**Impact:** The `_last_send_ts` is a module-level global variable. In a Streamlit deployment, all users share the same process. If User A sends a morning email, User B cannot send one for 5 minutes -- even though they are different users.

Worse, if Streamlit forks or restarts the process, the rate limit resets. The cooldown provides no real protection against abuse.

**Fix:** Use per-user rate limiting with file-based or cache-based timestamps. Include `to_address` or `user_id` in the rate limit key.

---

### P2-5: Unsubscribe link is a dead `#unsubscribe` anchor

**File:** `src/morning_email.py`, line 566
**Impact:** The unsubscribe link points to `#unsubscribe` which does nothing. Under CAN-SPAM regulations (US) and GDPR (EU), commercial emails must have a functional unsubscribe mechanism. While this is currently a local/demo tool, it is a compliance risk if ever deployed to real users.

**Fix:** Either implement an unsubscribe endpoint or remove the link and add a note like "To stop receiving these emails, disable morning emails in your Aegis settings."

---

### P2-6: Dashboard vote buttons do not pass `ai_confidence` accurately

**File:** `dashboard/app.py`, lines 3027-3032
**Impact:** The vote buttons pass `ai_confidence=_adj_conf` but `_adj_conf` is the adjusted confidence after all boosts (regime, social, geo). The `record_vote()` function stores this as `ai_confidence`. When the scorecard later displays AI accuracy, it compares signal correctness (from market_learner) against these inflated confidence numbers. The mismatch could confuse analysis.

This is a data quality issue rather than a functional bug, but it means the stored confidence values are not directly comparable to the raw scanner confidence.

**Fix:** Either document that stored confidence includes all boosts, or pass the raw base confidence separately.

---

### P2-7: Morning email `_get_yesterday_scorecard` uses different accuracy logic than prediction_game

**File:** `src/morning_email.py`, lines 71-118 vs `src/prediction_game.py`, lines 305-380
**Impact:** The morning email and the prediction game calculate "accuracy" differently:

- **Morning email** (line 96-101): Uses AI predictions directly. Counts outcome `"correct"` / `"incorrect"` / `"neutral"`. Excludes neutral from accuracy denominator.
- **Prediction game** (line 354-359): Uses user votes. Counts user "correct" / "wrong". No neutral category exists for user votes.

These are measuring different things (AI accuracy vs user accuracy), which is fine. But the morning email's scorecard calls itself "Yesterday's Scorecard" -- same label as the dashboard. If a user sees 80% in the email and 60% on the dashboard, they will be confused because they measure different populations (all AI predictions vs only user-voted predictions).

**Fix:** Either align the labels to make the distinction clear, or use the same data source for both.

---

## P3 LOW (4 findings) -- Minor issues, code quality

### P3-1: `get_vote()` scans the full vote list linearly

**File:** `src/prediction_game.py`, lines 228-235
**Impact:** For each asset card on the Advisor page, `get_vote()` is called (line 3011 of app.py). It scans the entire `votes` list (up to 500 entries) looking for a match. With 12 assets, that is 12 * 500 = 6,000 comparisons per page load. Not a performance issue at current scale but inefficient.

**Fix:** Build a lookup dict `{(date, asset): vote}` once per page load instead of scanning for each asset.

---

### P3-2: `_pg_vote_color` hex-to-RGB parsing is fragile

**File:** `dashboard/app.py`, line 3016
**Impact:** The inline expression `','.join(str(int(_pg_vote_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))` converts a hex color to RGB for the `rgba()` background. This works for 6-digit hex codes but would crash for 3-digit shorthand, named colors, or if `_pg_vote_color` is somehow empty. Currently the colors are hardcoded (`#3fb950` or `#f85149`), so this is safe, but it is fragile if the palette ever changes.

**Fix:** Extract into a helper function with proper error handling.

---

### P3-3: `morning_email.py` CLI `--preview` and `--to` are mutually exclusive without explicit guard

**File:** `src/morning_email.py`, lines 746-752
**Impact:** If both `--preview` and `--to` are passed, only `--preview` runs (due to `if/elif`). This is acceptable but undocumented. The `--to` flag is silently ignored.

**Fix:** Either document the precedence or add `mutually_exclusive_group` in argparse.

---

### P3-4: `morning_email.py` plain-text fallback uses `--` instead of em-dash

**File:** `src/morning_email.py`, lines 597, 634
**Impact:** Minor formatting inconsistency. The HTML version uses `&mdash;` (em-dash) in the subject and footer, while the plain-text version uses `--`. This is standard practice for plain text and not a real bug, just noting for completeness.

---

## Summary Table

| ID | Severity | Component | Issue |
|----|----------|-----------|-------|
| P0-1 | CRITICAL | prediction_game.py | `_check_outcome()` reads nonexistent fields -- validation NEVER works |
| P0-2 | CRITICAL | prediction_game.py | `get_signals_you_ignored()` reads nonexistent fields -- always empty |
| P0-3 | CRITICAL | prediction_game.py | Stats pipeline dead because P0-1 blocks all validation |
| P1-1 | HIGH | morning_email.py | No HTML escaping on interpolated data |
| P1-2 | HIGH | prediction_game.py | Race condition on concurrent `record_vote()` calls |
| P1-3 | HIGH | dashboard/app.py | Display gap: no scorecard AND no callout after first vote |
| P1-4 | HIGH | prediction_game.py | `total_votes` counter diverges from actual vote count after truncation |
| P1-5 | HIGH | morning_email.py | CTA hardcoded to `localhost:8501` |
| P2-1 | MEDIUM | prediction_game.py | No path traversal guard on `user_id` |
| P2-2 | MEDIUM | prediction_game.py | `validate_outcomes()` triggers disk I/O on every page load |
| P2-3 | MEDIUM | prediction_game.py | Streak sort non-deterministic on equal timestamps |
| P2-4 | MEDIUM | morning_email.py | Rate limiting is per-process, not per-user |
| P2-5 | MEDIUM | morning_email.py | Dead unsubscribe link (compliance risk) |
| P2-6 | MEDIUM | dashboard/app.py | `ai_confidence` stores adjusted value, not raw |
| P2-7 | MEDIUM | morning_email.py | Different accuracy metric than dashboard, same label |
| P3-1 | LOW | prediction_game.py | Linear scan per asset in `get_vote()` |
| P3-2 | LOW | dashboard/app.py | Fragile hex-to-RGB inline parser |
| P3-3 | LOW | morning_email.py | CLI `--preview` silently overrides `--to` |
| P3-4 | LOW | morning_email.py | Minor dash formatting inconsistency |

---

## Mathematical Accuracy Audit

### 1. `user_accuracy = correct / (correct + wrong) * 100`
**File:** `src/prediction_game.py`, lines 354-359
**Verdict:** CORRECT (with div-by-zero guard). Returns 0 when `total_validated == 0`.

### 2. `ai_accuracy = ai_correct / (ai_correct + ai_wrong) * 100`
**File:** `src/prediction_game.py`, lines 361-364
**Verdict:** CORRECT (with div-by-zero guard). Returns 0 when `ai_total == 0`.

### 3. `user_beat_ai` logic
**File:** `src/prediction_game.py`, line 376
```python
"user_beat_ai": user_accuracy > ai_accuracy if total_validated > 0 and ai_total > 0 else None
```
**Verdict:** CORRECT for win/lose, but ties (user_accuracy == ai_accuracy) return `False`, not a tie state. The dashboard (line 2242) treats `False` as "The AI beat you" -- which is wrong for ties. A 60% vs 60% result would say "The AI beat you" when it should say "It's a tie!".

### 4. `_update_streak()` reverse sort
**File:** `src/prediction_game.py`, lines 286-303
**Verdict:** CORRECT logic. Sorts by `created_at` descending, counts consecutive "correct" from most recent. Breaks on first "wrong". However, see P2-3 for non-determinism issue on equal timestamps.

### 5. Morning email accuracy calculation
**File:** `src/morning_email.py`, lines 96-101
**Verdict:** CORRECT. Excludes neutral from denominator. Div-by-zero guarded.

### 6. Per-asset accuracy in `get_all_time_stats()`
**File:** `src/prediction_game.py`, lines 406-420
**Verdict:** CORRECT. Computes per-asset accuracy with div-by-zero guard.

---

## Recommendations (Priority Order)

1. **IMMEDIATE (P0s):** Fix field name mappings in `_check_outcome()` and `get_signals_you_ignored()`. Map `"date"` to `"timestamp"`, `"correct"` to `outcome == "correct"`, `"signal"` to `"signal_label"`. Compute `actual_move_pct` from `entry_price` and `outcome_price`. Without this fix, the entire prediction game is non-functional.

2. **NEXT (P1s):** Add `html.escape()` to morning email. Fix the display gap for users who have voted but have no scorecard yet. Fix the tie condition in `user_beat_ai`. Make the CTA URL configurable.

3. **THEN (P2s):** Add caching to `validate_outcomes()`. Implement per-user rate limiting. Add path sanitization. Fix the unsubscribe link.

4. **LATER (P3s):** Optimize vote lookups. Extract hex parser. Clean up CLI args.
