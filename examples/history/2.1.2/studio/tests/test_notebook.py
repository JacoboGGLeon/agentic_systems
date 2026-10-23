from __future__ import annotations

import agentic_systems as toolkit
import pytest

from agentic_systems_studio import notebook as notebook_module
from agentic_systems_studio.notebook import (
    NotebookStudioSession,
    _message_html,
    display_notebook_studio,
)


@pytest.fixture(autouse=True)
def isolated_notebook_environment(monkeypatch, tmp_path):
    """Controller tests own their config; never discover the developer's .env."""
    settings = {
        "AGENTIC_SYSTEMS_PROVIDER": "vllm-runtime",
        "AGENTIC_SYSTEMS_FRAMEWORK": "native",
        "AGENTIC_SYSTEMS_MODEL": "",
        "VLLM_MODEL": "test-model",
        "VLLM_BASE_URL": "http://127.0.0.1:1/v1",
    }
    environment = tmp_path / ".env"
    environment.write_text(
        "".join(f"{key}={value}\n" for key, value in settings.items()),
        encoding="utf-8",
    )
    # Register every key with monkeypatch so dotenv writes are restored too.
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))
    monkeypatch.chdir(tmp_path)
    # Provider discovery is exercised separately; widget tests must not probe AWS.
    monkeypatch.setattr(
        notebook_module,
        "configured_provider_names",
        lambda: ("python-runtime", "vllm-runtime"),
    )


class _FakeStudio:
    def __init__(self) -> None:
        self.calls = []

    def run(self, message, *, history):
        self.calls.append({"message": message, "history": list(history)})
        return toolkit.RunResult(
            text=f"Verified answer: {message}",
            engine="vllm-runtime",
            model="test-model",
            usage={"requests": 1, "total_tokens": 12},
        )


def test_notebook_session_runs_the_canonical_system_and_preserves_history():
    fake = _FakeStudio()
    session = NotebookStudioSession(
        provider="vllm-runtime",
        framework="native",
        system_factory=lambda _config: fake,
    )

    first = session.run("hola")
    second = session.run("resume la conversación")

    assert first.text == "Verified answer: hola"
    assert second.text == "Verified answer: resume la conversación"
    assert len(fake.calls[0]["history"]) == 1
    assert len(fake.calls[1]["history"]) == 3
    assert session.messages[-1]["processing"].startswith("✓ Procesado")
    assert "total_tokens=12" in session.messages[-1]["usage"]
    assert session.last_result is second
    assert session.config.provider == "vllm-runtime"
    assert session.config.model == "test-model"

    session.clear()

    assert len(session.messages) == 1
    assert session.last_result is None


def test_notebook_failure_is_visible_and_preserves_the_user_message():
    pytest.importorskip("ipywidgets")

    class FailingStudio:
        def run(self, _message, *, history):
            assert history
            raise RuntimeError("private provider detail")

    session = NotebookStudioSession(
        provider="vllm-runtime",
        framework="native",
        system_factory=lambda _config: FailingStudio(),
    )
    view = display_notebook_studio(session)
    view.prompt.value = "intenta"
    view.send.click()

    assert session.messages[-1] == {"role": "user", "content": "intenta"}
    assert "RuntimeError" in view.status.value
    assert "private provider detail" not in view.status.value


def test_notebook_transcript_escapes_generated_html():
    rendered = _message_html(
        [{"role": "assistant", "content": "<script>alert('x')</script>"}]
    )

    assert "&lt;script&gt;" in rendered
    assert "<script>" not in rendered


def test_notebook_view_routes_send_through_the_session():
    pytest.importorskip("ipywidgets")
    fake = _FakeStudio()
    session = NotebookStudioSession(
        provider="vllm-runtime",
        framework="native",
        system_factory=lambda _config: fake,
    )

    view = display_notebook_studio(session)
    view.prompt.value = "17 * 19"
    view.send.click()

    assert view.provider.value == "vllm-runtime"
    assert view.framework.value == "native"
    assert fake.calls[-1]["message"] == "17 * 19"
    assert session.last_result.text == "Verified answer: 17 * 19"
