# VPS_INVENTORY.md — FXPulse Phase 1 Deployment Record
Generated: 2026-04-26

## VPS Access
- Host: 161.97.83.167
- User: Administrator
- Password: 2VKn282EEqF1c1
- RDP port: 3389 (primary access)
- SSH port: 22 (intermittent — restart with `Restart-Service sshd -Force` from RDP if down)

## File Paths on VPS
- Bot root: `C:\fxpulse\`
- Main entry: `C:\fxpulse\main.py`
- Config: `C:\fxpulse\config.py`
- Secrets: `C:\fxpulse\.env` (never committed to git)
- Logs: `C:\fxpulse\logs\`
- Models: `C:\fxpulse\models\`
- Bot state: `C:\fxpulse\logs\bot_state.json`
- Heartbeat: `C:\fxpulse\heartbeat.txt`

## Python
- Interpreter: `C:\Python310\python.exe`
- Venv (alt): `C:\fxpulse\venv\Scripts\python.exe`

## MT5 Terminal
- Path: `C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe`
- Account: 61508353
- Server: Pepperstone-Demo
- Symbols: all use `.a` suffix (e.g. EURUSD.a, GBPUSD.a)
- Startup shortcut: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PepperstoneMT5.lnk`

## .env Required Keys (values in C:\fxpulse\.env on VPS only — never committed)
```
MT5_LOGIN=<demo account number>
MT5_PASSWORD=<demo account password>
MT5_SERVER=Pepperstone-Demo
MT5_TERMINAL_PATH=C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe
GITHUB_TOKEN=<PAT with repo scope — regenerate at github.com/settings/tokens>
TWILIO_SID=<Twilio account SID>
TWILIO_TOKEN=<Twilio auth token>
TWILIO_FROM=<Twilio AU number>
SITEGROUND_API_KEY=<SiteGround API key>
```

## Scheduled Tasks
| Task | Trigger | What it runs |
|------|---------|--------------|
| FXPulse | At logon (interactive session) | `C:\fxpulse\watchdog.bat` → `main.py` |
| FXPulse-Agent | Every 2 min | `C:\fxpulse\agent.py` |
| FXPulseMonitor | Every 5 min | `C:\fxpulse\health_monitor.py` |

**CRITICAL:** FXPulse task must run as logged-in user (interactive session), NOT as SYSTEM/Session 0. MT5 IPC requires the same session as the terminal.

## Bethwel Trial Config (Phase 1)
- PAPER_TRADING = True (LOCKED)
- RISK_PERCENT = 0.5%
- MAX_DAILY_DRAWDOWN = 2.0%
- MAX_CONCURRENT_TRADES = 6
- Pairs: EURUSD.a, GBPUSD.a, USDJPY.a, AUDUSD.a, USDCAD.a
- Balance: $50,000 demo

## Dashboard
- URL: myforexpulse.com/dashboard.php
- Data source: bot_state.json pushed to GitHub every 60s
- Admin: myforexpulse.com/admin/waitlist.php

## GitHub
- Repo: github.com/ropkiplagat/fxpulse
- bot_state.json: in .gitignore (never committed)
- .env: in .gitignore (never committed)
- Deploy method: GitHub API PUT → VPS Invoke-WebRequest (never git push)

## Last Known Good Restart Command
Run from PowerShell on VPS (after MT5 is logged in with prices ticking):

```powershell
Stop-ScheduledTask FXPulse -ErrorAction SilentlyContinue
Stop-Process -Name python* -Force -ErrorAction SilentlyContinue
Start-Sleep 3
Start-ScheduledTask FXPulse
Start-Sleep 15
Get-Content C:\fxpulse\logs\service.log -Tail 10
Get-Content C:\fxpulse\logs\service_err.log -Tail 5
```

## Phase 1 Self-Healing Features (deployed 2026-04-26)
1. Pattern A mt5.initialize() — passes path+login+server so MT5 launches if not running
2. Retry loop — 5 attempts with 30s sleep, logs each failure
3. MT5 startup shortcut — auto-launches on Windows login
4. MAX_CONCURRENT_TRADES = 6 enforced in trade loop
5. AutoLogon — configure via Sysinternals AutoLogon tool (pending)

## Phase 2 (deferred — this week)
- Heartbeat watchdog + UptimeRobot external monitoring
- SMS escalation if bot down > 10 min

## Known Issues
- SSH service flaps under load — fix: Restart-Service sshd from RDP
- MT5 requires interactive desktop session for IPC (cannot run in Session 0)
- Twilio SMS currently stubbed — credentials confirmed but 401 error unresolved
