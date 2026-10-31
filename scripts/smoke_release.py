"""Check the installed SDK/CLI outside source; no inference or external clients."""

import json
import os
from pathlib import Path
import sys

import pydantic
import agentic_systems as toolkit


def main():
    expected = os.environ.get("EXPECTED_VERSION")
    if not expected:
        raise ValueError("EXPECTED_VERSION is required")
    assert toolkit.__version__ == expected
    assert "site-packages" in Path(toolkit.__file__).parts, toolkit.__file__

    class State(pydantic.BaseModel):
        value: int

    @toolkit.tool
    def increment(value: int) -> dict:
        return {"value": value + 1}

    graph = toolkit.Graph(State)
    graph.add_node("increment", increment)
    graph.add_edge(toolkit.START, "increment")
    graph.add_edge("increment", toolkit.END)
    unit = toolkit.System("installed-smoke", graph)
    result = unit.compile().run({"value": 4})
    assert result.ok and result.data == {"value": 5}
    assert toolkit.RunResult(**result.to_dict()).check_invariants().ok
    print(json.dumps({"version": toolkit.__version__, "module": toolkit.__file__,
                      "python": sys.version.split()[0], "output": result.data,
                      "human_results": result.human_results(), "inference_requests": 0}))


if __name__ == "__main__":
    main()
