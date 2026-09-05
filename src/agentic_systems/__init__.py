"""Agentic Systems public API."""

from . import core, providers, integrations
from .compatibility import (
    CompatibilityCase,
    FRAMEWORK_NAMES,
    PROVIDER_NAMES,
    compatibility_matrix,
    compatibility_report,
)
from .registry import dependency_target
from .agents import Agent
from .api import PUBLIC_API as _PUBLIC_API
from .factories import (
    agent,
    default_model_id,
    default_region,
    environment,
    framework,
    eval,
    load_skill,
    model_artifact,
    model_server,
    runtime,
    provider,
    scheduler,
    skill,
    system,
    toolset,
    output_schema,
)
from .api_contract import api_contract, exercise_api
from .bedrock_runtime_client import BedrockRuntimeClient, DEFAULT_EMBEDDING_MODEL_ID
from .chain import Chain, ChainStep
from .contracts import (
    AgentContract,
    ContractPolicySpec,
    RunPolicy,
    ToolExpectationValue,
    ValidationIssue,
    ValidationResult,
    normalize_tool_expectation,
    validate_contract_policy,
    validate_tool_expectation,
)
from .engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OLLAMA_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
    SUPPORTED_ENGINES,
    canonical_engine_name,
    supported_engine_names,
)
from .environments import (
    AgenticEnvironment,
    AgentStepGraph,
    DynamicAgentRouterGraph,
    PlannedAgentGraph,
    EnvironmentTransition,
    build_agent_step_graph,
    build_dynamic_agent_router_graph,
    build_planned_agent_graph,
    environment_lineage,
)
from .evals import (
    EvalCaseResult,
    EvalReport,
    EvalReproducibility,
    Evaluator,
    JudgeResult,
    JudgeRubric,
    run_eval,
)
from .expectations import ExpectationBuilder, expect
from .integrations.langgraph import (
    AgenticGraph,
    GraphApp,
    agent_node,
    graph,
    build_langgraph_agent_graph,
    build_langgraph_agent_node,
    build_langgraph_planned_graph,
    lineage_from_langgraph_result,
    lineage_from_langgraph_state,
)
from .integrations.config import FrameworkConfig
from .output_contracts import (
    AGENTIC_OUTPUT_SCHEMA_VERSION,
    AgenticOutput,
    EpisodeResult,
    GraphStateOutput,
    OutputToolEvent,
    OutputValidation,
    RuntimeInfo,
    TraceEvent,
    UsageInfo,
)
from .protocols import ModelServer
from .schemas.serving import EndpointInfo, ModelArtifact, ServerHealth, VLLMServerSpec
from .serving.vllm import VLLMServer
from .results import TRACE_SCHEMA_VERSION, RunResult
from .execution import (
    AsyncExecutable,
    CallableExecutable,
    Executable,
    ExecutionPlan,
    CompiledSystem,
    SequentialPlan,
    ParallelPlan,
    coerce_run_result,
    is_executable,
)
from .lineage import LINEAGE_SCHEMA_VERSION, LineageMemory, LineageStep, lineage_memory
from .final_answer import (
    FINAL_ANSWER_SCHEMA_VERSION,
    OutputSchema,
    final_answer,
    normalize_output,
)
from .core.provider import ModelProviderConfig
from .core.runtime import (
    AUTO_PROVIDER_ENV_VAR,
    DEFAULT_AUTO_PROVIDER_PRIORITY,
    RuntimeConfig,
    normalize_provider_priority,
    resolve_auto_provider,
)
from .core.scheduler import SchedulerConfig
from .skills import LoadedSkill, Skill, SkillManifest
from .system import AgenticSystem, InspectReport, PublicToolRegistry
from .tools import Tool, tool
from .tools import ToolSet, ToolSetRef
from .human_output import human_result
from .utils import (
    AGENT_OUTPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    agent_output,
    agent_output_mapper,
    make_agent_output_mapper,
    aws_environment_snapshot,
    boto3_session_snapshot,
    configure_notebook_environment,
    chain_history_summary,
    environment_summary,
    eval_report_output,
    eval_report_summary,
    mask_sensitive,
    maybe_show_trace,
    repair_ada_credential_chain,
    run_result_output,
    run_result_summary,
    run_result_view,
    show_json,
    show,
    compare,
    compose_result,
    tool_result_summary,
)
from .providers.openai_runtime import openai_environment_snapshot
from .providers.ollama_runtime import ollama_environment_snapshot
from .providers.vllm_runtime import vllm_environment_snapshot

__version__ = "2.1.2"

__all__ = list(_PUBLIC_API)
del _PUBLIC_API
for _name in tuple(globals()):
    if not _name.startswith("_") and _name not in __all__:
        del globals()[_name]
del _name
