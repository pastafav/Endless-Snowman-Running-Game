#!/usr/bin/env bash
set -euo pipefail

# Build SnowSurvivor Linux executable using PyInstaller
REPO_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$REPO_DIR"

python3 -m pip install -U pip
[ -f requirements.txt ] && python3 -m pip install -U -r requirements.txt || true
[ -f requirements-build.txt ] && python3 -m pip install -U -r requirements-build.txt || python3 -m pip install -U pyinstaller

rm -rf build dist

pyinstaller \
  --noconfirm \
  --clean \
  --name SnowSurvivor \
  --add-data "olaf-v2/image:image" \
  --add-data "olaf-v2/sound:sound" \
  --windowed \
  olaf-v2/run.py

OUT="dist/SnowSurvivor-linux"
mkdir -p "$OUT"
[ -f "dist/SnowSurvivor" ] && cp "dist/SnowSurvivor" "$OUT/"
cat > "$OUT/Run on Linux.txt" << 'EOF'
If SDL or audio libraries are missing, install them via your distro.
Run: ./SnowSurvivor
EOF

echo "Built Linux binary at: $OUT"
