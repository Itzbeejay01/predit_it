"""Orchestrates market analysis, alerts and tightly gated demo order execution."""
import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from .broker import BrokerError
from .mac_broker import select_broker
from .config import Settings
from .ml import research
from .risk import propose, RiskRejected
from .signals import analyze, outlook
from .storage import Store
from .telegram import Telegram

log = logging.getLogger(__name__)


class BeeHiveService:
    def __init__(self, settings=None, broker=None, store=None, telegram=None):
        self.settings = settings or Settings()
        self.store = store or Store(self.settings.database)
        self.broker = broker or select_broker(self.settings)
        self.telegram = telegram or Telegram(self.settings)

    def safe_send(self, text):
        try:
            return self.telegram.send(text)
        except Exception as exc:
            # Never let Telegram outages cause duplicate broker orders.
            log.error("Telegram notification failed: %s", type(exc).__name__)
            return False

    def _load(self, symbol):
        m15 = self.broker.candles(symbol, "M15", 600)
        h1 = self.broker.candles(symbol, "H1", 200)
        current = datetime.now(timezone.utc)
        # MT5 candle timestamps are opening times, not close times.
        if current - (m15.index[-1].to_pydatetime() + timedelta(minutes=15)) > timedelta(minutes=20):
            raise BrokerError("M15 market data is stale; no signal may be executed.")
        if current - (h1.index[-1].to_pydatetime() + timedelta(hours=1)) > timedelta(minutes=75):
            raise BrokerError("H1 market data is stale; no signal may be executed.")
        return m15, h1

    def scan(self):
        """One idempotent pass. Use schedule/daemon for continuous execution."""
        outcomes = {}
        self.broker.connect()
        try:
            try:
                self.telegram.handle_admin_commands(self.store)
            except Exception:
                log.warning("Telegram command polling failed; demo safety defaults remain in effect.")
            account = self.broker.require_demo()
            # Establish the day's starting equity even if no setup ever appears.
            self.store.start_equity(float(account.equity))
            for symbol in self.settings.symbols:
                try:
                    m15, h1 = self._load(symbol)
                    idea = analyze(symbol, m15, h1)
                    if idea is None:
                        outcomes[symbol] = "NO TRADE"
                        continue
                    if not self.store.claim_signal(idea):
                        outcomes[symbol] = "ALREADY SEEN"
                        continue
                    research_note = "ML unavailable"
                    try:
                        ml = research(m15)
                        research_note = (f"Experimental ML up-probability: {ml.probability_up:.1%}; "
                                         f"holdout Brier: {ml.holdout_brier:.3f} "
                                         f"(baseline {ml.baseline_brier:.3f}; n={ml.test_samples}). "
                                         "Not a calibrated win probability.")
                    except (ValueError, RuntimeError) as exc:
                        research_note = f"ML skipped ({type(exc).__name__})."
                    msg = (f"🐝 BeeHive | {symbol} | {idea.side}\n"
                           f"Closed M15 candle: {idea.candle_time}\n"
                           f"H1 trend + M15 breakout and momentum\n"
                           f"Stop distance: {idea.stop_distance:.5f}; target: {idea.reward_multiple:.1f}R\n"
                           f"{research_note}")
                    if self.store.halted():
                        self.store.result(idea.signal_id, "halted", "Signal only; kill switch active")
                        outcomes[symbol] = "HALTED / SIGNAL ONLY"
                        self.safe_send(msg + "\n🛑 Demo execution halted.")
                    elif not self.settings.demo_auto_execute:
                        self.store.result(idea.signal_id, "signal_only", "Automatic demo execution disabled")
                        outcomes[symbol] = "SIGNAL ONLY"
                        self.safe_send(msg + "\nℹ️ Demo auto-execution not enabled.")
                    else:
                        try:
                            plan = propose(self.broker, self.store, self.settings, idea)
                            result = self.broker.place_demo_order(plan)
                            self.store.result(idea.signal_id, "submitted",
                                              f"order={getattr(result,'order',0)} volume={plan.volume}")
                            outcomes[symbol] = "DEMO ORDER SUBMITTED"
                            self.safe_send(msg + f"\n✅ DEMO {plan.side} {plan.volume} {plan.symbol}"
                                               f"\nEntry {plan.entry:.5f} | SL {plan.stop:.5f}"
                                               f" | TP {plan.take_profit:.5f}"
                                               f"\nRisk estimate: {plan.risk_cash:.2f} account currency"
                                               f"\nBroker order: {getattr(result,'order',0)}")
                        except (RiskRejected, BrokerError) as exc:
                            self.store.result(idea.signal_id, "blocked", str(exc))
                            outcomes[symbol] = "RISK BLOCKED"
                            self.safe_send(msg + f"\n⛔ DEMO order blocked: {exc}")
                except Exception as exc:
                    # One symbol failure must never prompt an unchecked order in another.
                    log.exception("Scan failed for %s", symbol)
                    outcomes[symbol] = f"ERROR: {type(exc).__name__}"
            return outcomes
        finally:
            self.broker.close()

    def publish_outlook(self, session="Daily"):
        report = [f"🐝 BeeHive {session} market outlook",
                  datetime.now(ZoneInfo(self.settings.time_zone)).strftime("%Y-%m-%d %H:%M WAT"),
                  "Demo research only; NO TRADE is a valid outcome."]
        self.broker.connect()
        try:
            self.broker.require_demo()
            for sym in self.settings.symbols:
                try:
                    m15, h1 = self._load(sym)
                    info = outlook(sym, m15, h1)
                    report.append(f"\n{sym}: {info['bias']} H1 bias | "
                                  f"last M15 close {info['last_close']:.5f} | "
                                  f"RSI {info['rsi']:.1f} | ATR {info['atr']:.5f}\n"
                                  f"As of {info['as_of']}")
                except Exception as exc:
                    report.append(f"\n{sym}: data unavailable ({type(exc).__name__})")
        finally:
            self.broker.close()
        message = "\n".join(report)
        self.safe_send(message)
        return message

    def publish_summary(self):
        rows = self.store.recent_signals(20)
        status = "HALTED" if self.store.halted() else "ARMED (DEMO only)"
        msg = ("🐝 BeeHive daily research journal\n"
               f"Execution mode: {status}\n"
               f"Last {len(rows)} signals (not realised P/L):")
        for created_at, symbol, side, result, _ in rows:
            msg += f"\n{created_at[:16]} {symbol} {side}: {result}"
        msg += "\nBroker P/L tracking is not yet included; do not interpret as a profit report."
        self.safe_send(msg)
        return msg
