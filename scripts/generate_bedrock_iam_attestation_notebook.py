"""Generate the exact-wheel Bedrock IAM attestation notebook for SageMaker."""

from __future__ import annotations

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "release" / "notebooks" / "bedrock_iam_attestation.ipynb"


def build_notebook() -> nbformat.NotebookNode:
    notebook = nbformat.v4.new_notebook(
        metadata={
            "agentic_systems": {
                "execution_mode": "live-dotenv",
                "frameworks": [
                    "native",
                    "langgraph",
                    "openai-agents",
                    "strands",
                ],
                "provider": "bedrock-runtime",
                "target": "sagemaker-jupyterlab",
                "candidate_identity_source": ".env",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10"},
        }
    )
    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            """# Bedrock attestation - SageMaker JupyterLab

Objetivo: certificar el wheel exacto de Agentic Systems 2.1.1 con el modo de
autenticación que seleccione .env y sin fallback. En SageMaker, un bearer vacío
delega en la cadena normal de boto3 y hereda el execution role del JupyterLab
space; un bearer con valor selecciona la API key nativa de Bedrock.

Evidencia exigida: un RunResult sencillo y cuatro casos live para native,
LangGraph, OpenAI Agents y Strands, todos con engine bedrock-runtime."""
        ),
        nbformat.v4.new_markdown_cell(
            """## Parámetros

| Variable | Default | Propósito |
|---|---|---|
| RUN_BEDROCK_LIVE | 1 | Usa 0 para revisar el notebook sin invocar Bedrock. |
| AGENTIC_SYSTEMS_WHEEL | búsqueda local | Ruta al wheel subido a SageMaker. |
| AWS_REGION | us-east-2 | Endpoint regional de Bedrock. |
| BEDROCK_MODEL_ID | us.amazon.nova-pro-v1:0 | Modelo o inference profile ya habilitado. |
| BEDROCK_STREAMING | 0 | Usa Converse; 1 opta por ConverseStream y requiere su permiso IAM. |
| AGENTIC_SYSTEMS_COMMIT_SHA | candidato 2.1.1 | Commit que produjo el wheel. |
| AGENTIC_SYSTEMS_WHEEL_SHA256 | candidato 2.1.1 | Hash del wheel esperado. |

Sube el wheel al mismo directorio del notebook o define AGENTIC_SYSTEMS_WHEEL.
El .env es el selector único: configura ahí RUN_BEDROCK_LIVE, región y modelo.
Deja AWS_BEARER_TOKEN_BEDROCK vacío para heredar IAM mediante boto3 o dale un
valor para probar la ruta de API key. El notebook nunca modifica esa elección."""
        ),
        nbformat.v4.new_code_cell(
            """import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def load_canonical_dotenv(start: Path) -> Path | None:
    # Load the nearest .env before resolving wheel identity or authentication.
    for directory in (start.resolve(), *start.resolve().parents):
        candidate = directory / ".env"
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                os.environ[key] = value.strip().strip('"').strip("'")
        return candidate
    return None


DOTENV_PATH = load_canonical_dotenv(Path.cwd())

COMMIT_SHA = os.getenv("AGENTIC_SYSTEMS_COMMIT_SHA", "").strip()
EXPECTED_WHEEL_FILENAME = os.getenv(
    "AGENTIC_SYSTEMS_WHEEL_FILENAME", ""
).strip()
EXPECTED_WHEEL_SHA256 = os.getenv(
    "AGENTIC_SYSTEMS_WHEEL_SHA256", ""
).strip().lower()
assert len(COMMIT_SHA) == 40, "Define AGENTIC_SYSTEMS_COMMIT_SHA en .env"
assert EXPECTED_WHEEL_FILENAME.endswith(".whl"), (
    "Define AGENTIC_SYSTEMS_WHEEL_FILENAME en .env"
)
assert len(EXPECTED_WHEEL_SHA256) == 64, (
    "Define AGENTIC_SYSTEMS_WHEEL_SHA256 en .env"
)

configured_wheel = os.getenv("AGENTIC_SYSTEMS_WHEEL")
search_roots = [Path.cwd(), *list(Path.cwd().parents)[:3], Path.home()]
wheel_candidates = (
    [Path(configured_wheel).expanduser()]
    if configured_wheel
    else [
        path
        for root in search_roots
        for path in (
            root / EXPECTED_WHEEL_FILENAME,
            root / "dist" / EXPECTED_WHEEL_FILENAME,
        )
        if path.is_file()
    ]
)
wheel_candidates = list(dict.fromkeys(path.resolve() for path in wheel_candidates))
assert len(wheel_candidates) <= 1, (
    "Define AGENTIC_SYSTEMS_WHEEL cuando exista más de un candidato",
    [str(path) for path in wheel_candidates],
)

if not wheel_candidates:
    raise FileNotFoundError(
        f"Falta el wheel exacto {EXPECTED_WHEEL_FILENAME}. "
        "al mismo directorio, reinicia el kernel y ejecuta Run All."
    )

WHEEL_PATH = wheel_candidates[0]
wheel_sha256 = hashlib.sha256(WHEEL_PATH.read_bytes()).hexdigest()
assert WHEEL_PATH.name == EXPECTED_WHEEL_FILENAME
assert wheel_sha256 == EXPECTED_WHEEL_SHA256, (
    wheel_sha256,
    EXPECTED_WHEEL_SHA256,
)
subprocess.run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "-q",
    "--force-reinstall",
    "--no-deps",
    str(WHEEL_PATH),
], check=True)
subprocess.run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "-q",
    "boto3>=1.39",
    "botocore>=1.39",
    "openai>=2.45,<3",
    "openai-agents>=0.18.3,<0.19",
    "langgraph>=0.2",
    "strands-agents>=1.29,<2",
    "mcp>=1,<2",
], check=True)

loaded_package = sys.modules.get("agentic_systems")
if loaded_package is not None and getattr(loaded_package, "__version__", None) != "2.1.1":
    raise RuntimeError(
        "El kernel conserva agentic_systems "
        f"{getattr(loaded_package, '__version__', 'desconocido')} en memoria. "
        "El wheel 2.1.1 ya se instaló: reinicia el kernel y ejecuta Run All."
    )"""
        ),
        nbformat.v4.new_code_cell(
            """import boto3
import agentic_systems as toolkit

required_api = ("aws_environment_snapshot", "boto3_session_snapshot")
missing_api = [name for name in required_api if not hasattr(toolkit, name)]
if toolkit.__version__ != "2.1.1" or missing_api:
    raise RuntimeError(
        "Se importó un paquete distinto al wheel candidato. "
        f"version={toolkit.__version__!r}, file={toolkit.__file__!r}, "
        f"missing_api={missing_api!r}. Reinicia el kernel y ejecuta Run All."
    )

# This public snapshot loads the nearest .env. The notebook never mutates auth.
aws_environment = toolkit.aws_environment_snapshot()
RUN_BEDROCK_LIVE = os.getenv("RUN_BEDROCK_LIVE", "1").strip().lower() in {"1", "true", "yes"}
REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-2"
MODEL = os.getenv("BEDROCK_MODEL_ID") or "us.amazon.nova-pro-v1:0"
aws_session = toolkit.boto3_session_snapshot(region_name=REGION)
identity = {"available": False, "status": "not-run"}

assert toolkit.__version__ == "2.1.1"
if RUN_BEDROCK_LIVE:
    assert WHEEL_PATH is not None, (
        "Sube el wheel exacto o configura AGENTIC_SYSTEMS_WHEEL antes de certificar live."
    )
    assert aws_session["has_credentials"], aws_session
    if (
        aws_session["authentication_mode"] == "aws-credential-chain"
        and aws_session.get("credential_method") == "env"
        and os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and not os.getenv("AWS_SESSION_TOKEN")
    ):
        raise RuntimeError(
            "El .env contiene credenciales AWS incompletas que ocultan el execution role. "
            "Corrige el .env; el notebook no mutará la configuración."
        )

    if aws_session["authentication_mode"] == "aws-credential-chain":
        try:
            raw_identity = boto3.client("sts", region_name=REGION).get_caller_identity()
            identity = toolkit.mask_sensitive({
                "account": raw_identity.get("Account"),
                "arn": raw_identity.get("Arn"),
                "user_id": raw_identity.get("UserId"),
            })
        except Exception as exc:
            identity = {
                "available": False,
                "error_type": type(exc).__name__,
                "note": "STS is diagnostic; the Bedrock Converse call remains the live gate.",
            }
    else:
        identity = {
            "available": False,
            "status": "not-applicable",
            "note": "Bedrock API-key mode does not use STS identity.",
        }

toolkit.show_json({
    "package": toolkit.__version__,
    "commit_sha": COMMIT_SHA,
    "wheel_sha256": wheel_sha256,
    "region": REGION,
    "model": MODEL,
    "environment": aws_environment,
    "session": aws_session,
    "identity": identity,
}, title="Bedrock authentication preflight")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 1) Smoke Bedrock por la API pública

Esta ejecución reproduce el tutorial de provider: Tool determinista, Agent,
System y RunResult. La Tool no conoce boto3; IAM pertenece al provider."""
        ),
        nbformat.v4.new_code_cell(
            """@toolkit.tool
def inspect_public_api(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "is_public": symbol in toolkit.__all__,
        "package_version": toolkit.__version__,
    }

runtime = toolkit.runtime(
    provider="bedrock-runtime",
    model=MODEL,
    region=REGION,
    scheduler=toolkit.scheduler(
        timeout_s=90,
        max_retries=1,
        max_tool_calls=1,
        max_turns=3,
    ),
    metadata={"attestation": "bedrock-dotenv-sagemaker"},
)
system = toolkit.system(runtime=runtime)
agent = system.agent(
    name="bedrock_auth_probe",
    instructions=(
        "Usa inspect_public_api para comprobar el símbolo system y responde brevemente."
    ),
    tools=[inspect_public_api],
    contract=toolkit.AgentContract(
        must_call=["inspect_public_api"],
        completion="when_required_tools_satisfied",
    ),
    policy=toolkit.RunPolicy(
        max_turns=3,
        max_tool_calls=1,
        temperature=0.0,
        strict=True,
    ),
)

if RUN_BEDROCK_LIVE:
    result = agent.run("Verifica si system pertenece a la API pública.", mode="eval")
    assert isinstance(result, toolkit.RunResult)
    assert result.ok, result.errors
    assert result.engine == "bedrock-runtime"
    assert not result.meta.get("fallback_provider")
    result.check_invariants().raise_if_failed()
    toolkit.human_result(result, title="Bedrock RunResult", show_lineage=True)
else:
    result = None
    toolkit.show_json(
        {"status": "not-run", "provider": "bedrock-runtime"},
        title="Bedrock IAM live gate",
    )"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 2) Matriz Bedrock × cuatro frameworks

El runner oficial conserva provider, modelo, prompt contractual, errores
normalizados y round-trip de RunResult. Sólo cambia el framework."""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_BEDROCK_LIVE:
    runner_path = Path.cwd() / "run_live_matrix.py"
    validator_path = Path.cwd() / "validate_live_attestation.py"
    assert runner_path.is_file(), runner_path
    assert validator_path.is_file(), validator_path

    OUTPUT = Path.cwd() / "bedrock-attestation.json"
    completed = subprocess.run([
        sys.executable,
        str(runner_path),
        "--wheel",
        str(WHEEL_PATH),
        "--output",
        str(OUTPUT),
        "--commit",
        COMMIT_SHA,
        "--providers",
        "bedrock-runtime",
        "--frameworks",
        "native",
        "langgraph",
        "openai-agents",
        "strands",
    ], text=True, capture_output=True)
    toolkit.show_json({
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }, title="Bedrock IAM live matrix")
    if completed.returncode:
        raise RuntimeError(f"La matriz live falló con código {completed.returncode}")

    attestation = json.loads(OUTPUT.read_text(encoding="utf-8"))
    attestation["environment"].update({
        "bedrock_authentication_mode": aws_session["authentication_mode"],
        "bedrock_credential_method": aws_session["credential_method"],
        "aws_region": REGION,
        "aws_identity": identity,
        "uses_aws_credential_chain": aws_session["authentication_mode"] == "aws-credential-chain",
    })
    OUTPUT.write_text(json.dumps(attestation, indent=2), encoding="utf-8")

    failed_cases = [case for case in attestation["cases"] if not case["ok"]]
    observed_pairs = {
        (case["provider"], case["framework"]) for case in attestation["cases"]
    }
    expected_pairs = {
        ("bedrock-runtime", framework)
        for framework in ("native", "langgraph", "openai-agents", "strands")
    }
    assert observed_pairs == expected_pairs
    assert not failed_cases, failed_cases
    assert attestation["wheel_sha256"] == EXPECTED_WHEEL_SHA256
    assert attestation["commit_sha"] == COMMIT_SHA
    assert attestation["environment"]["bedrock_authentication_mode"] == aws_session["authentication_mode"]
    assert all(case["model"] for case in attestation["cases"])

    validation = subprocess.run([
        sys.executable,
        str(validator_path),
        str(OUTPUT),
        "--commit",
        COMMIT_SHA,
        "--wheel-sha256",
        EXPECTED_WHEEL_SHA256,
        "--provider",
        "bedrock-runtime",
    ], text=True, capture_output=True)
    toolkit.show_json({
        "returncode": validation.returncode,
        "stdout": validation.stdout,
        "stderr": validation.stderr,
        "artifact": str(OUTPUT.resolve()),
    }, title="Bedrock IAM attestation validation")
    assert validation.returncode == 0, validation.stderr

    from IPython.display import FileLink, display

    display(FileLink(str(OUTPUT)))
else:
    toolkit.show_json(
        {"status": "not-run", "scope": "bedrock-attestation"},
        title="Attestation gate",
    )"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Aceptación

La prueba Bedrock termina cuando el smoke y las cuatro combinaciones pasan, el
hash y commit coinciden y el provider observado es bedrock-runtime. La evidencia
registra el modo elegido por .env y no contiene secretos ni permite fallback.
Para que también certifique IAM, bedrock_authentication_mode debe ser
aws-credential-chain; una ejecución bedrock-api-key sigue siendo evidencia live
válida de esa ruta, pero no se etiqueta como IAM."""
        ),
    ]
    for index, cell in enumerate(notebook.cells):
        cell["id"] = f"bedrock-iam-{index:02d}"
    return notebook


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(build_notebook(), OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
