from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import urllib.error

from pydantic import SecretStr, ValidationError
import pytest

import agentic_systems as toolkit
from agentic_systems.protocols import ModelServer
from agentic_systems.schemas.serving import ModelArtifact, VLLMServerSpec
from agentic_systems.serving import vllm as serving_vllm
from agentic_systems.serving.vllm import VLLMServer, VLLMServerError, vllm_server_spec


class _Response:
    def __init__(self, model: str) -> None:
        self.model = model

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({"data": [{"id": self.model}]}).encode()


class _Opener:
    def __init__(self, model: str, *, failures: int = 0) -> None:
        self.model = model
        self.failures = failures

    def open(self, request: object, timeout: float) -> _Response:
        if self.failures:
            self.failures -= 1
            raise urllib.error.URLError("starting")
        return _Response(self.model)


class _Process:
    pid = 1234

    def __init__(self, *, returncode: int | None = None) -> None:
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: float) -> int:
        return int(self.returncode or 0)


def test_serving_specs_are_closed_versioned_and_secret_safe() -> None:
    artifact = toolkit.model_artifact(
        "adapter/model",
        base_model="Qwen/Qwen3-0.6B",
        adapter_path="adapter",
        tokenizer="tokenizer",
        quantization="merged_16bit",
    )
    assert artifact.base_model_id == "Qwen/Qwen3-0.6B"
    with pytest.raises(ValidationError):
        ModelArtifact(model_id="m", unknown=True)

    spec = vllm_server_spec(artifact, api_key="secret")
    dumped = spec.model_dump_json()
    assert "secret" not in dumped
    assert spec.schema_version == "agentic_systems.serving.v1"
    with pytest.raises(ValidationError):
        VLLMServerSpec(artifact=artifact, port=0)


def test_profiles_and_command_are_deterministic() -> None:
    server = toolkit.model_server(
        "unsloth/Qwen3-0.6B",
        profile="fast",
        reasoning_parser="qwen3",
    )
    assert isinstance(server, ModelServer)
    assert server.spec.gpu_memory_utilization == 0.4
    assert "--enable-auto-tool-choice" in server.command
    assert server.command[-4:] == (
        "--reasoning-parser",
        "qwen3",
        "--generation-config",
        "vllm",
    )

    custom = vllm_server_spec(
        "m",
        profile="custom",
        gpu_memory_utilization=0.7,
        max_model_len=1024,
        max_num_seqs=2,
    )
    assert custom.profile == "custom"
    with pytest.raises(ValueError, match="Unknown vLLM profile"):
        vllm_server_spec("m", profile="missing")
    with pytest.raises(ValueError, match="requires tool_call_parser"):
        VLLMServer(vllm_server_spec("m", tool_call_parser=None)).command


def test_factory_rejects_ambiguous_or_unknown_configuration() -> None:
    spec = vllm_server_spec("m")
    assert toolkit.model_server(spec=spec).spec is spec
    with pytest.raises(ValueError, match="cannot be combined"):
        toolkit.model_server("m", spec=spec)
    with pytest.raises(ValueError, match="requires model"):
        toolkit.model_server()
    with pytest.raises(ValueError, match="Unknown model-server backend"):
        toolkit.model_server("m", backend="missing")


def test_health_and_runtime_bind_explicit_endpoint_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = toolkit.model_server("served", api_key="private")
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("served"),
    )
    health = server.health()
    assert health.status == "healthy"
    assert health.endpoint.owned is False

    runtime = server.runtime(metadata={"purpose": "test"})
    assert runtime.endpoint == "http://127.0.0.1:8000/v1"
    assert runtime.describe()["endpoint"] == runtime.endpoint
    assert runtime.describe()["api_key_configured"] is True
    assert isinstance(runtime.api_key, SecretStr)
    assert "private" not in json.dumps(runtime.to_dict())
    assert runtime.metadata["purpose"] == "test"


