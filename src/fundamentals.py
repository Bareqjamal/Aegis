"""Fundamentals — Fetch fundamental data, earnings calendar, financials.

Uses yfinance to retrieve:
- Key ratios (P/E, EPS, market cap, dividend yield)
- Earnings calendar
- Financial statements (income, balance sheet, cash flow)
- Analyst ratings and price targets
"""

from datetime import datetime, timezone
import pandas as pd


def _detect_asset_type(ticker: str) -> str:
    """Detect asset type from ticker symbol."""
    t_upper = ticker.upper()
    if t_upper.endswith("=F"):
        return "commodity"
    if t_upper.endswith("-USD") and any(c in t_upper for c in ("BTC", "ETH", "SOL", "ADA", "DOGE", "XRP", "BNB", "AVAX")):
        return "crypto"
    if t_upper.endswith("=X"):
        return "forex"
    if t_upper.startswith("^"):
        return "index"
    return "stock"


def get_price_performance(ticker: str) -> dict:
    """Fetch price performance metrics for any asset type."""
    import yfinance as yf

    result = {
        "current_price": "N/A", "prev_close": "N/A",
        "day_change_pct": "N/A", "week_change_pct": "N/A",
        "month_change_pct": "N/A", "three_month_pct": "N/A",
        "six_month_pct": "N/A", "ytd_pct": "N/A",
        "year_change_pct": "N/A", "52w_high": "N/A", "52w_low": "N/A",
        "avg_volume": 0, "avg_volume_fmt": "N/A", "volatility_30d": "N/A",
    }
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty:
            return result

        close = hist["Close"]
        current = float(close.iloc[-1])
        result["current_price"] = round(current, 2)
        result["52w_high"] = round(float(close.max()), 2)
        result["52w_low"] = round(float(close.min()), 2)

        if len(close) >= 2:
            prev = float(close.iloc[-2])
            result["prev_close"] = round(prev, 2)
            result["day_change_pct"] = f"{(current - prev) / prev * 100:+.2f}%"

        for label, days in [("week_change_pct", 5), ("month_change_pct", 21),
                            ("three_month_pct", 63), ("six_month_pct", 126),
                            ("year_change_pct", 252)]:
            if len(close) > days:
                old = float(close.iloc[-days - 1])
                pct = (current - old) / old * 100
                result[label] = f"{pct:+.2f}%"

        year_start = close[close.index.year == close.index[-1].year]
        if len(year_start) > 1:
            first = float(year_start.iloc[0])
            result["ytd_pct"] = f"{(current - first) / first * 100:+.2f}%"

        if "Volume" in hist.columns:
            avg_vol = int(hist["Volume"].tail(30).mean())
            result["avg_volume"] = avg_vol
            result["avg_volume_fmt"] = _fmt_large(avg_vol).replace("$", "")

        if len(close) >= 30:
            returns = close.pct_change().tail(30).dropna()
            vol = float(returns.std() * (252 ** 0.5) * 100)
            result["volatility_30d"] = f"{vol:.1f}%"

    except Exception:
        pass
    return result


