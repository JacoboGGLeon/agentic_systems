import agentic_systems as toolkit


def build(backend="native"):
    worker = toolkit.Agent("sum", toolkit.Action("sum", lambda d: {"total": d["previous"] + d["amount"]}), backend=backend)
    return toolkit.Environment("ledger", worker, ({"amount": 2}, {"amount": 3}, {"amount": 100}),
        memory={"total": 0}, observe=lambda row, memory: {"amount": row["amount"], "previous": memory["total"]},
        update=lambda memory, row, result: result.data, stop=lambda memory, result: memory["total"] >= 5)


def run():
    reports = []
    for backend in ("native", "langgraph"):
        episode = build(backend)
        result = episode.run()
        assert result.ok and result.data["outputs"] == [{"total": 2}, {"total": 5}]
        assert result.data["summary"]["terminated"]
        replay = episode.run()
        assert replay.data["outputs"] == result.data["outputs"]
        assert replay.data["summary"] == result.data["summary"]
        assert replay.execution_id != result.execution_id
        reports.append({"backend": backend, "result": result.to_dict()})
    return {"input": [{"amount": 2}, {"amount": 3}, {"amount": 100}], "process": "Memory 0 → 2 → 5; stop before 100", "output": reports}
