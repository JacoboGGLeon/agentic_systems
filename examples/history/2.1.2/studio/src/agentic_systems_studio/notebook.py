"""Notebook-native presentation adapter for hosts without WebSocket proxying."""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
from typing import Any, Callable

from agentic_systems.registry import FRAMEWORK_NAMES

from .conversation import (
    ConversationConfig,
    build_conversational_system,
    configured_provider_names,
)
from .presentation import processing_mark, public_result_payload, usage_mark


_GREETING = "Ready. Ask a question or request a verified calculation."


@dataclass(slots=True)
class NotebookStudioSession:
    """Stateful controller shared by the notebook widgets and direct tests."""

    provider: str
    framework: str
    system_factory: Callable[[ConversationConfig], Any] = field(
        default=build_conversational_system,
        repr=False,
    )
    messages: list[dict[str, str]] = field(
        default_factory=lambda: [{"role": "assistant", "content": _GREETING}]
    )
    last_result: Any | None = None
    _systems: dict[tuple[Any, ...], Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_environment(cls) -> "NotebookStudioSession":
        config = ConversationConfig.from_environment()
        return cls(provider=config.provider, framework=config.framework)

    @property
    def config(self) -> ConversationConfig:
        return ConversationConfig.from_environment(
            provider=self.provider,
            framework=self.framework,
        )

    def select(self, *, provider: str, framework: str) -> None:
        """Select independent runtime axes without changing credentials."""

        config = ConversationConfig.from_environment(
            provider=provider,
            framework=framework,
        )
        self.provider = config.provider
        self.framework = config.framework

    def _system(self) -> Any:
        config = self.config
        key = (
            config.provider,
            config.framework,
            config.model,
            config.timeout_s,
        )
        if key not in self._systems:
            self._systems[key] = self.system_factory(config)
        return self._systems[key]

    def run(self, message: str) -> Any:
        """Run the canonical conversational System and preserve public history."""

        clean = message.strip()
        if not clean:
            raise ValueError("A non-empty message is required")
        prior_history = list(self.messages)
        self.messages.append({"role": "user", "content": clean})
        result = self._system().run(clean, history=prior_history)
        self.messages.append(
            {
                "role": "assistant",
                "content": result.text,
                "processing": processing_mark(result),
                "usage": usage_mark(result),
            }
        )
        self.last_result = result
        return result

    def clear(self) -> None:
        self.messages[:] = [{"role": "assistant", "content": _GREETING}]
        self.last_result = None


@dataclass(slots=True)
class NotebookStudioView:
    """Public handle returned after rendering Studio in a notebook."""

    session: NotebookStudioSession
    root: Any
    provider: Any
    framework: Any
    prompt: Any
    send: Any
    clear: Any
    transcript: Any
    status: Any
    latest: Any


def _message_html(messages: list[dict[str, str]]) -> str:
    rows = []
    for message in messages:
        role = "You" if message.get("role") == "user" else "Agentic System"
        content = html.escape(str(message.get("content", ""))).replace("\n", "<br>")
        details = "".join(
            f'<div class="as-detail">{html.escape(str(message[key]))}</div>'
            for key in ("processing", "usage")
            if message.get(key)
        )
        rows.append(
            f'<section class="as-message as-{message.get("role", "assistant")}">'
            f'<strong>{role}</strong><div class="as-content">{content}</div>'
            f"{details}</section>"
        )
    return """
    <style>
      .as-message {border:1px solid #d8dee9;border-radius:10px;padding:12px;
        margin:8px 0;font-family:system-ui,sans-serif}
      .as-user {background:#f4f6f8}.as-assistant {background:#fff}
      .as-content {margin-top:6px}.as-detail {color:#68707c;font-size:12px;
        margin-top:8px;overflow-wrap:anywhere}
    </style>
    """ + "".join(rows)


def display_notebook_studio(
    session: NotebookStudioSession | None = None,
) -> NotebookStudioView:
    """Render Studio using Jupyter widgets and the canonical conversational System."""

    try:
        import ipywidgets as widgets
        from IPython.display import HTML, clear_output, display
    except ImportError as exc:  # pragma: no cover - exercised by delivery checks
        raise RuntimeError(
            "Notebook Studio requires agentic-systems-studio[notebook]."
        ) from exc

    active = session or NotebookStudioSession.from_environment()
    providers = configured_provider_names()
    if active.provider not in providers:
        providers = (active.provider, *providers)
    frameworks = tuple(FRAMEWORK_NAMES)
    provider_widget = widgets.Dropdown(
        options=providers,
        value=active.provider,
        description="Provider",
        layout=widgets.Layout(width="48%"),
    )
    framework_widget = widgets.Dropdown(
        options=frameworks,
        value=active.framework,
        description="Framework",
        layout=widgets.Layout(width="48%"),
    )
    prompt_widget = widgets.Textarea(
        placeholder="Message the Agentic System",
        layout=widgets.Layout(width="82%", height="72px"),
    )
    send_widget = widgets.Button(
        description="Send",
        button_style="primary",
        icon="paper-plane",
        layout=widgets.Layout(width="84px", height="40px"),
    )
    clear_widget = widgets.Button(
        description="Clear",
        icon="trash",
        layout=widgets.Layout(width="84px", height="40px"),
    )
    transcript = widgets.Output(
        layout=widgets.Layout(border="1px solid #e5e7eb", padding="12px")
    )
    status = widgets.HTML()
    latest = widgets.HTML()

    def render() -> None:
        with transcript:
            clear_output(wait=True)
            display(HTML(_message_html(active.messages)))
        config = active.config
        status.value = (
            "<small>"
            f"provider={html.escape(config.provider)} · "
            f"framework={html.escape(config.framework)} · "
            f"model={html.escape(config.model or 'provider default')}"
            "</small>"
        )
        payload = (
            public_result_payload(active.last_result)
            if active.last_result is not None
            else {"status": "ready"}
        )
        latest.value = (
            "<details><summary>Latest normalized RunResult</summary><pre>"
            + html.escape(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str)
            )
            + "</pre></details>"
        )

    def select_route(_change: Any) -> None:
        active.select(
            provider=str(provider_widget.value),
            framework=str(framework_widget.value),
        )
        render()

    def submit(_button: Any) -> None:
        message = prompt_widget.value.strip()
        if not message:
            return
        prompt_widget.value = ""
        send_widget.disabled = True
        status.value = "<small>Running deterministic and reasoning boundaries…</small>"
        try:
            active.run(message)
        except Exception as exc:
            render()
            status.value = (
                "<small>Execution failed without provider fallback: "
                f"{html.escape(type(exc).__name__)}</small>"
            )
        else:
            render()
        finally:
            send_widget.disabled = False

    def clear(_button: Any) -> None:
        active.clear()
        render()

    provider_widget.observe(select_route, names="value")
    framework_widget.observe(select_route, names="value")
    send_widget.on_click(submit)
    clear_widget.on_click(clear)

    root = widgets.VBox(
        [
            widgets.HTML(
                "<h2>Agentic Systems Studio</h2>"
                "<p>Notebook-native presentation; the same conversational System, "
                "RunResult, lineage and usage contracts remain in force.</p>"
            ),
            widgets.HBox([provider_widget, framework_widget]),
            transcript,
            widgets.HBox([prompt_widget, send_widget, clear_widget]),
            status,
            latest,
        ],
        layout=widgets.Layout(width="100%"),
    )
    view = NotebookStudioView(
        session=active,
        root=root,
        provider=provider_widget,
        framework=framework_widget,
        prompt=prompt_widget,
        send=send_widget,
        clear=clear_widget,
        transcript=transcript,
        status=status,
        latest=latest,
    )
    render()
    display(root)
    return view


__all__ = [
    "NotebookStudioSession",
    "NotebookStudioView",
    "display_notebook_studio",
]
