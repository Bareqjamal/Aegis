"""Strategy Builder — Natural language to backtestable trading strategies.

Parses English strategy descriptions into executable condition logic.
No LLM required for common patterns — uses template matching.

Example inputs:
- "Buy when RSI < 30 and MACD crosses above signal line"
- "Sell when price drops below SMA 200"
- "Buy when Bollinger Band lower touch and RSI < 40"
"""

import re
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Condition types
# ---------------------------------------------------------------------------

@dataclass
class Condition:
    indicator: str
    operator: str  # <, >, <=, >=, crosses_above, crosses_below
    value: float | str
    label: str = ""

    def evaluate(self, df: pd.DataFrame, i: int) -> bool:
        """Evaluate condition at row index i."""
        col = self._resolve_column(df)
        if col is None or i < 1:
            return False

        current = df[col].iloc[i]

        # Handle cross conditions (needs previous value)
        if self.operator == "crosses_above":
            ref = self._resolve_value(df, i)
            prev_val = df[col].iloc[i - 1]
            prev_ref = self._resolve_value(df, i - 1)
            return prev_val <= prev_ref and current > ref
        elif self.operator == "crosses_below":
            ref = self._resolve_value(df, i)
            prev_val = df[col].iloc[i - 1]
            prev_ref = self._resolve_value(df, i - 1)
            return prev_val >= prev_ref and current < ref

        ref = self._resolve_value(df, i)
        if self.operator == "<":
            return current < ref
        elif self.operator == ">":
            return current > ref
        elif self.operator == "<=":
            return current <= ref
        elif self.operator == ">=":
            return current >= ref
        return False

    def _resolve_column(self, df: pd.DataFrame) -> str | None:
        mapping = {
            "rsi": "RSI", "price": "Close", "close": "Close",
            "macd": "MACD", "macd_signal": "MACD_SIGNAL", "macd_hist": "MACD_HIST",
            "sma_20": "SMA_20", "sma_50": "SMA_50", "sma_200": "SMA_200",
            "ema_12": "EMA_12", "ema_26": "EMA_26",
            "bb_upper": "BB_UPPER", "bb_lower": "BB_LOWER",
            "volume": "Volume",
        }
        col = mapping.get(self.indicator.lower(), self.indicator)
        return col if col in df.columns else None

    def _resolve_value(self, df: pd.DataFrame, i: int) -> float:
        if isinstance(self.value, str):
            mapping = {
                "macd_signal": "MACD_SIGNAL", "signal_line": "MACD_SIGNAL",
                "sma_20": "SMA_20", "sma_50": "SMA_50", "sma_200": "SMA_200",
                "bb_upper": "BB_UPPER", "bb_lower": "BB_LOWER",
                "zero": 0,
            }
            col = mapping.get(self.value.lower(), self.value)
            if col in df.columns:
                return df[col].iloc[i]
            return 0
        return self.value


@dataclass
class Strategy:
    name: str
    buy_conditions: list[Condition] = field(default_factory=list)
    sell_conditions: list[Condition] = field(default_factory=list)
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "buy_conditions": [
                {"indicator": c.indicator, "operator": c.operator,
                 "value": c.value, "label": c.label}
                for c in self.buy_conditions
            ],
            "sell_conditions": [
                {"indicator": c.indicator, "operator": c.operator,
                 "value": c.value, "label": c.label}
                for c in self.sell_conditions
            ],
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
        }


# ---------------------------------------------------------------------------
# Natural language parser
# ---------------------------------------------------------------------------

