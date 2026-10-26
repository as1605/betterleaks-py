# betterleaks-cli

[![Build and Publish CLI](https://github.com/as1605/betterleaks-py/actions/workflows/build-cli.yml/badge.svg)](https://github.com/as1605/betterleaks-py/actions/workflows/build-cli.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Standalone command-line tool for [Betterleaks](https://github.com/betterleaks/betterleaks), the ultra-fast secret and credential detection engine written in Go.

This package installs **only the standalone `betterleaks` (and `gitleaks`) command-line executable**.

> **Looking for Python bindings?**  
> If you want to detect secrets from Python code (`import betterleaks`, `scan_string`, `scan_file`), install [`betterleaks-py`](https://pypi.org/project/betterleaks-py/) instead.

---

## Installation

```bash
pip install betterleaks-cli
```

Pre-compiled binary wheels are available for:
- **Linux**: `x86_64`, `aarch64`
- **macOS**: Apple Silicon (`arm64`), Intel (`x86_64`)
- **Windows**: `x86_64`

No Go compiler or external dependencies are required to install.

---

## Usage

Once installed, the `betterleaks` (and alias `gitleaks`) command is available in your environment:

```bash
# Scan a git repository
betterleaks git .

# Scan an uncommitted git working tree
betterleaks git --staged

# Scan arbitrary files or directories
betterleaks filesystem /path/to/project

# Scan from stdin (great for pre-commit hooks and CI pipelines)
cat sensitive_file.env | betterleaks stdin

# View all options and supported flags
betterleaks --help
```

---

## Pre-commit Hook Integration

You can easily integrate `betterleaks-cli` into your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: betterleaks
        name: Betterleaks Secret Detection
        entry: betterleaks protect --staged --verbose
        language: system
        pass_filenames: false
```

---

## Python API Alternative

For programmatic Python use:

```bash
pip install betterleaks-py
```

```python
import betterleaks

findings = betterleaks.scan_string("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
for f in findings:
    print(f"[{f.rule_id}] {f.secret} at line {f.location.start_line}")
```

---

## License

MIT License. See [LICENSE](https://github.com/as1605/betterleaks-py/blob/main/LICENSE) for details.
