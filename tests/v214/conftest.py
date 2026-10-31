"""The development contract suite never permits application networking."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tutorials"))
from _offline import enforce_offline, blocked_attempts  # noqa: E402

enforce_offline()
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


def pytest_sessionfinish(session, exitstatus):
    assert blocked_attempts() == 0, "Unexpected application networking or subprocess"
