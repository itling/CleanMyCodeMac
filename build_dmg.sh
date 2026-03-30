#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python3}"
PIP_BIN="${PIP_BIN:-$VENV_DIR/bin/pip3}"
APP_NAME="CleanMyCodeMac"
DIST_ROOT="$PROJECT_DIR/dist"
BUILD_ROOT="$PROJECT_DIR/build"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

normalize_arch() {
  case "$1" in
    x86_64|amd64)
      echo "x86_64"
      ;;
    arm64|aarch64)
      echo "arm64"
      ;;
    *)
      echo ""
      ;;
  esac
}

build_one_arch() {
  local arch="$1"
  local dist_dir="$DIST_ROOT/$arch"
  local build_dir="$BUILD_ROOT/$arch"
  local app_bundle="$dist_dir/$APP_NAME.app"
  local dmg_staging_dir="$dist_dir/dmg"
  local dmg_name="${APP_NAME}-${arch}.dmg"
  local dmg_path="$DIST_ROOT/$dmg_name"

  echo "Cleaning previous build ($arch)..."
  rm -rf "$build_dir" "$dist_dir" "$dmg_path"

  echo "Building .app ($arch)..."
  PYINSTALLER_TARGET_ARCH="$arch" "$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$dist_dir" \
    --workpath "$build_dir" \
    "$PROJECT_DIR/CleanMyCodeMac.spec"

  if [[ ! -d "$app_bundle" ]]; then
    echo "Build failed, app bundle not found: $app_bundle"
    exit 1
  fi

  mkdir -p "$dmg_staging_dir"
  cp -R "$app_bundle" "$dmg_staging_dir/"
  ln -sfn /Applications "$dmg_staging_dir/Applications"

  echo "Creating .dmg ($arch)..."
  hdiutil create \
    -volname "$APP_NAME $arch" \
    -srcfolder "$dmg_staging_dir" \
    -ov \
    -format UDZO \
    "$dmg_path"

  echo "Build complete ($arch):"
  echo "APP: $app_bundle"
  echo "DMG: $dmg_path"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script only runs on macOS."
  exit 1
fi

require_cmd hdiutil
require_cmd python3

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python interpreter not found: $PYTHON_BIN"
  echo "Override with PYTHON_BIN, e.g.:"
  echo "PYTHON_BIN=/path/to/python3 ./build_dmg.sh"
  exit 1
fi

if [[ ! -x "$PIP_BIN" ]]; then
  echo "pip not found: $PIP_BIN"
  echo "Override with PIP_BIN, e.g.:"
  echo "PIP_BIN=/path/to/pip3 ./build_dmg.sh"
  exit 1
fi

if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "Installing build dependencies..."
  "$PIP_BIN" install -r "$PROJECT_DIR/requirements-build.txt"
fi

ARCH_INPUTS=("$@")
if [[ ${#ARCH_INPUTS[@]} -eq 0 ]]; then
  ARCH_INPUTS=("$(uname -m)")
fi

ARCHS=()
for arch_input in "${ARCH_INPUTS[@]}"; do
  if [[ "$arch_input" == "all" ]]; then
    ARCHS+=("x86_64" "arm64")
    continue
  fi
  normalized_arch="$(normalize_arch "$arch_input")"
  if [[ -z "$normalized_arch" ]]; then
    echo "Unsupported architecture: $arch_input"
    echo "Valid values: x86_64, arm64, all"
    exit 1
  fi
  ARCHS+=("$normalized_arch")
done

SEEN_ARCHS=""
for arch in "${ARCHS[@]}"; do
  if [[ " $SEEN_ARCHS " == *" $arch "* ]]; then
    continue
  fi
  SEEN_ARCHS="$SEEN_ARCHS $arch"
  build_one_arch "$arch"
done
