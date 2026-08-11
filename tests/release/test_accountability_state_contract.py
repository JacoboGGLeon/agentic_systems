from __future__ import annotations

from tutorials.skills.accountability_otc import multi_agent_system as accountability_tools_mas


class _Result:
    def __init__(self, data, text="ok"):
        self.data = data
        self.text = text

    def normalized(self):
        return {"answer": {"data": self.data, "text": self.text}, "blocks": {"tool_actions": [], "sql": [], "tables": []}}


def test_2499_fundamentals_arithmetic_system_is_not_hidden_in_grouped_helper() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert not (root / "tutorials/tools/fundamentals_arithmetic").exists()

def test_accountability_tool_output_preserves_plan_for_notebooks():
    state = {
        "user_prompt": "mtm por clase de activo",
        "route": "nl2sql",
        "plan": {"route": "nl2sql"},
        "tool_input": {"question": "mtm por clase de activo"},
    }
    updated = accountability_tools_mas._tool_output(_Result({"rows": []}, text="respuesta"), state)

    assert updated["user_prompt"] == "mtm por clase de activo"
    assert updated["selected_tool"] == "nl2sql"
    assert updated["plan"] == {"route": "nl2sql"}
    assert updated["tool_input"] == {"question": "mtm por clase de activo"}
    assert updated["final_answer"] == "respuesta"
