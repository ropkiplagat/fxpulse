cd C:\fxpulse
Stop-ScheduledTask -TaskName "FXPulse" -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName "FXPulseMonitor" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/main.py" -OutFile "C:\fxpulse\main.py"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/config.py" -OutFile "C:\fxpulse\config.py"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/copy_trades.py" -OutFile "C:\fxpulse\copy_trades.py"
.\venv\Scripts\pip install pycryptodome
$e = Get-Content ".\.env" -Raw
if ($e -notmatch "MT5_ENCRYPT_SECRET") { Add-Content ".\.env" "MT5_ENCRYPT_SECRET=fxpulse-mt5-enc-v1-changeme-on-server" }
.\venv\Scripts\python.exe -c "import config; import copy_trades; print('Imports OK')"
Start-ScheduledTask -TaskName "FXPulse"
Start-ScheduledTask -TaskName "FXPulseMonitor"
Get-ScheduledTask | Where-Object {$_.TaskName -like "FXPulse*"} | Select-Object TaskName, State
