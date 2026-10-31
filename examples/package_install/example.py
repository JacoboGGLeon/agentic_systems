import importlib.metadata
import agentic_systems as toolkit


def run():
    assert (
        toolkit.__version__
        == importlib.metadata.version("agentic-systems")
        == '2.1.4'
    )
    assert set(toolkit.__all__) == {
        "tool", "skill", "load_skill", "Agent", "System", "Environment", "Eval",
        "RunResult", "Context", "Memory", "pause", "runtime", "framework", "model_artifact",
        "model_server", "Graph", "START", "END", "Command", "Send", "__version__",
    }
    return {
        "input": "installed distribution",
        "process": "Compare metadata, version and public names",
        "output": {"version": toolkit.__version__, "public_api": toolkit.__all__},
    }
