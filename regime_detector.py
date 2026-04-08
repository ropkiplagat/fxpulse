"""
Markov Regime Detector — classifies current market state.
States: trending_up | trending_down | ranging | volatile | crisis

Based on trading-signals skill: regime determines methodology weights.
Only trade in trending regimes. Avoid ranging/crisis.
"""
import numpy as np
import pandas as pd
from ta.volatility import AverageTrueRange, BollingerBands
from ta.trend import ADXIndicator, EMAIndicator
import mt5_connector as mt5c
import config

# Regime definitions
REGIMES = {
    "trending_up":   {"trade": True,  "confidence_boost": 0.10},
    "trending_down": {"trade": True,  "confidence_boost": 0.10},
    "ranging":       {"trade": False, "confidence_boost": -0.15},
    "volatile":      {"trade": False, "confidence_boost": -0.20},
    "crisis":        {"trade": False, "confidence_boost": -0.40},
}


def detect_regime(symbol: str = "EURUSD.a") -> dict:
    """
    Classify the current market regime using ADX, ATR, Bollinger Width.
    Uses EURUSD as the reference pair (most liquid, most representative).
    """
    df = mt5c.get_bars(symbol, config.TF_SLOW, count=100)
    if df is None or len(df) < 50:
        # Default to ranging if no data
        return {"regime": "ranging", "tradeable": False, "adx": 0, "atr_pct": 0, "bb_width": 0}

    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    # ADX — trend strength (>25 = trending, <20 = ranging)
    adx_obj = ADXIndicator(high, low, close, window=14)
    adx     = adx_obj.adx().iloc[-1]
    adx_pos = adx_obj.adx_pos().iloc[-1]  # +DI
    adx_neg = adx_obj.adx_neg().iloc[-1]  # -DI

    # ATR as % of price — volatility measure
    atr     = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
    atr_pct = (atr / close.iloc[-1]) * 100

    # Bollinger Band width — squeeze = ranging, expansion = volatile/trending
    bb = BollingerBands(close, window=20, window_dev=2)
    bb_width = ((bb.bollinger_hband().iloc[-1] - bb.bollinger_lband().iloc[-1])
                / close.iloc[-1] * 100)

    # EMA trend direction
    ema20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = EMAIndicator(close, window=50).ema_indicator().iloc[-1]

    # --- Classify ---
    if atr_pct > 1.5:  # Extremely volatile (crisis/news spike)
        regime = "crisis"
    elif adx > 25 and adx_pos > adx_neg:
        regime = "trending_up"
    elif adx > 25 and adx_neg > adx_pos:
        regime = "trending_down"
    elif adx < 20 and bb_width < 0.5:
        regime = "ranging"
    elif atr_pct > 0.8:
        regime = "volatile"
    elif adx >= 20:
        regime = "trending_up" if ema20 > ema50 else "trending_down"
    else:
        regime = "ranging"

    info = REGIMES[regime]
    return {
        "regime":           regime,
        "tradeable":        info["trade"],
        "confidence_boost": info["confidence_boost"],
        "adx":              round(adx, 2),
        "atr_pct":          round(atr_pct, 4),
        "bb_width":         round(bb_width, 4),
        "ema_direction":    "up" if ema20 > ema50 else "down",
    }


def adjust_confluence_for_regime(confluence: float, regime_info: dict) -> float:
    """Apply regime boost/penalty to confluence score."""
    adjusted = confluence + regime_info.get("confidence_boost", 0)
    return round(max(0.0, min(1.0, adjusted)), 4)
