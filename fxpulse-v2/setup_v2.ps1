# FXPulse v2 Setup — runs on VPS, creates everything from scratch
# Single paste: iwr https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/fxpulse-v2/setup_v2.ps1 -o C:\setup_v2.ps1; powershell -ExecutionPolicy Bypass -File C:\setup_v2.ps1

# Create folders
New-Item -ItemType Directory -Force -Path C:\fxpulse-v2 | Out-Null
New-Item -ItemType Directory -Force -Path C:\fxpulse-v2\data | Out-Null
New-Item -ItemType Directory -Force -Path C:\fxpulse-v2\logs | Out-Null
Write-Host "Folders created" -ForegroundColor Green

# Download all v2 files
$base = "https://raw.githubusercontent.com/ropkiplagat/fxpulse/main/fxpulse-v2"
$files = @("config.py", "brain.py")

foreach ($f in $files) {
    Invoke-WebRequest -Uri "$base/$f" -OutFile "C:\fxpulse-v2\$f"
    Write-Host "Downloaded: $f" -ForegroundColor Green
}

# Copy .env from old install if exists
if (Test-Path "C:\fxpulse\.env") {
    Copy-Item "C:\fxpulse\.env" "C:\fxpulse-v2\.env"
    Write-Host "Copied .env from C:\fxpulse" -ForegroundColor Green
} else {
    Write-Host ".env not found — create C:\fxpulse-v2\.env manually" -ForegroundColor Yellow
}

# Test imports
Write-Host "Testing imports..." -ForegroundColor Cyan
C:\Python310\python.exe -c "import sys; sys.path.insert(0,'C:\fxpulse-v2'); import config; print('config OK')"

Write-Host ""
Write-Host "Setup complete. Run brain:" -ForegroundColor Green
Write-Host "  C:\Python310\python.exe C:\fxpulse-v2\brain.py"
