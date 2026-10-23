from types import SimpleNamespace
import agentic_systems as toolkit


def test_model_presentation_survives_agent_system_and_compile(monkeypatch):
    from agentic_systems._engine import factories
    from agentic_systems._engine.results import RunResult

    monkeypatch.setattr(factories, "agent", lambda **kwargs: SimpleNamespace(run=lambda value:
        RunResult(text="La respuesta verificada es 42.", final={"answer": 42}, data={"answer": 42},
                  engine="openai-runtime", model="fixture")))
    actor = toolkit.Agent("answer", runtime=toolkit.runtime(provider="openai-runtime", model="fixture"))
    system = toolkit.System("conversation", toolkit.Sequence((actor,)))
    for unit in (actor, actor.compile(), system, system.compile()):
        result = unit.run("Question")
        assert result.ok and result.text == "La respuesta verificada es 42."
        assert result.final == {"answer": 42} and result.data == {"answer": 42}
        assert result.check_invariants().ok
