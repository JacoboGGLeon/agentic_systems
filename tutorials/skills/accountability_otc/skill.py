"""External Accountability OTC skill for Agentic Systems tutorials."""

from __future__ import annotations

from typing import Any

from agentic_systems import Skill, tool

from .athena import Reader, StaticAthenaReader
from .catalog import query_catalog_rows
from .config import AccountabilitySettings
from .prompts import (
    ACCOUNTABILITY_AGENT_EXAMPLES,
    ACCOUNTABILITY_AGENT_INSTRUCTIONS,
    ACCOUNTABILITY_EXPECTED_TOOLS,
    ACCOUNTABILITY_TOOL_EXAMPLES,
    ACCOUNTABILITY_USER_PROMPT,
    AccountabilityPlan,
    build_accountability_plan,
    free_sql_example,
)
from .nl2sql_agent import BedrockNL2SQLPlanner, NL2SQLPlanner, StaticSemanticNL2SQLPlanner
from .runtime import run_free_sql, run_nl2sql
from .contracts import ACCOUNTABILITY_SKILL_AGENT_SPEC, ACCOUNTABILITY_SKILL_CONTRACTS


class AccountabilityOTCSkill(Skill):
    """Reusable OTC accountability skill with two visible tools.

    The skill intentionally exposes only two tools: ``free_sql`` and ``nl2sql``.
    Known business queries live in the catalog, not as separate tools.
    """

    def __init__(
        self,
        *,
        settings: AccountabilitySettings | None = None,
        reader: Reader | None = None,
        nl2sql_planner: NL2SQLPlanner | None = None,
        name: str = "accountability_otc",
    ) -> None:
        self.settings = settings or AccountabilitySettings()
        self.reader = reader
        super().__init__(
            name=name,
            version="0.1.0",
            description="Accountability OTC: SQL seguro y NL2SQL agent-tool para Athena.",
            tools=make_tools(settings=self.settings, reader=reader, nl2sql_planner=nl2sql_planner),
            prompts={
                "instructions": ACCOUNTABILITY_AGENT_INSTRUCTIONS,
                "user_prompt": ACCOUNTABILITY_USER_PROMPT,
                "agent_examples": ACCOUNTABILITY_AGENT_EXAMPLES,
                "tool_examples": ACCOUNTABILITY_TOOL_EXAMPLES,
            },
            contracts={
                "expected_tools": ACCOUNTABILITY_EXPECTED_TOOLS,
                "agent": ACCOUNTABILITY_SKILL_AGENT_SPEC.contract.model_dump(mode="json"),
                "contract_policy_specs": {key: spec.to_dict() for key, spec in ACCOUNTABILITY_SKILL_CONTRACTS.items()},
            },
            policy={
                "agent": ACCOUNTABILITY_SKILL_AGENT_SPEC.policy.model_dump(mode="json"),
                "temperature": 0.0,
                "max_turns": 6,
                "max_tool_calls": 1,
            },
            metadata={
                "kind": "external_tutorial_skill",
                "domain": "otc_accountability",
                "query_catalog": query_catalog_rows(),
                "database": self.settings.database,
                "table": self.settings.table,
                "workgroup": self.settings.workgroup,
            },
        )

    @property
    def expected_tools(self) -> dict[str, object]:
        return dict(ACCOUNTABILITY_EXPECTED_TOOLS)

    def plan(self, user_prompt: str | None = None, *, load_date: str = "", limit: int = 10) -> AccountabilityPlan:
        return build_accountability_plan(user_prompt or ACCOUNTABILITY_USER_PROMPT, load_date=load_date, limit=limit)

    def catalog_rows(self) -> list[dict[str, str]]:
        return query_catalog_rows()

    def agent_examples(self) -> list[dict[str, Any]]:
        return [dict(item) for item in ACCOUNTABILITY_AGENT_EXAMPLES]

    def tool_examples(self) -> list[dict[str, Any]]:
        return [dict(item) for item in ACCOUNTABILITY_TOOL_EXAMPLES]

    def free_sql_example(self, *, limit: int = 10) -> dict[str, Any]:
        return free_sql_example(self.settings, limit=limit)

    def smoke_reader(self) -> StaticAthenaReader:
        """Return a tiny deterministic reader for tests or offline demos."""

        return StaticAthenaReader(
            {
                "group by currency_id": [{"currency_id": "MXN", "total_nominal": 100, "total_mtm": 7}],
                "group by financial_asset_class_type": [{"financial_asset_class_type": "EQD", "operaciones": 1, "total_mtm": 7}],
            }
        )


def make_tools(
    *,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
    nl2sql_planner: NL2SQLPlanner | None = None,
):
    """Create the two public tools exposed by the Accountability OTC skill."""

    resolved_settings = settings or AccountabilitySettings()

    @tool
    def free_sql(sql: str = "", query_id: str = "", load_date: str = "", limit: int = 50) -> dict:
        """Ejecuta SQL libre validado o una consulta conocida por query_id."""

        return run_free_sql(sql=sql, query_id=query_id, load_date=load_date, limit=limit, settings=resolved_settings, reader=reader)

    @tool
    def nl2sql(question: str, load_date: str = "", limit: int = 10) -> dict:
        """Usa un planner agent interno para convertir una pregunta OTC a SQL seguro y ejecuta la consulta."""

        return run_nl2sql(
            question,
            load_date=load_date,
            limit=limit,
            settings=resolved_settings,
            reader=reader,
            planner=nl2sql_planner,
        )

    return [free_sql, nl2sql]


def build_skill(
    *,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
    nl2sql_planner: NL2SQLPlanner | None = None,
    name: str = "accountability_otc",
) -> AccountabilityOTCSkill:
    """Build the external Accountability OTC skill."""

    return AccountabilityOTCSkill(settings=settings, reader=reader, nl2sql_planner=nl2sql_planner, name=name)


def register(system):
    """Filesystem skill entrypoint used by lab.load_skill(path)."""

    skill = build_skill()
    system.skill(skill)
    return {
        "manifest": {
            "name": skill.name,
            "version": skill.version,
            "description": skill.description,
            "tools": list(skill.tool_names),
        },
        "runtime_skill": skill,
    }
