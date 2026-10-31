"""The canonical suite is offline even when invoked directly by pytest or mutmut."""
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tutorials"))
from _offline import enforce_offline  # noqa: E402

enforce_offline()

import agentic_systems as toolkit  # noqa: E402

assert toolkit.__version__ == "2.1.4.dev1"
if os.environ.get("AGENTIC_TEST_REQUIRE_INSTALLED") == "1":
    assert "site-packages" in Path(toolkit.__file__).parts, "Install the wheel non-editably"
