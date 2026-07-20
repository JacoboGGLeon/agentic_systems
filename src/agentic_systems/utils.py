"""Notebook and diagnostics utilities for Agentic Systems 1.0."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


_DEFAULT_SENSITIVE_KEY_PATTERN = re.compile(
    r"(secret|token|password|passwd|credential|access[_-]?key|session[_-]?key|private[_-]?key|api[_-]?key)",
    flags=re.IGNORECASE,
)
_DEFAULT_IDENTIFIER_KEY_PATTERN = re.compile(
    r"^(account|account_id|arn|userid|user_id|access_key_id)$",
    flags=re.IGNORECASE,
)
_AWS_ENV_KEYS = (
    "AWS_PROFILE",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
)



AGENT_OUTPUT_SCHEMA_VERSION = "agentic_systems.agent_output.v1"
OUTPUT_SCHEMA_VERSION = "agentic_systems.output.v1"

FieldsMapper = Callable[[Any, Mapping[str, Any]], Mapping[str, Any]]


def _aggregate_usage(results: list[Any]) -> dict[str, Any]:
    usage: dict[str, Any] = {}
    for result in results:
        current = getattr(result, "usage", None) or {}
        if not isinstance(current, Mapping):
            continue
        for key, value in current.items():
            if isinstance(value, bool):
                usage[key] = value
            elif isinstance(value, int | float):
                usage[key] = usage.get(key, 0) + value
            elif key not in usage:
                usage[key] = value
    return usage


def _select_representative_result(results: list[Any]) -> Any | None:
    for result in reversed(results):
        if getattr(result, "usage", None):
            return result
    return results[-1] if results else None


def compose_result(
    *,
    text: str,
    data: Mapping[str, Any],
    results: list[Any] | tuple[Any, ...],
    mode: str,
    framework: str = "agentic-systems",
    input: Any | None = None,
    engine: str | None = None,
    model: str | None = None,
    meta: Mapping[str, Any] | None = None,
) -> Any:
    """Compose several real ``RunResult`` objects into one auditable result.

    Tutorials use this when a visible workflow has several internal agent runs:
    deterministic tools, optional LM review, graph nodes, and final rendering.
    The helper keeps engine, usage and tool events grounded in actual results so
    notebooks do not invent one-off runtime metadata.
    """

    from .engines.names import PYTHON_RUNTIME_ENGINE
    from .results import RunResult

    real_results = [item for item in results if item is not None]
    selected_runtime = _select_representative_result(real_results)
    resolved_engine = engine or getattr(selected_runtime, "engine", None) or PYTHON_RUNTIME_ENGINE
    resolved_model = model or getattr(selected_runtime, "model", None) or "python-runtime"
    tool_events: list[Any] = []
    raw_responses: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    engines_used: list[str] = []

    for item in real_results:
        item_engine = getattr(item, "engine", None)
        if item_engine and item_engine not in engines_used:
            engines_used.append(str(item_engine))
        tool_events.extend(list(getattr(item, "tool_events", []) or []))
        raw_responses.extend(list(getattr(item, "raw_responses", []) or []))
        messages.extend(list(getattr(item, "messages", []) or []))

    result_meta = dict(meta or {})
    if input is not None:
        result_meta.setdefault("input", input)
    result_meta.setdefault("framework", framework)
    result_meta.setdefault("runtime_engine", resolved_engine)
    result_meta.setdefault("execution_engine", resolved_engine)
    result_meta.setdefault("engines_used", engines_used or [resolved_engine])

    return RunResult(
        text=text,
        data=dict(data),
        final=dict(data),
        ok=all(bool(getattr(item, "ok", True)) for item in real_results) if real_results else True,
        messages=messages,
        tool_events=tool_events,
        raw_responses=raw_responses,
        usage=_aggregate_usage(real_results),
        engine=resolved_engine,
        model=resolved_model,
        mode=mode,
        meta=result_meta,
    )


def agent_output(
    result: Any,
    *,
    kind: str = "agent",
    fields_mapper: FieldsMapper | None = None,
    include_trace: bool = False,
    max_string_chars: int | None = None,
) -> dict[str, Any]:
    """Return the canonical output envelope for any agentic execution.

    ``answer`` is always a string: the final user-facing business answer. Any
    compact preview of that answer belongs in ``summary.answer_preview``. Tools,
    runtime metadata, usage and validation stay in their own fields so notebooks
    do not create one-off output dialects.

    ``fields_mapper`` is the sanctioned extension point for domain notebooks. It
    receives the raw result plus normalized context and may derive business
    fields from real evidence. The core does not know demo-specific tools or
    expected answers.
    """

    result_dict = _to_jsonable(result)
    data = result_dict.get("data") or {}
    validation = result_dict.get("validation") or {}
    events = _result_events(result_dict)
    raw_text = str(result_dict.get("text") or "")
    answer_text = _user_facing_answer_text(raw_text, data, result_dict)
    tools = [
        _tool_event_summary(
            event,
            include_input=True,
            max_string_chars=max_string_chars or 10_000,
        )
        for event in events
    ]
    fields = _extract_output_fields(
        result,
        result_dict=result_dict,
        answer_text=answer_text,
        data=data,
        tools=tools,
        fields_mapper=fields_mapper,
    )
    summary = _agent_data_summary(data, raw_text, max_string_chars=max_string_chars)
    answer_preview = _answer_preview(answer_text, max_string_chars=max_string_chars)
    if answer_preview:
        summary = {**summary, "answer_preview": answer_preview}

    meta = result_dict.get("meta") if isinstance(result_dict.get("meta"), Mapping) else {}
    runtime_engine = meta.get("runtime_engine") or result_dict.get("engine")
    framework = meta.get("framework") or result_dict.get("framework")
    output: dict[str, Any] = {
        "schema_version": AGENT_OUTPUT_SCHEMA_VERSION,
        "kind": kind,
        "ok": bool(result_dict.get("ok")),
        "answer": _answer_string(answer_text, max_string_chars=max_string_chars),
        "fields": fields,
        "summary": summary,
        "data": _maybe_bound_json(data, max_string_chars=max_string_chars),
        "tools": tools,
        "runtime": {
            "engine": runtime_engine,
            "framework": framework,
            "mode": result_dict.get("mode"),
            "model": result_dict.get("model"),
        },
        "usage": _usage_summary(result_dict.get("usage") or {}),
        "validation_ok": validation.get("ok"),
        "validation": {
            "ok": validation.get("ok"),
            "issues": _maybe_bound_json(validation.get("issues") or [], max_string_chars=max_string_chars),
        },
    }
    if include_trace:
        trace = result.trace("compact") if hasattr(result, "trace") else result_dict
        output["trace"] = _maybe_bound_json(trace, max_string_chars=max_string_chars)
    return output


def make_agent_output_mapper(
    *,
    kind: str = "agent",
    fields_mapper: FieldsMapper | None = None,
    include_trace: bool = False,
    max_string_chars: int | None = None,
) -> Callable[[Any, Mapping[str, Any] | None], dict[str, Any]]:
    """Create a graph output mapper that writes ``agent_output``.

    This keeps LangGraph/portable graph nodes generic while allowing a notebook
    to attach a domain-specific fields mapper explicitly.
    """

    def _mapper(result: Any, state: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {
            "agent_output": agent_output(
                result,
                kind=kind,
                fields_mapper=fields_mapper,
                include_trace=include_trace,
                max_string_chars=max_string_chars,
            )
        }

    return _mapper


def agent_output_mapper(result: Any, state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Default graph output mapper that writes the canonical ``agent_output``.

    The ``state`` argument is accepted for compatibility with mapper call sites;
    it is intentionally unused so the default mapper remains business-agnostic.
    """

    return {"agent_output": agent_output(result)}

