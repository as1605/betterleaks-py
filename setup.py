import os
import platform
import subprocess
import sys
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


def build_go_shared_library(target_dir: str) -> str:
    os.makedirs(target_dir, exist_ok=True)
    out_lib = os.path.join(target_dir, get_lib_filename())
    wrapper_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "wrapper"))

    cmd = [
        "go",
        "build",
        "-buildmode=c-shared",
        "-o",
        out_lib,
        "cgo_wrapper.go",
    ]
    env = os.environ.copy()
    env["CGO_ENABLED"] = "1"

    print(f"--> Compiling Go shared library: {' '.join(cmd)} in {wrapper_dir}")
    subprocess.check_call(cmd, cwd=wrapper_dir, env=env)
    return out_lib


class CustomBuildPy(build_py):
    def run(self):
        # Build library into the wheel build tree
        target_dir = os.path.join(self.build_lib, "betterleaks")
        build_go_shared_library(target_dir)

        # Also keep in-tree library up-to-date
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
