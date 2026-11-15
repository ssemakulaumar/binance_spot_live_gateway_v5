"""V5 configuration. Live trading is opt-in and uses separate credentials."""
import os
from decimal import Decimal

MODE = os.getenv("BINANCE_MODE", "paper").lower()
if MODE not in {"paper", "testnet", "live"}:
    raise ValueError("BINANCE_MODE must be paper, testnet, or live")

URLS = {
    "paper": None,
    "testnet": "https://testnet.binance.vision",
    "live": "https://api.binance.com",
}
BASE_URL = URLS[MODE]
if MODE == "live":
    API_KEY = os.getenv("BINANCE_LIVE_API_KEY", "")
    API_SECRET = os.getenv("BINANCE_LIVE_API_SECRET", "")
else:
    API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
    API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "")

QUOTE_ASSET = os.getenv("BOT_QUOTE_ASSET", "USDT").upper()
RISK_FRACTION = Decimal(os.getenv("BOT_RISK_FRACTION", "0.005"))
MAX_ALLOCATION_FRACTION = Decimal(os.getenv("BOT_MAX_ALLOCATION", "0.10"))
MAX_DAILY_LOSS_FRACTION = Decimal(os.getenv("BOT_MAX_DAILY_LOSS", "0.02"))
FEE_BUFFER_FRACTION = Decimal("0.002")
RECV_WINDOW_MS = 5000
HTTP_TIMEOUT_SECONDS = 10
STATE_DB = os.getenv("BOT_STATE_DB", "v5_state.sqlite3")
KILL_SWITCH_FILE = os.getenv("BOT_KILL_SWITCH_FILE", "KILL_SWITCH")
