#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$PROJECT_DIR/resources"
SOURCE_PNG="${SOURCE_PNG:-$RESOURCES_DIR/app_icon.png}"
GENERATED_DIR="$RESOURCES_DIR/generated_icons"
ICNS_PATH="$RESOURCES_DIR/app.icns"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python3}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script only runs on macOS."
  exit 1
fi

require_cmd sips

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "Python interpreter not found: ${PYTHON_BIN:-<empty>}"
  echo "Override with PYTHON_BIN, e.g.:"
  echo "PYTHON_BIN=/path/to/python3 ./build_icon.sh"
  exit 1
fi

mkdir -p "$GENERATED_DIR"

if [[ ! -f "$SOURCE_PNG" ]]; then
  "$PYTHON_BIN" "$PROJECT_DIR/scripts/generate_app_icon.py" >/dev/null
fi

if [[ ! -f "$SOURCE_PNG" ]]; then
  echo "Source icon not found: $SOURCE_PNG"
  exit 1
fi

rm -rf "$GENERATED_DIR"
mkdir -p "$GENERATED_DIR"

sips -z 16 16     "$SOURCE_PNG" --out "$GENERATED_DIR/icon_16x16.png" >/dev/null
sips -z 32 32     "$SOURCE_PNG" --out "$GENERATED_DIR/icon_32x32.png" >/dev/null
sips -z 64 64     "$SOURCE_PNG" --out "$GENERATED_DIR/icon_64x64.png" >/dev/null
sips -z 128 128   "$SOURCE_PNG" --out "$GENERATED_DIR/icon_128x128.png" >/dev/null
sips -z 256 256   "$SOURCE_PNG" --out "$GENERATED_DIR/icon_256x256.png" >/dev/null
sips -z 512 512   "$SOURCE_PNG" --out "$GENERATED_DIR/icon_512x512.png" >/dev/null
cp "$SOURCE_PNG" "$GENERATED_DIR/icon_1024x1024.png"

"$PYTHON_BIN" "$PROJECT_DIR/scripts/build_icns.py" >/dev/null

echo "Icon generated: $ICNS_PATH"
