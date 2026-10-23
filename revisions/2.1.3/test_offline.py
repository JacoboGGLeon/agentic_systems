"""Test the installed 2.1.3 wheel, never the root 2.1.2 source checkout."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
sys.path.insert(0, str(ROOT / "tutorials"))
from _offline import enforce_offline
enforce_offline()
import pytest

if __name__ == "__main__":
    raise SystemExit(pytest.main([str(Path(__file__).parent / "tests"), "-q", "-o", "pythonpath=", *sys.argv[1:]]))
