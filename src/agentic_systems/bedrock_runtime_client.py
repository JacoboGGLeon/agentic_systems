"""Small public Bedrock Runtime primitive layer.

This module intentionally contains no agents and no tools. It is the lowest
user-facing layer for sandbox checks, one-shot completions, markdown Q&A, and
embeddings. Higher layers (Agent, System, Environment, Evals, Skills) build on
this foundation instead of hiding Bedrock behind a demo-specific notebook cell.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Sequence

from .engines.names import BEDROCK_RUNTIME_ENGINE
from .results import RunResult

DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"


class BedrockRuntimeClient:
    """Primitive Bedrock Runtime client for non-agent workflows.

    Parameters
    ----------
    model:
        Language model id used for ``complete``.
    region:
        AWS region. If omitted, boto3/AWS defaults are used.
    embedding_model:
        Bedrock embedding model id used by ``embed``. The default is conservative
        and region-dependent; callers can pass their approved enterprise model.
    defaults:
        Optional runtime defaults such as ``max_tokens`` and ``temperature``.
    """

    def __init__(
        self,
        *,
        model: str,
        region: str | None = None,
        embedding_model: str | None = DEFAULT_EMBEDDING_MODEL_ID,
        defaults: dict[str, Any] | None = None,
        disable_framework_tracing: bool = True,
    ) -> None:
        self.model = model
        self.embedding_model = embedding_model
        self.defaults = dict(defaults or {})
        BedrockRuntime = _import_bedrock_runtime()
        self._runtime = BedrockRuntime(
            model_id=model,
            region_name=region,
            max_tokens_default=int(self.defaults.get("max_tokens", 800)),
            temperature_default=float(self.defaults.get("temperature", 0.0)),
            disable_openai_runtime_tracing=disable_framework_tracing,
        )
        self.region = self._runtime.region_name

    @property
    def runtime(self) -> Any:
        """Return the internal Bedrock runtime object for advanced integrations."""

        return self._runtime

    def profile(self) -> dict[str, Any]:
        """Return non-secret runtime configuration."""

        return {
            "engine": BEDROCK_RUNTIME_ENGINE,
            "region": self.region,
            "language_model": self.model,
            "embedding_model": self.embedding_model,
            "defaults": dict(self.defaults),
        }

    def whoami(
        self,
        *,
        mask: bool = True,
        check_language_model: bool = False,
        check_embedding_model: bool = False,
    ) -> dict[str, Any]:
        """Return AWS identity plus selected language/embedding models.

        Model checks are optional because some execution roles can invoke models
        while being denied Bedrock management metadata APIs.
        """

        output: dict[str, Any] = {
            "ok": True,
            "profile": self.profile(),
        }
        try:
            output["identity"] = self._runtime.whoami(mask=mask)
        except Exception as exc:  # noqa: BLE001 - diagnostics should not crash notebooks.
            output["ok"] = False
            output["identity"] = {
                "ok": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        if check_language_model:
            try:
                output["language_model_availability"] = self._runtime.model_availability(
                    self.model,
                    full_metadata=False,
                )
            except Exception as exc:  # noqa: BLE001 - optional metadata call.
                output["language_model_availability"] = {"ok": False, "error_type": type(exc).__name__, "message": str(exc)}
        if check_embedding_model and self.embedding_model:
            try:
                output["embedding_model_availability"] = self._runtime.model_availability(
                    self.embedding_model,
                    full_metadata=False,
                )
            except Exception as exc:  # noqa: BLE001 - optional metadata call.
                output["embedding_model_availability"] = {"ok": False, "error_type": type(exc).__name__, "message": str(exc)}
        return output

    def complete(
        self,
        prompt: str,
        *,
        instructions: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        mode: str = "default",
        data: dict[str, Any] | None = None,
    ) -> RunResult:
        """Run a one-shot language completion without agents or tools."""

        runtime_result = self._runtime.run_direct(
            str(prompt or ""),
            instructions=str(instructions or ""),
            model_id=model or self.model,
            tool_names=None,
            max_turns=1,
            max_tool_calls=0,
            max_tokens=max_tokens,
            temperature=temperature,
            retry_tool_errors=False,
            synthesize_final_on_max_turns=False,
        )
        return RunResult.from_bedrock_runtime(
            runtime_result,
            engine=BEDROCK_RUNTIME_ENGINE,
            model=model or self.model,
            mode=mode,
            data=data or {"kind": "completion"},
        )

    def read_markdown(self, path: str | Path, *, encoding: str = "utf-8") -> dict[str, Any]:
        """Read a Markdown file as a primitive chain input."""

        markdown_path = Path(path).expanduser().resolve()
        content = markdown_path.read_text(encoding=encoding)
        return {
            "path": str(markdown_path),
            "content": content,
            "chars": len(content),
            "lines": content.count("\n") + 1 if content else 0,
        }

    def answer_from_markdown(
        self,
        *,
        path: str | Path,
        question: str,
        instructions: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        mode: str = "default",
    ) -> RunResult:
        """Read a Markdown file and answer a question using plain Bedrock."""

        markdown = self.read_markdown(path)
        prompt = (
            "Responde la pregunta usando únicamente la evidencia del Markdown.\n"
            "No copies ni reimprimas el Markdown completo. No devuelvas tablas salvo que la pregunta lo pida explícitamente.\n"
            "Devuelve sólo la respuesta final, breve y directa. Si la respuesta no aparece en el Markdown, di: No encontré la respuesta en el Markdown.\n\n"
            f"# Pregunta\n{question}\n\n"
            f"# Markdown disponible\n{markdown['content']}"
        )
        result = self.complete(
            prompt,
            instructions=instructions or (
                "Eres un lector estricto de Markdown. Contesta sólo la pregunta, con la mínima información necesaria; "
                "no reproduzcas el documento fuente."
            ),
            max_tokens=max_tokens,
            temperature=temperature,
            mode=mode,
            data={"kind": "markdown_answer", "source": {k: v for k, v in markdown.items() if k != "content"}},
        )
        return result

    def embed(
        self,
        texts: str | Sequence[str],
        *,
        model: str | None = None,
        input_type: str | None = None,
    ) -> dict[str, Any]:
        """Create embeddings through Bedrock Runtime ``invoke_model``.

        The payload shape is selected generically for common Bedrock families.
        If your enterprise model uses a different schema, pass it through a
        dedicated wrapper instead of hardcoding it in notebooks.
        """

        selected_model = model or self.embedding_model
        if not selected_model:
            raise ValueError("No embedding model configured. Pass embedding_model=... or model=...")
        items = [texts] if isinstance(texts, str) else [str(item) for item in texts]
        if not items:
            raise ValueError("embed(...) expects at least one text.")

        payload = _embedding_payload(selected_model, items, input_type=input_type)
        try:
            started_at = time.perf_counter()
            response = self._runtime.runtime.invoke_model(
                modelId=selected_model,
                body=json.dumps(payload).encode("utf-8"),
                accept="application/json",
                contentType="application/json",
            )
            client_duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            raw_body = response.get("body")
            body_bytes = raw_body.read() if hasattr(raw_body, "read") else raw_body
            parsed = json.loads(body_bytes.decode("utf-8") if isinstance(body_bytes, bytes) else body_bytes)
            embeddings = _extract_embeddings(parsed)
            return {
                "ok": True,
                "engine": BEDROCK_RUNTIME_ENGINE,
                "model": selected_model,
                "input_count": len(items),
                "embedding_count": len(embeddings),
                "dimensions": len(embeddings[0]) if embeddings else 0,
                "client_duration_ms": client_duration_ms,
                "embeddings": embeddings,
                "raw": parsed,
            }
        except Exception as exc:  # noqa: BLE001 - provider errors should be returned as data.
            error = exc.response.get("Error", {}) if hasattr(exc, "response") else {}
            return {
                "ok": False,
                "engine": BEDROCK_RUNTIME_ENGINE,
                "model": selected_model,
                "input_count": len(items),
                "error_code": error.get("Code"),
                "message": error.get("Message", str(exc)),
            }


def _import_bedrock_runtime() -> Any:
    """Import the optional Bedrock provider with a notebook-friendly error."""

    try:
        from .providers.bedrock_runtime import BedrockRuntime
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise ImportError(
            "BedrockRuntimeClient requires optional AWS dependencies. "
            "Install with: pip install -e '.[bedrock]'."
        ) from exc
    return BedrockRuntime


def _embedding_payload(model_id: str, texts: list[str], *, input_type: str | None) -> dict[str, Any]:
    lower_model = model_id.lower()
    if "cohere" in lower_model:
        payload: dict[str, Any] = {"texts": texts, "input_type": input_type or "search_document"}
        return payload
    if "titan" in lower_model:
        if len(texts) == 1:
            return {"inputText": texts[0]}
        return {"inputText": "\n\n".join(texts)}
    # Generic modern embedding fallback. Many marketplace models accept either
    # inputs or texts; callers can specialize outside this primitive when needed.
    return {"texts": texts, **({"input_type": input_type} if input_type else {})}


def _extract_embeddings(payload: Any) -> list[list[float]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("embedding"), list):
        return [payload["embedding"]]
    if isinstance(payload.get("embeddings"), list):
        embeddings = payload["embeddings"]
        if embeddings and isinstance(embeddings[0], dict) and "embedding" in embeddings[0]:
            return [item["embedding"] for item in embeddings if isinstance(item, dict) and isinstance(item.get("embedding"), list)]
        return embeddings
    if isinstance(payload.get("vectors"), list):
        return payload["vectors"]
    return []


__all__ = ["BedrockRuntimeClient", "DEFAULT_EMBEDDING_MODEL_ID"]
