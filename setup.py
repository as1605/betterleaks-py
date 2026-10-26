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

# Ensure minimum macOS deployment target compatible with modern Go (1.25+) toolchain
if sys.platform == "darwin" and "MACOSX_DEPLOYMENT_TARGET" not in os.environ:
    os.environ["MACOSX_DEPLOYMENT_TARGET"] = "12.0"


def get_lib_filename() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "libbetterleaks.dylib"
    elif system == "windows":
        return "libbetterleaks.dll"
    else:
        return "libbetterleaks.so"


def get_upstream_version() -> str:
    version = "2.0.0-rc.4"
    try:
        init_path = os.path.join(os.path.dirname(__file__), "src", "betterleaks", "__init__.py")
        with open(init_path, "r") as f:
            for line in f:
                if line.startswith("__upstream_version__"):
                    version = line.split("=")[1].strip().strip("\"'")
                    break
    except Exception:
        pass
    return version

def get_cli_filename() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "betterleaks.exe"
    else:
        return "betterleaks"


def build_go_cli_binary(target_dir: str) -> str:
    bin_dir = os.path.join(target_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    out_bin = os.path.join(bin_dir, get_cli_filename())

    # If binary already exists, use it
    if os.path.isfile(out_bin) and os.path.getsize(out_bin) > 0:
        return out_bin

    go_bin = find_go_binary()
    if not go_bin:
        print("--> Go compiler not found for building CLI. Skipping...", file=sys.stderr)
        return ""

    upstream_mod = os.path.abspath(os.path.join(os.path.dirname(__file__), "upstream", "go.mod"))
    if not os.path.exists(upstream_mod):
        print("--> Upstream submodule missing for building CLI. Skipping...", file=sys.stderr)
        return ""

    upstream_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "upstream"))
    
    upstream_version = get_upstream_version()
    ldflags = f"-X=github.com/betterleaks/betterleaks/v2/version.Version={upstream_version}"
    cmd = [
        go_bin,
        "build",
        "-ldflags",
        ldflags,
        "-o",
        out_bin,
        ".",
    ]
    env = os.environ.copy()
    env["CGO_ENABLED"] = "0"

    print(f"--> Compiling Go CLI binary: {' '.join(cmd)} in {upstream_dir}")
    try:
        subprocess.check_call(cmd, cwd=upstream_dir, env=env)
    except subprocess.CalledProcessError as e:
        print(f"\\nERROR: Failed to compile Go CLI binary: {e}", file=sys.stderr)
        raise SystemExit(e.returncode)

    return out_bin


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

    upstream_mod = os.path.abspath(os.path.join(os.path.dirname(__file__), "upstream", "go.mod"))
    if not os.path.exists(upstream_mod):
        print("--> Upstream submodule missing (go.mod not found).", file=sys.stderr)
        print("--> Attempting to download pre-built library instead...", file=sys.stderr)
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

    print(f"--> Compiling Go shared library: {' '.join(cmd)} in {wrapper_dir}")
    try:
        subprocess.check_call(cmd, cwd=wrapper_dir, env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Failed to compile Go wrapper: {e}", file=sys.stderr)
        raise SystemExit(e.returncode)

    return out_lib

def download_fallback_library(target_dir: str) -> str:
    import json
    import tempfile
    import zipfile
    
    version = get_upstream_version()
    machine = platform.machine().lower()
    system = platform.system().lower()
    out_lib = os.path.join(target_dir, get_lib_filename())
    
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
        req = urllib.request.Request(api_url)
        with urllib.request.urlopen(req, timeout=30) as response:
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
            with urllib.request.urlopen(req, timeout=30) as response, open(whl_path, "wb") as f:
                f.write(response.read())
                
            with zipfile.ZipFile(whl_path) as z:
                lib_name = None
                bin_name = None
                for name in z.namelist():
                    if name.startswith("betterleaks/libbetterleaks.") and not name.endswith(".h"):
                        lib_name = name
                    elif name.startswith("betterleaks/bin/betterleaks"):
                        bin_name = name
                
                if not lib_name:
                    raise RuntimeError("Could not find libbetterleaks shared library in downloaded wheel")
                    
                with z.open(lib_name) as source, open(out_lib, "wb") as target:
                    target.write(source.read())
                    
                if bin_name:
                    bin_dir = os.path.join(target_dir, "bin")
                    os.makedirs(bin_dir, exist_ok=True)
                    out_bin = os.path.join(bin_dir, get_cli_filename())
                    with z.open(bin_name) as source, open(out_bin, "wb") as target:
                        target.write(source.read())
                    if sys.platform != "win32":
                        os.chmod(out_bin, 0o755)
                    
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
  pip install betterleaks-py
  # or from GitHub Releases:
  # pip install --find-links https://github.com/as1605/betterleaks-py/releases/expanded_assets/v2.0.0-rc.4 betterleaks-py
================================================================================
"""
        print(err_msg, file=sys.stderr)
        raise SystemExit(1)


class CustomBuildPy(build_py):
    def run(self):
        target_dir = os.path.join(self.build_lib, "betterleaks")
        build_go_shared_library(target_dir)
        build_go_cli_binary(target_dir)

        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "betterleaks"))
        if not os.path.exists(os.path.join(local_dir, get_lib_filename())):
            build_go_shared_library(local_dir)
        if not os.path.exists(os.path.join(local_dir, "bin", get_cli_filename())):
            build_go_cli_binary(local_dir)

        super().run()


class CustomDevelop(develop):
    def run(self):
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "betterleaks"))
        build_go_shared_library(local_dir)
        build_go_cli_binary(local_dir)
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
            "py.typed",
            "bin/*",
        ],
    },
)
