"""
Paper Trading Mode — simulates trades without real money.
Tracks virtual positions, P&L, and win rate identically to live mode.
Switch between paper and live via config.PAPER_TRADING = True/False.

Why this matters: validate the strategy for 2-4 weeks before going live.
Gives the friend/client a risk-free way to see the bot work.
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
import config

PAPER_STATE_FILE = "logs/paper_positions.json"
PAPER_HISTORY_FILE = "logs/paper_history.json"


def _load(path: str, default) -> dict | list:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, default=str, indent=2)


class PaperTrader:
    """
    Drop-in replacement for mt5_connector order functions when PAPER_TRADING=True.
    Uses same interface as live trading so main.py doesn't change.
    """
    def __init__(self, starting_balance: float = 10_000.0):
        self.balance  = starting_balance
        self.equity   = starting_balance
        self.positions: list[dict] = _load(PAPER_STATE_FILE, [])
        self.history:   list[dict] = _load(PAPER_HISTORY_FILE, [])
        self._restore_balance()

    def _restore_balance(self):
        """Restore balance from history on restart."""
        if self.history:
            last = self.history[-1]
            self.balance = last.get("balance_after", self.balance)

    # ── Order Placement ──────────────────────────────────────────────
    def place_order(self, symbol: str, direction: str, lot: float,
                    sl: float, tp: float, comment: str = "") -> dict:
        import mt5_connector as mt5c
        tick = mt5c.get_symbol_info(symbol)
        if not tick:
            return {"success": False, "error": "Symbol not found"}

        import MetaTrader5 as mt5
        mt5.symbol_select(symbol, True)
        tick_data   = mt5.symbol_info_tick(symbol)
        entry_price = tick_data.ask if direction == "buy" else tick_data.bid

        ticket = str(uuid.uuid4())[:8].upper()
        pos = {
            "ticket":    ticket,
            "symbol":    symbol,
            "direction": direction,
            "lot":       lot,
            "entry":     entry_price,
            "sl":        sl,
            "tp":        tp,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "comment":   comment,
            "magic":     config.MAGIC_NUMBER,
            "partial_closed": False,
        }
        self.positions.append(pos)
        _save(PAPER_STATE_FILE, self.positions)
        print(f"[PAPER] BUY/SELL simulated: {direction.upper()} {symbol} @ {entry_price:.5f} | Ticket: {ticket}")
        return {"success": True, "ticket": ticket, "price": entry_price}

    def close_position(self, ticket: str, lot: float = None) -> dict:
        pos = next((p for p in self.positions if str(p["ticket"]) == str(ticket)), None)
        if not pos:
            return {"success": False, "error": "Position not found"}

        import MetaTrader5 as mt5
        mt5.symbol_select(pos["symbol"], True)
        tick_data   = mt5.symbol_info_tick(pos["symbol"])
        close_price = tick_data.bid if pos["direction"] == "buy" else tick_data.ask

        close_lot = lot if lot else pos["lot"]
        pnl       = self._calc_pnl(pos, close_price, close_lot)
        self.balance += pnl
        outcome = "win" if pnl > 0 else "loss"

        record = {
            **pos,
            "close_price": close_price,
            "close_lot":   close_lot,
            "pnl":         round(pnl, 2),
            "outcome":     outcome,
            "closed_at":   datetime.now(timezone.utc).isoformat(),
            "balance_after": round(self.balance, 2),
        }
        self.history.append(record)
        self.positions = [p for p in self.positions if str(p["ticket"]) != str(ticket)]
        _save(PAPER_STATE_FILE, self.positions)
        _save(PAPER_HISTORY_FILE, self.history)
        print(f"[PAPER] Closed {pos['symbol']} #{ticket}: {outcome} | P&L: {pnl:+.2f} | Bal: {self.balance:.2f}")
        return {"success": True, "ticket": ticket}

    def modify_sl(self, ticket: str, new_sl: float) -> dict:
        for pos in self.positions:
            if str(pos["ticket"]) == str(ticket):
                pos["sl"] = new_sl
                _save(PAPER_STATE_FILE, self.positions)
                return {"success": True}
        return {"success": False, "error": "Position not found"}

    # ── Position Monitoring ──────────────────────────────────────────
    def check_hits(self):
        """
        Check if any paper positions have hit SL or TP.
        Call this every loop iteration.
        """
        import MetaTrader5 as mt5
        to_close = []
        for pos in self.positions:
            mt5.symbol_select(pos["symbol"], True)
            tick  = mt5.symbol_info_tick(pos["symbol"])
            price = tick.bid if pos["direction"] == "buy" else tick.ask

            if pos["direction"] == "buy":
                if price <= pos["sl"]:
                    to_close.append((pos["ticket"], "sl"))
                elif price >= pos["tp"]:
                    to_close.append((pos["ticket"], "tp"))
            else:
                if price >= pos["sl"]:
                    to_close.append((pos["ticket"], "sl"))
                elif price <= pos["tp"]:
                    to_close.append((pos["ticket"], "tp"))

        for ticket, reason in to_close:
            print(f"[PAPER] {reason.upper()} hit on #{ticket}")
            self.close_position(ticket)

    def update_equity(self):
        """Recalculate equity from open unrealized P&L."""
        import MetaTrader5 as mt5
        unrealized = 0.0
        for pos in self.positions:
            mt5.symbol_select(pos["symbol"], True)
            tick  = mt5.symbol_info_tick(pos["symbol"])
            price = tick.bid if pos["direction"] == "buy" else tick.ask
            unrealized += self._calc_pnl(pos, price, pos["lot"])
        self.equity = self.balance + unrealized
        return self.equity

    def get_open_positions(self, symbol: str = None) -> list:
        if symbol:
            return [p for p in self.positions if p["symbol"] == symbol]
        return self.positions

    def get_summary(self) -> dict:
        closed = self.history
        total  = len(closed)
        wins   = sum(1 for t in closed if t.get("outcome") == "win")
        losses = total - wins
        pnl    = sum(t.get("pnl", 0) for t in closed)
        return {
            "total":     total,
            "wins":      wins,
            "losses":    losses,
            "win_rate":  wins / total if total > 0 else 0.0,
            "total_pnl": round(pnl, 2),
            "balance":   round(self.balance, 2),
            "equity":    round(self.update_equity(), 2),
            "mode":      "PAPER",
        }

    # ── Internal ─────────────────────────────────────────────────────
    def _calc_pnl(self, pos: dict, close_price: float, lot: float) -> float:
        import mt5_connector as mt5c
        info = mt5c.get_symbol_info(pos["symbol"])
        if not info:
            return 0.0

        point     = info.point
        digits    = info.digits
        pip_size  = point * 10 if digits in (3, 5) else point
        tick_val  = info.trade_tick_value
        tick_size = info.trade_tick_size
        pip_val   = (pip_size / tick_size) * tick_val if tick_size > 0 else 1.0

        price_diff = close_price - pos["entry"]
        if pos["direction"] == "sell":
            price_diff = -price_diff

        pips = price_diff / pip_size
        return round(pips * pip_val * lot, 2)


# Singleton instance (used when PAPER_TRADING=True)
_paper_instance: Optional[PaperTrader] = None


def get_paper_trader() -> PaperTrader:
    global _paper_instance
    if _paper_instance is None:
        starting_bal = getattr(config, "PAPER_STARTING_BALANCE", 10_000.0)
        _paper_instance = PaperTrader(starting_balance=starting_bal)
    return _paper_instance
