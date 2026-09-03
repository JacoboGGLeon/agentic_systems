"""Shared Streamlit launcher for the Studio CLI and notebooks."""

from __future__ import annotations

import errno
import html
import os
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
DEFAULT_PROXY_PREFIX = "/jupyterlab/default/proxy"
StudioTransport = Literal["auto", "colab-proxy", "jupyter-proxy", "local"]


@dataclass(slots=True)
class StudioServer:
    process: subprocess.Popen
    app_path: Path
    log_path: Path
    pid_path: Path
    host: str
    port: int

    @property
    def local_url(self) -> str:
        browser_host = (
            "localhost" if self.host in {"127.0.0.1", "0.0.0.0", "::"} else self.host
        )
        return f"http://{browser_host}:{self.port}/"

    def stop(self, *, timeout_s: float = 5.0) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout_s)
        if self.pid_path.exists():
            recorded = self.pid_path.read_text(encoding="utf-8").strip()
            if recorded == str(self.process.pid):
                self.pid_path.unlink()


@dataclass(slots=True)
class StudioPresentation:
    """A running Studio plus the host transport used to present it."""

    server: StudioServer
    transport: str
    local_url: str
    proxy_url: str | None = None
    display_result: Any | None = None

    @property
    def url(self) -> str:
        return self.proxy_url or self.local_url


def resolve_studio_app(app_path: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if app_path is not None:
        candidates.append(Path(app_path))
    configured = os.getenv("AGENTIC_STUDIO_APP")
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path(__file__).resolve().parents[2] / "app.py",
            Path.cwd() / "examples" / "agentic_systems_studio" / "app.py",
            Path.cwd() / "app.py",
        ]
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.is_file():
            return resolved
    rendered = os.linesep.join(f"- {candidate}" for candidate in candidates)
    raise FileNotFoundError(
        "Could not locate the Agentic Systems Studio Streamlit app. "
        "Pass --app or set AGENTIC_STUDIO_APP. Checked:" + os.linesep + rendered
    )


def streamlit_command(
    app_path: str | Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        Path(app_path).name,
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--server.fileWatcherType",
        "none",
    ]


def wait_for_studio(
    process: subprocess.Popen,
    *,
    port: int,
    timeout_s: float = 60.0,
) -> tuple[bool, str]:
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False, f"Streamlit exited with code {process.returncode}."
        try:
            with urllib.request.urlopen(health_url, timeout=2.0) as response:
                return True, response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    return False, repr(last_error)


def stop_recorded_studio(pid_path: Path) -> None:
    if not pid_path.exists():
        return
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, ValueError):
        pass
    except OSError as exc:
        if exc.errno != errno.ESRCH and getattr(exc, "winerror", None) != 87:
            raise
    finally:
        pid_path.unlink(missing_ok=True)


def start_studio_server(
    *,
    app_path: str | Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_dir: str | Path | None = None,
    timeout_s: float = 60.0,
    stop_previous: bool = True,
) -> StudioServer:
    app = resolve_studio_app(app_path)
    logs = Path(log_dir).resolve() if log_dir is not None else app.parent / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    pid_path = logs / "streamlit.pid"
    log_path = logs / "streamlit.log"
    if stop_previous:
        stop_recorded_studio(pid_path)

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            streamlit_command(app, host=host, port=port),
            cwd=str(app.parent),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
    pid_path.write_text(str(process.pid), encoding="utf-8")
    ready, detail = wait_for_studio(process, port=port, timeout_s=timeout_s)
    if not ready:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
        handle = StudioServer(process, app, log_path, pid_path, host, port)
        handle.stop()
        raise RuntimeError("Studio did not become ready: " + detail + os.linesep + tail)
    return StudioServer(process, app, log_path, pid_path, host, port)


def studio_proxy_url(port: int = DEFAULT_PORT, *, prefix: str | None = None) -> str:
    selected = prefix or os.getenv("AGENTIC_STUDIO_PROXY_PREFIX")
    if not selected:
        service_prefix = os.getenv("JUPYTERHUB_SERVICE_PREFIX")
        selected = (
            f"{service_prefix.rstrip('/')}/proxy"
            if service_prefix
            else DEFAULT_PROXY_PREFIX
        )
    if "{port}" in selected:
        return selected.format(port=port)
    return f"{selected.rstrip('/')}/{port}/"


def studio_button_html(
    url: str,
    *,
    label: str = "Open Agentic Systems Studio",
    alternate_url: str | None = None,
    alternate_label: str = "Open through Jupyter proxy",
) -> str:
    def render_link(target: str, text: str, *, secondary: bool = False) -> str:
        safe_url = html.escape(target, quote=True)
        safe_label = html.escape(text)
        background = "#6c757d" if secondary else "#ff4b4b"
        return (
            f"<a href='{safe_url}' target='_blank' rel='noopener noreferrer' "
            "style='display:inline-block;padding:11px 18px;border-radius:9px;"
            f"background:{background};color:white;text-decoration:none;"
            "font-weight:700;margin-right:10px;margin-bottom:6px'>"
            f"{safe_label}</a>"
        )

    links = render_link(url, label)
    if alternate_url and alternate_url != url:
        links += render_link(alternate_url, alternate_label, secondary=True)
    return (
        "<div style='padding:18px 20px;border:1px solid rgba(128,128,128,.28);"
        "border-radius:14px;margin-top:12px'>"
        "<h3 style='margin:0 0 12px 0'>Agentic Systems Studio is ready</h3>"
        f"{links}</div>"
    )


