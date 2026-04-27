"""
Phase 1 — Strength Gap Distribution Analysis
Pulls 30 days M15+H1 from live MT5, simulates currency_strength.py over
rolling 100-bar windows (sampled every 4 M15 bars = hourly), outputs
gap distribution for the 5 traded pairs.

Run on VPS: C:\fxpulse\venv\Scripts\python.exe C:\fxpulse\analysis_strength_gap.py
Output:     C:\fxpulse\analysis\strength_gap_distribution_27apr2026.md
"""
import sys, os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Must be on VPS where MT5 is installed
try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 not available — run this on the VPS.")
    sys.exit(1)

from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

# ── Config (inline — avoids importing config.py which needs .env) ────────────
ALL_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "XAU"]

PAIR_CURRENCIES = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"), "USDCHF": ("USD", "CHF"),
    "USDCAD": ("USD", "CAD"), "AUDUSD": ("AUD", "USD"),
    "NZDUSD": ("NZD", "USD"), "EURGBP": ("EUR", "GBP"),
    "EURJPY": ("EUR", "JPY"), "GBPJPY": ("GBP", "JPY"),
    "AUDJPY": ("AUD", "JPY"), "CADJPY": ("CAD", "JPY"),
    "GBPCHF": ("GBP", "CHF"), "EURAUD": ("EUR", "AUD"),
}

TRADED_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
PAIR_TO_CCY  = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"), "AUDUSD": ("AUD", "USD"),
    "USDCAD": ("USD", "CAD"),
}

WINDOW       = 100   # bars per calculation window (matches live bot)
STEP         = 4     # sample every 4 M15 bars (= hourly resolution)
HISTORY_DAYS = 30

OUTPUT_DIR  = Path(r"C:\fxpulse\analysis")
OUTPUT_FILE = OUTPUT_DIR / "strength_gap_distribution_27apr2026.md"


# ── Replicate _score_pair() on a numpy close array ──────────────────────────
def _score_pair_np(close_arr: np.ndarray, tf_weight: float) -> float:
    if len(close_arr) < 30:
        return 0.0
    close = pd.Series(close_arr.astype(float))
    ema20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    if ema50 == 0:
        return 0.0
    ema_slope  = (ema20 - ema50) / ema50 * 100
    rsi        = RSIIndicator(close, window=14).rsi().iloc[-1]
    rsi_score  = (rsi - 50) / 50
    roc        = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100 if close.iloc[-10] != 0 else 0.0
    return float((ema_slope * 0.4 + rsi_score * 0.3 + roc * 0.3) * tf_weight)


