"""Internal C shared library bindings for Betterleaks."""

import ctypes
import json
import os
import platform
from typing import Any, Dict, Optional
from betterleaks.models import BetterleaksError


def _find_library() -> str:
    """Locate the compiled Betterleaks shared library."""
    custom_path = os.environ.get("BETTERLEAKS_LIB_PATH")
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    system = platform.system().lower()

    candidate_names = []
    if system == "darwin":
        candidate_names = ["libbetterleaks.dylib", "libbetterleaks.so"]
    elif system == "windows":
        candidate_names = ["libbetterleaks.dll", "betterleaks.dll"]
    else:
        candidate_names = ["libbetterleaks.so"]

    # Check package directory first
    for name in candidate_names:
        candidate = os.path.join(pkg_dir, name)
        if os.path.isfile(candidate):
            return candidate

    # Check wrapper output / build directories
    root_dir = os.path.abspath(os.path.join(pkg_dir, "..", ".."))
    for name in candidate_names:
        candidate = os.path.join(root_dir, "src", "betterleaks", name)
        if os.path.isfile(candidate):
            return candidate

    searched = [os.path.join(pkg_dir, n) for n in candidate_names]
    raise BetterleaksError(
        f"Could not find Betterleaks shared library. Searched: {searched}. "
        "Please build the Go wrapper or set BETTERLEAKS_LIB_PATH."
    )


class _BetterleaksBinding:
    def __init__(self) -> None:
        lib_path = _find_library()
        self._lib = ctypes.CDLL(lib_path)

        # ScanStringCGO(char* content) -> char*
        self._lib.ScanStringCGO.argtypes = [ctypes.c_char_p]
        self._lib.ScanStringCGO.restype = ctypes.c_void_p

        # ScanStringWithConfigCGO(char* content, char* configPath) -> char*
        self._lib.ScanStringWithConfigCGO.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.ScanStringWithConfigCGO.restype = ctypes.c_void_p

        # ScanFileCGO(char* filePath, char* configPath) -> char*
        self._lib.ScanFileCGO.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.ScanFileCGO.restype = ctypes.c_void_p

        # FreeMemory(char* ptr) -> void
        self._lib.FreeMemory.argtypes = [ctypes.c_void_p]
        self._lib.FreeMemory.restype = None

    def _call_and_parse(self, ptr: Optional[int]) -> Dict[str, Any]:
        if not ptr:
            raise BetterleaksError("Null pointer returned from Betterleaks library")
        try:
            raw_bytes = ctypes.cast(ptr, ctypes.c_char_p).value
            if not raw_bytes:
                raise BetterleaksError("Empty response from Betterleaks library")
            data = json.loads(raw_bytes.decode("utf-8"))
            if not data.get("success", False):
                err_msg = data.get("error", "Unknown scanning error")
                raise BetterleaksError(err_msg)
            return data
        finally:
            self._lib.FreeMemory(ptr)

    def scan_string(self, content: str, config_path: Optional[str] = None) -> Dict[str, Any]:
        encoded_content = content.encode("utf-8")
        if config_path:
            encoded_cfg = config_path.encode("utf-8")
            ptr = self._lib.ScanStringWithConfigCGO(encoded_content, encoded_cfg)
        else:
            ptr = self._lib.ScanStringCGO(encoded_content)
        return self._call_and_parse(ptr)

    def scan_file(self, file_path: str, config_path: Optional[str] = None) -> Dict[str, Any]:
        encoded_file = file_path.encode("utf-8")
        encoded_cfg = config_path.encode("utf-8") if config_path else None
        ptr = self._lib.ScanFileCGO(encoded_file, encoded_cfg)
        return self._call_and_parse(ptr)


_binding_instance: Optional[_BetterleaksBinding] = None


def get_binding() -> _BetterleaksBinding:
    global _binding_instance
    if _binding_instance is None:
        _binding_instance = _BetterleaksBinding()
    return _binding_instance
