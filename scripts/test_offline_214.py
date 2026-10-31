"""Run the 2.1.4 development and inherited regressions with no inference."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
source = "--source" in sys.argv
if source:
    sys.argv.remove("--source")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "examples/agentic_systems_studio/src"))
    sys.path.insert(0, str(ROOT / "integrations/ada/src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tutorials"))
from _offline import enforce_offline, blocked_attempts, blocked_details  # noqa: E402

enforce_offline()
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
os.environ["AGENTIC_TEST_REQUIRE_INSTALLED"] = "0" if source else "1"
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
import pytest  # noqa: E402

os.chdir(ROOT)
status = pytest.main(["-c", str(ROOT / "pyproject.toml"), "-q", "-o", "pythonpath=", *sys.argv[1:]])
if blocked_attempts():
    print("Offline guard diagnostics:", blocked_details())
assert blocked_attempts() == 0, "The suite attempted application network/process access"
print("Offline guard: blocked attempts=0; real inference requests=0")
raise SystemExit(status)
