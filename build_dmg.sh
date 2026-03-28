#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python3}"
PIP_BIN="${PIP_BIN:-$VENV_DIR/bin/pip3}"
APP_NAME="CleanMyCodeMac"
APP_BUNDLE="$PROJECT_DIR/dist/$APP_NAME.app"
DMG_STAGING_DIR="$PROJECT_DIR/dist/dmg"
DMG_NAME="${APP_NAME}.dmg"
DMG_PATH="$PROJECT_DIR/dist/$DMG_NAME"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1"
    exit 1
  fi
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

echo "清理旧产物..."
rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/dist"

echo "构建 .app ..."
"$PYTHON_BIN" -m PyInstaller --noconfirm "$PROJECT_DIR/CleanMyCodeMac.spec"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "构建失败，未生成应用包: $APP_BUNDLE"
  exit 1
fi

mkdir -p "$DMG_STAGING_DIR"
cp -R "$APP_BUNDLE" "$DMG_STAGING_DIR/"
ln -sfn /Applications "$DMG_STAGING_DIR/Applications"

echo "生成 .dmg ..."
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "构建完成:"
echo "APP: $APP_BUNDLE"
echo "DMG: $DMG_PATH"

