"""Run canonical 2.1.3 checks with application network/process access blocked."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
source = "--source" in sys.argv
if source:
    sys.argv.remove("--source")
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tutorials"))
from _offline import enforce_offline, blocked_attempts  # noqa: E402

enforce_offline()
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
os.environ["AGENTIC_TEST_REQUIRE_INSTALLED"] = "0" if source else "1"
import pytest  # noqa: E402

status = pytest.main([str(ROOT / "tests/v213"), "-q", "-o", "pythonpath=", *sys.argv[1:]])
assert blocked_attempts() == 0, "The offline suite attempted application network/process access"
print("Offline guard: blocked attempts=0; real inference requests=0")
raise SystemExit(status)
