"""
brain.py — FXPulse v2 | Agent 2: Brain
=======================================
Does ONE thing: scans 28 pairs every 60s and writes signals.json.

Technical analysis only — no ML, no xgboost.
Indicators: RSI(14), EMA9/21 crossover, ATR(14), currency strength, regime.

GATE 5 acceptance test:
  signals.json exists and updates every 60 seconds.
"""

import os
import sys
import json
import time
import math
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
        logging.FileHandler(os.path.join(config.LOG_DIR, "brain.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("brain")

# ── MT5 ───────────────────────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_OK = True
except ImportError:
    mt5    = None
    MT5_OK = False
    log.warning("MetaTrader5 not installed — running in signal-only mode")

TF_MAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388}


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
        log.info(f"MT5 connected: {info.name} | {info.server} | Balance: {info.balance:.2f}")
    return True


def _get_candles(symbol: str, n: int = 100) -> list[dict] | None:
    """Fetch last N candles on M15. Returns list of {open,high,low,close,volume}."""
    if not MT5_OK:
        return None
    tf = mt5.TIMEFRAME_M15
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, n)
    if rates is None or len(rates) == 0:
        return None
    return [
        {"open": r["open"], "high": r["high"], "low": r["low"],
         "close": r["close"], "volume": r["tick_volume"]}
        for r in rates
    ]


# ── Pure Python Technical Indicators ─────────────────────────────────────────

