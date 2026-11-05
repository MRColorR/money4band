#!/usr/bin/env bash
# Cross-platform launcher for Money4Band (macOS / Linux).
# Thin wrapper: all logic lives in run.py so behaviour is identical
# everywhere. Override the interpreter with PYTHON=/path/to/python.
set -e
cd "$(dirname "$0")"
exec "${PYTHON:-python3}" run.py "$@"
