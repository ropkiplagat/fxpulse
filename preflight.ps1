# ==============================================================================
# FXPulse Pre-Flight Check — run BEFORE starting the service
# Usage: powershell -ExecutionPolicy Bypass -File C:\fxpulse\preflight.ps1
# Checks: Python version, package compatibility, imports, MT5, NSSM, dirs
# ==============================================================================

$PythonExe  = "C:\Program Files\Python311\python.exe"
$BotDir     = "C:\fxpulse"
$ServiceName= "FXPulse"
$sep        = "=" * 70
$pass       = 0
$fail       = 0
$warnings   = @()
$errors     = @()

function OK($msg)   { Write-Host "  [PASS] $msg" -f Green;  $script:pass++ }
function FAIL($msg) { Write-Host "  [FAIL] $msg" -f Red;    $script:fail++; $script:errors += $msg }
function WARN($msg) { Write-Host "  [WARN] $msg" -f Yellow; $script:warnings += $msg }

Write-Host ""
Write-Host $sep -f Cyan
Write-Host "  FXPulse Pre-Flight Check" -f Cyan
Write-Host $sep -f Cyan

# ── 1. Python exists ──────────────────────────────────────────────────────────
Write-Host "`n[ 1 ] Python Executable" -f White
if (Test-Path $PythonExe) {
    $ver = & "$PythonExe" --version 2>&1
    OK "Found: $ver at $PythonExe"
    # Must be 3.9 - 3.11 (3.12+ breaks several packages)
    if ($ver -match "3\.(\d+)") {
        $minor = [int]$Matches[1]
        if ($minor -lt 9)  { FAIL "Python too old — need 3.9+" }
        elseif ($minor -gt 11) { WARN "Python 3.$minor — some packages may not support it yet. 3.11 recommended." }
        else { OK "Python version 3.$minor is in the supported range (3.9-3.11)" }
    }
} else {
    FAIL "Python not found at $PythonExe — check installation path"
}

# ── 2. Package versions ───────────────────────────────────────────────────────
Write-Host "`n[ 2 ] Package Compatibility" -f White

$pkgScript = @"
import sys, importlib, pkg_resources

checks = [
    # (package_name, import_name, min_ver, max_ver, reason)
    ("numpy",        "numpy",        "1.24", "1.99",  "numpy 2.x breaks Python 3.11 (randbits error)"),
    ("pandas",       "pandas",       "2.0",  "2.99",  "pandas 3.x incompatible with numpy<2"),
    ("MetaTrader5",  "MetaTrader5",  "5.0",  "99.99", ""),
    ("scikit-learn", "sklearn",      "1.3",  "99.99", ""),
    ("xgboost",      "xgboost",      "2.0",  "99.99", ""),
    ("flask",        "flask",        "3.0",  "99.99", ""),
    ("requests",     "requests",     "2.31", "99.99", ""),
    ("ta",           "ta",           "0.11", "99.99", ""),
    ("cryptography", "cryptography", "42.0", "99.99", ""),
    ("psutil",       "psutil",       "5.9",  "99.99", ""),
]

all_ok = True
for pkg, imp, min_v, max_v, note in checks:
    try:
        installed = pkg_resources.get_distribution(pkg).version
        parts = installed.split(".")
        major_minor = float(f"{parts[0]}.{parts[1]}" if len(parts)>1 else parts[0])
        min_f = float(min_v); max_f = float(max_v)
        if major_minor < min_f:
            print(f"FAIL|{pkg}=={installed} too old (need >={min_v})")
            all_ok = False
        elif major_minor > max_f:
            note_txt = f" — {note}" if note else ""
            print(f"FAIL|{pkg}=={installed} too new (need <={max_v}){note_txt}")
            all_ok = False
        else:
            print(f"PASS|{pkg}=={installed}")
    except Exception as e:
        print(f"FAIL|{pkg} not installed ({e})")
        all_ok = False

sys.exit(0 if all_ok else 1)
"@

$pkgResult = & "$PythonExe" -c $pkgScript 2>&1
$pkgOK = $true
foreach ($line in $pkgResult) {
    if ($line -match "^PASS\|(.+)") { OK $Matches[1] }
    elseif ($line -match "^FAIL\|(.+)") { FAIL $Matches[1]; $pkgOK = $false }
    else { Write-Host "  $line" -f DarkGray }
}

# ── 3. Import test (all bot modules) ─────────────────────────────────────────
Write-Host "`n[ 3 ] Bot Module Imports" -f White

$importScript = @"
import sys
sys.path.insert(0, r'$BotDir')
modules = ['config', 'mt5_connector', 'signals', 'trade_manager',
           'performance_log', 'ai_predictor', 'regime_detector',
           'news_filter', 'currency_strength', 'telegram_alerts',
           'telegram_bot', 'security', 'watchdog', 'executor']