def _ema(closes: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    k   = 2 / (period + 1)
    ema = [closes[0]]
    for c in closes[1:]:
        ema.append(c * k + ema[-1] * (1 - k))
    return ema


def _rsi(closes: list[float], period: int = 14) -> float:
    """RSI — returns latest value 0-100."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - (100 / (1 + rs)), 2)


def _atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range — returns latest value."""
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h  = candles[i]["high"]
        l  = candles[i]["low"]
        pc = candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return round(sum(trs[-period:]) / period, 6)


def _analyse_symbol(symbol: str, candles: list[dict]) -> dict | None:
    """Run all indicators on a symbol. Returns signal dict or None."""
    if len(candles) < 30:
        return None

    closes = [c["close"] for c in candles]
    ema9   = _ema(closes, 9)
    ema21  = _ema(closes, 21)
    rsi    = _rsi(closes, 14)
    atr    = _atr(candles, 14)

    e9_now  = ema9[-1]
    e21_now = ema21[-1]
    e9_prev = ema9[-2]
    e21_prev = ema21[-2]

    spread     = e9_now - e21_now
    cross_bull = e9_prev <= e21_prev and e9_now > e21_now   # golden cross
    cross_bear = e9_prev >= e21_prev and e9_now < e21_now   # death cross

    # Regime: trending if EMA spread > 0.5 ATR
    trending = atr > 0 and abs(spread) > (0.5 * atr)
    regime   = "trending" if trending else "ranging"

    # Direction
    if spread > 0:
        direction = "buy"
    elif spread < 0:
        direction = "sell"
    else:
        direction = "neutral"

    # Confidence — composite of RSI alignment + EMA spread strength + crossover
    conf = 0.0

    # RSI contribution (0-0.4)
    if direction == "buy" and 40 <= rsi <= 65:
        conf += 0.4
    elif direction == "buy" and rsi < 40:
        conf += 0.2   # oversold, possible reversal
    elif direction == "sell" and 35 <= rsi <= 60:
        conf += 0.4
    elif direction == "sell" and rsi > 60:
        conf += 0.2

    # EMA spread strength (0-0.3)
    if atr > 0:
        spread_ratio = min(abs(spread) / atr, 1.0)
        conf += spread_ratio * 0.3

    # Crossover bonus (0-0.3)
    if cross_bull and direction == "buy":
        conf += 0.3
    elif cross_bear and direction == "sell":
        conf += 0.3

    conf = round(min(conf, 1.0), 3)

    return {
        "symbol":    symbol,
        "direction": direction,
        "confidence": conf,
        "rsi":       rsi,
        "ema9":      round(e9_now, 6),
        "ema21":     round(e21_now, 6),
        "ema_cross": "bullish" if cross_bull else ("bearish" if cross_bear else "none"),
        "atr":       atr,
        "spread":    round(spread, 6),
        "regime":    regime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Currency Strength ─────────────────────────────────────────────────────────

def _currency_strength(all_signals: list[dict]) -> dict[str, float]:
    """
    Score each of 8 currencies by averaging confidence-weighted
    direction across all pairs it appears in.
    +1 = strong buy side, -1 = strong sell side.
    """
    scores = {c: 0.0 for c in config.CURRENCIES}
    counts = {c: 0 for c in config.CURRENCIES}

    for sig in all_signals:
        sym  = sig["symbol"]
        base = sym[:3]
        quot = sym[3:]
        conf = sig["confidence"]
        if sig["direction"] == "buy":
            score = conf
        elif sig["direction"] == "sell":
            score = -conf
        else:
            score = 0.0

        if base in scores:
            scores[base] += score
            counts[base] += 1
        if quot in scores:
            scores[quot] -= score   # Inverse for quote currency
            counts[quot] += 1

    result = {}
    for c in config.CURRENCIES:
        n = counts[c]
        result[c] = round(scores[c] / n, 3) if n > 0 else 0.0
    return result


# ── Main Scan Loop ────────────────────────────────────────────────────────────

def scan_once() -> dict:
    """Scan all 28 symbols once. Returns full signals payload."""
    log.info(f"Scanning {len(config.SYMBOLS)} symbols...")
    start      = time.time()
    all_sigs   = []
    errors     = []

    for symbol in config.SYMBOLS:
        try:
            candles = _get_candles(symbol, config.CANDLES)
            if candles is None:
                errors.append(symbol)
                continue
            sig = _analyse_symbol(symbol, candles)
            if sig:
                all_sigs.append(sig)
        except Exception as e:
            log.warning(f"{symbol} failed: {e}")
            errors.append(symbol)

    # Filter actionable signals
    actionable = [
        s for s in all_sigs
        if s["confidence"] >= config.CONFIDENCE_MIN
        and s["direction"] != "neutral"
        and s["regime"] == "trending"
    ]
    actionable.sort(key=lambda s: s["confidence"], reverse=True)

    strength = _currency_strength(all_sigs)
    elapsed  = round(time.time() - start, 2)

    payload = {
        "updated":     datetime.now(timezone.utc).isoformat(),
        "scanned":     len(all_sigs),
        "errors":      errors,
        "elapsed_sec": elapsed,
        "paper_trading": config.PAPER_TRADING,
        "signals":     actionable,
        "all_signals": all_sigs,
        "strength":    strength,
        "top_pairs":   actionable[:5],
    }

    log.info(
        f"Done in {elapsed}s — {len(all_sigs)} scanned, "
        f"{len(actionable)} actionable, {len(errors)} errors"
    )
    if actionable:
        top = actionable[0]
        log.info(f"Top signal: {top['symbol']} {top['direction'].upper()} "
                 f"conf={top['confidence']:.0%} regime={top['regime']}")

    return payload


def write_signals(payload: dict):
    """Atomically write signals.json."""
    tmp = config.SIGNALS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, config.SIGNALS_FILE)
    log.info(f"signals.json updated — {len(payload['signals'])} actionable signals")


def run():
    log.info("=" * 55)
    log.info("FXPulse v2 | Brain starting")
    log.info(f"  Symbols : {len(config.SYMBOLS)}")
    log.info(f"  Interval: {config.SCAN_INTERVAL}s")
    log.info(f"  Min conf: {config.CONFIDENCE_MIN:.0%}")
    log.info("=" * 55)

    connected = _connect_mt5()
    if not connected:
        log.warning("MT5 not connected — brain will write empty signals until MT5 is available")

    while True:
        try:
            payload = scan_once()
            write_signals(payload)
        except Exception as e:
            log.error(f"Scan failed: {e}", exc_info=True)

        time.sleep(config.SCAN_INTERVAL)


if __name__ == "__main__":
    run()
