# setup_tasks.ps1 — Register FXPulse Scheduled Tasks (DOE architecture)
# Run once on VPS: C:\Python310\python.exe orchestrator.py (not main.py directly)
# Usage: powershell -ExecutionPolicy Bypass -File C:\fxpulse\setup_tasks.ps1

$Python  = "C:\Python310\python.exe"
$BotDir  = "C:\fxpulse"

# ── Remove old tasks ──────────────────────────────────────────────────────────
foreach ($t in @("FXPulse","FXPulseMonitor")) {
    Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed old task: $t"
}

# ── FXPulse — Orchestrator (replaces direct main.py) ─────────────────────────
$action  = New-ScheduledTaskAction -Execute $Python -Argument "orchestrator.py" -WorkingDirectory $BotDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings= New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
           -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "Administrator" -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName "FXPulse" -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force
Write-Host "Registered: FXPulse -> orchestrator.py"

# ── FXPulseMonitor — Health monitor ──────────────────────────────────────────
$action2  = New-ScheduledTaskAction -Execute $Python -Argument "health_monitor.py" -WorkingDirectory $BotDir
$trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "FXPulseMonitor" -Action $action2 -Trigger $trigger2 `
    -Settings $settings -Principal $principal -Force
Write-Host "Registered: FXPulseMonitor -> health_monitor.py"

Write-Host ""
Write-Host "Starting tasks..."
Start-ScheduledTask -TaskName "FXPulse"
Start-ScheduledTask -TaskName "FXPulseMonitor"

Get-ScheduledTask | Where-Object {$_.TaskName -like "FXPulse*"} | Select TaskName, State
Write-Host "Done."
