from __future__ import annotations

import agentic_systems as lab


def _report() -> lab.EvalReport:
    @lab.tool
    def add(a: float, b: float) -> dict:
        return {"value": a + b}

    agent = lab.agent(
        name="test_eval_agent",
        tools=[add],
        engine="python-direct",
        contract=lab.AgentContract(tool_expectation=lab.expect.exactly("add")),
        policy=lab.RunPolicy(max_tool_calls=1),
    )
    return lab.run_eval(agent, [{
        "name": "math_01_default",
        "input": {"tool": "add", "input": {"a": 1, "b": 2}},
        "expected": {"must_call": ["add"], "data_contains": {"tool": "add", "ok": True, "value": 3}},
    }])


def test_eval_lineage_human_text_is_concise_and_not_duplicated() -> None:
    lineage = _report().lineage(name="test.eval.lineage")
    text = lineage.human_text()
    assert "No executable step was recorded" not in text
    assert "math_01: math_01" not in text
    assert "math_01_default" in text


def test_eval_human_result_suppresses_unspecified_validation_table(capsys) -> None:
    report = _report()
    lineage = report.lineage(name="test.eval.lineage")
    lab.human_result(
        report,
        title="Eval batch + Lineage Memory · fundamentals",
        pretty=False,
        show_lineage=True,
        lineage=lineage,
    )
    out = capsys.readouterr().out
    assert "Estado: OK" in out
    assert "Qué pasó · Lineage Memory" in out
    assert "Casos evaluados" in out
    assert "no se ejecutaron tools" not in out
    assert "Regla esperada: unspecified" not in out
    assert "Validación" not in out
