"""
FXPulse Telegram Chatbot — 2-way control from your phone.
Runs as a background thread alongside the trading loop.

Commands:
  /status   — bot running status + account balance/equity
  /trades   — open trades right now
  /pnl      — today's P&L summary
  /stop     — pause trading (sets global flag)
  /resume   — resume trading
  /help     — list all commands

Setup:
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Message @userinfobot → copy your chat ID
  3. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in config.py
"""

import threading
import time
import json
import os
import requests
from datetime import datetime, timezone
import config

# Global flag — main.py reads this to pause/resume trading
trading_paused = False
_bot_running   = False
_last_update   = 0   # Telegram update offset

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscribers.json")

WELCOME_MSG = (
    "Welcome to *FXPulse* 🤖\n\n"
    "You're now subscribed to live AI forex signals.\n\n"
    "*What to expect:*\n"
    "• 5 majors: EURUSD · GBPUSD · USDJPY · AUDUSD · USDCAD\n"
    "• Signals during London (07:00–16:00 UTC) & New York (13:00–22:00 UTC)\n"
    "• Each alert: direction, entry, SL/TP, AI confidence\n"
    "• Dashboard: myforexpulse.com/dashboard.php\n\n"
    "_Sit tight — signals fire when the AI finds a setup._"
)


def load_subscribers() -> list:
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_subscriber(chat_id: str, name: str) -> bool:
    """Add subscriber if not already present. Returns True if newly added."""
    subs = load_subscribers()
    for s in subs:
        if str(s.get("chat_id")) == str(chat_id):
            return False
    subs.append({
        "chat_id":   str(chat_id),
        "name":      name,
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "active":    True,
    })
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f, indent=2)
    print(f"[TG-BOT] New subscriber: {name} (id={str(chat_id)[:6]}...)")
    return True


def _handle_start(msg: dict):
    chat_id = str(msg.get("chat", {}).get("id", ""))
    name    = msg.get("from", {}).get("first_name", "Trader")
    if not chat_id:
        return
    is_new = save_subscriber(chat_id, name)
    text   = WELCOME_MSG if is_new else f"Hey {name}, you're already subscribed. Signals on the way!"
    try:
        requests.post(
            f"https://api.telegram.org/bot{_token()}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        print(f"[TG-BOT] Welcome send failed: {e}")


def _token():
    return getattr(config, "TELEGRAM_TOKEN", "")


def _chat_id():
    return getattr(config, "TELEGRAM_CHAT_ID", "")


def _is_configured() -> bool:
    return bool(_token() and _chat_id())


# ── Send ────────────────────────────────────────────────────────────────────

def send(text: str) -> bool:
    if not _is_configured():
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{_token()}/sendMessage",
            data={"chat_id": _chat_id(), "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[TG-BOT] Send error: {e}")
        return False


# ── Polling ──────────────────────────────────────────────────────────────────

def _get_updates(offset: int):
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{_token()}/getUpdates",
            params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
            timeout=35,
        )
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception:
        pass
    return []


# ── Command handlers ─────────────────────────────────────────────────────────

def _cmd_status():
    global trading_paused
    state_file = getattr(config, "BOT_STATE_FILE", "logs/bot_state.json")
    try:
        with open(state_file) as f:
            state = json.load(f)
        acc     = state.get("account", {})
        balance = acc.get("balance", "N/A")
        equity  = acc.get("equity", "N/A")
        regime  = state.get("regime", "unknown")
        session = state.get("session", "none")
        updated = state.get("updated", "")[:19].replace("T", " ")
        status  = "PAUSED" if trading_paused else "RUNNING"
        mode    = "PAPER" if getattr(config, "PAPER_TRADING", True) else "LIVE"
        return (
            f"*FXPulse Status* — {updated} UTC\n"
            f"Bot: *{status}* | Mode: *{mode}*\n"
            f"Balance: `${balance:,.2f}` | Equity: `${equity:,.2f}`\n"
            f"Regime: `{regime}` | Session: `{session}`"
        )
    except Exception as e:
        return f"Status unavailable: {e}"


