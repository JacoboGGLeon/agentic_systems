import pytest
from scripts.two_phase_semantic_application import run_case
from scripts.compact_evaluation_system import run_evaluation, aggregate_decision


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
@pytest.mark.parametrize("conclusion", ["pass", "fail"])
def test_three_agent_pipeline_controls(framework, conclusion):
    source = run_case("python-runtime", "native", "python-runtime")
    fixture = {
        name: dict(
            conclusion=conclusion,
            evidence_ids=["e1"],
            reason="Deterministic fixture, not semantic inference.",
        )
        for name in ("fulfillment", "clarity", "grounding")
    }
    report = run_evaluation(
        source, "python-runtime", framework, "python-runtime", control_decision=fixture
    )
    assert report["execution_passed"], report["result"]
    assert report["verdict"]["reported_semantic_quality"] == conclusion
    assert report["verdict"]["release_approved"] is False
    assert len(report["result"]["children"]) == 3


def test_unknown_reference_cannot_be_approved():
    decision = {
        name: dict(conclusion="pass", evidence_ids=["foreign"], reason="Unsupported.")
        for name in ("fulfillment", "clarity", "grounding")
    }
    verdict = aggregate_decision(
        dict(evidence={"e1": {}}, integrity="passed"), decision
    )
    assert not verdict["judge_structure_valid"]
    assert verdict["reported_semantic_quality"] == "unknown"


@pytest.mark.parametrize(
    "provider", ["openai-runtime", "ollama-runtime", "bedrock-runtime"]
)
def test_judge_keeps_explicit_model_before_execution(monkeypatch, provider):
    import scripts.compact_evaluation_system as app

    original = app.toolkit.system
    observed = {}

    class StopBeforeInference(Exception):
        pass

    def system_factory(*args, **kwargs):
        system = original(*args, **kwargs)

        def compile_without_execution(*args, **kwargs):
            observed["model"] = system.agents[1].model
            raise StopBeforeInference

        monkeypatch.setattr(system, "compile", compile_without_execution)
        return system

    monkeypatch.setattr(app.toolkit, "system", system_factory)
    with pytest.raises(StopBeforeInference):
        app.run_evaluation({}, provider, "native", "explicit-test-model")
    assert observed["model"] == "explicit-test-model"
