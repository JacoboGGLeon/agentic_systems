"""LangGraph multi-agent system for the packaged Accountability skill.

Unlike ``accountability_tools``, this module receives the final skill package
and builds one node-agent per tool exposed by that skill.  LangGraph compiles
the graph; Bedrock Runtime is the default LM engine for the agent nodes.

For local smoke tests without an LM, pass ``engine='python-runtime', framework=None``
to ``build_system(...)``.
"""

from __future__ import annotations

import re
from typing import Any

from typing_extensions import TypedDict

import agentic_systems as lab

_QUERY_ID_RE = re.compile(r"query_id\s*=\s*[`'\"]?([a-zA-Z0-9_\-]+)[`'\"]?", re.IGNORECASE)
_SELECT_RE = re.compile(r"\bSELECT\b.+", re.IGNORECASE | re.DOTALL)

AGENT_ENGINE = "bedrock-runtime"
AGENT_FRAMEWORK = "langgraph"


class AccountabilitySkillsGraphState(TypedDict, total=False):
    """LangGraph state schema for the accountability multi-agent system.

    The explicit schema makes LangGraph merge partial node updates instead of
    replacing the root dict. This keeps ``plan`` and ``tool_result`` available
    to notebook display cells after routing.
    """

    user_prompt: str
    load_date: str
    limit: int
    plan: dict[str, Any]
    route: str
    tool_input: dict[str, Any]
    selected_tool: str
    tool_result: dict[str, Any]
    final_answer: str
    orchestrator_result: dict[str, Any]
    graph_validation: dict[str, Any]


@lab.tool
def plan_accountability_skill_request(user_prompt: str, load_date: str = "", limit: int = 10) -> dict:
    """Route a packaged-skill request to one of the skill tool-agents."""

    prompt = str(user_prompt or "").strip()
    query_id = _extract_query_id(prompt)
    if query_id:
        return {
            "route": "free_sql",
            "mode": "query_id",
            "tool": "free_sql",
            "tool_input": {"query_id": query_id, "load_date": load_date, "limit": limit},
            "reason": "El usuario pidió una consulta empaquetada por query_id.",
            "ok": True,
        }

    sql = _extract_sql(prompt)
    if sql:
        return {
            "route": "free_sql",
            "mode": "sql",
            "tool": "free_sql",
            "tool_input": {"sql": sql, "limit": limit},
            "reason": "El usuario entregó SQL explícito para la tool empaquetada.",
            "ok": True,
        }

    question = _extract_business_question(prompt)
    return {
        "route": "nl2sql",
        "mode": "natural_question",
        "tool": "nl2sql",
        "tool_input": {"question": question, "load_date": load_date, "limit": limit},
        "reason": "El usuario hizo una pregunta natural para nl2sql empaquetado.",
        "ok": True,
    }


def _extract_query_id(prompt: str) -> str:
    match = _QUERY_ID_RE.search(prompt)
    if match:
        return match.group(1)
    backtick = re.search(r"`(otc_[a-zA-Z0-9_]+)`", prompt)
    return backtick.group(1) if backtick else ""


def _extract_sql(prompt: str) -> str:
    match = _SELECT_RE.search(prompt)
    if not match:
        return ""
    sql = match.group(0).strip()
    for marker in ("\n\nResume", "\nResume", "\n\nResponde", "\nResponde"):
        index = sql.lower().find(marker.lower())
        if index >= 0:
            sql = sql[:index].strip()
    return sql.rstrip(";")


def _extract_business_question(prompt: str) -> str:
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    candidates = [line for line in lines if line.endswith("?") or line.startswith("¿")]
    return candidates[-1] if candidates else prompt


def _runtime_kwargs(
    *,
    engine: str = AGENT_ENGINE,
    framework: str | None = AGENT_FRAMEWORK,
    model: str | None = None,
    region: str | None = None,
    defaults: dict[str, Any] | None = None,
    runtime: Any | None = None,
) -> dict[str, Any]:
    """Return agent factory kwargs using the new runtime API when provided."""

    if runtime is not None:
        return {"runtime": runtime, "defaults": defaults}
    kwargs: dict[str, Any] = {"engine": engine, "model": model, "region": region, "defaults": defaults}
    if framework and engine != "python-runtime":
        kwargs["framework"] = framework
    return kwargs


def _single_tool_contract(tool_name: str) -> lab.AgentContract:
    return lab.AgentContract(must_call=[tool_name], completion="when_required_tools_satisfied")


def _single_tool_policy(tool_name: str) -> lab.RunPolicy:
    return lab.RunPolicy(
        max_turns=4,
        max_tool_calls=1,
        temperature=0.0,
        tool_choice=tool_name,
        finalize="after_required_tools",
    )


