"""
Configuration for the trading bot.

All secrets are loaded from environment variables — NEVER hard-code
API keys or tokens in this file or commit them to version control.

Set these before running (e.g. in a .env file loaded by run.sh, or
exported in your shell):

    BYBIT_API_KEY
    BYBIT_API_SECRET
    BYBIT_TESTNET          "true" or "false" (default: true)
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID       your personal chat id (so only you can command it)
"""

import os


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# --- Exchange ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
BYBIT_TESTNET = _env_bool("BYBIT_TESTNET", True)  # default to fake-money testnet

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # only this chat can control the bot

# --- Market scanning ---
# Universe of pairs to scan. "Any coin that looks promising" starts here —
# the strategy filters this list down, it does not invent new symbols.
CANDIDATE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "TONUSDT",
]
SCAN_INTERVAL_SECONDS = 60          # how often to re-scan the market
KLINE_INTERVAL = "15"               # minutes per candle for indicators
KLINE_LOOKBACK = 100                # number of candles to fetch

# --- Strategy thresholds ---
RSI_PERIOD = 14
RSI_OVERSOLD = 30                   # RSI below this = potential buy signal
MA_FAST = 9
MA_SLOW = 21

# --- Risk management (hard limits — the bot will not exceed these) ---
MAX_OPEN_POSITIONS = 3
POSITION_SIZE_USDT = 20.0           # amount per trade, in USDT
TAKE_PROFIT_USDT = 3.0              # close the trade once profit reaches this
STOP_LOSS_PERCENT = 1.5             # close the trade if it drops this % from entry
MAX_DAILY_LOSS_USDT = 30.0          # bot halts new trades if daily losses exceed this
