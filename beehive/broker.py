"""MT5 adapter. Every connection and every order checks that the account is DEMO."""
from datetime import datetime, timezone
import math
import pandas as pd


class BrokerError(RuntimeError):
    pass


class Mt5Broker:
    def __init__(self, settings):
        self.settings = settings
        self.mt5 = None
        self._symbols = {}

    def connect(self):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise BrokerError("MetaTrader5 Python package requires a supported Windows terminal environment.") from exc
        opts = {}
        if self.settings.mt5_login:
            if not self.settings.mt5_password or not self.settings.mt5_server:
                raise BrokerError("MT5_PASSWORD and MT5_SERVER are required with MT5_LOGIN.")
            opts.update(login=int(self.settings.mt5_login),
                        password=self.settings.mt5_password,
                        server=self.settings.mt5_server)
        # MT5's path is the optional first positional argument.
        path = self.settings.mt5_terminal_path
        connected = mt5.initialize(path, **opts) if path else mt5.initialize(**opts)
        if not connected:
            raise BrokerError("MT5 initialization failed; check terminal connection and demo credentials.")
        self.mt5 = mt5
        try:
            self.require_demo()
        except Exception:
            self.close()
            raise
        return self

    def close(self):
        if self.mt5 is not None:
            self.mt5.shutdown()
            self.mt5 = None

    def require_demo(self):
        if self.mt5 is None:
            raise BrokerError("MT5 is disconnected.")
        account = self.mt5.account_info()
        if account is None:
            raise BrokerError("MT5 account unavailable.")
        if account.trade_mode != self.mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise BrokerError("REFUSED: only MetaTrader 5 DEMO accounts are permitted.")
        if account.equity <= 0 or not math.isfinite(float(account.equity)):
            raise BrokerError("Invalid demo account equity.")
        return account

    def account(self):
        return self.require_demo()

    def resolve_symbol(self, desired):
        if desired in self._symbols:
            return self._symbols[desired]
        self.require_demo()
        entries = self.mt5.symbols_get()
        if entries is None:
            raise BrokerError("Could not list broker symbols.")
        exact = [s.name for s in entries if s.name.upper() == desired.upper()]
        # Some Exness demo servers suffix names with m or another identifier.
        suffix = [s.name for s in entries if s.name.upper().startswith(desired.upper())
                  and s.name[len(desired):].lower() in {"m", "c", ".m", ".c"}]
        matches = exact or suffix
        if len(matches) != 1:
            raise BrokerError(f"Cannot unambiguously resolve {desired} on this demo server.")
        symbol = matches[0]
        if not self.mt5.symbol_select(symbol, True):
            raise BrokerError(f"Cannot select {symbol}.")
        self._symbols[desired] = symbol
        return symbol

    def candles(self, desired, timeframe="M15", count=600):
        self.require_demo()
        symbol = self.resolve_symbol(desired)
        tf = {"M15": self.mt5.TIMEFRAME_M15, "H1": self.mt5.TIMEFRAME_H1}.get(timeframe)
        if tf is None:
            raise ValueError("Supported timeframes are M15 and H1.")
        # Start at position 1, never the forming (position 0) candle.
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 1, count)
        if rates is None or len(rates) < min(count, 60):
            raise BrokerError(f"Insufficient completed {timeframe} candles for {symbol}.")
        df = pd.DataFrame(rates)
        df.index = pd.to_datetime(df.pop("time"), unit="s", utc=True)
        df.index.name = "time"
        return df.sort_index()

    def quote(self, symbol):
        self.require_demo()
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None or tick.ask <= 0 or tick.bid <= 0 or tick.ask <= tick.bid:
            raise BrokerError(f"No valid bid/ask tick for {symbol}.")
        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(tick.time, timezone.utc)).total_seconds()
        if age < -10 or age > 120:
            raise BrokerError(f"Stale tick for {symbol}: {age:.0f}s.")
        return tick

    def info(self, symbol):
        self.require_demo()
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise BrokerError(f"No symbol metadata for {symbol}.")
        return info

    def positions(self):
        self.require_demo()
        positions = self.mt5.positions_get()
        if positions is None:
            raise BrokerError("Cannot verify open positions; refusing new orders.")
        return list(positions)

    def open_position_risk(self, positions):
        """Potential loss from CURRENT marked equity to each known stop, in account currency.

        Require a stop on every open position; foreign/manual positions can consume
        the same account-level daily loss budget as BeeHive.
        """
        self.require_demo()
        at_risk = 0.0
        for pos in positions:
            if not pos.sl or pos.volume <= 0:
                raise BrokerError("An open position has no SL; refusing additional orders.")
            side = self.mt5.ORDER_TYPE_BUY if pos.type == self.mt5.POSITION_TYPE_BUY else self.mt5.ORDER_TYPE_SELL
            tick = self.quote(pos.symbol)
            current = float(tick.bid if side == self.mt5.ORDER_TYPE_BUY else tick.ask)
            projected = self.mt5.order_calc_profit(side, pos.symbol, pos.volume, current, pos.sl)
            if projected is None or not math.isfinite(float(projected)):
                raise BrokerError("Could not evaluate existing position risk.")
            at_risk += max(0.0, -float(projected))
        return at_risk

    def loss_for_one_lot(self, symbol, side, entry, stop):
        self.require_demo()
        kind = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
        pnl = self.mt5.order_calc_profit(kind, symbol, 1.0, entry, stop)
        if pnl is None or not math.isfinite(float(pnl)) or pnl >= 0:
            raise BrokerError("Broker could not calculate stop-loss risk.")
        return abs(float(pnl))

    def place_demo_order(self, plan):
        account = self.require_demo()  # Hard block real accounts even after scan.
        if not self.settings.demo_auto_execute:
            raise BrokerError("Demo execution disabled; set DEMO_AUTO_EXECUTE=true to opt in.")
        terminal = self.mt5.terminal_info()
        if terminal is None or not terminal.trade_allowed or not account.trade_allowed:
            raise BrokerError("MT5 trading is disabled in terminal/account.")
        # Recheck tick and demo mode immediately before order submission.
        tick = self.quote(plan.symbol)
        current = tick.ask if plan.side == "BUY" else tick.bid
        if abs(current - plan.entry) > plan.max_deviation_price:
            raise BrokerError("Price moved from validated entry; refusing stale trade.")
        info = self.info(plan.symbol)
        # Two independent pre-send guards: risk cannot grow and no duplicate positions.
        existing = self.positions()
        if len(existing) >= self.settings.max_positions or any(p.symbol == plan.symbol for p in existing):
            raise BrokerError("Position limit changed before submission.")
        actual_loss = self.loss_for_one_lot(plan.symbol, plan.side, current, plan.stop) * plan.volume
        if actual_loss > plan.risk_cash + 1e-7 or actual_loss > float(account.equity) * self.settings.risk_fraction + 1e-7:
            raise BrokerError("Market movement increased expected risk; order cancelled.")
        if info.trade_stops_level * info.point > abs(current - plan.stop):
            raise BrokerError("Broker stop-distance restriction violated.")
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": plan.symbol,
            "volume": plan.volume,
            "type": self.mt5.ORDER_TYPE_BUY if plan.side == "BUY" else self.mt5.ORDER_TYPE_SELL,
            "price": current,
            "sl": plan.stop,
            "tp": plan.take_profit,
            "deviation": 20,
            "magic": 76112026,
            "comment": "BeeHive DEMO only",
            "type_time": self.mt5.ORDER_TIME_GTC,
        }
        # Validate fill method with order_check; no blind submissions.
        checked = None
        for fill in (self.mt5.ORDER_FILLING_IOC, self.mt5.ORDER_FILLING_FOK):
            request["type_filling"] = fill
            result = self.mt5.order_check(request)
            if result is not None and result.retcode == 0:
                checked = request.copy()
                break
        if checked is None:
            raise BrokerError("MT5 order_check rejected this trade.")
        self.require_demo()
        result = self.mt5.order_send(checked)
        if result is None or result.retcode not in {
            self.mt5.TRADE_RETCODE_DONE, self.mt5.TRADE_RETCODE_PLACED
        }:
            code = "unknown" if result is None else str(result.retcode)
            raise BrokerError(f"Demo order rejected; retcode={code}.")
        return result
