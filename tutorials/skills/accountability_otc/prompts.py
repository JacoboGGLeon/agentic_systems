"""Prompts and deterministic plan helpers for the Accountability OTC skill."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic_systems import expect

ACCOUNTABILITY_FREE_SQL_CATALOG_PROMPT = """
Usa free_sql con query_id="otc_exposure_by_currency".
Devuelve la exposición OTC por moneda con máximo 10 filas y resume el hallazgo principal en español.
""".strip()

ACCOUNTABILITY_FREE_SQL_SQL = """
SELECT
  currency_id,
  COUNT(*) AS operaciones
FROM "mx_master"."t_mrdc_mthly_invty_otc"
WHERE load_date = (SELECT MAX(load_date) FROM "mx_master"."t_mrdc_mthly_invty_otc")
GROUP BY currency_id
ORDER BY operaciones DESC
LIMIT 10
""".strip()

ACCOUNTABILITY_FREE_SQL_SQL_PROMPT = f"""
Usa free_sql con SQL explícito.
Pasa exactamente este SQL en el argumento sql; no uses query_id ni nl2sql.

{ACCOUNTABILITY_FREE_SQL_SQL}

Resume el resultado en español.
""".strip()

ACCOUNTABILITY_NL2SQL_PROMPT = """
Usa nl2sql para responder esta pregunta de negocio:
¿Cuál es el MTM por clase de activo?
Devuelve máximo 10 filas y resume el hallazgo principal en español.
""".strip()

ACCOUNTABILITY_USER_PROMPT = """Compara la exposición OTC por moneda contra el MTM por clase de activo.
Usa datos reales de Athena y explícame el hallazgo principal en español.
"""

ACCOUNTABILITY_AGENT_INSTRUCTIONS = """
Eres un agente de accountability OTC.
Usa sólo la evidencia que devuelven las tools.

Tools disponibles:
- free_sql: úsala cuando el usuario pida una consulta conocida por query_id o entregue SQL explícito validado.
- nl2sql: úsala cuando el usuario haga una pregunta de negocio en lenguaje natural; usa un planner agent interno con catálogo semántico; no usa query_id.

Reglas:
- Si el usuario menciona un query_id, usa free_sql(query_id=...).
- Si el usuario entrega SQL explícito, usa free_sql(sql=...).
- Si el usuario hace una pregunta natural sin SQL ni query_id, usa nl2sql(question=...).
- No inventes datos. Resume sólo lo que devuelven las tools.
- No incluyas SQL exacto en tu respuesta final; la vista humana lo mostrará desde la evidencia de tools.
- Responde en español con: consulta usada, filas devueltas y hallazgo principal.
""".strip()

ACCOUNTABILITY_EXPECTED_TOOLS = expect.all_of("free_sql", "nl2sql")
ACCOUNTABILITY_EXPECTED_FREE_SQL = expect.exactly("free_sql")
ACCOUNTABILITY_EXPECTED_NL2SQL = expect.exactly("nl2sql")
ACCOUNTABILITY_EXPECTED_TOOLS_ANY = expect.any_of("free_sql", "nl2sql")

ACCOUNTABILITY_AGENT_EXAMPLES = [
    {
        "id": "free_sql_catalog",
        "title": "free_sql con query_id de catálogo",
        "user_prompt": ACCOUNTABILITY_FREE_SQL_CATALOG_PROMPT,
        "expected_tools": ACCOUNTABILITY_EXPECTED_FREE_SQL,
    },
    {
        "id": "free_sql_sql",
        "title": "free_sql con SQL explícito",
        "user_prompt": ACCOUNTABILITY_FREE_SQL_SQL_PROMPT,
        "expected_tools": ACCOUNTABILITY_EXPECTED_FREE_SQL,
    },
    {
        "id": "nl2sql",
        "title": "nl2sql con pregunta natural",
        "user_prompt": ACCOUNTABILITY_NL2SQL_PROMPT,
        "expected_tools": ACCOUNTABILITY_EXPECTED_NL2SQL,
    },
]

ACCOUNTABILITY_TOOL_EXAMPLES = [
    {
        "id": "free_sql_catalog",
        "title": "free_sql con query_id de catálogo",
        "tool": "free_sql",
        "input": {"query_id": "otc_exposure_by_currency", "load_date": "", "limit": 10},
        "expected_tools": ACCOUNTABILITY_EXPECTED_FREE_SQL,
    },
    {
        "id": "free_sql_sql",
        "title": "free_sql con SQL explícito",
        "tool": "free_sql",
        "input": {"sql": ACCOUNTABILITY_FREE_SQL_SQL, "limit": 10},
        "expected_tools": ACCOUNTABILITY_EXPECTED_FREE_SQL,
    },
    {
        "id": "nl2sql",
        "title": "nl2sql con pregunta natural",
        "tool": "nl2sql",
        "input": {"question": "mtm por clase de activo", "load_date": "", "limit": 10},
        "expected_tools": ACCOUNTABILITY_EXPECTED_NL2SQL,
    },
]


@dataclass(frozen=True)
class ToolPlanStep:
    """One deterministic tool call derived from a natural-language prompt."""

    tool: str
    input: dict[str, Any]


@dataclass(frozen=True)
class AccountabilityPlan:
    """Small plan used to compare direct tools and agent frameworks fairly."""

    user_prompt: str
    steps: list[ToolPlanStep]

    def input_for(self, tool_name: str) -> dict[str, Any]:
        for step in self.steps:
            if step.tool == tool_name:
                return dict(step.input)
        raise KeyError(f"Tool {tool_name!r} is not in this accountability plan.")

    def as_tool_calls(self) -> list[dict[str, Any]]:
        return [{"tool": step.tool, "input": dict(step.input)} for step in self.steps]


def build_accountability_plan(user_prompt: str, *, load_date: str = "", limit: int = 10) -> AccountabilityPlan:
    """Build the notebook's expected tool plan from a natural user prompt."""

    return AccountabilityPlan(
        user_prompt=user_prompt,
        steps=[
            ToolPlanStep(tool="free_sql", input={"query_id": "otc_exposure_by_currency", "load_date": load_date, "limit": limit}),
            ToolPlanStep(tool="nl2sql", input={"question": "mtm por clase de activo", "load_date": load_date, "limit": limit}),
        ],
    )


def free_sql_example(settings: Any, *, limit: int = 10) -> dict[str, Any]:
    """Return a safe explicit-SQL example for optional direct-tool cells."""

    sql = f"""
SELECT
  currency_id,
  COUNT(*) AS operaciones
FROM "{settings.database}"."{settings.table}"
WHERE load_date = (SELECT MAX(load_date) FROM "{settings.database}"."{settings.table}")
GROUP BY currency_id
ORDER BY operaciones DESC
LIMIT {limit}
""".strip()
    return {"sql": sql, "limit": limit}
