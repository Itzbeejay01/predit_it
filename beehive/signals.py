"""Completed-candle, explainable rule-based market signals."""
from dataclasses import dataclass
import hashlib
import math
import pandas as pd


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str
    candle_time: str
    stop_distance: float
    reward_multiple: float
    reasons: tuple[str, ...]
    signal_id: str


def features(df):
    if len(df) < 60:
        raise ValueError("Need at least 60 historical candles.")
    x = df.copy()
    close = x["close"].astype(float)
    x["ema20"] = close.ewm(span=20, adjust=False).mean()
    x["ema50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = up / down.replace(0, float("nan"))
    x["rsi"] = (100 - 100 / (1 + rs)).fillna(50)
    x["macd"] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    prev = close.shift(1)
    tr = pd.concat([x["high"] - x["low"], (x["high"] - prev).abs(),
                    (x["low"] - prev).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    # shift(1) ensures the breakout level comes strictly from earlier bars.
    x["prior_high"] = x["high"].shift(1).rolling(10).max()
    x["prior_low"] = x["low"].shift(1).rolling(10).min()
    return x


def analyze(desired_symbol, m15, h1):
    """Return a selective setup or None. No forced trade on inconclusive data."""
    a, b = features(m15), features(h1)
    latest, direction = a.iloc[-1], b.iloc[-1]
    if not all(math.isfinite(float(latest[k])) for k in
               ("atr", "rsi", "macd", "macd_signal", "prior_high", "prior_low")):
        return None
    if float(latest["atr"]) <= 0:
        return None
    bullish = (
        direction.ema20 > direction.ema50
        and latest.close > latest.ema20
        and latest.close > latest.prior_high
        and 52 <= latest.rsi <= 72
        and latest.macd > latest.macd_signal
    )
    bearish = (
        direction.ema20 < direction.ema50
        and latest.close < latest.ema20
        and latest.close < latest.prior_low
        and 28 <= latest.rsi <= 48
        and latest.macd < latest.macd_signal
    )
    if bullish == bearish:
        return None
    side = "BUY" if bullish else "SELL"
    stamp = str(a.index[-1])
    token = hashlib.sha256(f"{desired_symbol}:{side}:{stamp}".encode()).hexdigest()[:24]
    return Signal(
        symbol=desired_symbol,
        side=side,
        candle_time=stamp,
        stop_distance=float(latest["atr"]) * 1.5,
        reward_multiple=2.0,
        reasons=("H1 EMA20/EMA50 trend alignment",
                 "M15 10-bar completed-candle breakout",
                 "M15 RSI and MACD momentum confirmation"),
        signal_id=token,
    )


def outlook(desired_symbol, m15, h1):
    a, b = features(m15), features(h1)
    last, trend = a.iloc[-1], b.iloc[-1]
    bias = "BULLISH" if trend.ema20 > trend.ema50 else (
        "BEARISH" if trend.ema20 < trend.ema50 else "NEUTRAL")
    return {
        "symbol": desired_symbol,
        "bias": bias,
        "last_close": float(last.close),
        "rsi": float(last.rsi),
        "atr": float(last.atr),
        "as_of": str(a.index[-1]),
        "note": "Market context, not a trade recommendation.",
    }
