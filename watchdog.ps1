# FXPulse Auto-Fix Watchdog
# Runs every 2 minutes. Fixes known crash types. SMS if unfixable.
# Incident log: 20 incidents Apr 10-14. 75% auto-fixable.

$BOT_DIR    = "C:\fxpulse"
$PYTHON     = "C:\Python310\python.exe"
$LOG        = "C:\fxpulse\logs\watchdog.log"
$ENV_FILE   = "C:\fxpulse\.env"
$FAIL_COUNT = "C:\fxpulse\logs\watchdog_fails.txt"

function Log($msg) {
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts UTC] $msg"
    Write-Host $line
    Add-Content -Path $LOG -Value $line -ErrorAction SilentlyContinue
}

function SendSMS($body) {
    $env_content = Get-Content $ENV_FILE -ErrorAction SilentlyContinue
    $sid   = ($env_content | Where-Object { $_ -match "^TWILIO_SID=" })  -replace "^TWILIO_SID=",""
    $token = ($env_content | Where-Object { $_ -match "^TWILIO_TOKEN=" }) -replace "^TWILIO_TOKEN=",""
    $from  = ($env_content | Where-Object { $_ -match "^TWILIO_FROM=" })  -replace "^TWILIO_FROM=",""
    if (-not $sid) { Log "[SMS] No Twilio creds in .env"; return }
    $url  = "https://api.twilio.com/2010-04-01/Accounts/$sid/Messages.json"
    $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${sid}:${token}"))
    $data = "To=%2B61431274377&From=$([Uri]::EscapeDataString($from))&Body=$([Uri]::EscapeDataString($body))"
    try {
        Invoke-RestMethod -Uri $url -Method POST -Headers @{Authorization="Basic $cred"} `
            -ContentType "application/x-www-form-urlencoded" -Body $data | Out-Null
        Log "[SMS] Sent: $($body.Substring(0,[Math]::Min(60,$body.Length)))"
    } catch { Log "[SMS] Failed: $_" }
}

function GetFailCount {
    if (Test-Path $FAIL_COUNT) { return [int](Get-Content $FAIL_COUNT) } else { return 0 }
}
function IncrFail { $n = (GetFailCount) + 1; Set-Content $FAIL_COUNT $n; return $n }
function ResetFail { Set-Content $FAIL_COUNT 0 }

New-Item -ItemType Directory -Force -Path "$BOT_DIR\logs" | Out-Null
Log "=== Watchdog check ==="

# ── P0: secrets.py shadow (caused 3 incidents, 12+ hours debug) ──────────────
if (Test-Path "$BOT_DIR\secrets.py") {
    Log "[P0] FIXING: secrets.py shadows Python stdlib — renaming"
    Rename-Item "$BOT_DIR\secrets.py" "$BOT_DIR\_secrets.py" -Force
    Log "[P0] Fixed: renamed to _secrets.py"
}

# ── P0: config.py syntax check ────────────────────────────────────────────────
$syntax = & $PYTHON -c "import py_compile; py_compile.compile('$BOT_DIR\config.py', doraise=True)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "[P0] config.py syntax error: $syntax"
    Log "[P0] Restoring config.py from GitHub"
    try {
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/config.py" `
            -OutFile "$BOT_DIR\config.py"
        # Re-inject token from .env
        $token = (Get-Content $ENV_FILE | Where-Object { $_ -match "^GITHUB_TOKEN=" }) -replace "^GITHUB_TOKEN=",""
        if ($token) {
            (Get-Content "$BOT_DIR\config.py") -replace 'GITHUB_TOKEN\s*=\s*""',"GITHUB_TOKEN = `"$token`"" |
                Set-Content "$BOT_DIR\config.py" -Encoding UTF8
        }
        Log "[P0] config.py restored from GitHub"
    } catch { Log "[P0] Restore failed: $_" }
}

# ── P0: siteground_api.py syntax check ───────────────────────────────────────
$sg_syntax = & $PYTHON -c "import py_compile; py_compile.compile('$BOT_DIR\siteground_api.py', doraise=True)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "[P0] siteground_api.py syntax error — restoring from GitHub"
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/siteground_api.py" `
        -OutFile "$BOT_DIR\siteground_api.py" -ErrorAction SilentlyContinue
}

# ── P1: MT5 running check ─────────────────────────────────────────────────────
$mt5 = Get-Process "terminal64" -ErrorAction SilentlyContinue
if (-not $mt5) {
    Log "[P1] MT5 not running — attempting launch"
    $mt5path = "C:\Program Files\MetaTrader 5\terminal64.exe"
    if (Test-Path $mt5path) {
        Start-Process $mt5path
        Start-Sleep 15
        Log "[P1] MT5 launched"
    } else {
        Log "[P1] MT5 exe not found at default path"
    }
}

# ── P1: Bot process check + auto-restart ──────────────────────────────────────
$bot = Get-Process "python" -ErrorAction SilentlyContinue
if (-not $bot) {
    Log "[P1] Bot not running — restarting FXPulse Scheduled Task"
    Stop-ScheduledTask  -TaskName "FXPulse" -ErrorAction SilentlyContinue
    Start-Sleep 2
    Start-ScheduledTask -TaskName "FXPulse"
    Start-Sleep 10
    $bot = Get-Process "python" -ErrorAction SilentlyContinue
    if ($bot) {
        Log "[P1] Bot restarted OK (PID $($bot.Id))"
        ResetFail
    } else {
        $fails = IncrFail
        Log "[P1] Bot restart FAILED (attempt $fails)"
        if ($fails -ge 3) {
            SendSMS "FXPulse CRITICAL: Bot wont start after $fails attempts. RDP to 161.97.83.167 and check MT5 + logs."
            ResetFail
        }
    }
} else {
    Log "[P1] Bot running OK (PID $($bot.Id))"
    ResetFail
}

# ── P1: GITHUB_TOKEN present ──────────────────────────────────────────────────
$token_check = & $PYTHON -c "import config; print('OK' if config.GITHUB_TOKEN else 'MISSING')" 2>&1
if ($token_check -ne "OK") {
    Log "[P1] GITHUB_TOKEN missing — re-injecting from .env"
    $token = (Get-Content $ENV_FILE | Where-Object { $_ -match "^GITHUB_TOKEN=" }) -replace "^GITHUB_TOKEN=",""
    if ($token) {
        (Get-Content "$BOT_DIR\config.py") -replace 'GITHUB_TOKEN\s*=\s*""',"GITHUB_TOKEN = `"$token`"" |
            Set-Content "$BOT_DIR\config.py" -Encoding UTF8
        Log "[P1] Token re-injected"
    }
}

# ── P2: Dashboard data freshness (GitHub) ────────────────────────────────────
try {
    $gh = Invoke-RestMethod -Uri "https://api.github.com/repos/ropkiplagat/fxpulse/commits?per_page=3" `
        -Headers @{"User-Agent"="FXPulse-Watchdog"} -TimeoutSec 10
    $last = [datetime]::Parse($gh[0].commit.committer.date).ToUniversalTime()
    $age  = [int]((Get-Date).ToUniversalTime() - $last).TotalMinutes
    Log "[P2] Last GitHub push: $age min ago"
    if ($age -gt 10) {
        Log "[P2] Data stale >10min — bot may not be pushing"
    }
} catch { Log "[P2] GitHub check failed: $_" }

# ── P2: Log rotation (keep last 1000 lines) ───────────────────────────────────
if (Test-Path $LOG) {
    $lines = Get-Content $LOG
    if ($lines.Count -gt 1000) {
        $lines[-1000..-1] | Set-Content $LOG
        Log "[P2] Log rotated"
    }
}

Log "=== Check complete ==="
