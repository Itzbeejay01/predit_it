"""Telegram Bot API transport and admin-only safety commands."""
import json
from urllib.request import Request, urlopen
from urllib.error import URLError


class Telegram:
    def __init__(self, settings):
        self.token = settings.telegram_token
        self.chat_id = str(settings.telegram_chat_id)
        self.admin_id = str(settings.telegram_admin_id)

    def _call(self, method, payload):
        if not self.token:
            return None
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError) as exc:
            # Never expose the URL: it contains the secret bot token.
            raise RuntimeError("Telegram API unavailable.") from exc
        if not result.get("ok"):
            raise RuntimeError("Telegram API rejected the request.")
        return result.get("result")

    def send(self, message, chat_id=None):
        destination = str(chat_id or self.chat_id)
        if not self.token or not destination:
            return False
        self._call("sendMessage", {"chat_id": destination,
                                   "text": message[:4000],
                                   "disable_web_page_preview": True})
        return True

    def handle_admin_commands(self, store):
        """Poll private commands; ignore all non-admin senders."""
        if not self.token or not self.admin_id:
            return
        offset = int(store.get("telegram_offset", "0"))
        updates = self._call("getUpdates", {"offset": offset, "limit": 30, "timeout": 0}) or []
        for event in updates:
            next_offset = int(event["update_id"]) + 1
            payload = event.get("message") or {}
            sender = str((payload.get("from") or {}).get("id", ""))
            command = (payload.get("text") or "").strip().split(" ")[0].lower().split("@")[0]
            target = (payload.get("chat") or {}).get("id")
            if sender == self.admin_id and target:
                if command == "/stop":
                    store.set_halted(True)
                    self.send("🛑 BeeHive demo execution HALTED. Market alerts may continue.", target)
                elif command == "/resume":
                    store.set_halted(False)
                    self.send("✅ BeeHive demo execution RESUMED. Demo-account checks remain mandatory.", target)
                elif command == "/status":
                    state = "HALTED" if store.halted() else "ARMED"
                    self.send(f"🐝 BeeHive: {state}. This bot NEVER executes live-account trades.", target)
            store.set("telegram_offset", str(next_offset))
