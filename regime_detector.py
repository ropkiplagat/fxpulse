"""
Five-Regime Market Detector
States: neutral | bull | bear | crash | euphoria

neutral  — ADX < 20 or mixed EMAs        -> no trades
bull     — ADX 20-35, EMA20>EMA50>EMA200 -> buy only
bear     — ADX 20-35, EMA20<EMA50<EMA200 -> sell only
crash    — ADX > 35, strong downtrend    -> no trades (overextended bear)
euphoria — ADX > 35, strong uptrend      -> no trades (overextended bull)
"""
import pandas as pd
from ta.volatility import AverageTrueRange, BollingerBands
from ta.trend import ADXIndicator, EMAIndicator
import mt5_connector as mt5c
import config

REGIMES = {
    "neutral":  {"trade": False, "direction": None,   "confidence_boost": -0.10},
    "bull":     {"trade": True,  "direction": "buy",  "confidence_boost":  0.10},
    "bear":     {"trade": True,  "direction": "sell", "confidence_boost":  0.10},
    "crash":    {"trade": False, "direction": None,   "confidence_boost": -0.30},
    "euphoria": {"trade": False, "direction": None,   "confidence_boost": -0.20},
}


def detect_regime(symbol: str = "EURUSD.a") -> dict:
    """
    Classify market into one of 5 regimes using ADX, EMA20/50/200, ATR, BB width.
    Uses EURUSD as the reference pair — most liquid and representative.
    Requires 250 bars for EMA200 to be meaningful.
    """
    df = mt5c.get_bars(symbol, config.TF_SLOW, count=250)
    if df is None or len(df) < 100:
        return {
            "regime": "neutral", "tradeable": False, "direction": None,
            "confidence": 0.3, "confidence_boost": -0.10,
            "adx": 0, "atr_pct": 0, "bb_width": 0, "ema_direction": "flat",
        }

    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    # ADX — trend strength and direction
    adx_obj = ADXIndicator(high, low, close, window=14)
    adx     = adx_obj.adx().iloc[-1]
    adx_pos = adx_obj.adx_pos().iloc[-1]  # +DI (bulls)
    adx_neg = adx_obj.adx_neg().iloc[-1]  # -DI (bears)

    # ATR as % of price
    atr     = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
    atr_pct = (atr / close.iloc[-1]) * 100

    # Bollinger Band width — squeeze detection
    bb       = BollingerBands(close, window=20, window_dev=2)
    bb_width = ((bb.bollinger_hband().iloc[-1] - bb.bollinger_lband().iloc[-1])
                / close.iloc[-1] * 100)

    # EMAs — trend structure
    price  = close.iloc[-1]
    ema20  = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50  = EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = EMAIndicator(close, window=200).ema_indicator().iloc[-1]

    # ── Five-regime classification ────────────────────────────────────────
    if adx > 35 and adx_neg > adx_pos and price < ema200:
        regime = "crash"
    elif adx > 35 and adx_pos > adx_neg and price > ema200:
        regime = "euphoria"
    elif adx >= 20 and ema20 > ema50 and ema50 > ema200:
        regime = "bull"
    elif adx >= 20 and ema20 < ema50 and ema50 < ema200:
        regime = "bear"
    else:
        regime = "neutral"

    # Confidence — how strongly we're in this regime (0.0–1.0)
    if regime in ("bull", "bear"):
        confidence = round(min(1.0, (adx - 20) / 20), 4)   # 0.0 at ADX=20, 1.0 at ADX=40
    elif regime in ("crash", "euphoria"):
        confidence = round(min(1.0, (adx - 35) / 15), 4)
    else:
        confidence = round(max(0.0, 1.0 - adx / 20), 4)    # Higher confidence when more flat

    info = REGIMES[regime]
    return {
        "regime":           regime,
        "tradeable":        info["trade"],
        "direction":        info["direction"],
        "confidence":       confidence,
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