def configure_notebook_environment(
    repo_root: str | Path | None = None,
    *,
    add_src: bool = True,
    aws_safe: bool = True,
) -> Path:
    """Configure local imports for notebooks without mutating real AWS credentials.

    Parameters
    ----------
    repo_root:
        Optional repository root. When omitted, the root is discovered from the
        current working directory.
    add_src:
        If true, prepend ``<repo>/src`` to ``sys.path`` when it exists.
    aws_safe:
        Reserved for backward-compatible call sites. It intentionally **does
        not** create fake AWS credentials. Earlier notebooks used dummy
        ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` values for local tests;
        in managed environments such as ADA/SageMaker those env variables can
        shadow the real execution role and cause ``InvalidClientTokenId``.

    Returns
    -------
    pathlib.Path
        Resolved repository root.
    """

    root = Path(repo_root) if repo_root is not None else _discover_repo_root(Path.cwd())
    root = root.resolve()
    # Put both repository root and src/ on sys.path for local notebook runs.
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    src_dir = root / "src"
    if add_src and src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    if aws_safe:
        _clear_dummy_aws_test_credentials()

    return root



def _clear_dummy_aws_test_credentials() -> list[str]:
    """Remove known dummy AWS credentials that can shadow managed roles.

    Some local tests and examples historically used ``AWS_ACCESS_KEY_ID=test``
    and ``AWS_SECRET_ACCESS_KEY=test``. In ADA/SageMaker those values are not
    harmless: boto3 chooses the ``env`` provider before the execution role and
    STS/Bedrock then fail with ``InvalidClientTokenId``.

    The helper only removes the literal dummy pair, never real-looking keys.
    """

    if os.getenv("AWS_ACCESS_KEY_ID") != "test":
        return []
    if os.getenv("AWS_SECRET_ACCESS_KEY") != "test":
        return []

    removed: list[str] = []
    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_SECURITY_TOKEN",
        "AWS_PROFILE",
    ):
        if key in os.environ:
            os.environ.pop(key, None)
            removed.append(key)
    return removed


