"""Agent-powered NL2SQL planner for the Accountability OTC tutorials.

The public ``nl2sql`` tool is intentionally an *agent-tool*: the outer agent
may call ``nl2sql``, and this tool then asks a Bedrock language model to build
an auditable SQL plan from the semantic catalog. The model never gets to run
arbitrary SQL directly. It returns a constrained JSON plan; local code validates
that plan against the catalog and renders safe read-only SQL.

Current retrieval strategy
--------------------------
For this release, the planner reads the full semantic catalog and sends the
relevant schema to the model in one prompt. That is a deliberate brute-force
retrieval baseline. The seam is explicit: a future version can replace
``catalog_prompt_payload`` with tool-based retrieval without changing the
public ``nl2sql(question=...)`` API.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from agentic_systems import BedrockRuntimeClient

from .catalog import SemanticSQLPlan, compile_nl2sql_plan, load_catalog
from .config import AccountabilitySettings


@dataclass(frozen=True)
class NL2SQLPlanningResult:
    """Validated planning result returned by an NL2SQL planner."""

    plan: SemanticSQLPlan
    meta: dict[str, Any] = field(default_factory=dict)


class NL2SQLPlanner(Protocol):
    """Small protocol implemented by agent and test planners."""

    def plan(
        self,
        question: str,
        *,
        catalog: dict[str, Any],
        load_date: str,
        limit: int,
    ) -> NL2SQLPlanningResult:
        """Return a validated semantic SQL plan."""


@dataclass(frozen=True)
class StaticSemanticNL2SQLPlanner:
    """Offline planner used only for tests and smoke demos.

    This preserves deterministic local tests without making the production
    ``nl2sql`` path pretend to be agentic. Runtime code uses
    :class:`BedrockNL2SQLPlanner` by default.
    """

    route: str = "nl2sql_static_semantic_test_planner"

    def plan(
        self,
        question: str,
        *,
        catalog: dict[str, Any],
        load_date: str,
        limit: int,
    ) -> NL2SQLPlanningResult:
        semantic_plan = compile_nl2sql_plan(question, catalog=catalog, load_date=load_date, limit=limit)
        return NL2SQLPlanningResult(
            plan=semantic_plan,
            meta={
                "planner": self.route,
                "agentic": False,
                "catalog_version": catalog.get("version"),
            },
        )


@dataclass(frozen=True)
class BedrockNL2SQLPlanner:
    """Bedrock-backed planner used inside the public ``nl2sql`` tool."""

    settings: AccountabilitySettings = field(default_factory=AccountabilitySettings)
    model_id: str | None = None
    region: str | None = None
    max_tokens: int = 900
    temperature: float = 0.0

    def plan(
        self,
        question: str,
        *,
        catalog: dict[str, Any],
        load_date: str,
        limit: int,
    ) -> NL2SQLPlanningResult:
        selected_model = self.model_id or self.settings.model_id
        selected_region = self.region or self.settings.region
        client = BedrockRuntimeClient(
            model=selected_model,
            region=selected_region,
            defaults={"max_tokens": self.max_tokens, "temperature": self.temperature},
        )
        prompt = build_nl2sql_agent_prompt(
            question=question,
            catalog=catalog,
            load_date=load_date,
            limit=limit,
        )
        result = client.complete(
            prompt,
            instructions=NL2SQL_AGENT_INSTRUCTIONS,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            mode="nl2sql_agent_planner",
            data={"kind": "nl2sql_agent_plan", "catalog_version": catalog.get("version")},
        )
        payload = extract_json_object(result.text)
        semantic_plan = semantic_plan_from_agent_payload(
            payload,
            question=question,
            catalog=catalog,
            load_date=load_date,
            limit=limit,
        )
        return NL2SQLPlanningResult(
            plan=semantic_plan,
            meta={
                "planner": "bedrock_nl2sql_agent",
                "agentic": True,
                "model": selected_model,
                "region": selected_region,
                "usage": result.usage,
                "raw_text": result.text,
                "raw_json": payload,
                "catalog_version": catalog.get("version"),
            },
        )


NL2SQL_AGENT_INSTRUCTIONS = """
Eres un agente especialista en compilar preguntas de negocio OTC a un plan SQL seguro.
No escribes SQL libre. Devuelves únicamente JSON válido siguiendo el contrato solicitado.
Usa sólo columnas declaradas en el catálogo. No inventes tablas, columnas, filtros ni métricas.
""".strip()


def catalog_prompt_payload(catalog: dict[str, Any]) -> dict[str, Any]:
    """Return the semantic catalog slice that is safe and useful for planning."""

    semantic = catalog.get("semantic_layer", {})
    return {
        "version": catalog.get("version"),
        "date_column": catalog.get("date_column", "load_date"),
        "columns": [
            {
                "name": column.get("name"),
                "role": column.get("role"),
                "data_type": column.get("data_type"),
                "aliases": column.get("aliases", []),
                "description": column.get("description", ""),
            }
            for column in catalog.get("columns", [])
        ],
        "semantic_layer": {
            "default_dimension": semantic.get("default_dimension"),
            "default_metric": semantic.get("default_metric"),
            "include_count_by_default": semantic.get("include_count_by_default", True),
            "count_alias": semantic.get("count_alias", "operaciones"),
            "metrics": semantic.get("metrics", {}),
            "concepts": semantic.get("concepts", []),
        },
        "allowed_plan_contract": {
            "dimensions": "list[str] de columnas con role=dimension",
            "metrics": "list[str] de columnas con role=metric",
            "include_count": "bool",
            "order": {
                "metric": "una métrica elegida",
                "mode": "DESC | ASC | ABS_DESC | ABS_ASC",
            },
            "confidence": "float entre 0 y 1",
            "reason": "explicación breve",
        },
    }


def build_nl2sql_agent_prompt(
    *,
    question: str,
    catalog: dict[str, Any] | None = None,
    load_date: str,
    limit: int,
) -> str:
    """Build the single brute-force catalog prompt used by the agent-tool."""

    resolved_catalog = catalog or load_catalog()
    payload = catalog_prompt_payload(resolved_catalog)
    return f"""
