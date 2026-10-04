"""Betterleaks Python bindings.

High-performance secret and credential detection engine powered by Go.
"""

from typing import List, Optional
from betterleaks.models import BetterleaksError, Finding, Location, Match
from betterleaks._lib import get_binding

__version__ = "2.0.0rc4"
__upstream_version__ = "2.0.0-rc.4"
__all__ = [
    "scan_string",
    "scan_file",
    "Finding",
    "Match",
    "Location",
    "BetterleaksError",
    "__version__",
    "__upstream_version__",
]


def scan_string(content: str, config_path: Optional[str] = None) -> List[Finding]:
    """Scan a string for secrets and credentials.

    Args:
        content: String content to scan.
        config_path: Optional path to a custom Betterleaks configuration TOML file.

    Returns:
        A list of Finding objects.

    Raises:
        BetterleaksError: If scanning fails.
    """
    binding = get_binding()
    resp = binding.scan_string(content, config_path=config_path)
    findings_data = resp.get("data", [])
    return [Finding.from_dict(item) for item in findings_data]


def scan_file(file_path: str, config_path: Optional[str] = None) -> List[Finding]:
    """Scan a file for secrets and credentials.

    Args:
        file_path: Path to the file to scan.
        config_path: Optional path to a custom Betterleaks configuration TOML file.

    Returns:
        A list of Finding objects.

    Raises:
        BetterleaksError: If the file cannot be read or scanning fails.
    """
    binding = get_binding()
    resp = binding.scan_file(file_path, config_path=config_path)
    findings_data = resp.get("data", [])
    return [Finding.from_dict(item) for item in findings_data]