failed = []
for m in modules:
    try:
        __import__(m)
        print(f'PASS|{m}')
    except Exception as e:
        print(f'FAIL|{m}: {e}')
        failed.append(m)
sys.exit(len(failed))
"@

$importResult = & "$PythonExe" -c $importScript 2>&1
foreach ($line in $importResult) {
    if ($line -match "^PASS\|(.+)") { OK "import $($Matches[1])" }
    elseif ($line -match "^FAIL\|(.+)") { FAIL "import $($Matches[1])" }
}

# ── 4. MT5 terminal installed ─────────────────────────────────────────────────
Write-Host "`n[ 4 ] MetaTrader5 Terminal" -f White

$mt5Paths = @(
    "$env:ProgramFiles\MetaTrader 5\terminal64.exe",
    "${env:ProgramFiles(x86)}\MetaTrader 5\terminal64.exe"
)
$mt5Found = $mt5Paths | Where-Object { Test-Path $_ }
if ($mt5Found) {
    OK "MT5 terminal found: $mt5Found"
} else {
    # Broader search
    $broader = Get-ChildItem "$env:ProgramFiles" -Filter "terminal64.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($broader) { OK "MT5 terminal found: $($broader.FullName)" }
    else { FAIL "MT5 terminal NOT installed — bot cannot connect to broker. Run C:\mt5setup.exe" }
}

# ── 5. Required files & directories ──────────────────────────────────────────
Write-Host "`n[ 5 ] Required Files & Directories" -f White

$required = @(
    "C:\fxpulse\main.py",
    "C:\fxpulse\config.py",
    "C:\fxpulse\mt5_connector.py",
    "C:\fxpulse\requirements.txt"
)
foreach ($f in $required) {
    if (Test-Path $f) { OK "Found: $f" } else { FAIL "Missing: $f" }
}

$dirs = @("C:\fxpulse\logs", "C:\fxpulse\models")
foreach ($d in $dirs) {
    if (Test-Path $d) { OK "Dir exists: $d" }
    else {
        New-Item $d -ItemType Directory -Force | Out-Null
        WARN "Created missing dir: $d"
    }
}

# ── 6. NSSM service configuration ────────────────────────────────────────────
Write-Host "`n[ 6 ] NSSM Service Configuration" -f White

$scOut = sc.exe query $ServiceName 2>&1
if ($scOut -match "SERVICE_NAME") {
    OK "Service '$ServiceName' is registered in Windows SCM"
    $state = ($scOut | Where-Object { $_ -match "STATE" }) -replace ".*STATE.*:.*\d\s+", ""
    if ($scOut -match "RUNNING")  { OK "Service state: RUNNING" }
    elseif ($scOut -match "STOPPED") { WARN "Service state: STOPPED — run: nssm start $ServiceName" }
    elseif ($scOut -match "PAUSED")  { WARN "Service state: PAUSED — run: nssm stop $ServiceName then nssm start $ServiceName" }
    else { WARN "Service state: $state" }
} else {
    FAIL "Service '$ServiceName' not found in SCM — re-install with nssm install"
}

$nssmApp = nssm get $ServiceName Application 2>&1
if ($nssmApp -match [regex]::Escape($PythonExe)) { OK "NSSM Application path correct" }
else { FAIL "NSSM Application path wrong: $nssmApp" }

$nssmDir = nssm get $ServiceName AppDirectory 2>&1
if ($nssmDir -match [regex]::Escape($BotDir)) { OK "NSSM AppDirectory correct" }
else { FAIL "NSSM AppDirectory wrong: $nssmDir" }

# ── 7. Final summary ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host $sep -f Cyan
Write-Host "  PREFLIGHT SUMMARY" -f Cyan
Write-Host $sep -f Cyan
Write-Host "  Passed : $pass" -f Green
Write-Host "  Failed : $fail" -f $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "  Warnings: $($warnings.Count)" -f Yellow

if ($errors.Count -gt 0) {
    Write-Host "`n  ERRORS TO FIX:" -f Red
    $errors | ForEach-Object { Write-Host "    - $_" -f Red }
}
if ($warnings.Count -gt 0) {
    Write-Host "`n  WARNINGS:" -f Yellow
    $warnings | ForEach-Object { Write-Host "    - $_" -f Yellow }
}

Write-Host ""
if ($fail -eq 0) {
    Write-Host "  VERDICT: ALL CHECKS PASSED — safe to start FXPulse" -f Green
    Write-Host "  Run: cmd /c `"nssm start $ServiceName`"" -f Green
} else {
    Write-Host "  VERDICT: $fail CHECK(S) FAILED — fix errors before starting" -f Red
}
Write-Host $sep -f Cyan
Write-Host ""

exit $fail
