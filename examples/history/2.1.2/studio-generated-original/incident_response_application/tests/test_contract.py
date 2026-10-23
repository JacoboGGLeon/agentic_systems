from incident_response_application.system import STAGES, build_system

def test_declared_stage_count():
    assert len(STAGES) == 4

def test_system_builds_and_inspects():
    compiled = build_system()
    assert compiled.inspect()["unit_count"] == len(STAGES)
