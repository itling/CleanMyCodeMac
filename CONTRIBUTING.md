# Contributing to CleanMyCodeMac

Thanks for your interest in contributing.

## Before You Start

- This project targets macOS.
- The app is built with Swift, AppKit, and WKWebView.
- The UI lives in `resources/ui/index.html`.
- Native bridge and scan logic live in `source/`.

## Local Setup

```bash
swift build
```

Run the app:

```bash
swift run
```

## Development Notes

- Keep changes focused and easy to review.
- Update both `README.md` and `README_ZH.md` when public-facing behavior changes.
- Update `resources/ui/index.html` for UI behavior or copy changes.
- Update `source/AppSupport.swift` when bridge method names or shared strings change.
- Update `source/NativeScanEngine.swift` when scan, selection, cleanup, or analysis behavior changes.
- Prefer safe cleanup behavior and avoid making deletion flows more aggressive without a strong reason.

## Validation

At minimum, please run:

```bash
swift build
./build_dmg.sh "$(uname -m)"
```

If your change affects scanning or cleanup behavior, a quick manual smoke test is also helpful.

## Pull Requests

- Describe the user-facing change clearly.
- Mention any macOS permission requirements if relevant.
- Include screenshots for UI changes when possible.

Thanks for helping improve CleanMyCodeMac.