def compare(outputs: Any, *, key: str = "fields", keys: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Compare normalized outputs and keep notebook display compact.

    ``outputs`` may contain ``RunResult`` objects, compact traces, normalized
    dictionaries or LangGraph state dictionaries. The helper coerces every item
    to the same compact run shape before selecting fields.
    """

    runs = [_coerce_compare_item(item) for item in list(outputs if isinstance(outputs, (list, tuple)) else [outputs])]
    if keys is not None:
        selected = list(keys)
        rows = [_compact_run_for_keys(item, selected, index=index) for index, item in enumerate(runs, start=1)]
        same = {name: _all_equal([row.get(name) for row in rows]) for name in selected}
        return {
            "ok": all(bool(row.get("run_ok", row.get("ok", False))) for row in rows),
            "count": len(rows),
            "keys": selected,
            "same": same,
            "runs": rows,
        }

    comparable = [item for item in runs if isinstance(item, Mapping) and key in item]
    same = None
    shared_value: Any = None
    if comparable:
        first = comparable[0].get(key)
        same = all(item.get(key) == first for item in comparable[1:])
        shared_value = first if same else None

    return {
        "ok": all(isinstance(item, Mapping) and item.get("ok", item.get("run_ok")) is True for item in runs),
        f"same_{key}": same,
        key: shared_value,
        "runs": [_compact_run_for_compare(item, key=key, include_key=not bool(same)) for item in runs],
    }


def _coerce_compare_item(item: Any) -> dict[str, Any]:
    """Return a compact, framework-agnostic run dictionary."""

    if hasattr(item, "trace"):
        try:
            traced = item.trace("compact")
            if isinstance(traced, Mapping):
                return dict(traced)
        except Exception:
            pass

    value = _to_jsonable(item)
    if not isinstance(value, Mapping):
        return {"run_ok": False, "value": value}

    if "trace_schema_version" in value or "run_ok" in value:
        compact = dict(value)
        normalized = compact.get("normalized") if isinstance(compact.get("normalized"), Mapping) else None
        runtime = normalized.get("runtime") if isinstance(normalized, Mapping) and isinstance(normalized.get("runtime"), Mapping) else {}
        compact.setdefault("framework", runtime.get("framework"))
        return compact

    normalized = value.get("normalized") if isinstance(value.get("normalized"), Mapping) else None
    if normalized is None and isinstance(value.get("compact"), Mapping):
        compact = value["compact"]
        if isinstance(compact.get("normalized"), Mapping):
            normalized = compact["normalized"]
    if normalized is not None:
        return _compact_from_normalized(dict(normalized), value)

    # Serialized RunResult dictionaries from LangGraph land here.
    if "tool_events" in value or "ok" in value or "engine" in value:
        return _compact_from_serialized_run(dict(value))

    return dict(value)


def _compact_from_serialized_run(value: Mapping[str, Any]) -> dict[str, Any]:
    events = value.get("tool_events") if isinstance(value.get("tool_events"), list) else []
    failed = [event for event in events if isinstance(event, Mapping) and not event.get("ok")]
    meta = value.get("meta") if isinstance(value.get("meta"), Mapping) else {}
    normalized = {
        "schema_version": "agentic_systems.run.v1",
        "ok": bool(value.get("ok", False)),
        "runtime": {
            "engine": value.get("engine"),
            "runtime_engine": meta.get("runtime_engine", value.get("engine")),
            "framework": meta.get("framework") or value.get("framework"),
            "model": value.get("model"),
            "mode": value.get("mode"),
        },
        "input": meta.get("input") or value.get("input") or value.get("prompt"),
        "answer": {"text": value.get("text") or "", "data": value.get("data") or {}},
        "tools": [_normalize_compare_event(event) for event in events if isinstance(event, Mapping)],
        "usage": value.get("usage") or {},
        "validation": value.get("validation"),
    }
    compact = _compact_from_normalized(normalized, value)
    compact["tool_events"] = list(events)
    compact["failed_tool_event_count"] = len(failed)
    compact["successful_tool_count"] = len(events) - len(failed)
    return compact


def _compact_from_normalized(normalized: Mapping[str, Any], source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    runtime = normalized.get("runtime") if isinstance(normalized.get("runtime"), Mapping) else {}
    tools = normalized.get("tools") if isinstance(normalized.get("tools"), list) else []
    failed = [tool for tool in tools if isinstance(tool, Mapping) and not tool.get("ok")]
    source = source or {}
    return {
        "trace_schema_version": source.get("trace_schema_version", "agentic_systems.trace.v1"),
        "run_ok": bool(normalized.get("ok", source.get("ok", False))),
        "ok": bool(normalized.get("ok", source.get("ok", False))),
        "engine": runtime.get("engine") or source.get("engine"),
        "framework": runtime.get("framework") or source.get("framework"),
        "model": runtime.get("model") or source.get("model"),
        "mode": runtime.get("mode") or source.get("mode"),
        "text": (normalized.get("answer") or {}).get("text") if isinstance(normalized.get("answer"), Mapping) else source.get("text"),
        "data": (normalized.get("answer") or {}).get("data") if isinstance(normalized.get("answer"), Mapping) else source.get("data"),
        "tool_event_count": len(tools),
        "successful_tool_count": len(tools) - len(failed),
        "failed_tool_event_count": len(failed),
        "usage": normalized.get("usage") or source.get("usage") or {},
        "validation": normalized.get("validation") or source.get("validation"),
        "normalized": dict(normalized),
    }


def _normalize_compare_event(event: Mapping[str, Any]) -> dict[str, Any]:
    output = event.get("output") or {}
    payload = output.get("data") if isinstance(output, Mapping) and isinstance(output.get("data"), Mapping) else output
    payload = payload if isinstance(payload, Mapping) else {"value": payload}
    table = payload.get("table") if isinstance(payload.get("table"), Mapping) else {}
    query = payload.get("query") if isinstance(payload.get("query"), Mapping) else {}
    return {
        "name": event.get("name") or payload.get("tool") or "tool",
        "ok": bool(event.get("ok")),
        "input": event.get("input") or {},
        "output": dict(payload),
        "summary": payload.get("summary") or payload.get("error") or payload.get("text"),
        "sql": payload.get("sql"),
        "rows": table.get("rows") or [],
        "row_count": table.get("n_rows"),
        "route": payload.get("route"),
        "query_id": query.get("query_id") or payload.get("query_id"),
    }


def _all_equal(values: list[Any]) -> bool | None:
    if not values:
        return None
    first = values[0]
    return all(value == first for value in values[1:])


def _lookup_key(item: Mapping[str, Any], key: str) -> Any:
    current: Any = item
    for part in key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _compact_run_for_keys(item: Any, keys: list[str], *, index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        return {"run": index, "ok": False, "value": _to_jsonable(item)}
    row: dict[str, Any] = {"run": index}
    for name in keys:
        value = _lookup_key(item, name)
        if value is None and name == "ok":
            value = item.get("run_ok")
        if value is None and name == "run_ok":
            value = item.get("ok")
        row[name] = _to_jsonable(value)
    return row


def _compact_run_for_compare(item: Any, *, key: str, include_key: bool) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        return {"ok": False, "value": _to_jsonable(item)}

    runtime = item.get("runtime") if isinstance(item.get("runtime"), Mapping) else {}
    row: dict[str, Any] = {
        "label": item.get("label"),
        "tool_declaration": item.get("tool_declaration"),
        "kind": item.get("kind"),
        "ok": item.get("ok", item.get("run_ok")),
        "validation_ok": item.get("validation_ok"),
        "engine": runtime.get("engine") if runtime else item.get("engine"),
        "framework": item.get("framework"),
    }
    if "executed" in item:
        row["executed"] = item.get("executed")
    if "run_requested" in item:
        row["run_requested"] = item.get("run_requested")
    if "sdk_available" in item:
        row["sdk_available"] = item.get("sdk_available")
    if item.get("graph_mode") is not None:
        row["graph_mode"] = item.get("graph_mode")
    if item.get("tools") is not None:
        row["tools"] = item.get("tools")
    if item.get("reason"):
        row["reason"] = item.get("reason")
    if include_key and key in item:
        row[key] = item.get(key)
    return {k: v for k, v in row.items() if v is not None}

def show_json(
    value: Any,
    title: str | None = None,
    *,
    mask: bool = True,
    explanations: Mapping[str, str] | None = None,
) -> None:
    """Pretty-print JSON-compatible values with optional masking and field notes.

    ``mask=True`` is the default because diagnostics often contain AWS account
    identifiers, ARNs, tokens or credential metadata. The masking preserves the
    shape of the output while reducing accidental leakage in notebook screenshots
    and logs.
    """

    if title:
        print(f"\n=== {title} ===")
    jsonable = _to_jsonable(value)
    if mask:
        jsonable = mask_sensitive(jsonable)
    print(json.dumps(jsonable, indent=2, ensure_ascii=False, default=str))
    if explanations:
        print("\nExplanation:")
        for key, description in explanations.items():
            print(f"- {key}: {description}")


def show(
    value: Any,
    title: str | None = None,
    *,
    mask: bool = True,
    explanations: Mapping[str, str] | None = None,
) -> None:
    """Notebook display helper for Agentic Systems objects.

    JSON-compatible objects keep the historical ``show_json`` behavior.
    ``LineageMemory``-like objects render as an explanation so notebooks show
    "qué pasó" instead of only a compact prompt blob.
    """

    if hasattr(value, "human_text") and callable(value.human_text):
        if title:
            print(f"\n=== {title} ===")
        print(value.human_text())
        if explanations:
            print("\nExplanation:")
            for key, description in explanations.items():
                print(f"- {key}: {description}")
        return
    show_json(value, title=title, mask=mask, explanations=explanations)


def mask_sensitive(value: Any) -> Any:
    """Return a copy of ``value`` with sensitive-looking fields masked."""

    return _mask_sensitive(value, parent_key="")


def aws_environment_snapshot(*, include_values: bool = False, mask: bool | None = None) -> dict[str, Any]:
    """Return a small AWS-related environment snapshot for notebooks.

    By default values are represented as ``"SET"``/``None`` to avoid exposing
    credentials. Set ``include_values=True`` only for trusted local debugging;
    callers should still pass the result through :func:`show_json` with masking.
    """

    env: dict[str, Any] = {}
    for key in _AWS_ENV_KEYS:
        raw_value = os.getenv(key)
        if include_values:
            env[key] = raw_value
        else:
            env[key] = "SET" if raw_value else None
    return env


def boto3_session_snapshot(region_name: str | None = None, *, mask: bool | None = None) -> dict[str, Any]:
    """Describe the active boto3 credential provider without exposing secrets."""

    try:
        import boto3
    except Exception as exc:  # pragma: no cover - depends on optional runtime env
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
            "hint": "Install boto3 to inspect AWS credentials and Bedrock access.",
        }

    session = boto3.Session(region_name=region_name)
    credentials = session.get_credentials()
    return {
        "ok": credentials is not None,
        "session_region": session.region_name,
        "credential_method": getattr(credentials, "method", None) if credentials else None,
        "has_credentials": credentials is not None,
    }


def repair_ada_credential_chain(
    region_name: str | None = None,
    *,
    force: bool = False,
    mask: bool | None = None,
) -> dict[str, Any]:
    """Repair a common ADA/SageMaker credential-chain failure mode.

    In ADA/SageMaker, stale static env credentials can shadow the execution
    role. When ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY`` are present
    but ``AWS_SESSION_TOKEN`` is missing, boto3 often chooses the broken ``env``
    provider and STS returns ``InvalidClientTokenId``.

    To avoid surprising users with valid long-lived static credentials, the
    helper only mutates env variables when ``force=True``. Without force, it
    reports whether a repair *would* be applied.
    """

    before_env = aws_environment_snapshot(include_values=False)
    before_session = boto3_session_snapshot(region_name=region_name)

    has_static_pair = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    missing_session_token = not bool(os.getenv("AWS_SESSION_TOKEN"))
    credential_method = before_session.get("credential_method")
    repair_candidate = bool(has_static_pair and missing_session_token and credential_method == "env")
    should_repair = bool(force and repair_candidate)

    removed: list[str] = []
    if should_repair:
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_SECURITY_TOKEN",
            "AWS_PROFILE",
        ):
            if key in os.environ:
                os.environ.pop(key, None)
                removed.append(key)

    return {
        "repair_candidate": repair_candidate,
        "repaired": should_repair,
        "force": force,
        "removed_env_keys": removed,
        "before": {
            "environment": before_env,
            "session": before_session,
        },
        "after": {
            "environment": aws_environment_snapshot(include_values=False),
            "session": boto3_session_snapshot(region_name=region_name),
        },
    }



def run_result_output(result: Any, *, include_trace: bool = False) -> dict[str, Any]:
    """Return the compact audit view of a ``RunResult``.

    This keeps the normalized execution evidence close to the raw runtime
    contract: answer text, structured data, validation, tool outputs and token
    usage. It is intentionally JSON-first. For notebook screenshots or quick
    sandbox review, prefer :func:`run_result_view`, which summarizes long tool
    payloads and extracts field/value bullets from the answer text.
    """

    result_dict = _to_jsonable(result)
    events = _result_events(result_dict)
    output = {
        "ok": result_dict.get("ok"),
        "engine": result_dict.get("engine"),
        "mode": result_dict.get("mode"),
        "text": result_dict.get("text"),
        "final": result_dict.get("final") or result_dict.get("data") or {},
        "data": result_dict.get("data") or {},
        "validation_ok": (result_dict.get("validation") or {}).get("ok"),
        "tools_called": [event.get("name") for event in events],
        "tool_outputs": [_compact_tool_event(event) for event in events],
        "usage": result_dict.get("usage") or {},
    }
    if include_trace and hasattr(result, "trace"):
        output["trace"] = result.trace("compact")
    return output


def run_result_view(
    result: Any,
    *,
    include_tools: bool = True,
    include_usage: bool = True,
    max_string_chars: int = 240,
    max_items: int = 20,
    max_depth: int = 4,
) -> dict[str, Any]:
    """Return a human-first notebook view of a ``RunResult``.

    The view is generic: it does not know specific demo cases or tool names. It
    simply extracts common ``- key: value`` answer fields, summarizes large JSON
    payloads, and keeps runtime metadata separate from the business answer.
    """

    result_dict = _to_jsonable(result)
    validation = result_dict.get("validation") or {}
    text = str(result_dict.get("text") or "")
    data = result_dict.get("data") or {}
    final = result_dict.get("final") or {}
    events = _result_events(result_dict)

    meta = result_dict.get("meta") or {}
    runtime_engine = meta.get("runtime_engine") or result_dict.get("engine")
    framework = meta.get("framework")

    final_is_plain_text = isinstance(final, dict) and set(final) == {"text"} and final.get("text") == text
    final_fields = final if isinstance(final, dict) and final and not final_is_plain_text else _parse_answer_fields(text)

    view: dict[str, Any] = {
        "status": {
            "ok": result_dict.get("ok"),
            "validation_ok": validation.get("ok"),
            "issue_count": len(validation.get("issues") or []),
        },
        "answer": _summarize_json(final if final and not final_is_plain_text else text, max_string_chars=max_string_chars, max_items=max_items, max_depth=max_depth),
        "fields": final_fields,
        "final": _summarize_json(final, max_string_chars=max_string_chars, max_items=max_items, max_depth=max_depth),
        "data": _summarize_json(data, max_string_chars=max_string_chars, max_items=max_items, max_depth=max_depth),
        "runtime": {
            "engine": runtime_engine,
            "framework": framework,
            "mode": result_dict.get("mode"),
            "model": result_dict.get("model"),
        },
    }
    if include_tools:
        view["tools"] = [
            _tool_event_view(
                event,
                max_string_chars=max_string_chars,
                max_items=max_items,
                max_depth=max_depth,
            )
            for event in events
        ]
    if include_usage:
        view["usage"] = result_dict.get("usage") or {}
    return view



def tool_result_summary(result: Any, *, max_string_chars: int = 120) -> dict[str, Any]:
    """Return the smallest useful view of a direct ``Tool.run`` result.

    This is meant for tutorials and smoke tests. It keeps the tool name,
    success flag and final normalized output, without repeating runtime fields
    or raw trace payloads.
    """

    result_dict = _to_jsonable(result)
    events = _result_events(result_dict)
    primary = events[-1] if events else {}
    output = _compact_tool_event(primary).get("output") if primary else (result_dict.get("data") or {})
    summary: dict[str, Any] = {
        "ok": result_dict.get("ok"),
        "tool": primary.get("name") if primary else None,
        "output": _minimal_json(output, max_string_chars=max_string_chars),
    }
    if not result_dict.get("ok"):
        summary["error"] = _minimal_json(result_dict.get("data") or result_dict.get("text"), max_string_chars=max_string_chars)
    return summary


def run_result_summary(
    result: Any,
    *,
    kind: str = "agent",
    fields_mapper: FieldsMapper | None = None,
    include_runtime: bool = False,
    include_usage: bool = False,
    include_tool_inputs: bool = True,
    max_string_chars: int = 120,
) -> dict[str, Any]:
    """Return the default normalized notebook view of a ``RunResult``.

    The shape mirrors :func:`agent_output` but stays compact for screenshots:
    ``answer`` is always a string, ``fields`` are always structured values,
    ``summary`` contains previews/shape hints, and ``tools`` contains evidence.
    """

    result_dict = _to_jsonable(result)
    validation = result_dict.get("validation") or {}
    text = str(result_dict.get("text") or "")
    data = result_dict.get("data") or {}
    events = _result_events(result_dict)
    answer_text = _user_facing_answer_text(text, data, result_dict)
    tools = [
        _tool_event_summary(event, include_input=include_tool_inputs, max_string_chars=max_string_chars)
        for event in events
    ]
    fields = _extract_output_fields(
        result,
        result_dict=result_dict,
        answer_text=answer_text,
        data=data,
        tools=tools,
        fields_mapper=fields_mapper,
    )
    summary_payload = _agent_data_summary(data, text, max_string_chars=max_string_chars)
    answer_preview = _answer_preview(answer_text, max_string_chars=max_string_chars)
    if answer_preview:
        summary_payload = {**summary_payload, "answer_preview": answer_preview}

    summary: dict[str, Any] = {
        "schema_version": AGENT_OUTPUT_SCHEMA_VERSION,
        "kind": kind,
        "ok": result_dict.get("ok"),
        "answer": _answer_string(answer_text, max_string_chars=max_string_chars),
        "fields": fields,
        "summary": summary_payload,
        "validation_ok": validation.get("ok"),
    }
    if data:
        summary["data"] = _minimal_json(data, max_string_chars=max_string_chars)
    if tools:
        summary["tools"] = tools
    issues = validation.get("issues") or []
    if issues:
        summary["issues"] = _minimal_json(issues, max_string_chars=max_string_chars)
    if include_runtime:
        summary["runtime"] = {
            "engine": result_dict.get("engine"),
            "mode": result_dict.get("mode"),
            "model": result_dict.get("model"),
        }
    if include_usage:
        summary["usage"] = _usage_summary(result_dict.get("usage") or {})
    return summary

def chain_history_summary(history: Any, *, max_string_chars: int = 120) -> list[dict[str, Any]]:
    """Return a compact step list for ``Chain.history()``."""

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(_to_jsonable(history) or [], start=1):
        if not isinstance(item, dict):
            rows.append({"step": index, "value": _minimal_json(item, max_string_chars=max_string_chars)})
            continue
        output = item.get("output") or {}
        row = {
            "step": index,
            "name": item.get("name"),
            "kind": item.get("kind"),
            "ok": output.get("ok"),
            "answer": _summarize_string(str(output.get("text") or ""), max_chars=max_string_chars),
        }
        usage = output.get("usage") or {}
        if usage:
            row["usage"] = _usage_summary(usage)
        rows.append(row)
    return rows


def environment_summary(environment_or_render: Any, *, max_string_chars: int = 120) -> dict[str, Any]:
    """Return a minimal episode view for ``AgenticEnvironment`` outputs.

    The full environment render contains graph state, memory and embedded
    ``RunResult`` payloads. This summary keeps the episode headline and one
    compact row per transition.
    """

    payload = environment_or_render.render() if hasattr(environment_or_render, "render") else _to_jsonable(environment_or_render)
    payload = _to_jsonable(payload)
    history = payload.get("history") or [] if isinstance(payload, dict) else []
    steps: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        graph_state = item.get("graph_state") or {}
        agent_output_payload = graph_state.get("agent_output") if isinstance(graph_state.get("agent_output"), dict) else {}
        agent_result = graph_state.get("agent_result") or graph_state.get("eval", {}).get("result")
        answer = agent_output_payload.get("answer") or graph_state.get("agent_text")
        if not answer and isinstance(agent_result, dict):
            answer = agent_result.get("text")
        step: dict[str, Any] = {
            "step": item.get("step_index"),
            "reward": item.get("reward"),
            "done": bool(item.get("terminated") or item.get("truncated")),
        }
        row = item.get("row")
        if row:
            step["row"] = _minimal_json(row, max_string_chars=max_string_chars)
        selected = graph_state.get("selected_agent")
        if selected:
            step["agent"] = selected
        plan = graph_state.get("plan") or {}
        if isinstance(plan, dict) and plan:
            if plan.get("step_id"):
                step["plan_step"] = plan.get("step_id")
            if plan.get("reason"):
                step["reason"] = _summarize_string(str(plan.get("reason")), max_chars=max_string_chars)
            if plan.get("expected_tools"):
                step["expected_tools"] = list(plan.get("expected_tools") or [])
        if answer:
            step["answer"] = _answer_string(str(answer), max_string_chars=max_string_chars)
        if agent_output_payload:
            fields = agent_output_payload.get("fields") or {}
            if fields:
                step["fields"] = _minimal_json(fields, max_string_chars=max_string_chars)
            tool_names = [event.get("name") for event in agent_output_payload.get("tools") or [] if isinstance(event, dict)]
            if tool_names:
                step["tools"] = tool_names
            validation = agent_output_payload.get("validation") or {}
            if validation:
                step["validation_ok"] = validation.get("ok")
        if isinstance(agent_result, dict):
            tool_names = [event.get("name") for event in agent_result.get("tool_events") or [] if isinstance(event, dict)]
            if tool_names and "tools" not in step:
                step["tools"] = tool_names
            validation = agent_result.get("validation") or {}
            if validation and "validation_ok" not in step:
                step["validation_ok"] = validation.get("ok")
        steps.append(step)

    return {
        "ok": bool(payload.get("done")) if isinstance(payload, dict) else None,
        "name": payload.get("name") if isinstance(payload, dict) else None,
        "episode_id": payload.get("episode_id") if isinstance(payload, dict) else None,
        "steps_done": payload.get("step") if isinstance(payload, dict) else None,
        "total_records": payload.get("total_records") if isinstance(payload, dict) else None,
        "reward_total": sum(float(step.get("reward") or 0.0) for step in steps),
        "steps": steps,
    }


def eval_report_summary(report: Any, *, max_string_chars: int = 120) -> dict[str, Any]:
    """Return the minimal notebook view of an ``EvalReport``."""

    payload = _to_jsonable(report)
    cases = []
    for case in payload.get("cases", []) or []:
        result = case.get("result") or {}
        cases.append(
            {
                "name": case.get("name"),
                "ok": case.get("ok"),
                "answer": _summarize_string(str(result.get("text") or ""), max_chars=max_string_chars),
                "tools": [event.get("name") for event in result.get("tool_events") or [] if isinstance(event, dict)],
                "validation_ok": (case.get("validation") or {}).get("ok"),
            }
        )
    return {
        "ok": payload.get("ok"),
        "passed": payload.get("passed"),
        "failed": payload.get("failed"),
        "pass_rate": payload.get("pass_rate"),
        "cases": cases,
    }

def eval_report_output(report: Any, *, include_trace: bool = False) -> dict[str, Any]:
    """Return a compact, output-first view of an ``EvalReport``."""

    payload = _to_jsonable(report)
    if include_trace:
        return payload
    return {
        "ok": payload.get("ok"),
        "total": payload.get("total"),
        "passed": payload.get("passed"),
        "failed": payload.get("failed"),
        "pass_rate": payload.get("pass_rate"),
        "cases": [
            {
                "name": case.get("name"),
                "ok": case.get("ok"),
                "validation": case.get("validation"),
                "result": run_result_output(case.get("result") or {}),
            }
            for case in payload.get("cases", [])
        ],
    }


def maybe_show_trace(result: Any, *, show_trace: bool = False, title: str = "Trace", mask: bool = True) -> None:
    """Display compact trace only when a notebook toggles ``SHOW_TRACE=True``."""

    if not show_trace:
        return
    if hasattr(result, "trace"):
        show_json(result.trace("compact"), title=title, mask=mask)
        return
    show_json(_to_jsonable(result), title=title, mask=mask)


def _result_events(result_dict: dict[str, Any]) -> list[dict[str, Any]]:
    events = result_dict.get("tool_events") or []
    return [event for event in events if isinstance(event, dict)]


def _compact_tool_event(event: dict[str, Any]) -> dict[str, Any]:
    output = event.get("output") or {}
    if isinstance(output, dict):
        output_data = output.get("data", output)
    else:
        output_data = output
    compact = {
        "tool": event.get("name"),
        "ok": event.get("ok"),
        "input": event.get("input") or {},
        "output": output_data,
    }
    error = event.get("error")
    if error:
        compact["error"] = error
    return compact


def _tool_event_view(
    event: dict[str, Any],
    *,
    max_string_chars: int,
    max_items: int,
    max_depth: int,
) -> dict[str, Any]:
    output = event.get("output") or {}
    output_data = output.get("data", output) if isinstance(output, dict) else output
    view = {
        "tool": event.get("name"),
        "ok": event.get("ok"),
        "input": _summarize_json(event.get("input") or {}, max_string_chars=max_string_chars, max_items=max_items, max_depth=max_depth),
        "output": _summarize_json(output_data, max_string_chars=max_string_chars, max_items=max_items, max_depth=max_depth),
    }
    error = event.get("error")
    if error:
        view["error"] = _summarize_json(error, max_string_chars=max_string_chars, max_items=max_items, max_depth=max_depth)
    return view





def _extract_output_fields(
    result: Any,
    *,
    result_dict: dict[str, Any],
    answer_text: str,
    data: Any,
    tools: list[dict[str, Any]],
    fields_mapper: FieldsMapper | None,
) -> dict[str, Any]:
    """Extract normalized output fields without embedding business logic."""

    fields: dict[str, Any] = {}
    fields.update(_parse_answer_fields(answer_text))

    if isinstance(data, dict) and isinstance(data.get("fields"), Mapping):
        fields.update({str(key): _to_jsonable(value) for key, value in data["fields"].items()})
    elif not fields and isinstance(data, dict):
        reserved_data_keys = {"ok", "tool", "tools", "steps", "last", "operation", "schema_version"}
        simple_data = {
            str(key): _to_jsonable(value)
            for key, value in data.items()
            if str(key) not in reserved_data_keys and not isinstance(value, (dict, list, tuple, set))
        }
        if simple_data and len(simple_data) <= 12:
            fields.update(simple_data)

    if fields_mapper is not None:
        mapped = fields_mapper(
            result,
            {
                "result_dict": result_dict,
                "answer": answer_text,
                "data": data,
                "tools": tools,
                "fields": dict(fields),
            },
        )
        if not isinstance(mapped, Mapping):
            raise TypeError("fields_mapper must return a mapping.")
        fields.update({str(key): _to_jsonable(value) for key, value in mapped.items()})

    return fields


def _answer_string(value: str, *, max_string_chars: int | None) -> str:
    """Bound an answer while preserving the invariant that answer is a string."""

    text = str(value or "")
    if max_string_chars is None or len(text) <= max_string_chars:
        return text
    return f"{text[: max(max_string_chars, 0)].rstrip()}…"


def _answer_preview(value: str, *, max_string_chars: int | None) -> dict[str, Any]:
    text = str(value or "")
    if not text:
        return {}
    limit = max_string_chars or 240
    if len(text) <= limit:
        return {"type": "string", "chars": len(text), "lines": text.count("\n") + 1}
    preview = text[: max(limit, 0)].rstrip()
    return {
        "type": "string",
        "chars": len(text),
        "lines": text.count("\n") + 1,
        "preview": f"{preview}…",
    }


def _user_facing_answer_text(text: str, data: Any, result_dict: dict[str, Any]) -> str:
    """Keep ``answer`` reserved for final user-facing text only."""

    if not text:
        return ""
    engine = str(result_dict.get("engine") or "")
    if engine == "python-runtime":
        # python-runtime is a deterministic tool runner. Its text is an execution
        # artifact (for example JSON of tool steps), not a synthesized business
        # answer. Keep the data visible under ``data``/``summary`` instead.
        return ""
    if isinstance(data, dict) and isinstance(data.get("steps"), list) and _looks_like_json_object(text):
        return ""
    return text


def _looks_like_json_object(text: str) -> bool:
    stripped = text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return False
    try:
        parsed = json.loads(stripped)
    except Exception:
        return False
    return isinstance(parsed, dict)


def _agent_data_summary(data: Any, text: str, *, max_string_chars: int | None) -> Any:
    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        steps = data.get("steps") or []
        return {
            "kind": "tool_plan",
            "step_count": len(steps),
            "last": _maybe_bound_json(data.get("last") or {}, max_string_chars=max_string_chars),
        }
    if isinstance(data, dict) and data:
        return {
            "kind": "structured_data",
            "keys": list(data.keys()),
        }
    if text:
        return {"kind": "text"}
    return {"kind": "empty"}


def _maybe_bound_string(value: str, *, max_string_chars: int | None) -> Any:
    if max_string_chars is None:
        return value
    return _summarize_string(value, max_chars=max_string_chars)


def _maybe_bound_json(value: Any, *, max_string_chars: int | None) -> Any:
    if max_string_chars is None:
        return _to_jsonable(value)
    return _minimal_json(value, max_string_chars=max_string_chars)


def _result_answer_summary(text: str, data: Any, *, max_string_chars: int) -> Any:
    """Return a minimal answer that does not reprint structured tool-plan JSON."""

    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        steps = data.get("steps") or []
        last = data.get("last")
        return {
            "step_count": len(steps),
            "last": _minimal_json(last, max_string_chars=max_string_chars),
        }
    return _summarize_string(text, max_chars=max_string_chars) if text else ""


def _tool_event_summary(event: dict[str, Any], *, include_input: bool, max_string_chars: int) -> dict[str, Any]:
    compact = _compact_tool_event(event)
    summary: dict[str, Any] = {
        "name": compact.get("tool"),
        "ok": compact.get("ok"),
    }
    if include_input and compact.get("input"):
        summary["input"] = _minimal_json(compact.get("input"), max_string_chars=max_string_chars)
    output = compact.get("output")
    if output not in ({}, None, ""):
        summary["output"] = _minimal_json(output, max_string_chars=max_string_chars)
    if compact.get("error"):
        summary["error"] = _minimal_json(compact.get("error"), max_string_chars=max_string_chars)
    return summary


def _usage_summary(usage: dict[str, Any]) -> dict[str, Any]:
    """Return complete usage metrics without collapsing token accounting.

    Notebook summaries should be small, but token and timing information is
    already compact and highly useful for sandbox review. Keep every known usage
    metric instead of replacing it with a generic ``tokens`` field. Timing fields
    are included only when the runtime/backend reports them.
    """

    if not isinstance(usage, dict):
        return {}

    key_map = {
        "inputTokens": "input_tokens",
        "outputTokens": "output_tokens",
        "totalTokens": "total_tokens",
        "latencyMs": "service_latency_ms",
        "durationMs": "client_duration_ms",
    }
    normalized: dict[str, Any] = {}
    for raw_key, value in usage.items():
        key = key_map.get(str(raw_key), str(raw_key))
        normalized[key] = value

    ordered_keys = [
        "requests",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "service_latency_ms",
        "client_duration_ms",
        "duration_ms",
    ]
    output = {key: normalized[key] for key in ordered_keys if key in normalized}
    for key, value in normalized.items():
        if key not in output:
            output[key] = value
    return output


def _minimal_json(value: Any, *, max_string_chars: int, _depth: int = 0) -> Any:
    """Bound nested values aggressively for human-first summaries."""

    value = _to_jsonable(value)
    if _depth >= 2:
        return _shape_summary(value) if isinstance(value, (dict, list, tuple, set, str)) else value
    if isinstance(value, dict):
        items = list(value.items())
        result: dict[str, Any] = {}
        for key, item in items[:6]:
            result[str(key)] = _minimal_json(item, max_string_chars=max_string_chars, _depth=_depth + 1)
        if len(items) > 6:
            result["__more__"] = len(items) - 6
        return result
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        result = [_minimal_json(item, max_string_chars=max_string_chars, _depth=_depth + 1) for item in items[:6]]
        if len(items) > 6:
            result.append({"__more__": len(items) - 6})
        return result
    if isinstance(value, str):
        return _summarize_string(value, max_chars=max_string_chars)
    return value

def _summarize_json(
    value: Any,
    *,
    max_string_chars: int,
    max_items: int,
    max_depth: int,
    _depth: int = 0,
) -> Any:
    """Return a bounded JSON-like value for notebook display."""

    value = _to_jsonable(value)
    if _depth >= max_depth:
        return _shape_summary(value)
    if isinstance(value, dict):
        items = list(value.items())
        summarized = {
            str(key): _summarize_json(
                item,
                max_string_chars=max_string_chars,
                max_items=max_items,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
            for key, item in items[:max_items]
        }
        if len(items) > max_items:
            summarized["__truncated__"] = {"omitted_items": len(items) - max_items, "total_items": len(items)}
        return summarized
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        summarized_items = [
            _summarize_json(
                item,
                max_string_chars=max_string_chars,
                max_items=max_items,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
            for item in items[:max_items]
        ]
        if len(items) > max_items:
            summarized_items.append({"__truncated__": {"omitted_items": len(items) - max_items, "total_items": len(items)}})
        return summarized_items
    if isinstance(value, str):
        return _summarize_string(value, max_chars=max_string_chars)
    return value


def _summarize_string(value: str, *, max_chars: int) -> str | dict[str, Any]:
    if len(value) <= max_chars:
        return value
    preview = value[: max(max_chars, 0)].rstrip()
    return {
        "type": "string",
        "chars": len(value),
        "lines": value.count("\n") + 1,
        "preview": f"{preview}…",
    }


def _shape_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"type": "object", "keys": list(value.keys()), "items": len(value)}
    if isinstance(value, (list, tuple, set)):
        return {"type": "array", "items": len(value)}
    if isinstance(value, str):
        return {"type": "string", "chars": len(value), "lines": value.count("\n") + 1}
    return {"type": type(value).__name__}


_BULLET_FIELD_PATTERN = re.compile(r"^\s*[-*]\s*([^:\n]{1,120})\s*:\s*(.*?)\s*$")


def _parse_answer_fields(text: str) -> dict[str, Any]:
    """Extract user-facing fields from common answer formats.

    This is intentionally generic: it supports the two formats LLMs commonly
    emit in notebooks without embedding any tutorial-specific keys:

    - Markdown bullets: ``- key: value``
    - A top-level JSON object: ``{"key": value}``

    Keys are normalized the same way in both paths so framework differences
    (for example Markdown from one runner and JSON text from another) do not
    make ``fields`` disappear from the presentation view.
    """

    fields: dict[str, Any] = {}
    fields.update(_parse_json_object_fields(text))

    for line in text.splitlines():
        match = _BULLET_FIELD_PATTERN.match(line)
        if not match:
            continue
        key = _normalize_field_key(match.group(1))
        if not key:
            continue
        fields[key] = _coerce_field_value(match.group(2))
    return fields


def _parse_json_object_fields(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if not cleaned:
        return {}

    if cleaned.startswith("```"):
        cleaned = _strip_markdown_code_fence(cleaned)

    obj = _loads_json_object(cleaned)
    if obj is None:
        obj = _loads_first_json_object(cleaned)
    if not isinstance(obj, Mapping):
        return {}

    return {
        key: _to_jsonable(value)
        for raw_key, value in obj.items()
        if (key := _normalize_field_key(str(raw_key)))
    }


def _strip_markdown_code_fence(text: str) -> str:
    lines = text.strip().splitlines()
    if len(lines) >= 2 and lines[0].lstrip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text.strip()


def _loads_json_object(text: str) -> Any | None:
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _loads_first_json_object(text: str) -> Any | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except Exception:
            continue
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _normalize_field_key(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().strip("`*_ ")).lower()


def _coerce_field_value(value: str) -> Any:
    cleaned = value.strip().strip("`*_ ")
    if cleaned == "":
        return ""
    lowered = cleaned.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None
    try:
        if re.fullmatch(r"[-+]?\d+", cleaned):
            return int(cleaned)
        if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", cleaned):
            return float(cleaned)
    except Exception:
        return cleaned
    return cleaned

def _discover_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.name in {"notebooks", "tutorials"}:
        return current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src").exists():
            return candidate
    return current


def _to_jsonable(value: Any) -> Any:
    """Normalize supported public values without depending on provider types.

    Precedence is intentional and forms the structural serialization contract:
    Pydantic-style ``model_dump`` objects, ``to_dict`` objects, dataclasses,
    mappings, and finally common containers. Unknown leaf values are left to
    ``json.dumps(..., default=str)`` by the presentation layer.
    """
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return _to_jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    return value


def _mask_sensitive(value: Any, *, parent_key: str) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _mask_sensitive(item, parent_key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mask_sensitive(item, parent_key=parent_key) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_sensitive(item, parent_key=parent_key) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if not isinstance(value, str):
        return value

    key = parent_key or ""
    if _DEFAULT_SENSITIVE_KEY_PATTERN.search(key):
        return _mask_string(value, keep_start=4, keep_end=4)
    if _DEFAULT_IDENTIFIER_KEY_PATTERN.search(key):
        return _mask_string(value, keep_start=6, keep_end=4)
    if value.startswith("arn:aws:"):
        return _mask_string(value, keep_start=18, keep_end=12)
    return value


def _mask_string(value: str, *, keep_start: int = 4, keep_end: int = 4) -> str:
    if value == "SET":
        return value
    if not value:
        return value
    if len(value) <= keep_start:
        return "*" * min(len(value), 8)
    if len(value) <= keep_start + keep_end + 3:
        return f"{value[:keep_start]}..."
    return f"{value[:keep_start]}...{value[-keep_end:]}"
