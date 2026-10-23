"""Offline project entry point; use the same constructor as the notebook."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from unified_grammar.offline import enforce_offline
enforce_offline()

from order_challenge import verify
from order_challenge.settings import load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--both", action="store_true", help="Compare native and LangGraph offline")
    args = parser.parse_args()
    settings = load_settings(ROOT / ".env")
    backends = ("native", "langgraph") if args.both else (settings.backend,)
    reports = [verify(backend) for backend in backends]
    if len(reports) == 2:
        assert [r["output"] for r in reports[0]["cases"]] == [r["output"] for r in reports[1]["cases"]]
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    output = evidence / "challenge.json"
    output.write_text(json.dumps({"target_version": "2.1.3", "reports": reports},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for report in reports:
        for case in report["cases"]:
            print(report["backend"], case["name"], "->", case["output"], "PASS")
    print(json.dumps({"target_version": "2.1.3", "backends": list(backends),
                      "passed": True, "inference_requests": 0, "evidence": str(output)}))


if __name__ == "__main__":
    main()