def make_agents(
    skill: Any,
    *,
    engine: str = AGENT_ENGINE,
    framework: str | None = AGENT_FRAMEWORK,
    model: str | None = None,
    region: str | None = None,
    defaults: dict[str, Any] | None = None,
    runtime: Any | None = None,
) -> dict[str, Any]:
    """Create one orchestrator and one node-agent per packaged skill tool."""

    runtime_kwargs = _runtime_kwargs(engine=engine, framework=framework, model=model, region=region, defaults=defaults, runtime=runtime)
    return {
        "orchestrator": lab.agent(
            name="accountability_skill_orchestrator",
            instructions=(
                "Eres el orquestador de la skill OTC. Debes llamar exactamente una vez "
                "a plan_accountability_skill_request con user_prompt, load_date y limit. "
                "No ejecutes SQL ni respondas el caso de negocio directamente."
            ),
            tools=[plan_accountability_skill_request],
            contract=_single_tool_contract("plan_accountability_skill_request"),
            policy=_single_tool_policy("plan_accountability_skill_request"),
            **runtime_kwargs,
        ),
        "free_sql": lab.agent(
            name="free_sql_skill_agent",
            instructions=(
                "Eres el nodo free_sql de la skill. Recibirás un JSON con tool='free_sql' e input. "
                "Debes llamar exactamente una vez a free_sql usando ese input y luego sintetizar en español."
            ),
            tools=[skill.tool("free_sql")],
            contract=_single_tool_contract("free_sql"),
            policy=_single_tool_policy("free_sql"),
            **runtime_kwargs,
        ),
        "nl2sql": lab.agent(
            name="nl2sql_skill_agent",
            instructions=(
                "Eres el nodo nl2sql de la skill. Recibirás un JSON con tool='nl2sql' e input. "
                "Debes llamar exactamente una vez a nl2sql usando ese input y luego sintetizar en español."
            ),
            tools=[skill.tool("nl2sql")],
            contract=_single_tool_contract("nl2sql"),
            policy=_single_tool_policy("nl2sql"),
            **runtime_kwargs,
        ),
    }


def _result_payload(result: Any) -> dict[str, Any]:
    return result.normalized() if hasattr(result, "normalized") else {"value": result}


def _answer_data(normalized: dict[str, Any]) -> dict[str, Any]:
    answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
    data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
    return data


def _tool_payload(result: Any, tool_name: str | None = None) -> dict[str, Any]:
    """Extract successful structured tool output from python-runtime or Bedrock results."""

    normalized = _result_payload(result)
    tools = normalized.get("tools") if isinstance(normalized.get("tools"), list) else []
    for tool in reversed(tools):
        if not isinstance(tool, dict) or tool.get("ok") is False:
            continue
        if tool_name is not None and tool.get("name") != tool_name:
            continue
        output = tool.get("output")
        if isinstance(output, dict):
            return dict(output)
    data = _answer_data(normalized)
    if data:
        return dict(data)
    result_data = getattr(result, "data", None)
    if isinstance(result_data, dict):
        return dict(result_data)
    return {}


def _orchestrator_input(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": "plan_accountability_skill_request",
        "input": {
            "user_prompt": state["user_prompt"],
            "load_date": state.get("load_date", ""),
            "limit": state.get("limit", 10),
        },
    }


def _orchestrator_output(result: Any, _state: dict[str, Any]) -> dict[str, Any]:
    plan = _tool_payload(result, "plan_accountability_skill_request")
    return {
        **dict(_state),
        "plan": plan,
        "route": plan["route"],
        "tool_input": dict(plan["tool_input"]),
        "orchestrator_result": _result_payload(result),
    }


def _route(state: dict[str, Any]) -> str:
    return str(state["route"])


def _free_sql_input(state: dict[str, Any]) -> dict[str, Any]:
    return {"tool": "free_sql", "input": dict(state["tool_input"])}


def _nl2sql_input(state: dict[str, Any]) -> dict[str, Any]:
    return {"tool": "nl2sql", "input": dict(state["tool_input"])}


def _summary_from_normalized_run(normalized: dict[str, Any]) -> str:
    """Extract a concise human answer from a normalized RunResult payload."""

    answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
    data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
    for key in ("summary", "text", "message", "error"):
        value = data.get(key)
        if value:
            return str(value)

    tools = normalized.get("tools") if isinstance(normalized.get("tools"), list) else []
    for tool in tools:
        if isinstance(tool, dict) and tool.get("summary"):
            return str(tool["summary"])

    text = str(answer.get("text") or "").strip()
    return text


