"""
copy_trades.py — FXPulse Copy Trading Engine
=============================================
After the master bot places or closes a trade, this module mirrors
that exact trade on every active user account stored in mt5_accounts.json.

Architecture
------------
- Master bot trades on MT5_LOGIN from config.py (one account on VPS)
- Users register on myforexpulse.com and connect their Pepperstone demo accounts
- Their credentials are fetched live from the SiteGround API endpoint
- This module decrypts passwords and replicates trades sequentially

Account switching
-----------------
MetaTrader5 Python API supports sequential account switching via mt5.login().
After copying to all users we re-login to the master account to restore the bot.

Usage in main.py
----------------
import copy_trades as ct

# On startup — logs how many user accounts are registered
ct.log_user_count()

# After a trade opens on master:
ct.copy_open(symbol, direction, sl=sl, tp=tp)

# After a trade closes on master:
ct.copy_close(symbol, direction)
"""

import json
import os
import time
import base64
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # not on VPS — all copy calls are no-ops

import config
import siteground_api as sg_api

# ── SiteGround accounts API ───────────────────────────────────────────────────
# The VPS fetches accounts fresh from this endpoint on every copy event.
# Authenticated by the same API_KEY used for bot state pushes.
_ACCOUNTS_API   = "https://myforexpulse.com/api/get_accounts.php"
_API_KEY        = "0d070602123b2dbf102ab30f01d95f34cab48bf4e08cabd8dd5b53561d6cdac7"

# ── AES-256-CBC encryption secret ────────────────────────────────────────────
# MUST match ENCRYPT_SECRET in deploy/includes/config.php on SiteGround.
# Set MT5_ENCRYPT_SECRET env var on VPS to the real secret.
_ENCRYPT_SECRET = os.environ.get("MT5_ENCRYPT_SECRET", "fxpulse-mt5-enc-v1-changeme-on-server")

# ── Master account (restored after each copy round) ──────────────────────────
_MASTER_LOGIN    = config.MT5_LOGIN
_MASTER_PASSWORD = config.MT5_PASSWORD
_MASTER_SERVER   = config.MT5_SERVER


# ─────────────────────────────────────────────────────────────────────────────
# Decrypt MT5 password  (mirrors PHP encrypt_mt5_password / decrypt_mt5_password)
# AES-256-CBC, key = first 32 bytes of SHA-256(ENCRYPT_SECRET), IV prepended
# ─────────────────────────────────────────────────────────────────────────────

