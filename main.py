"""
Forex AI Bot — Main Entry Point
Pepperstone MT5 | Currency Strength + Renko + XGBoost + LSTM + News + Regime

Run: python main.py
     python main.py --train       (train XGBoost + LSTM first)
     python main.py --backtest    (run backtest and exit)
"""
import sys
import io
import time
import json
import os
import ctypes
import traceback
from datetime import datetime, timezone, timedelta

# Force UTF-8 stdout/stderr so unicode arrows (▲▼) don't crash when output
# is redirected to a file on a cp1252 Windows locale
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Keep console window visible and titled — never minimizes on VPS
try:
    ctypes.windll.kernel32.SetConsoleTitleW("FXPulse Bot — LIVE")
except Exception:
    pass
import mt5_connector as mt5c
import currency_strength as cs
import renko as rk
import signals as sig
import trade_manager as tm
import performance_log as perf
import dashboard as dash
import ai_predictor as ai
import regime_detector as regime
import news_filter as news
import correlation_filter as corr
import telegram_alerts as tg
import telegram_bot as tg_bot
import copy_trades as ct
import kelly_sizer as ks
import siteground_api as sg
import analytics
import watchdog as wd
import alerts
import executor
import paper_trader as pt
import security
import config

# Load encrypted credentials if available (overrides plain config.py values)
security.apply_to_config()

try:
    from lstm_predictor import LSTMPredictor, train_lstm, ensemble_probability
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False
    print("[BOOT] TensorFlow not found — LSTM disabled, using XGBoost only.")

LOOP_INTERVAL = 60  # seconds between scans


def _next_session_info(now_utc: datetime) -> dict:
    """Return name and minutes until the next trading session opens."""
    now_min = now_utc.hour * 60 + now_utc.minute
    best_name, best_wait = "london", 9999
    for sess_name, (start, end) in config.SESSIONS.items():
        start_min = start * 60
        wait = (start_min - now_min) % (24 * 60)
        if wait == 0:
            wait = 24 * 60
        if wait < best_wait:
            best_wait = wait
            best_name = sess_name
    h, m = divmod(best_wait, 60)
    label = f"{best_name.replace('_', ' ').title()} opens in {h}h {m:02d}m"
    return {"next_session": best_name, "opens_in_min": best_wait, "label": label}


def _send_emergency_sms(message: str):
    """Send Twilio SMS to Rop for level-4 circuit breaker emergencies."""
    print(f"[CB] SMS stubbed (Twilio credentials pending): {message[:80]}")
    return  # Twilio disabled until credentials confirmed — re-enable after token rotation
    import urllib.request, urllib.parse, base64
    try:
        sid   = os.environ.get("TWILIO_SID", "")
        token = os.environ.get("TWILIO_TOKEN", "")
        from_ = os.environ.get("TWILIO_FROM", "+61489263227")
        to    = "+61431274377"
        if not sid or not token:
            print("[CB] SMS skipped: TWILIO_SID/TOKEN not set")
            return
        data = urllib.parse.urlencode({"To": to, "From": from_, "Body": message}).encode()
        url  = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        req  = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10):
            print(f"[CB] Emergency SMS sent to {to}")
    except Exception as e:
        print(f"[CB] SMS send failed: {e}")


def _save_state(strength, top_pairs, account_info, win_probs,
                regime_info, in_session, session_name, performance,
                next_session: dict = None, bot_running: bool = True,
                circuit_breaker: dict = None):
    """Write bot state to JSON for web dashboard."""
    try:
        os.makedirs("logs", exist_ok=True)
        acc = account_info
        state = {
            "updated":         datetime.now(timezone.utc).isoformat(),
            "bot_running":     bot_running,
            "account":         {"balance": acc.balance, "equity": acc.equity} if acc else {},
            "strength":        strength,
            "top_pairs":       top_pairs,
            "win_probs":       win_probs,
            "regime":           regime_info.get("regime"),
            "regime_tradeable": regime_info.get("tradeable", False),
            "regime_direction": regime_info.get("direction"),
            "regime_confidence":regime_info.get("confidence", 0),
            "adx":              regime_info.get("adx", 0),
            "in_session":      in_session,
            "session":         session_name,
            "next_session":    next_session or {},
            "performance":     performance,
            "news":            news.get_news_summary() if config.USE_NEWS_FILTER else [],
            "circuit_breaker": circuit_breaker or {
                "level": 0, "session_open_balance": None,
                "session_drawdown_pct": 0, "triggered_at": None,
            },
        }
        # Write to logs/ (primary) AND root dir (dashboard reads from here)
        with open(config.BOT_STATE_FILE, "w") as f:
            json.dump(state, f, default=str)
        root_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_state.json")
        with open(root_file, "w") as f:
            json.dump(state, f, default=str)
    except Exception as e:
        print(f"[STATE] Save error: {e}")


