"""Conservative candle-level research backtest. Never used for order submission.

Uses MT5 historical BID OHLC and historical spread points to approximate ASK.
Assumptions: entry at next-bar open, SL first if SL and TP both touched,
gap-through stop fills at worse open, timeout after at most 16 bars.
NOT a tick simulation: commissions, swaps, latency and slippage are omitted.
"""
from dataclasses import asdict, dataclass
import math
import pandas as pd

from .signals import analyze


@dataclass(frozen=True)
class SimTrade:
    symbol: str
    signal_time: str
    entry_time: str
    exit_time: str
    side: str
    entry: float
    stop: float
    target: float
    exit_price: float
    result_r: float
    exit_reason: str


def _bid_ask_bar(bar, point):
    """Return bid OHLC and inferred ask OHLC from historical MT5 spread."""
    spread_pts = getattr(bar, "spread", None)
    if spread_pts is None or pd.isna(spread_pts) or float(spread_pts) <= 0:
        raise ValueError("Historical spread unavailable; refusing a zero-cost backtest.")
    spread = float(spread_pts) * point
    if spread <= 0 or not math.isfinite(spread):
        raise ValueError("Invalid historical spread.")
    return (
        float(bar.open), float(bar.high), float(bar.low), float(bar.close),
        float(bar.open)+spread, float(bar.high)+spread,
        float(bar.low)+spread, float(bar.close)+spread,
    )


def _fill_exit(side, entry, stop, target, future, point):
    """Conservative first-hit model; accepts next entry bar through max holding."""
    for time, bar in future.iterrows():
        bid_open, bid_high, bid_low, bid_close, ask_open, ask_high, ask_low, ask_close = _bid_ask_bar(bar, point)
        if side == "BUY":
            if bid_low <= stop:  # stop wins the ambiguous same-bar collision
                return str(time), min(stop, bid_open), "STOP"
            if bid_high >= target:
                return str(time), target, "TARGET"
        else:
            if ask_high >= stop:
                return str(time), max(stop, ask_open), "STOP"
            if ask_low <= target:
                return str(time), target, "TARGET"
    time = future.index[-1]
    last = _bid_ask_bar(future.iloc[-1], point)
    return str(time), last[3] if side == "BUY" else last[7], "TIMEOUT"


def simulate(m15, h1, symbol, point, risk_fraction=0.005, max_holding_bars=16):
    """Return transparent experimental metrics and individual simulated trades.

    Research equity starts at 1.0, compounding exactly risk_fraction of that
    balance for each observed realised R. No same-symbol overlap.
    """
    if point <= 0 or risk_fraction <= 0 or risk_fraction > 0.005:
        raise ValueError("Invalid tick size or risk fraction.")
    if max_holding_bars < 1 or max_holding_bars > 96:
        raise ValueError("Invalid holding period.")
    if len(m15) < 260 or len(h1) < 65:
        raise ValueError("Need at least 260 M15 and 65 H1 completed candles.")
    m15, h1 = m15.sort_index(), h1.sort_index()
    if "spread" not in m15.columns or (m15["spread"] <= 0).any():
        raise ValueError("Backtest requires nonzero historical spread on every input candle.")
    trades = []
    i = 220
    while i < len(m15)-max_holding_bars-1:
        signal_time = m15.index[i]
        # A candle is usable only AFTER its close, not at its opening timestamp.
        h1_cutoff = signal_time + pd.Timedelta(minutes=15) - pd.Timedelta(hours=1)
        valid_h1 = h1.loc[:h1_cutoff]
        if len(valid_h1) < 60:
            i += 1
            continue
        candidate = analyze(symbol, m15.iloc[:i+1], valid_h1)
        if candidate is None:
            i += 1
            continue
        next_bar = m15.iloc[i+1]
        bid_open, _, _, _, ask_open, _, _, _ = _bid_ask_bar(next_bar, point)
        entry = ask_open if candidate.side == "BUY" else bid_open
        distance = candidate.stop_distance
        if not math.isfinite(distance) or distance <= 0:
            i += 1
            continue
        stop = entry - distance if candidate.side == "BUY" else entry + distance
        target = entry + distance*candidate.reward_multiple if candidate.side == "BUY" else entry - distance*candidate.reward_multiple
        future = m15.iloc[i+1:i+1+max_holding_bars]
        exit_time, exit_price, reason = _fill_exit(candidate.side, entry, stop, target, future, point)
        result_r = ((exit_price-entry)/distance if candidate.side == "BUY"
                    else (entry-exit_price)/distance)
        if not math.isfinite(result_r):
            raise ValueError("Nonfinite simulated trade result.")
        exit_index = m15.index.get_loc(pd.Timestamp(exit_time))
        trades.append(SimTrade(symbol, str(signal_time), str(m15.index[i+1]),
                               exit_time, candidate.side, entry, stop, target,
                               exit_price, result_r, reason))
        i = exit_index + 1  # no overlapping trades on this symbol
    equity, peak, max_dd = 1.0, 1.0, 0.0
    for t in trades:
        equity *= max(0, 1 + risk_fraction*t.result_r)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak-equity)/peak)
    metrics = {
        "symbol": symbol,
        "trade_count": len(trades),
        "win_rate": (sum(t.result_r > 0 for t in trades)/len(trades)) if trades else None,
        "average_r": (sum(t.result_r for t in trades)/len(trades)) if trades else None,
        "simulated_return": equity-1,
        "max_closed_trade_drawdown": max_dd,
        "notes": ("BID OHLC + historical spreads; next-open fills; "
                  "ambiguous SL/TP bars counted as SL; no commission, swap, "
                  "latency or non-gap slippage. Not a profit forecast."),
    }
    return {"metrics": metrics, "trades": [asdict(t) for t in trades]}
