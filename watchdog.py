"""
Watchdog & Error Handler — keeps the bot running 24/7.
Handles:
  - MT5 disconnection and auto-reconnect
  - Uncaught exceptions with auto-restart
  - Heartbeat monitoring (alerts if bot goes silent)
  - Windows service registration (optional)
  - Memory leak detection

Run via: python watchdog.py   (wraps main.py)
Or call manage_connection() inside the main loop for reconnects.
"""
import os
import sys
import time
import subprocess
import threading
import psutil
from datetime import datetime, timezone, timedelta
import mt5_connector as mt5c
import telegram_alerts as tg
import config

HEARTBEAT_FILE    = "logs/heartbeat.txt"
MAX_RESTART_COUNT = 5
RESTART_DELAY     = 30       # seconds between restarts
MAX_MEMORY_MB     = 1024     # Restart if bot uses > 1 GB RAM
HEARTBEAT_INTERVAL= 60       # Write heartbeat every N seconds
STALE_AFTER       = 300      # Alert if no heartbeat for 5 minutes


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def write_heartbeat():
    """Write timestamp to heartbeat file. Call every loop iteration."""
    os.makedirs("logs", exist_ok=True)
    with open(HEARTBEAT_FILE, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def check_heartbeat() -> tuple[bool, int]:
    """Returns (is_alive, seconds_since_last_beat)."""
    if not os.path.exists(HEARTBEAT_FILE):
        return False, 9999
    with open(HEARTBEAT_FILE) as f:
        ts_str = f.read().strip()
    try:
        last = datetime.fromisoformat(ts_str)
        diff = int((datetime.now(timezone.utc) - last).total_seconds())
        return diff < STALE_AFTER, diff
    except Exception:
        return False, 9999


# ── MT5 Connection Manager ─────────────────────────────────────────────────────

def ensure_mt5_connected(max_attempts: int = 5) -> bool:
    """
    Check MT5 connection and reconnect if needed.
    Returns True if connected after attempts.
    """
    import MetaTrader5 as mt5
    for attempt in range(1, max_attempts + 1):
        if mt5.terminal_info() is not None:
            return True  # Still connected
        print(f"[WATCHDOG] MT5 disconnected. Reconnect attempt {attempt}/{max_attempts}...")
        try:
            mt5.shutdown()
            time.sleep(3)
            mt5c.connect()
            if mt5.terminal_info() is not None:
                print("[WATCHDOG] MT5 reconnected successfully.")
                tg._send("🔄 *MT5 reconnected* after disconnection.")
                return True
        except Exception as e:
            print(f"[WATCHDOG] Reconnect failed: {e}")
            time.sleep(10)
    tg._send("🚨 *MT5 reconnect FAILED* after 5 attempts. Manual intervention needed.")
    return False


# ── Memory Monitor ─────────────────────────────────────────────────────────────

def check_memory() -> float:
    """Return current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def memory_ok() -> bool:
    mb = check_memory()
    if mb > MAX_MEMORY_MB:
        print(f"[WATCHDOG] Memory usage {mb:.0f}MB > limit {MAX_MEMORY_MB}MB")
        return False
    return True


# ── Process-Level Watchdog (wraps main.py) ────────────────────────────────────

class BotWatchdog:
    """
    Runs main.py as a subprocess and auto-restarts it on failure.
    This is the outer wrapper that ensures 24/7 operation.
    """
    def __init__(self):
        self.restart_count  = 0
        self.process        = None
        self.running        = True

    def start(self):
        print("[WATCHDOG] Starting Forex AI Bot with 24/7 watchdog...")
        tg._send("🤖 *Forex AI Bot Watchdog started* — 24/7 monitoring active.")

        while self.running and self.restart_count < MAX_RESTART_COUNT:
            self._run()

        if self.restart_count >= MAX_RESTART_COUNT:
            msg = f"🚨 *Bot stopped* after {MAX_RESTART_COUNT} restarts. Manual fix needed."
            print(f"[WATCHDOG] {msg}")
            tg._send(msg)

    def _run(self):
        print(f"[WATCHDOG] Launching main.py (restart #{self.restart_count})...")
        self.process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        exit_code = self.process.wait()

        if exit_code == 0:
            print("[WATCHDOG] Bot exited cleanly (code 0). Not restarting.")
            self.running = False
            return

        self.restart_count += 1
        print(f"[WATCHDOG] Bot crashed (code {exit_code}). Restart {self.restart_count}/{MAX_RESTART_COUNT} in {RESTART_DELAY}s...")
        tg._send(f"⚠️ *Bot crashed* (exit {exit_code}). Restarting in {RESTART_DELAY}s... ({self.restart_count}/{MAX_RESTART_COUNT})")
        time.sleep(RESTART_DELAY)

    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()


# ── Thread-based heartbeat writer (call from main.py) ─────────────────────────

class HeartbeatThread(threading.Thread):
    """Background thread that writes heartbeat every 60s."""
    def __init__(self):
        super().__init__(daemon=True)
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            write_heartbeat()
            self._stop.wait(HEARTBEAT_INTERVAL)

    def stop(self):
        self._stop.set()


# ── Windows Service Setup ─────────────────────────────────────────────────────

def install_windows_service():
    """
    Register the bot as a Windows service using NSSM.
    NSSM must be installed: https://nssm.cc/download
    Run this once as Administrator.
    """
    bot_dir  = os.path.dirname(os.path.abspath(__file__))
    py_path  = sys.executable
    script   = os.path.join(bot_dir, "watchdog.py")
    svc_name = "ForexAIBot"

    cmds = [
        f'nssm install {svc_name} "{py_path}" "{script}"',
        f'nssm set {svc_name} AppDirectory "{bot_dir}"',
        f'nssm set {svc_name} DisplayName "Forex AI Trading Bot"',
        f'nssm set {svc_name} Description "Currency Strength + Renko + AI Trading Bot"',
        f'nssm set {svc_name} Start SERVICE_AUTO_START',
        f'nssm set {svc_name} AppRestartDelay 30000',
        f'nssm set {svc_name} AppStdout "{bot_dir}\\logs\\service_stdout.log"',
        f'nssm set {svc_name} AppStderr "{bot_dir}\\logs\\service_stderr.log"',
    ]

    print(f"[WATCHDOG] Installing Windows service '{svc_name}'...")
    for cmd in cmds:
        ret = os.system(cmd)
        if ret != 0:
            print(f"[WATCHDOG] Command failed: {cmd}")
            print("[WATCHDOG] Ensure NSSM is installed and run as Administrator.")
            return False

    os.system(f"nssm start {svc_name}")
    print(f"[WATCHDOG] Service '{svc_name}' installed and started.")
    print(f"[WATCHDOG] Manage with: nssm start/stop/restart {svc_name}")
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--install-service" in args:
        install_windows_service()
    else:
        watchdog = BotWatchdog()
        try:
            watchdog.start()
        except KeyboardInterrupt:
            print("\n[WATCHDOG] Stopped by user.")
            watchdog.stop()