# Pattern library
_PATTERNS = [
    # RSI conditions
    (r"rsi\s*(?:is\s*)?(?:below|under|<)\s*(\d+)", lambda m: Condition("RSI", "<", float(m.group(1)), f"RSI < {m.group(1)}")),
    (r"rsi\s*(?:is\s*)?(?:above|over|>)\s*(\d+)", lambda m: Condition("RSI", ">", float(m.group(1)), f"RSI > {m.group(1)}")),
    # MACD conditions
    (r"macd\s+cross(?:es)?\s+above\s+signal", lambda m: Condition("MACD", "crosses_above", "MACD_SIGNAL", "MACD crosses above signal")),
    (r"macd\s+cross(?:es)?\s+below\s+signal", lambda m: Condition("MACD", "crosses_below", "MACD_SIGNAL", "MACD crosses below signal")),
    (r"macd\s*(?:is\s*)?(?:above|over|>)\s*(?:zero|0)", lambda m: Condition("MACD", ">", 0, "MACD > 0")),
    (r"macd\s*(?:is\s*)?(?:below|under|<)\s*(?:zero|0)", lambda m: Condition("MACD", "<", 0, "MACD < 0")),
    # SMA conditions
    (r"price\s+(?:is\s+)?(?:above|over|>)\s+sma\s*(\d+)", lambda m: Condition("Close", ">", f"SMA_{m.group(1)}", f"Price > SMA {m.group(1)}")),
    (r"price\s+(?:is\s+)?(?:below|under|<)\s+sma\s*(\d+)", lambda m: Condition("Close", "<", f"SMA_{m.group(1)}", f"Price < SMA {m.group(1)}")),
    (r"price\s+cross(?:es)?\s+above\s+sma\s*(\d+)", lambda m: Condition("Close", "crosses_above", f"SMA_{m.group(1)}", f"Price crosses above SMA {m.group(1)}")),
    (r"price\s+cross(?:es)?\s+below\s+sma\s*(\d+)", lambda m: Condition("Close", "crosses_below", f"SMA_{m.group(1)}", f"Price crosses below SMA {m.group(1)}")),
    # Golden/Death cross
    (r"golden\s+cross", lambda m: Condition("SMA_50", "crosses_above", "SMA_200", "Golden Cross (SMA 50 > SMA 200)")),
    (r"death\s+cross", lambda m: Condition("SMA_50", "crosses_below", "SMA_200", "Death Cross (SMA 50 < SMA 200)")),
    # Bollinger Band
    (r"(?:price\s+)?(?:touches?|hits?|at)\s+(?:lower\s+)?bollinger", lambda m: Condition("Close", "<=", "BB_LOWER", "Price at lower Bollinger Band")),
    (r"(?:price\s+)?(?:touches?|hits?|at)\s+(?:upper\s+)?bollinger", lambda m: Condition("Close", ">=", "BB_UPPER", "Price at upper Bollinger Band")),
    # Price thresholds
    (r"price\s*(?:is\s*)?(?:above|over|>)\s*\$?([\d.]+)", lambda m: Condition("Close", ">", float(m.group(1)), f"Price > ${m.group(1)}")),
    (r"price\s*(?:is\s*)?(?:below|under|<)\s*\$?([\d.]+)", lambda m: Condition("Close", "<", float(m.group(1)), f"Price < ${m.group(1)}")),
]


def parse_strategy(text: str) -> Strategy:
    """Parse a natural language strategy description into a Strategy object.

    Supports "buy when ... and ..." / "sell when ... and ..." format.
    """
    text_lower = text.lower().strip()
    strategy = Strategy(name=text[:80])

    # Split into buy and sell parts
    buy_text = ""
    sell_text = ""

    buy_match = re.search(r"buy\s+when\s+(.+?)(?=sell\s+when|$)", text_lower, re.DOTALL)
    sell_match = re.search(r"sell\s+when\s+(.+?)(?=buy\s+when|$)", text_lower, re.DOTALL)

    if buy_match:
        buy_text = buy_match.group(1).strip()
    if sell_match:
        sell_text = sell_match.group(1).strip()

    # If no buy/sell structure, treat entire text as buy conditions
    if not buy_text and not sell_text:
        buy_text = text_lower

    # Parse conditions
    for condition_text, target_list in [(buy_text, strategy.buy_conditions),
                                         (sell_text, strategy.sell_conditions)]:
        # Split on "and" / ","
        parts = re.split(r"\s+and\s+|,\s*", condition_text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            for pattern, factory in _PATTERNS:
                match = re.search(pattern, part)
                if match:
                    target_list.append(factory(match))
                    break

    # Extract stop-loss / take-profit if mentioned
    sl_match = re.search(r"stop[- ]?loss\s*(?:at\s*)?(\d+(?:\.\d+)?)%?", text_lower)
    tp_match = re.search(r"(?:take[- ]?profit|target)\s*(?:at\s*)?(\d+(?:\.\d+)?)%?", text_lower)
    if sl_match:
        strategy.stop_loss_pct = float(sl_match.group(1))
    if tp_match:
        strategy.take_profit_pct = float(tp_match.group(1))

    return strategy


# ---------------------------------------------------------------------------
# Backtesting engine for parsed strategies
# ---------------------------------------------------------------------------

def backtest_strategy(
    strategy: Strategy,
    df: pd.DataFrame,
    initial_capital: float = 1000.0,
    position_size_pct: float = 100.0,
) -> dict:
    """Run a simple backtest of a parsed strategy on OHLCV data.

    Args:
        strategy: Parsed Strategy object.
        df: DataFrame with OHLCV + indicator columns.
        initial_capital: Starting balance.
        position_size_pct: Percentage of capital per trade.

    Returns:
        Dict with trades, equity curve, and metrics.
    """
    from chart_engine import add_indicators
    df = add_indicators(df.copy())

    capital = initial_capital
    position = None  # {entry_price, quantity, entry_idx}
    trades = []
    equity_curve = []

    for i in range(1, len(df)):
        price = df["Close"].iloc[i]
        current_equity = capital + (position["quantity"] * price if position else 0)
        equity_curve.append({"idx": i, "equity": current_equity, "date": str(df.index[i])})

        if position is None:
            # Check buy conditions
            if strategy.buy_conditions and all(c.evaluate(df, i) for c in strategy.buy_conditions):
                invest = capital * (position_size_pct / 100)
                quantity = invest / price
                position = {"entry_price": price, "quantity": quantity, "entry_idx": i}
                capital -= invest
        else:
            # Check sell conditions or stop-loss/take-profit
            entry = position["entry_price"]
            pnl_pct = (price - entry) / entry * 100

            should_sell = False
            exit_reason = ""

            if pnl_pct <= -strategy.stop_loss_pct:
                should_sell = True
                exit_reason = "stop_loss"
            elif pnl_pct >= strategy.take_profit_pct:
                should_sell = True
                exit_reason = "take_profit"
            elif strategy.sell_conditions and all(c.evaluate(df, i) for c in strategy.sell_conditions):
                should_sell = True
                exit_reason = "signal"

            if should_sell:
                pnl = (price - entry) * position["quantity"]
                capital += position["quantity"] * price
                trades.append({
                    "entry_price": entry,
                    "exit_price": price,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": exit_reason,
                    "entry_date": str(df.index[position["entry_idx"]]),
                    "exit_date": str(df.index[i]),
                })
                position = None

    # Close open position at end
    if position:
        final_price = df["Close"].iloc[-1]
        pnl = (final_price - position["entry_price"]) * position["quantity"]
        capital += position["quantity"] * final_price
        trades.append({
            "entry_price": position["entry_price"],
            "exit_price": final_price,
            "pnl": round(pnl, 2),
            "pnl_pct": round((final_price - position["entry_price"]) / position["entry_price"] * 100, 2),
            "exit_reason": "end_of_data",
            "entry_date": str(df.index[position["entry_idx"]]),
            "exit_date": str(df.index[-1]),
        })

    # Calculate metrics
    wins = [t for t in trades if t["pnl"] > 0]
    total_pnl = sum(t["pnl"] for t in trades)
    final_equity = capital
    total_return = (final_equity - initial_capital) / initial_capital * 100

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(trades) - len(wins),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return, 2),
        "final_equity": round(final_equity, 2),
    }


