"""User Pydantic state must not inflate toolkit grammar coverage."""
from grammar_coverage_214 import Coverage

def test_user_state_is_not_a_toolkit_constructor():
    coverage = Coverage()
    with coverage.example("teaching"):
        exec(compile("import pydantic\nclass State(pydantic.BaseModel):\n    value: int\nState(value=3)", "<ipython-input-coverage>", "exec"), {})
    assert coverage.rows["teaching"] == set()
    with coverage.example("teaching"):
        exec(compile("import agentic_systems as toolkit\ntoolkit.runtime(provider='python-runtime')", "<ipython-input-coverage>", "exec"), {})
    assert "runtime" in coverage.rows["teaching"]