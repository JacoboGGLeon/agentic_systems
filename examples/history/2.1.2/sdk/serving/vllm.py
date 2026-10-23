"""Explicit, owned lifecycle for a local vLLM OpenAI-compatible server."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import time
from types import TracebackType
from typing import Any, Callable, Iterator, Literal, cast
import urllib.request

from pydantic import SecretStr

from agentic_systems.core.runtime import RuntimeConfig
from agentic_systems.core.scheduler import SchedulerConfig
from agentic_systems.schemas.serving import (
    EndpointInfo,
    ModelArtifact,
    ServerHealth,
    VLLMServerSpec,
)


_PROFILE_VALUES: dict[str, dict[str, int | float]] = {
    "fast": {
        "gpu_memory_utilization": 0.40,
        "max_model_len": 2048,
        "max_num_seqs": 4,
    },
    "medium": {
        "gpu_memory_utilization": 0.55,
        "max_model_len": 4096,
        "max_num_seqs": 4,
    },
    "power": {
        "gpu_memory_utilization": 0.90,
        "max_model_len": 32768,
        "max_num_seqs": 1,
    },
}


class VLLMServerError(RuntimeError):
    """Raised when a managed vLLM process cannot satisfy its lifecycle contract."""


def vllm_server_spec(
    model: str | ModelArtifact,
    *,
    profile: str = "fast",
    served_model_name: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    tool_call_parser: str | None = "hermes",
    reasoning_parser: str | None = None,
    enable_auto_tool_choice: bool = True,
    api_key: str | SecretStr = "vllm",
    startup_timeout_s: float = 600.0,
    log_path: str = "vllm-server.log",
    binary: str = "vllm",
    extra_args: tuple[str, ...] = (),
    gpu_memory_utilization: float | None = None,
    max_model_len: int | None = None,
    max_num_seqs: int | None = None,
) -> VLLMServerSpec:
    """Create a validated vLLM server declaration from a named profile."""

    normalized_profile = profile.strip().lower()
    if normalized_profile not in {*_PROFILE_VALUES, "custom"}:
        raise ValueError(
            f"Unknown vLLM profile {profile!r}; expected fast, medium, power, or custom."
        )
    defaults = _PROFILE_VALUES.get(normalized_profile, _PROFILE_VALUES["fast"])
    gpu_value = (
        gpu_memory_utilization
        if gpu_memory_utilization is not None
        else float(defaults["gpu_memory_utilization"])
    )
    model_len_value = (
        max_model_len if max_model_len is not None else int(defaults["max_model_len"])
    )
    sequence_value = (
        max_num_seqs if max_num_seqs is not None else int(defaults["max_num_seqs"])
    )
    artifact = (
        model if isinstance(model, ModelArtifact) else ModelArtifact(model_id=model)
    )
    secret = api_key if isinstance(api_key, SecretStr) else SecretStr(api_key)
    return VLLMServerSpec(
        artifact=artifact,
        profile=cast(Literal["fast", "medium", "power", "custom"], normalized_profile),
        served_model_name=served_model_name,
        host=host,
        port=port,
        tool_call_parser=tool_call_parser,
        reasoning_parser=reasoning_parser,
        enable_auto_tool_choice=enable_auto_tool_choice,
        api_key=secret,
        startup_timeout_s=startup_timeout_s,
        log_path=log_path,
        binary=binary,
        extra_args=extra_args,
        gpu_memory_utilization=gpu_value,
        max_model_len=model_len_value,
        max_num_seqs=sequence_value,
    )


class VLLMServer:
    """Own and supervise one explicitly started local vLLM process."""

    def __init__(
        self,
        spec: VLLMServerSpec,
        *,
        popen_factory: Callable[..., subprocess.Popen[Any]] = subprocess.Popen,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.spec = spec
        self._popen_factory = popen_factory
        self._clock = clock
        self._sleeper = sleeper
        self._process: subprocess.Popen[Any] | None = None
        self._log_stream: Any | None = None
        self._owned = False

    @property
    def endpoint(self) -> EndpointInfo:
        model_id = self.spec.served_model_name or self.spec.artifact.model_id
        pid = self._process.pid if self._process is not None else None
        return EndpointInfo(
            backend="vllm",
            base_url=f"http://{self.spec.host}:{self.spec.port}/v1",
            model_id=model_id,
            api_key_configured=bool(self.spec.api_key.get_secret_value()),
            pid=pid,
            owned=self._owned,
        )

    @property
    def command(self) -> tuple[str, ...]:
        binary = shutil.which(self.spec.binary) or self.spec.binary
        command = [
            binary,
            "serve",
            self.spec.artifact.model_id,
            "--host",
            self.spec.host,
            "--port",
            str(self.spec.port),
            "--served-model-name",
            self.endpoint.model_id,
            "--gpu-memory-utilization",
            str(self.spec.gpu_memory_utilization),
            "--max-model-len",
            str(self.spec.max_model_len),
            "--max-num-seqs",
            str(self.spec.max_num_seqs),
        ]
        if self.spec.enable_auto_tool_choice:
            if not self.spec.tool_call_parser:
                raise ValueError(
                    "enable_auto_tool_choice=True requires tool_call_parser."
                )
            command.extend(
                [
                    "--enable-auto-tool-choice",
                    "--tool-call-parser",
                    self.spec.tool_call_parser,
                ]
            )
        if self.spec.reasoning_parser:
            command.extend(["--reasoning-parser", self.spec.reasoning_parser])
        if self.spec.generation_config:
            command.extend(["--generation-config", self.spec.generation_config])
        command.extend(self.spec.extra_args)
        return tuple(command)

    def inspect(self) -> dict[str, Any]:
        """Describe the exact process without starting it."""

        return {
            "backend": "vllm",
            "installed": shutil.which(self.spec.binary) is not None,
            "command": list(self.command),
            "endpoint": self.endpoint.model_dump(mode="json"),
            "spec": self.spec.model_dump(mode="json"),
        }

    def start(self) -> EndpointInfo:
        """Start vLLM or bind to an already healthy external endpoint."""

        current = self.health()
        if current.status == "healthy":
            return current.endpoint
        binary = shutil.which(self.spec.binary)
        if binary is None:
            raise ImportError(
                'vLLM serving requires pip install "agentic-systems[vllm-server]" '
                "or an available vllm executable."
            )
        log_path = Path(self.spec.log_path).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_stream = log_path.open("w", encoding="utf-8")
        command = list(self.command)
        command[0] = binary
        self._process = self._popen_factory(
            command,
            stdout=self._log_stream,
            stderr=subprocess.STDOUT,
        )
        self._owned = True
        deadline = self._clock() + self.spec.startup_timeout_s
        while self._clock() < deadline:
            if self._process.poll() is not None:
                detail = self._log_tail()
                self.stop()
                raise VLLMServerError(
                    "vLLM exited before becoming healthy."
                    + (f"\n{detail}" if detail else "")
                )
            health = self.health()
            if health.status == "healthy":
                return health.endpoint
            self._sleeper(2.0)
        detail = self._log_tail()
        self.stop()
        raise VLLMServerError(
            f"vLLM did not become healthy within {self.spec.startup_timeout_s}s."
            + (f"\n{detail}" if detail else "")
        )

    def health(self) -> ServerHealth:
        """Probe the OpenAI-compatible model inventory without proxy inheritance."""

        endpoint = self.endpoint
        process = self._process
        if process is not None and process.poll() is not None:
            return ServerHealth(
                status="failed", endpoint=endpoint, detail=self._log_tail()
            )
        request = urllib.request.Request(
            endpoint.base_url.rstrip("/") + "/models",
            headers={"Authorization": f"Bearer {self.spec.api_key.get_secret_value()}"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=3.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            models = tuple(
                str(item.get("id"))
                for item in payload.get("data", ())
                if isinstance(item, dict) and item.get("id")
            )
            if endpoint.model_id not in models:
                return ServerHealth(
                    status="failed",
                    endpoint=endpoint,
                    detail=f"Endpoint models {models!r} do not include {endpoint.model_id!r}.",
                )
            return ServerHealth(status="healthy", endpoint=endpoint)
        except Exception as exc:
            status = (
                "starting"
                if process is not None and process.poll() is None
                else "stopped"
            )
            return ServerHealth(
                status=status,
                endpoint=endpoint,
                detail=f"{type(exc).__name__}: {exc}",
            )

    def runtime(
        self,
        *,
        scheduler: SchedulerConfig | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeConfig:
        """Bind this endpoint explicitly to a vLLM RuntimeConfig."""

        return RuntimeConfig(
            provider="vllm-runtime",
            model_id=self.endpoint.model_id,
            endpoint=self.endpoint.base_url,
            api_key=self.spec.api_key,
            scheduler=SchedulerConfig.coerce(scheduler),
            metadata={"managed_server": self.inspect(), **(metadata or {})},
        )

    def stop(self) -> None:
        """Stop only the process owned by this object and close its log."""

        process = self._process
        if self._owned and process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if self._log_stream is not None:
            self._log_stream.close()
        self._process = None
        self._log_stream = None
        self._owned = False

    @contextmanager
    def running(self) -> Iterator[EndpointInfo]:
        endpoint = self.start()
        try:
            yield endpoint
        finally:
            self.stop()

    def __enter__(self) -> "VLLMServer":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    def _log_tail(self, max_chars: int = 8000) -> str:
        path = Path(self.spec.log_path).expanduser()
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[-max_chars:]


__all__ = ["VLLMServer", "VLLMServerError", "vllm_server_spec"]
