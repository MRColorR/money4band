#!/usr/bin/env python3
"""Cross-platform launcher for Money4Band (Windows, macOS, Linux).

Sets up dependencies and starts the app, so a fresh checkout runs with a
single command. Prefers `uv` (fast, modern); falls back to a stdlib venv
plus pip when uv is not installed. Requires Python 3.10+ and Docker.

Usage:
    python run.py [args...]      # any args are forwarded to the m4b CLI

Examples:
    python run.py                # interactive menu / first-run setup
    python run.py --help
    python run.py status
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_PY = (3, 10)


def _die(msg: str, code: int = 1) -> None:
    print(f"[run] ERROR: {msg}", file=sys.stderr)
    print("[run] Ensure Python 3.10+ and Docker are installed.", file=sys.stderr)
    sys.exit(code)


def _run(cmd: list[str]) -> int:
    print(f"[run] $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode  # noqa: S603


def main() -> int:
    if sys.version_info < MIN_PY:
        _die(
            f"Python {MIN_PY[0]}.{MIN_PY[1]}+ required, found {sys.version.split()[0]}"
        )
    os.chdir(ROOT)
    args = sys.argv[1:]

    # Preferred path: uv manages the environment and run.
    if shutil.which("uv"):
        print("[run] uv detected -> syncing runtime dependencies")
        if _run(["uv", "sync", "--no-dev"]) != 0:
            _die("'uv sync' failed")
        return _run(["uv", "run", "python", "main.py", *args])

    # Fallback: stdlib venv + pip with the current interpreter.
    print("[run] uv not found -> using venv + pip")
    venv = ROOT / ".venv"
    bindir = venv / ("Scripts" if os.name == "nt" else "bin")
    py = bindir / ("python.exe" if os.name == "nt" else "python")

    if not py.exists():
        print("[run] creating virtual environment (.venv)")
        if _run([sys.executable, "-m", "venv", str(venv)]) != 0:
            _die("failed to create virtual environment")

    if _run([str(py), "-m", "pip", "install", "--upgrade", "pip"]) != 0:
        _die("failed to upgrade pip")
    if _run([str(py), "-m", "pip", "install", "-r", "requirements.txt"]) != 0:
        _die("failed to install requirements")

    return _run([str(py), "main.py", *args])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
