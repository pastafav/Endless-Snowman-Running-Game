#!/usr/bin/env zsh
set -euo pipefail

# Build SnowSurvivor macOS .app using PyInstaller
REPO_DIR=${0:A:h}/..
cd "$REPO_DIR"

python3 -m pip install -U pip
if [ -f requirements.txt ]; then
  python3 -m pip install -U -r requirements.txt || true
fi
if [ -f requirements-build.txt ]; then
  python3 -m pip install -U -r requirements-build.txt
else
  python3 -m pip install -U pyinstaller
fi

# Clean previous builds
rm -rf build dist

# Build via spec (bundles image/ and sound/ from olaf-v2)
pyinstaller snow_survivor.spec

# Prepare release folder
APP_OUT="dist/SnowSurvivor-mac"
mkdir -p "$APP_OUT"
# Copy .app bundle and optional CLI exe if generated
if [ -d "dist/SnowSurvivor.app" ]; then
  cp -R "dist/SnowSurvivor.app" "$APP_OUT/"
fi
if [ -f "dist/SnowSurvivor" ]; then
  cp "dist/SnowSurvivor" "$APP_OUT/"
fi

# Helpful note
cat > "$APP_OUT/Run on macOS.txt" << 'EOF'
Open SnowSurvivor.app. If macOS blocks the app:
- Right-click the app → Open → Open
- Or System Settings → Privacy & Security → Allow Anyway
EOF

echo "Built macOS app at: $APP_OUT"
