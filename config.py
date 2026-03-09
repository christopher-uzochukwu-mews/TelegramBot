"""Load env and config."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

def get_allowed_chat_ids():
    raw = os.getenv("ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return None
    ids = []
    for x in raw.split(","):
        x = x.strip()
        if not x:
            continue
        try:
            ids.append(int(x))
        except ValueError:
            pass
    return ids if ids else None

ALLOWED_CHAT_IDS = get_allowed_chat_ids()
SCHEDULE_PATH = Path(__file__).parent / "schedule.json"
# When to send "tomorrow's" reminder (hour in 24h, server local time)
def _int_env(name: str, default: str) -> int:
    try:
        return int(os.getenv(name, default).strip())
    except (ValueError, AttributeError):
        return int(default)
REMINDER_HOUR = _int_env("REMINDER_HOUR", "20")  # 8pm
REMINDER_MINUTE = _int_env("REMINDER_MINUTE", "0")
# Health check HTTP server (for Docker / monitoring)
HEALTH_CHECK_PORT = _int_env("HEALTH_CHECK_PORT", "8080")
