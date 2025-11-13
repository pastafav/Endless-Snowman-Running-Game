Param(
  [string]$Python = "python"
)

# Build SnowSurvivor Windows .exe using PyInstaller
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Join-Path $repo ".."
Set-Location $repo

& $Python -m pip install -U pip
if (Test-Path requirements.txt) {
  try { & $Python -m pip install -U -r requirements.txt } catch {}
}
if (Test-Path requirements-build.txt) {
  & $Python -m pip install -U -r requirements-build.txt
} else {
  & $Python -m pip install -U pyinstaller
}

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# Use inline args on Windows if spec causes issues. Spec should also work.
& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --name SnowSurvivor `
  --add-data "olaf-v2\image;image" `
  --add-data "olaf-v2\sound;sound" `
  --windowed `
  olaf-v2\run.py

$newOut = "dist\SnowSurvivor-win"
New-Item -ItemType Directory -Force -Path $newOut | Out-Null
if (Test-Path "dist\SnowSurvivor.exe") { Copy-Item "dist\SnowSurvivor.exe" $newOut }
if (Test-Path "dist\SnowSurvivor") { Copy-Item -Recurse -Force "dist\SnowSurvivor" $newOut }

Set-Content -Path (Join-Path $newOut 'Run on Windows.txt') -Value @'
Double-click SnowSurvivor.exe to play.
If SmartScreen warns, click More info → Run anyway.
'@

Write-Host "Built Windows exe at: $newOut"
