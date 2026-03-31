#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="CleanMyCodeMac"
APP_ID="com.itling.cleanmycodemac"
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

DOTENV_APP_VERSION="$(read_dotenv_value APP_VERSION || true)"
DOTENV_VERSION="$(read_dotenv_value VERSION || true)"
APP_VERSION_RAW="${APP_VERSION:-${VERSION:-${DOTENV_APP_VERSION:-${DOTENV_VERSION:-1.0.0}}}}"
APP_VERSION="${APP_VERSION_RAW#v}"
APP_VERSION="${APP_VERSION#V}"
APP_BUILD_VERSION_RAW="${APP_BUILD_VERSION:-$APP_VERSION}"
APP_BUILD_VERSION="${APP_BUILD_VERSION_RAW#v}"
APP_BUILD_VERSION="${APP_BUILD_VERSION#V}"
DIST_ROOT="$PROJECT_DIR/dist"
BUILD_ROOT="$PROJECT_DIR/build"
SWIFT_BIN="${SWIFT_BIN:-$(command -v swift)}"
SWIFT_BUILD_HOME="${SWIFT_BUILD_HOME:-$BUILD_ROOT/swift-home}"
SWIFT_CLANG_MODULE_CACHE_PATH="${SWIFT_CLANG_MODULE_CACHE_PATH:-$BUILD_ROOT/clang-module-cache}"
ICON_PATH="$PROJECT_DIR/resources/app.icns"
UI_DIR="$PROJECT_DIR/resources/ui"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

clean_legacy_dist_artifacts() {
  rm -rf \
    "$DIST_ROOT/$APP_NAME" \
    "$DIST_ROOT/$APP_NAME.app"

  rm -f "$DIST_ROOT/.DS_Store"
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

resolve_binary_path() {
  local scratch_dir="$1"
  local arch="$2"
  local direct="$scratch_dir/${arch}-apple-macosx/release/$APP_NAME"
  if [[ -x "$direct" ]]; then
    echo "$direct"
    return 0
  fi

  local found
  found="$(find "$scratch_dir" -path "*/release/$APP_NAME" -type f | head -n 1)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return 0
  fi

  return 1
}

create_info_plist() {
  local plist_path="$1"
  cat > "$plist_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>$APP_NAME</string>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>
  <string>app</string>
  <key>CFBundleIdentifier</key>
  <string>$APP_ID</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>$APP_VERSION</string>
  <key>CFBundleVersion</key>
  <string>$APP_BUILD_VERSION</string>
  <key>LSApplicationCategoryType</key>
  <string>public.app-category.developer-tools</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF
}

build_one_arch() {
  local arch="$1"
  local scratch_dir="$BUILD_ROOT/swift-$arch"
  local dist_dir="$DIST_ROOT/$arch"
  local app_bundle="$dist_dir/$APP_NAME.app"
  local contents_dir="$app_bundle/Contents"
  local macos_dir="$contents_dir/MacOS"
  local resources_dir="$contents_dir/Resources"
  local dmg_staging_dir="$dist_dir/dmg"
  local dmg_name="${APP_NAME}-${arch}.dmg"
  local dmg_path="$DIST_ROOT/$dmg_name"

  echo "Cleaning previous build ($arch)..."
  rm -rf "$scratch_dir" "$dist_dir" "$dmg_path"

  if [[ ! -f "$ICON_PATH" ]]; then
    echo "App icon not found: $ICON_PATH"
    echo "Run ./build_icon.sh first."
    exit 1
  fi

  if [[ ! -d "$UI_DIR" ]]; then
    echo "UI resources not found: $UI_DIR"
    exit 1
  fi

  echo "Building executable ($arch)..."
  mkdir -p "$SWIFT_BUILD_HOME" "$SWIFT_CLANG_MODULE_CACHE_PATH"
  env \
    HOME="$SWIFT_BUILD_HOME" \
    CLANG_MODULE_CACHE_PATH="$SWIFT_CLANG_MODULE_CACHE_PATH" \
    "$SWIFT_BIN" build \
    --configuration release \
    --arch "$arch" \
    --scratch-path "$scratch_dir"

  local binary_path
  binary_path="$(resolve_binary_path "$scratch_dir" "$arch")" || {
    echo "Build failed, executable not found in: $scratch_dir"
    exit 1
  }

  mkdir -p "$macos_dir" "$resources_dir"
  cp "$binary_path" "$macos_dir/$APP_NAME"
  chmod +x "$macos_dir/$APP_NAME"
  cp "$ICON_PATH" "$resources_dir/app.icns"
  mkdir -p "$resources_dir/ui"
  cp -R "$UI_DIR/." "$resources_dir/ui/"
  create_info_plist "$contents_dir/Info.plist"

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
require_cmd xattr

clean_legacy_dist_artifacts

if [[ -z "$SWIFT_BIN" || ! -x "$SWIFT_BIN" ]]; then
  echo "Swift toolchain not found: ${SWIFT_BIN:-<empty>}"
  echo "Override with SWIFT_BIN, e.g.:"
  echo "SWIFT_BIN=/path/to/swift ./build_dmg.sh"
  exit 1
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
