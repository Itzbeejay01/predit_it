"""Experimental macOS connector: strictly read-only for demo accounts.

Community mt5_mac is not the official MT5 Python SDK. The published Mac
interface lacks order_check / order_calc_profit, so orders are NEVER sent.
"""
from datetime import datetime, timezone
import importlib
import math
import pandas as pd
from .broker import BrokerError, Mt5Broker


class MacMt5Broker(Mt5Broker):
    def __init__(self, settings, mt5_override=None):
        super().__init__(settings)
        self._override = mt5_override

    def connect(self):
        try:
            api = self._override or importlib.import_module("mt5_mac")
        except ImportError as exc:
            raise BrokerError("Optional mt5_mac is not installed; see README_BEEHIVE.md.") from exc
        if self.settings.mt5_terminal_path:
            raise BrokerError("MT5_TERMINAL_PATH is Windows-only; unset for Mac.")
        if not api.initialize():
            raise BrokerError("Unable to initialize Mac MetaTrader 5 bridge.")
        self.mt5 = api
        try:
            if self.settings.mt5_login:
                if not self.settings.mt5_password or not self.settings.mt5_server:
                    raise BrokerError("Missing demo password or server.")
                if not api.login(int(self.settings.mt5_login),
                                 self.settings.mt5_password,
                                 self.settings.mt5_server):
                    raise BrokerError("Demo login failed.")
            self.require_demo()
        except Exception:
            self.close()
            raise
        return self

    def require_demo(self):
        if self.mt5 is None:
            raise BrokerError("Disconnected.")
        account = self.mt5.account_info()
        # MetaTrader account trade mode enum: DEMO == 0.
        if account is None or int(getattr(account, "trade_mode", -1)) != 0:
            raise BrokerError("REFUSED: Mac research adapter requires DEMO mode.")
        equity = float(getattr(account, "equity", 0))
        if equity <= 0 or not math.isfinite(equity):
            raise BrokerError("Invalid demo equity.")
        return account

    def candles(self, desired, timeframe="M15", count=600):
        self.require_demo()
        symbol = self.resolve_symbol(desired)
        tf = {"M15": getattr(self.mt5, "TIMEFRAME_M15", None),
              "H1": getattr(self.mt5, "TIMEFRAME_H1", None)}.get(timeframe)
        if tf is None:
            raise BrokerError("Unsupported timeframe.")
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 1, count)
        if rates is None or len(rates) < min(count, 60):
            raise BrokerError("Insufficient complete candles.")
        rows = []
        for r in rates:
            if hasattr(r, "_asdict"):
                rows.append(r._asdict())
            elif hasattr(r, "__dict__"):
                rows.append(vars(r))
            else:
                raise BrokerError("Unrecognized Mac candle format.")
        df = pd.DataFrame(rows)
        required = {"time", "open", "high", "low", "close", "spread"}
        if not required.issubset(df.columns):
            raise BrokerError("Candle data is missing columns.")
        df.index = pd.to_datetime(df.pop("time"), unit="s", utc=True)
        df.index.name = "time"
        return df.sort_index()

    def quote(self, symbol):
        self.require_demo()
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None or tick.bid <= 0 or tick.ask <= tick.bid:
            raise BrokerError("Invalid demo tick.")
        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(float(tick.time),timezone.utc)).total_seconds()
        if age < -10 or age > 120:
            raise BrokerError("Stale broker tick.")
        return tick

    def pending_orders(self):
        self.require_demo()
        orders = self.mt5.orders_get()
        if orders is None:
            raise BrokerError("Cannot inspect pending orders.")
        return list(orders)

    def positions(self):
        self.require_demo()
        positions = self.mt5.positions_get()
        if positions is None:
            raise BrokerError("Cannot inspect positions.")
        return list(positions)

    def open_position_risk(self, positions):
        raise BrokerError("Mac connector cannot verify full open-position risk.")

    def loss_for_one_lot(self, symbol, side, entry, stop):
        raise BrokerError("Mac connector cannot perform verified order_calc_profit.")

    def place_demo_order(self, plan):
        raise BrokerError("Mac connector is READ-ONLY. Demo orders require a separately tested MQL5 bridge.")


def select_broker(settings):
    import sys
    return MacMt5Broker(settings) if sys.platform == "darwin" else Mt5Broker(settings)
