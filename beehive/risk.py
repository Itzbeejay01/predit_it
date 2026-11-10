"""Conservative position sizing and demo-trade risk gates."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
import math


class RiskRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    side: str
    volume: float
    entry: float
    stop: float
    take_profit: float
    max_deviation_price: float
    risk_cash: float


def _volume_floor(amount, step):
    v = Decimal(str(amount))
    s = Decimal(str(step))
    if s <= 0:
        raise RiskRejected("Invalid broker volume step.")
    return float((v / s).to_integral_value(rounding=ROUND_FLOOR) * s)


def propose(broker, store, settings, signal):
    """Refuse orders if equity/risk/market metadata is unknown or unsafe."""
    account = broker.require_demo()
    today_start = store.start_equity(float(account.equity))
    if float(account.equity) <= today_start * (1 - settings.daily_loss_fraction):
        raise RiskRejected("Daily 2% equity drawdown limit reached.")
    all_positions = broker.positions()
    if len(all_positions) >= settings.max_positions:
        raise RiskRejected("Maximum two concurrent positions reached.")
    symbol = broker.resolve_symbol(signal.symbol)
    if any(p.symbol == symbol for p in all_positions):
        raise RiskRejected("A position already exists on this symbol.")
    tick, meta = broker.quote(symbol), broker.info(symbol)
    spread = float(tick.ask - tick.bid)
    max_spread = 0.70 if signal.symbol == "XAUUSD" else 0.00025
    if not (0 < spread <= max_spread):
        raise RiskRejected("Spread exceeds the instrument-specific limit.")
    side = signal.side
    entry = float(tick.ask if side == "BUY" else tick.bid)
    if not math.isfinite(signal.stop_distance) or signal.stop_distance <= 0:
        raise RiskRejected("Invalid ATR-based stop distance.")
    distance = max(float(signal.stop_distance), spread * 3)
    stop = entry - distance if side == "BUY" else entry + distance
    take_profit = entry + distance * signal.reward_multiple if side == "BUY" else entry - distance * signal.reward_multiple
    digits = int(meta.digits)
    stop, take_profit = round(stop, digits), round(take_profit, digits)
    if side == "BUY" and not (stop < entry < take_profit):
        raise RiskRejected("Invalid BUY stop-loss/take-profit geometry.")
    if side == "SELL" and not (take_profit < entry < stop):
        raise RiskRejected("Invalid SELL stop-loss/take-profit geometry.")
    if abs(entry - stop) <= float(meta.trade_stops_level) * float(meta.point):
        raise RiskRejected("Stop too close for broker restrictions.")
    one_lot_loss = broker.loss_for_one_lot(symbol, side, entry, stop)
    intended_cash = float(account.equity) * settings.risk_fraction
    # Reduce remaining risk allocation as we approach the daily limit.
    remaining_daily_cash = max(0, float(account.equity) - today_start * (1 - settings.daily_loss_fraction))
    allowed_cash = min(intended_cash, remaining_daily_cash)
    if allowed_cash <= 0:
        raise RiskRejected("No remaining daily risk budget.")
    if not (meta.volume_min > 0 and meta.volume_max >= meta.volume_min):
        raise RiskRejected("Invalid broker volume limits.")
    vol = min(allowed_cash / one_lot_loss, float(meta.volume_max))
    vol = _volume_floor(vol, float(meta.volume_step))
    if vol < float(meta.volume_min):
        raise RiskRejected("Minimum broker lot exceeds permitted 0.5% risk.")
    calculated_loss = broker.loss_for_one_lot(symbol, side, entry, stop) * vol
    if calculated_loss > allowed_cash + 1e-7:
        raise RiskRejected("Proposed size exceeds permitted risk.")
    return TradePlan(symbol, side, vol, entry, stop, take_profit,
                     max_deviation_price=max(float(meta.point) * 20, spread * 1.5),
                     risk_cash=calculated_loss)
