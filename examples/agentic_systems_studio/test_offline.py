"""Offline application and UI contracts; no provider calls."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tutorials"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from _offline import enforce_offline, blocked_attempts  # noqa: E402

enforce_offline()
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
import pytest  # noqa: E402

if __name__ == "__main__":
    status = pytest.main([str(Path(__file__).parent / "tests"), "-q", "-o", "pythonpath=", *sys.argv[1:]])
    assert blocked_attempts() == 0
    raise SystemExit(status)
