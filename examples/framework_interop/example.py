"""Run the same four-framework declaration used by Studio."""
from agentic_systems_studio.lab.interop import build, run  # noqa: F401

if __name__ == "__main__":
    import json
    print(json.dumps(run(), ensure_ascii=False, indent=2))
