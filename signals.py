"""
Signal Engine — combines currency strength + Renko + session filters
into a confluence score for each opportunity.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import mt5_connector as mt5c
import config


def _in_session() -> tuple[bool, bool]:
    """Returns (in_any_session, in_overlap)."""
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour

    active_sessions = []
    for session_name in config.TRADE_IN_SESSIONS:
        start, end = config.SESSIONS[session_name]
        if start <= hour < end:
            active_sessions.append(session_name)

    in_any = len(active_sessions) > 0
    in_overlap = len(active_sessions) >= 2  # London + NY overlap
    return in_any, in_overlap


def _compute_indicators(df: pd.DataFrame) -> dict:
    """Compute all technical indicators from OHLCV dataframe."""
    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]

    ema20 = EMAIndicator(close, window=20).ema_indicator()
    ema50 = EMAIndicator(close, window=50).ema_indicator()
    ema_cross = "up" if ema20.iloc[-1] > ema50.iloc[-1] else "down"
    ema_slope  = (ema20.iloc[-1] - ema20.iloc[-5]) / ema20.iloc[-5] * 100

    macd_obj  = MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_val  = macd_obj.macd().iloc[-1]
    macd_sig  = macd_obj.macd_signal().iloc[-1]
    macd_hist = macd_obj.macd_diff().iloc[-1]
    macd_dir  = "bull" if macd_hist > 0 else "bear"

    bb = BollingerBands(close, window=20, window_dev=2)
    bb_pct = bb.bollinger_pband().iloc[-1]  # 0 = lower band, 1 = upper band

    atr = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]

    # Price vs EMA (above or below trend)
    price_vs_ema = "above" if close.iloc[-1] > ema50.iloc[-1] else "below"

    return {
        "rsi":          round(rsi, 2),
        "ema_cross":    ema_cross,
        "ema_slope":    round(ema_slope, 4),
        "macd_dir":     macd_dir,
        "macd_hist":    round(macd_hist, 6),
        "bb_pct":       round(bb_pct, 3),
        "atr":          round(atr, 5),
        "price_vs_ema": price_vs_ema,
        "close":        round(close.iloc[-1], 5),
    }


def _confluence_score(direction: str, indicators: dict,
                      strength_gap: float, in_overlap: bool,
                      renko_setup: dict) -> float:
    """
    Score 0.0-1.0 based on how many factors align.
    Based on trading-signals skill: 0.7+ = high conviction.
    """
    score = 0.0
    weights = {
        "strength_gap":  0.25,
        "renko_trigger": 0.25,
        "ema":           0.15,
        "macd":          0.15,
        "rsi":           0.10,
        "session":       0.10,
    }

    # 1. Strength gap — larger = better
    if strength_gap >= 2.5:
        score += weights["strength_gap"]
    elif strength_gap >= config.MIN_STRENGTH_GAP:
        score += weights["strength_gap"] * 0.6

    # 2. Renko trigger/setup
    if renko_setup.get("trigger"):
        score += weights["renko_trigger"]
    elif renko_setup.get("in_pullback"):
        score += weights["renko_trigger"] * 0.5

    # 3. EMA alignment
    expected_ema = "up" if direction == "buy" else "down"
    if indicators["ema_cross"] == expected_ema:
        score += weights["ema"]
        if abs(indicators["ema_slope"]) > 0.02:  # Strong slope
            score += weights["ema"] * 0.3

    # 4. MACD alignment
    expected_macd = "bull" if direction == "buy" else "bear"
    if indicators["macd_dir"] == expected_macd:
        score += weights["macd"]

    # 5. RSI — not overbought/oversold against trade direction
    rsi = indicators["rsi"]
    if direction == "buy" and 40 <= rsi <= 65:
        score += weights["rsi"]
    elif direction == "sell" and 35 <= rsi <= 60:
        score += weights["rsi"]
    elif direction == "buy" and rsi < 70:
        score += weights["rsi"] * 0.5
    elif direction == "sell" and rsi > 30:
        score += weights["rsi"] * 0.5

    # 6. Session bonus
    if in_overlap:
        score += weights["session"]
    else:
        score += weights["session"] * 0.5

    return round(min(score, 1.0), 4)


def build_features(symbol: str, direction: str, strength_gap: float,
                   renko_setup: dict, in_overlap: bool) -> dict | None:
    """
    Build feature dict for the AI predictor.
    Returns None if data unavailable.
    """
    df_m15 = mt5c.get_bars(symbol, config.TF_FAST, count=100)
    df_h1  = mt5c.get_bars(symbol, config.TF_SLOW, count=100)

    if df_m15 is None or df_h1 is None:
        return None
    if len(df_m15) < 60 or len(df_h1) < 60:
        return None

    ind_m15 = _compute_indicators(df_m15)
    ind_h1  = _compute_indicators(df_h1)

    dir_bin = 1 if direction == "buy" else 0

    return {
        # Direction
        "direction":        dir_bin,
        # Strength
        "strength_gap":     abs(strength_gap),
        # M15 indicators
        "rsi_m15":          ind_m15["rsi"],
        "ema_slope_m15":    ind_m15["ema_slope"],
        "macd_hist_m15":    ind_m15["macd_hist"],
        "bb_pct_m15":       ind_m15["bb_pct"],
        "atr_m15":          ind_m15["atr"],
        "ema_aligned_m15":  1 if (direction == "buy" and ind_m15["ema_cross"] == "up")
                               or (direction == "sell" and ind_m15["ema_cross"] == "down") else 0,
        # H1 indicators
        "rsi_h1":           ind_h1["rsi"],
        "ema_slope_h1":     ind_h1["ema_slope"],
        "macd_hist_h1":     ind_h1["macd_hist"],
        "bb_pct_h1":        ind_h1["bb_pct"],
        "ema_aligned_h1":   1 if (direction == "buy" and ind_h1["ema_cross"] == "up")
                               or (direction == "sell" and ind_h1["ema_cross"] == "down") else 0,
        # Renko
        "renko_valid":      1 if renko_setup.get("valid") else 0,
        "renko_trigger":    1 if renko_setup.get("trigger") else 0,
        "renko_in_pullback":1 if renko_setup.get("in_pullback") else 0,
        "renko_pullback_n": renko_setup.get("pullback_count", 0),
        # Session
        "in_overlap":       1 if in_overlap else 0,
        # Confluence
        "confluence":       _confluence_score(
                                direction, ind_m15, strength_gap, in_overlap, renko_setup
                            ),
    }


def evaluate_opportunity(opportunity: dict, strength: dict, renko_setup: dict) -> dict | None:
    """
    Full evaluation of a single pair opportunity.
    Returns enriched opportunity dict or None if not tradeable.
    """
    symbol    = opportunity["symbol"]
    direction = opportunity["direction"]
    gap       = opportunity["gap"]

    # Session check
    in_session, in_overlap = _in_session()
    if not in_session:
        return None

    # Spread check
    spread = mt5c.get_spread_pips(symbol)
    if spread > config.MAX_SPREAD_PIPS:
        return None

    # Build features
    features = build_features(symbol, direction, gap, renko_setup, in_overlap)
    if features is None:
        return None

    confluence = features["confluence"]
    if confluence < config.MIN_CONFLUENCE_SCORE:
        return None

    return {
        **opportunity,
        "confluence":   confluence,
        "spread":       round(spread, 2),
        "in_overlap":   in_overlap,
        "features":     features,
        "renko":        renko_setup,
    }
