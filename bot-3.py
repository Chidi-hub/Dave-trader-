"""
Telegram-controlled crypto trading bot (Bybit spot).

Commands (only usable from TELEGRAM_CHAT_ID):
  /start        - show status and available commands
  /run          - start the auto-scanning/trading loop
  /pause        - stop opening new trades (existing positions still managed)
  /status       - show open positions and today's P&L
  /balance      - show USDT wallet balance
  /close <SYM>  - manually close a position right now

Run with:  python bot.py
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
import strategy
from exchange import BybitExchange
from risk import RiskManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("bot")

exchange = BybitExchange()
risk = RiskManager()
state = {"running": False}


def _authorized(update: Update) -> bool:
    if not config.TELEGRAM_CHAT_ID:
        return True  # no restriction configured
    return str(update.effective_chat.id) == str(config.TELEGRAM_CHAT_ID)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_text(
        "Crypto bot ready.\n"
        f"Mode: {'TESTNET (fake money)' if config.BYBIT_TESTNET else 'LIVE — real funds'}\n\n"
        "/run - start trading loop\n"
        "/pause - stop opening new trades\n"
        "/status - open positions + today's P&L\n"
        "/balance - USDT balance\n"
        "/close <SYMBOL> - close a position now"
    )


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    state["running"] = True
    await update.message.reply_text("Trading loop started.")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    state["running"] = False
    await update.message.reply_text("Paused. No new trades will open. Existing positions are still watched for exit.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    lines = [f"Running: {state['running']}", f"Today's P&L: {risk.daily_pnl:.2f} USDT"]
    if not risk.positions:
        lines.append("No open positions.")
    else:
        lines.append("Open positions:")
        for sym, pos in risk.positions.items():
            price = exchange.get_last_price(sym)
            unrealized = (price - pos.entry_price) * pos.qty
            lines.append(f"  {sym}: entry {pos.entry_price:.4f}, now {price:.4f}, P&L {unrealized:+.2f} USDT")
    await update.message.reply_text("\n".join(lines))


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    bal = exchange.get_balance("USDT")
    await update.message.reply_text(f"USDT balance: {bal:.2f}")


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /close SYMBOL")
        return
    symbol = context.args[0].upper()
    pos = risk.positions.get(symbol)
    if not pos:
        await update.message.reply_text(f"No open position in {symbol}.")
        return
    exchange.place_market_sell(symbol, pos.qty)
    price = exchange.get_last_price(symbol)
    pnl = risk.register_close(symbol, price)
    await update.message.reply_text(f"Closed {symbol}. P&L: {pnl:+.2f} USDT")


async def trading_loop(app: Application):
    """Background loop: scans candidates, opens/closes trades, notifies via Telegram."""
    while True:
        try:
            if state["running"]:
                await _manage_open_positions(app)
                await _scan_for_entries(app)
        except Exception:
            log.exception("Error in trading loop")
        await asyncio.sleep(config.SCAN_INTERVAL_SECONDS)


async def _notify(app, text):
    if config.TELEGRAM_CHAT_ID:
        await app.bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=text)
    log.info(text)


async def _manage_open_positions(app):
    for symbol in list(risk.open_symbols()):
        price = exchange.get_last_price(symbol)
        should_close, reason = risk.check_exit(symbol, price)
        if should_close:
            pos = risk.positions[symbol]
            exchange.place_market_sell(symbol, pos.qty)
            pnl = risk.register_close(symbol, price)
            await _notify(app, f"Closed {symbol}: {reason}. P&L {pnl:+.2f} USDT")


async def _scan_for_entries(app):
    can_open, why = risk.can_open_new_trade()
    if not can_open:
        return
    for symbol in config.CANDIDATE_SYMBOLS:
        if symbol in risk.open_symbols():
            continue
        can_open, why = risk.can_open_new_trade()
        if not can_open:
            return
        candles = exchange.get_klines(symbol, config.KLINE_INTERVAL, config.KLINE_LOOKBACK)
        signal = strategy.evaluate(symbol, candles)
        if signal.action == "buy":
            order = exchange.place_market_buy(symbol, config.POSITION_SIZE_USDT)
            qty = config.POSITION_SIZE_USDT / signal.price  # approximation until fill data is read
            risk.register_open(symbol, signal.price, qty, config.POSITION_SIZE_USDT)
            await _notify(app, f"Opened {symbol} @ {signal.price:.4f} — {signal.reason}")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN before running.")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("close", cmd_close))

    async def post_init(app):
        app.create_task(trading_loop(app))

    app.post_init = post_init
    log.info("Starting bot (testnet=%s)...", config.BYBIT_TESTNET)
    app.run_polling()


if __name__ == "__main__":
    main()
