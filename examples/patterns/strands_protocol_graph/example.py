"""Current API adaptation; see README for its measured scope."""
from pathlib import Path
import tempfile
from agentic_systems_studio.budget import CampaignBudget
from agentic_systems_studio.lab.probes import protocols


def run():
    # These are real local protocols. A zero-inference transport guard remains
    # active for the whole process; run this example in its own process.
    budget = CampaignBudget(Path(tempfile.mkdtemp()) / "local.json", {}, "local-protocols", usd=0, requests=0)
    budget.install()
    return {"mcp": protocols("python-runtime", "mcp", budget),
            "a2a": protocols("python-runtime", "a2a", budget), "inference_requests": 0}
