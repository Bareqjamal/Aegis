"""Bitcoin trading strategies — signal generators.

Each strategy function takes a DataFrame with OHLCV columns and returns
a Series of signals: 1 (buy), -1 (sell), 0 (hold).
"""

import pandas as pd


def sma_crossover(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.Series:
    """Golden cross / death cross strategy.

    Buy when fast SMA crosses above slow SMA, sell on the reverse.
    """
    close = df["Close"].squeeze()
    sma_fast = close.rolling(fast).mean()
    sma_slow = close.rolling(slow).mean()
    signal = pd.Series(0, index=df.index)
    signal[sma_fast > sma_slow] = 1
    signal[sma_fast <= sma_slow] = -1
    return signal


def rsi_strategy(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> pd.Series:
    """RSI mean-reversion: buy when oversold, sell when overbought."""
    close = df["Close"].squeeze()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    signal = pd.Series(0, index=df.index)
    signal[rsi < oversold] = 1
    signal[rsi > overbought] = -1
    return signal


def macd_crossover(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_period: int = 9) -> pd.Series:
    """MACD line crossing signal line."""
    close = df["Close"].squeeze()
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    signal = pd.Series(0, index=df.index)
    signal[macd_line > signal_line] = 1
    signal[macd_line <= signal_line] = -1
    return signal


def bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.Series:
    """Bollinger Band mean reversion: buy at lower band, sell at upper band."""
    close = df["Close"].squeeze()
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std

    signal = pd.Series(0, index=df.index)
    signal[close <= lower] = 1
    signal[close >= upper] = -1
    return signal


ALL_STRATEGIES = {
    "SMA Crossover (50/200)": sma_crossover,
    "RSI (14)": rsi_strategy,
    "MACD (12/26/9)": macd_crossover,
    "Bollinger Bands (20/2)": bollinger_bands,
}
