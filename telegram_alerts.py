"""
Telegram Alerts — sends trade notifications to your Telegram.
Setup: create a bot via @BotFather, get token + chat ID.
"""
import requests
from datetime import datetime, timezone
import config

def _get_token() -> str:
    return getattr(config, "TELEGRAM_TOKEN", "")


def _get_subscribers() -> list:
    raw = getattr(config, "TELEGRAM_SUBSCRIBERS", "") or getattr(config, "TELEGRAM_CHAT_ID", "")
    return [c.strip() for c in str(raw).split(",") if c.strip()]


def _send(message: str) -> bool:
    token = _get_token()
    if not token:
        return False
    subscribers = _get_subscribers()
    if not subscribers:
        return False
    ok = True
    for chat_id in subscribers:
        try:
            url  = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(url, data={
                "chat_id":    chat_id,
                "text":       message,
                "parse_mode": "Markdown",
            }, timeout=5)
            if resp.status_code != 200:
                print(f"[TG] Failed {chat_id[:4]}...: HTTP {resp.status_code}")
                ok = False
        except Exception as e:
            print(f"[TG] Send failed {chat_id[:4]}...: {e}")
            ok = False
    return ok


def alert_trade_opened(symbol: str, direction: str, lot: float,
                       entry: float, sl: float, tp: float,
                       win_prob: float, confluence: float):
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    emoji = "🟢" if direction == "buy" else "🔴"
    msg = (
        f"{emoji} *TRADE OPENED* — {now}\n"
        f"Pair: `{symbol}`\n"
        f"Direction: *{direction.upper()}*\n"
        f"Lot: `{lot}`\n"
        f"Entry: `{entry:.5f}`\n"
        f"SL: `{sl:.5f}`\n"
        f"TP: `{tp:.5f}`\n"
        f"AI Confidence: *{win_prob:.0%}*\n"
        f"Confluence: `{confluence:.2f}`"
    )
    _send(msg)


def alert_trade_closed(symbol: str, direction: str, ticket: int,
                       outcome: str, pnl: float):
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    emoji = "✅" if outcome == "win" else "❌"
    msg = (
        f"{emoji} *TRADE CLOSED* — {now}\n"
        f"Pair: `{symbol}`\n"
        f"Direction: *{direction.upper()}*\n"
        f"Ticket: `#{ticket}`\n"
        f"Result: *{outcome.upper()}*\n"
        f"P&L: `{pnl:+.2f}`"
    )
    _send(msg)


def alert_breakeven(symbol: str, ticket: int):
    _send(f"⚡ *Break-even set* on `{symbol}` (#{ticket})")


def alert_partial_close(symbol: str, ticket: int, lot: float, pnl: float):
    _send(f"📤 *Partial close* {lot} lots on `{symbol}` (#{ticket}) | P&L: `{pnl:+.2f}`")


def alert_drawdown_halt(drawdown_pct: float):
    _send(f"🚨 *TRADING HALTED* — Daily drawdown {drawdown_pct:.1f}% limit reached.")


def alert_news_block(symbol: str, reason: str):
    _send(f"📰 *News block* on `{symbol}` — {reason}")


def alert_daily_summary(total: int, wins: int, losses: int,
                         win_rate: float, total_pnl: float):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    emoji = "📈" if total_pnl >= 0 else "📉"
    msg = (
        f"{emoji} *Daily Summary* — {now}\n"
        f"Trades: `{total}` | Wins: `{wins}` | Losses: `{losses}`\n"
        f"Win Rate: *{win_rate:.1%}*\n"
        f"Total P&L: `{total_pnl:+.2f}`"
    )
    _send(msg)


def alert_bot_started():
    _send("🤖 *Forex AI Bot started* — monitoring markets...")


def alert_bot_stopped():
    _send("🛑 *Forex AI Bot stopped.*")
