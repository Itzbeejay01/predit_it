"""Run with: python -m beehive.cli {scan|outlook|summary|status|stop|resume|daemon}"""
import argparse
from datetime import datetime
import logging
import time
from zoneinfo import ZoneInfo

from .config import Settings
from .service import BeeHiveService
from .storage import Store
from .telegram import Telegram


def daemon(service):
    """Local-time schedule; no cloud scheduling or perpetual reliability implied."""
    settings = service.settings
    store = service.store
    telegram = service.telegram
    logging.info("BeeHive daemon started: DEMO-only; automatic execution=%s; halted=%s",
                 settings.demo_auto_execute, store.halted())
    while True:
        try:
            telegram.handle_admin_commands(store)
            now = datetime.now(ZoneInfo(settings.time_zone))
            date = now.strftime("%Y-%m-%d")
            # M15 bar closes at :00/:15/:30/:45. Evaluate just afterward.
            if now.minute in (1, 16, 31, 46):
                bucket = now.minute // 15
                key = f"scan:{date}:{now.hour}:{bucket}"
                if store.claim_message(key):
                    logging.info("Scheduled scan %s", key)
                    logging.info("Outcomes: %s", service.scan())
            # Market outlook and summaries follow Nigerian local time (WAT).
            if now.minute < 5 and now.hour in (7, 9, 14, 22):
                kind = "summary" if now.hour == 22 else "outlook"
                key = f"report:{date}:{now.hour}:{kind}"
                if store.claim_message(key):
                    if kind == "summary":
                        service.publish_summary()
                    else:
                        labels = {7: "Morning", 9: "London", 14: "New York preparation"}
                        service.publish_outlook(labels[now.hour])
        except KeyboardInterrupt:
            raise
        except Exception:
            logging.exception("Scheduled task failed; no unsafe fallback execution.")
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="BeeHive demo-only forex intelligence bot")
    parser.add_argument("command", choices=[
        "scan", "outlook", "summary", "status", "stop", "resume", "daemon"
    ])
    parser.add_argument("--session", default="Daily", help="Outlook label")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    store = Store(settings.database)
    if args.command == "stop":
        store.set_halted(True)
        print("BeeHive demo execution halted. Existing MT5 positions are NOT automatically closed.")
        return
    if args.command == "resume":
        store.set_halted(False)
        print("BeeHive armed for DEMO accounts ONLY. Execution additionally requires DEMO_AUTO_EXECUTE=true.")
        return
    if args.command == "status":
        print(f"Safety status: {'HALTED' if store.halted() else 'ARMED'}")
        print(f"Demo auto-execution opt-in: {settings.demo_auto_execute}")
        for row in store.recent_signals(10):
            print(" | ".join(map(str, row)))
        return
    service = BeeHiveService(settings=settings, store=store, telegram=Telegram(settings))
    if args.command == "scan":
        for symbol, result in service.scan().items():
            print(f"{symbol}: {result}")
    elif args.command == "outlook":
        print(service.publish_outlook(args.session))
    elif args.command == "summary":
        print(service.publish_summary())
    elif args.command == "daemon":
        try:
            daemon(service)
        except KeyboardInterrupt:
            print("BeeHive daemon stopped. Already-open demo positions remain under broker SL/TP.")


if __name__ == "__main__":
    main()
