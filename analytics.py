"""
Performance Analytics — professional-grade metrics.
Calculates: Sharpe, Sortino, Calmar, Profit Factor, Max Drawdown,
            Win Rate, Expectancy, Equity Curve, R-multiple distribution.

Run standalone: python analytics.py
Or call from main loop for live dashboard updates.
"""
import os
import csv
import math
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import config


def load_trade_history(file: str = config.PERFORMANCE_FILE) -> pd.DataFrame:
    """Load closed trade history from CSV."""
    if not os.path.exists(file):
        return pd.DataFrame()
    try:
        df = pd.read_csv(file)
        df = df[df["outcome"].isin(["win", "loss"])].copy()
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df.sort_values("timestamp")
    except Exception as e:
        print(f"[ANALYTICS] Load error: {e}")
        return pd.DataFrame()


def equity_curve(df: pd.DataFrame, starting_balance: float = 10_000) -> np.ndarray:
    """Build equity curve array from trade P&L."""
    if df.empty:
        return np.array([starting_balance])
    curve = [starting_balance]
    for pnl in df["pnl"]:
        curve.append(curve[-1] + pnl)
    return np.array(curve)


def max_drawdown(curve: np.ndarray) -> tuple[float, float]:
    """
    Returns (max_drawdown_pct, max_drawdown_dollars).
    """
    if len(curve) < 2:
        return 0.0, 0.0
    peak      = np.maximum.accumulate(curve)
    dd_dollar = np.max(peak - curve)
    dd_pct    = np.max((peak - curve) / peak) * 100
    return round(float(dd_pct), 2), round(float(dd_dollar), 2)


def sharpe_ratio(df: pd.DataFrame, risk_free_rate: float = 0.05,
                 periods_per_year: int = 252 * 26) -> float:
    """
    Sharpe ratio annualized (assumes M15 bars).
    periods_per_year = 252 trading days * 26 M15 bars/day = 6552.
    """
    if df.empty or len(df) < 5:
        return 0.0
    returns = df["pnl"].values
    excess  = returns - (risk_free_rate / periods_per_year)
    if returns.std() == 0:
        return 0.0
    return round(float(np.mean(excess) / returns.std() * math.sqrt(periods_per_year)), 3)


def sortino_ratio(df: pd.DataFrame, risk_free_rate: float = 0.05,
                  periods_per_year: int = 6552) -> float:
    """
    Sortino ratio — penalizes only downside volatility (better for asymmetric returns).
    """
    if df.empty or len(df) < 5:
        return 0.0
    returns    = df["pnl"].values
    excess     = returns - (risk_free_rate / periods_per_year)
    downside   = returns[returns < 0]
    if len(downside) == 0 or downside.std() == 0:
        return float("inf") if np.mean(excess) > 0 else 0.0
    return round(float(np.mean(excess) / downside.std() * math.sqrt(periods_per_year)), 3)


def calmar_ratio(df: pd.DataFrame, starting_balance: float = 10_000) -> float:
    """
    Calmar ratio = Annualized Return / Max Drawdown.
    Good risk-adjusted return metric for drawdown-focused traders.
    """
    if df.empty or len(df) < 5:
        return 0.0
    curve = equity_curve(df, starting_balance)
    dd_pct, _ = max_drawdown(curve)
    if dd_pct == 0:
        return float("inf")
    total_return = (curve[-1] - curve[0]) / curve[0]
    # Annualize based on trade count (rough)
    trades_per_year = 252  # Estimated
    annualized = (1 + total_return) ** (trades_per_year / max(len(df), 1)) - 1
    return round(annualized / (dd_pct / 100), 3)


def profit_factor(df: pd.DataFrame) -> float:
    """Gross profit / Gross loss. > 1.5 is good. > 2.0 is excellent."""
    if df.empty:
        return 0.0
    gross_profit = df[df["pnl"] > 0]["pnl"].sum()
    gross_loss   = abs(df[df["pnl"] < 0]["pnl"].sum())
    return round(gross_profit / gross_loss, 3) if gross_loss > 0 else float("inf")


def expectancy(df: pd.DataFrame) -> float:
    """
    Average $ made per trade. Positive = edge.
    Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
    """
    if df.empty:
        return 0.0
    wins   = df[df["pnl"] > 0]["pnl"]
    losses = df[df["pnl"] < 0]["pnl"]
    if len(df) == 0:
        return 0.0
    wr      = len(wins) / len(df)
    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_los = abs(losses.mean()) if len(losses) > 0 else 0
    return round(wr * avg_win - (1 - wr) * avg_los, 3)


