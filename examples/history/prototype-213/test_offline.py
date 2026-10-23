"""Run only this prototype's tests, without third-party pytest auto-plugins."""

import os
from pathlib import Path
import sys

# Unrelated auto-plugins can spawn Windows OS probes while rendering failures.
# Disable them rather than weakening the subprocess/network guard.
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import pytest  # noqa: E402

if __name__ == "__main__":
    home = Path(__file__).resolve().parent
    raise SystemExit(
        pytest.main(
            [
                str(home / "tests"),
                "-q",
                "--color=no",
                "--tb=short",
                "-o",
                "pythonpath=",
                "-o",
                "cache_dir=.tmp/unified-grammar/pytest_cache",
                *sys.argv[1:],
            ]
        )
    )
