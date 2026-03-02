"""Portfolio Allocation Optimizer — Mean-Variance, Efficient Frontier, Kelly.

Provides:
- Mean-variance portfolio optimization (Markowitz)
- Minimum variance portfolio
- Equal-weight benchmark
- Kelly Criterion optimal allocation
- Efficient frontier computation + Plotly charts
- Allocation bar charts + pie charts

Uses scipy.optimize for constrained optimization.
All data fetched via yfinance with timeout protection.
"""

import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

try:
    from scipy.optimize import minimize
except ImportError:
    minimize = None  # graceful degradation

import plotly.graph_objects as go


DATA_DIR = Path(__file__).resolve().parent / "data"
WATCHLIST_FILE = DATA_DIR / "user_watchlist.json"

TRADING_DAYS = 252  # annualization factor


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_watchlist() -> dict:
    """Load user watchlist assets."""
    if WATCHLIST_FILE.exists():
        try:
            return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def fetch_returns(tickers: list[str], period: str = "6mo", timeout: int = 20) -> pd.DataFrame | None:
    """Fetch daily returns for a list of tickers with timeout protection.

    Returns DataFrame with columns=ticker symbols, rows=dates, values=daily returns.
    Returns None if fetch fails.
    """
    if not tickers:
        return None

    ticker_str = " ".join(tickers)

    def _download():
        return yf.download(ticker_str, period=period, progress=False, auto_adjust=True)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_download)
            df = future.result(timeout=timeout)
    except (FuturesTimeout, Exception):
        return None

    if df is None or df.empty:
        return None

    # Handle MultiIndex columns from batch download
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"]
    else:
        close = df[["Close"]] if "Close" in df.columns else df
        if len(tickers) == 1:
            close.columns = [tickers[0]]

    # Daily returns
    returns = close.pct_change().dropna()
    if returns.empty:
        return None

    return returns


# ---------------------------------------------------------------------------
# Optimization engine
# ---------------------------------------------------------------------------

