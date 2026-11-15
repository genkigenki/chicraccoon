#!/bin/sh
# Start the eNote backup viewer on macOS / Linux.
# macOS: double-click this file (first time: right-click -> Open).
# Linux: run  sh START_macOS_Linux.command
cd "$(dirname "$0")" || exit 1

PY=""
for p in python3 python; do
    if command -v "$p" >/dev/null 2>&1 &&
       "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' 2>/dev/null; then
        PY="$p"; break
    fi
done
if [ -z "$PY" ]; then
    echo "Python 3 was not found. Please install it from https://www.python.org/downloads/"
    echo "Python 3 が見つかりません。https://www.python.org/downloads/ からインストールしてください。"
    echo "Python 3 wurde nicht gefunden. Bitte von https://www.python.org/downloads/ installieren."
    (open "https://www.python.org/downloads/" || xdg-open "https://www.python.org/downloads/") >/dev/null 2>&1
    exit 1
fi

if ! "$PY" -c 'import jinja2, PIL' >/dev/null 2>&1; then
    echo "Installing the required libraries (only needed once)..."
    "$PY" -m pip install --user --disable-pip-version-check -r requirements.txt ||
        echo "pip failed - on Linux try: sudo apt install python3-pil python3-jinja2 python3-tk"
fi
if ! "$PY" -c 'import tkinter' >/dev/null 2>&1; then
    echo "tkinter is missing - on Linux try: sudo apt install python3-tk"
    exit 1
fi

exec "$PY" -m chicraccoon.gui
