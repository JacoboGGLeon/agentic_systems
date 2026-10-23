import json
import agentic_systems as toolkit


def run():
    result = toolkit.Agent("incrementer", toolkit.Action("increment", lambda d: {"value": d["value"] + 1})).run({"value": 3})
    payload = json.loads(json.dumps(result.to_dict()))
    restored = toolkit.RunResult(**payload)
    assert restored.to_dict() == payload and restored.check_invariants().ok
    memory = restored.lineage(name="increment", question="What happened?", goal="Explain execution", tags=["offline"], metadata={"fixture": True}, max_tool_rows=2)
    assert memory.to_dict()["steps"] and memory.explain()["ok"]
    return {"input": {"value": 3}, "process": restored.trace(), "output": payload,
            "lineage": memory.to_dict(), "prompt_context": memory.to_prompt_context(max_chars=500)}
