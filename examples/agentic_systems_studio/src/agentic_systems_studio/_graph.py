"""Internal application state adapter; orchestration is ordinary LangGraph."""

from dataclasses import replace
import pydantic
import agentic_systems as toolkit


class Payload(pydantic.BaseModel):
    payload: dict


def pipeline(name, steps):
    graph = toolkit.Graph(Payload)
    previous = toolkit.START
    for index, operation in enumerate(steps):
        key = "step_" + str(index)

        def node(state, operation=operation):
            raw = (
                operation.run(state.payload)
                if hasattr(operation, "run")
                else operation(state.payload)
            )
            return (
                replace(raw, data={"payload": raw.data})
                if isinstance(raw, toolkit.RunResult)
                else {"payload": raw}
            )

        graph.add_node(key, node)
        graph.add_edge(previous, key)
        previous = key
    graph.add_edge(previous, toolkit.END)
    return toolkit.System(name, graph=graph)