def test_start_waits_for_health_and_stops_only_owned_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _Process()
    opener = _Opener("served", failures=1)
    monkeypatch.setattr(serving_vllm.shutil, "which", lambda value: value)
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: opener,
    )
    server = VLLMServer(
        vllm_server_spec("served", log_path=str(tmp_path / "server.log")),
        popen_factory=lambda *args, **kwargs: process,  # type: ignore[arg-type]
        sleeper=lambda seconds: None,
    )

    endpoint = server.start()
    assert endpoint.owned is True
    assert endpoint.pid == 1234
    server.stop()
    assert process.terminated is True
    assert server.endpoint.owned is False


def test_start_reports_process_failure_and_log_tail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _Process(returncode=1)
    log_path = tmp_path / "server.log"
    monkeypatch.setattr(serving_vllm.shutil, "which", lambda value: value)
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("served", failures=10),
    )

    def popen(*args: Any, **kwargs: Any) -> _Process:
        stream = kwargs["stdout"]
        stream.write("CUDA mismatch")
        stream.flush()
        return process

    server = VLLMServer(
        vllm_server_spec("served", log_path=str(log_path)),
        popen_factory=popen,  # type: ignore[arg-type]
        sleeper=lambda seconds: None,
    )
    with pytest.raises(VLLMServerError, match="CUDA mismatch"):
        server.start()


def test_missing_binary_fails_before_process_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(serving_vllm.shutil, "which", lambda value: None)
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("missing", failures=10),
    )
    with pytest.raises(ImportError, match="vllm-server"):
        toolkit.model_server("missing").start()


class _TimeoutProcess(_Process):
    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float) -> int:
        if not self.killed:
            raise serving_vllm.subprocess.TimeoutExpired("vllm", timeout)
        return -9


def test_serving_schema_rejects_unknown_version() -> None:
    current = ModelArtifact(model_id="m", schema_version="agentic_systems.serving.v1")
    assert current.schema_version == "agentic_systems.serving.v1"
    with pytest.raises(ValidationError, match="Unsupported serving schema"):
        ModelArtifact(model_id="m", schema_version="legacy")


def test_start_reuses_healthy_external_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("served"),
    )
    server = toolkit.model_server("served")

    endpoint = server.start()

    assert endpoint.owned is False
    assert endpoint.pid is None


def test_health_reports_failed_process_wrong_model_and_missing_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = toolkit.model_server("served", log_path="missing-vllm-test.log")
    server._process = _Process(returncode=1)
    assert server.health().status == "failed"
    assert server.health().detail == ""

    server._process = None
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("different"),
    )
    health = server.health()
    assert health.status == "failed"
    assert "do not include 'served'" in health.detail


def test_start_timeout_stops_owned_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _Process()
    times = iter((0.0, 0.0, 2.0))
    monkeypatch.setattr(serving_vllm.shutil, "which", lambda value: value)
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("served", failures=10),
    )
    server = VLLMServer(
        vllm_server_spec(
            "served",
            startup_timeout_s=1,
            log_path=str(tmp_path / "timeout.log"),
        ),
        popen_factory=lambda *args, **kwargs: process,  # type: ignore[arg-type]
        sleeper=lambda seconds: None,
        clock=lambda: next(times),
    )

    with pytest.raises(VLLMServerError, match="did not become healthy"):
        server.start()

    assert process.terminated is True


def test_stop_kills_process_that_ignores_terminate(tmp_path: Path) -> None:
    process = _TimeoutProcess()
    server = VLLMServer(vllm_server_spec("served", log_path=str(tmp_path / "kill.log")))
    server._process = process
    server._owned = True

    server.stop()

    assert process.terminated is True
    assert process.killed is True


def test_context_managers_delegate_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        serving_vllm.urllib.request,
        "build_opener",
        lambda *args: _Opener("served"),
    )
    server = toolkit.model_server("served")

    with server.running() as endpoint:
        assert endpoint.model_id == "served"
    with server as bound:
        assert bound is server
