"""
Forex AI Bot — Main Entry Point
Pepperstone MT5 | Currency Strength + Renko + XGBoost + LSTM + News + Regime

Run: python main.py
     python main.py --train       (train XGBoost + LSTM first)
     python main.py --backtest    (run backtest and exit)
"""
import sys
import time
import json
import os
import ctypes
import traceback
from datetime import datetime, timezone, timedelta

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


def _save_state(strength, top_pairs, account_info, win_probs,
                regime_info, in_session, session_name, performance,
                bot_running: bool = True):
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
            "regime":          regime_info.get("regime"),
            "regime_tradeable":regime_info.get("tradeable", False),
            "in_session":      in_session,
            "session":         session_name,
            "performance":     performance,
            "news":            news.get_news_summary() if config.USE_NEWS_FILTER else [],
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
    print("[BOT] Starting trading loop...")
    print(f"[BOT] Mode: {'PAPER TRADING' if config.PAPER_TRADING else 'LIVE TRADING'}")

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

            # --- Market regime check ---
            regime_info = regime.detect_regime()
            if config.SKIP_NON_TRENDING_REGIMES and not regime_info["tradeable"]:
                print(f"[BOT] Regime: {regime_info['regime']} — skipping scan.")
                available = mt5c.get_available_symbols()
                account   = mt5c.get_account_info()
                _save_state({}, [], account, {}, regime_info, False, "none", perf.get_summary())
                time.sleep(LOOP_INTERVAL)
                continue

            # --- Available symbols ---
            available = mt5c.get_available_symbols()

            # --- Currency Strength ---
            strength = cs.calculate_strength(available)
            crossovers = cs.detect_crossover(prev_strength, strength)
            if crossovers:
                print(f"[BOT] Crossovers: {crossovers}")
            prev_strength = strength

            # --- Top pair opportunities ---
            top_pairs = cs.get_top_pairs(strength, available)

            # --- Session status ---
            now_hour = datetime.now(timezone.utc).hour
            in_session        = False
            active_session    = "none"
            for sess_name in config.TRADE_IN_SESSIONS:
                start, end = config.SESSIONS[sess_name]
                if start <= now_hour < end:
                    in_session     = True
                    active_session = sess_name

            active_signals = []
            win_probs      = {}

            for opportunity in top_pairs:
                symbol    = opportunity["symbol"]
                direction = opportunity["direction"]

                # Cooldown
                last_trade = cooldown_tracker.get(symbol)
                if last_trade and datetime.now(timezone.utc) - last_trade < timedelta(minutes=config.COOLDOWN_MINUTES):
                    continue

                # Already in position
                if mt5c.get_open_positions(symbol=symbol):
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

                if not in_session:
                    continue

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

                print(f"\n[BOT] EXECUTING: {direction.upper()} {symbol}")
                print(f"      Entry:{entry_price:.5f}  SL:{sl:.5f}  TP:{tp:.5f}  Lot:{lot}")
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

            # --- Dashboard & state save ---
            account    = mt5c.get_account_info()
            summary    = perf.get_summary()

            dash.render(strength, top_pairs, account, active_signals,
                        win_probs, consecutive_losses, in_session, active_session)

            _save_state(strength, top_pairs, account, win_probs,
                        regime_info, in_session, active_session, summary)

            # Push to GitHub → SiteGround cron fetches it
            if getattr(config, "GITHUB_TOKEN", ""):
                import json, os
                if os.path.exists(config.BOT_STATE_FILE):
                    with open(config.BOT_STATE_FILE) as f:
                        sg.push_state(json.load(f))

            # --- Analytics ---
            analytics_metrics = analytics.compute_all()
            mode_label = "PAPER" if config.PAPER_TRADING else "LIVE"
            print(f"\n  [{mode_label}] Regime:{regime_info['regime'].upper():15s} | "
                  f"ADX:{regime_info['adx']:.1f} | Memory:{wd.check_memory():.0f}MB")
            print(f"  Trades:{summary['total']} | WR:{summary['win_rate']:.1%} | "
                  f"P&L:{summary['total_pnl']:+.2f} | "
                  f"Sharpe:{analytics_metrics.get('sharpe_ratio', 0):.2f} | "
                  f"ExecLatency:{executor.avg_latency_ms():.0f}ms")

            # --- Retrain ---
            if scan_count % config.RETRAIN_EVERY_BARS == 0 and scan_count > 0:
                print("[BOT] Scheduled retrain...")
                all_syms = config.MAJOR_CURRENCIES + config.MINOR_CURRENCIES
                xgb_predictor = ai.train_model(all_syms, available)
                if LSTM_AVAILABLE and config.USE_LSTM:
                    lstm_predictor = train_lstm(all_syms, available)

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
