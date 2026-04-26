# FXPulse Agent Audit Trail

> **NEW AGENT START HERE:** Before asking "where is X" — read `VPS_INVENTORY.md` first.
> It contains all VPS paths, credentials, MT5 config, scheduled tasks, and Phase 1 deployment record.

This file logs all significant agent-driven audits, deployments, and decisions.
Newest section at top.

---

## Telegram multi-subscriber activation — 26 April 2026

**Auditor:** Claude (claude-sonnet-4-6)
**Status:** COMPLETE — end-to-end confirmed, messages received on phone

### What was done
- Audited `telegram_alerts.py` — NOT stubbed, real HTTP calls, both alert functions present
- Found paper ENTRY alert gated behind `if not config.PAPER_TRADING` — fixed
- Found single `TELEGRAM_CHAT_ID` — replaced with multi-subscriber loop
- `config.py`: wired `TELEGRAM_TOKEN` and `TELEGRAM_SUBSCRIBERS` to read from `.env`
- Deployed: config.py, telegram_alerts.py, main.py → GitHub → VPS via Invoke-WebRequest
- Bot restarted clean: no crash loop, Memory:10MB (Telegram loaded), no tracebacks
- Test message sent via `C:\Python310\python.exe` from `C:\fxpulse` — delivered ✅

### Architecture
- Bot reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_SUBSCRIBERS` from `C:\fxpulse\.env`
- `TELEGRAM_SUBSCRIBERS` = comma-separated list of chat_ids
- Each subscriber DMs the bot with `/start` once — owner adds their chat_id to `.env`
- One delivery failure doesn't block others (per-subscriber try/except)

### Alert coverage
- Paper ENTRY → Telegram ✅ (fixed tonight)
- Paper EXIT → Telegram ✅ (was already wired in paper_trader.py)
- Live ENTRY → Telegram ✅
- Live EXIT → Telegram ✅
- Daily summary, drawdown halt, news block → Telegram ✅

### To add new subscriber
1. Have them open Telegram, search bot, send /start
2. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` — find their chat_id
3. Add to TELEGRAM_SUBSCRIBERS in `C:\fxpulse\.env` (comma-separated)
4. Restart bot task

---

## London session window analysis — 22 April 2026

**Auditor:** Claude (claude-sonnet-4-6)
**Window investigated:** 07:00–14:18 UTC April 21 (17:00–00:18 AEST — full London session)
**Sources:** agent.log (417KB), service.log (37MB), service_err.log (38KB), bot_state.json

### Q1: Were any signals generated during London session?

**NO. Zero signals in the entire 07:00–14:18 UTC window.**

Evidence from service.log:
- 1,680 total `Regime:` entries in service.log
- Regime distribution: `ranging` = 118 entries, `neutral` = 1,562 entries
- ADX throughout London window: 15.6–16.5 (ranging) → 12.24 (neutral)
- ADX threshold for trading: ≥ 20 (bull/bear regime required)
- Service.log repeats every cycle: "No valid pairs above minimum strength gap."
  and "No signals meet threshold at this time."

Root cause: Market was in consolidation all session. ADX never crossed 20.
`SKIP_NON_TRENDING_REGIMES = True` correctly blocked trade evaluation.

### Q2: Were any trade executions attempted?

**NO. Zero executions.**

Every cycle in service.log shows:
`Trades:0 | WR:0.0% | P&L:+0.00 | Sharpe:0.00 | ExecLatency:0ms`

Execution path was never reached — the regime gate blocked it upstream.

### Q3: Were any SMS sent?

**NO. Zero SMS.**

No Twilio, SMS, or emergency references in agent.log or service.log beyond
the circuit breaker wiring (which was never triggered, CB level remained 0).

### Q4: Any errors or skip events?

**Skip events: expected.** Every cycle shows:
- Outside London window (early hours): `"skipping trades (outside session)"`
- Inside London window: `"skipping trades (regime=ranging)"` / `regime=neutral`

**Errors found — TWO separate bugs:**

**BUG A — UnboundLocalError (boot-phase, repeated crashes):**
```
UnboundLocalError: local variable 'os' referenced before assignment
  File "C:\fxpulse\main.py", line 267, in run_trading_loop
    cb_reset_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb_reset.txt")
```
The VPS had a version of main.py where Python's scoping rules treated `os`
as a local variable (likely due to an `import os` or `os = x` inside the
same function scope somewhere after line 267). This caused repeated crashes
during the early-morning boot phase (00:49–02:00 UTC). The agent detected
stale state at 01:56 UTC and triggered restarts. Eventually resolved itself.
**Status:** Not currently crashing (bot ran 12+ hours after recovery). But must be
diagnosed before next restart — if main.py is downloaded fresh from GitHub, it
may reintroduce or fix depending on which version is on GitHub vs VPS.

