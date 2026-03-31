#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="CleanMyCodeMac"
APP_PATH="${APP_PATH:-}"
DMG_PATH="${DMG_PATH:-}"

read_dotenv_value() {
  local key="$1"
  local env_file="$PROJECT_DIR/.env"
  local line=""
  local value=""

  [[ -f "$env_file" ]] || return 1

  line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$env_file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 1

  value="${line#*=}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"

  if [[ "$value" =~ ^\".*\"$ ]] || [[ "$value" =~ ^\'.*\'$ ]]; then
    value="${value:1:${#value}-2}"
  fi

  printf '%s' "$value"
}

APPLE_ID="${APPLE_ID:-$(read_dotenv_value APPLE_ID || true)}"
TEAM_ID="${TEAM_ID:-$(read_dotenv_value TEAM_ID || true)}"
APP_PASSWORD="${APP_PASSWORD:-$(read_dotenv_value APP_PASSWORD || true)}"
DEVELOPER_ID_APP="${DEVELOPER_ID_APP:-$(read_dotenv_value DEVELOPER_ID_APP || true)}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

recreate_dmg_from_signed_app() {
  local app_bundle="$1"
  local dmg_path="$2"
  local stage_root
  local volume_name="$APP_NAME"

  stage_root="$(mktemp -d "${TMPDIR:-/tmp}/cleanmycodemac-sign-XXXXXX")"
  trap 'rm -rf "$stage_root"' RETURN

  mkdir -p "$stage_root"
  cp -R "$app_bundle" "$stage_root/"
  ln -sfn /Applications "$stage_root/Applications"
  rm -f "$dmg_path"

  hdiutil create \
    -volname "$volume_name" \
    -srcfolder "$stage_root" \
    -ov \
    -format UDZO \
    "$dmg_path"

  rm -rf "$stage_root"
  trap - RETURN
}

resolve_default_dmg_path() {
  local direct_path="$PROJECT_DIR/dist/${APP_NAME}.dmg"
  local inferred_arch=""
  local inferred_path=""
  local matches=()

  if [[ -f "$direct_path" ]]; then
    echo "$direct_path"
    return 0
  fi

  if [[ "$APP_PATH" == "$PROJECT_DIR"/dist/*/"$APP_NAME".app ]]; then
    inferred_arch="${APP_PATH#"$PROJECT_DIR/dist/"}"
    inferred_arch="${inferred_arch%%/*}"
    inferred_path="$PROJECT_DIR/dist/${APP_NAME}-${inferred_arch}.dmg"
    if [[ -f "$inferred_path" ]]; then
      echo "$inferred_path"
      return 0
    fi
  fi

  shopt -s nullglob
  matches=("$PROJECT_DIR"/dist/"$APP_NAME"-*.dmg)
  shopt -u nullglob
  if [[ ${#matches[@]} -gt 0 ]]; then
    echo "${matches[0]}"
    return 0
  fi

  echo "$direct_path"
}

resolve_default_app_path() {
  local direct_path="$PROJECT_DIR/dist/${APP_NAME}.app"
  local inferred_path=""
  local matches=()

  if [[ -d "$direct_path" ]]; then
    echo "$direct_path"
    return 0
  fi

  shopt -s nullglob
  matches=("$PROJECT_DIR"/dist/*/"$APP_NAME".app)
  shopt -u nullglob
  if [[ ${#matches[@]} -gt 0 ]]; then
    echo "${matches[0]}"
    return 0
  fi

  echo "$direct_path"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script only runs on macOS."
  exit 1
fi

require_cmd codesign
require_cmd xcrun
require_cmd hdiutil

if [[ -z "$DEVELOPER_ID_APP" ]]; then
  echo "Please set the signing certificate, e.g.:"
  echo 'DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)" ./sign_and_notarize.sh'
  exit 1
fi

if [[ -z "$APP_PATH" ]]; then
  APP_PATH="$(resolve_default_app_path)"
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found: $APP_PATH"
  exit 1
fi

if [[ -z "$DMG_PATH" ]]; then
  DMG_PATH="$(resolve_default_dmg_path)"
fi

codesign --force --deep --options runtime --sign "$DEVELOPER_ID_APP" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

if [[ -f "$DMG_PATH" ]]; then
  recreate_dmg_from_signed_app "$APP_PATH" "$DMG_PATH"
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
