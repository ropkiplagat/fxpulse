"""
Correlation Filter — prevents over-exposure by blocking correlated pairs.
E.g. if already in EURUSD buy, block GBPUSD buy (both USD shorts).
Also blocks pairs that are highly correlated to open positions.
"""
import numpy as np
import pandas as pd
import mt5_connector as mt5c
import config

# Max allowed correlation (above this = block duplicate exposure)
MAX_CORRELATION = 0.75

# Pre-defined high-correlation groups (avoid holding multiple from same group)
CORRELATION_GROUPS = [
    {"EUR long":  ["EURUSD", "EURGBP", "EURJPY", "EURAUD", "EURCAD", "EURCHF"]},
    {"USD short": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]},
    {"USD long":  ["USDJPY", "USDCHF", "USDCAD"]},
    {"GBP long":  ["GBPUSD", "GBPJPY", "GBPCHF", "GBPAUD", "EURGBP"]},
    {"JPY short": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY"]},
    {"AUD long":  ["AUDUSD", "AUDJPY", "AUDCAD", "AUDNZD", "EURAUD"]},
]


def _strip(symbol: str) -> str:
    return symbol.replace(".a", "").replace(".A", "").upper()


def _compute_correlation(symbol_a: str, symbol_b: str, available: set) -> float:
    """Compute price correlation between two pairs."""
    sym_a = symbol_a if symbol_a in available else symbol_a + ".a"
    sym_b = symbol_b if symbol_b in available else symbol_b + ".a"

    df_a = mt5c.get_bars(sym_a, config.TF_FAST, count=100)
    df_b = mt5c.get_bars(sym_b, config.TF_FAST, count=100)

    if df_a is None or df_b is None:
        return 0.0

    returns_a = df_a["close"].pct_change().dropna()
    returns_b = df_b["close"].pct_change().dropna()

    min_len = min(len(returns_a), len(returns_b))
    if min_len < 20:
        return 0.0

    return float(np.corrcoef(returns_a.values[-min_len:],
                              returns_b.values[-min_len:])[0, 1])


def is_correlated_to_open(candidate_symbol: str, candidate_direction: str,
                           available: set) -> tuple[bool, str]:
    """
    Check if candidate trade is too correlated with existing open positions.
    Returns (is_blocked, reason).
    """
    open_positions = mt5c.get_open_positions()
    if not open_positions:
        return False, ""

    cand_base = _strip(candidate_symbol)

    for pos in open_positions:
        open_sym = _strip(pos.symbol)
        open_dir = "buy" if pos.type == 0 else "sell"

        if open_sym == cand_base:
            continue  # Same symbol already blocked elsewhere

        # Check static correlation groups
        for group_dict in CORRELATION_GROUPS:
            for group_name, members in group_dict.items():
                if open_sym in members and cand_base in members:
                    # Both in same correlation group
                    if open_dir == candidate_direction:
                        return True, f"Correlated with open {open_sym} {open_dir} ({group_name})"

        # Dynamic correlation check (expensive — only if group check passes)
        corr = _compute_correlation(candidate_symbol, pos.symbol, available)
        if abs(corr) > MAX_CORRELATION:
            # Same direction on positively correlated pair = duplicate risk
            if (corr > 0 and open_dir == candidate_direction) or \
               (corr < 0 and open_dir != candidate_direction):
                return True, f"Dynamic correlation {corr:.2f} with {open_sym}"

    return False, ""


def get_exposure_summary() -> dict:
    """Return current currency exposure from open positions."""
    exposure = {c: 0.0 for c in config.STRENGTH_CURRENCIES}
    positions = mt5c.get_open_positions()

    from currency_strength import PAIR_CURRENCIES
    for pos in positions:
        sym  = _strip(pos.symbol)
        pair = PAIR_CURRENCIES.get(sym)
        if not pair:
            continue
        base, quote = pair
        direction   = 1 if pos.type == 0 else -1
        lot         = pos.volume

        if base in exposure:
            exposure[base]  += direction * lot
        if quote in exposure:
            exposure[quote] -= direction * lot

    return {k: round(v, 2) for k, v in exposure.items() if v != 0}