Compila la pregunta de negocio OTC a un plan JSON validable.

Reglas obligatorias:
- Devuelve sólo JSON. Sin Markdown. Sin texto adicional.
- No devuelvas SQL.
- Usa únicamente columnas que aparecen en catalog.columns.
- dimensions debe contener columnas con role="dimension".
- metrics debe contener columnas con role="metric".
- Si el usuario pregunta "por X", normalmente X debe ser una dimensión.
- Si el usuario menciona MTM, usa market_valuation_amount.
- Si el usuario menciona nominal/exposición/notional, usa nominal_amount.
- Si el usuario menciona contabilidad/saldo contable/GL amount, usa gl_account_amount.
- Si la pregunta pide exposición/riesgo/concentración, puedes incluir nominal_amount y market_valuation_amount.
- include_count debe ser true si ayuda a auditar número de operaciones.
- order.metric debe ser una de las metrics elegidas.
- order.mode debe ser ABS_DESC para métricas que pueden ser negativas cuando la pregunta pide mayor impacto/MTM/valor absoluto.
- No agregues filtros salvo load_date; el runtime lo aplicará fuera de tu JSON.

Contrato exacto de salida:
{{
  "dimensions": ["..."],
  "metrics": ["..."],
  "include_count": true,
  "order": {{"metric": "...", "mode": "DESC"}},
  "confidence": 0.0,
  "reason": "..."
}}

Parámetros runtime:
{json.dumps({"load_date": load_date, "limit": limit}, ensure_ascii=False, indent=2)}

Catálogo semántico disponible:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Pregunta del usuario:
{question}
""".strip()


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a model response."""

    raw = str(text or "").strip()
    if not raw:
        raise ValueError("NL2SQL agent returned an empty response.")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise ValueError(f"NL2SQL agent did not return JSON: {raw[:300]}") from None
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("NL2SQL agent JSON must be an object.")
    return parsed