**BUG B — MT5 IPC failed (early restarts):**
```
RuntimeError: MT5 init failed: (-10003, 'IPC initialize failed, MetaTrader 5 x64 not found')
```
MT5 terminal was not running when the watchdog restarted the bot after crash.
Multiple rapid restarts at 00:49, 00:50, 00:51, 00:52 UTC. Eventually MT5
came up and bot connected successfully. Standard watchdog race condition.

**XGBoost retrain at 11:54 UTC:** Completed with only a deprecation warning
(`use_label_encoder not used`) — did NOT hang. This clears the retrain-hang
hypothesis for the 14:18 UTC freeze.

### Q5: Is the empty paper_history.json a trade-logging bug?

**NO. It is correct behavior.**

The market was not trending during the London session. ADX peaked at 16.5,
never reaching the 20 threshold. No signals → no trades → no log entries.
The `paper_history.json` absence is exactly what should happen when the
regime filter blocks all entries.

There is NO logging bug.

### What actually froze the bot at 14:18 UTC?

XGBoost retrain is now ruled out (completed at 11:54 UTC without hanging).
Remaining candidates for the 14:18 UTC freeze:

1. **`dash.prompt_action()` keyboard block** — if the dashboard's input
   prompt uses a blocking call (e.g. `input()` or `msvcrt.getch()`) with no
   timeout, the main loop stalls at end-of-cycle waiting for a keypress that
   never comes on a headless VPS session.
2. **MT5 API call timeout** — `mt5c.get_account_info()` or `mt5c.get_bars()`
   blocking indefinitely if MT5 loses connectivity but doesn't raise an error.
3. **Memory exhaustion** — service.log grew to 37MB; service.log logging
   overhead + 37MB file = possible I/O slowdown but unlikely to fully freeze.

**Highest probability: `dash.prompt_action()` blocking without a timeout.**
Run `C:\fxpulse\dashboard.py` content check to confirm.

### Agent CHECK2 warn (HTTP 202) — persistent throughout

Every agent cycle in the entire log shows:
`[CHECK2] WARN — unexpected response HTTP 202`

This is the SiteGround WAF returning a captcha redirect for direct POST.
Expected behaviour (GitHub relay is the working path). Not a bug.

---

## Pre-live audit follow-up — 22 April 2026

**Auditor:** Claude (claude-sonnet-4-6)
**Actions taken:**
- Kelly sizer regime key mismatch fixed and deployed to VPS
- VPS inspected via SSH: bot state, task status, logs read
- Paper trade history pulled: 0 trades on record

### Kelly Sizer Fix — COMPLETED

**Diff:**
```diff
-REGIME_MULTIPLIERS = {
-    "trending_up":   1.0,
-    "trending_down": 1.0,
-    "ranging":       0.0,   # Don't trade
-    "volatile":      0.5,
-    "crisis":        0.0,   # Don't trade
-}
+# Regime-based position size multipliers — keys match regime_detector.py output
+REGIME_MULTIPLIERS = {
+    "bull":      1.0,
+    "bear":      1.0,
+    "neutral":   0.0,
+    "crash":     0.0,
+    "euphoria":  0.0,
+}
```

- Local file edited: `C:/Users/HP/forex-bot/kelly_sizer.py` ✓
- GitHub commit: `d37ee3e58030bdadb8308ad5e4170ea8b85f7d50` ✓
- VPS deployed via Invoke-WebRequest ✓
- VPS verified: `findstr` confirms `"bull": 1.0` and `"bear": 1.0` at lines 17–18 ✓

### CRITICAL — BOT FROZEN (24+ hours)

**Symptom:**
- Scheduled task FXPulse: `State = Running` (process alive)
- `bot_state.json` last updated: `2026-04-21T14:18:41 UTC`
- `heartbeat.txt` last updated: `2026-04-21T14:16:41 UTC`
- No GitHub state commits since `2026-04-21T13:21:14 UTC`
- Dashboard offline for 24+ hours

**Root cause:**
`RETRAIN_EVERY_BARS = 500` in config.py. At scan #500 (~8.3 hours after startup),
`ai.train_model()` is called on the main thread. XGBoost training blocks indefinitely
(same class of hang as the LSTM issue documented in CLAUDE.md — just XGBoost instead
of TensorFlow). Timer: bot started ~06:00 UTC April 21, froze at ~14:18 UTC April 21.
Timing matches exactly.

