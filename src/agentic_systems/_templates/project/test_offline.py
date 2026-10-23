"""Dedicated offline test process; no third-party pytest auto-plugins."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
sys.path.insert(0, str(ROOT / "src"))
from order_fulfillment.offline import enforce_offline  # noqa: E402
enforce_offline()
import pytest  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(pytest.main([str(ROOT / "tests"), "-q", *sys.argv[1:]]))
