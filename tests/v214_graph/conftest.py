"""The current public grammar is LangGraph only; all tests deny inference."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tutorials"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _offline import enforce_offline  # noqa: E402

enforce_offline()
import agentic_systems as toolkit  # noqa: E402

assert toolkit.__version__ == os.environ.get("AGENTIC_TEST_VERSION", '2.1.4')
if os.environ.get("AGENTIC_TEST_REQUIRE_INSTALLED") == "1":
    assert "site-packages" in Path(toolkit.__file__).parts