def _cmd_trades():
    state_file = getattr(config, "BOT_STATE_FILE", "logs/bot_state.json")
    try:
        with open(state_file) as f:
            state = json.load(f)
        pairs = state.get("top_pairs", [])
        probs = state.get("win_probs", {})
        if not pairs:
            return "No active signals right now."
        lines = ["*Top Pairs (Current Scan)*"]
        for p in pairs[:5]:
            prob = probs.get(p, 0)
            lines.append(f"• `{p}` — AI: *{prob:.0%}*")
        return "\n".join(lines)
    except Exception as e:
        return f"Trade data unavailable: {e}"


def _cmd_pnl():
    perf_file = getattr(config, "PERFORMANCE_FILE", "logs/performance.csv")
    try:
        import csv
        from datetime import date
        today = date.today().isoformat()
        wins = losses = total_pnl = 0
        if os.path.exists(perf_file):
            with open(perf_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("date", "").startswith(today):
                        pnl = float(row.get("pnl", 0))
                        total_pnl += pnl
                        if pnl >= 0:
                            wins += 1
                        else:
                            losses += 1
        total = wins + losses
        rate  = (wins / total * 100) if total else 0
        emoji = "📈" if total_pnl >= 0 else "📉"
        return (
            f"{emoji} *Today's P&L* — {today}\n"
            f"Trades: `{total}` | W: `{wins}` | L: `{losses}`\n"
            f"Win Rate: *{rate:.0f}%*\n"
            f"P&L: `{total_pnl:+.2f}`"
        )
    except Exception as e:
        return f"P&L data unavailable: {e}"


def _cmd_stop():
    global trading_paused
    trading_paused = True
    return "Trading *PAUSED*. Send /resume to restart."


def _cmd_resume():
    global trading_paused
    trading_paused = False
    return "Trading *RESUMED*."


def _cmd_help():
    return (
        "*FXPulse Bot Commands*\n"
        "/status — account balance + bot state\n"
        "/trades — current top pairs + AI confidence\n"
        "/pnl — today's P&L summary\n"
        "/stop — pause trading\n"
        "/resume — resume trading\n"
        "/help — this message"
    )


COMMANDS = {
    "/status": _cmd_status,
    "/trades": _cmd_trades,
    "/pnl":    _cmd_pnl,
    "/stop":   _cmd_stop,
    "/resume": _cmd_resume,
    "/help":   _cmd_help,
}


# ── Main loop ────────────────────────────────────────────────────────────────

def _poll_loop():
    global _last_update, _bot_running
    print("[TG-BOT] Chatbot started — polling for commands...")
    send("🤖 *FXPulse chatbot online.* Send /help for commands.")

    while _bot_running:
        updates = _get_updates(_last_update)
        for update in updates:
            _last_update = update["update_id"] + 1
            msg  = update.get("message", {})
            text = msg.get("text", "").strip().split()[0].lower()  # first word only
            # /start is open to everyone — auto-subscribe
            if text == "/start":
                _handle_start(msg)
                continue
            # All other commands: only authorised admin chat
            from_id = str(msg.get("chat", {}).get("id", ""))
            if from_id != str(_chat_id()):
                continue
            handler = COMMANDS.get(text)
            if handler:
                reply = handler()
                send(reply)
            elif text:
                send(f"Unknown command: `{text}`\nSend /help for options.")
        time.sleep(1)


def start():
    """Start chatbot in background thread. Call from main.py."""
    global _bot_running
    if not _is_configured():
        print("[TG-BOT] Skipping — TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set in config.py")
        return
    _bot_running = True
    t = threading.Thread(target=_poll_loop, daemon=True)
    t.start()


def stop():
    """Stop the chatbot polling loop."""
    global _bot_running
    _bot_running = False
    send("🛑 FXPulse chatbot stopping.")
