# FXPulse v2 Setup

New-Item -ItemType Directory -Force -Path C:\fxpulse-v2 | Out-Null
New-Item -ItemType Directory -Force -Path C:\fxpulse-v2\data | Out-Null
New-Item -ItemType Directory -Force -Path C:\fxpulse-v2\logs | Out-Null
Write-Host "Folders created" -ForegroundColor Green

$base = "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/fxpulse-v2"

Invoke-WebRequest -Uri "$base/config.py" -OutFile "C:\fxpulse-v2\config.py"
Write-Host "config.py downloaded" -ForegroundColor Green

Invoke-WebRequest -Uri "$base/brain.py" -OutFile "C:\fxpulse-v2\brain.py"
Write-Host "brain.py downloaded" -ForegroundColor Green

if (Test-Path "C:\fxpulse\.env") {
    Copy-Item "C:\fxpulse\.env" "C:\fxpulse-v2\.env"
    Write-Host "env copied" -ForegroundColor Green
}

C:\Python310\python.exe -c "import sys; sys.path.insert(0, 'C:/fxpulse-v2'); import config; print('config OK')"

Write-Host "Done. Now run brain.py" -ForegroundColor Green
