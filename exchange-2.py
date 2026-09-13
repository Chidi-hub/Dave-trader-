"""
Thin wrapper around the Bybit API (via pybit) — handles market data
and order placement. Keeps exchange-specific details out of the
strategy and bot logic.
"""

import logging
from pybit.unified_trading import HTTP

import config

log = logging.getLogger("exchange")


class BybitExchange:
    def __init__(self):
        self.client = HTTP(
            testnet=config.BYBIT_TESTNET,
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
        )
        log.info("Connected to Bybit (%s)", "TESTNET" if config.BYBIT_TESTNET else "LIVE")

    def get_klines(self, symbol: str, interval: str, limit: int):
        """Returns candles oldest-first: list of dicts with o/h/l/c/v."""
        resp = self.client.get_kline(
            category="spot",
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        rows = resp["result"]["list"]
        rows.reverse()  # bybit returns newest-first
        candles = []
        for r in rows:
            candles.append({
                "time": int(r[0]),
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "volume": float(r[5]),
            })
        return candles

    def get_last_price(self, symbol: str) -> float:
        resp = self.client.get_tickers(category="spot", symbol=symbol)
        return float(resp["result"]["list"][0]["lastPrice"])

    def get_balance(self, coin: str = "USDT") -> float:
        resp = self.client.get_wallet_balance(accountType="UNIFIED", coin=coin)
        try:
            return float(resp["result"]["list"][0]["coin"][0]["walletBalance"])
        except (KeyError, IndexError):
            return 0.0

    def place_market_buy(self, symbol: str, usdt_amount: float):
        """Buys `usdt_amount` worth of `symbol` at market price (spot)."""
        log.info("BUY %s ~ %.2f USDT", symbol, usdt_amount)
        return self.client.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            marketUnit="quoteCoin",   # amount is specified in USDT
            qty=str(usdt_amount),
        )

    def place_market_sell(self, symbol: str, qty: float):
        """Sells `qty` units of the base asset at market price (spot)."""
        log.info("SELL %s qty=%s", symbol, qty)
        return self.client.place_order(
            category="spot",
            symbol=symbol,
            side="Sell",
            orderType="Market",
            marketUnit="baseCoin",
            qty=str(qty),
        )
