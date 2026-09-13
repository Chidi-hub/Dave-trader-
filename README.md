Bybit Telegram Trading Bot
Scans a list of coins on Bybit spot, buys on a simple RSI + moving-average
dip signal, and auto-closes each trade at a take-profit target or stop-loss.
Controlled entirely from Telegram.
⚠️ Before you touch real money
No bot guarantees profit. This one enforces a stop-loss so losses are
capped, but it will lose money on some trades — that's normal for any
strategy. Test on testnet and/or paper-trade for a while first.
Never share your API keys or bot token with anyone, and never paste them
into chat with an AI assistant, including this one.
Start with BYBIT_TESTNET=true (the default). Only switch to live once
you've watched it run for a while and understand what it's doing.
Set POSITION_SIZE_USDT and MAX_DAILY_LOSS_USDT in config.py to
amounts you'd be fine losing entirely.
1. Get your credentials
Bybit API key (Account → API Management):
Create a key with Spot Trading permission only — do NOT enable
withdrawals.
For testing, create it on testnet.bybit.com
instead, and use their faucet for fake funds.
Telegram bot token: message @BotFather on
Telegram, /newbot, follow the prompts, copy the token it gives you.
Your Telegram chat id: message @userinfobot
and it will reply with your numeric id. This locks the bot so only you can
issue commands.
2. Install
Bash
3. Configure
Set these as environment variables (e.g. create a .env and source it,
or export directly in your shell):
Bash
Adjust trading parameters (coins scanned, position size, take-profit,
stop-loss, max concurrent trades, daily loss limit) at the top of
config.py.
4. Run
Bash
Then in Telegram, message your bot:
/start — see status and commands
/run — start the scanning/trading loop
/status — open positions and today's P&L
/balance — USDT balance
/pause — stop opening new trades
/close SYMBOL — manually close a position immediately
How the strategy works
Every SCAN_INTERVAL_SECONDS, the bot pulls recent candles for each symbol
in CANDIDATE_SYMBOLS and checks:
RSI(14) below 30 (oversold), and
the longer moving average is still trending up (avoids catching a coin
in freefall)
If both are true, it opens a position sized at POSITION_SIZE_USDT. Open
positions are checked every scan and closed automatically when they hit
TAKE_PROFIT_USDT profit or STOP_LOSS_PERCENT loss.
This is intentionally simple so you can read and adjust it — it is a
starting point, not a proven strategy. Consider backtesting changes before
running them live.
Files
File
Purpose
config.py
All settings — coins, risk limits, API key loading
exchange.py
Bybit API wrapper (market data + order placement)
strategy.py
Entry signal logic (RSI + moving averages)
risk.py
Position tracking, stop-loss/take-profit, daily loss cap
bot.py
Telegram bot + main scanning loop
state.json
Auto-created — persists open positions across restarts
