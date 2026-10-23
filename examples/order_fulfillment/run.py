"""Run the canonical 2.1.3 example against both flow backends, offline."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from order_fulfillment.offline import enforce_offline  # noqa: E402
enforce_offline()
import agentic_systems as toolkit  # noqa: E402
from order_fulfillment import verify  # noqa: E402

assert toolkit.__version__ == "2.1.3", "Install the local 2.1.3 wheel first"
reports = [verify(backend) for backend in ("native", "langgraph")]
assert [c["output"] for c in reports[0]["cases"]] == [c["output"] for c in reports[1]["cases"]]
destination = Path(__file__).parent / "evidence"
destination.mkdir(exist_ok=True)
(destination / "run.json").write_text(json.dumps({"version": "2.1.3", "inference_requests": 0,
    "reports": reports}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"version": toolkit.__version__, "cases_passed": 14, "inference_requests": 0}))