class PortfolioOptimizer:
    """Mean-Variance Portfolio Optimizer.

    Usage:
        opt = PortfolioOptimizer(asset_names, returns_df)
        result = opt.optimize(target_return=None)  # max Sharpe
        result = opt.min_variance()
        result = opt.equal_weight()
        frontier = opt.efficient_frontier(n_points=50)
    """

    def __init__(self, names: list[str], returns: pd.DataFrame, risk_free_rate: float = 0.04):
        """Initialize with asset names and returns DataFrame.

        Args:
            names: Human-readable asset names (same order as returns columns)
            returns: DataFrame of daily returns (columns = tickers)
            risk_free_rate: Annual risk-free rate (default 4% ~ T-bill)
        """
        self.names = names
        self.returns = returns
        self.n = len(names)
        self.risk_free_rate = risk_free_rate

        # Compute annualized stats
        self.mean_returns = returns.mean() * TRADING_DAYS
        self.cov_matrix = returns.cov() * TRADING_DAYS
        self.daily_rf = risk_free_rate / TRADING_DAYS

    def _portfolio_stats(self, weights: np.ndarray) -> tuple[float, float, float]:
        """Calculate portfolio return, volatility, and Sharpe ratio.

        Returns: (annual_return, annual_vol, sharpe_ratio)
        """
        port_return = np.dot(weights, self.mean_returns.values)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix.values, weights)))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        return port_return, port_vol, sharpe

    def optimize(self, target_return: float | None = None) -> dict:
        """Find optimal portfolio weights.

        If target_return is None: maximize Sharpe ratio (tangency portfolio).
        If target_return given: minimize volatility for that return level.

        Returns dict with weights, return, volatility, sharpe, allocations.
        """
        if minimize is None:
            return self.equal_weight()  # fallback if scipy missing

        n = self.n
        bounds = tuple((0.0, 1.0) for _ in range(n))  # long-only
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        if target_return is not None:
            # Minimize volatility for target return
            constraints.append({
                "type": "eq",
                "fun": lambda w: np.dot(w, self.mean_returns.values) - target_return,
            })

            def objective(w):
                return np.sqrt(np.dot(w.T, np.dot(self.cov_matrix.values, w)))
        else:
            # Maximize Sharpe (minimize negative Sharpe)
            def objective(w):
                ret = np.dot(w, self.mean_returns.values)
                vol = np.sqrt(np.dot(w.T, np.dot(self.cov_matrix.values, w)))
                if vol == 0:
                    return 1e6
                return -(ret - self.risk_free_rate) / vol

        # Initial guess: equal weight
        w0 = np.array([1.0 / n] * n)

        try:
            result = minimize(objective, w0, method="SLSQP", bounds=bounds,
                              constraints=constraints, options={"maxiter": 1000, "ftol": 1e-10})
            weights = result.x
        except Exception:
            weights = w0

        # Clean up tiny weights
        weights = np.maximum(weights, 0)
        weights /= weights.sum()

        ret, vol, sharpe = self._portfolio_stats(weights)

        return {
            "method": "max_sharpe" if target_return is None else "target_return",
            "weights": weights.tolist(),
            "allocations": {name: round(w * 100, 2) for name, w in zip(self.names, weights) if w > 0.001},
            "annual_return": round(ret * 100, 2),
            "annual_volatility": round(vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "risk_free_rate": self.risk_free_rate,
        }

    def min_variance(self) -> dict:
        """Find the minimum variance portfolio."""
        if minimize is None:
            return self.equal_weight()

        n = self.n
        bounds = tuple((0.0, 1.0) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        def objective(w):
            return np.dot(w.T, np.dot(self.cov_matrix.values, w))

        w0 = np.array([1.0 / n] * n)

        try:
            result = minimize(objective, w0, method="SLSQP", bounds=bounds,
                              constraints=constraints, options={"maxiter": 1000})
            weights = result.x
        except Exception:
            weights = w0

        weights = np.maximum(weights, 0)
        weights /= weights.sum()

        ret, vol, sharpe = self._portfolio_stats(weights)

        return {
            "method": "min_variance",
            "weights": weights.tolist(),
            "allocations": {name: round(w * 100, 2) for name, w in zip(self.names, weights) if w > 0.001},
            "annual_return": round(ret * 100, 2),
            "annual_volatility": round(vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "risk_free_rate": self.risk_free_rate,
        }

    def equal_weight(self) -> dict:
        """Equal-weight benchmark portfolio."""
        weights = np.array([1.0 / self.n] * self.n)
        ret, vol, sharpe = self._portfolio_stats(weights)

        return {
            "method": "equal_weight",
            "weights": weights.tolist(),
            "allocations": {name: round(100 / self.n, 2) for name in self.names},
            "annual_return": round(ret * 100, 2),
            "annual_volatility": round(vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "risk_free_rate": self.risk_free_rate,
        }

    def kelly_allocation(self) -> dict:
        """Kelly Criterion allocation (half-Kelly for safety).

        Uses the formula: f* = (mu - rf) / sigma^2  per asset,
        then normalizes and caps at 100%.
        """
        weights = []
        for i in range(self.n):
            mu = self.mean_returns.iloc[i]
            sigma_sq = self.cov_matrix.iloc[i, i]
            if sigma_sq > 0:
                kelly_f = (mu - self.risk_free_rate) / sigma_sq
                half_kelly = max(kelly_f * 0.5, 0)  # half-Kelly, long-only
            else:
                half_kelly = 0
            weights.append(half_kelly)

        weights = np.array(weights)
        total = weights.sum()
        if total > 0:
            weights = weights / total
        else:
            weights = np.array([1.0 / self.n] * self.n)

        ret, vol, sharpe = self._portfolio_stats(weights)

        return {
            "method": "half_kelly",
            "weights": weights.tolist(),
            "allocations": {name: round(w * 100, 2) for name, w in zip(self.names, weights) if w > 0.001},
            "annual_return": round(ret * 100, 2),
            "annual_volatility": round(vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "risk_free_rate": self.risk_free_rate,
        }

    def efficient_frontier(self, n_points: int = 50) -> list[dict]:
        """Compute the efficient frontier.

        Returns list of {return, volatility, sharpe, weights} for n_points
        along the frontier from min-variance to max-return.
        """
        if minimize is None:
            return []

        # Find min and max return bounds
        min_var = self.min_variance()
        min_ret = min_var["annual_return"] / 100
        max_ret = float(self.mean_returns.max())

        if min_ret >= max_ret:
            return []

        frontier = []
        target_returns = np.linspace(min_ret, max_ret, n_points)

        for tr in target_returns:
            result = self.optimize(target_return=tr)
            frontier.append({
                "return": result["annual_return"],
                "volatility": result["annual_volatility"],
                "sharpe": result["sharpe_ratio"],
                "weights": result["weights"],
            })

        return frontier


# ---------------------------------------------------------------------------
# Plotly chart builders
# ---------------------------------------------------------------------------

def efficient_frontier_chart(frontier: list[dict], portfolios: dict | None = None,
                             height: int = 500) -> go.Figure:
    """Plot the efficient frontier with optional named portfolios marked.

    Args:
        frontier: List of {return, volatility, sharpe} from efficient_frontier()
        portfolios: Dict of {name: {annual_return, annual_volatility, sharpe_ratio}}
        height: Chart height
    """
    if not frontier:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient data for efficient frontier",
                           showarrow=False, font=dict(size=16, color="#8b949e"))
        fig.update_layout(template="plotly_dark", height=height,
                          paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        return fig

    vols = [p["volatility"] for p in frontier]
    rets = [p["return"] for p in frontier]
    sharpes = [p["sharpe"] for p in frontier]

    fig = go.Figure()

    # Efficient frontier curve
    fig.add_trace(go.Scatter(
        x=vols, y=rets,
        mode="lines",
        name="Efficient Frontier",
        line=dict(color="#58a6ff", width=3),
        hovertemplate="Vol: %{x:.1f}%<br>Return: %{y:.1f}%<br>Sharpe: %{customdata:.2f}<extra></extra>",
        customdata=sharpes,
    ))

    # Mark special portfolios
    if portfolios:
        colors = {"Max Sharpe": "#3fb950", "Min Variance": "#d29922",
                  "Equal Weight": "#6e7681", "Half-Kelly": "#a371f7"}
        symbols = {"Max Sharpe": "star", "Min Variance": "diamond",
                   "Equal Weight": "square", "Half-Kelly": "hexagon"}

        for pname, pdata in portfolios.items():
            fig.add_trace(go.Scatter(
                x=[pdata["annual_volatility"]],
                y=[pdata["annual_return"]],
                mode="markers+text",
                name=pname,
                marker=dict(
                    color=colors.get(pname, "#e6edf3"),
                    size=14,
                    symbol=symbols.get(pname, "circle"),
                    line=dict(width=2, color="#0d1117"),
                ),
                text=[pname],
                textposition="top center",
                textfont=dict(size=10, color=colors.get(pname, "#e6edf3")),
                hovertemplate=(
                    f"<b>{pname}</b><br>"
                    f"Return: {pdata['annual_return']:.1f}%<br>"
                    f"Vol: {pdata['annual_volatility']:.1f}%<br>"
                    f"Sharpe: {pdata['sharpe_ratio']:.3f}<extra></extra>"
                ),
            ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=height,
        title=dict(text="Efficient Frontier", font=dict(size=16, color="#e6edf3")),
        xaxis=dict(title="Annual Volatility (%)", gridcolor="rgba(48,54,61,0.4)"),
        yaxis=dict(title="Annual Return (%)", gridcolor="rgba(48,54,61,0.4)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=50, r=20, t=50, b=50),
    )

    return fig


def allocation_bar_chart(allocations: dict, title: str = "Portfolio Allocation",
                         height: int = 350) -> go.Figure:
    """Horizontal bar chart of portfolio allocation percentages."""
    if not allocations:
        fig = go.Figure()
        fig.add_annotation(text="No allocation data", showarrow=False,
                           font=dict(size=14, color="#8b949e"))
        fig.update_layout(template="plotly_dark", height=height,
                          paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        return fig

    # Sort by allocation weight
    sorted_alloc = sorted(allocations.items(), key=lambda x: x[1], reverse=True)
    names = [a[0] for a in sorted_alloc]
    weights = [a[1] for a in sorted_alloc]

    # Color gradient from green (top) to muted (bottom)
    n = len(names)
    colors = []
    for i in range(n):
        ratio = 1 - (i / max(n - 1, 1))
        r = int(63 + (110 - 63) * (1 - ratio))
        g = int(185 + (117 - 185) * (1 - ratio))
        b = int(80 + (125 - 80) * (1 - ratio))
        colors.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=weights,
        y=names,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{w:.1f}%" for w in weights],
        textposition="auto",
        textfont=dict(color="#e6edf3", size=12, family="JetBrains Mono"),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=height,
        title=dict(text=title, font=dict(size=14, color="#e6edf3")),
        xaxis=dict(title="Allocation (%)", gridcolor="rgba(48,54,61,0.4)", range=[0, 100]),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=100, r=20, t=50, b=40),
        showlegend=False,
    )

    return fig


def allocation_pie_chart(allocations: dict, title: str = "Allocation",
                         height: int = 350) -> go.Figure:
    """Donut chart of portfolio allocation."""
    if not allocations:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", height=height,
                          paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        return fig

    sorted_alloc = sorted(allocations.items(), key=lambda x: x[1], reverse=True)
    names = [a[0] for a in sorted_alloc]
    weights = [a[1] for a in sorted_alloc]

    colors = ["#3fb950", "#58a6ff", "#d29922", "#a371f7", "#f85149",
              "#20c997", "#fd7e14", "#6e7681", "#e6edf3", "#484f58",
              "#1f6feb", "#da3633"]

    fig = go.Figure(go.Pie(
        labels=names,
        values=weights,
        hole=0.45,
        marker=dict(colors=colors[:len(names)], line=dict(color="#0d1117", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, family="JetBrains Mono"),
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=height,
        title=dict(text=title, font=dict(size=14, color="#e6edf3")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


# ---------------------------------------------------------------------------
# Convenience function: run full optimization from watchlist
# ---------------------------------------------------------------------------

def optimize_from_watchlist(period: str = "6mo") -> dict | None:
    """Run full optimization pipeline on user watchlist assets.

    Returns dict with:
        - max_sharpe, min_variance, equal_weight, half_kelly: portfolio results
        - frontier: efficient frontier data
        - asset_names, tickers: used for the optimization
        - returns: the returns DataFrame (for further analysis)

    Returns None if data fetch fails.
    """
    wl = _load_watchlist()
    if not wl:
        return None

    names = []
    tickers = []
    for name, data in wl.items():
        if data.get("enabled", True):
            ticker = data.get("ticker", "")
            if ticker:
                names.append(name)
                tickers.append(ticker)

    if len(tickers) < 2:
        return None

    returns = fetch_returns(tickers, period=period)
    if returns is None or returns.shape[1] < 2:
        return None

    # Map ticker columns back to names for any that succeeded
    valid_names = []
    valid_tickers = []
    for name, ticker in zip(names, tickers):
        if ticker in returns.columns:
            valid_names.append(name)
            valid_tickers.append(ticker)

    if len(valid_names) < 2:
        return None

    # Subset returns to valid tickers
    returns = returns[valid_tickers]

    optimizer = PortfolioOptimizer(valid_names, returns)

    max_sharpe = optimizer.optimize()
    min_var = optimizer.min_variance()
    equal_wt = optimizer.equal_weight()
    kelly = optimizer.kelly_allocation()
    frontier = optimizer.efficient_frontier(n_points=40)

    return {
        "max_sharpe": max_sharpe,
        "min_variance": min_var,
        "equal_weight": equal_wt,
        "half_kelly": kelly,
        "frontier": frontier,
        "asset_names": valid_names,
        "tickers": valid_tickers,
        "returns": returns,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
