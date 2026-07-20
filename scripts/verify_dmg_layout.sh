#!/bin/bash

set -euo pipefail

DMG_PATH="${1:-}"
APP_NAME="${2:-CleanMyCodeMac}"

if [[ -z "$DMG_PATH" || ! -f "$DMG_PATH" ]]; then
  echo "DMG not found: ${DMG_PATH:-<empty>}"
  exit 1
fi

attach_output="$(hdiutil attach "$DMG_PATH" -readonly -nobrowse)"
device="$(printf '%s\n' "$attach_output" | awk 'NR == 1 { print $1 }')"
mount_point="$(printf '%s\n' "$attach_output" | sed -n 's#^.*\(/Volumes/.*\)$#\1#p' | tail -n 1)"

cleanup() {
  if [[ -n "$device" ]]; then
    hdiutil detach "$device" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ -z "$mount_point" || ! -d "$mount_point" ]]; then
  echo "Unable to locate mounted DMG volume."
  exit 1
fi

required_paths=(
  "$mount_point/$APP_NAME.app"
  "$mount_point/Applications"
  "$mount_point/.background/background.png"
  "$mount_point/.DS_Store"
)

for path in "${required_paths[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "Styled DMG is missing: ${path#"$mount_point"/}"
    exit 1
  fi
done

if [[ ! -L "$mount_point/Applications" ]]; then
  echo "Applications must be a symlink."
  exit 1
fi

echo "Styled DMG layout verified: $DMG_PATH"
