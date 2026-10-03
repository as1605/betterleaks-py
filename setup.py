import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from typing import Optional
from setuptools import find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.dist import Distribution


def get_lib_filename() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "libbetterleaks.dylib"
    elif system == "windows":
        return "libbetterleaks.dll"
    else:
        return "libbetterleaks.so"


def find_go_binary() -> Optional[str]:
    """Search for the go compiler in PATH and standard system installation paths."""
    go_bin = shutil.which("go")
    if go_bin:
        return go_bin

    home = os.path.expanduser("~")
    candidates = [
        # macOS Homebrew (Apple Silicon)
        "/opt/homebrew/bin/go",
        # macOS Homebrew (Intel) & Linux /usr/local
        "/usr/local/bin/go",
        "/usr/local/go/bin/go",
        # User GOPATH / asdf / gvm
        os.path.join(home, "go", "bin", "go"),
        os.path.join(home, ".asdf", "shims", "go"),
        # Linux standard distribution packages & snap
        "/usr/bin/go",
        "/snap/bin/go",
        # Windows standard installer locations
        r"C:\Program Files\Go\bin\go.exe",
        r"C:\Go\bin\go.exe",
    ]

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def download_prebuilt_library(target_file: str) -> bool:
    """Attempt to download precompiled library from GitHub Releases if Go is unavailable."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        return False

    lib_name = get_lib_filename()
    version = "2.0.0rc1"
    url = f"https://github.com/as1605/betterleaks-py/releases/download/v{version}/libbetterleaks-{system}-{arch}-{lib_name}"

    try:
        print(f"--> Go compiler not found. Attempting to download pre-built library from:\n    {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "betterleaks-py-installer"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                with open(target_file, "wb") as f:
                    f.write(resp.read())
                print(f"--> Successfully downloaded pre-built library to {target_file}")
                return True
    except Exception as e:
        print(f"--> Could not download pre-built binary: {e}")

    return False


def build_go_shared_library(target_dir: str) -> str:
    os.makedirs(target_dir, exist_ok=True)
    out_lib = os.path.join(target_dir, get_lib_filename())

    # If library already exists (e.g. pre-bundled in wheel or cached), use it
    if os.path.isfile(out_lib) and os.path.getsize(out_lib) > 0:
        return out_lib

    go_bin = find_go_binary()
    if not go_bin:
        # Try downloading precompiled binary first
        if download_prebuilt_library(out_lib):
            return out_lib

        err_msg = """
================================================================================
BETTERLEAKS INSTALLATION ERROR: Go compiler ('go') not found!
================================================================================
Building 'betterleaks-py' from source requires the Go compiler (version 1.25+).

Please install Go on your system:
  • macOS:    brew install go
  • Ubuntu:   sudo apt install golang  (or visit https://go.dev/dl/)
  • Fedora:   sudo dnf install golang
  • Windows:  choco install golang     (or visit https://go.dev/dl/)

If Go is already installed, ensure its binary directory is in your PATH.
(Common locations: /opt/homebrew/bin, /usr/local/bin, /usr/local/go/bin)

Pre-built binary wheels (which do not require Go) are available at:
  https://github.com/as1605/betterleaks-py/releases
================================================================================
"""
        print(err_msg, file=sys.stderr)
        raise SystemExit(1)

    wrapper_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "wrapper"))
    cmd = [
        go_bin,
        "build",
        "-buildmode=c-shared",
        "-o",
        out_lib,
        "cgo_wrapper.go",
    ]
    env = os.environ.copy()
    env["CGO_ENABLED"] = "1"

    print(f"--> Compiling Go shared library: {' '.join(cmd)} in {wrapper_dir}")
    try:
        subprocess.check_call(cmd, cwd=wrapper_dir, env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Failed to compile Go wrapper: {e}", file=sys.stderr)
        raise SystemExit(e.returncode)

    return out_lib


class CustomBuildPy(build_py):
    def run(self):
        target_dir = os.path.join(self.build_lib, "betterleaks")
        build_go_shared_library(target_dir)

        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "betterleaks"))
        if not os.path.exists(os.path.join(local_dir, get_lib_filename())):
            build_go_shared_library(local_dir)

        super().run()


class CustomDevelop(develop):
    def run(self):
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "betterleaks"))
        build_go_shared_library(local_dir)
        super().run()


class BinaryDistribution(Distribution):
    """Marks package as containing binary platform-specific extensions."""
    def has_ext_modules(self):
        return True


setup(
    distclass=BinaryDistribution,
    cmdclass={
        "build_py": CustomBuildPy,
        "develop": CustomDevelop,
    },
    package_data={
        "betterleaks": [
            "*.so",
            "*.dylib",
            "*.dll",
            "*.h",
        ],
    },
)