def get_fundamentals(ticker: str) -> dict:
    """Fetch key fundamental metrics for a ticker.

    Returns dict with ratios, company info, and market data.
    Detects asset type and returns appropriate data.
    """
    import yfinance as yf
    t = yf.Ticker(ticker)
    info = t.info or {}

    asset_type = _detect_asset_type(ticker)

    base = {
        "name": info.get("shortName", info.get("longName", ticker)),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "asset_type": asset_type,
        "market_cap": info.get("marketCap", 0),
        "market_cap_fmt": _fmt_large(info.get("marketCap", 0)),
        "pe_ratio": _safe_round(info.get("trailingPE")),
        "forward_pe": _safe_round(info.get("forwardPE")),
        "peg_ratio": _safe_round(info.get("pegRatio")),
        "pb_ratio": _safe_round(info.get("priceToBook")),
        "ps_ratio": _safe_round(info.get("priceToSalesTrailing12Months")),
        "eps": _safe_round(info.get("trailingEps")),
        "forward_eps": _safe_round(info.get("forwardEps")),
        "revenue": info.get("totalRevenue", 0),
        "revenue_fmt": _fmt_large(info.get("totalRevenue", 0)),
        "revenue_growth": _safe_round(info.get("revenueGrowth"), mult=100, suffix="%"),
        "profit_margin": _safe_round(info.get("profitMargins"), mult=100, suffix="%"),
        "operating_margin": _safe_round(info.get("operatingMargins"), mult=100, suffix="%"),
        "roe": _safe_round(info.get("returnOnEquity"), mult=100, suffix="%"),
        "debt_to_equity": _safe_round(info.get("debtToEquity")),
        "current_ratio": _safe_round(info.get("currentRatio")),
        "dividend_yield": _safe_round(info.get("dividendYield"), mult=100, suffix="%"),
        "dividend_rate": _safe_round(info.get("dividendRate")),
        "beta": _safe_round(info.get("beta")),
        "52w_high": _safe_round(info.get("fiftyTwoWeekHigh")),
        "52w_low": _safe_round(info.get("fiftyTwoWeekLow")),
        "avg_volume": info.get("averageVolume", 0),
        "target_mean": _safe_round(info.get("targetMeanPrice")),
        "target_high": _safe_round(info.get("targetHighPrice")),
        "target_low": _safe_round(info.get("targetLowPrice")),
        "recommendation": info.get("recommendationKey", "N/A"),
        "num_analysts": info.get("numberOfAnalystOpinions", 0),
    }

    # For non-stock assets, also fetch price performance
    if asset_type in ("commodity", "crypto", "forex", "index"):
        base["price_performance"] = get_price_performance(ticker)

    return base


def get_earnings_calendar(tickers: list[str]) -> list[dict]:
    """Get upcoming earnings dates for a list of tickers."""
    import yfinance as yf
    results = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is not None and not (isinstance(cal, pd.DataFrame) and cal.empty):
                if isinstance(cal, dict):
                    earnings_date = cal.get("Earnings Date", [])
                    if earnings_date:
                        date_val = earnings_date[0] if isinstance(earnings_date, list) else earnings_date
                        results.append({
                            "ticker": ticker,
                            "earnings_date": str(date_val),
                            "eps_estimate": cal.get("EPS Estimate"),
                            "revenue_estimate": cal.get("Revenue Estimate"),
                        })
                elif isinstance(cal, pd.DataFrame):
                    for col in cal.columns:
                        results.append({
                            "ticker": ticker,
                            "earnings_date": str(col),
                            "eps_estimate": cal.loc["EPS Estimate", col] if "EPS Estimate" in cal.index else None,
                            "revenue_estimate": cal.loc["Revenue Estimate", col] if "Revenue Estimate" in cal.index else None,
                        })
        except Exception:
            pass
    # Sort by date
    results.sort(key=lambda x: x.get("earnings_date", "9999"))
    return results


def get_financial_statements(ticker: str) -> dict:
    """Fetch income statement, balance sheet, cash flow (annual)."""
    import yfinance as yf
    t = yf.Ticker(ticker)
    result = {}

    try:
        inc = t.financials
        if inc is not None and not inc.empty:
            result["income_statement"] = inc.to_dict()
    except Exception:
        result["income_statement"] = {}

    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            result["balance_sheet"] = bs.to_dict()
    except Exception:
        result["balance_sheet"] = {}

    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            result["cash_flow"] = cf.to_dict()
    except Exception:
        result["cash_flow"] = {}

    return result


def get_analyst_recommendations(ticker: str) -> list[dict]:
    """Get recent analyst recommendations."""
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
        recs = t.recommendations
        if recs is not None and not recs.empty:
            recent = recs.tail(10)
            return recent.reset_index().to_dict("records")
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_round(val, digits: int = 2, mult: float = 1, suffix: str = "") -> str:
    """Safely round and format a value."""
    if val is None:
        return "N/A"
    try:
        result = round(float(val) * mult, digits)
        return f"{result}{suffix}"
    except (ValueError, TypeError):
        return "N/A"


def _fmt_large(num) -> str:
    """Format large numbers (market cap, revenue)."""
    if not num or num == 0:
        return "N/A"
    try:
        num = float(num)
    except (ValueError, TypeError):
        return "N/A"
    if num >= 1e12:
        return f"${num / 1e12:.2f}T"
    elif num >= 1e9:
        return f"${num / 1e9:.2f}B"
    elif num >= 1e6:
        return f"${num / 1e6:.2f}M"
    else:
        return f"${num:,.0f}"
