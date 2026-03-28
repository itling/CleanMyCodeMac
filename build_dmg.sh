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
    echo "缺少命令: $1"
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

  echo "清理旧产物 ($arch)..."
  rm -rf "$build_dir" "$dist_dir" "$dmg_path"

  echo "构建 .app ($arch) ..."
  PYINSTALLER_TARGET_ARCH="$arch" "$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "$dist_dir" \
    --workpath "$build_dir" \
    "$PROJECT_DIR/CleanMyCodeMac.spec"

  if [[ ! -d "$app_bundle" ]]; then
    echo "构建失败，未生成应用包: $app_bundle"
    exit 1
  fi

  mkdir -p "$dmg_staging_dir"
  cp -R "$app_bundle" "$dmg_staging_dir/"
  ln -sfn /Applications "$dmg_staging_dir/Applications"

  echo "生成 .dmg ($arch) ..."
  hdiutil create \
    -volname "$APP_NAME $arch" \
    -srcfolder "$dmg_staging_dir" \
    -ov \
    -format UDZO \
    "$dmg_path"

  echo "构建完成 ($arch):"
  echo "APP: $app_bundle"
  echo "DMG: $dmg_path"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "该脚本仅支持在 macOS 上执行。"
  exit 1
fi

require_cmd hdiutil
require_cmd python3

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "未找到 Python 解释器: $PYTHON_BIN"
  echo "可通过环境变量 PYTHON_BIN 指定，例如:"
  echo "PYTHON_BIN=/path/to/python3 ./build_dmg.sh"
  exit 1
fi

if [[ ! -x "$PIP_BIN" ]]; then
  echo "未找到 pip: $PIP_BIN"
  echo "可通过环境变量 PIP_BIN 指定，例如:"
  echo "PIP_BIN=/path/to/pip3 ./build_dmg.sh"
  exit 1
fi

if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "正在安装构建依赖..."
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
    echo "不支持的架构参数: $arch_input"
    echo "可用值: x86_64, arm64, all"
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
