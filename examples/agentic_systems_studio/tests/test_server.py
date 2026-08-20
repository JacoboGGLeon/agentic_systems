from __future__ import annotations

import json
from pathlib import Path

import agentic_systems_studio.__main__ as studio_cli
from agentic_systems_studio import studio_button_html, studio_proxy_url
from agentic_systems_studio.server import (
    DEFAULT_HOST,
    resolve_studio_app,
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


def test_html_button_escapes_url_and_opens_new_tab():
    payload = studio_button_html(
        "/jupyterlab/default/proxy/8501/?a=1&b=2",
        label="Abrir Studio",
    )
    assert "href='/jupyterlab/default/proxy/8501/?a=1&amp;b=2'" in payload
    assert "target='_blank'" in payload
    assert "rel='noopener noreferrer'" in payload
    assert "Abrir Studio" in payload


def test_cli_serve_delegates_to_shared_launcher(monkeypatch):
    captured = {}

    def fake_serve(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(studio_cli, "serve_studio", fake_serve)
    assert studio_cli.main(
        [
            "serve",
            "--port",
            "8765",
            "--proxy-prefix",
            "/jupyterlab/default/proxy",
            "--detach",
        ]
    ) == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8765
    assert captured["proxy_prefix"] == "/jupyterlab/default/proxy"
    assert captured["detach"] is True


def test_launch_notebook_uses_same_public_launcher_and_html_proxy_button():
    path = PROJECT_ROOT / "notebooks" / "02_launch_studio.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert "start_studio_server(" in code
    assert "studio_proxy_url(" in code
    assert "studio_button_html(" in code
    assert "display(HTML(" in code
    assert "/jupyterlab/default/proxy" in code
    assert notebook["metadata"]["agentic_systems"]["cli_equivalent"] == (
        "agentic-studio serve"
    )
