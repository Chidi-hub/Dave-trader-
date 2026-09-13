"""
Simple, transparent entry strategy: RSI + moving-average trend filter.

This is deliberately basic and easy to read/modify — it is a starting
point, not a proven money-maker. Backtest and paper-trade before
trusting it with real funds.

Signal logic:
  - Compute RSI(14). Oversold (<30) suggests the coin may be due for
    a bounce.
  - Compute fast/slow moving averages. Only take the "buy the dip"
    signal if the longer-term trend (slow MA) is still pointed up —
    this avoids buying dips in coins that are just falling steadily.
"""

from dataclasses import dataclass

import config


@dataclass
class Signal:
    symbol: str
    action: str      # "buy" or "hold"
    reason: str
    price: float


def _rsi(closes, period):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        change = closes[-i] - closes[-i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _sma(closes, period):
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def evaluate(symbol: str, candles: list) -> Signal:
    closes = [c["close"] for c in candles]
    if len(closes) < max(config.MA_SLOW, config.RSI_PERIOD + 1):
        return Signal(symbol, "hold", "not enough data yet", closes[-1] if closes else 0)

    price = closes[-1]
    rsi = _rsi(closes, config.RSI_PERIOD)
    ma_fast = _sma(closes, config.MA_FAST)
    ma_slow_now = _sma(closes, config.MA_SLOW)
    ma_slow_prev = _sma(closes[:-1], config.MA_SLOW)

    slow_trend_up = ma_slow_prev is not None and ma_slow_now >= ma_slow_prev

    if rsi is not None and rsi < config.RSI_OVERSOLD and slow_trend_up:
        return Signal(
            symbol, "buy",
            f"RSI={rsi:.1f} (oversold) with slow MA trending up",
            price,
        )

    rsi_display = f"{rsi:.1f}" if rsi is not None else "n/a"
    return Signal(symbol, "hold", f"RSI={rsi_display}, no signal", price)