def _tool_output(result: Any, state: dict[str, Any]) -> dict[str, Any]:
    normalized = _result_payload(result)
    return {
        **dict(state),
        "selected_tool": state["route"],
        "plan": dict(state.get("plan") or {}),
        "tool_input": dict(state.get("tool_input") or {}),
        "tool_result": normalized,
        "final_answer": _summary_from_normalized_run(normalized),
    }


def synthesize_result(state: dict[str, Any]) -> dict[str, Any]:
    """Pure Python function node: validate the selected route and preserve output."""

    tool_result = state.get("tool_result") or {}
    blocks = tool_result.get("blocks") if isinstance(tool_result.get("blocks"), dict) else {}
    actions = blocks.get("tool_actions") if isinstance(blocks.get("tool_actions"), list) else []
    executed = [str(action.get("name")) for action in actions if isinstance(action, dict) and action.get("ok")]
    expected = str(state.get("selected_tool") or state.get("route") or "")
    return {
        **dict(state),
        "graph_validation": {
            "ok": expected in executed,
            "expected_tool": expected,
            "executed_tools": executed,
            "node": "synthesize_result",
        },
        "final_answer": state.get("final_answer") or _summary_from_normalized_run(tool_result),
    }


def graph_blueprint(
    *,
    engine: str = AGENT_ENGINE,
    framework: str | None = AGENT_FRAMEWORK,
    model: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Return a notebook-friendly description of nodes, edges and runtime."""

    return {
        "name": "accountability_skills_multi_agent_system",
        "runtime": {"graph_engine": "langgraph", "agent_engine": engine, "agent_framework": framework, "model": model, "region": region},
        "nodes": {
            "orchestrator": {"kind": "agent_node", "tool": "plan_accountability_skill_request"},
            "free_sql_agent": {"kind": "agent_node", "tool": "free_sql"},
            "nl2sql_agent": {"kind": "agent_node", "tool": "nl2sql"},
            "synthesize_result": {"kind": "function_node"},
        },
        "edges": [
            "START -> orchestrator",
            "free_sql_agent -> synthesize_result",
            "nl2sql_agent -> synthesize_result",
            "synthesize_result -> END",
        ],
        "conditional_edges": [
            {
                "from": "orchestrator",
                "route_fn": "state['route']",
                "routes": {"free_sql": "free_sql_agent", "nl2sql": "nl2sql_agent"},
            }
        ],
    }


def make_nodes(agents: dict[str, Any]) -> dict[str, Any]:
    """Create explicit graph nodes from already-created skill agents."""

    return {
        "orchestrator": lab.agent_node(agents["orchestrator"], input=_orchestrator_input, output=_orchestrator_output, result_key=None, mode="eval"),
        "free_sql_agent": lab.agent_node(agents["free_sql"], input=_free_sql_input, output=_tool_output, result_key=None, mode="eval"),
        "nl2sql_agent": lab.agent_node(agents["nl2sql"], input=_nl2sql_input, output=_tool_output, result_key=None, mode="eval"),
        "synthesize_result": synthesize_result,
    }


def graph_edges() -> list[tuple[str, str]]:
    """Return static graph edges. Conditional routing is declared separately."""

    return [("START", "orchestrator"), ("free_sql_agent", "synthesize_result"), ("nl2sql_agent", "synthesize_result"), ("synthesize_result", "END")]


def graph_conditional_edges() -> list[tuple[str, Any, dict[str, str]]]:
    """Return conditional edges for the route selected by the orchestrator."""

    return [("orchestrator", _route, {"free_sql": "free_sql_agent", "nl2sql": "nl2sql_agent"})]


def build_system(
    skill: Any,
    *,
    engine: str = AGENT_ENGINE,
    framework: str | None = AGENT_FRAMEWORK,
    model: str | None = None,
    region: str | None = None,
    defaults: dict[str, Any] | None = None,
    runtime: Any | None = None,
) -> Any:
    """Build and compile the LangGraph multi-agent system around a loaded skill."""

    agents = make_agents(skill, engine=engine, framework=framework, model=model, region=region, defaults=defaults, runtime=runtime)
    nodes = make_nodes(agents)
    return lab.graph(
        name="accountability_skills_multi_agent_system",
        state=AccountabilitySkillsGraphState,
        nodes=nodes,
        edges=graph_edges(),
        conditional_edges=graph_conditional_edges(),
    )


__all__ = [
    "AccountabilitySkillsGraphState",
    "build_system",
    "graph_blueprint",
    "graph_conditional_edges",
    "graph_edges",
    "make_agents",
    "make_nodes",
    "plan_accountability_skill_request",
    "synthesize_result",
]