def consecutive_stats(df: pd.DataFrame) -> dict:
    """Max consecutive wins and losses."""
    if df.empty:
        return {"max_consec_wins": 0, "max_consec_losses": 0}
    outcomes = df["outcome"].values
    max_w = max_l = cur_w = cur_l = 0
    for o in outcomes:
        if o == "win":
            cur_w += 1; cur_l = 0
        else:
            cur_l += 1; cur_w = 0
        max_w = max(max_w, cur_w)
        max_l = max(max_l, cur_l)
    return {"max_consec_wins": max_w, "max_consec_losses": max_l}


def compute_all(starting_balance: float = 10_000) -> dict:
    """Compute all analytics metrics in one call."""
    df = load_trade_history()

    if df.empty:
        return {
            "total_trades": 0, "note": "No closed trades yet."
        }

    curve       = equity_curve(df, starting_balance)
    dd_pct, dd_usd = max_drawdown(curve)
    wins        = df[df["outcome"] == "win"]
    losses      = df[df["outcome"] == "loss"]
    consec      = consecutive_stats(df)

    metrics = {
        # Core stats
        "total_trades":         len(df),
        "wins":                 len(wins),
        "losses":               len(losses),
        "win_rate":             round(len(wins) / len(df), 4),
        "total_pnl":            round(df["pnl"].sum(), 2),
        "avg_win":              round(wins["pnl"].mean(), 2) if len(wins) > 0 else 0,
        "avg_loss":             round(losses["pnl"].mean(), 2) if len(losses) > 0 else 0,
        "largest_win":          round(wins["pnl"].max(), 2) if len(wins) > 0 else 0,
        "largest_loss":         round(losses["pnl"].min(), 2) if len(losses) > 0 else 0,
        # Risk metrics
        "profit_factor":        profit_factor(df),
        "expectancy_per_trade": expectancy(df),
        "max_drawdown_pct":     dd_pct,
        "max_drawdown_usd":     dd_usd,
        # Risk-adjusted returns
        "sharpe_ratio":         sharpe_ratio(df),
        "sortino_ratio":        sortino_ratio(df),
        "calmar_ratio":         calmar_ratio(df, starting_balance),
        # Streaks
        **consec,
        # Equity
        "starting_balance":     round(curve[0], 2),
        "current_equity":       round(curve[-1], 2),
        "return_pct":           round((curve[-1] / curve[0] - 1) * 100, 2),
        "computed_at":          datetime.now(timezone.utc).isoformat(),
    }
    return metrics


def print_report():
    """Print a formatted analytics report to terminal."""
    m = compute_all()

    print("\n" + "=" * 60)
    print("  PERFORMANCE ANALYTICS REPORT")
    print("=" * 60)
    if "note" in m:
        print(f"  {m['note']}")
        return

    print(f"  Total Trades:      {m['total_trades']}")
    print(f"  Wins / Losses:     {m['wins']} / {m['losses']}")
    print(f"  Win Rate:          {m['win_rate']:.1%}  {'✓ Target met' if m['win_rate'] >= 0.65 else '✗ Below 65% target'}")
    print(f"  Profit Factor:     {m['profit_factor']:.2f}  {'✓' if m['profit_factor'] >= 1.5 else '⚠'}")
    print(f"  Expectancy/Trade:  ${m['expectancy_per_trade']:+.2f}")
    print()
    print(f"  Total P&L:         ${m['total_pnl']:+.2f}")
    print(f"  Return:            {m['return_pct']:+.1f}%")
    print(f"  Max Drawdown:      {m['max_drawdown_pct']:.1f}%  (${m['max_drawdown_usd']:.2f})")
    print()
    print(f"  Sharpe Ratio:      {m['sharpe_ratio']:.3f}  {'✓ >1 is good' if m['sharpe_ratio'] >= 1.0 else ''}")
    print(f"  Sortino Ratio:     {m['sortino_ratio']:.3f}")
    print(f"  Calmar Ratio:      {m['calmar_ratio']:.3f}")
    print()
    print(f"  Avg Win:           ${m['avg_win']:+.2f}")
    print(f"  Avg Loss:          ${m['avg_loss']:+.2f}")
    print(f"  Largest Win:       ${m['largest_win']:+.2f}")
    print(f"  Largest Loss:      ${m['largest_loss']:+.2f}")
    print(f"  Max Consec Wins:   {m['max_consec_wins']}")
    print(f"  Max Consec Losses: {m['max_consec_losses']}")
    print("=" * 60)

    # Save to JSON for web dashboard
    os.makedirs("logs", exist_ok=True)
    with open("logs/analytics.json", "w") as f:
        json.dump(m, f, indent=2)
    print(f"  Report saved: logs/analytics.json")


if __name__ == "__main__":
    print_report()





