from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
VLLM = ROOT / "release" / "notebooks" / "vllm_attestation.ipynb"
BEDROCK_IAM = ROOT / "release" / "notebooks" / "bedrock_iam_attestation.ipynb"
COMMIT = "5865dbc893ef397581fee1a8e9ff58efabce3625"
WHEEL = "agentic_systems-2.1.2-py3-none-any.whl"
BEDROCK_SHA256 = "5a873a4979768a4142d4debd8c1eeb7c4e27a9515892c4cde41607d1bfedfe25"
DOTENV_EXAMPLE = ROOT / ".env.example"
ADA_GUIDE = ROOT / "examples" / "agentic_systems_studio" / "docs" / "ADA.md"


def _load(path: Path):
    return nbformat.read(path, as_version=4)


def _code(path: Path) -> str:
    notebook = _load(path)
    return chr(10).join(
        str(cell.source) for cell in notebook.cells if cell.cell_type == "code"
    )


def test_release_attestation_notebooks_are_clean_and_compilable() -> None:
    for path in (VLLM, BEDROCK_IAM):
        notebook = _load(path)
        assert all(
            cell.execution_count is None
            for cell in notebook.cells
            if cell.cell_type == "code"
        )
        assert all(
            not cell.outputs for cell in notebook.cells if cell.cell_type == "code"
        )
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type != "code":
                continue
            compile(
                str(cell.source),
                f"{path.name}#cell-{index}",
                "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )


def test_vllm_attestation_reads_candidate_identity_from_dotenv() -> None:
    code = _code(VLLM)
    assert COMMIT not in code
    assert WHEEL not in code
    assert 'COMMIT_SHA = os.getenv("AGENTIC_SYSTEMS_COMMIT_SHA", "").strip()' in code
    assert (
        'EXPECTED_WHEEL_FILENAME = os.getenv("AGENTIC_SYSTEMS_WHEEL_FILENAME", "").strip()'
        in code
    )
    assert (
        'EXPECTED_WHEEL_SHA256 = os.getenv("AGENTIC_SYSTEMS_WHEEL_SHA256", "").strip().lower()'
        in code
    )
    assert "assert len(COMMIT_SHA) == 40" in code
    assert "assert len(EXPECTED_WHEEL_SHA256) == 64" in code
    assert 'summary = attestation["summary"]' in code
    assert 'assert summary["total"] == 4' in code
    assert 'assert summary["episodes_total"] == 16' in code
    assert 'assert summary["episodes_failed"] == 0' in code
    assert 'title="Fallas semánticas por episodio"' in code
    assert "files.download(str(OUTPUT))" in code
    assert 'attestation["gate_assets"]["runner"]["sha256"]' in code
    assert '"native", "langgraph", "openai-agents", "strands"' in code
    assert "server.health()" in code
    assert 'result.engine == "vllm-runtime"' in code
    assert 'REQUESTED_PROFILE = os.getenv("VLLM_PROFILE", "fast")' in code
    assert 'tool_choice="multiply"' in code
    assert 'completion="when_required_tools_satisfied"' in code
    assert '"qwen3" if VLLM_ENABLE_THINKING else ""' in code
    assert 'VLLM_ENABLE_THINKING = os.getenv("VLLM_ENABLE_THINKING", "0")' in code
    assert '"--default-chat-template-kwargs"' in code
    assert 'json.dumps({"enable_thinking": VLLM_ENABLE_THINKING})' in code
    assert "temperature=VLLM_TEMPERATURE" in code
    assert 'assert [event.name for event in result.tool_events] == ["multiply"]' in code
    assert 'assert "323" in result.text' in code
    assert 'assert "ToolEnvelope" not in result.text' in code
    assert 'semantic_runner = Path.cwd() / "run_semantic_matrix.py"' in code
    assert 'semantic_application = Path.cwd() / "semantic_e2e_application.py"' in code
    assert 'episode["deterministic_validation"]["ok"]' in code
    assert 'episode["judge"]["ok"]' in code
    assert '"git", "clone"' not in code
    assert "https://github.com" not in code
    assert "VLLM_GPU_MEMORY_UTILIZATION" in code
    assert 'VLLM_MAX_MODEL_LEN = int(os.getenv("VLLM_MAX_MODEL_LEN", "8192"))' in code
    assert '"--force-reinstall", "--no-deps", WHEEL_PATH' in code
    assert "load_canonical_dotenv(Path.cwd())" in code
    assert "os.environ[key] = value.strip()" in code
    assert '"vllm", "torchvision",' in code
    assert '"uninstall", "-y", "torchaudio"' in code
    assert '"uninstall", "-y", "torchaudio", "torchvision"' not in code
    assert "tool_call_parser=VLLM_TOOL_CALL_PARSER" in code
    assert "reasoning_parser=VLLM_REASONING_PARSER" in code
    assert "gpu_memory_gib < 20" in code
    assert "gpu_memory_gib < 60" in code
    assert '"half" if cuda_major < 8 else "bfloat16"' in code
    assert "SERVER_EXTRA_ARGS = (" in code
    assert '"--dtype",' in code
    assert "VLLM_DTYPE," in code
    assert '"log_head": log_text[:24000]' in code
    assert '"diagnostic_lines": diagnostic_lines[-200:]' in code


def test_bedrock_attestation_respects_dotenv_auth_and_runs_full_framework_matrix() -> (
    None
):
    code = _code(BEDROCK_IAM)
    assert COMMIT not in code
    assert WHEEL not in code
    assert BEDROCK_SHA256 not in code
    assert 'COMMIT_SHA = os.getenv("AGENTIC_SYSTEMS_COMMIT_SHA", "").strip()' in code
    assert '"AGENTIC_SYSTEMS_WHEEL_FILENAME", ""' in code
    assert '"AGENTIC_SYSTEMS_WHEEL_SHA256", ""' in code
    assert "assert len(COMMIT_SHA) == 40" in code
    assert "assert len(EXPECTED_WHEEL_SHA256) == 64" in code
    assert "toolkit.aws_environment_snapshot()" in code
    assert "from agentic_systems.utils import mask_sensitive" in code
    assert "toolkit.mask_sensitive" not in code
    assert "boto3.Session(region_name=REGION)" in code
    assert '"diagnostic_stage": "sts:GetCallerIdentity"' in code
    assert '"AWS_STS_IDENTITY_REQUIRED", "1"' in code
    assert 'if STS_IDENTITY_REQUIRED and not identity["available"]' in code
    assert "El .env resolvió otro modo" not in code
    assert 'os.environ["AWS_BEARER_TOKEN_BEDROCK"]' not in code
    assert "toolkit.repair_ada_credential_chain" not in code
    assert "Corrige el .env; el notebook no mutará la configuración." in code
    assert 'result.engine == "bedrock-runtime"' in code
    assert 'not result.meta.get("fallback_provider")' in code
    for framework in ("native", "langgraph", "openai-agents", "strands"):
        assert f'"{framework}"' in code
    assert '"--provider"' in code
    assert '"bedrock-runtime"' in code
    assert (
        'attestation["environment"]["bedrock_authentication_mode"] == aws_session["authentication_mode"]'
        in code
    )
    assert 'runner_path = Path.cwd() / "run_live_matrix.py"' in code
    assert 'validator_path = Path.cwd() / "validate_live_attestation.py"' in code
    assert '"git", "clone"' not in code
    assert "https://github.com" not in code
    assert "FileLink" in code
    assert code.index("if not wheel_candidates:") < code.index(
        "import agentic_systems as toolkit"
    )
    assert '"--force-reinstall"' in code
    assert '"--no-deps"' in code
    assert (
        'required_api = ("aws_environment_snapshot", "boto3_session_snapshot")' in code
    )
    assert "El kernel conserva agentic_systems" in code


def test_bedrock_authentication_is_selected_by_dotenv_without_notebook_mutation() -> (
    None
):
    dotenv = DOTENV_EXAMPLE.read_text(encoding="utf-8")
    ada_docs = ADA_GUIDE.read_text(encoding="utf-8")
    assert "AWS_BEARER_TOKEN_BEDROCK=" in dotenv
    assert "AWS_BEARER_TOKEN_BEDROCK=your_" not in dotenv
    assert "boto3 automatically uses" in ada_docs
    assert "execution-role credential chain" in ada_docs
    assert "never mutate the authentication route" in ada_docs


def test_live_runner_discovers_gpu_cuda_and_vllm_without_env_hardcoding(
    monkeypatch,
) -> None:
    import sys
    from types import SimpleNamespace

    import scripts.run_live_matrix as runner

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def get_device_name(index: int) -> str:
            assert index == 0
            return "NVIDIA Test GPU"

    fake_torch = SimpleNamespace(version=SimpleNamespace(cuda="12.8"), cuda=FakeCuda())
    for variable in ("CUDA_VERSION", "GPU_NAME", "VLLM_VERSION"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setattr(runner.metadata, "version", lambda name: "0.27.1")

    assert runner._live_environment() == {
        "platform": runner.platform.platform(),
        "cuda": "12.8",
        "gpu": "NVIDIA Test GPU",
        "vllm": "0.27.1",
    }


def test_live_runner_treats_torch_as_optional_environment_evidence(monkeypatch) -> None:
    import scripts.run_live_matrix as runner

    def missing_optional_module(name: str):
        raise ModuleNotFoundError(name=name)

    for variable in ("CUDA_VERSION", "GPU_NAME", "VLLM_VERSION"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(runner, "import_module", missing_optional_module)
    monkeypatch.setattr(runner.metadata, "version", lambda name: "0.27.1")

    assert runner._live_environment() == {
        "platform": runner.platform.platform(),
        "cuda": None,
        "gpu": None,
        "vllm": "0.27.1",
    }
