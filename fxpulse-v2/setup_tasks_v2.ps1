# setup_tasks_v2.ps1 — FXPulse v2 Scheduled Tasks
# Run on VPS: powershell -ExecutionPolicy Bypass -File C:\fxpulse-v2\setup_tasks_v2.ps1

$py  = 'C:\Python310\python.exe'
$dir = 'C:\fxpulse-v2'
$pri = New-ScheduledTaskPrincipal -UserId 'Administrator' -LogonType Interactive -RunLevel Highest
$cfg = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)

# Stop existing v2 tasks if running
foreach ($t in @('FXPulseV2-Brain','FXPulseV2-Executor','FXPulseV2-Heartbeat','FXPulseV2-Monitor')) {
    Stop-ScheduledTask  -TaskName $t -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
}

# TASK 1 — Brain (signal scanner, runs forever)
$a1 = New-ScheduledTaskAction -Execute $py -Argument 'brain.py' -WorkingDirectory $dir
Register-ScheduledTask -TaskName 'FXPulseV2-Brain' -Action $a1 -Principal $pri -Settings $cfg `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Description 'FXPulse v2: scans 28 pairs every 60s'
Write-Host 'Registered: FXPulseV2-Brain' -ForegroundColor Green

# TASK 2 — Executor (trade execution, runs forever)
$a2 = New-ScheduledTaskAction -Execute $py -Argument 'executor.py' -WorkingDirectory $dir
Register-ScheduledTask -TaskName 'FXPulseV2-Executor' -Action $a2 -Principal $pri -Settings $cfg `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Description 'FXPulse v2: executes trades from signals.json'
Write-Host 'Registered: FXPulseV2-Executor' -ForegroundColor Green

# TASK 3 — Heartbeat (GitHub ping every 30s, runs forever)
$a3 = New-ScheduledTaskAction -Execute $py -Argument 'heartbeat.py' -WorkingDirectory $dir
Register-ScheduledTask -TaskName 'FXPulseV2-Heartbeat' -Action $a3 -Principal $pri -Settings $cfg `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Description 'FXPulse v2: heartbeat push to GitHub every 30s'
Write-Host 'Registered: FXPulseV2-Heartbeat' -ForegroundColor Green

# TASK 4 — Monitor (checks heartbeat, alerts if stale)
$a4 = New-ScheduledTaskAction -Execute $py -Argument 'monitor.py' -WorkingDirectory $dir
Register-ScheduledTask -TaskName 'FXPulseV2-Monitor' -Action $a4 -Principal $pri -Settings $cfg `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Description 'FXPulse v2: fires Telegram/SMS if heartbeat dies'
Write-Host 'Registered: FXPulseV2-Monitor' -ForegroundColor Green

# Start all 4
foreach ($t in @('FXPulseV2-Brain','FXPulseV2-Executor','FXPulseV2-Heartbeat','FXPulseV2-Monitor')) {
    Start-ScheduledTask -TaskName $t
}

Write-Host ''
Get-ScheduledTask | Where-Object {$_.TaskName -like 'FXPulseV2*'} | Select-Object TaskName,State
Write-Host ''
Write-Host 'GATE 11 complete — all 4 tasks running.' -ForegroundColor Cyan
