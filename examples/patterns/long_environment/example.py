"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

worker = toolkit.Agent("ledger", toolkit.Action("sum", lambda data: {"balance": data["balance"] + data["amount"]}))
app = toolkit.System("application", toolkit.Sequence((worker,)))
episode = toolkit.Environment("ledger_episode", app, records=tuple({"amount": 1} for _ in range(30)),
    memory={"balance": 0}, observe=lambda row, memory: {**row, **memory},
    update=lambda memory, row, result: result.data)


def run():
    first = episode.run()
    second = episode.run()
    assert first.ok and second.ok
    assert first.data["summary"]["memory"] == second.data["summary"]["memory"] == {"balance": 30}
    assert first.execution_id != second.execution_id
    return first
