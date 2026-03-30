# CleanMyCodeMac Build Guide

[中文文档](BUILD_ZH.md)

This project can be packaged as a `.app` on macOS using `PyInstaller`, then wrapped into a `.dmg` with `hdiutil`.

## Prerequisites

- macOS
- A working Python 3 environment
- A virtual environment set up, or override `PYTHON_BIN` / `PIP_BIN` via environment variables

## One-Step Build

From the project root:

```bash
chmod +x build_dmg.sh
./build_dmg.sh
```

By default, it builds for the current machine's architecture, e.g.:

- `dist/x86_64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-x86_64.dmg`

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

## App Icon

If you have `resources/app_icon.png`, generate the `.icns` first:

```bash
chmod +x build_icon.sh
./build_icon.sh
```

After generation, `CleanMyCodeMac.spec` will automatically use `resources/app.icns`.

## Custom Python Path

If your Python or pip is not in the default virtual environment:

```bash
PYTHON_BIN=/path/to/python3 PIP_BIN=/path/to/pip3 ./build_dmg.sh
```

## Notes

- The build script automatically installs `requirements-build.txt` if `PyInstaller` is not found.
- The `.dmg` includes `CleanMyCodeMac.app` and an `/Applications` symlink for drag-to-install.
- When targeting `arm64` / `x86_64`, the current Python and PyInstaller environment must support the target architecture.

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
