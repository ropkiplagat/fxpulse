"""
Renko Simulation — built from M1 OHLCV data.
Detects: trend direction, pullback depth, continuation trigger.
"""
import numpy as np
import pandas as pd
from ta.volatility import AverageTrueRange
import mt5_connector as mt5c
import config


def _calculate_brick_size(df_m1: pd.DataFrame) -> float:
    """Dynamic brick size = ATR(14) * multiplier."""
    atr = AverageTrueRange(
        high=df_m1["high"], low=df_m1["low"], close=df_m1["close"],
        window=config.RENKO_BRICK_ATR_PERIOD
    ).average_true_range().iloc[-1]
    return atr * config.RENKO_BRICK_MULTIPLIER


def build_renko(df_m1: pd.DataFrame, brick_size: float = None) -> pd.DataFrame:
    """
    Convert M1 OHLCV to Renko bricks.
    Returns DataFrame with columns: [open, close, direction, brick_num]
    direction: 1 = up brick, -1 = down brick
    """
    if brick_size is None:
        brick_size = _calculate_brick_size(df_m1)
        if brick_size <= 0:
            return pd.DataFrame()

    closes = df_m1["close"].values
    bricks = []
    current_price = closes[0]
    last_brick_close = round(current_price / brick_size) * brick_size

    for price in closes[1:]:
        while price >= last_brick_close + brick_size:
            brick_open  = last_brick_close
            brick_close = last_brick_close + brick_size
            bricks.append({"open": brick_open, "close": brick_close, "direction": 1})
            last_brick_close = brick_close
        while price <= last_brick_close - brick_size:
            brick_open  = last_brick_close
            brick_close = last_brick_close - brick_size
            bricks.append({"open": brick_open, "close": brick_close, "direction": -1})
            last_brick_close = brick_close

    if not bricks:
        return pd.DataFrame()

    df = pd.DataFrame(bricks)
    df["brick_num"] = range(1, len(df) + 1)
    return df


def analyze_renko(symbol: str) -> dict:
    """
    Full Renko analysis for a symbol.
    Returns setup dict with: trend, pullback_count, trigger, brick_size, sl_distance
    """
    # Fetch M1 data (more bars = more Renko bricks)
    df_m1 = mt5c.get_bars(symbol, config.RENKO_TF, count=500)
    if df_m1 is None or len(df_m1) < 100:
        return {"valid": False, "reason": "insufficient M1 data"}

    brick_size = _calculate_brick_size(df_m1)
    renko = build_renko(df_m1, brick_size)

    if len(renko) < 10:
        return {"valid": False, "reason": "not enough Renko bricks formed"}

    # Determine trend direction from last 10 bricks
    last_10 = renko.tail(10)
    up_count   = (last_10["direction"] == 1).sum()
    down_count = (last_10["direction"] == -1).sum()

    if up_count > down_count:
        trend = "up"
    elif down_count > up_count:
        trend = "down"
    else:
        return {"valid": False, "reason": "no clear trend"}

    # Count pullback bricks (counter-trend at the end)
    bricks = renko["direction"].values
    pullback_count = 0
    pullback_direction = -1 if trend == "up" else 1

    # Walk backwards from last brick
    for i in range(len(bricks) - 1, -1, -1):
        if bricks[i] == pullback_direction:
            pullback_count += 1
        else:
            break

    # Check for valid continuation trigger
    # Trigger: last brick resumed the trend after a pullback
    trigger = False
    if (config.PULLBACK_MIN_BRICKS <= pullback_count <= config.PULLBACK_MAX_BRICKS):
        # Last brick was trend direction (pullback ended)
        if len(bricks) >= 2 and bricks[-1] != pullback_direction:
            # The brick before last was counter-trend (pullback)
            if bricks[-2] == pullback_direction:
                trigger = True

    # Check if we're IN a pullback (waiting for trigger)
    in_pullback = (
        config.PULLBACK_MIN_BRICKS <= pullback_count <= config.PULLBACK_MAX_BRICKS
        and bricks[-1] == pullback_direction
    )

    # SL distance = 2-3 bricks beyond pullback extreme
    sl_bricks    = pullback_count + 2
    sl_distance  = sl_bricks * brick_size

    # TP distance = 2R (2x SL distance from entry)
    tp_distance  = sl_distance * config.TP_R_MULTIPLE

    return {
        "valid":          True,
        "trend":          trend,
        "pullback_count": pullback_count,
        "in_pullback":    in_pullback,
        "trigger":        trigger,
        "brick_size":     round(brick_size, 5),
        "sl_distance":    round(sl_distance, 5),
        "tp_distance":    round(tp_distance, 5),
        "total_bricks":   len(renko),
        "last_brick_dir": int(bricks[-1]) if len(bricks) > 0 else 0,
    }


def get_renko_trailing_sl(symbol: str, direction: str, entry_price: float) -> float:
    """
    Calculate trailing SL based on current Renko bricks.
    Trails N bricks from the latest extreme.
    """
    df_m1 = mt5c.get_bars(symbol, config.RENKO_TF, count=300)
    if df_m1 is None:
        return 0.0

    brick_size = _calculate_brick_size(df_m1)
    renko = build_renko(df_m1, brick_size)

    if len(renko) < 5:
        return 0.0

    trail_distance = config.TRAILING_BRICKS * brick_size

    if direction == "buy":
        # Trail below the highest close reached
        max_close = renko[renko["direction"] == 1]["close"].max()
        return round(max_close - trail_distance, 5)
    else:
        min_close = renko[renko["direction"] == -1]["close"].min()
        return round(min_close + trail_distance, 5)
