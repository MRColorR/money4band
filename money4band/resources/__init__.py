"""Package-data resources (static website, images, service files).

Use :func:`get_path` to resolve resource paths reliably — works both in
development (source tree) and in PyInstaller frozen binaries.
"""

from __future__ import annotations

import sys
from pathlib import Path

# PyInstaller extracts data into sys._MEIPASS when frozen.
_ROOT: Path = (
    Path(getattr(sys, "_MEIPASS", ""))
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)


def get_path(*parts: str) -> Path:
    """Return an absolute path to a resource file or directory.

    >>> from money4band.resources import get_path
    >>> get_path("www")           # .../money4band/resources/www
    >>> get_path("files", "docker.binfmt.service")
    """
    return _ROOT.joinpath(*parts)
