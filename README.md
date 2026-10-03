# betterleaks-py

Python bindings for [Betterleaks](https://github.com/betterleaks/betterleaks), the ultra-fast, multi-tenant secret and credential detection engine written in Go.

## Features

- **Fast & Multi-threaded**: Powered by Betterleaks' Go detection pipeline with regex precompilation and multi-pattern Aho-Corasick matching.
- **Robust CGO + Ctypes Architecture**: Stable memory management boundary between Go and Python using JSON transport and explicit memory deallocation.
- **Zero Heavy Python Dependencies**: Uses Python standard library `ctypes` and `dataclasses`.
- **Rich Detection Details**: Returns detected secret value, rule ID, description, confidence rating, line and column numbers, fingerprints, and attributes.
- **Configurable**: Works out-of-the-box with embedded Betterleaks rules, or accepts custom `betterleaks.toml` configuration files.

---

## Installation

### Option 1: Install from GitHub (requires Go >= 1.25)

```bash
pip install git+https://github.com/as1605/betterleaks-py.git
```

> **Note**: Installing directly from git builds the native Go shared library for your system. Ensure Go (>= 1.25) is installed (`brew install go` on macOS, `sudo apt install golang` on Linux).

### Option 2: Pre-built Binary Wheels (No Go required)

Pre-compiled binary wheels for macOS, Linux, and Windows are available under [GitHub Releases](https://github.com/as1605/betterleaks-py/releases). You can install directly without having Go or C compilers installed:

```bash
# Example for macOS Apple Silicon:
pip install https://github.com/as1605/betterleaks-py/releases/download/v2.0.0-rc.1/betterleaks-2.0.0rc1-cp39-cp39-macosx_26_0_universal2.whl
```

### Option 3: Building from Source Locally

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
export GITHUB_TOKEN="ghp_aB3dE5fG7hI9jK1mN3pQ5rS7tU9vW1xY3zA5"
"""

findings = betterleaks.scan_string(content)

for finding in findings:
    print(f"[{finding.rule_id}] Found secret: {finding.secret}")
    print(f"  Confidence: {finding.confidence}")
    print(f"  Line: {finding.location.start_line}, Col: {finding.location.start_column}")
    print(f"  Description: {finding.description}")
```

### Scanning Files

```python
import betterleaks

findings = betterleaks.scan_file("path/to/source_code.py")

for finding in findings:
    print(f"Rule: {finding.rule_id} in {finding.location.path}:{finding.location.start_line}")
```

### Using Custom Config

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
| `rule_id` | `str` | Identifier of the triggered rule (e.g. `github-pat`). |
| `description` | `str` | Description of the credential vulnerability. |
| `confidence` | `str` | Detection confidence (`low`, `medium`, `high`). |
| `secret` | `str` | Matched credential / secret value. |
| `match` | `Match` | Details of the match (raw line, captures, hash fingerprint). |
| `location` | `Location` | `path`, `start_line`, `end_line`, `start_column`, `end_column`. |
| `tags` | `List[str]` | List of rule tags. |

`Finding` objects support both attribute access and dictionary subscripting:
```python
finding.rule_id == finding["rule_id"]
finding.secret == finding["secret"]
```

---

## Running Tests

```bash
pytest tests/
```

## License

MIT License. See [LICENSE](LICENSE) for details.
