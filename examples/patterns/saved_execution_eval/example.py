"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

calls = []


def calculate(data):
    calls.append(data)
    return {"total": sum(data["values"])}


candidate = toolkit.Agent("candidate", toolkit.Action("sum", calculate))


def run():
    saved = candidate.run({"values": [2, 3]})
    before = len(calls)
    frozen = toolkit.RunResult(**saved.to_dict())
    observer = toolkit.Agent("saved_execution", toolkit.Action("read", lambda data: frozen))
    result = toolkit.Eval("observe", observer, cases=({"input": {}, "expected": {"data": {"total": 5}}},)).run()
    assert result.ok and len(calls) == before
    return {"original": saved.to_dict(), "evaluation": result.to_dict(), "candidate_reruns": 0}
