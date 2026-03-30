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
    echo "Missing command: $1"
    exit 1
  fi
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script only runs on macOS."
  exit 1
fi

require_cmd codesign
require_cmd xcrun

if [[ -z "$DEVELOPER_ID_APP" ]]; then
  echo "Please set the signing certificate, e.g.:"
  echo 'DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)" ./sign_and_notarize.sh'
  exit 1
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found: $APP_PATH"
  exit 1
fi

codesign --force --deep --options runtime --sign "$DEVELOPER_ID_APP" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

if [[ -f "$DMG_PATH" ]]; then
  codesign --force --sign "$DEVELOPER_ID_APP" "$DMG_PATH"
fi

if [[ -z "$APPLE_ID" || -z "$TEAM_ID" || -z "$APP_PASSWORD" ]]; then
  echo "Signing complete. Notarization skipped (APPLE_ID, TEAM_ID, APP_PASSWORD not set)."
  echo "To notarize, set those variables and re-run."
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

echo "Signing and notarization complete."
