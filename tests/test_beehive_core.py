"""Offline tests. No real broker connection or Telegram API access."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd

from beehive.broker import BrokerError, Mt5Broker
from beehive.backtest import _fill_exit, simulate
from beehive.preflight import check_environment
from beehive.config import Settings
from beehive.ml import feature_frame, research
from beehive.risk import RiskRejected, propose
from beehive.signals import Signal, analyze, features
from beehive.storage import Store
from beehive.service import BeeHiveService
from beehive.ml import ResearchResult


class DummyBroker:
    def __init__(self, equity=1000.0):
        self.equity = equity
        self.open_positions = []
        self.tick = SimpleNamespace(ask=1.1002, bid=1.1001)
        self.meta = SimpleNamespace(digits=5, point=0.00001,
                                    trade_stops_level=10, volume_min=0.01,
                                    volume_max=10.0, volume_step=0.01)
    def require_demo(self):
        return SimpleNamespace(equity=self.equity)
    def positions(self):
        return self.open_positions
    def pending_orders(self):
        return []
    def resolve_symbol(self, desired):
        return desired
    def quote(self, symbol):
        return self.tick
    def info(self, symbol):
        return self.meta
    def loss_for_one_lot(self, symbol, side, entry, stop):
        return abs(entry-stop) * 100000
    def open_position_risk(self, positions):
        return sum(getattr(pos, "risk", 0.0) for pos in positions)


def candle_frame(n=500):
    index = pd.date_range("2026-01-05", periods=n, freq="15min", tz="UTC")
    moves = 0.00005*np.sin(np.arange(n)/6) + np.arange(n)*0.000002
    close = 1.1 + moves
    return pd.DataFrame({"open": close-0.00002, "high": close+0.00010,
                         "low": close-0.00010, "close": close,
                         "tick_volume": np.full(n, 100)}, index=index)


def idea():
    return Signal("EURUSD", "BUY", "2026-01-05 10:00:00+00:00", 0.002, 2.0,
                  ("test",), "test-signal")


class TestRiskAndStorage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "journal.db")
        self.settings = Settings(database=Path(self.temp.name)/"journal.db")
        self.broker = DummyBroker()

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_risk_limit_and_lot_rounding(self):
        plan = propose(self.broker, self.store, self.settings, idea())
        self.assertLessEqual(plan.risk_cash, 5.0 + 1e-7)
        self.assertGreater(plan.volume, 0)
        self.assertLessEqual(plan.volume, 0.03)
        self.assertLess(plan.stop, plan.entry)
        self.assertGreater(plan.take_profit, plan.entry)

    def test_daily_equity_loss_blocks_order(self):
        self.store.start_equity(1000)
        self.broker.equity = 975
        with self.assertRaises(RiskRejected):
            propose(self.broker, self.store, self.settings, idea())

    def test_existing_symbol_position_blocks_order(self):
        self.broker.open_positions = [SimpleNamespace(symbol="EURUSD")]
        with self.assertRaises(RiskRejected):
            propose(self.broker, self.store, self.settings, idea())

    def test_open_position_risk_reduces_remaining_daily_budget(self):
        self.store.start_equity(1000)
        self.broker.equity = 985
        self.broker.open_positions = [SimpleNamespace(symbol="GBPUSD", risk=6)]
        with self.assertRaises(RiskRejected):
            propose(self.broker, self.store, self.settings, idea())

    def test_pending_orders_block_submission(self):
        self.broker.pending_orders = lambda: [SimpleNamespace(symbol="GBPUSD")]
        with self.assertRaises(RiskRejected):
            propose(self.broker, self.store, self.settings, idea())

    def test_unaffordable_minimum_lot_blocks_order(self):
        self.broker.meta.volume_min = 0.1
        with self.assertRaises(RiskRejected):
            propose(self.broker, self.store, self.settings, idea())

    def test_spread_filter_blocks_order(self):
        self.broker.tick.ask = 1.1010
        with self.assertRaises(RiskRejected):
            propose(self.broker, self.store, self.settings, idea())

    def test_kill_switch_defaults_to_halted(self):
        self.assertTrue(self.store.halted())
        self.store.set_halted(False)
        self.assertFalse(self.store.halted())

    def test_signal_claim_is_unique(self):
        self.assertTrue(self.store.claim_signal(idea()))
        self.assertFalse(self.store.claim_signal(idea()))
        self.store.result("test-signal", "blocked", "test")
        self.assertEqual(self.store.recent_signals()[0][3], "blocked")


class TestMarketResearch(unittest.TestCase):
    def test_indicators_are_causal(self):
        short = candle_frame(120)
        long = candle_frame(200)
        original = features(short)[["ema20", "rsi", "atr"]]
        extended = features(long).loc[short.index][["ema20", "rsi", "atr"]]
        np.testing.assert_allclose(original.values, extended.values, equal_nan=True)

    def test_no_forced_trade(self):
        df = candle_frame(180)
        h1 = df.iloc[::4]
        h1 = pd.concat([h1, h1.iloc[[-1]]])  # at least 60 H1 needed below
        h1 = candle_frame(200)
        self.assertIsNone(analyze("EURUSD", df, h1))

    def test_ml_experiment_has_holdout(self):
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("Optional scikit-learn unavailable")
        result = research(candle_frame(500))
        self.assertEqual(result.label, "experimental / uncalibrated")
        self.assertGreaterEqual(result.probability_up, 0)
        self.assertLessEqual(result.probability_up, 1)
        self.assertGreater(result.test_samples, 40)

    def test_ml_features_causal(self):
        a = feature_frame(candle_frame(100))
        b = feature_frame(candle_frame(150)).iloc[:100]
        np.testing.assert_allclose(a.values, b.values, equal_nan=True)


class TestBacktest(unittest.TestCase):
    def test_ambiguous_bar_counts_as_stop(self):
        t = pd.date_range("2026-01-01", periods=1, freq="15min", tz="UTC")
        future = pd.DataFrame([{"open": 1.1, "high": 1.13, "low": 1.08,
                                "close": 1.1, "spread": 2}], index=t)
        _, price, reason = _fill_exit("BUY", 1.1, 1.09, 1.12, future, 0.0001)
        self.assertEqual(reason, "STOP")
        self.assertAlmostEqual(price, 1.09)

    def test_spread_missing_is_not_free_execution(self):
        t = pd.date_range("2026-01-01", periods=1, freq="15min", tz="UTC")
        future = pd.DataFrame([{"open": 1.1, "high": 1.13, "low": 1.08,
                                "close": 1.1, "spread": 0}], index=t)
        with self.assertRaises(ValueError):
            _fill_exit("BUY", 1.1, 1.09, 1.12, future, 0.0001)

    def test_short_history_rejected(self):
        short = candle_frame(100)
        with self.assertRaises(ValueError):
            simulate(short, short, "EURUSD", 0.00001)


class FakeTelegram:
    def __init__(self):
        self.messages = []
    def handle_admin_commands(self, store):
        return None
    def send(self, message):
        self.messages.append(message)
        return True


class FakeExecutionBroker(DummyBroker):
    def __init__(self):
        super().__init__()
        self.sent = 0
    def connect(self):
        return self
    def close(self):
        return None
    def candles(self, desired, timeframe="M15", count=600):
        interval = "15min" if timeframe == "M15" else "1h"
        frame = candle_frame(count)
        frame.index = pd.date_range(
            end=pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=15 if timeframe == "M15" else 60),
            periods=count, freq=interval)
        return frame
    def place_demo_order(self, plan):
        self.sent += 1
        return SimpleNamespace(order=98765)


class TestServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "journal.db")
        self.telegram = FakeTelegram()
        self.broker = FakeExecutionBroker()
        self.store.set_halted(False)

    def tearDown(self):
        self.temp.cleanup()

    def service(self, enabled):
        return BeeHiveService(
            settings=Settings(database=Path(self.temp.name)/"journal.db",
                              demo_auto_execute=enabled),
            store=self.store, broker=self.broker, telegram=self.telegram)

    def test_demo_order_only_after_explicit_opt_in(self):
        score = ResearchResult(0.6, 0.53, 0.25, 0.26, 100)
        with patch("beehive.service.analyze", return_value=idea()), patch(
            "beehive.service.research", return_value=score
        ):
            result = self.service(enabled=False).scan()
        self.assertEqual(result["EURUSD"], "SIGNAL ONLY")
        self.assertEqual(self.broker.sent, 0)

    def test_demo_order_submitted_only_once_per_signal(self):
        score = ResearchResult(0.6, 0.53, 0.25, 0.26, 100)
        service = self.service(enabled=True)
        with patch("beehive.service.analyze", return_value=idea()), patch(
            "beehive.service.research", return_value=score
        ):
            first = service.scan()
            second = service.scan()
        self.assertEqual(first["EURUSD"], "DEMO ORDER SUBMITTED")
        self.assertEqual(second["EURUSD"], "ALREADY SEEN")
        self.assertEqual(self.broker.sent, 1)
        self.assertTrue(any("DEMO" in m for m in self.telegram.messages))


class TestPreflight(unittest.TestCase):
    def test_read_only_preflight_cannot_submit_demo_order(self):
        broker = FakeExecutionBroker()
        broker.mt5 = SimpleNamespace(terminal_info=lambda: SimpleNamespace(trade_allowed=True))
        account_before = broker.sent
        report = check_environment(broker, Settings())
        self.assertEqual(report["account"], "DEMO")
        self.assertEqual(report["symbols"]["EURUSD"]["result"], "OK")
        self.assertEqual(account_before, broker.sent)


class TestHardDemoGate(unittest.TestCase):
    def test_refuses_real_account(self):
        broker = Mt5Broker(Settings())
        broker.mt5 = SimpleNamespace(
            ACCOUNT_TRADE_MODE_DEMO=0,
            account_info=lambda: SimpleNamespace(trade_mode=1, equity=5000.0)
        )
        with self.assertRaises(BrokerError):
            broker.require_demo()

    def test_accepts_demo_account(self):
        broker = Mt5Broker(Settings())
        broker.mt5 = SimpleNamespace(
            ACCOUNT_TRADE_MODE_DEMO=0,
            account_info=lambda: SimpleNamespace(trade_mode=0, equity=5000.0)
        )
        self.assertEqual(broker.require_demo().equity, 5000.0)


if __name__ == "__main__":
    unittest.main()