def _decrypt_password(encrypted_b64: str) -> str:
    try:
        from Crypto.Cipher import AES
        key       = hashlib.sha256(_ENCRYPT_SECRET.encode()).digest()[:32]
        raw       = base64.b64decode(encrypted_b64)
        iv        = raw[:16]
        enc       = raw[16:]
        cipher    = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(enc)
        pad       = decrypted[-1]          # PKCS7 unpad
        return decrypted[:-pad].decode("utf-8")
    except Exception as e:
        print(f"[COPY] Decrypt error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Fetch user accounts from SiteGround API
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_user_accounts() -> list[dict]:
    """Fetch active user MT5 accounts from SiteGround, decrypt passwords."""
    try:
        req = urllib.request.Request(
            _ACCOUNTS_API,
            headers={"X-API-Key": _API_KEY, "User-Agent": "FXPulse-Bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[COPY] API error {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"[COPY] Could not reach accounts API: {e}")
        return []

    accounts = []
    for username, acc in body.get("accounts", {}).items():
        enc_pw   = acc.get("mt5_password_enc", "")
        password = _decrypt_password(enc_pw) if enc_pw else ""
        if not password:
            print(f"[COPY] Skipping {username} — password decrypt failed (check MT5_ENCRYPT_SECRET)")
            continue
        accounts.append({
            "username":      username,
            "mt5_login":     int(acc["mt5_login"]),
            "mt5_password":  password,
            "broker_server": acc.get("broker_server", "Pepperstone-Demo"),
            "lot_size":      float(acc.get("lot_size", 0.10)),
            "account_type":  acc.get("account_type", "demo"),
        })
    return accounts


def log_user_count():
    accounts = _fetch_user_accounts()
    print(f"[COPY] {len(accounts)} active user account(s) ready for copy trading.")


# ─────────────────────────────────────────────────────────────────────────────
# MT5 account switcher
# ─────────────────────────────────────────────────────────────────────────────

def _switch_to(login: int, password: str, server: str) -> bool:
    if mt5 is None:
        return False
    ok = mt5.login(login, password=password, server=server)
    if not ok:
        print(f"[COPY] Login failed #{login} on {server}: {mt5.last_error()}")
    return ok


def _restore_master() -> bool:
    ok = _switch_to(_MASTER_LOGIN, _MASTER_PASSWORD, _MASTER_SERVER)
    if ok:
        print(f"[COPY] Master #{_MASTER_LOGIN} restored.")
    else:
        print(f"[COPY] WARNING: Could not restore master #{_MASTER_LOGIN}!")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Copy open
# ─────────────────────────────────────────────────────────────────────────────

def copy_open(symbol: str, direction: str, sl: float = 0, tp: float = 0,
              comment: str = "fxpulse-copy") -> list[dict]:
    """
    Open a copy of the master trade on all active user accounts.
    Each user's lot size comes from their account settings.
    Completely skipped in paper mode.
    """
    if mt5 is None or config.PAPER_TRADING:
        if config.PAPER_TRADING:
            print(f"[COPY] Paper mode — skipping copy open for {symbol}")
        return []

    accounts = _fetch_user_accounts()
    if not accounts:
        print("[COPY] No active user accounts — nothing to copy.")
        return []

    results   = []
    order_type = mt5.ORDER_TYPE_BUY if direction.lower() == "buy" else mt5.ORDER_TYPE_SELL

    for acc in accounts:
        username = acc["username"]
        try:
            if not _switch_to(acc["mt5_login"], acc["mt5_password"], acc["broker_server"]):
                results.append({"username": username, "success": False, "error": "login_failed"})
                continue

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                results.append({"username": username, "success": False, "error": "no_tick"})
                continue

            price = tick.ask if direction.lower() == "buy" else tick.bid

            request = {
                "action":       mt5.TRADE_ACTION_DEAL,
                "symbol":       symbol,
                "volume":       acc["lot_size"],
                "type":         order_type,
                "price":        price,
                "sl":           sl,
                "tp":           tp,
                "deviation":    20,
                "magic":        88888,
                "comment":      comment,
                "type_time":    mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                ticket = result.order
                print(f"[COPY] ✓ {username} | {direction.upper()} {symbol} "
                      f"{acc['lot_size']} lots | #{ticket}")
                results.append({
                    "username":  username, "success": True,
                    "ticket":    ticket,   "symbol":  symbol,
                    "direction": direction, "lot":    acc["lot_size"],
                })
                _log(f"OPEN  | {username} | {symbol} {direction.upper()} "
                     f"{acc['lot_size']} lots | #{ticket}")
                _push_user_state(username, _get_master_state())
            else:
                err     = result.comment if result else "no_result"
                retcode = result.retcode if result else -1
                print(f"[COPY] ✗ {username} | {symbol} failed: {err} ({retcode})")
                results.append({"username": username, "success": False, "error": err})

        except Exception as e:
            print(f"[COPY] Exception for {username}: {e}")
            results.append({"username": username, "success": False, "error": str(e)})

        time.sleep(0.3)

    _restore_master()
    ok   = sum(1 for r in results if r.get("success"))
    fail = len(results) - ok
    print(f"[COPY] Open done: {ok} copied, {fail} failed ({len(results)} users).")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Copy close
# ─────────────────────────────────────────────────────────────────────────────

def copy_close(symbol: str, direction: str) -> list[dict]:
    """
    Close all FXPulse copy positions (magic=88888) on all user accounts
    for the given symbol. Called when the master closes its trade.
    """
    if mt5 is None or config.PAPER_TRADING:
        if config.PAPER_TRADING:
            print(f"[COPY] Paper mode — skipping copy close for {symbol}")
        return []

    accounts = _fetch_user_accounts()
    if not accounts:
        return []

    results    = []
    close_type = mt5.ORDER_TYPE_SELL if direction.lower() == "buy" else mt5.ORDER_TYPE_BUY

    for acc in accounts:
        username = acc["username"]
        try:
            if not _switch_to(acc["mt5_login"], acc["mt5_password"], acc["broker_server"]):
                results.append({"username": username, "success": False, "error": "login_failed"})
                continue

            positions = mt5.positions_get(symbol=symbol) or []
            copies    = [p for p in positions if p.magic == 88888]

            if not copies:
                print(f"[COPY] {username} | No copy position for {symbol} — skipping")
                results.append({"username": username, "success": True, "skipped": True})
                continue

            tick = mt5.symbol_info_tick(symbol)
            for pos in copies:
                price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
                request = {
                    "action":       mt5.TRADE_ACTION_DEAL,
                    "symbol":       symbol,
                    "volume":       pos.volume,
                    "type":         close_type,
                    "position":     pos.ticket,
                    "price":        price,
                    "deviation":    20,
                    "magic":        88888,
                    "comment":      "fxpulse-copy-close",
                    "type_time":    mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    pnl = pos.profit
                    print(f"[COPY] ✓ {username} | Closed {symbol} #{pos.ticket} P&L:{pnl:.2f}")
                    results.append({"username": username, "success": True,
                                    "ticket": pos.ticket, "pnl": pnl})
                    _log(f"CLOSE | {username} | {symbol} #{pos.ticket} | P&L:{pnl:.2f}")
                else:
                    err = result.comment if result else "no_result"
                    print(f"[COPY] ✗ {username} | Close {symbol} failed: {err}")
                    results.append({"username": username, "success": False, "error": err})

            _push_user_state(username, _get_master_state())

        except Exception as e:
            print(f"[COPY] Exception closing for {username}: {e}")
            results.append({"username": username, "success": False, "error": str(e)})

        time.sleep(0.3)

    _restore_master()
    ok   = sum(1 for r in results if r.get("success"))
    fail = len(results) - ok
    print(f"[COPY] Close done: {ok} closed, {fail} failed ({len(results)} users).")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Read current master bot state from local log file
# ─────────────────────────────────────────────────────────────────────────────

def _get_master_state() -> dict:
    try:
        state_file = os.path.join(os.path.dirname(__file__), "logs", "bot_state.json")
        if os.path.exists(state_file):
            with open(state_file) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Push per-user state to GitHub → SiteGround dashboard
# ─────────────────────────────────────────────────────────────────────────────

def _push_user_state(username: str, master_state: dict):
    """Fetch this user's MT5 account + open positions and push to GitHub."""
    try:
        account_info = mt5.account_info()
        positions    = mt5.positions_get() or []
        open_trades  = []
        for p in positions:
            open_trades.append({
                "ticket":    p.ticket,
                "symbol":    p.symbol,
                "type":      "buy" if p.type == mt5.ORDER_TYPE_BUY else "sell",
                "volume":    p.volume,
                "price":     p.price_open,
                "sl":        p.sl,
                "tp":        p.tp,
                "profit":    p.profit,
                "comment":   p.comment,
            })
        state = {
            "updated":  datetime.now(timezone.utc).isoformat(),
            "username": username,
            "account": {
                "login":   account_info.login   if account_info else 0,
                "balance": account_info.balance  if account_info else 0,
                "equity":  account_info.equity   if account_info else 0,
                "currency": account_info.currency if account_info else "USD",
                "server":  account_info.server   if account_info else "",
            },
            "open_trades":   open_trades,
            "bot_running":   master_state.get("bot_running", True),
            "regime":        master_state.get("regime", ""),
            "session":       master_state.get("session", ""),
            "in_session":    master_state.get("in_session", False),
            "performance":   master_state.get("performance", {}),
            "signals":       master_state.get("signals", []),
        }
        sg_api.push_user_state(username, state)
    except Exception as e:
        print(f"[COPY] Could not push state for {username}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────────────────────────────────────

def _log(message: str):
    log_dir  = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "copy_trades.log")
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{ts}] {message}\n")