# ── Compute strength dict for one snapshot ───────────────────────────────────
def _strength_at(m15: dict, h1: dict, idx_m15: int) -> dict:
    raw    = {c: 0.0 for c in ALL_CURRENCIES}
    counts = {c: 0   for c in ALL_CURRENCIES}
    idx_h1 = max(0, idx_m15 // 4)

    for pair, (base, quote) in PAIR_CURRENCIES.items():
        if base not in ALL_CURRENCIES or quote not in ALL_CURRENCIES:
            continue

        if pair in m15 and idx_m15 >= WINDOW:
            window = m15[pair][idx_m15 - WINDOW : idx_m15]
            if len(window) == WINDOW:
                s = _score_pair_np(window, 0.6)
                raw[base] += s;  raw[quote] -= s
                counts[base] += 1; counts[quote] += 1

        if pair in h1 and idx_h1 >= WINDOW:
            window = h1[pair][idx_h1 - WINDOW : idx_h1]
            if len(window) == WINDOW:
                s = _score_pair_np(window, 0.4)
                raw[base] += s;  raw[quote] -= s
                counts[base] += 1; counts[quote] += 1

    return {c: raw[c] / (counts[c] or 1) for c in ALL_CURRENCIES}


# ── Pull MT5 historical bars ─────────────────────────────────────────────────
def _pull(sym_candidates: list, tf: int, start: datetime, end: datetime):
    for sym in sym_candidates:
        rates = mt5.copy_rates_range(sym, tf, start, end)
        if rates is not None and len(rates) > WINDOW:
            return rates["close"]
    return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    print("MT5 connected.")

    end_dt   = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=HISTORY_DAYS)

    TF_M15 = mt5.TIMEFRAME_M15
    TF_H1  = mt5.TIMEFRAME_H1

    m15_data: dict[str, np.ndarray] = {}
    h1_data:  dict[str, np.ndarray] = {}

    print(f"Pulling {HISTORY_DAYS}-day history ({start_dt.date()} → {end_dt.date()}) …")
    for pair in PAIR_CURRENCIES:
        candidates = [pair + ".a", pair]
        c = _pull(candidates, TF_M15, start_dt, end_dt)
        if c is not None:
            m15_data[pair] = c
            print(f"  M15 {pair}: {len(c)} bars")
        c = _pull(candidates, TF_H1, start_dt, end_dt)
        if c is not None:
            h1_data[pair] = c

    if not m15_data:
        print("No M15 data returned — is MT5 terminal logged in?")
        mt5.shutdown(); sys.exit(1)

    # Use EURUSD or first available traded pair as length reference
    ref = next((p for p in TRADED_PAIRS if p in m15_data), next(iter(m15_data)))
    n_m15 = len(m15_data[ref])
    n_snapshots = (n_m15 - WINDOW) // STEP
    print(f"\nReference pair: {ref} | {n_m15} M15 bars | {n_snapshots} snapshots (step={STEP})\n")

    # ── Rolling analysis ─────────────────────────────────────────────────────
    gaps: dict[str, list] = {p: [] for p in TRADED_PAIRS}

    for i, idx in enumerate(range(WINDOW, n_m15, STEP)):
        if i % 200 == 0:
            print(f"  Processing snapshot {i}/{n_snapshots} …", flush=True)

        strength = _strength_at(m15_data, h1_data, idx)
        for pair in TRADED_PAIRS:
            base, quote = PAIR_TO_CCY[pair]
            gaps[pair].append(abs(strength[base] - strength[quote]))

    mt5.shutdown()
    print("MT5 disconnected.")

    all_gaps = np.array([g for v in gaps.values() for g in v])
    if len(all_gaps) == 0:
        print("No gap observations — aborting.")
        sys.exit(1)

    # ── Statistics ───────────────────────────────────────────────────────────
    THRESHOLDS  = [0.05, 0.075, 0.10, 0.125, 0.15, 0.20]
    PERCENTILES = [50, 75, 90, 95, 99]
    hist_edges  = np.arange(0, 0.41, 0.01)
    hist_counts, _ = np.histogram(all_gaps, bins=hist_edges)

    lines = [
        "# FXPulse Strength Gap Distribution Analysis",
        f"Generated   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Data range  : {start_dt.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')} ({HISTORY_DAYS} days)",
        f"Observations: {len(all_gaps):,}  ({len(TRADED_PAIRS)} pairs × {len(gaps[ref])} hourly snapshots)",
        f"Config note : MIN_STRENGTH_GAP currently 1.5 — max achievable = {np.max(all_gaps):.4f}",
        "",
        "## Summary Statistics (all 5 traded pairs combined)",
        f"- Mean   : {np.mean(all_gaps):.4f}",
        f"- Median : {np.median(all_gaps):.4f}",
        f"- Std dev: {np.std(all_gaps):.4f}",
        f"- Max    : {np.max(all_gaps):.4f}",
        f"- Min    : {np.min(all_gaps):.4f}",
        "",
        "## Percentile Table",
        "| Percentile | Gap Value |",
        "|------------|-----------|",
    ]
    for p in PERCENTILES:
        lines.append(f"| {p}th       | {np.percentile(all_gaps, p):.4f}     |")

    lines += [
        "",
        "## Observations Above Candidate Thresholds",
        "| Threshold | Observations | % of total | Implied trades/week* |",
        "|-----------|-------------|------------|---------------------|",
    ]
    total_hours = n_snapshots  # one snapshot per hour
    weeks = HISTORY_DAYS / 7
    for t in THRESHOLDS:
        count = int(np.sum(all_gaps > t))
        pct   = count / len(all_gaps) * 100
        # Divide by 5 pairs and by weeks to get qualifying pair-hours per pair per week
        per_week = (count / len(TRADED_PAIRS)) / weeks
        lines.append(f"| > {t:<5} | {count:>11,} | {pct:>9.1f}% | {per_week:>19.0f} pair-hrs/pair/wk |")

    lines += [
        "",
        "## Per-Pair Statistics",
        "| Pair    | Mean   | 75th pct | 90th pct | 95th pct | Max    |",
        "|---------|--------|----------|----------|----------|--------|",
    ]
    for pair in TRADED_PAIRS:
        g = np.array(gaps[pair])
        if len(g) == 0:
            lines.append(f"| {pair:7} | NO DATA |")
        else:
            lines.append(
                f"| {pair:7} | {np.mean(g):.4f} | {np.percentile(g,75):.4f}   "
                f"| {np.percentile(g,90):.4f}   | {np.percentile(g,95):.4f}   | {np.max(g):.4f} |"
            )

    lines += [
        "",
        "## Histogram (absolute gap, 0.01 buckets)",
        "| Bucket     | Count |",
        "|------------|-------|",
    ]
    for i, cnt in enumerate(hist_counts):
        if cnt > 0:
            lines.append(f"| {hist_edges[i]:.2f}–{hist_edges[i+1]:.2f} | {cnt:,} |")

    output = "\n".join(lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("\n" + output)
    print(f"\n\nPhase 1 complete. Report saved to:\n  {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
