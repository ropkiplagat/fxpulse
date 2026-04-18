"""
executor.py — FXPulse v2 | Agent 3: Executor
=============================================
Does ONE thing: reads signals.json every 60s and places/closes trades.

Rules:
  - Only trades signals with confidence >= CONFIDENCE_MIN and regime=trending
  - Max 1 open trade per symbol at a time
  - Risk: 1% of balance per trade, sized by ATR
  - Paper trading by default (config.PAPER_TRADING = True)
  - Closes trade when signal flips direction or confidence drops below threshold

GATE 9 acceptance test:
  In paper mode: logs "PAPER BUY/SELL" lines. No real orders placed.
  In live mode: real MT5 order placed and ticket logged.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

import config

os.makedirs("data", exist_ok=True)
os.makedirs(config.LOG_DIR, exist_ok=True)

# ── Logger ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_DIR, "executor.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("executor")

# ── MT5 ───────────────────────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_OK = True
except ImportError:
    mt5    = None
    MT5_OK = False
    log.warning("MetaTrader5 not installed — executor running in paper mode only")


def _connect_mt5() -> bool:
    if not MT5_OK:
        return False
    if not mt5.initialize():
        log.error(f"MT5 init failed: {mt5.last_error()}")
        return False
    if config.MT5_LOGIN:
        ok = mt5.login(config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER)
        if not ok:
            log.error(f"MT5 login failed: {mt5.last_error()}")
            return False
    info = mt5.account_info()
    if info:
        log.info(f"[EXEC] MT5 connected: {info.name} | Balance: {info.balance:.2f}")
    return True


# ── Signals ───────────────────────────────────────────────────────────────────

def _load_signals() -> dict | None:
    if not os.path.exists(config.SIGNALS_FILE):
        return None
    try:
        with open(config.SIGNALS_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"[EXEC] Failed to read signals.json: {e}")
        return None


def _signals_age_seconds(payload: dict) -> float:
    try:
        updated = datetime.fromisoformat(payload["updated"])
        now     = datetime.now(timezone.utc)
        return (now - updated).total_seconds()
    except Exception:
        return 9999.0


# ── Position sizing ───────────────────────────────────────────────────────────

def _lot_size(symbol: str, atr: float, balance: float) -> float:
    """
    Risk 1% of balance per trade.
    Stop = 1.5 * ATR. Lot = risk_amount / (stop_pips * pip_value).
    Returns a safe minimum of 0.01 lots.
    """
    risk_amount = balance * 0.01
    stop        = 1.5 * atr if atr > 0 else 0.001

    if not MT5_OK:
        return 0.01

    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.01

    # pip value = contract_size * point / leverage (approx)
    pip_value = info.trade_contract_size * info.point
    if pip_value <= 0:
        return 0.01

    lot = risk_amount / (stop / info.point * pip_value)
    lot = max(0.01, min(round(lot, 2), 5.0))   # clamp 0.01 – 5.0
    return lot


# ── Open positions tracking ───────────────────────────────────────────────────

def _open_positions() -> dict[str, dict]:
    """Returns {symbol: position_info} for all open trades."""
    if not MT5_OK:
        return {}
    positions = mt5.positions_get()
    if positions is None:
        return {}
    return {p.symbol: {"ticket": p.ticket, "type": p.type, "volume": p.volume} for p in positions}


def _close_position(ticket: int, symbol: str, lot: float, pos_type: int) -> bool:
    """Close a position by ticket."""
    if not MT5_OK or config.PAPER_TRADING:
        log.info(f"[EXEC] PAPER CLOSE {symbol} ticket={ticket}")
        return True

    info  = mt5.symbol_info_tick(symbol)
    price = info.bid if pos_type == mt5.ORDER_TYPE_BUY else info.ask

    req = {
        "action":   mt5.TRADE_ACTION_DEAL,
        "symbol":   symbol,
        "volume":   lot,
        "type":     mt5.ORDER_TYPE_SELL if pos_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": ticket,
        "price":    price,
        "deviation": 20,
        "magic":    202600,
        "comment":  "fxpulse_v2_close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(req)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(f"[EXEC] CLOSED {symbol} ticket={ticket}")
        return True
    log.error(f"[EXEC] Close failed {symbol}: {result}")
    return False


def _place_order(signal: dict, balance: float) -> bool:
    """Place a new order for a signal."""
    symbol    = signal["symbol"]
    direction = signal["direction"]
    atr       = signal["atr"]
    conf      = signal["confidence"]
    lot       = _lot_size(symbol, atr, balance)

    if config.PAPER_TRADING or not MT5_OK:
        log.info(f"[EXEC] PAPER {direction.upper()} {symbol} lot={lot} conf={conf:.0%} atr={atr:.6f}")
        return True

    info  = mt5.symbol_info_tick(symbol)
    if info is None:
        log.error(f"[EXEC] No tick for {symbol}")
        return False

    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    price      = info.ask if direction == "buy" else info.bid
    sl         = price - 1.5 * atr if direction == "buy" else price + 1.5 * atr
    tp         = price + 2.0 * atr if direction == "buy" else price - 2.0 * atr

    req = {
        "action":   mt5.TRADE_ACTION_DEAL,
        "symbol":   symbol,
        "volume":   lot,
        "type":     order_type,
        "price":    price,
        "sl":       round(sl, 6),
        "tp":       round(tp, 6),
        "deviation": 20,
        "magic":    202600,
        "comment":  "fxpulse_v2",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(req)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(f"[EXEC] LIVE {direction.upper()} {symbol} ticket={result.order} lot={lot} price={price:.5f}")
        return True
    log.error(f"[EXEC] Order failed {symbol}: {result}")
    return False


# ── Main execution loop ───────────────────────────────────────────────────────

def execute_once(connected: bool):
    payload = _load_signals()
    if payload is None:
        log.warning("[EXEC] signals.json not found — waiting for brain.py")
        return

    age = _signals_age_seconds(payload)
    if age > 180:
        log.warning(f"[EXEC] signals.json is {age:.0f}s old — brain may be down")
        return

    signals   = payload.get("signals", [])
    balance   = 50000.0  # paper default

    if connected and MT5_OK:
        info    = mt5.account_info()
        balance = info.balance if info else balance

    open_pos = _open_positions() if connected else {}

    log.info(f"[EXEC] {len(signals)} actionable signals | {len(open_pos)} open positions | balance={balance:.2f}")

    # Close positions where signal has flipped or gone neutral
    for symbol, pos in open_pos.items():
        matching = next((s for s in signals if s["symbol"] == symbol), None)
        pos_dir  = "buy" if pos["type"] == 0 else "sell"
        if matching is None or matching["direction"] != pos_dir:
            log.info(f"[EXEC] Signal flipped for {symbol} — closing")
            _close_position(pos["ticket"], symbol, pos["volume"], pos["type"])

    # Open new positions for top signals not already open
    for sig in signals[:3]:   # max 3 concurrent trades
        symbol = sig["symbol"]
        if symbol not in open_pos:
            _place_order(sig, balance)


def run():
    log.info("=" * 55)
    log.info("FXPulse v2 | Executor starting")
    log.info(f"  Paper trading : {config.PAPER_TRADING}")
    log.info(f"  Min confidence: {config.CONFIDENCE_MIN:.0%}")
    log.info("=" * 55)

    connected = _connect_mt5()
    if not connected:
        log.warning("[EXEC] MT5 not connected — paper mode only")

    while True:
        try:
            execute_once(connected)
        except Exception as e:
            log.error(f"[EXEC] Cycle failed: {e}", exc_info=True)

        time.sleep(config.SCAN_INTERVAL)


if __name__ == "__main__":
    run()
