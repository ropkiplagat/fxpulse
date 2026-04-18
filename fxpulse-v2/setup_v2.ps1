# FXPulse v2 Setup
$base = 'https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/fxpulse-v2'
$dir  = 'C:\fxpulse-v2'

New-Item -ItemType Directory -Force -Path $dir        | Out-Null
New-Item -ItemType Directory -Force -Path "$dir\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$dir\logs" | Out-Null
Write-Host 'Folders created' -ForegroundColor Green

iwr -Uri "$base/config.py" -OutFile "$dir\config.py"
Write-Host 'config.py downloaded' -ForegroundColor Green

iwr -Uri "$base/brain.py" -OutFile "$dir\brain.py"
Write-Host 'brain.py downloaded' -ForegroundColor Green

$src = 'C:\fxpulse\.env'
$dst = "$dir\.env"
if (Test-Path $src) {
    Copy-Item $src $dst
    Write-Host 'env copied' -ForegroundColor Green
} else {
    Write-Host 'No .env found - create one manually' -ForegroundColor Yellow
}

& 'C:\Python310\python.exe' -c "import sys; sys.path.insert(0,'C:/fxpulse-v2'); import config; print('config OK')"

Write-Host 'Done. Now run: C:\Python310\python.exe C:\fxpulse-v2\brain.py' -ForegroundColor Green
