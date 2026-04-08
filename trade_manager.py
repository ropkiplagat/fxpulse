"""
Trade Manager — lot sizing, SL/TP calculation, partial close, break-even, trailing stop.
"""
import math
import MetaTrader5 as mt5
import mt5_connector as mt5c
import config


def calculate_lot_size(symbol: str, sl_distance_price: float) -> float:
    """
    Risk-based lot sizing.
    Risk = RISK_PERCENT% of account balance.
    """
    info    = mt5c.get_symbol_info(symbol)
    account = mt5c.get_account_info()

    if not info or not account or sl_distance_price <= 0:
        return 0.01

    risk_amount = (config.RISK_PERCENT / 100) * account.balance

    # Pip value per lot
    # For most pairs: pip = 0.0001, for JPY pairs: pip = 0.01
    point  = info.point
    digits = info.digits

    # Convert price distance to pips
    if digits in (3, 5):
        pip_size = point * 10
    else:
        pip_size = point * 100 if digits == 2 else point

    sl_pips = sl_distance_price / pip_size

    # Pip value for 1 standard lot
    contract_size = info.trade_contract_size  # Usually 100,000
    tick_value    = info.trade_tick_value
    tick_size     = info.trade_tick_size
    pip_value_per_lot = (pip_size / tick_size) * tick_value

    if pip_value_per_lot <= 0 or sl_pips <= 0:
        return 0.01

    lot = risk_amount / (sl_pips * pip_value_per_lot)

    # Round to broker's step
    step = info.volume_step or 0.01
    lot  = max(info.volume_min, min(info.volume_max, round(lot / step) * step))
    return round(lot, 2)


def calculate_sl_tp(symbol: str, direction: str, entry_price: float,
                    sl_distance: float) -> tuple[float, float]:
    """
    Calculate SL and TP prices from entry + distance.
    sl_distance: price distance (from renko brick calculation)
    """
    info = mt5c.get_symbol_info(symbol)
    point = info.point if info else 0.00001

    if direction == "buy":
        sl = round(entry_price - sl_distance, info.digits if info else 5)
        tp = round(entry_price + sl_distance * config.TP_R_MULTIPLE, info.digits if info else 5)
    else:
        sl = round(entry_price + sl_distance, info.digits if info else 5)
        tp = round(entry_price - sl_distance * config.TP_R_MULTIPLE, info.digits if info else 5)

    return sl, tp


def manage_open_positions():
    """
    Check all open positions managed by this bot and apply:
    - Partial close at 1R
    - Break-even at 1R
    - Renko trailing stop
    """
    from renko import get_renko_trailing_sl

    positions = mt5c.get_open_positions()
    for pos in positions:
        symbol    = pos.symbol
        ticket    = pos.ticket
        direction = "buy" if pos.type == 0 else "sell"
        entry     = pos.price_open
        current   = pos.price_current
        sl        = pos.sl
        tp        = pos.tp
        volume    = pos.volume

        if sl == 0 or tp == 0:
            continue

        sl_dist = abs(entry - sl)
        r_multiple = abs(current - entry) / sl_dist if sl_dist > 0 else 0

        info = mt5c.get_symbol_info(symbol)
        digits = info.digits if info else 5

        # --- Break-even at 1R ---
        if r_multiple >= config.BREAKEVEN_AT_R:
            if direction == "buy" and sl < entry:
                new_sl = round(entry + (sl_dist * 0.05), digits)  # Tiny buffer above entry
                result = mt5c.modify_sl(ticket, new_sl)
                if result["success"]:
                    print(f"[TM] BE set on {symbol} #{ticket}: SL → {new_sl}")

            elif direction == "sell" and sl > entry:
                new_sl = round(entry - (sl_dist * 0.05), digits)
                result = mt5c.modify_sl(ticket, new_sl)
                if result["success"]:
                    print(f"[TM] BE set on {symbol} #{ticket}: SL → {new_sl}")

        # --- Partial close at 1R (only if not already partially closed) ---
        # Track via comment — if comment contains "partial", skip
        if r_multiple >= config.BREAKEVEN_AT_R and "partial" not in (pos.comment or ""):
            partial_lot = round(volume * config.PARTIAL_CLOSE_RATIO, 2)
            info = mt5c.get_symbol_info(symbol)
            min_lot = info.volume_min if info else 0.01
            if partial_lot >= min_lot:
                result = mt5c.close_position(ticket, lot=partial_lot)
                if result["success"]:
                    print(f"[TM] Partial close {partial_lot} lots on {symbol} #{ticket}")

        # --- Renko trailing stop ---
        new_trail_sl = get_renko_trailing_sl(symbol, direction, entry)
        if new_trail_sl > 0:
            # Only move SL in favorable direction
            if direction == "buy" and new_trail_sl > sl and new_trail_sl < current:
                result = mt5c.modify_sl(ticket, round(new_trail_sl, digits))
                if result["success"]:
                    print(f"[TM] Trail SL updated {symbol} #{ticket}: {sl} → {new_trail_sl}")

            elif direction == "sell" and new_trail_sl < sl and new_trail_sl > current:
                result = mt5c.modify_sl(ticket, round(new_trail_sl, digits))
                if result["success"]:
                    print(f"[TM] Trail SL updated {symbol} #{ticket}: {sl} → {new_trail_sl}")


def check_daily_drawdown() -> bool:
    """Returns True if daily drawdown limit exceeded (halt trading)."""
    account   = mt5c.get_account_info()
    if not account:
        return False
    balance   = account.balance
    equity    = account.equity
    drawdown  = (balance - equity) / balance * 100
    if drawdown >= config.MAX_DAILY_DRAWDOWN:
        print(f"[TM] DRAWDOWN LIMIT HIT: {drawdown:.2f}% >= {config.MAX_DAILY_DRAWDOWN}%")
        return True
    return False