def run_trading_loop(xgb_predictor: ai.AIPredictor, lstm_predictor=None):
    import threading
    _pending_model = [None]  # background retrain drops new model here

    print("[BOT] Starting trading loop...")
    print(f"[BOT] Mode: {'PAPER TRADING' if config.PAPER_TRADING else 'LIVE TRADING'}")
    ct.log_user_count()

    # Start async executor, heartbeat, Telegram chatbot, and offline alert watchdog
    executor.start()
    heartbeat = wd.HeartbeatThread()
    heartbeat.start()
    tg_bot.start()
    alert_thread = alerts.OfflineAlertThread(config.BOT_STATE_FILE)
    alert_thread.start()

    # Paper trader instance if in paper mode
    paper = pt.get_paper_trader() if config.PAPER_TRADING else None

    tg.alert_bot_started()

    prev_strength       = {}
    cooldown_tracker    = {}
    consecutive_losses  = 0
    traded_tickets      = {}  # symbol → {ticket, direction, entry}
    scan_count          = 0
    last_daily_summary  = datetime.now(timezone.utc).date()

    # Circuit breaker state
    cb = {
        "level": 0,
        "session_open_balance": None,
        "session_drawdown_pct": 0.0,
        "triggered_at": None,
        "paused_until": None,
        "sms_sent": False,
    }
    cb_prev_in_session = False

    while True:
        try:
            scan_count += 1

            # --- Daily summary ---
            today = datetime.now(timezone.utc).date()
            if today != last_daily_summary:
                summary = perf.get_summary()
                tg.alert_daily_summary(
                    summary["total"], summary["wins"], summary["losses"],
                    summary["win_rate"], summary["total_pnl"]
                )
                last_daily_summary = today

            # --- Telegram /stop command check ---
            if tg_bot.trading_paused:
                print("[BOT] Trading paused via Telegram /stop command. Waiting...")
                time.sleep(30)
                continue

            # --- Safety: Daily drawdown check ---
            if tm.check_daily_drawdown():
                tg.alert_drawdown_halt(config.MAX_DAILY_DRAWDOWN)
                print("[BOT] Daily drawdown limit reached. Pausing 30 min.")
                time.sleep(1800)
                continue

            if consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
                print(f"[BOT] {consecutive_losses} consecutive losses. Pausing 60 min.")
                time.sleep(3600)
                consecutive_losses = 0
                continue

            # ── ALWAYS RUN every cycle (24/7) ────────────────────────────
            available   = mt5c.get_available_symbols()
            account     = mt5c.get_account_info()
            regime_info = regime.detect_regime()

            strength   = cs.calculate_strength(available)
            crossovers = cs.detect_crossover(prev_strength, strength)
            if crossovers:
                print(f"[BOT] Crossovers: {crossovers}")
            prev_strength = strength
            top_pairs = cs.get_top_pairs(strength, available)

            # Session status
            now_utc        = datetime.now(timezone.utc)
            now_hour       = now_utc.hour
            in_session     = False
            active_session = "none"
            for sess_name in config.TRADE_IN_SESSIONS:
                start, end = config.SESSIONS[sess_name]
                if start <= now_hour < end:
                    in_session     = True
                    active_session = sess_name

            next_sess = {} if in_session else _next_session_info(now_utc)

            # ── CIRCUIT BREAKER ──────────────────────────────────────────
            # Reset levels 1 & 2 on each new session open; capture open balance
            if in_session and not cb_prev_in_session:
                if cb["level"] in (0, 1, 2):
                    cb["level"] = 0
                if account:
                    cb["session_open_balance"] = account.balance
                cb["triggered_at"] = None
                print(f"[CB] New session — open balance ${cb['session_open_balance'] or 0:.2f}")
            cb_prev_in_session = in_session

            # Calculate session drawdown from equity
            if cb["session_open_balance"] and account and account.equity > 0:
                dd_pct = max(0.0, (cb["session_open_balance"] - account.equity)
                             / cb["session_open_balance"] * 100)
                cb["session_drawdown_pct"] = round(dd_pct, 4)
            else:
                dd_pct = 0.0

            # Level 3: auto-clear after 1 hour
            if cb["level"] == 3 and cb.get("paused_until"):
                if datetime.now(timezone.utc) >= cb["paused_until"]:
                    cb["level"] = 0
                    cb["paused_until"] = None
                    print("[CB] Level 3 cleared — 1-hour pause complete")

            # Level 4: check for manual reset file
            cb_reset_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb_reset.txt")
            if cb["level"] == 4 and os.path.exists(cb_reset_file):
                os.remove(cb_reset_file)
                cb["level"] = 0
                cb["triggered_at"] = None
                cb["sms_sent"] = False
                print("[CB] Level 4 manually cleared via cb_reset.txt")

            # Escalate CB level (only escalate, never auto-downgrade within session)
            if cb["level"] < 4 and dd_pct >= 10.0:
                cb["level"] = 4
                cb["triggered_at"] = datetime.now(timezone.utc).isoformat()
                if not cb.get("sms_sent"):
                    _send_emergency_sms(
                        f"FXPulse EMERGENCY STOP: {dd_pct:.1f}% session DD. "
                        f"Balance ${cb['session_open_balance']:.2f}. "
                        f"Create C:\\fxpulse\\cb_reset.txt to resume."
                    )
                    cb["sms_sent"] = True
                print(f"[CB] LEVEL 4 EMERGENCY STOP ({dd_pct:.1f}% DD)")
            elif cb["level"] < 3 and dd_pct >= 5.0:
                cb["level"] = 3
                cb["triggered_at"] = datetime.now(timezone.utc).isoformat()
                cb["paused_until"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
                print(f"[CB] LEVEL 3 — closing all positions + 1h pause ({dd_pct:.1f}% DD)")
                try:
                    if config.PAPER_TRADING and paper:
                        paper.close_all()
                    elif not config.PAPER_TRADING:
                        tm.close_all_positions()
                except Exception as cb_close_err:
                    print(f"[CB] Close-all error: {cb_close_err}")
            elif cb["level"] < 2 and dd_pct >= 3.0:
                cb["level"] = 2
                cb["triggered_at"] = datetime.now(timezone.utc).isoformat()
                print(f"[CB] LEVEL 2 — no new entries ({dd_pct:.1f}% DD)")
            elif cb["level"] < 1 and dd_pct >= 2.0:
                cb["level"] = 1
                cb["triggered_at"] = datetime.now(timezone.utc).isoformat()
                print(f"[CB] LEVEL 1 — lot size 50% ({dd_pct:.1f}% DD)")

            if cb["level"] > 0:
                print(f"[CB] Active L{cb['level']} | DD:{dd_pct:.2f}% | "
                      f"OpenBal:${cb['session_open_balance'] or 0:.2f}")

            print(f"[BOT] Regime:{regime_info['regime']} ADX:{regime_info.get('adx',0):.1f} "
                  f"| Session:{active_session if in_session else next_sess.get('label','')}")

            active_signals = []
            win_probs      = {}

            # ── TRADE EXECUTION — only when regime + session allow ────────
            skip_trading = (config.SKIP_NON_TRENDING_REGIMES and not regime_info["tradeable"]) or not in_session
            if not skip_trading and cb["level"] >= 2:
                skip_trading = True
                cb_labels = {2: "L2 no new entries", 3: "L3 paused 1h", 4: "L4 EMERGENCY STOP"}
                cb_lbl = cb_labels.get(cb["level"], f"L{cb['level']} active")
                print(f"[CB] {cb_lbl} — skipping trades")
            if skip_trading and cb["level"] < 2:
                reason = "outside session" if not in_session else f"regime={regime_info['regime']}"
                print(f"[BOT] Data collected — skipping trades ({reason})")

            for opportunity in ([] if skip_trading else top_pairs):
                symbol    = opportunity["symbol"]
                direction = opportunity["direction"]

                # Regime direction constraint (bull=buy only, bear=sell only)
                regime_dir = regime_info.get("direction")
                if regime_dir and direction != regime_dir:
                    continue

                # Cooldown
                last_trade = cooldown_tracker.get(symbol)
                if last_trade and datetime.now(timezone.utc) - last_trade < timedelta(minutes=config.COOLDOWN_MINUTES):
                    continue

                # Global concurrent trade cap
                if config.PAPER_TRADING:
                    total_open = len(paper.get_open_positions()) if paper else 0
                else:
                    total_open = len(mt5c.get_open_positions())
                if total_open >= config.MAX_CONCURRENT_TRADES:
                    break

                # Already in position (paper: check virtual positions; live: check MT5)
                if config.PAPER_TRADING:
                    if paper and paper.get_open_positions(symbol=symbol):
                        continue
                elif mt5c.get_open_positions(symbol=symbol):
                    continue

                # --- News filter ---
                if config.USE_NEWS_FILTER:
                    base  = opportunity["base"]
                    quote = opportunity["quote"]
                    blocked, reason = news.is_news_blocked(base, quote)
                    if blocked:
                        tg.alert_news_block(symbol, reason)
                        print(f"[NEWS] {symbol} blocked: {reason}")
                        continue

                # --- Correlation filter ---
                if config.USE_CORRELATION_FILTER:
                    corr_blocked, corr_reason = corr.is_correlated_to_open(
                        symbol, direction, available
                    )
                    if corr_blocked:
                        print(f"[CORR] {symbol} blocked: {corr_reason}")
                        continue

                # --- Renko analysis ---
                renko_setup = rk.analyze_renko(symbol)

                # --- Signal evaluation ---
                evaluated = sig.evaluate_opportunity(opportunity, strength, renko_setup)
                if evaluated is None:
                    continue

                # --- Regime-adjust confluence ---
                adj_confluence = regime.adjust_confluence_for_regime(
                    evaluated["confluence"], regime_info
                )
                evaluated["confluence"] = adj_confluence

                if adj_confluence < config.MIN_CONFLUENCE_SCORE:
                    continue

                # --- AI prediction ---
                features        = evaluated["features"]
                features["confluence"] = adj_confluence

                xgb_prob = xgb_predictor.predict(features)

                # LSTM ensemble
                if LSTM_AVAILABLE and lstm_predictor and config.USE_LSTM:
                    df_m15 = mt5c.get_bars(symbol, config.TF_FAST, count=100)
                    if df_m15 is not None:
                        lstm_prob = lstm_predictor.predict(df_m15, direction)
                        final_prob = ensemble_probability(xgb_prob, lstm_prob,
                                                          config.XGB_WEIGHT, config.LSTM_WEIGHT)
                    else:
                        final_prob = xgb_prob
                else:
                    final_prob = xgb_prob

                win_probs[symbol] = final_prob
                tradeable = final_prob >= config.MIN_WIN_PROBABILITY

                perf.log_signal(symbol, direction, final_prob, adj_confluence, tradeable)
                active_signals.append(evaluated)

                if not tradeable:
                    continue

                # --- Margin protection (30% free margin floor) ---
                _acct = mt5c.get_account_info()
                if _acct and _acct.equity > 0:
                    _margin_ratio = _acct.margin_free / _acct.equity
                    if _margin_ratio < config.MARGIN_MIN_FREE_RATIO:
                        print(f"[BOT] Margin protection: free margin {_margin_ratio:.0%} < 30% — skipping all trades")
                        break

                # --- Execute ---
                sl_distance = renko_setup.get("sl_distance", 0)
                if sl_distance <= 0:
                    continue

                import MetaTrader5 as mt5_mod
                mt5_mod.symbol_select(symbol, True)
                tick_data  = mt5_mod.symbol_info_tick(symbol)
                entry_price = tick_data.ask if direction == "buy" else tick_data.bid

                sl, tp = tm.calculate_sl_tp(symbol, direction, entry_price, sl_distance)

                # Kelly-based lot sizing (superior to flat risk%)
                if config.USE_KELLY_SIZING:
                    lot, sizing_info = ks.calculate_kelly_lot(
                        symbol, sl_distance, final_prob, regime_info["regime"]
                    )
                    if sizing_info.get("blocked"):
                        print(f"[BOT] Trade blocked by Kelly sizer: {sizing_info.get('reason')}")
                        continue
                    print(f"      Kelly: {sizing_info.get('risk_pct'):.2f}% risk "
                          f"| DD mult: {sizing_info.get('dd_multiplier', 1):.2f} "
                          f"| Portfolio at risk: {sizing_info.get('portfolio_risk_used', 0):.1%}")
                else:
                    lot = tm.calculate_lot_size(symbol, sl_distance)

                # CB level 1: halve lot size
                if cb["level"] == 1:
                    lot = max(round(lot * 0.5, 2), 0.01)

                print(f"\n[BOT] EXECUTING: {direction.upper()} {symbol}")
                print(f"      Entry:{entry_price:.5f}  SL:{sl:.5f}  TP:{tp:.5f}  Lot:{lot}"
                      + (f" [CB-L1 50%]" if cb["level"] == 1 else ""))
                print(f"      XGB:{xgb_prob:.0%}  Final AI:{final_prob:.0%}  Regime:{regime_info['regime']}")

                if config.PAPER_TRADING:
                    # Paper trade — simulate without real money
                    result = paper.place_order(symbol, direction, lot, sl, tp,
                                               comment=f"paper-ai-{final_prob:.2f}")
                else:
                    # Live: use async executor for low-latency execution
                    queued = executor.submit_order(symbol, direction, lot, sl, tp,
                                                   final_prob, adj_confluence)
                    result = {"success": queued, "ticket": "queued"}

                if result["success"]:
                    ticket = result.get("ticket", "queued")
                    traded_tickets[symbol] = {
                        "ticket": ticket, "direction": direction, "entry": entry_price
                    }
                    cooldown_tracker[symbol] = datetime.now(timezone.utc)
                    if not config.PAPER_TRADING:
                        perf.log_trade(str(ticket), symbol, direction, lot,
                                       entry_price, sl, tp, final_prob)
                    tg.alert_trade_opened(symbol, direction, lot,
                                          entry_price, sl, tp, final_prob, adj_confluence)
                    mode_str = "[PAPER]" if config.PAPER_TRADING else "[LIVE]"
                    print(f"[BOT] {mode_str} Trade initiated: {direction.upper()} {symbol}")
                    if config.PAPER_TRADING:
                        alerts.send_trade_sms(
                            f"FXPulse PAPER ENTRY | {direction.upper()} {symbol} | "
                            f"Lot:{lot} Entry:{entry_price:.5f} SL:{sl:.5f} TP:{tp:.5f} "
                            f"AI:{final_prob:.0%}"
                        )
                    # ── Copy to all user accounts ──────────────────────────
                    ct.copy_open(symbol, direction, sl=sl, tp=tp)
                else:
                    print(f"[BOT] Order failed: {result}")

            # --- Write heartbeat ---
            wd.write_heartbeat()

            # --- Ensure MT5 still connected ---
            if not wd.ensure_mt5_connected():
                print("[BOT] MT5 connection lost. Waiting 60s...")
                time.sleep(60)
                continue

            # --- Paper trade: check SL/TP hits ---
            if config.PAPER_TRADING and paper:
                paper.check_hits()

            # --- Manage open positions ---
            if not config.PAPER_TRADING:
                tm.manage_open_positions()

            # --- Check closed positions ---
            import MetaTrader5 as mt5_mod
            for symbol, trade_info in list(traded_tickets.items()):
                ticket    = trade_info["ticket"]
                direction = trade_info["direction"]
                history   = mt5_mod.history_deals_get(ticket=ticket)
                if history:
                    for deal in history:
                        if deal.entry == 1:
                            outcome = "win" if deal.profit > 0 else "loss"
                            perf.update_trade_outcome(ticket, outcome, deal.profit)
                            del traded_tickets[symbol]
                            tg.alert_trade_closed(symbol, direction, ticket, outcome, deal.profit)
                            if outcome == "loss":
                                consecutive_losses += 1
                            else:
                                consecutive_losses = 0
                            print(f"[BOT] #{ticket} closed: {outcome} | P&L:{deal.profit:.2f}")
                            # ── Close copies on all user accounts ─────────
                            ct.copy_close(symbol, direction)

            # --- State save + push (always runs before render to guarantee dashboard updates) ---
            account    = mt5c.get_account_info()
            summary    = perf.get_summary()

            cb_state = {
                "level":                cb["level"],
                "session_open_balance": cb["session_open_balance"],
                "session_drawdown_pct": cb["session_drawdown_pct"],
                "triggered_at":         cb.get("triggered_at"),
            }
            _save_state(strength, top_pairs, account, win_probs,
                        regime_info, in_session, active_session, summary,
                        next_session=next_sess, circuit_breaker=cb_state)

            if os.path.exists(config.BOT_STATE_FILE):
                with open(config.BOT_STATE_FILE) as f:
                    sg.push_state(json.load(f))

            # Terminal dashboard render (non-critical — crash here won't block state push)
            try:
                dash.render(strength, top_pairs, account, active_signals,
                            win_probs, consecutive_losses, in_session, active_session)
            except Exception as render_err:
                print(f"[DASH] Render error (non-fatal): {render_err}")

            # --- Analytics ---
            analytics_metrics = analytics.compute_all()
            mode_label = "PAPER" if config.PAPER_TRADING else "LIVE"
            print(f"\n  [{mode_label}] Regime:{regime_info['regime'].upper():15s} | "
                  f"ADX:{regime_info['adx']:.1f} | Memory:{wd.check_memory():.0f}MB")
            print(f"  Trades:{summary['total']} | WR:{summary['win_rate']:.1%} | "
                  f"P&L:{summary['total_pnl']:+.2f} | "
                  f"Sharpe:{analytics_metrics.get('sharpe_ratio', 0):.2f} | "
                  f"ExecLatency:{executor.avg_latency_ms():.0f}ms")

            # Hot-swap model if background retrain completed
            if _pending_model[0] is not None:
                xgb_predictor = _pending_model[0]
                _pending_model[0] = None
                print("[BOT] XGBoost model hot-swapped from background retrain")

            # --- Retrain (background daemon — main loop never blocks) ---
            if scan_count % config.RETRAIN_EVERY_BARS == 0 and scan_count > 0:
                if not any(t.name == "RetrainThread" for t in threading.enumerate()):
                    print("[BOT] Scheduled retrain (background — loop continues)...")
                    all_syms = config.MAJOR_CURRENCIES + config.MINOR_CURRENCIES
                    avail_snap = set(available)
                    def _do_retrain(result_slot, syms, avail):
                        try:
                            result_slot[0] = ai.train_model(syms, avail)
                            print("[BOT] Background retrain complete — hot-swaps next cycle")
                        except Exception as e:
                            print(f"[BOT] Retrain failed: {e}")
                    threading.Thread(
                        target=_do_retrain,
                        args=(_pending_model, all_syms, avail_snap),
                        daemon=True, name="RetrainThread"
                    ).start()

            # --- Key input ---
            key = dash.prompt_action()
            if key == "q":
                print("[BOT] Quitting...")
                break
            elif key == "r":
                all_syms = config.MAJOR_CURRENCIES + config.MINOR_CURRENCIES
                xgb_predictor = ai.train_model(all_syms, available)
                if LSTM_AVAILABLE and config.USE_LSTM:
                    lstm_predictor = train_lstm(all_syms, available)
            elif key == "t":
                continue

            time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            print("\n[BOT] Stopped by user.")
            break
        except Exception as e:
            print(f"[BOT] Error: {e}")
            traceback.print_exc()
            time.sleep(10)

    executor.stop()
    heartbeat.stop()
    tg.alert_bot_stopped()


def main():
    args = sys.argv[1:]

    if "--backtest" in args:
        from backtest import run_backtest
        run_backtest()
        return

    print("=" * 65)
    print("  FOREX AI BOT — Currency Strength + Renko + XGBoost + LSTM")
    print("  Pepperstone MT5  |  Targets 65%+ win rate")
    print("=" * 65)

    mt5c.connect()
    available = mt5c.get_available_symbols()
    print(f"[BOOT] {len(available)} symbols available.")

    # Train or load XGBoost
    if "--train" in args or not _model_exists():
        print("[BOOT] Training XGBoost on historical data...")
        all_syms = config.MAJOR_CURRENCIES + config.MINOR_CURRENCIES
        xgb_predictor = ai.train_model(all_syms, available)
    else:
        xgb_predictor = ai.AIPredictor()

    # Train or load LSTM
    lstm_predictor = None
    if LSTM_AVAILABLE and config.USE_LSTM:
        if "--train" in args or not _lstm_model_exists():
            print("[BOOT] Training LSTM on historical data...")
            all_syms = config.MAJOR_CURRENCIES + config.MINOR_CURRENCIES
            lstm_predictor = train_lstm(all_syms, available)
        else:
            lstm_predictor = LSTMPredictor()

    try:
        run_trading_loop(xgb_predictor, lstm_predictor)
    finally:
        mt5c.disconnect()
        print("[BOT] MT5 disconnected. Goodbye.")


def _model_exists() -> bool:
    return os.path.exists(config.MODEL_PATH) and os.path.exists(config.SCALER_PATH)


def _lstm_model_exists() -> bool:
    return os.path.exists("models/lstm_forex.keras")


if __name__ == "__main__":
    main()
