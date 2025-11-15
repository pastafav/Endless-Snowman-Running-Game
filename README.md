# Endless-Snowman-Running-Game

This repository contains "Snow Survivor" — a small Pygame-based endless runner.

Quick status
- Play from source: supported (see instructions below).
- Build executables: scripts are provided for macOS, Linux and Windows (PyInstaller).

Prerequisites
- Python 3.8+ (3.10/3.11 recommended)
- pip
- For packaging: PyInstaller (see scripts/requirements-build.txt)

Run from source (developer or player)
1. Install requirements:

```bash
python3 -m pip install -U pip
python3 -m pip install -U -r requirements.txt
```

2. Run the game:

```bash
python3 olaf-v2/run.py
```

Build an executable
- macOS:

```bash
./scripts/build_mac.sh
```

- Linux:

```bash
./scripts/build_linux.sh
```

- Windows (PowerShell):

```powershell
./scripts/build_win.ps1 -Python python
```

Notes
- The build scripts use PyInstaller and will bundle `olaf-v2/image` and `olaf-v2/sound` into the app/binary.
- If you plan to redistribute a macOS `.app`, codesigning and notarization may be required to avoid gatekeeper warnings.
- If you want, I can (locally) produce the built artifacts for you — but I need access to a macOS/Linux/Windows runner with Python and PyInstaller installed.

If anything breaks when you try these, tell me the platform and the exact error output and I'll help fix it.