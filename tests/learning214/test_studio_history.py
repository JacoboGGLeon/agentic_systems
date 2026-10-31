"""Presentation hints must never masquerade as conversation memory."""

from pathlib import Path
import pytest


@pytest.mark.parametrize("framework", ("native", "openai-agents", "strands"))
def test_visual_greeting_does_not_enter_history(monkeypatch, framework):
    monkeypatch.setenv("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    from streamlit.testing.v1 import AppTest

    path = (
        Path(__file__).resolve().parents[2]
        / "examples/agentic_systems_studio/src/agentic_systems_studio/ui.py"
    )
    app = AppTest.from_file(str(path), default_timeout=45).run()
    assert not app.exception and not app.session_state["messages"]
    app.selectbox(key="framework").set_value(framework).run()
    app.chat_input[0].set_value("Hola").run()
    result = app.session_state["last_result"]
    assert result.ok and result.data["history_turns"] == 0
    assert result.meta["framework"] == framework
    app.button(key="clear_conversation").click().run()
    assert "last_result" not in app.session_state
    assert not app.session_state["messages"]
