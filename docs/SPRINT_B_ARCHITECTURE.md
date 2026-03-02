# Sprint B: app.py Split Architecture Plan

## Current State
- `dashboard/app.py` = **9,900+ lines** in ONE file
- 28 views, 66 functions, 264 widgets
- Every button click re-executes the entire file

## Target State
```
dashboard/
    app.py                  (~300 lines — shell, auth, navigation only)
    components/
        __init__.py
        signal_card.py      (advisor card HTML builder)
        portfolio_ticker.py (sidebar portfolio widget)
        search_bar.py       (global search component)
        page_header.py      (render_page_header + breadcrumbs)
        impact_badge.py     (news impact HTML builder)
        social_bar.py       (social sentiment bar)
        glossary.py         (tooltip CSS + helper)
    pages/
        __init__.py
        advisor.py          (Daily Advisor — default landing)
        morning_brief.py
        watchlist.py
        charts.py
        paper_trading.py
        trade_journal.py
        watchlist_mgr.py
        alerts.py
        asset_detail.py
        news_intel.py
        econ_calendar.py
        report_card.py
        fundamentals.py
        strategy_lab.py
        analytics.py
        risk_dashboard.py
        optimizer.py
        market_overview.py
        kanban.py
        evolution.py
        performance.py
        monitor.py
        budget.py
        logs.py
        settings.py
    helpers/
        __init__.py
        data_loaders.py     (all load_* functions with @st.cache_data)
        price_fetcher.py    (fetch_live_prices + caching)
        chart_helpers.py    (chart rendering utilities)
        auth_helpers.py     (login form, auth checks)
        nav_helpers.py      (navigation state, view routing)
        styles.py           (CSS constants, SIGNAL_STYLES, DARK_LAYOUT)
```

## Migration Strategy (Incremental, Non-Breaking)

### Phase 1: Extract helpers/ (Day 1)
1. Create `helpers/data_loaders.py` — move ALL `load_*` functions
2. Create `helpers/price_fetcher.py` — move `fetch_live_prices` + cache
3. Create `helpers/styles.py` — move CSS strings + SIGNAL_STYLES dict
4. Update imports in app.py: `from helpers.data_loaders import *`
5. **Test:** App works identically, just cleaner imports

### Phase 2: Extract components/ (Day 2)
1. Move `render_page_header()`, `asset_link_button()`, glossary helpers
2. Move signal card HTML builder (the big f-string in advisor)
3. Move portfolio ticker sidebar widget
4. **Test:** App works identically

### Phase 3: Extract pages/ one at a time (Day 3-5)
1. Start with the simplest page (e.g., `kanban.py`)
2. Use Streamlit's `st.navigation()` API:
   ```python
   # app.py (new, slim version)
   import streamlit as st
   from pages import advisor, watchlist, charts, ...

   pages = {
       "advisor": advisor.render,
       "watchlist": watchlist.render,
       "charts": charts.render,
       ...
   }

   # Auth + sidebar here
   current_view = st.session_state.get("view", "advisor")
   pages[current_view]()
   ```
3. Each page file has a single `render()` function
4. Extract one page per commit — always have a working app

### Phase 4: Fragment-based refresh (Day 5)
1. Replace `st_autorefresh` with `@st.fragment` on price-dependent sections
2. Only the price/data fragment refreshes, not the entire page
3. **Result:** Zero flickering

## Key Rules During Migration
- **One page per commit** — always have a working app
- **Run py_compile after every change** — catch syntax errors immediately
- **Keep the old if/elif chain as fallback** until all pages are extracted
- **Shared state** via `st.session_state` (already used everywhere)
- **Shared data** via `helpers/data_loaders.py` (centralized caching)

## Estimated Timeline
| Task | Effort | Risk |
|------|--------|------|
| Extract helpers/ | 4 hours | Low |
| Extract components/ | 4 hours | Low |
| Extract 28 pages/ | 2-3 days | Medium |
| Fragment-based refresh | 4 hours | Low |
| **Total** | **3-5 days** | **Medium** |

## Dependencies
- Streamlit >= 1.36 (for `st.navigation()`)
- Current Streamlit version: check with `streamlit version`
- If < 1.36, use manual `if/elif` routing with imported render functions (still works)
