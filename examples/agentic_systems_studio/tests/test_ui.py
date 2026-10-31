from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_actual_chat_ui_with_each_framework(framework):
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
    ).run()
    assert not app.exception
    app.selectbox(key="framework").set_value(framework).run()
    app.chat_input[0].set_value("Hola desde la prueba de interfaz").run()
    assert not app.exception
    result = app.session_state["last_result"]
    assert result.ok and result.text and result.meta["framework"] == framework
    assert "mock determinista" in result.text


def test_python_ui_needs_no_dotenv(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(tmp_path / "absent.env"))
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
    ).run()
    assert not app.exception
    app.chat_input[0].set_value("Hola sin credenciales").run()
    assert not app.exception and app.session_state["last_result"].ok
