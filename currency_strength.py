"""
Currency Strength Engine
Calculates strength score for 8 currencies across M15 + H1 timeframes.
Method: momentum-based scoring using EMA slopes and price change rates.
"""
import numpy as np
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
import mt5_connector as mt5c
import config

# Pair-to-currency mapping
PAIR_CURRENCIES = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"), "USDCHF": ("USD", "CHF"),
    "USDCAD": ("USD", "CAD"), "AUDUSD": ("AUD", "USD"),
    "NZDUSD": ("NZD", "USD"), "EURGBP": ("EUR", "GBP"),
    "EURJPY": ("EUR", "JPY"), "GBPJPY": ("GBP", "JPY"),
    "AUDJPY": ("AUD", "JPY"), "CADJPY": ("CAD", "JPY"),
    "GBPCHF": ("GBP", "CHF"), "EURAUD": ("EUR", "AUD"),
    "NZDJPY": ("NZD", "JPY"), "CHFJPY": ("CHF", "JPY"),
    "EURCAD": ("EUR", "CAD"), "GBPAUD": ("GBP", "AUD"),
    "AUDCAD": ("AUD", "CAD"), "AUDNZD": ("AUD", "NZD"),
    # Gold — XAU strength vs USD
    "XAUUSD": ("XAU", "USD"),
}


def _strip_suffix(symbol: str) -> str:
    """Remove .a or other broker suffixes."""
    return symbol.replace(".a", "").replace(".A", "").upper()


def _score_pair(df: pd.DataFrame, timeframe_weight: float) -> float:
    """
    Compute a single directional score for a pair from its OHLCV data.
    Positive = base currency strong. Negative = base currency weak.
    """
    close = df["close"]
    if len(close) < 30:
        return 0.0

    # EMA slope (20 vs 50 — direction)
    ema20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema_slope = (ema20 - ema50) / ema50 * 100

    # RSI deviation from neutral (50)
    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    rsi_score = (rsi - 50) / 50  # -1 to +1

    # Price rate of change (last 10 bars)
    roc = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100

    # Weighted composite
    score = (ema_slope * 0.4 + rsi_score * 0.3 + roc * 0.3) * timeframe_weight
    return score


def calculate_strength(available_symbols: set) -> dict:
    """
    Returns dict: { 'USD': {'score': 2.3, 'rank': 1, 'slope': 'up'}, ... }
    Fetches M15 + H1 data for all cross pairs.
    """
    raw_scores = {c: 0.0 for c in config.STRENGTH_CURRENCIES}
    pair_counts = {c: 0 for c in config.STRENGTH_CURRENCIES}

    tf_configs = [
        (config.TF_FAST, 0.6),   # M15 — more weight (recent momentum)
        (config.TF_SLOW, 0.4),   # H1  — trend direction
    ]

    for timeframe, tf_weight in tf_configs:
        for base_pair, (base_cur, quote_cur) in PAIR_CURRENCIES.items():
            if base_cur not in config.STRENGTH_CURRENCIES:
                continue
            if quote_cur not in config.STRENGTH_CURRENCIES:
                continue

            # Try both plain and .a suffix
            symbol = None
            for candidate in [base_pair + ".a", base_pair, base_pair.lower() + ".a"]:
                if candidate in available_symbols:
                    symbol = candidate
                    break
            if symbol is None:
                continue

            df = mt5c.get_bars(symbol, timeframe, count=100)
            if df is None or len(df) < 50:
                continue

            pair_score = _score_pair(df, tf_weight)

            raw_scores[base_cur]  += pair_score
            raw_scores[quote_cur] -= pair_score
            pair_counts[base_cur]  += 1
            pair_counts[quote_cur] += 1

    # Normalize by pair count
    normalized = {}
    for cur in config.STRENGTH_CURRENCIES:
        count = pair_counts[cur] or 1
        normalized[cur] = raw_scores[cur] / count

    # Rank currencies (1 = strongest)
    sorted_currencies = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    ranks = {cur: i + 1 for i, (cur, _) in enumerate(sorted_currencies)}

    result = {}
    for cur, score in normalized.items():
        slope = "up" if score > 0.05 else "down" if score < -0.05 else "flat"
        result[cur] = {
            "score": round(score, 4),
            "rank":  ranks[cur],
            "slope": slope,
        }

    return result


def get_strength_gap(strength: dict, base: str, quote: str) -> float:
    """Return strength difference between two currencies."""
    return strength[base]["score"] - strength[quote]["score"]


def detect_crossover(prev_strength: dict, curr_strength: dict) -> list:
    """
    Detect when one currency crosses another in strength ranking.
    Returns list of (currency_a, currency_b, direction) tuples.
    """
    if not prev_strength:
        return []

    crossovers = []
    currencies = config.STRENGTH_CURRENCIES

    for i, c1 in enumerate(currencies):
        for c2 in currencies[i+1:]:
            prev_diff = prev_strength[c1]["score"] - prev_strength[c2]["score"]
            curr_diff = curr_strength[c1]["score"] - curr_strength[c2]["score"]

            # Crossover detected
            if prev_diff < 0 and curr_diff > 0:
                # c1 crossed above c2
                if abs(curr_diff) > 0.1:  # Filter weak crossovers
                    crossovers.append((c1, c2, "c1_above"))
            elif prev_diff > 0 and curr_diff < 0:
                # c2 crossed above c1
                if abs(curr_diff) > 0.1:
                    crossovers.append((c1, c2, "c2_above"))

    return crossovers


def get_top_pairs(strength: dict, available_symbols: set) -> list:
    """
    Generate top N pair opportunities based on strength gap.
    Returns list of dicts sorted by opportunity score.
    """
    opportunities = []

    for base_pair, (base_cur, quote_cur) in PAIR_CURRENCIES.items():
        if base_cur not in strength or quote_cur not in strength:
            continue

        # Check symbol available — Gold uses wider spread tolerance
        symbol = None
        for candidate in [base_pair + ".a", base_pair]:
            if candidate in available_symbols:
                symbol = candidate
                break
        if not symbol:
            continue

        gap = get_strength_gap(strength, base_cur, quote_cur)
        abs_gap = abs(gap)

        if abs_gap < config.MIN_STRENGTH_GAP:
            continue

        direction = "buy" if gap > 0 else "sell"
        base_rank  = strength[base_cur]["rank"]
        quote_rank = strength[quote_cur]["rank"]

        # Score: stronger gap + both currencies have momentum (not flat)
        momentum_bonus = 0.0
        if strength[base_cur]["slope"] != "flat":
            momentum_bonus += 0.2
        if strength[quote_cur]["slope"] != "flat":
            momentum_bonus += 0.2

        # Rank bonus: top vs bottom is best setup
        rank_gap = abs(base_rank - quote_rank)
        rank_score = rank_gap / len(config.STRENGTH_CURRENCIES)

        opportunity_score = abs_gap * (1 + momentum_bonus + rank_score * 0.3)

        opportunities.append({
            "symbol":    symbol,
            "direction": direction,
            "base":      base_cur,
            "quote":     quote_cur,
            "gap":       round(gap, 4),
            "score":     round(opportunity_score, 4),
            "base_rank": base_rank,
            "quote_rank": quote_rank,
        })

    opportunities.sort(key=lambda x: x["score"], reverse=True)
    return opportunities[:config.TOP_PAIRS_COUNT]