def semantic_plan_from_agent_payload(
    payload: dict[str, Any],
    *,
    question: str,
    catalog: dict[str, Any],
    load_date: str,
    limit: int,
) -> SemanticSQLPlan:
    """Validate an agent JSON plan and convert it to ``SemanticSQLPlan``."""

    dimensions = _validate_columns(payload.get("dimensions"), role="dimension", catalog=catalog, field_name="dimensions")
    metrics = _validate_columns(payload.get("metrics"), role="metric", catalog=catalog, field_name="metrics")
    if not dimensions:
        dimensions = (str(catalog.get("semantic_layer", {}).get("default_dimension") or "product_type"),)
    if not metrics:
        metrics = (str(catalog.get("semantic_layer", {}).get("default_metric") or "nominal_amount"),)
    _assert_columns_have_role(dimensions, role="dimension", catalog=catalog)
    _assert_columns_have_role(metrics, role="metric", catalog=catalog)

    include_count = bool(payload.get("include_count", True))
    order_by = _validated_order_by(payload.get("order"), metrics=metrics, catalog=catalog)
    confidence = _confidence(payload.get("confidence"))
    evidence = {
        "planner": "bedrock_nl2sql_agent",
        "catalog_version": catalog.get("version"),
        "agent_reason": str(payload.get("reason", "")).strip(),
        "raw_agent_plan": payload,
    }
    return SemanticSQLPlan(
        question=str(question or "").strip(),
        dimensions=dimensions,
        metrics=metrics,
        include_count=include_count,
        order_by=order_by,
        limit=int(limit),
        load_date=str(load_date),
        confidence=confidence,
        evidence=evidence,
    )


def _validate_columns(value: Any, *, role: str, catalog: dict[str, Any], field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"Agent field {field_name!r} must be a list.")
    names = tuple(str(item).strip() for item in value if str(item).strip())
    _assert_columns_have_role(names, role=role, catalog=catalog)
    return names


def _columns_by_role(catalog: dict[str, Any], role: str) -> set[str]:
    return {str(column.get("name")) for column in catalog.get("columns", []) if column.get("role") == role}


def _assert_columns_have_role(names: tuple[str, ...], *, role: str, catalog: dict[str, Any]) -> None:
    allowed = _columns_by_role(catalog, role)
    unknown = [name for name in names if name not in allowed]
    if unknown:
        raise ValueError(f"Column(s) {unknown} are not allowed as {role}. Allowed: {sorted(allowed)}")


def _metric_output_alias(metric: str, catalog: dict[str, Any]) -> str:
    semantic = catalog.get("semantic_layer", {})
    return str(
        semantic.get("metrics", {}).get(metric, {}).get("output_alias")
        or catalog.get("nl2sql", {}).get("metric_aliases", {}).get(metric)
        or f"total_{metric}"
    )


def _validated_order_by(order: Any, *, metrics: tuple[str, ...], catalog: dict[str, Any]) -> str:
    first_metric = metrics[0]
    metric = first_metric
    mode = str(catalog.get("semantic_layer", {}).get("metrics", {}).get(first_metric, {}).get("default_order", "DESC")).upper()
    if isinstance(order, dict):
        requested_metric = str(order.get("metric") or first_metric).strip()
        if requested_metric in metrics:
            metric = requested_metric
        requested_mode = str(order.get("mode") or mode).strip().upper()
        if requested_mode in {"DESC", "ASC", "ABS_DESC", "ABS_ASC"}:
            mode = requested_mode
    alias = _metric_output_alias(metric, catalog)
    if mode == "ABS_DESC":
        return f"ABS({alias}) DESC"
    if mode == "ABS_ASC":
        return f"ABS({alias}) ASC"
    if mode == "ASC":
        return f"{alias} ASC"
    return f"{alias} DESC"


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.5
    return round(min(1.0, max(0.0, number)), 3)
