#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR/cleanmycodemac"
"$PROJECT_DIR/venv/bin/python3" main.py
