from __future__ import annotations

import agentic_systems as toolkit
import pytest

from agentic_systems_studio.notebook import (
    NotebookStudioSession,
    _message_html,
    display_notebook_studio,
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
