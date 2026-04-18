# fix_task.ps1 — Fix FXPulse Scheduled Task working directory
# Run on VPS: powershell -ExecutionPolicy Bypass -File C:\fxpulse\fix_task.ps1

Stop-ScheduledTask FXPulse -ErrorAction SilentlyContinue
Stop-ScheduledTask FXPulseMonitor -ErrorAction SilentlyContinue

$a1 = New-ScheduledTaskAction -Execute "C:\Python310\python.exe" -Argument "orchestrator.py" -WorkingDirectory "C:\fxpulse"
$a2 = New-ScheduledTaskAction -Execute "C:\Python310\python.exe" -Argument "health_monitor.py" -WorkingDirectory "C:\fxpulse"
$principal = New-ScheduledTaskPrincipal -UserId "Administrator" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew

Set-ScheduledTask -TaskName "FXPulse" -Action $a1 -Principal $principal -Settings $settings
Set-ScheduledTask -TaskName "FXPulseMonitor" -Action $a2 -Principal $principal -Settings $settings

Start-ScheduledTask FXPulse
Start-ScheduledTask FXPulseMonitor

Get-ScheduledTask | Where-Object {$_.TaskName -like "FXPulse*"} | Select TaskName, State
Write-Host "Done — tasks fixed and restarted."
