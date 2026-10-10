import tempfile

import pytest

import betterleaks
from betterleaks import BetterleaksError

GH_TOKEN = "gh" + "p_aB3dE5fG7hI9jK1mN3pQ5rS7tU9vW1xY3zA5"


def test_scan_file_with_secret():
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as f:
        f.write(f"# Config file\nAPI_KEY = '{GH_TOKEN}'\n")
        f.flush()
        filename = f.name

    try:
        findings = betterleaks.scan_file(filename)
        assert len(findings) == 1
        assert findings[0].rule_id == "github-pat"
        assert findings[0].secret == GH_TOKEN
        assert findings[0].location.path == filename
        assert findings[0].location.start_line == 2
    finally:
        import os

        if os.path.exists(filename):
            os.remove(filename)


def test_scan_file_clean():
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
        f.write("Just some clean log statements\nhello world\n")
        f.flush()
        filename = f.name

    try:
        findings = betterleaks.scan_file(filename)
        assert findings == []
    finally:
        import os

        if os.path.exists(filename):
            os.remove(filename)


def test_scan_nonexistent_file():
    with pytest.raises(BetterleaksError):
        betterleaks.scan_file("/path/to/nonexistent/file/12345.txt")
