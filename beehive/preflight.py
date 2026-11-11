"""Read-only MT5 connection and market-data smoke test. Never submits an order."""
from datetime import datetime, timezone, timedelta


def check_environment(broker, settings):
    """Fail closed on wrong account; report each instrument independently."""
    report = {"account": "UNKNOWN", "execution_enabled": False, "symbols": {}}
    try:
        broker.connect()  # includes the hard MetaTrader DEMO account check
        account = broker.require_demo()
        report["account"] = "DEMO"
        report["equity_positive"] = account.equity > 0
        terminal_info = getattr(broker.mt5, 'terminal_info', None)
        terminal = terminal_info() if callable(terminal_info) else None
        report["terminal_trade_allowed"] = bool(terminal and terminal.trade_allowed)
        report["account_trade_allowed"] = bool(getattr(account, "trade_allowed", False))
        report["execution_enabled"] = bool(
            settings.demo_auto_execute
            and report["terminal_trade_allowed"]
            and report["account_trade_allowed"]
        )
        report["safety_note"] = (
            "Read-only check. No orders sent. Kill switch is a separate gate; "
            "execution_enabled does not imply that trading will occur."
        )
        for desired in settings.symbols:
            try:
                symbol = broker.resolve_symbol(desired)
                info = broker.info(symbol)
                m15 = broker.candles(desired, "M15", 100)
                h1 = broker.candles(desired, "H1", 100)
                if getattr(info, "point", 0) <= 0 or getattr(info, "volume_min", 0) <= 0:
                    raise ValueError("Invalid broker instrument specification.")
                last_m15_close = m15.index[-1].to_pydatetime() + timedelta(minutes=15)
                age_minutes = (datetime.now(timezone.utc) - last_m15_close).total_seconds()/60
                if age_minutes > 20:
                    raise ValueError("Latest M15 candle is stale.")
                tick = broker.quote(symbol)
                report["symbols"][desired] = {
                    "result": "OK",
                    "broker_symbol": symbol,
                    "spread_price_units": round(float(tick.ask-tick.bid), 7),
                    "m15_candles": len(m15),
                    "h1_candles": len(h1),
                }
            except Exception as exc:
                report["symbols"][desired] = {
                    "result": "FAIL",
                    "reason": str(exc)[:180] if type(exc).__name__ in {
                        "BrokerError", "ValueError"
                    } else type(exc).__name__,
                }
    except Exception as exc:
        report["account"] = "FAILED"
        report["error"] = (
            str(exc)[:180] if type(exc).__name__ in {"BrokerError", "ValueError"}
            else type(exc).__name__
        )
    finally:
        broker.close()
    return report
