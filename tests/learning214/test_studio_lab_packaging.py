"""Installed Studio lab uses the current public SDK grammar, without inference."""
import pytest


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_lab_python_matrix(framework):
    from agentic_systems_studio.lab.probes import matrix

    result = matrix("python-runtime", framework)
    assert result["result"]["ok"]