**VPS config confirmed:**
- `PAPER_TRADING = True` ✓
- `USE_LSTM = False` ✓
- `RETRAIN_EVERY_BARS = 500` ← hanging culprit

**Fix required:**
Option A (quick): Set `RETRAIN_EVERY_BARS = 99999` — effectively disable periodic
retrain. Model loads from disk at startup; retrain only on `--train` flag or manual `r`.

Option B (proper): Move retrain into a daemon thread so it never blocks the main loop.

**Action needed from Rop:** Approve bot restart after the fix is deployed.

### Paper Trade Track Record

**Total trades: 0**

- `logs/paper_history.json` does not exist on VPS
- `logs/paper_positions.json` does not exist on VPS
- `logs/signals.csv` does not exist on VPS
- `logs/performance.csv` does not exist on VPS

**Reasons:**
1. Bot has been running in a low-ADX neutral regime (ADX = 12.24, threshold = 20).
   `SKIP_NON_TRENDING_REGIMES = True` means no trades fire in neutral.
2. Bot has been frozen since ~14:18 UTC April 21 — even if a trending regime had
   occurred after that time, no trades could fire.

**Account state:** Balance $50,000 demo, Equity $50,000, zero drawdown.

**Implication for go-live decision:** There is no paper track record to evaluate yet.
The audit prerequisite (sufficient paper trades) cannot be met until the bot is
unfrozen and runs through trending sessions.

### Items 3a–3e from Original Brief

