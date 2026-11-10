"""Configuration for the isolated BeeHive demo bot. Never commit credentials."""
from dataclasses import dataclass
from pathlib import Path
import os


def enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database: Path = Path(os.getenv("BEEHIVE_DB", "beehive.sqlite3"))
    mt5_login: str = os.getenv("MT5_LOGIN", "")
    mt5_password: str = os.getenv("MT5_PASSWORD", "")
    mt5_server: str = os.getenv("MT5_SERVER", "")
    mt5_terminal_path: str = os.getenv("MT5_TERMINAL_PATH", "")
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_admin_id: str = os.getenv("TELEGRAM_ADMIN_ID", "")
    # Deliberately opt-in. A demo connection alone does not authorize trading.
    demo_auto_execute: bool = enabled("DEMO_AUTO_EXECUTE")
    risk_fraction: float = 0.005
    daily_loss_fraction: float = 0.02
    max_positions: int = 2
    time_zone: str = "Africa/Lagos"
    symbols: tuple[str, ...] = ("EURUSD", "GBPUSD", "XAUUSD")

    def __post_init__(self) -> None:
        if self.risk_fraction <= 0 or self.risk_fraction > 0.005:
            raise ValueError("Risk per trade must not exceed 0.5%.")
        if self.daily_loss_fraction <= 0 or self.daily_loss_fraction > 0.02:
            raise ValueError("Daily loss limit must not exceed 2%.")
        if self.max_positions > 2 or self.max_positions <= 0:
            raise ValueError("Maximum positions must be between 1 and 2.")
