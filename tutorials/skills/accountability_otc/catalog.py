"""Catalog and semantic layer for the Accountability OTC tutorials.

``free_sql`` can execute curated query IDs. ``nl2sql`` does not reuse those
query IDs. The public ``nl2sql`` tool uses an internal planner agent that reads
this semantic catalog and returns a constrained JSON plan; this module owns the
validated SQL plan and rendering primitives.

``compile_nl2sql_plan`` remains as a deterministic test/smoke helper, not the
default production route.
"""


from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def load_catalog() -> dict[str, Any]:
    resource = Path(__file__).resolve().parent / "assets" / "otc_catalog.json"
    return json.loads(resource.read_text(encoding="utf-8"))


QUERY_CATALOG: dict[str, dict[str, str]] = {
    "otc_nominal_by_product_type": {
        "title": "Nominal por tipo de producto",
        "description": "Agrupa operaciones OTC por product_type y suma nominal_amount.",
        "sql": """
SELECT
  product_type,
  COUNT(*) AS operaciones,
  SUM(nominal_amount) AS total_nominal
FROM {table}
WHERE load_date = DATE '{load_date}'
GROUP BY product_type
ORDER BY total_nominal DESC
LIMIT {limit}
""".strip(),
    },
    "otc_mtm_by_asset_class": {
        "title": "MTM por clase de activo",
        "description": "Agrupa operaciones OTC por financial_asset_class_type y suma market_valuation_amount.",
        "sql": """
SELECT
  financial_asset_class_type,
  COUNT(*) AS operaciones,
  SUM(market_valuation_amount) AS total_mtm
FROM {table}
WHERE load_date = DATE '{load_date}'
GROUP BY financial_asset_class_type
ORDER BY ABS(total_mtm) DESC
LIMIT {limit}
""".strip(),
    },
    "otc_exposure_by_currency": {
        "title": "Exposición por moneda",
        "description": "Agrupa operaciones OTC por currency_id y suma nominal_amount y market_valuation_amount.",
        "sql": """
SELECT
  currency_id,
  SUM(nominal_amount) AS total_nominal,
  SUM(market_valuation_amount) AS total_mtm
FROM {table}
WHERE load_date = DATE '{load_date}'
GROUP BY currency_id
ORDER BY total_nominal DESC
LIMIT {limit}
""".strip(),
    },
}

QUERY_ALIASES: dict[str, str] = {
    "nominal_by_product_type": "otc_nominal_by_product_type",
    "mtm_by_asset_class": "otc_mtm_by_asset_class",
    "exposure_by_currency": "otc_exposure_by_currency",
}

QUERY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "otc_nominal_by_product_type": ("nominal por tipo de producto", "nominal producto", "product_type", "tipo de producto"),
    "otc_mtm_by_asset_class": ("mtm por clase de activo", "mtm asset class", "clase de activo", "financial_asset_class_type"),
    "otc_exposure_by_currency": ("exposición por moneda", "exposure by currency", "moneda", "currency", "currency_id", "nominal por moneda"),
}


@dataclass(frozen=True)
class SemanticSQLPlan:
    """Deterministic plan produced before rendering SQL."""

    question: str
    dimensions: tuple[str, ...]
    metrics: tuple[str, ...]
    include_count: bool
    order_by: str
    limit: int
    load_date: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "dimensions": list(self.dimensions),
            "metrics": list(self.metrics),
            "include_count": self.include_count,
            "order_by": self.order_by,
            "limit": self.limit,
            "load_date": self.load_date,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


def query_catalog_rows() -> list[dict[str, str]]:
    """Return the query catalog as notebook-friendly rows."""

    return [
        {"query_id": query_id, "title": spec["title"], "description": spec["description"]}
        for query_id, spec in QUERY_CATALOG.items()
    ]


def resolve_query_id(query_id: str) -> str:
    key = str(query_id or "").strip()
    if not key:
        raise ValueError("query_id is required when sql is empty.")
    key = QUERY_ALIASES.get(key, key)
    if key not in QUERY_CATALOG:
        available = ", ".join(sorted(QUERY_CATALOG))
        raise ValueError(f"Unknown query_id {query_id!r}. Available: {available}")
    return key


