#!/usr/bin/env bash
# Double-click this file (macOS) or run it from a terminal (Linux) to start
# VerifyIntern on this computer. It needs Python 3, which macOS and most
# Linux distributions already have.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  python3 tools/serve.py
elif command -v python >/dev/null 2>&1; then
  python tools/serve.py
else
  echo
  echo "Python 3 was not found. Install it from https://python.org/downloads"
  echo "and then open this file again."
  echo
  read -r -p "Press Enter to close."
  exit 1
fi
