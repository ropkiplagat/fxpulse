"""
MT5 Connector — handles connection, data fetching, account info
"""
import numpy.random  # must import before MetaTrader5 to prevent randbits error on Windows Server
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import config

_TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}


def connect():
    """Initialize MT5 connection with credentials from config."""
    kwargs = {}
    if config.MT5_LOGIN:
        kwargs = {
            "login":    config.MT5_LOGIN,
            "password": config.MT5_PASSWORD,
            "server":   config.MT5_SERVER,
        }
    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
    info = mt5.account_info()
    print(f"[MT5] Connected: {info.name} | {info.server} | Balance: {info.balance:.2f} {info.currency}")
    return info


def disconnect():
    mt5.shutdown()


def get_available_symbols():
    """Return symbols available on broker filtered by max spread."""
    raw = mt5.symbols_get(group="*") or []
    return {s.name for s in raw if s.spread < config.MAX_SPREAD_PIPS * 10}


def get_bars(symbol: str, timeframe: str, count: int = config.NUM_BARS) -> pd.DataFrame | None:
    """Fetch OHLCV bars and return as DataFrame."""
    tf = _TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    df.rename(columns={"open": "open", "high": "high", "low": "low",
                        "close": "close", "tick_volume": "volume"}, inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


def get_account_info():
    return mt5.account_info()


def get_symbol_info(symbol: str):
    return mt5.symbol_info(symbol)


def get_open_positions(symbol: str = None, magic: int = config.MAGIC_NUMBER):
    """Return open positions filtered by magic number."""
    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if not positions:
        return []
    return [p for p in positions if p.magic == magic]


def place_order(symbol: str, order_type: str, lot: float,
                sl: float, tp: float, comment: str = "forex-bot") -> dict:
    """
    Place a market order.
    order_type: 'buy' or 'sell'
    Returns dict with success flag and ticket number.
    """
    info = mt5.symbol_info(symbol)
    if not info:
        return {"success": False, "error": f"Symbol {symbol} not found"}

    mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)

    price = tick.ask if order_type == "buy" else tick.bid
    otype = mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL

    request = {
        "action":     mt5.TRADE_ACTION_DEAL,
        "symbol":     symbol,
        "volume":     round(lot, 2),
        "type":       otype,
        "price":      price,
        "sl":         sl,
        "tp":         tp,
        "deviation":  config.SLIPPAGE,
        "magic":      config.MAGIC_NUMBER,
        "comment":    comment,
        "type_time":  mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"success": True, "ticket": result.order, "price": result.price}
    return {"success": False, "retcode": result.retcode, "comment": result.comment}


def close_position(ticket: int, lot: float = None) -> dict:
    """Close a position (full or partial)."""
    position = mt5.positions_get(ticket=ticket)
    if not position:
        return {"success": False, "error": "Position not found"}
    pos = position[0]
    close_lot = lot if lot else pos.volume
    close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(pos.symbol)
    price = tick.bid if pos.type == 0 else tick.ask

    request = {
        "action":     mt5.TRADE_ACTION_DEAL,
        "symbol":     pos.symbol,
        "volume":     round(close_lot, 2),
        "type":       close_type,
        "position":   ticket,
        "price":      price,
        "deviation":  config.SLIPPAGE,
        "magic":      config.MAGIC_NUMBER,
        "comment":    "close",
        "type_time":  mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"success": True, "ticket": result.order}
    return {"success": False, "retcode": result.retcode, "comment": result.comment}


def modify_sl(ticket: int, new_sl: float) -> dict:
    """Modify stop loss on an open position."""
    position = mt5.positions_get(ticket=ticket)
    if not position:
        return {"success": False, "error": "Position not found"}
    pos = position[0]
    request = {
        "action":   mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol":   pos.symbol,
        "sl":       new_sl,
        "tp":       pos.tp,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"success": True}
    return {"success": False, "retcode": result.retcode, "comment": result.comment}


def get_spread_pips(symbol: str) -> float:
    """Return current spread in pips."""
    info = mt5.symbol_info(symbol)
    if not info:
        return 999.0
    tick = mt5.symbol_info_tick(symbol)
    point = info.point
    digits = info.digits
    spread = (tick.ask - tick.bid) / point
    # Convert to pips (5-digit brokers: 10 points = 1 pip)
    return spread / 10 if digits in (5, 3) else spread
