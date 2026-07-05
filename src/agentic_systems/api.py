"""Intentional public API surface for Agentic Systems.

``PUBLIC_API`` is the curated surface documented for new users.
Use docs and notebooks to teach only these names unless a section is explicitly
about internals.
"""

from __future__ import annotations

RECOMMENDED_API = (
    "agent",
    "runtime",
    "scheduler",
    "output_schema",
    "final_answer",
    "normalize_output",
    "tool",
    "Tool",
    "Agent",
    "RunResult",
    "LineageMemory",
    "LineageStep",
    "lineage_memory",
    "LINEAGE_SCHEMA_VERSION",
    "AgentContract",
    "ContractPolicySpec",
    "RunPolicy",
    "validate_contract_policy",
    "RuntimeConfig",
    "SchedulerConfig",
    "OutputSchema",
    "human_result",
    "human_results",
    "load_skill",
    "Skill",
    "LoadedSkill",
    "expect",
    "core",
    "providers",
    "integrations",
)

CORE_API = (
    "agent",
    "runtime",
    "scheduler",
    "load_skill",
    "default_model_id",
    "default_region",
    "AgenticSystem",
    "PublicToolRegistry",
    "Agent",
    "Tool",
    "tool",
    "expect",
    "human_result",
    "human_results",
    "print_human_result",
    "print_human_results",
    "Skill",
    "SkillManifest",
    "LoadedSkill",
    "AgentContract",
    "ContractPolicySpec",
    "RunPolicy",
    "ToolExpectationValue",
    "ValidationIssue",
    "ValidationResult",
    "normalize_tool_expectation",
    "validate_contract_policy",
    "validate_tool_expectation",
    "RunResult",
    "LineageMemory",
    "LineageStep",
    "lineage_memory",
    "LINEAGE_SCHEMA_VERSION",
    "RuntimeConfig",
    "SchedulerConfig",
    "OutputSchema",
    "FINAL_ANSWER_SCHEMA_VERSION",
    "final_answer",
    "normalize_output",
    "output_schema",
    "AgenticOutput",
    "RuntimeInfo",
    "UsageInfo",
    "OutputToolEvent",
    "OutputValidation",
    "TraceEvent",
    "GraphStateOutput",
    "EpisodeResult",
)

BEDROCK_PRIMITIVE_API = (
    "BedrockRuntimeClient",
    "DEFAULT_EMBEDDING_MODEL_ID",
)

CHAIN_API = (
    "Chain",
    "ChainStep",
)

# Recommended integration API for notebooks. It is intentionally small.
INTEGRATION_API = (
    "agent_node",
    "graph",
)

ENGINE_API = (
    "BEDROCK_RUNTIME_ENGINE",
    "OPENAI_RUNTIME_ENGINE",
    "PYTHON_RUNTIME_ENGINE",
    "VLLM_RUNTIME_ENGINE",
    "SUPPORTED_ENGINES",
    "canonical_engine_name",
    "supported_engine_names",
)

EVAL_API = (
    "EvalCaseResult",
    "EvalReport",
    "Evaluator",
    "run_eval",
)

# Advanced system/environment API. These are public, but should appear after
# fundamentals/custom in docs and tutorials.
ENVIRONMENT_API = (
    "AgenticEnvironment",
    "EnvironmentTransition",
    "AgentStepGraph",
    "DynamicAgentRouterGraph",
    "PlannedAgentGraph",
    "build_agent_step_graph",
    "build_dynamic_agent_router_graph",
    "build_planned_agent_graph",
    "environment_lineage",
)

NOTEBOOK_API = (
    "AGENT_OUTPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "AGENTIC_OUTPUT_SCHEMA_VERSION",
    "agent_output",
    "agent_output_mapper",
    "make_agent_output_mapper",
    "configure_notebook_environment",
    "show_json",
    "show",
    "compare",
    "compose_result",
    "mask_sensitive",
    "aws_environment_snapshot",
    "boto3_session_snapshot",
    "repair_ada_credential_chain",
    "run_result_output",
    "run_result_view",
    "run_result_summary",
    "tool_result_summary",
    "chain_history_summary",
    "environment_summary",
    "eval_report_output",
    "eval_report_summary",
    "maybe_show_trace",
)

TRACE_API = (
    "TRACE_SCHEMA_VERSION",
)

LINEAGE_API = (
    "LINEAGE_SCHEMA_VERSION",
    "LineageMemory",
    "LineageStep",
    "lineage_memory",
)

NAMESPACE_API = (
    "core",
    "providers",
    "integrations",
)

ADVANCED_API = tuple(dict.fromkeys((
    *CORE_API,
    *BEDROCK_PRIMITIVE_API,
    *CHAIN_API,
    *ENGINE_API,
    *INTEGRATION_API,
    *EVAL_API,
    *ENVIRONMENT_API,
    *NOTEBOOK_API,
    *TRACE_API,
    *LINEAGE_API,
    *NAMESPACE_API,
)))

PUBLIC_API = tuple(dict.fromkeys((
    *ADVANCED_API,
    "__version__",
)))

__all__ = [
    "RECOMMENDED_API",
    "CORE_API",
    "BEDROCK_PRIMITIVE_API",
    "CHAIN_API",
    "ENGINE_API",
    "INTEGRATION_API",
    "EVAL_API",
    "ENVIRONMENT_API",
    "NOTEBOOK_API",
    "TRACE_API",
    "LINEAGE_API",
    "NAMESPACE_API",
    "ADVANCED_API",
    "PUBLIC_API",
]
