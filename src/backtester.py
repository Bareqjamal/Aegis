"""Backtester — run strategies against historical BTC data and compute metrics."""

from pathlib import Path

import numpy as np
import pandas as pd

from strategies import ALL_STRATEGIES

DATA_FILE = Path(__file__).resolve().parent / "data" / "btc_usd_daily.csv"


def load_data() -> pd.DataFrame:
    # yfinance writes a 3-row header (Price, Ticker, Date). Skip the Ticker row.
    df = pd.read_csv(DATA_FILE, header=0, skiprows=[1, 2], index_col=0, parse_dates=True)
    df = df.apply(pd.to_numeric, errors="coerce")
    return df


def backtest(df: pd.DataFrame, signals: pd.Series) -> dict:
    """Simulate a long/short/flat strategy based on signals.

    Signal values:
        1  -> long  (BUY):  profit when price rises
       -1  -> short (SELL): profit when price falls
        0  -> flat  (HOLD): no position

    Returns a dict of performance metrics including per-side breakdowns.
    """
    close = df["Close"].squeeze()
    daily_returns = close.pct_change()

    # Position: +1 (long), -1 (short), 0 (flat). Shift to avoid lookahead.
    position = signals.clip(-1, 1).shift(1).fillna(0)

    # Long component: +1 when long, 0 otherwise
    long_position = (position == 1).astype(int)
    # Short component: +1 when short, 0 otherwise
    short_position = (position == -1).astype(int)

    # Strategy returns: long profits from up moves, short profits from down moves
    # For short: multiply daily_returns by -1 (price drop = profit)
    long_returns = long_position * daily_returns
    short_returns = short_position * (-daily_returns)
    strategy_returns = long_returns + short_returns

    cumulative = (1 + strategy_returns).cumprod()
    buy_and_hold = (1 + daily_returns).cumprod()

    total_return = cumulative.iloc[-1] - 1 if len(cumulative) > 0 else 0
    bnh_return = buy_and_hold.iloc[-1] - 1 if len(buy_and_hold) > 0 else 0

    # Sharpe ratio (annualized, 365 trading days for crypto)
    mean_ret = strategy_returns.mean()
    std_ret = strategy_returns.std()
    sharpe = (mean_ret / std_ret) * np.sqrt(365) if std_ret > 0 else 0

    # Max drawdown
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    max_drawdown = drawdown.min()

    # Overall win rate
    active_days = strategy_returns[strategy_returns != 0]
    win_rate = (active_days > 0).sum() / len(active_days) if len(active_days) > 0 else 0

    # Per-side metrics
    long_active = long_returns[long_returns != 0]
    long_win_rate = (long_active > 0).sum() / len(long_active) if len(long_active) > 0 else 0
    long_days = int(long_position.sum())

    short_active = short_returns[short_returns != 0]
    short_win_rate = (short_active > 0).sum() / len(short_active) if len(short_active) > 0 else 0
    short_days = int(short_position.sum())

    return {
        "total_return": f"{total_return:.2%}",
        "buy_hold_return": f"{bnh_return:.2%}",
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": f"{max_drawdown:.2%}",
        "win_rate": f"{win_rate:.2%}",
        "num_trading_days": long_days + short_days,
        "long_days": long_days,
        "short_days": short_days,
        "long_win_rate": f"{long_win_rate:.2%}",
        "short_win_rate": f"{short_win_rate:.2%}",
        "cumulative": cumulative,
        "buy_and_hold": buy_and_hold,
    }


def run_all() -> dict[str, dict]:
    """Run all strategies and return results keyed by strategy name."""
    df = load_data()
    results = {}
    for name, strategy_fn in ALL_STRATEGIES.items():
        signals = strategy_fn(df)
        results[name] = backtest(df, signals)
    return results


if __name__ == "__main__":
    results = run_all()
    print(
        f"\n{'Strategy':<30} {'Return':>10} {'B&H':>10} {'Sharpe':>8} "
        f"{'MaxDD':>10} {'WinRate':>8} {'LongDays':>9} {'ShortDays':>10} "
        f"{'LongWR':>8} {'ShortWR':>8}"
    )
    print("-" * 115)
    for name, r in results.items():
        print(
            f"{name:<30} {r['total_return']:>10} {r['buy_hold_return']:>10} "
            f"{r['sharpe_ratio']:>8} {r['max_drawdown']:>10} {r['win_rate']:>8} "
            f"{r['long_days']:>9} {r['short_days']:>10} "
            f"{r['long_win_rate']:>8} {r['short_win_rate']:>8}"
        )
