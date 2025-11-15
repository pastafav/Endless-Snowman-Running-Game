#!/usr/bin/env zsh
set -euo pipefail

# Build SnowSurvivor macOS .app using PyInstaller (CLI fallback when spec is missing)
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

# If a spec file exists use it, otherwise use the CLI (bundles image/ and sound/ from olaf-v2)
if [ -f snow_survivor.spec ]; then
  pyinstaller snow_survivor.spec
else
  pyinstaller \
    --noconfirm \
    --clean \
    --name SnowSurvivor \
    --add-data "olaf-v2/image:image" \
    --add-data "olaf-v2/sound:sound" \
    --windowed \
    olaf-v2/run.py
fi

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