def normalize_text(text: str) -> str:
    raw = str(text or "").lower()
    decomposed = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_accents.replace("_", " ").split())


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", normalize_text(text)) if len(token) > 1}


def contains_token(text: str, token: str) -> bool:
    normalized_token = normalize_text(token)
    if not normalized_token:
        return False
    normalized_text = normalize_text(text)
    if " " in normalized_token:
        return normalized_token in normalized_text
    return re.search(rf"(^|\W){re.escape(normalized_token)}($|\W)", normalized_text) is not None


def match_query_id(question: str) -> str | None:
    """Legacy helper for catalog lookup examples.

    ``nl2sql`` intentionally does not use this helper. It remains available for
    query catalog diagnostics and backwards-compatible tests.
    """

    text = normalize_text(question)
    for query_id, keywords in QUERY_KEYWORDS.items():
        if any(contains_token(text, keyword) for keyword in keywords):
            return query_id
    return None


def _semantic_columns(catalog: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [dict(column) for column in catalog.get("columns", []) if column.get("role") == role]


def _candidate_terms(column: dict[str, Any]) -> list[str]:
    return [str(column.get("name", "")), *[str(item) for item in column.get("aliases", [])], str(column.get("description", ""))]


def _score_candidate(question: str, candidate: dict[str, Any], *, role: str) -> tuple[float, list[str]]:
    text = normalize_text(question)
    q_tokens = _tokens(text)
    score = 0.0
    evidence: list[str] = []

    name = normalize_text(candidate.get("name", ""))
    if name and contains_token(text, name):
        score += 6.0
        evidence.append(f"name:{candidate['name']}")

    for alias in candidate.get("aliases", []):
        alias_text = normalize_text(alias)
        if not alias_text:
            continue
        if alias_text in text:
            score += 7.0 if " " in alias_text else 5.0
            evidence.append(f"alias:{alias}")
            continue
        alias_tokens = _tokens(alias_text)
        overlap = q_tokens & alias_tokens
        if alias_tokens and overlap:
            score += len(overlap) / len(alias_tokens) * 2.0
            evidence.append(f"alias_tokens:{alias}")

    description_tokens = _tokens(candidate.get("description", ""))
    if description_tokens:
        overlap = q_tokens & description_tokens
        if overlap:
            score += min(1.5, 0.35 * len(overlap))

    if role == "dimension":
        for term in [candidate.get("name", ""), *candidate.get("aliases", [])]:
            normalized_term = normalize_text(term)
            if normalized_term and (f"por {normalized_term}" in text or f"by {normalized_term}" in text):
                score += 4.0
                evidence.append(f"group_by:{term}")
                break

    return score, evidence


def pick_column(question: str, role: str, catalog: dict[str, Any]) -> str | None:
    ranked = rank_columns(question, role, catalog)
    return ranked[0]["name"] if ranked else None


def rank_columns(question: str, role: str, catalog: dict[str, Any], *, min_score: float = 1.0) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for column in _semantic_columns(catalog, role):
        score, evidence = _score_candidate(question, column, role=role)
        if score >= min_score:
            ranked.append({"name": column["name"], "score": round(score, 3), "evidence": evidence})
    return sorted(ranked, key=lambda item: (-float(item["score"]), str(item["name"])))


def _concept_metrics(question: str, catalog: dict[str, Any]) -> list[str]:
    text = normalize_text(question)
    metrics: list[str] = []
    for concept in catalog.get("semantic_layer", {}).get("concepts", []):
        aliases = [concept.get("name", ""), *concept.get("aliases", [])]
        if any(contains_token(text, alias) for alias in aliases):
            metrics.extend(str(metric) for metric in concept.get("metrics", []))
    return metrics


def _unique_keep_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def compile_nl2sql_plan(
    question: str,
    *,
    catalog: dict[str, Any] | None = None,
    load_date: str,
    limit: int,
) -> SemanticSQLPlan:
    """Compile a natural-language OTC question into a SQL plan.

    This is a semantic catalog compiler, not a query-id router. It brute-force
    scores every metric and dimension in the catalog, then renders only allowed
    columns. That keeps the tutorial honest while leaving a clean seam for a
    future retrieval-agent implementation.
    """

    catalog = catalog or load_catalog()
    semantic = catalog.get("semantic_layer", {})
    dimension_rank = rank_columns(question, "dimension", catalog)
    metric_rank = rank_columns(question, "metric", catalog)

    dimensions = [item["name"] for item in dimension_rank[:1]]
    if not dimensions:
        dimensions = [str(semantic.get("default_dimension") or catalog.get("nl2sql", {}).get("default_dimension") or "product_type")]

    metrics = [item["name"] for item in metric_rank]
    metrics.extend(_concept_metrics(question, catalog))
    if not metrics:
        metrics = [str(semantic.get("default_metric") or catalog.get("nl2sql", {}).get("default_metric") or "nominal_amount")]
    metrics_tuple = _unique_keep_order(metrics)

    metric_specs = semantic.get("metrics", {})
    first_metric = metrics_tuple[0]
    output_alias = metric_specs.get(first_metric, {}).get("output_alias") or catalog.get("nl2sql", {}).get("metric_aliases", {}).get(first_metric, f"total_{first_metric}")
    order_mode = str(metric_specs.get(first_metric, {}).get("default_order", "DESC")).upper()
    order_by = f"ABS({output_alias}) DESC" if order_mode == "ABS_DESC" else f"{output_alias} DESC"

    include_count = bool(semantic.get("include_count_by_default", True)) or contains_token(question, "operaciones") or contains_token(question, "conteo")
    evidence = {
        "dimension_candidates": dimension_rank,
        "metric_candidates": metric_rank,
        "concept_metrics": _concept_metrics(question, catalog),
        "catalog_version": catalog.get("version"),
    }
    best_scores = [float(item["score"]) for item in [*dimension_rank[:1], *metric_rank[:1]]]
    confidence = min(1.0, sum(best_scores) / 16.0) if best_scores else 0.25

    return SemanticSQLPlan(
        question=str(question or "").strip(),
        dimensions=tuple(dimensions),
        metrics=metrics_tuple,
        include_count=include_count,
        order_by=order_by,
        limit=limit,
        load_date=load_date,
        confidence=round(confidence, 3),
        evidence=evidence,
    )


def render_semantic_sql(plan: SemanticSQLPlan, *, table_ref: str, catalog: dict[str, Any] | None = None) -> str:
    catalog = catalog or load_catalog()
    semantic = catalog.get("semantic_layer", {})
    metric_specs = semantic.get("metrics", {})
    count_alias = str(semantic.get("count_alias", "operaciones"))
    allowed_columns = {column["name"] for column in catalog.get("columns", [])}

    for column in [*plan.dimensions, *plan.metrics]:
        if column not in allowed_columns:
            raise ValueError(f"Column {column!r} is not declared in the semantic catalog.")

    select_lines = [f"  {dimension}" for dimension in plan.dimensions]
    if plan.include_count:
        select_lines.append(f"  COUNT(*) AS {count_alias}")
    for metric in plan.metrics:
        spec = metric_specs.get(metric, {})
        aggregate = str(spec.get("aggregate", "SUM")).upper()
        alias = spec.get("output_alias") or catalog.get("nl2sql", {}).get("metric_aliases", {}).get(metric, f"total_{metric}")
        if aggregate not in {"SUM", "AVG", "MIN", "MAX", "COUNT"}:
            raise ValueError(f"Unsupported aggregate {aggregate!r} for metric {metric!r}.")
        select_lines.append(f"  {aggregate}({metric}) AS {alias}")

    select_clause = ",\n".join(select_lines)
    group_by = ", ".join(plan.dimensions)
    return f"""
SELECT
{select_clause}
FROM {table_ref}
WHERE load_date = DATE '{plan.load_date}'
GROUP BY {group_by}
ORDER BY {plan.order_by}
LIMIT {plan.limit}
""".strip()
