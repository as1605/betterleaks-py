import os
import platform
import shutil
import subprocess
import sys
from typing import Optional
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.dist import Distribution

# Ensure minimum macOS deployment target compatible with modern Go
if sys.platform == "darwin" and "MACOSX_DEPLOYMENT_TARGET" not in os.environ:
    os.environ["MACOSX_DEPLOYMENT_TARGET"] = "12.0"


def get_cli_filename() -> str:
    return "betterleaks.exe" if platform.system().lower() == "windows" else "betterleaks"


def build_go_cli_binary(target_dir: str) -> str:
    bin_dir = os.path.join(target_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    out_bin = os.path.join(bin_dir, get_cli_filename())

    if os.path.isfile(out_bin) and os.path.getsize(out_bin) > 0:
        return out_bin

    go_bin = shutil.which("go")
    if not go_bin:
        for p in ["/opt/homebrew/bin/go", "/usr/local/bin/go", "/usr/local/go/bin/go"]:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                go_bin = p
                break

    upstream_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "upstream"))
    if not go_bin or not os.path.exists(os.path.join(upstream_dir, "go.mod")):
        return ""

    upstream_version = "2.0.0-rc.4"
    init_path = os.path.join(os.path.dirname(__file__), "src", "betterleaks_cli", "__init__.py")
    if os.path.isfile(init_path):
        with open(init_path, "r") as f:
            for line in f:
                if line.startswith("__upstream_version__"):
                    upstream_version = line.split("=")[1].strip().strip("\"'")
                    break

    ldflags = f"-X=github.com/betterleaks/betterleaks/v2/version.Version={upstream_version}"
    cmd = [go_bin, "build", "-ldflags", ldflags, "-o", out_bin, "."]
    env = os.environ.copy()
    env["CGO_ENABLED"] = "0"

    print(f"--> Compiling Betterleaks CLI: {' '.join(cmd)} in {upstream_dir}")
    try:
        subprocess.check_call(cmd, cwd=upstream_dir, env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Failed to compile Go CLI binary: {e}", file=sys.stderr)
        raise SystemExit(e.returncode)

    if sys.platform != "win32" and os.path.isfile(out_bin):
        os.chmod(out_bin, 0o755)

    return out_bin


class CustomBuildPy(build_py):
    def run(self):
        target_dir = os.path.join(self.build_lib, "betterleaks_cli")
        build_go_cli_binary(target_dir)

        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "betterleaks_cli"))
        if not os.path.exists(os.path.join(local_dir, "bin", get_cli_filename())):
            build_go_cli_binary(local_dir)

        super().run()


class CustomDevelop(develop):
    def run(self):
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "betterleaks_cli"))
        build_go_cli_binary(local_dir)
        super().run()


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


setup(
    distclass=BinaryDistribution,
    cmdclass={
        "build_py": CustomBuildPy,
        "develop": CustomDevelop,
    },
    package_data={
        "betterleaks_cli": [
            "bin/*",
            "py.typed",
        ],
    },
)
