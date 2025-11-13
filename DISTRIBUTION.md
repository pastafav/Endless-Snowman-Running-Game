# Ship Snow Survivor

This repo is ready to create downloadable executables for macOS, Windows, and Linux. The game entry point is `olaf-v2/run.py`.

## 0) Prereqs
- Python 3.10+ installed (3.12+ recommended)
- On macOS: run in Terminal app; on Windows: run in PowerShell

## 1) Build commands

### macOS (produces SnowSurvivor.app)
```sh
# From repo root
zsh scripts/build_mac.sh
open dist/SnowSurvivor-mac
```
- Output:
  - `dist/SnowSurvivor.app` (double‑clickable app bundle)
  - `dist/SnowSurvivor-mac/` folder with app and helper notes

If macOS Gatekeeper blocks the app, right‑click → Open → Open once, or allow from System Settings → Privacy & Security.

### Windows (produces SnowSurvivor.exe)
```powershell
# From repo root, in PowerShell
Set-ExecutionPolicy -Scope Process Bypass -Force
./scripts/build_win.ps1
Start-Process dist/SnowSurvivor-win
```
- Output:
  - `dist/SnowSurvivor.exe` and a `dist/SnowSurvivor/` onedir folder (depending on PyInstaller mode)
  - `dist/SnowSurvivor-win/` folder with the runnable files and helper notes

If Windows SmartScreen warns, click “More info” → “Run anyway”.

Or build via GitHub Actions (no Windows PC needed):

1) Commit and push to GitHub (the workflow is already added at `.github/workflows/windows-build.yml`).
2) On GitHub → Actions → “Build Windows EXE” → Run workflow.
3) After it completes, download artifact “SnowSurvivor-Windows” — it contains `SnowSurvivor.exe` and the onedir folder.

### Linux
```bash
bash scripts/build_linux.sh
ls -l dist/SnowSurvivor-linux
```
- Output: `dist/SnowSurvivor-linux/SnowSurvivor`

## 2) What’s included
- Assets are bundled automatically:
  - `olaf-v2/image` → bundled as `image/`
  - `olaf-v2/sound` → bundled as `sound/`
- The game automatically resolves asset paths in both source and packaged modes.

## 3) Quick local test
- macOS: `open dist/SnowSurvivor.app`
- Windows: double‑click `dist/SnowSurvivor.exe`
- Linux: `./dist/SnowSurvivor-linux/SnowSurvivor`

If audio is silent, ensure your OS audio is available to SDL2 and volume is up.

## 4) Create downloadable zips
From repo root after building:

```sh
# macOS zip
cd dist && zip -r SnowSurvivor-mac.zip SnowSurvivor.app && cd -

# Windows zip (from PowerShell)
Compress-Archive -Path dist/SnowSurvivor.exe, dist/SnowSurvivor -DestinationPath dist/SnowSurvivor-win.zip
# If using GitHub Actions artifact, you can zip the downloaded "SnowSurvivor-win" folder directly.

# Linux tar.gz
cd dist && tar czf SnowSurvivor-linux.tar.gz SnowSurvivor-linux && cd -
```

## 5) Share with others
- Preferred: upload the ZIPs to a GitHub Release and share the link
- Or share the zip files via Drive/Dropbox
- Recipients just unzip and run:
  - macOS: open the `.app` (may need right‑click → Open the first time)
  - Windows: double‑click `.exe` (SmartScreen may require “Run anyway”)
  - Linux: `chmod +x SnowSurvivor` then `./SnowSurvivor`

## 6) Troubleshooting
- Black window or crash at start:
  - Ensure assets exist inside the bundle: `image/` and `sound/` next to the executable or inside the `.app/Contents/Resources/` area.
  - Try rebuilding after `rm -rf build dist`.
- macOS says the app is “damaged”:
  - This usually means it was quarantined by Gatekeeper. Run: `xattr -r -d com.apple.quarantine dist/SnowSurvivor.app`
- Windows missing DLL error:
  - Rebuild using the provided script so all dependencies are included.

## 7) Notes
- Build scripts install only what’s needed: runtime `pygame`, build‑time `pyinstaller`.
- If you have a custom app icon, add it to `snow_survivor.spec` (the `BUNDLE` section) with `icon='path/to/icon.icns'` (macOS) and pass `--icon path\to\icon.ico` on Windows.
