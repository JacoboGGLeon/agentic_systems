"""Run the reference graph offline, without provider flags."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from order_fulfillment.offline import enforce_offline  # noqa: E402

enforce_offline()
from order_fulfillment import demonstrate  # noqa: E402

if __name__ == "__main__":
    report = demonstrate()
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/run-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Input:", report["input"])
    print("Process:", " → ".join(report["process"]))
    print("Output:", report["output"])
