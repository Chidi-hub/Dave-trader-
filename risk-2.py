"""
Tracks open positions and enforces hard risk limits:
  - fixed position size
  - per-trade take-profit (in USDT)
  - per-trade stop-loss (in %)
  - max concurrent open positions
  - max daily loss (bot stops opening new trades once hit)

This module holds no exchange logic — it just decides *whether* a
trade should happen and *when* an open one should be closed.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import date

import config

log = logging.getLogger("risk")

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")


@dataclass
class Position:
    symbol: str
    entry_price: float
    qty: float
    usdt_spent: float
    opened_at: float


class RiskManager:
    def __init__(self):
        self.positions: dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.pnl_date = str(date.today())
        self._load()

    # --- persistence so a restart doesn't lose track of open trades ---
    def _load(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                data = json.load(f)
            self.positions = {
                s: Position(**p) for s, p in data.get("positions", {}).items()
            }
            self.daily_pnl = data.get("daily_pnl", 0.0)
            self.pnl_date = data.get("pnl_date", str(date.today()))

    def _save(self):
        data = {
            "positions": {s: asdict(p) for s, p in self.positions.items()},
            "daily_pnl": self.daily_pnl,
            "pnl_date": self.pnl_date,
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _roll_day_if_needed(self):
        today = str(date.today())
        if today != self.pnl_date:
            self.pnl_date = today
            self.daily_pnl = 0.0
            self._save()

    # --- decisions ---
    def can_open_new_trade(self) -> tuple[bool, str]:
        self._roll_day_if_needed()
        if len(self.positions) >= config.MAX_OPEN_POSITIONS:
            return False, "max open positions reached"
        if self.daily_pnl <= -abs(config.MAX_DAILY_LOSS_USDT):
            return False, "daily loss limit reached — no new trades today"
        return True, ""

    def register_open(self, symbol: str, entry_price: float, qty: float, usdt_spent: float):
        self.positions[symbol] = Position(
            symbol=symbol, entry_price=entry_price, qty=qty,
            usdt_spent=usdt_spent, opened_at=time.time(),
        )
        self._save()

    def register_close(self, symbol: str, exit_price: float) -> float:
        pos = self.positions.pop(symbol, None)
        if not pos:
            return 0.0
        pnl = (exit_price - pos.entry_price) * pos.qty
        self.daily_pnl += pnl
        self._save()
        return pnl

    def check_exit(self, symbol: str, current_price: float) -> tuple[bool, str]:
        """Returns (should_close, reason) for an open position."""
        pos = self.positions.get(symbol)
        if not pos:
            return False, ""
        unrealized = (current_price - pos.entry_price) * pos.qty
        if unrealized >= config.TAKE_PROFIT_USDT:
            return True, f"take-profit hit (+{unrealized:.2f} USDT)"
        drop_pct = (pos.entry_price - current_price) / pos.entry_price * 100
        if drop_pct >= config.STOP_LOSS_PERCENT:
            return True, f"stop-loss hit (-{drop_pct:.2f}%)"
        return False, ""

    def open_symbols(self):
        return list(self.positions.keys())
