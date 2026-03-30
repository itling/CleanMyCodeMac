# Contributing to CleanMyCodeMac

Thanks for your interest in contributing.

## Before You Start

- This project targets macOS.
- The app is built with Python and `pywebview`.
- The UI is embedded directly inside `cleanmycodemac/web_app.py`.

## Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the app:

```bash
cd cleanmycodemac
../venv/bin/python3 main.py
```

## Development Notes

- Keep changes focused and easy to review.
- Update both `README.md` and `README_ZH.md` when public-facing behavior changes.
- Add or update strings in `cleanmycodemac/utils/i18n.py` for UI text changes.
- Prefer safe cleanup behavior and avoid making deletion flows more aggressive without a strong reason.

## Validation

At minimum, please run:

```bash
python3 -m py_compile cleanmycodemac/web_app.py cleanmycodemac/utils/i18n.py
python3 -m compileall cleanmycodemac
```

If your change affects scanning or cleanup behavior, a quick manual smoke test is also helpful.

## Pull Requests

- Describe the user-facing change clearly.
- Mention any macOS permission requirements if relevant.
- Include screenshots for UI changes when possible.

Thanks for helping improve CleanMyCodeMac.
