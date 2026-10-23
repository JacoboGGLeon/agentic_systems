"""One import and one call for the full deterministic order application."""
from . import verify


def run():
    reports = [verify(backend) for backend in ("native", "langgraph")]
    assert all(report["cases_passed"] == 7 for report in reports)
    return {"reports": reports, "inference_requests": 0}
