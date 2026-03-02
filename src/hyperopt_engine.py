"""Hyperopt Engine — Optimize strategy parameters for maximum performance.

Uses Optuna to search indicator parameter space and find optimal
stop-loss, take-profit, and indicator thresholds.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,11,18,0.95)",
    font={"color": "#c9d1d9", "family": "Inter, sans-serif"},
)


# ---------------------------------------------------------------------------
# Objective functions
# ---------------------------------------------------------------------------

def _backtest_with_params(df: pd.DataFrame, params: dict, initial_capital: float = 1000.0) -> dict:
    """Run a parameterized backtest. Returns performance metrics."""
    from chart_engine import add_indicators
    df = add_indicators(df.copy())

    rsi_buy = params.get("rsi_buy", 30)
    rsi_sell = params.get("rsi_sell", 70)
    sma_fast = params.get("sma_fast", 20)
    sma_slow = params.get("sma_slow", 50)
    stop_loss_pct = params.get("stop_loss_pct", 5.0)
    take_profit_pct = params.get("take_profit_pct", 10.0)

    # Compute custom SMAs if different from default
    c = df["Close"]
    df["SMA_FAST"] = c.rolling(sma_fast).mean()
    df["SMA_SLOW"] = c.rolling(sma_slow).mean()

    capital = initial_capital
    position = None
    trades = []
    equity = []

    for i in range(1, len(df)):
        price = df["Close"].iloc[i]
        eq = capital + (position["qty"] * price if position else 0)
        equity.append(eq)

        if position is None:
            rsi = df["RSI"].iloc[i] if "RSI" in df.columns and pd.notna(df["RSI"].iloc[i]) else 50
            sma_f = df["SMA_FAST"].iloc[i]
            sma_s = df["SMA_SLOW"].iloc[i]

            if pd.notna(sma_f) and pd.notna(sma_s):
                if rsi < rsi_buy and sma_f > sma_s:
                    qty = capital / price
                    position = {"entry": price, "qty": qty}
                    capital = 0
        else:
            pnl_pct = (price - position["entry"]) / position["entry"] * 100
            rsi = df["RSI"].iloc[i] if "RSI" in df.columns and pd.notna(df["RSI"].iloc[i]) else 50

            if pnl_pct <= -stop_loss_pct or pnl_pct >= take_profit_pct or rsi > rsi_sell:
                pnl = (price - position["entry"]) * position["qty"]
                capital = position["qty"] * price
                trades.append({"pnl": pnl, "pnl_pct": pnl_pct})
                position = None

    # Close open
    if position:
        final = df["Close"].iloc[-1]
        pnl = (final - position["entry"]) * position["qty"]
        capital = position["qty"] * final
        trades.append({"pnl": pnl, "pnl_pct": (final - position["entry"]) / position["entry"] * 100})

    final_equity = capital
    total_return = (final_equity - initial_capital) / initial_capital * 100

    # Sharpe approximation from equity
    if len(equity) > 2:
        returns = np.diff(equity) / np.array(equity[:-1])
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
    else:
        sharpe = 0

    wins = sum(1 for t in trades if t["pnl"] > 0)
    return {
        "total_return": round(total_return, 2),
        "sharpe": round(sharpe, 2),
        "total_trades": len(trades),
        "win_rate": round(wins / len(trades) * 100, 1) if trades else 0,
        "final_equity": round(final_equity, 2),
    }


# ---------------------------------------------------------------------------
# Optuna optimization
# ---------------------------------------------------------------------------

def optimize_strategy(
    df: pd.DataFrame,
    n_trials: int = 50,
    initial_capital: float = 1000.0,
    objective_metric: str = "sharpe",
) -> dict:
    """Run hyperparameter optimization using Optuna.

    Args:
        df: OHLCV DataFrame.
        n_trials: Number of optimization trials.
        initial_capital: Starting capital.
        objective_metric: "sharpe" or "total_return".

    Returns:
        Dict with best_params, best_value, all_trials.
    """
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        params = {
            "rsi_buy": trial.suggest_int("rsi_buy", 15, 45),
            "rsi_sell": trial.suggest_int("rsi_sell", 55, 85),
            "sma_fast": trial.suggest_int("sma_fast", 5, 30),
            "sma_slow": trial.suggest_int("sma_slow", 30, 200),
            "stop_loss_pct": trial.suggest_float("stop_loss_pct", 1.0, 15.0, step=0.5),
            "take_profit_pct": trial.suggest_float("take_profit_pct", 2.0, 30.0, step=0.5),
        }
        # Ensure fast < slow
        if params["sma_fast"] >= params["sma_slow"]:
            return float("-inf")

        result = _backtest_with_params(df, params, initial_capital)
        return result.get(objective_metric, 0)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    # Collect trial results
    trials = []
    for t in study.trials:
        if t.value is not None:
            trials.append({
                "number": t.number,
                "value": round(t.value, 4),
                "params": t.params,
            })

    best = study.best_trial
    best_result = _backtest_with_params(df, best.params, initial_capital)

    return {
        "best_params": best.params,
        "best_value": round(best.value, 4),
        "best_result": best_result,
        "n_trials": n_trials,
        "all_trials": sorted(trials, key=lambda t: t["value"], reverse=True)[:20],
    }


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_optimization_results(opt_result: dict, height: int = 300) -> go.Figure:
    """Plot optimization trial results."""
    trials = opt_result.get("all_trials", [])
    if not trials:
        return go.Figure()

    numbers = [t["number"] for t in trials]
    values = [t["value"] for t in trials]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(values))), y=sorted(values, reverse=True),
        mode="lines+markers",
        line={"color": "#58a6ff", "width": 2},
        marker={"size": 4, "color": "#58a6ff"},
        name="Trial Performance",
    ))
    fig.add_hline(y=opt_result["best_value"], line_dash="dash", line_color="#3fb950",
                  annotation_text=f"Best: {opt_result['best_value']}")
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=30, b=30, l=50, r=20),
                      xaxis_title="Trial Rank", yaxis_title="Objective Value")
    fig.update_xaxes(gridcolor="rgba(48,54,61,0.3)")
    fig.update_yaxes(gridcolor="rgba(48,54,61,0.3)")
    return fig


def plot_param_importance(opt_result: dict, height: int = 250) -> go.Figure:
    """Plot parameter values of top trials as a parallel coordinates chart."""
    trials = opt_result.get("all_trials", [])[:10]
    if not trials or not trials[0].get("params"):
        return go.Figure()

    param_names = list(trials[0]["params"].keys())
    dimensions = []
    for pname in param_names:
        vals = [t["params"].get(pname, 0) for t in trials]
        dimensions.append(dict(
            label=pname.replace("_", " ").title(),
            values=vals,
            range=[min(vals) * 0.9, max(vals) * 1.1] if vals else [0, 1],
        ))

    fig = go.Figure(go.Parcoords(
        line=dict(
            color=[t["value"] for t in trials],
            colorscale=[[0, "#f85149"], [0.5, "#ffa657"], [1, "#3fb950"]],
            showscale=True,
            colorbar=dict(title="Score"),
        ),
        dimensions=dimensions,
    ))
    fig.update_layout(**DARK_LAYOUT, height=height, margin=dict(t=30, b=30, l=80, r=80))
    return fig