The original brief message was truncated — the portion containing items 3a–3e was
cut off before it reached this session. Only the tail end ("confirms item 3d works
in reality not just theory — Average signals per hour during London/NY sessions")
was received.

**Action required:** Please paste the 3a–3e checklist items so they can be assessed.

---

## Pre-live audit — 21 April 2026

**Auditor:** Claude (claude-sonnet-4-6)
**Files reviewed:** main.py, config.py, signals.py, regime_detector.py,
siteground_api.py, trade_manager.py, kelly_sizer.py, paper_trader.py,
executor.py, performance_log.py, security.py, mt5_connector.py, copy_trades.py
**Bot status at audit time:** Running PAPER mode. Last GitHub push: 13:21 UTC (live, healthy).
**PAPER_TRADING:** NOT changed. Awaiting user go-ahead.

---

### SECTION 1 — PAPER_TRADING Guard

**Result: PASS**

- `config.py`: `PAPER_TRADING = True` — correctly set.
- `main.py` prints `[BOT] Mode: PAPER TRADING` on boot.
- Paper trader instantiated only when `config.PAPER_TRADING` is True.
- Live executor (`executor.submit_order`) only called in the `else` branch — paper path uses `paper.place_order()`.
- Copy trading correctly gated: `copy_open` / `copy_close` return `[]` immediately if `config.PAPER_TRADING`.
- Telegram `alert_bot_started()` fires in both modes (intentional).

**No issues.**

---

### SECTION 2 — Live Credential Readiness

**Result: DECISION NEEDED**

`config.py` defaults:
```python
MT5_LOGIN    = int(os.environ.get("MT5_LOGIN",    "0"))
MT5_PASSWORD = os.environ.get("MT5_PASSWORD",    "")
MT5_SERVER   = os.environ.get("MT5_SERVER",      "Pepperstone-Demo")
```

All values come from `.env` on VPS. The current `.env` has **demo** credentials.
`security.py` `apply_to_config()` runs at startup and can override via encrypted
`.credentials.enc` — but only if that file exists on VPS.

**Action required before going live:**
1. Update VPS `.env` with Pepperstone LIVE account number, password, and server name.
2. Confirm live server name (check in MT5 terminal → File → Open Account → Pepperstone).
3. Optionally run `python security.py --setup` to encrypt the live creds.

---

### SECTION 3 — SL/TP and Execution Logic

**Result: PASS**

- `calculate_sl_tp()` (trade_manager.py): Buy → SL below entry, TP above at 2R. Sell → reversed. ✓
- Guard in main.py: `if sl_distance <= 0: continue` — no zero-SL orders possible. ✓
- Margin protection: `free_margin / equity < 0.30` → skips all trades for that cycle. ✓
- MT5 order uses `ORDER_FILLING_IOC`, `ORDER_TIME_GTC`, SLIPPAGE=10 points. ✓
- Spread filter: `MAX_SPREAD_PIPS = 3.0` applied before signal evaluation. ✓

---

### SECTION 4 — Risk Management Stack

**Result: PASS with one redundancy note**

Nine independent layers, outermost to innermost:

| Layer | Trigger | Action | Code location |
|-------|---------|--------|---------------|
| 1 | Daily DD ≥ 5% (equity vs balance) | halt 30 min | trade_manager.check_daily_drawdown() |
| 2 | 3 consecutive losses | pause 60 min | main.py consecutive_losses counter |
| 3 | CB L1: session DD ≥ 2% | 50% lot size | main.py cb dict |
| 4 | CB L2: session DD ≥ 3% | no new entries | main.py cb dict |
| 5 | CB L3: session DD ≥ 5% | close all + 1h pause | main.py cb dict |
| 6 | CB L4: session DD ≥ 10% | emergency stop + SMS to +61431274377 | main.py cb dict |
| 7 | Kelly DD ≥ 8% | halt sizing (0x) | kelly_sizer.get_drawdown_multiplier() |
| 8 | Kelly DD ≥ 5% | reduce to 50% | kelly_sizer |
| 9 | Free margin < 30% equity | skip all trades | main.py margin check |

**Note:** Layers 1 and 7 both measure drawdown but from different bases. Redundant
but conservative — not a problem.

**CB Level 4 reset:** requires creating `C:\fxpulse\cb_reset.txt` manually on VPS.

---

### SECTION 5 — CRITICAL BUG: Kelly Sizer Regime Key Mismatch

**Result: FAIL — confirmed bug, not blocking but causes consistent under-sizing**

`regime_detector.py` outputs these regime strings:
`"neutral"` | `"bull"` | `"bear"` | `"crash"` | `"euphoria"`

`kelly_sizer.py` REGIME_MULTIPLIERS keys:
```python
REGIME_MULTIPLIERS = {
    "trending_up":   1.0,
    "trending_down": 1.0,
    "ranging":       0.0,
    "volatile":      0.5,
    "crisis":        0.0,
}
```

**None of the keys match.** `REGIME_MULTIPLIERS.get(regime, 0.5)` always falls
through to the default of `0.5` because regime_detector outputs "bull"/"bear",
not "trending_up"/"trending_down".

**Impact:** In bull or bear regimes (the only states where trades fire), every
trade is sized at **50% of optimal Kelly** instead of 100%. Bot trades but leaves
performance on the table.

**Fix (5-line change in kelly_sizer.py):**
```python
REGIME_MULTIPLIERS = {
    "bull":      1.0,
    "bear":      1.0,
    "neutral":   0.0,   # already blocked by SKIP_NON_TRENDING_REGIMES
    "crash":     0.0,   # already blocked
    "euphoria":  0.0,   # already blocked
}
```

**Recommendation: fix before going live.**

---

### SECTION 6 — Signal Engine Sanity Check

**Result: PASS with one observation**

`signals.py` confluence weights sum to 1.0. No hardcoded test values.
No TODO comments in signals.py or regime_detector.py.

**Observation:** RSI valid range for sell signals is 35–60. RSI between 60–70 on
a sell setup only gets 0.5x weight (0.05 score deduction). Minor — conservative
by design.

---

### SECTION 7 — Push Infrastructure

**Result: PASS**

- `siteground_api.py` PUSH_URL = `https://myforexpulse.com/api/bot_push.php` ✓
  (correct endpoint — old `state_push.php` bug fixed in commit dd6b64d)
- No GITHUB_TOKEN gate on push (removed in 6a5fdb4). ✓
- GitHub relay fallback handles 409 conflicts by clearing SHA cache. ✓
- State push runs every cycle unconditionally, before dashboard render. ✓
- Live evidence: GitHub commits showing `state HH:MM:SS` every ~60s today. ✓

---

### SECTION 8 — Copy Trading Readiness

**Result: CONDITIONAL PASS**

- Paper mode gate: `copy_open` / `copy_close` return `[]` if `config.PAPER_TRADING`. ✓
- AES-256-CBC decryption mirrors PHP implementation. ✓
- Master account restored after each copy round via `_restore_master()`. ✓

**FLAG — MT5_ENCRYPT_SECRET:**
`copy_trades.py` default:
```python
_ENCRYPT_SECRET = os.environ.get("MT5_ENCRYPT_SECRET", "fxpulse-mt5-enc-v1-changeme-on-server")
```
If VPS `.env` does NOT have `MT5_ENCRYPT_SECRET` set, all user passwords will fail
to decrypt silently. Copy trades fire 0 copies.

**Verify on VPS before live day:**
```powershell
Select-String "MT5_ENCRYPT_SECRET" C:\fxpulse\.env
```
Value must match `ENCRYPT_SECRET` in `deploy/includes/config.php` on SiteGround.

**FLAG — Restore failure not halted:**
If `_restore_master()` fails after a copy round, the next loop iteration operates
on the wrong account. Warning prints to console but trading is not halted.
Worth monitoring on day 1.

---

### SECTION 9 — Executor (Live Order Path)

**Result: PASS with one medium flag**

- Thread-safe async queue, maxsize=20, daemon thread drains it. ✓
- Latency tracking via `avg_latency_ms()`. ✓

**FLAG — Queue full = silent drop:**
```python
except queue.Full:
    print(f"[EXEC] Queue full — order for {symbol} dropped.")
```
Dropped orders only print to console — no Telegram alert. Under normal conditions
the queue of 20 will never fill, but worth monitoring on live day 1.

---

### SECTION 10 — Console Title Cosmetic Bug

**Result: LOW — cosmetic only**

`main.py` line ~27:
```python
ctypes.windll.kernel32.SetConsoleTitleW("FXPulse Bot — LIVE")
```
Says "LIVE" regardless of `PAPER_TRADING`. Not dangerous. One-line fix:
```python
mode_str = "PAPER" if config.PAPER_TRADING else "LIVE"
ctypes.windll.kernel32.SetConsoleTitleW(f"FXPulse Bot — {mode_str}")
```

---

### SECTION 11 — Performance Log and Track Record

**Result: PASS — with note**

- `log_signal()` called for every evaluated signal in both modes. ✓
- `log_trade()` / `update_trade_outcome()` only called in live mode — paper
  P&L tracked separately in `logs/paper_history.json`. ✓
- When live is enabled, `performance.csv` starts fresh — correct for a clean
  live track record.

**Paper performance lives at:** `C:\fxpulse\logs\paper_history.json` on VPS.
Not committed to GitHub. To check: connect via RDP, open PowerShell:
```powershell
Get-Content C:\fxpulse\logs\paper_history.json | ConvertFrom-Json | Measure-Object -Property pnl -Sum
```

---

### SECTION 12 — Signal Frequency Estimate (Code Analysis)

**Result: INFORMATIONAL**

Filters that must ALL pass to produce an executed trade:
1. In London (7–16 UTC) or NY (12–21 UTC) session
2. Regime = bull or bear (ADX ≥ 20, aligned EMA20/50/200)
3. Circuit breaker level < 2
4. Spread ≤ 3.0 pips
5. News filter clear
6. Correlation filter clear
7. Confluence ≥ 0.60
8. AI win probability ≥ 0.65
9. Renko sl_distance > 0

With 3 pairs evaluated per 60s cycle during London/NY overlap (12–16 UTC) on a
trending day: **estimated 0–4 executed signals per session day**. Quiet/ranging
days: 0. This is expected — the strategy is deliberately selective.

**For real data:** read `C:\fxpulse\logs\signals.csv` and filter `executed=1`.

---

### MASTER SUMMARY — Pre-live Readiness

#### READY (no changes needed to go live)
- PAPER_TRADING guard — airtight
- SL/TP calculation — correct
- All 9 risk layers — wired and functional
- Push infrastructure — live and healthy
- Copy trade paper-mode gate — correctly disabled
- Signal engine — clean, no TODOs, no test values
- Executor — async, non-blocking

#### FIX BEFORE GOING LIVE

| Priority | Issue | File | Action |
|----------|-------|------|--------|
| HIGH | Kelly regime keys don't match detector output — 50% sizing | kelly_sizer.py | Replace REGIME_MULTIPLIERS keys |
| HIGH | Verify MT5_ENCRYPT_SECRET set in VPS .env | .env on VPS | `Select-String "MT5_ENCRYPT_SECRET" C:\fxpulse\.env` |
| HIGH | Update .env with Pepperstone LIVE creds | .env on VPS | MT5_LOGIN, MT5_PASSWORD, MT5_SERVER |
| LOW | Console title says LIVE in paper mode | main.py | One-line cosmetic fix |
| LOW | Dropped executor orders not alerted | executor.py | Add Telegram alert in queue.Full handler |

#### DECISIONS NEEDED FROM RON

1. **Is the paper track record sufficient?**
   Read `C:\fxpulse\logs\paper_history.json`. Suggested minimum: 30+ trades,
   60%+ win rate, max drawdown < 5%.

2. **Fix Kelly sizer now or post-launch?**
   Before = full optimal sizing from day 1. After = 50% sizing on day 1.
   Recommendation: fix it now — it's a 5-line change.

3. **Which Pepperstone live server name?**
   Check in MT5 terminal → File → Open Account → Pepperstone servers list.

4. **Copy trading on live day 1 or solo first?**
   Run solo first session to confirm execution before mirroring to user accounts?

---

**Audit complete. Bot not restarted. PAPER_TRADING unchanged.**
**Awaiting your go-ahead.**
