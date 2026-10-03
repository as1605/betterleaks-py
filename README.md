# betterleaks-py

[![Build and Publish Wheels](https://github.com/as1605/betterleaks-py/actions/workflows/build-wheels.yml/badge.svg)](https://github.com/as1605/betterleaks-py/actions/workflows/build-wheels.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python bindings for [Betterleaks](https://github.com/betterleaks/betterleaks), the ultra-fast secret and credential detection engine written in Go.

---

## Features

- **Fast & Multi-threaded**: Powered by Betterleaks' Go detection pipeline with regex precompilation and multi-pattern Aho-Corasick scanning (scans thousands of lines across 460+ rules in milliseconds).
- **Multi-Component Correlation**: Natively pairs dependent secrets (e.g. AWS Access Key IDs + Secret Access Keys within proximity) to eliminate standalone false positives.
- **Robust CGO + Ctypes Architecture**: Clean memory boundary between Go and Python using JSON transport and explicit memory deallocation—zero segfaults, zero memory leaks.
- **Zero Heavy Python Dependencies**: Built entirely on Python's standard library `ctypes` and `dataclasses`.
- **Rich Finding Metadata**: Returns matched secret values, rule IDs, descriptions, confidence ratings, line and column numbers, fingerprints, and correlated component sets.
- **Configurable**: Works out-of-the-box with embedded Betterleaks rules, or accepts custom `betterleaks.toml` configuration files.

---

## Installation

### Option 1: Pre-built Binary Wheels (Recommended — No Go required)

Pre-compiled binary wheels for **Linux** (`x86_64`, `aarch64`), **macOS** (Apple Silicon `arm64` & Intel `x86_64`), and **Windows** (`x86_64`) are built automatically via GitHub Actions and published under [GitHub Releases](https://github.com/as1605/betterleaks-py/releases).

You can install directly without having Go or C compilers installed:

```bash
# Direct install from the latest release:
pip install "https://github.com/as1605/betterleaks-py/releases/download/v2.0.0-rc.1/betterleaks-2.0.0rc1-cp39-cp39-macosx_26_0_universal2.whl"
```

Or install using `--find-links`:
```bash
pip install --find-links https://github.com/as1605/betterleaks-py/releases/expanded_assets/v2.0.0-rc.1 betterleaks
```

---

### Option 2: Install from GitHub Repository (Builds from source)

If you have Go installed on your machine, you can install directly from git:

```bash
pip install git+https://github.com/as1605/betterleaks-py.git
```

> **Requirements for building from source**:
> - Python >= 3.8
> - Go >= 1.25 (with CGO enabled)
>
> `setup.py` automatically checks `$PATH` as well as standard system Go installation paths (`/opt/homebrew/bin/go`, `/usr/local/bin/go`, `/usr/local/go/bin/go`, etc.). If Go is not found, the installer will attempt to download the pre-compiled binary library for your platform as a fallback.

---

### Option 3: Building Locally from Source

```bash
git clone --recurse-submodules https://github.com/as1605/betterleaks-py.git
cd betterleaks-py
pip install .
```

---

## Quickstart

### Scanning Strings

```python
import betterleaks

content = """
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
"""

findings = betterleaks.scan_string(content)

for finding in findings:
    print(f"[{finding.rule_id}] Secret: {finding.secret}")
    print(f"  Confidence: {finding.confidence}")
    print(f"  Line: {finding.location.start_line}, Col: {finding.location.start_column}")
    print(f"  Description: {finding.description}")

    # Inspect multi-component pairings (e.g. AWS secret key paired with access key)
    if finding.component_sets:
        print(f"  Correlated components: {len(finding.component_sets)}")
```

### Scanning Files

```python
import betterleaks

findings = betterleaks.scan_file("path/to/source_code.py")

for finding in findings:
    print(f"Rule: {finding.rule_id} at {finding.location.path}:{finding.location.start_line}")
```

### Using Custom Configuration

```python
import betterleaks

findings = betterleaks.scan_string(
    "secret = 'XYZ12345'", 
    config_path="custom_betterleaks.toml"
)
```

---

## Data Models

### `Finding`

| Attribute | Type | Description |
|-----------|------|-------------|
| `rule_id` | `str` | Identifier of the triggered rule (e.g. `github-pat`, `aws-access-token`). |
| `description` | `str` | Detailed description of the credential risk. |
| `confidence` | `str` | Detection confidence rating (`low`, `medium`, `high`). |
| `secret` | `str` | Matched credential / secret value (alias for `match.value`). |
| `file` | `Optional[str]` | Target file path, if scanning files. |
| `match` | `Match` | Match object with `full`, `value`, `fingerprint`, and regex `captures`. |
| `location` | `Location` | `path`, `start_line`, `end_line`, `start_column`, `end_column`. |
| `component_sets` | `List[dict]` | Correlated multi-part component findings (e.g. secret keys paired with access keys). |
| `encodings` | `List[str]` | List of encodings discovered during decode passes (e.g. `base64`). |
| `tags` | `List[str]` | List of rule tags. |

`Finding` objects support both attribute access and dictionary subscripting:
```python
finding.rule_id == finding["rule_id"]
finding.secret == finding["secret"]
```

---

## Architecture

`betterleaks-py` uses a hybrid CGO + `ctypes` architecture designed for reliability and maximum performance:

1. **Go Shared Library (`wrapper/cgo_wrapper.go`)**:
   - Compiles as a C-shared library (`libbetterleaks.so` / `.dylib` / `.dll`).
   - Exports a clean C ABI with thread-safe scanner caching.
   - Encapsulates findings into structured JSON payloads across the FFI boundary.
   - Exports an explicit `FreeMemory` routine to deallocate C strings on the Go runtime side.

2. **Python ctypes Client (`src/betterleaks/_lib.py`)**:
   - Loads the shared library across macOS, Linux, and Windows.
   - Manages memory safely in `try...finally` blocks to guarantee no memory leaks.
   - Unpacks JSON findings directly into typed Python dataclasses.

---

## Running Tests

```bash
# In your virtual environment:
pytest -v
```

## License

MIT License. See [LICENSE](LICENSE) for details.
