"""
News Filter — blocks trading during high-impact economic events.
Uses MT5's built-in calendar + JBlanked API fallback.
Prevents getting stopped out by NFP, CPI, Fed decisions, etc.
"""
import requests
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5
import config

# Block trading N minutes before and after high-impact news
BLOCK_BEFORE_MINUTES = 30
BLOCK_AFTER_MINUTES  = 30

# Currency → ISO code mapping
CURRENCY_COUNTRY = {
    "USD": "USD", "EUR": "EUR", "GBP": "GBP",
    "JPY": "JPY", "AUD": "AUD", "NZD": "NZD",
    "CAD": "CAD", "CHF": "CHF",
}

_news_cache = []
_cache_expiry = None


def _fetch_mt5_calendar() -> list:
    """Use MT5 built-in economic calendar (most reliable)."""
    try:
        now   = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)
        end   = now + timedelta(hours=4)

        events = mt5.calendar_get(start, end)
        if not events:
            return []

        result = []
        for e in events:
            # MT5 calendar importance: 1=low, 2=medium, 3=high
            if e.importance < 2:  # Only medium/high
                continue
            event_time = datetime.fromtimestamp(e.time, tz=timezone.utc)
            result.append({
                "time":       event_time,
                "currency":   e.currency,
                "importance": e.importance,
                "name":       e.name,
                "source":     "MT5",
            })
        return result
    except Exception as e:
        print(f"[NEWS] MT5 calendar error: {e}")
        return []


def _fetch_jblanked_calendar() -> list:
    """JBlanked free calendar API fallback."""
    global _news_cache, _cache_expiry
    now = datetime.now(timezone.utc)

    # Use cache if fresh (valid 30 min)
    if _cache_expiry and now < _cache_expiry and _news_cache:
        return _news_cache

    try:
        url = "https://www.jblanked.com/news/api/calendar/"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return []

        data = resp.json()
        result = []
        for event in data:
            # Only high impact
            if event.get("impact", "").lower() not in ("high", "medium"):
                continue
            try:
                event_time = datetime.fromisoformat(event["date"]).replace(tzinfo=timezone.utc)
            except Exception:
                continue
            result.append({
                "time":       event_time,
                "currency":   event.get("currency", ""),
                "importance": 3 if event.get("impact", "").lower() == "high" else 2,
                "name":       event.get("title", ""),
                "source":     "JBlanked",
            })

        _news_cache    = result
        _cache_expiry  = now + timedelta(minutes=30)
        return result
    except Exception as e:
        print(f"[NEWS] JBlanked API error: {e}")
        return []


def get_upcoming_events() -> list:
    """Return upcoming high-impact events (next 4 hours)."""
    events = _fetch_mt5_calendar()
    if not events:
        events = _fetch_jblanked_calendar()
    return events


def is_news_blocked(base_currency: str, quote_currency: str) -> tuple[bool, str]:
    """
    Returns (is_blocked, reason).
    Blocks if high-impact news for either currency within window.
    """
    events = get_upcoming_events()
    now    = datetime.now(timezone.utc)

    for event in events:
        event_cur = event.get("currency", "").upper()
        if event_cur not in (base_currency.upper(), quote_currency.upper()):
            continue

        event_time = event["time"]
        diff_minutes = (event_time - now).total_seconds() / 60

        # Block before news
        if -BLOCK_AFTER_MINUTES <= diff_minutes <= BLOCK_BEFORE_MINUTES:
            name = event.get("name", "Event")
            imp  = "HIGH" if event["importance"] == 3 else "MEDIUM"
            reason = f"{imp} NEWS: {event_cur} — {name} at {event_time.strftime('%H:%M UTC')}"
            return True, reason

    return False, ""


def get_news_summary() -> list:
    """Return upcoming events for dashboard display."""
    events  = get_upcoming_events()
    now     = datetime.now(timezone.utc)
    summary = []
    for e in events:
        diff = int((e["time"] - now).total_seconds() / 60)
        if -60 <= diff <= 240:
            summary.append({
                "currency": e["currency"],
                "name":     e["name"][:30],
                "in_min":   diff,
                "impact":   "HIGH" if e["importance"] == 3 else "MED",
            })
    return sorted(summary, key=lambda x: x["in_min"])