def _colab_output() -> Any | None:
    """Return Colab's public notebook-output module on a Colab host."""

    try:
        from google.colab import output as colab_output
    except ImportError:
        return None
    return colab_output


def resolve_colab_proxy_url(port: int) -> str:
    """Resolve the authenticated Colab URL for a kernel port."""

    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    colab_output = _colab_output()
    if colab_output is None:
        raise RuntimeError("The colab-proxy transport requires google.colab.output.")
    resolved = colab_output.eval_js(f"google.colab.kernel.proxyPort({port})")
    if not isinstance(resolved, str) or not resolved.startswith(
        ("https://", "http://")
    ):
        raise RuntimeError("Colab did not return a valid kernel-port proxy URL.")
    return resolved.rstrip("/") + "/"


def _display_html(payload: str) -> Any:
    from IPython.display import HTML, display

    return display(HTML(payload))


def present_studio_server(
    server: StudioServer,
    *,
    transport: StudioTransport = "auto",
    proxy_prefix: str | None = None,
    label: str = "Open Agentic Systems Studio",
) -> StudioPresentation:
    """Present one running Streamlit Studio through the current notebook host.

    Provider and framework selection never influence this decision. Auto only
    detects the presentation host: Colab renders a proxied HTML button that opens
    Studio in a new tab, Jupyter/SageMaker exposes the configured proxy URL, and a
    local process exposes the loopback URL. Notebook-native Studio remains a
    separate explicit adapter.
    """

    if transport not in {"auto", "colab-proxy", "jupyter-proxy", "local"}:
        raise ValueError(
            "Unknown Studio transport "
            f"{transport!r}; use auto, colab-proxy, jupyter-proxy or local."
        )

    colab_output = _colab_output()
    selected = transport
    if selected == "auto":
        if colab_output is not None:
            selected = "colab-proxy"
        elif os.getenv("JUPYTERHUB_SERVICE_PREFIX") or os.getenv(
            "AGENTIC_STUDIO_PROXY_PREFIX"
        ):
            selected = "jupyter-proxy"
        else:
            selected = "local"

    if selected == "colab-proxy":
        if colab_output is None:
            raise RuntimeError(
                "The colab-proxy transport requires google.colab.output."
            )
        proxy_url = resolve_colab_proxy_url(server.port)
        displayed = _display_html(
            studio_button_html(
                proxy_url,
                label=label,
            )
        )
        return StudioPresentation(
            server=server,
            transport=selected,
            local_url=server.local_url,
            proxy_url=proxy_url,
            display_result=displayed,
        )

    proxy_url = (
        studio_proxy_url(server.port, prefix=proxy_prefix)
        if selected == "jupyter-proxy"
        else None
    )
    displayed = _display_html(
        studio_button_html(
            proxy_url or server.local_url,
            label=(
                "Open Agentic Systems Studio through Jupyter proxy"
                if proxy_url
                else label
            ),
            alternate_url=(server.local_url if proxy_url else None),
            alternate_label="Open directly on this host",
        )
    )
    return StudioPresentation(
        server=server,
        transport=selected,
        local_url=server.local_url,
        proxy_url=proxy_url,
        display_result=displayed,
    )


def launch_studio(
    *,
    app_path: str | Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_dir: str | Path | None = None,
    timeout_s: float = 60.0,
    stop_previous: bool = True,
    transport: StudioTransport = "auto",
    proxy_prefix: str | None = None,
    label: str = "Open Agentic Systems Studio",
) -> StudioPresentation:
    """Start Streamlit and present it through an explicit host transport."""

    server = start_studio_server(
        app_path=app_path,
        host=host,
        port=port,
        log_dir=log_dir,
        timeout_s=timeout_s,
        stop_previous=stop_previous,
    )
    try:
        return present_studio_server(
            server,
            transport=transport,
            proxy_prefix=proxy_prefix,
            label=label,
        )
    except Exception:
        server.stop()
        raise


def serve_studio(
    *,
    app_path: str | Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_dir: str | Path | None = None,
    proxy_prefix: str | None = None,
    timeout_s: float = 60.0,
    detach: bool = False,
    open_browser: bool = False,
) -> int:
    server = start_studio_server(
        app_path=app_path,
        host=host,
        port=port,
        log_dir=log_dir,
        timeout_s=timeout_s,
    )
    print(f"Studio ready: {server.local_url}")
    print(f"Jupyter proxy: {studio_proxy_url(port, prefix=proxy_prefix)}")
    print(f"PID: {server.process.pid}")
    print(f"Log: {server.log_path}")
    if open_browser:
        webbrowser.open(server.local_url)
    if detach:
        return 0
    try:
        return server.process.wait()
    except KeyboardInterrupt:
        server.stop()
        return 130


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_PROXY_PREFIX",
    "StudioPresentation",
    "StudioServer",
    "StudioTransport",
    "resolve_colab_proxy_url",
    "launch_studio",
    "present_studio_server",
    "resolve_studio_app",
    "serve_studio",
    "start_studio_server",
    "studio_button_html",
    "studio_proxy_url",
    "streamlit_command",
    "wait_for_studio",
]
