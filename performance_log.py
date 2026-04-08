"""
Performance Logger — tracks trades, win rate, drawdown, P&L.
"""
import os
import csv
from datetime import datetime, timezone
import config


def _ensure_file(path: str, headers: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(headers)


def log_signal(symbol: str, direction: str, win_prob: float,
               confluence: float, executed: bool, reason: str = ""):
    _ensure_file(config.SIGNAL_LOG_FILE, [
        "timestamp", "symbol", "direction", "win_prob", "confluence", "executed", "reason"
    ])
    with open(config.SIGNAL_LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now(timezone.utc).isoformat(),
            symbol, direction,
            f"{win_prob:.4f}", f"{confluence:.4f}",
            int(executed), reason,
        ])


def log_trade(ticket: int, symbol: str, direction: str,
              lot: float, entry: float, sl: float, tp: float,
              win_prob: float):
    _ensure_file(config.PERFORMANCE_FILE, [
        "timestamp", "ticket", "symbol", "direction",
        "lot", "entry", "sl", "tp", "win_prob",
        "outcome", "pnl", "closed_at",
    ])
    with open(config.PERFORMANCE_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now(timezone.utc).isoformat(),
            ticket, symbol, direction,
            lot, entry, sl, tp, f"{win_prob:.4f}",
            "", "", "",  # outcome/pnl/closed_at filled on close
        ])


def update_trade_outcome(ticket: int, outcome: str, pnl: float):
    """Update the outcome row for a closed trade."""
    if not os.path.exists(config.PERFORMANCE_FILE):
        return
    rows = []
    with open(config.PERFORMANCE_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            if row.get("ticket") == str(ticket) and row.get("outcome") == "":
                row["outcome"]   = outcome
                row["pnl"]       = f"{pnl:.2f}"
                row["closed_at"] = datetime.now(timezone.utc).isoformat()
            rows.append(row)

    with open(config.PERFORMANCE_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def get_summary() -> dict:
    """Return win rate, total trades, total P&L."""
    if not os.path.exists(config.PERFORMANCE_FILE):
        return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "total_pnl": 0.0}

    with open(config.PERFORMANCE_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("outcome") in ("win", "loss")]

    total  = len(rows)
    wins   = sum(1 for r in rows if r["outcome"] == "win")
    losses = total - wins
    pnl    = sum(float(r.get("pnl", 0)) for r in rows)

    return {
        "total":    total,
        "wins":     wins,
        "losses":   losses,
        "win_rate": wins / total if total > 0 else 0.0,
        "total_pnl": round(pnl, 2),
    }
