#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="${APP_PATH:-$PROJECT_DIR/dist/CleanMyCodeMac.app}"
DMG_PATH="${DMG_PATH:-$PROJECT_DIR/dist/CleanMyCodeMac.dmg}"

APPLE_ID="${APPLE_ID:-}"
TEAM_ID="${TEAM_ID:-}"
APP_PASSWORD="${APP_PASSWORD:-}"
DEVELOPER_ID_APP="${DEVELOPER_ID_APP:-}"

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

require_cmd codesign
require_cmd xcrun

if [[ -z "$DEVELOPER_ID_APP" ]]; then
  echo "请设置签名证书，例如："
  echo 'DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)" ./sign_and_notarize.sh'
  exit 1
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "未找到应用包: $APP_PATH"
  exit 1
fi

codesign --force --deep --options runtime --sign "$DEVELOPER_ID_APP" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

if [[ -f "$DMG_PATH" ]]; then
  codesign --force --sign "$DEVELOPER_ID_APP" "$DMG_PATH"
fi

if [[ -z "$APPLE_ID" || -z "$TEAM_ID" || -z "$APP_PASSWORD" ]]; then
  echo "签名已完成，未提供 notarization 参数，跳过公证。"
  echo "如需公证，请设置 APPLE_ID、TEAM_ID、APP_PASSWORD 后重试。"
  exit 0
fi

TARGET_PATH="$DMG_PATH"
if [[ ! -f "$TARGET_PATH" ]]; then
  TARGET_PATH="$APP_PATH"
fi

xcrun notarytool submit "$TARGET_PATH" \
  --apple-id "$APPLE_ID" \
  --password "$APP_PASSWORD" \
  --team-id "$TEAM_ID" \
  --wait

if [[ -f "$DMG_PATH" ]]; then
  xcrun stapler staple "$DMG_PATH"
else
  xcrun stapler staple "$APP_PATH"
fi

echo "签名与公证完成。"

