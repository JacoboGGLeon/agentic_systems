import importlib.metadata
import agentic_systems as toolkit


def run():
    assert toolkit.__version__ == importlib.metadata.version("agentic-systems") == "2.1.3"
    assert len(toolkit.__all__) == 18
    return {"input": "installed distribution", "process": "Compare metadata, version and public names",
            "output": {"version": toolkit.__version__, "public_api": toolkit.__all__}}
