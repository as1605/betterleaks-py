"""Betterleaks CLI — standalone command-line secret scanner.

This package ships only the compiled Go binary.
For Python bindings (scan_string / scan_file), install ``betterleaks-py`` instead.
"""

import os
import stat
import subprocess
import sys
from pathlib import Path

__version__ = "2.0.0"
__upstream_version__ = "2.0.0-rc.4"


def _binary_name() -> str:
    return "betterleaks.exe" if sys.platform == "win32" else "betterleaks"


def get_binary_path() -> str:
    """Return the path to the bundled Betterleaks binary."""
    binary = Path(__file__).resolve().parent / "bin" / _binary_name()

    if not binary.exists():
        raise FileNotFoundError(
            "Betterleaks CLI binary not found. This wheel may not match your platform."
        )

    if sys.platform != "win32":
        try:
            current_mode = binary.stat().st_mode
            if not (current_mode & stat.S_IXUSR):
                binary.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass

    return os.fspath(binary)


def main() -> None:
    """Execute the bundled Betterleaks binary."""
    try:
        binary = get_binary_path()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if sys.platform == "win32":
        raise SystemExit(subprocess.call([binary, *sys.argv[1:]]))

    os.execvp(binary, [binary, *sys.argv[1:]])
