"""
Terminal Dashboard — displays currency strength rankings, top pairs,
Renko status, AI win probability, and trade controls.
"""
import os
import sys
from datetime import datetime, timezone


def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _bar(value: float, min_val: float = -3.0, max_val: float = 3.0, width: int = 20) -> str:
    """ASCII bar chart for strength score."""
    pct   = (value - min_val) / (max_val - min_val)
    pct   = max(0.0, min(1.0, pct))
    filled = int(pct * width)
    bar   = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"


def _slope_arrow(slope: str) -> str:
    return {"up": "▲", "down": "▼", "flat": "─"}.get(slope, "─")


def render(strength: dict, top_pairs: list, account_info,
           signals: list, win_probs: dict, consecutive_losses: int,
           in_session: bool, session_name: str):
    """Full dashboard render."""
    _clear()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    balance = account_info.balance if account_info else 0
    equity  = account_info.equity  if account_info else 0
    dd_pct  = (balance - equity) / balance * 100 if balance > 0 else 0

    print("=" * 72)
    print(f"  FOREX AI BOT  |  {now}  |  Bal: {balance:.2f}  Eq: {equity:.2f}  DD: {dd_pct:.1f}%")
    session_status = f"[{session_name.upper()}]" if in_session else "[OUT OF SESSION]"
    print(f"  Consecutive Losses: {consecutive_losses}/{3}  |  Session: {session_status}")
    print("=" * 72)

    # === Currency Strength ===
    print("\n  CURRENCY STRENGTH RANKINGS")
    print("  " + "-" * 56)
    sorted_strength = sorted(strength.items(), key=lambda x: x[1]["rank"])
    for cur, data in sorted_strength:
        score  = data["score"]
        rank   = data["rank"]
        slope  = _slope_arrow(data["slope"])
        bar    = _bar(score)
        color_str = f"+{score:.4f}" if score >= 0 else f"{score:.4f}"
        print(f"  #{rank} {cur:3s} {slope}  {bar}  {color_str:>8s}")

    # === Top Pair Opportunities ===
    print("\n  TOP PAIR OPPORTUNITIES")
    print("  " + "-" * 56)
    if not top_pairs:
        print("  No valid pairs above minimum strength gap.")
    for i, pair in enumerate(top_pairs, 1):
        sym   = pair["symbol"]
        dir_  = pair["direction"].upper()
        score = pair["score"]
        gap   = pair["gap"]
        wp    = win_probs.get(sym, 0.0)
        wp_str = f"{wp:.0%}"
        flag  = " ** HIGH CONVICTION **" if wp >= 0.70 else (" * ABOVE THRESHOLD *" if wp >= 0.65 else "")
        print(f"  #{i} {sym:<12s}  {dir_:4s}  Gap:{gap:+.3f}  Score:{score:.3f}  AI:{wp_str}{flag}")

    # === Active Signals ===
    print("\n  ACTIVE TRADE SIGNALS")
    print("  " + "-" * 56)
    if not signals:
        print("  No signals meet threshold at this time.")
    for sig in signals:
        sym   = sig["symbol"]
        dir_  = sig["direction"].upper()
        conf  = sig.get("confluence", 0)
        renko = sig.get("renko", {})
        renko_status = "TRIGGER" if renko.get("trigger") else ("PULLBACK" if renko.get("in_pullback") else "WATCHING")
        wp    = win_probs.get(sym, 0.0)
        print(f"  {sym:<12s}  {dir_:4s}  Conf:{conf:.2f}  Renko:{renko_status:10s}  AI:{wp:.0%}")
        print(f"    SL dist: {renko.get('sl_distance', 0):.5f}  Trend: {renko.get('trend', '?')} "
              f"  Pullback: {renko.get('pullback_count', 0)} bricks")

    # === Controls ===
    print("\n  CONTROLS")
    print("  " + "-" * 56)
    print("  [T] Force check now   [Q] Quit   [R] Retrain AI model")
    print("  Trades execute automatically when AI >= 65% confidence.")
    print("=" * 72)


def prompt_action() -> str:
    """Non-blocking key prompt. Returns '' if no input."""
    import select
    if sys.platform == "win32":
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch().decode("utf-8", errors="ignore").lower()
        return ""
    else:
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            return sys.stdin.readline().strip().lower()
        return ""
