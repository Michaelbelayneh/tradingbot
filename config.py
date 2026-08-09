"""
Loads all settings from a local .env file.
Copy .env.example to .env and fill in your real values.
NEVER commit .env to GitHub (it's already in .gitignore).
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _req(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}. Check your .env file.")
    return val

# MT5
MT5_LOGIN = int(_req("MT5_LOGIN"))
MT5_PASSWORD = _req("MT5_PASSWORD")
MT5_SERVER = _req("MT5_SERVER")
MT5_TERMINAL_PATH = os.getenv("MT5_TERMINAL_PATH") or None

# Telegram
TELEGRAM_BOT_TOKEN = _req("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _req("TELEGRAM_CHAT_ID")

# Webhook
WEBHOOK_SECRET = _req("WEBHOOK_SECRET")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))

# Risk
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.01"))
MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "5"))
MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "778899"))
