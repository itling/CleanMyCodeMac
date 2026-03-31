# CleanMyCodeMac Build Guide

This project is packaged as a native macOS `.app` with Swift Package Manager, then wrapped into a `.dmg` with `hdiutil`.

[中文文档](BUILD_ZH.md)

## Prerequisites

- macOS 13.0+
- Xcode 16.4+ or a compatible Swift 6.1 toolchain
- `hdiutil`, `codesign`, and `xcrun` are available by default on macOS

## One-Step Build

From the project root:

```bash
chmod +x build_dmg.sh
./build_dmg.sh
```

By default, it builds for the current machine's architecture, e.g.:

- `dist/arm64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-arm64.dmg`

You can also specify the target architecture explicitly:

```bash
./build_dmg.sh x86_64
./build_dmg.sh arm64
./build_dmg.sh all
```

When building both architectures, the output will be:

- `dist/x86_64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-x86_64.dmg`
- `dist/arm64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-arm64.dmg`

If you want the app UI and bundle metadata to show a custom version, pass it in via environment variable:

```bash
APP_VERSION=1.2.3 ./build_dmg.sh
```

If `APP_VERSION` is not set, the build script also falls back to `.env` in the project root:

```bash
APP_VERSION=1.2.3
```

## App Icon

If you update `resources/app_icon.png`, regenerate the `.icns` first:

```bash
chmod +x build_icon.sh
./build_icon.sh
```

The release workflow prefers the committed `resources/app.icns`. If it is missing, CI falls back to `./build_icon.sh`.

## Notes

- The build script uses `swift build --configuration release`.
- `resources/ui/index.html` is copied into the app bundle, so the shipped app does not depend on repo-relative files.
- The `.dmg` includes `CleanMyCodeMac.app` and an `/Applications` symlink for drag-to-install.
- When targeting `arm64` / `x86_64`, the local Swift toolchain must support that architecture.

## Signing and Notarization

If you have an Apple Developer certificate, run after building:

```bash
DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)" \
APPLE_ID="your-apple-id@example.com" \
TEAM_ID="TEAMID" \
APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
./sign_and_notarize.sh
```

If only `DEVELOPER_ID_APP` is provided, the script will sign and skip notarization.

For local development, `sign_and_notarize.sh` also falls back to the project root `.env` for:

- `DEVELOPER_ID_APP`
- `APPLE_ID`
- `TEAM_ID`
- `APP_PASSWORD`

## GitHub Release Automation

This repository can publish DMG files automatically through GitHub Actions.

- Push a tag such as `v1.0.0`
- The `release.yml` workflow builds DMG files for `arm64` and `x86_64`
- If signing secrets are configured, the workflow signs and optionally notarizes the build
- The generated DMG files are uploaded to the matching GitHub Release

Recommended GitHub secrets:

- `DEVELOPER_ID_APP`
- `APPLE_CERTIFICATE_P12` (base64-encoded `.p12` certificate)
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_ID`
- `TEAM_ID`
- `APP_PASSWORD`

If those secrets are not configured, the workflow still publishes unsigned DMG files.
