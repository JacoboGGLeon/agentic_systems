"""Deterministic contracts and measured evidence; no provider access."""
from copy import deepcopy
import json
from pathlib import Path

import agentic_systems as toolkit
from .offline import blocked_attempts
from .system import build_system


def load_cases():
    return json.loads((Path(__file__).parent / "fixtures/cases.json").read_text(encoding="utf-8"))


def check_tree(output):
    nodes = list(output.walk())
    assert len({n.execution_id for n in nodes}) == len(nodes)
    for node in nodes:
        for child in node.children:
            assert child.parent_execution_id == node.execution_id
    events = [e for n in nodes for e in n.tool_events]
    assert len({e.id for e in events}) == len(events)
    toolkit.RunResult(**json.loads(json.dumps(output.to_dict(), allow_nan=False)))


def trace(output):
    return [{"step": n.meta["name"], "ok": n.ok, "output": n.data}
            for n in output.walk() if n.meta.get("kind") == "action"]


def verify(backend="native"):
    blocked_before = blocked_attempts()
    unit = build_system(backend)
    prepared = unit.compile()
    cases = load_cases()
    rows = []
    for case in cases:
        payload = deepcopy(case["input"])
        output = prepared.run(payload)
        assert payload == case["input"]
        check_tree(output)
        assert output.ok == case["expected"]["ok"], output.to_dict()
        if output.ok:
            assert output.data == case["expected"]["data"], output.to_dict()
        events = [e for n in output.walk() for e in n.tool_events]
        names = {e.name for e in events}
        if case["name"] == "invalid":
            assert names == {"normalize_order", "validate_order", "reject_order"}
        elif case["name"] == "inventory_failure":
            assert names == {"normalize_order", "validate_order", "price_order", "check_inventory"}
            assert any(e.name == "price_order" and e.ok for e in events)
            assert any(e.name == "check_inventory" and not e.ok for e in events)
            assert any("controlled_inventory_unavailable" in str(n.errors) for n in output.walk())
        else:
            terminal = {"approved": "approve_order", "review": "review_order", "rejected": "reject_order"}
            assert names == {"normalize_order", "validate_order", "price_order", "check_inventory",
                             "assess_policy", terminal[output.data["decision"]]}
        rows.append({"name": case["name"], "input": case["input"], "passed": True,
                     "expected": case["expected"], "process": trace(output),
                     "output": output.data, "ok": output.ok, "result": output.to_dict()})

    accepted = [case for case in cases if case["expected"]["ok"]]
    episode = toolkit.Environment("orders", unit, tuple(c["input"] for c in accepted)).run()
    assert episode.ok and episode.data["outputs"] == [c["expected"]["data"] for c in accepted]
    assert episode.data["summary"]["state"] == {"processed": len(accepted)}
    assert len(episode.data["history"]) == len(accepted)
    for transition, child in zip(episode.data["history"], episode.children):
        assert transition["execution_id"] == child.execution_id
    check_tree(episode)

    judged = toolkit.Eval("order_contract", unit, tuple(accepted)).run()
    assert judged.ok and judged.data["passed"] == len(accepted) and judged.data["failed"] == 0
    check_tree(judged)
    wrong = deepcopy(accepted[0])
    wrong["expected"]["data"]["total_cents"] += 1
    negative = toolkit.Eval("wrong_total", unit, (wrong,)).run()
    assert not negative.ok and negative.data["failed"] == 1 and negative.children[0].ok
    check_tree(negative)
    attempts = blocked_attempts() - blocked_before
    assert attempts == 0
    return {"backend": backend, "passed": True, "target_version": toolkit.__version__,
            "sdk_version": toolkit.__version__, "inference_requests": 0,
            "blocked_network_or_subprocess_attempts": attempts,
            "cases_passed": len(rows), "cases": rows, "topology": prepared.inspect(),
            "environment": episode.to_dict(), "evaluation": judged.to_dict(),
            "negative_control": negative.to_dict()}