# ---------------------------------------------------------------------------
# Pre-built strategy templates
# ---------------------------------------------------------------------------

TEMPLATES = {
    "RSI Oversold Bounce": Strategy(
        name="RSI Oversold Bounce",
        buy_conditions=[Condition("RSI", "<", 30, "RSI < 30")],
        sell_conditions=[Condition("RSI", ">", 70, "RSI > 70")],
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
    ),
    "Golden Cross": Strategy(
        name="Golden Cross",
        buy_conditions=[Condition("SMA_50", "crosses_above", "SMA_200", "Golden Cross")],
        sell_conditions=[Condition("SMA_50", "crosses_below", "SMA_200", "Death Cross")],
        stop_loss_pct=8.0,
        take_profit_pct=15.0,
    ),
    "MACD Momentum": Strategy(
        name="MACD Momentum",
        buy_conditions=[
            Condition("MACD", "crosses_above", "MACD_SIGNAL", "MACD crosses above signal"),
            Condition("RSI", "<", 60, "RSI < 60"),
        ],
        sell_conditions=[
            Condition("MACD", "crosses_below", "MACD_SIGNAL", "MACD crosses below signal"),
        ],
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
    ),
    "Bollinger Bounce": Strategy(
        name="Bollinger Bounce",
        buy_conditions=[
            Condition("Close", "<=", "BB_LOWER", "Price at lower BB"),
            Condition("RSI", "<", 40, "RSI < 40"),
        ],
        sell_conditions=[
            Condition("Close", ">=", "BB_UPPER", "Price at upper BB"),
        ],
        stop_loss_pct=4.0,
        take_profit_pct=8.0,
    ),
    "Trend Following": Strategy(
        name="Trend Following",
        buy_conditions=[
            Condition("Close", ">", "SMA_50", "Price > SMA 50"),
            Condition("SMA_50", ">", "SMA_200", "SMA 50 > SMA 200"),
            Condition("RSI", "<", 70, "RSI < 70"),
        ],
        sell_conditions=[
            Condition("Close", "<", "SMA_50", "Price < SMA 50"),
        ],
        stop_loss_pct=7.0,
        take_profit_pct=15.0,
    ),
}
