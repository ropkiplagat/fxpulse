"""
director.py — FXPulse DOE Framework: DIRECTIVES
================================================
Rules that never change. All agents read from here.
Nothing in this file can be overridden at runtime.
"""

# ── Trading Safety ────────────────────────────────────────────────────────────
PAPER_TRADING       = True     # NEVER set False without manual deploy
MAX_DRAWDOWN_PCT    = 10.0     # Circuit breaker — halt trading above this
MAX_LOT_SIZE        = 0.10     # Hard cap per trade
MAGIC_NUMBER        = 88888    # All FXPulse orders tagged with this

# ── State Push ────────────────────────────────────────────────────────────────
PUSH_INTERVAL_SEC   = 60       # GitHub push every 60 seconds — MANDATORY
STALE_ALERT_MIN     = 5        # SMS/Telegram if no push for 5 min
STALE_CRITICAL_MIN  = 10       # Escalation alert at 10 min

# ── Orchestrator Restart Policy ───────────────────────────────────────────────
RESTART_DELAY_SEC   = 30       # Wait 30s before restarting crashed agent
FAST_CRASH_SEC      = 10       # Crash in < 10s = code error, not transient
MAX_FAST_CRASHES    = 5        # After 5 fast crashes → CRITICAL alert, long wait
CRITICAL_WAIT_SEC   = 300      # Wait 5 min after hitting max fast crashes
MAX_TOTAL_RESTARTS  = 20       # After 20 restarts → give up, alert for manual fix

# ── Alerts ────────────────────────────────────────────────────────────────────
ALERT_PHONE         = "+61431274377"   # SMS recipient
VPS_IP              = "161.97.83.167"  # For alert messages

# ── Sessions (UTC) ────────────────────────────────────────────────────────────
LONDON_OPEN_UTC     = 8
LONDON_CLOSE_UTC    = 17
NY_OPEN_UTC         = 13
NY_CLOSE_UTC        = 22

# ── Paths ─────────────────────────────────────────────────────────────────────
BOT_DIR             = r"C:\fxpulse"
LOG_DIR             = r"C:\fxpulse\logs"
STATE_FILE          = r"C:\fxpulse\logs\bot_state.json"
ORCH_LOG            = r"C:\fxpulse\logs\orchestrator.log"
AGENT_LOG           = r"C:\fxpulse\logs\agent_output.log"
