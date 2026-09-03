from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from agentic_systems_studio import (
    resolve_colab_proxy_url,
    studio_button_html,
    studio_proxy_url,
)
from agentic_systems_studio.server import (
    DEFAULT_HOST,
    StudioServer,
    present_studio_server,
    resolve_studio_app,
    stop_recorded_studio,
    streamlit_command,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_server_defaults_are_loopback_and_proxy_compatible():
    app = resolve_studio_app(PROJECT_ROOT / "app.py")
    command = streamlit_command(app, port=8765)
    assert DEFAULT_HOST == "127.0.0.1"
    assert command[command.index("--server.address") + 1] == "127.0.0.1"
    assert command[command.index("--server.port") + 1] == "8765"
    assert "--server.enableCORS" not in command
    assert "--server.enableXsrfProtection" not in command
    assert studio_proxy_url(8765) == "/jupyterlab/default/proxy/8765/"


def test_html_button_escapes_urls_and_opens_two_explicit_targets():
    payload = studio_button_html(
        "http://localhost:8501/?a=1&b=2",
        label="Open local",
        alternate_url="/jupyterlab/default/proxy/8501/?a=1&b=2",
        alternate_label="Open through proxy",
    )
    assert "href='http://localhost:8501/?a=1&amp;b=2'" in payload
    assert "href='/jupyterlab/default/proxy/8501/?a=1&amp;b=2'" in payload
    assert payload.count("target='_blank'") == 2
    assert payload.count("rel='noopener noreferrer'") == 2


def test_stop_recorded_studio_ignores_stale_windows_pid(monkeypatch, tmp_path):
    pid_path = tmp_path / "streamlit.pid"
    pid_path.write_text("999999", encoding="utf-8")

    error = OSError("The parameter is incorrect")
    error.winerror = 87

    def stale_pid(*_args):
        raise error

    monkeypatch.setattr("agentic_systems_studio.server.os.kill", stale_pid)
    stop_recorded_studio(pid_path)
    assert not pid_path.exists()


def test_launch_notebook_uses_public_launcher_and_proxy_button():
    path = PROJECT_ROOT / "notebooks" / "01_launch_studio.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert "environment_path = load_studio_environment()" in code
    assert code.index("load_studio_environment()") < code.index("PORT =")
    assert "start_studio_server(" in code
    assert "studio_proxy_url(" in code
    assert "studio_button_html(" in code
    assert "direct_url = studio_server.local_url" in code
    assert "alternate_url=proxy_url" in code
    assert "display(HTML(" in code
    assert "/jupyterlab/default/proxy" in code
    metadata = notebook["metadata"]["agentic_systems"]
    assert metadata["entrypoint"] == "streamlit"
    assert metadata["configuration"] == ".env"
    assert "cli_equivalent" not in metadata


def test_colab_transport_renders_proxy_button_that_opens_a_new_tab(
    monkeypatch, tmp_path
):
    scripts = []
    html_payloads = []
    server = StudioServer(
        process=SimpleNamespace(),
        app_path=tmp_path / "app.py",
        log_path=tmp_path / "streamlit.log",
        pid_path=tmp_path / "streamlit.pid",
        host="127.0.0.1",
        port=8501,
    )

    class ColabOutput:
        def eval_js(self, script):
            scripts.append(script)
            return "https://colab.example/proxy/8501"

    monkeypatch.setattr("agentic_systems_studio.server._colab_output", ColabOutput)
    monkeypatch.setattr(
        "agentic_systems_studio.server._display_html",
        lambda payload: html_payloads.append(payload) or "button-result",
    )

    presentation = present_studio_server(server, transport="auto")

    assert presentation.server is server
    assert presentation.transport == "colab-proxy"
    assert presentation.proxy_url == "https://colab.example/proxy/8501/"
    assert presentation.display_result == "button-result"
    assert scripts == ["google.colab.kernel.proxyPort(8501)"]
    assert len(html_payloads) == 1
    assert "href='https://colab.example/proxy/8501/'" in html_payloads[0]
    assert "target='_blank'" in html_payloads[0]
    assert "Open Agentic Systems Studio" in html_payloads[0]
    assert "iframe" not in html_payloads[0].lower()


def test_resolve_colab_proxy_url_validates_port_and_result(monkeypatch):
    import pytest

    monkeypatch.setattr(
        "agentic_systems_studio.server._colab_output",
        lambda: SimpleNamespace(eval_js=lambda _script: "not-a-url"),
    )
    with pytest.raises(ValueError, match="port must be"):
        resolve_colab_proxy_url(0)
    with pytest.raises(RuntimeError, match="valid kernel-port proxy URL"):
        resolve_colab_proxy_url(8501)


def test_explicit_colab_transport_fails_without_colab_instead_of_falling_back(
    monkeypatch, tmp_path
):
    server = StudioServer(
        process=SimpleNamespace(),
        app_path=tmp_path / "app.py",
        log_path=tmp_path / "streamlit.log",
        pid_path=tmp_path / "streamlit.pid",
        host="127.0.0.1",
        port=8501,
    )
    monkeypatch.setattr("agentic_systems_studio.server._colab_output", lambda: None)

    import pytest

    with pytest.raises(RuntimeError, match="requires google.colab.output"):
        present_studio_server(server, transport="colab-proxy")
