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


def build_go_shared_library(target_dir: str) -> str:
    os.makedirs(target_dir, exist_ok=True)
    out_lib = os.path.join(target_dir, get_lib_filename())

    # If library already exists (e.g. pre-bundled in wheel or cached), use it
    if os.path.isfile(out_lib) and os.path.getsize(out_lib) > 0:
        return out_lib

    go_bin = find_go_binary()
    if not go_bin:
        print("--> Go compiler not found. Attempting to download pre-built library...", file=sys.stderr)
        return download_fallback_library(target_dir)

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
    
    # Ensure correct Go architecture during cross-compilation (e.g., cibuildwheel on macOS)
    machine = platform.machine().lower()
    archflags = os.environ.get("ARCHFLAGS", "").lower()
    if "-arch x86_64" in archflags:
        env["GOARCH"] = "amd64"
    elif "-arch arm64" in archflags:
        env["GOARCH"] = "arm64"
    elif machine in ("aarch64", "arm64"):
        env["GOARCH"] = "arm64"
    else:
        env["GOARCH"] = "amd64"

    print(f"--> Compiling Go shared library for {env.get('GOARCH', 'default')}: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd, cwd=wrapper_dir, env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Failed to compile Go wrapper: {e}", file=sys.stderr)
        raise SystemExit(e.returncode)

    return out_lib

def download_fallback_library(target_dir: str) -> str:
    import json
    import ssl
    import tempfile
    import zipfile
    
    out_lib = os.path.join(target_dir, get_lib_filename())
    version = "2.0.0-rc.3"  # Match __upstream_version__
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        os_tag = "macosx"
    elif system == "windows":
        os_tag = "win"
    else:
        os_tag = "manylinux"
        
    if machine in ("aarch64", "arm64"):
        arch_tag = "arm64" if system == "darwin" else "aarch64"
    else:
        arch_tag = "amd64" if system == "windows" else "x86_64"
        
    api_url = f"https://api.github.com/repos/as1605/betterleaks-py/releases/tags/v{version}"
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(api_url)
        with urllib.request.urlopen(req, context=ctx) as response:
            release_data = json.loads(response.read())
            
        download_url = None
        for asset in release_data.get("assets", []):
            name = asset["name"]
            if name.endswith(".whl") and os_tag in name and arch_tag in name:
                download_url = asset["browser_download_url"]
                break
                
        if not download_url:
            raise RuntimeError(f"No pre-built wheel found on GitHub Releases for {system} {machine}.")
            
        print(f"--> Downloading fallback library from {download_url}...")
        with tempfile.NamedTemporaryFile(suffix=".whl", delete=False) as tf:
            whl_path = tf.name
            
        try:
            req = urllib.request.Request(download_url)
            with urllib.request.urlopen(req, context=ctx) as response, open(whl_path, "wb") as f:
                f.write(response.read())
                
            with zipfile.ZipFile(whl_path) as z:
                lib_name = None
                for name in z.namelist():
                    if name.startswith("betterleaks/libbetterleaks.") and not name.endswith(".h"):
                        lib_name = name
                        break
                
                if not lib_name:
                    raise RuntimeError("Could not find libbetterleaks shared library in downloaded wheel")
                    
                with z.open(lib_name) as source, open(out_lib, "wb") as target:
                    target.write(source.read())
                    
            print(f"--> Successfully installed fallback library to {out_lib}")
            return out_lib
        finally:
            if os.path.exists(whl_path):
                os.remove(whl_path)
    except Exception as e:
        err_msg = f"""
================================================================================
BETTERLEAKS INSTALLATION ERROR: Go compiler ('go') not found!
================================================================================
Building 'betterleaks-py' from source requires the Go compiler (version 1.25+).
Attempted to download a pre-built fallback library, but it failed:
{e}

Please install Go on your system:
  • macOS:    brew install go
  • Ubuntu:   sudo apt install golang  (or visit https://go.dev/dl/)
  • Fedora:   sudo dnf install golang
  • Windows:  choco install golang     (or visit https://go.dev/dl/)

If Go is already installed, ensure its binary directory is in your PATH.
(Common locations: /opt/homebrew/bin, /usr/local/bin, /usr/local/go/bin)

Alternatively, install a pre-compiled binary wheel manually:
  pip install --find-links https://github.com/as1605/betterleaks-py/releases/expanded_assets/v2.0.0-rc.3 betterleaks
================================================================================
"""
        print(err_msg, file=sys.stderr)
        raise SystemExit(1)


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
