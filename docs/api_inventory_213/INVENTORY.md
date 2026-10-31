> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](../API_214.md).

# Inventario completo observado — candidata 2.1.3

Generado con `python scripts/audit_api_213.py`; propuesta, no implementación.

Wheel SHA-256: `bb6c92e30ee3a3abe2d2c7a613106a8f3d0ec77773fce2ae4ead47df36f6610a`.

```json
{
  "rows": 3270,
  "by_exposure": {
    "root": 237,
    "reachable": 566,
    "submodule": 2266,
    "related-schema": 196,
    "cli": 5
  },
  "by_kind": {
    "function": 147,
    "parameter": 1813,
    "constant": 1,
    "class": 165,
    "field": 752,
    "property": 40,
    "method": 327,
    "protocol": 21,
    "command": 4
  },
  "candidate_root_exports": 18,
  "baseline_stable_exports": 89,
  "modules": 94,
  "pydantic_public_members": 28
}
```

Cada parámetro tiene su fila en [inventory.csv](inventory.csv) y su valor/tipo/modo en [inventory.json](inventory.json).
Las firmas siguientes incluyen métodos heredados propios y propiedades. Las de tipos no exportados son superficie accesible, no constructores que debamos enseñar.

[Decisión de diseño](../API_213_DISPOSITION.md). [Cobertura propuesta](../API_213_COVERAGE_PLAN.md).

## configuration

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `toolkit.runtime` | function | `(*, provider, model=None, region=None, endpoint=None, api_key=None, timeout_s=60.0, max_retries=0, max_tool_calls=5, max_turns=6)` | conservar |
| `toolkit.framework` | function | `(name, *, agent_kwargs=None, run_kwargs=None)` | conservar |
| `core.runtime.RuntimeConfig` | class | `(provider: str = BEDROCK_RUNTIME_ENGINE, model_id: str \| None = None, region_name: str \| None = None, endpoint: str \| None = None, api_key: SecretStr \| str \| None = field(default=None, repr=False), scheduler: SchedulerConfig = field(default_factory=lambda: DEFAULT_SCHEDULER_CONFIG), metadata: dict[str, Any] = field(default_factory=dict), provider_priority: tuple[str, ...] \| None = None, allow_python_fallback: bool = False)` | tipo retornado; sin constructor alternativo |
| `core.runtime.RuntimeConfig.provider` | field | `str = BEDROCK_RUNTIME_ENGINE` | conservar dato documentado |
| `core.runtime.RuntimeConfig.model_id` | field | `str \| None = None` | exponer como model |
| `core.runtime.RuntimeConfig.region_name` | field | `str \| None = None` | exponer como region |
| `core.runtime.RuntimeConfig.endpoint` | field | `str \| None = None` | conservar dato documentado |
| `core.runtime.RuntimeConfig.api_key` | field | `SecretStr \| str \| None = field(default=None, repr=False)` | conservar dato documentado |
| `core.runtime.RuntimeConfig.scheduler` | field | `SchedulerConfig = field(default_factory=lambda: DEFAULT_SCHEDULER_CONFIG)` | hacer interno |
| `core.runtime.RuntimeConfig.metadata` | field | `dict[str, Any] = field(default_factory=dict)` | hacer interno |
| `core.runtime.RuntimeConfig.provider_priority` | field | `tuple[str, ...] \| None = None` | hacer interno |
| `core.runtime.RuntimeConfig.allow_python_fallback` | field | `bool = False` | hacer interno |
| `core.runtime.RuntimeConfig.__post_init__` | protocol | `(self)` | hacer interno o sustituir |
| `core.runtime.RuntimeConfig.coerce` | method | `(cls, value: 'RuntimeConfig \| dict[str, Any] \| None', **overrides: Any)` | hacer interno o sustituir |
| `core.runtime.RuntimeConfig.to_dict` | method | `(self)` | hacer interno o sustituir |
| `core.runtime.RuntimeConfig.describe` | method | `(self)` | hacer interno o sustituir |
| `core.scheduler.SchedulerConfig` | class | `(timeout_s: float \| None = 60.0, max_retries: int = 0, max_tool_calls: int \| None = 5, max_turns: int \| None = 6, max_concurrency: int = 1, backoff_s: float = 0.0)` | tipo retornado; sin constructor alternativo |
| `core.scheduler.SchedulerConfig.timeout_s` | field | `float \| None = 60.0` | conservar dato documentado |
| `core.scheduler.SchedulerConfig.max_retries` | field | `int = 0` | conservar dato documentado |
| `core.scheduler.SchedulerConfig.max_tool_calls` | field | `int \| None = 5` | conservar dato documentado |
| `core.scheduler.SchedulerConfig.max_turns` | field | `int \| None = 6` | conservar dato documentado |
| `core.scheduler.SchedulerConfig.max_concurrency` | field | `int = 1` | conservar dato documentado |
| `core.scheduler.SchedulerConfig.backoff_s` | field | `float = 0.0` | conservar dato documentado |
| `core.scheduler.SchedulerConfig.__post_init__` | protocol | `(self)` | hacer interno o sustituir |
| `core.scheduler.SchedulerConfig.coerce` | method | `(cls, value: 'SchedulerConfig \| dict[str, Any] \| None')` | hacer interno o sustituir |
| `core.scheduler.SchedulerConfig.to_dict` | method | `(self)` | hacer interno o sustituir |
| `core.scheduler.SchedulerConfig.execution_limits` | method | `(self)` | hacer interno o sustituir |
| `core.scheduler.SchedulerConfig.policy_overrides` | method | `(self)` | hacer interno o sustituir |
| `integrations.config.FrameworkConfig` | class | `(*, name: str = NATIVE_FRAMEWORK, agent_kwargs: dict[str, Any] = Field(default_factory=dict), run_kwargs: dict[str, Any] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `integrations.config.FrameworkConfig.name` | field | `str = NATIVE_FRAMEWORK` | conservar dato documentado |
| `integrations.config.FrameworkConfig.agent_kwargs` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `integrations.config.FrameworkConfig.run_kwargs` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `integrations.config.FrameworkConfig.validate_name` | method | `(cls, value: str)` | hacer interno o sustituir |
| `integrations.config.FrameworkConfig.copy_kwargs` | method | `(cls, value: Mapping[str, Any] \| None)` | hacer interno o sustituir |
| `integrations.config.FrameworkConfig.reject_reserved_kwargs` | method | `(self)` | hacer interno o sustituir |
| `integrations.config.FrameworkConfig.coerce` | method | `(cls, value: 'FrameworkConfig \| str \| None')` | hacer interno o sustituir |
| `integrations.config.FrameworkConfig.to_dict` | method | `(self)` | hacer interno o sustituir |
| `integrations.config.FrameworkConfig.inspect` | method | `(self)` | conservar |

## contracts

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `contracts.AgentContract` | class | `(*, must_call: list[str] = Field(default_factory=list), must_not_call: list[str] = Field(default_factory=list), tool_expectation: dict[str, Any] \| None = None, completion: CompletionMode = 'default', failure_policy: FailurePolicy = 'no_unresolved', require_no_unresolved_tool_failures: bool = True, expected_output: dict[str, Any] \| None = None, expected_tool_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict))` | esquema relacionado; constructor interno |
| `contracts.AgentContract.must_call` | field | `list[str] = Field(default_factory=list)` | unificar en tool_expectation.all_of |
| `contracts.AgentContract.must_not_call` | field | `list[str] = Field(default_factory=list)` | unificar en tool_expectation.forbidden (propuesto) |
| `contracts.AgentContract.tool_expectation` | field | `dict[str, Any] \| None = None` | conservar dato documentado |
| `contracts.AgentContract.completion` | field | `CompletionMode = 'default'` | conservar dato documentado |
| `contracts.AgentContract.failure_policy` | field | `FailurePolicy = 'no_unresolved'` | conservar dato documentado |
| `contracts.AgentContract.require_no_unresolved_tool_failures` | field | `bool = True` | eliminar redundancia |
| `contracts.AgentContract.expected_output` | field | `dict[str, Any] \| None = None` | conservar dato documentado |
| `contracts.AgentContract.expected_tool_outputs` | field | `dict[str, dict[str, Any]] = Field(default_factory=dict)` | conservar dato documentado |
| `contracts.AgentContract.normalize_completion` | method | `(cls, value: Any)` | hacer interno o sustituir |
| `contracts.AgentContract.normalize_failure_policy` | method | `(cls, value: Any)` | hacer interno o sustituir |
| `contracts.AgentContract.model_post_init` | method | `(self, __context: Any)` | hacer interno o sustituir |
| `contracts.AgentContract.coerce` | method | `(cls, value: 'AgentContract \| dict[str, Any] \| None')` | hacer interno o sustituir |
| `contracts.AgentContract.check` | method | `(self, *, policy: 'RunPolicy \| dict[str, Any] \| None'=None, available_tools: list[str] \| tuple[str, ...] \| set[str] \| None=None)` | hacer interno o sustituir |
| `contracts.RunPolicy` | class | `(*, max_turns: int = 8, max_tool_calls: int \| None = None, max_tokens: int \| None = None, temperature: float \| None = None, tool_choice: str = 'auto', repair: bool = True, max_repairs: int = 2, finalize: Literal['never', 'on_max_turns', 'after_required_tools'] = 'on_max_turns', trace: Literal['compact', 'full'] = 'compact', strict: bool = True)` | esquema relacionado; constructor interno |
| `contracts.RunPolicy.max_turns` | field | `int = 8` | mover a runtime.max_turns |
| `contracts.RunPolicy.max_tool_calls` | field | `int \| None = None` | mover a runtime.max_tool_calls |
| `contracts.RunPolicy.max_tokens` | field | `int \| None = None` | mover a runtime.max_tokens (propuesto) |
| `contracts.RunPolicy.temperature` | field | `float \| None = None` | conservar dato documentado |
| `contracts.RunPolicy.tool_choice` | field | `str = 'auto'` | conservar dato documentado |
| `contracts.RunPolicy.repair` | field | `bool = True` | conservar dato documentado |
| `contracts.RunPolicy.max_repairs` | field | `int = 2` | conservar dato documentado |
| `contracts.RunPolicy.finalize` | field | `Literal['never', 'on_max_turns', 'after_required_tools'] = 'on_max_turns'` | conservar dato documentado |
| `contracts.RunPolicy.trace` | field | `Literal['compact', 'full'] = 'compact'` | conservar dato documentado |
| `contracts.RunPolicy.strict` | field | `bool = True` | conservar dato documentado |
| `contracts.RunPolicy.validate_positive_max_turns` | method | `(cls, value: int)` | hacer interno o sustituir |
| `contracts.RunPolicy.validate_optional_tool_limit` | method | `(cls, value: int \| None)` | hacer interno o sustituir |
| `contracts.RunPolicy.validate_optional_token_limit` | method | `(cls, value: int \| None)` | hacer interno o sustituir |
| `contracts.RunPolicy.validate_optional_positive_ints` | method | `(cls, value: int \| None)` | hacer interno o sustituir |
| `contracts.RunPolicy.validate_non_negative_repairs` | method | `(cls, value: int)` | hacer interno o sustituir |
| `contracts.RunPolicy.validate_temperature_range` | method | `(cls, value: float \| None)` | hacer interno o sustituir |
| `contracts.RunPolicy.validate_tool_choice` | method | `(cls, value: str)` | hacer interno o sustituir |
| `contracts.RunPolicy.coerce` | method | `(cls, value: 'RunPolicy \| dict[str, Any] \| None')` | hacer interno o sustituir |
| `contracts.RunPolicy.for_mode` | method | `(cls, mode: str='default')` | hacer interno o sustituir |
| `contracts.RunPolicy.merge` | method | `(self, overrides: 'RunPolicy \| dict[str, Any] \| None')` | hacer interno o sustituir |
| `contracts.RunPolicy.check` | method | `(self, *, contract: AgentContract \| dict[str, Any] \| None=None, available_tools: list[str] \| tuple[str, ...] \| set[str] \| None=None)` | hacer interno o sustituir |

## evaluation-payload

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `evals.EvalCaseResult` | class | `(*, name: str, ok: bool, input: Any, expected: dict[str, Any] = Field(default_factory=dict), result: dict[str, Any], validation: dict[str, Any], deterministic_validation: dict[str, Any] \| None = None, judge: JudgeResult \| None = None, candidate_usage: dict[str, Any] = Field(default_factory=dict), judge_usage: dict[str, Any] = Field(default_factory=dict), usage: dict[str, Any] = Field(default_factory=dict))` | esquema relacionado; constructor interno |
| `evals.EvalCaseResult.name` | field | `str = requerido` | conservar dato documentado |
| `evals.EvalCaseResult.ok` | field | `bool = requerido` | conservar dato documentado |
| `evals.EvalCaseResult.input` | field | `Any = requerido` | conservar dato documentado |
| `evals.EvalCaseResult.expected` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.EvalCaseResult.result` | field | `dict[str, Any] = requerido` | conservar dato documentado |
| `evals.EvalCaseResult.validation` | field | `dict[str, Any] = requerido` | conservar dato documentado |
| `evals.EvalCaseResult.deterministic_validation` | field | `dict[str, Any] \| None = None` | conservar dato documentado |
| `evals.EvalCaseResult.judge` | field | `JudgeResult \| None = None` | conservar dato documentado |
| `evals.EvalCaseResult.candidate_usage` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.EvalCaseResult.judge_usage` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.EvalCaseResult.usage` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.EvalCaseResult.to_dict` | method | `(self)` | hacer interno |
| `evals.EvalReport` | class | `(*, schema_version: str = 'agentic_systems.eval-report.v2', ok: bool, total: int, passed: int, failed: int, pass_rate: float, cases: list[EvalCaseResult], reproducibility: EvalReproducibility = Field(default_factory=EvalReproducibility))` | esquema relacionado; constructor interno |
| `evals.EvalReport.schema_version` | field | `str = 'agentic_systems.eval-report.v2'` | conservar dato documentado |
| `evals.EvalReport.ok` | field | `bool = requerido` | conservar dato documentado |
| `evals.EvalReport.total` | field | `int = requerido` | conservar dato documentado |
| `evals.EvalReport.passed` | field | `int = requerido` | conservar dato documentado |
| `evals.EvalReport.failed` | field | `int = requerido` | conservar dato documentado |
| `evals.EvalReport.pass_rate` | field | `float = requerido` | conservar dato documentado |
| `evals.EvalReport.cases` | field | `list[EvalCaseResult] = requerido` | conservar dato documentado |
| `evals.EvalReport.reproducibility` | field | `EvalReproducibility = Field(default_factory=EvalReproducibility)` | conservar dato documentado |
| `evals.EvalReport.validate_aggregates` | method | `(self)` | hacer interno |
| `evals.EvalReport.to_dict` | method | `(self)` | hacer interno |
| `evals.EvalReport.normalized` | method | `(self)` | hacer interno |
| `evals.EvalReport.summary_text` | method | `(self)` | hacer interno |
| `evals.EvalReport.raise_if_failed` | method | `(self)` | hacer interno |
| `evals.EvalReport.lineage` | method | `(self, *, name: str='eval_report.lineage', question: str='', goal: str='', tags: list[str] \| None=None, metadata: dict[str, Any] \| None=None)` | hacer interno |
| `evals.EvalReproducibility` | class | `(*, schema_version: str = 'agentic_systems.eval-reproducibility.v1', classification: Literal['deterministic', 'seeded', 'non_deterministic'] = 'non_deterministic', seed: int \| None = 0, replayable: bool = False, conditions: list[str] = Field(default_factory=list))` | esquema relacionado; constructor interno |
| `evals.EvalReproducibility.schema_version` | field | `str = 'agentic_systems.eval-reproducibility.v1'` | conservar dato documentado |
| `evals.EvalReproducibility.classification` | field | `Literal['deterministic', 'seeded', 'non_deterministic'] = 'non_deterministic'` | conservar dato documentado |
| `evals.EvalReproducibility.seed` | field | `int \| None = 0` | conservar dato documentado |
| `evals.EvalReproducibility.replayable` | field | `bool = False` | conservar dato documentado |
| `evals.EvalReproducibility.conditions` | field | `list[str] = Field(default_factory=list)` | conservar dato documentado |
| `evals.EvalReproducibility.validate_classification` | method | `(self)` | hacer interno |
| `evals.EvalReproducibility.to_dict` | method | `(self)` | hacer interno |
| `evals.JudgeFinding` | class | `(*, criterion: str, evidence: str)` | esquema relacionado; constructor interno |
| `evals.JudgeFinding.criterion` | field | `str = requerido` | conservar dato documentado |
| `evals.JudgeFinding.evidence` | field | `str = Field(min_length=1, max_length=1000)` | conservar dato documentado |
| `evals.JudgeResult` | class | `(*, ok: bool, score: float, criteria: dict[str, float] = Field(default_factory=dict), raw_score: float \| None = Field(default=None, ge=0.0, le=1.0), raw_criteria: dict[str, float] = Field(default_factory=dict), deterministic_authority: tuple[str, ...] = (), threshold: float = Field(default=0.8, ge=0.0, le=1.0), deterministic_validation_ok: bool = True, execution_ok: bool = True, certification_tool: str \| None = None, certification_recorded: bool = True, findings: tuple[JudgeFinding, ...] = (), consistent: bool = True, consistency_issues: tuple[str, ...] = (), rationale: str = '', provider: str \| None = None, framework: str \| None = None, model: str \| None = None, usage: dict[str, Any] = Field(default_factory=dict))` | esquema relacionado; constructor interno |
| `evals.JudgeResult.ok` | field | `bool = requerido` | conservar dato documentado |
| `evals.JudgeResult.score` | field | `float = Field(ge=0.0, le=1.0)` | conservar dato documentado |
| `evals.JudgeResult.criteria` | field | `dict[str, float] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.JudgeResult.raw_score` | field | `float \| None = Field(default=None, ge=0.0, le=1.0)` | conservar dato documentado |
| `evals.JudgeResult.raw_criteria` | field | `dict[str, float] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.JudgeResult.deterministic_authority` | field | `tuple[str, ...] = ()` | conservar dato documentado |
| `evals.JudgeResult.threshold` | field | `float = Field(default=0.8, ge=0.0, le=1.0)` | conservar dato documentado |
| `evals.JudgeResult.deterministic_validation_ok` | field | `bool = True` | conservar dato documentado |
| `evals.JudgeResult.execution_ok` | field | `bool = True` | conservar dato documentado |
| `evals.JudgeResult.certification_tool` | field | `str \| None = None` | conservar dato documentado |
| `evals.JudgeResult.certification_recorded` | field | `bool = True` | conservar dato documentado |
| `evals.JudgeResult.findings` | field | `tuple[JudgeFinding, ...] = ()` | conservar dato documentado |
| `evals.JudgeResult.consistent` | field | `bool = True` | conservar dato documentado |
| `evals.JudgeResult.consistency_issues` | field | `tuple[str, ...] = ()` | conservar dato documentado |
| `evals.JudgeResult.rationale` | field | `str = ''` | conservar dato documentado |
| `evals.JudgeResult.provider` | field | `str \| None = None` | conservar dato documentado |
| `evals.JudgeResult.framework` | field | `str \| None = None` | conservar dato documentado |
| `evals.JudgeResult.model` | field | `str \| None = None` | conservar dato documentado |
| `evals.JudgeResult.usage` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `evals.JudgeResult.validate_verdict` | method | `(self)` | hacer interno |
| `evals.JudgeResult.to_dict` | method | `(self)` | hacer interno |
| `evals.JudgeRubric` | class | `(*, criteria: tuple[str, ...] = DEFAULT_JUDGE_CRITERIA, threshold: float = Field(default=0.8, ge=0.0, le=1.0), instructions: str = DEFAULT_JUDGE_INSTRUCTIONS, certification_tool: str \| None = None, deterministic_authority: tuple[str, ...] = (), require_failure_findings: bool = True)` | esquema relacionado; constructor interno |
| `evals.JudgeRubric.criteria` | field | `tuple[str, ...] = DEFAULT_JUDGE_CRITERIA` | conservar dato documentado |
| `evals.JudgeRubric.threshold` | field | `float = Field(default=0.8, ge=0.0, le=1.0)` | conservar dato documentado |
| `evals.JudgeRubric.instructions` | field | `str = DEFAULT_JUDGE_INSTRUCTIONS` | conservar dato documentado |
| `evals.JudgeRubric.certification_tool` | field | `str \| None = None` | conservar dato documentado |
| `evals.JudgeRubric.deterministic_authority` | field | `tuple[str, ...] = ()` | conservar dato documentado |
| `evals.JudgeRubric.require_failure_findings` | field | `bool = True` | conservar dato documentado |

## execution

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `_grammar.Compiled` | class | `(prepared: _Prepared)` | tipo retornado; sin constructor alternativo |
| `_grammar.Compiled.prepared` | field | `_Prepared = requerido` | hacer interno |
| `_grammar.Compiled.run` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `_grammar.Compiled.arun` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `_grammar.Compiled.inspect` | method | `(self)` | conservar |
| `_grammar._CompiledEnvironment` | class | `(name: str, unit: Compiled, records_json: str, max_steps: int \| None)` | tipo retornado; sin constructor alternativo |
| `_grammar._CompiledEnvironment.name` | field | `str = requerido` | hacer interno |
| `_grammar._CompiledEnvironment.unit` | field | `Compiled = requerido` | hacer interno |
| `_grammar._CompiledEnvironment.records_json` | field | `str = requerido` | hacer interno |
| `_grammar._CompiledEnvironment.max_steps` | field | `int \| None = requerido` | hacer interno |
| `_grammar._CompiledEnvironment.run` | method | `(self, *, limits=Limits())` | conservar |
| `_grammar._CompiledEval` | class | `(name: str, unit: Compiled, cases_json: str)` | tipo retornado; sin constructor alternativo |
| `_grammar._CompiledEval.name` | field | `str = requerido` | hacer interno |
| `_grammar._CompiledEval.unit` | field | `Compiled = requerido` | hacer interno |
| `_grammar._CompiledEval.cases_json` | field | `str = requerido` | hacer interno |
| `_grammar._CompiledEval.run` | method | `(self, *, limits=Limits())` | conservar |

## flows

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `_actors.Agent` | class | `(self, *, name: str, instructions: str='', tools: Any=None, skills: Any=None, system: Any \| None=None, engine: str \| None=None, framework: str \| FrameworkConfig \| None=None, model: str \| None=None, contract: AgentContract \| dict[str, Any] \| None=None, policy: RunPolicy \| dict[str, Any] \| None=None, input_contract: Any \| None=None, output_contract: Any \| None=None, input: Any \| None=None, output: Any \| None=None, defaults: dict[str, Any] \| None=None, metadata: dict[str, Any] \| None=None, runtime: RuntimeConfig \| dict[str, Any] \| None=None)` | tipo retornado; sin constructor alternativo |
| `_actors.Agent.system` | field | `Any = system` | conservar dato documentado |
| `_actors.Agent.name` | field | `Any = str(name or '').strip()` | conservar dato documentado |
| `_actors.Agent.instructions` | field | `Any = str(instructions or '')` | conservar dato documentado |
| `_actors.Agent.runtime_config` | field | `Any = RuntimeConfig.coerce(runtime) if runtime is not None else getattr(system, 'runtime_config', None)` | conservar dato documentado |
| `_actors.Agent.framework_config` | field | `Any = FrameworkConfig.coerce(framework)` | conservar dato documentado |
| `_actors.Agent.model` | field | `Any = model if model is not None else self.runtime_config.model_id if self.runtime_config else getattr(system, 'model', None)` | conservar dato documentado |
| `_actors.Agent.contract` | field | `Any = AgentContract.coerce(contract)` | conservar dato documentado |
| `_actors.Agent.policy` | field | `Any = policy` | conservar dato documentado |
| `_actors.Agent.input_contract` | field | `Any = input_contract if input_contract is not None else input` | conservar dato documentado |
| `_actors.Agent.output_contract` | field | `Any = output_contract if output_contract is not None else output` | conservar dato documentado |
| `_actors.Agent.defaults` | field | `Any = defaults` | conservar dato documentado |
| `_actors.Agent.metadata` | field | `Any = dict(metadata or {})` | conservar dato documentado |
| `_actors.Agent.tools` | field | `Any = _dedupe_preserve_order([*skill_tool_names, *explicit_tool_names])` | conservar dato documentado |
| `_actors.Agent.skills` | field | `Any = _dedupe_preserve_order(skill_names)` | conservar dato documentado |
| `_actors.Agent.tool_names` | property | `(self)` | hacer interno o sustituir |
| `_actors.Agent.pipeline` | method | `(self, *steps: Any, execution: ExecutionPlan \| None=None, name: str \| None=None)` | hacer interno o sustituir |
| `_actors.Agent.available_tools` | method | `(self)` | hacer interno o sustituir |
| `_actors.Agent.info` | method | `(self)` | hacer interno o sustituir |
| `_actors.Agent.describe` | method | `(self)` | hacer interno o sustituir |
| `_actors.Agent.check` | method | `(self)` | hacer interno o sustituir |
| `_actors.Agent.bind` | method | `(self, system: Any)` | hacer interno o sustituir |
| `_actors.Agent.native_agent` | property | `(self)` | hacer interno o sustituir |
| `_actors.Agent.prepare` | method | `(self)` | hacer interno o sustituir |
| `_actors.Agent.run` | method | `(self, input: Any=None, *, mode: str='eval', config: RunPolicy \| dict[str, Any] \| None=None)` | conservar |
| `_actors.Agent.arun` | method | `(self, input: Any=None, *, mode: str='eval', config: RunPolicy \| dict[str, Any] \| None=None)` | conservar |
| `_actors.Agent.run_sync` | method | `(self, input: Any=None, *, mode: str='default', config: RunPolicy \| dict[str, Any] \| None=None)` | hacer interno o sustituir |
| `_actors.Agent.as_node` | method | `(self, *, input: str \| Callable[[dict[str, Any]], Any]='prompt', output: str \| Callable[[RunResult, dict[str, Any]], Any] \| None='answer', trace: str \| None='ada_trace', result_key: str \| None=None, mode: str='default', config: RunPolicy \| dict[str, Any] \| None=None)` | hacer interno o sustituir |
| `_actors.Agent.as_async_node` | method | `(self, *, input: str \| Callable[[dict[str, Any]], Any]='prompt', output: str \| Callable[[RunResult, dict[str, Any]], Any] \| None='answer', trace: str \| None='ada_trace', result_key: str \| None=None, mode: str='default', config: RunPolicy \| dict[str, Any] \| None=None)` | hacer interno o sustituir |
| `_actors.Agent.as_tool` | method | `(self, *, name: str \| None=None, description: str \| None=None)` | hacer interno o sustituir |
| `_actors.Agent.validate` | method | `(self)` | hacer interno o sustituir |
| `_actors.Agent.eval` | method | `(self, cases: list[dict[str, Any]], **kwargs: Any)` | hacer interno o sustituir |
| `toolkit.Action` | class | `(name: str, target: Any, input: Callable = identity)` | conservar |
| `toolkit.Action.name` | field | `str = requerido` | conservar dato documentado |
| `toolkit.Action.target` | field | `Any = requerido` | conservar dato documentado |
| `toolkit.Action.input` | field | `Callable = identity` | conservar dato documentado |
| `toolkit.Agent` | class | `(name: str, flow: Any = None, backend: str = 'native', skills: tuple = (), runtime: Any = None, framework: Any = None, instructions: str = '', contract: dict \| None = None, policy: dict \| None = None)` | conservar |
| `toolkit.Agent.name` | field | `str = requerido` | conservar dato documentado |
| `toolkit.Agent.flow` | field | `Any = None` | conservar dato documentado |
| `toolkit.Agent.backend` | field | `str = 'native'` | conservar dato documentado |
| `toolkit.Agent.skills` | field | `tuple = ()` | conservar dato documentado |
| `toolkit.Agent.kind` | field | `str = field(default='agent', init=False)` | conservar dato documentado |
| `toolkit.Agent.compile` | method | `(self)` | conservar |
| `toolkit.Agent.run` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `toolkit.Agent.arun` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `toolkit.Agent.inspect` | method | `(self)` | conservar |
| `toolkit.Agent.runtime` | field | `Any = None` | conservar dato documentado |
| `toolkit.Agent.framework` | field | `Any = None` | conservar dato documentado |
| `toolkit.Agent.instructions` | field | `str = ''` | conservar dato documentado |
| `toolkit.Agent.contract` | field | `dict \| None = None` | conservar dato documentado |
| `toolkit.Agent.policy` | field | `dict \| None = None` | conservar dato documentado |
| `toolkit.Agent.__post_init__` | protocol | `(self)` | hacer interno o sustituir |
| `toolkit.Environment` | class | `(name: str, unit: Unit, records: tuple, max_steps: int \| None = None)` | conservar |
| `toolkit.Environment.name` | field | `str = requerido` | conservar dato documentado |
| `toolkit.Environment.unit` | field | `Unit = requerido` | conservar dato documentado |
| `toolkit.Environment.records` | field | `tuple = requerido` | conservar dato documentado |
| `toolkit.Environment.max_steps` | field | `int \| None = None` | conservar dato documentado |
| `toolkit.Environment.compile` | method | `(self)` | conservar |
| `toolkit.Environment.run` | method | `(self, *, limits=Limits())` | conservar |
| `toolkit.Eval` | class | `(name: str, unit: Unit, cases: tuple)` | conservar |
| `toolkit.Eval.name` | field | `str = requerido` | conservar dato documentado |
| `toolkit.Eval.unit` | field | `Unit = requerido` | conservar dato documentado |
| `toolkit.Eval.cases` | field | `tuple = requerido` | conservar dato documentado |
| `toolkit.Eval.compile` | method | `(self)` | conservar |
| `toolkit.Eval.run` | method | `(self, *, limits=Limits())` | conservar |
| `toolkit.Graph` | class | `(nodes: tuple, edges: tuple, start: str, max_visits: int = 20, name: str = 'graph')` | conservar |
| `toolkit.Graph.nodes` | field | `tuple = requerido` | conservar dato documentado |
| `toolkit.Graph.edges` | field | `tuple = requerido` | conservar dato documentado |
| `toolkit.Graph.start` | field | `str = requerido` | conservar dato documentado |
| `toolkit.Graph.max_visits` | field | `int = 20` | conservar dato documentado |
| `toolkit.Graph.name` | field | `str = 'graph'` | conservar dato documentado |
| `toolkit.Limits` | class | `(max_actions: int = 100, timeout_s: float = 10)` | conservar |
| `toolkit.Limits.max_actions` | field | `int = 100` | conservar dato documentado |
| `toolkit.Limits.timeout_s` | field | `float = 10` | conservar dato documentado |
| `toolkit.Parallel` | class | `(steps: tuple, join: Callable, name: str = 'parallel')` | conservar |
| `toolkit.Parallel.steps` | field | `tuple = requerido` | conservar dato documentado |
| `toolkit.Parallel.join` | field | `Callable = requerido` | conservar dato documentado |
| `toolkit.Parallel.name` | field | `str = 'parallel'` | conservar dato documentado |
| `toolkit.Sequence` | class | `(steps: tuple, name: str = 'sequence')` | conservar |
| `toolkit.Sequence.steps` | field | `tuple = requerido` | conservar dato documentado |
| `toolkit.Sequence.name` | field | `str = 'sequence'` | conservar dato documentado |
| `toolkit.System` | class | `(name: str, flow: Any = None, backend: str = 'native', skills: tuple = ())` | conservar |
| `toolkit.System.name` | field | `str = requerido` | conservar dato documentado |
| `toolkit.System.flow` | field | `Any = None` | conservar dato documentado |
| `toolkit.System.backend` | field | `str = 'native'` | conservar dato documentado |
| `toolkit.System.skills` | field | `tuple = ()` | retirar del público |
| `toolkit.System.kind` | field | `str = field(default='system', init=False)` | conservar dato documentado |
| `toolkit.System.compile` | method | `(self)` | conservar |
| `toolkit.System.run` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `toolkit.System.arun` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `toolkit.System.inspect` | method | `(self)` | conservar |
| `_grammar.Unit` | class | `(name: str, flow: Any = None, backend: str = 'native', skills: tuple = ())` | tipo retornado; sin constructor alternativo |
| `_grammar.Unit.name` | field | `str = requerido` | conservar dato documentado |
| `_grammar.Unit.flow` | field | `Any = None` | conservar dato documentado |
| `_grammar.Unit.backend` | field | `str = 'native'` | conservar dato documentado |
| `_grammar.Unit.skills` | field | `tuple = ()` | conservar dato documentado |
| `_grammar.Unit.kind` | field | `str = field(default='unit', init=False)` | conservar dato documentado |
| `_grammar.Unit.compile` | method | `(self)` | conservar |
| `_grammar.Unit.run` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `_grammar.Unit.arun` | method | `(self, input=None, *, limits=Limits())` | conservar |
| `_grammar.Unit.inspect` | method | `(self)` | conservar |

## package

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `toolkit.__version__` | constant | `Any = requerido` | conservar |
| `_grammar._Prepared` | class | `(name: str, kind: str, backend: str, execute: Callable, native: Any = None, children: tuple = ())` | tipo retornado; sin constructor alternativo |
| `_grammar._Prepared.name` | field | `str = requerido` | conservar dato documentado |
| `_grammar._Prepared.kind` | field | `str = requerido` | conservar dato documentado |
| `_grammar._Prepared.backend` | field | `str = requerido` | conservar dato documentado |
| `_grammar._Prepared.execute` | field | `Callable = requerido` | conservar dato documentado |
| `_grammar._Prepared.native` | field | `Any = None` | conservar dato documentado |
| `_grammar._Prepared.children` | field | `tuple = ()` | conservar dato documentado |
| `_grammar._Prepared.run` | method | `(self, value, context)` | hacer interno o sustituir |
| `execution.CompiledSystem` | class | `(units: tuple[Executable, ...], plan: ExecutionPlan = field(default_factory=SequentialPlan), name: str = 'system', entrypoint: str \| None = None)` | tipo retornado; sin constructor alternativo |
| `execution.CompiledSystem.units` | field | `tuple[Executable, ...] = requerido` | conservar dato documentado |
| `execution.CompiledSystem.plan` | field | `ExecutionPlan = field(default_factory=SequentialPlan)` | conservar dato documentado |
| `execution.CompiledSystem.name` | field | `str = 'system'` | conservar dato documentado |
| `execution.CompiledSystem.entrypoint` | field | `str \| None = None` | conservar dato documentado |
| `execution.CompiledSystem.run` | method | `(self, input: Any=None, **kwargs: Any)` | hacer interno o sustituir |
| `execution.CompiledSystem.arun` | method | `(self, input: Any=None, **kwargs: Any)` | hacer interno o sustituir |
| `execution.CompiledSystem.inspect` | method | `(self)` | hacer interno o sustituir |
| `execution.Executable` | class | `()` | tipo retornado; sin constructor alternativo |
| `execution.Executable.run` | method | `(self, input: Any=None, **kwargs: Any)` | hacer interno o sustituir |
| `execution.ExecutionPlan` | class | `()` | tipo retornado; sin constructor alternativo |
| `execution.ExecutionPlan.name` | property | `(self)` | hacer interno o sustituir |
| `execution.ExecutionPlan.execute` | method | `(self, units: Iterable[Executable], input: Any=None, **kwargs: Any)` | hacer interno o sustituir |
| `schemas.base.ContractModel` | class | `()` | tipo retornado; sin constructor alternativo |
| `schemas.base.PersistedSpec` | class | `(*, schema_version: str)` | tipo retornado; sin constructor alternativo |
| `schemas.base.PersistedSpec.schema_version` | field | `str = requerido` | conservar dato documentado |
| `schemas.execution.ExecutionLimits` | class | `(*, max_turns: StrictInt \| None = Field(default=6, ge=1), max_tool_calls: StrictInt \| None = Field(default=5, ge=0), max_tokens: StrictInt \| None = Field(default=None, ge=1), timeout_s: StrictFloat \| StrictInt \| None = Field(default=60.0, gt=0), max_concurrency: StrictInt = Field(default=1, ge=1), max_retries: StrictInt = Field(default=0, ge=0), max_repairs: StrictInt = Field(default=0, ge=0), backoff_s: StrictFloat \| StrictInt = Field(default=0.0, ge=0))` | tipo retornado; sin constructor alternativo |
| `schemas.execution.ExecutionLimits.max_turns` | field | `StrictInt \| None = Field(default=6, ge=1)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.max_tool_calls` | field | `StrictInt \| None = Field(default=5, ge=0)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.max_tokens` | field | `StrictInt \| None = Field(default=None, ge=1)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.timeout_s` | field | `StrictFloat \| StrictInt \| None = Field(default=60.0, gt=0)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.max_concurrency` | field | `StrictInt = Field(default=1, ge=1)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.max_retries` | field | `StrictInt = Field(default=0, ge=0)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.max_repairs` | field | `StrictInt = Field(default=0, ge=0)` | conservar dato documentado |
| `schemas.execution.ExecutionLimits.backoff_s` | field | `StrictFloat \| StrictInt = Field(default=0.0, ge=0)` | conservar dato documentado |
| `schemas.results.ExecutionError` | class | `(*, category: Literal['authentication', 'authorization', 'configuration', 'invalid_request', 'rate_limit', 'timeout', 'transient', 'unsupported', 'provider', 'framework', 'internal'], message: str, provider: str, framework: str, code: str \| None = None, retryable: bool = False, cause_type: str \| None = None, details: dict[str, JsonValue] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `schemas.results.ExecutionError.category` | field | `Literal['authentication', 'authorization', 'configuration', 'invalid_request', 'rate_limit', 'timeout', 'transient', 'unsupported', 'provider', 'framework', 'internal'] = requerido` | conservar dato documentado |
| `schemas.results.ExecutionError.message` | field | `str = requerido` | conservar dato documentado |
| `schemas.results.ExecutionError.provider` | field | `str = requerido` | conservar dato documentado |
| `schemas.results.ExecutionError.framework` | field | `str = requerido` | conservar dato documentado |
| `schemas.results.ExecutionError.code` | field | `str \| None = None` | conservar dato documentado |
| `schemas.results.ExecutionError.retryable` | field | `bool = False` | conservar dato documentado |
| `schemas.results.ExecutionError.cause_type` | field | `str \| None = None` | conservar dato documentado |
| `schemas.results.ExecutionError.details` | field | `dict[str, JsonValue] = Field(default_factory=dict)` | conservar dato documentado |
| `schemas.serving._ServingSpec` | class | `(*, schema_version: str = SERVING_SCHEMA_VERSION)` | tipo retornado; sin constructor alternativo |
| `schemas.serving._ServingSpec.schema_version` | field | `str = SERVING_SCHEMA_VERSION` | conservar dato documentado |
| `schemas.serving._ServingSpec.supported_schema_version` | method | `(cls, value: str)` | hacer interno o sustituir |
| `cli.version` | command | `agentic-systems version` | conservar |
| `cli.api` | command | `agentic-systems api` | conservar |
| `cli.doctor` | command | `agentic-systems doctor` | conservar |
| `cli.new` | command | `agentic-systems new destination` | conservar |

## results

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `contracts.ValidationIssue` | class | `(*, code: str, message: str, severity: Literal['error', 'warning'] = 'error', path: str \| None = None, meta: dict[str, Any] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `contracts.ValidationIssue.code` | field | `str = requerido` | conservar dato documentado |
| `contracts.ValidationIssue.message` | field | `str = requerido` | conservar dato documentado |
| `contracts.ValidationIssue.severity` | field | `Literal['error', 'warning'] = 'error'` | conservar dato documentado |
| `contracts.ValidationIssue.path` | field | `str \| None = None` | conservar dato documentado |
| `contracts.ValidationIssue.meta` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `contracts.ValidationResult` | class | `(*, ok: bool = True, issues: list[ValidationIssue] = Field(default_factory=list))` | tipo retornado; sin constructor alternativo |
| `contracts.ValidationResult.ok` | field | `bool = True` | conservar dato documentado |
| `contracts.ValidationResult.issues` | field | `list[ValidationIssue] = Field(default_factory=list)` | conservar dato documentado |
| `contracts.ValidationResult.add` | method | `(self, code: str, message: str, *, severity: Literal['error', 'warning']='error', path: str \| None=None, meta: dict[str, Any] \| None=None)` | hacer interno o sustituir |
| `contracts.ValidationResult.raise_if_failed` | method | `(self)` | hacer interno o sustituir |
| `contracts.ValidationResult.to_dict` | method | `(self)` | conservar |
| `lineage.LineageMemory` | class | `(*, schema_version: str = LINEAGE_SCHEMA_VERSION, name: str = 'run', question: str = '', goal: str = '', answer: str = '', ok: bool = True, steps: list[LineageStep] = Field(default_factory=list), usage: dict[str, Any] = Field(default_factory=dict), validation: dict[str, Any] \| None = None, tags: list[str] = Field(default_factory=list), metadata: dict[str, Any] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `lineage.LineageMemory.schema_version` | field | `str = LINEAGE_SCHEMA_VERSION` | conservar dato documentado |
| `lineage.LineageMemory.name` | field | `str = 'run'` | conservar dato documentado |
| `lineage.LineageMemory.question` | field | `str = ''` | conservar dato documentado |
| `lineage.LineageMemory.goal` | field | `str = ''` | conservar dato documentado |
| `lineage.LineageMemory.answer` | field | `str = ''` | conservar dato documentado |
| `lineage.LineageMemory.ok` | field | `bool = True` | conservar dato documentado |
| `lineage.LineageMemory.steps` | field | `list[LineageStep] = Field(default_factory=list)` | conservar dato documentado |
| `lineage.LineageMemory.usage` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `lineage.LineageMemory.validation` | field | `dict[str, Any] \| None = None` | conservar dato documentado |
| `lineage.LineageMemory.tags` | field | `list[str] = Field(default_factory=list)` | conservar dato documentado |
| `lineage.LineageMemory.metadata` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `lineage.LineageMemory.from_run_result` | method | `(cls, result: Any, *, name: str='run', question: str \| None=None, goal: str='', tags: list[str] \| None=None, metadata: dict[str, Any] \| None=None, max_tool_rows: int=3)` | hacer interno o sustituir |
| `lineage.LineageMemory.from_result` | method | `(cls, result: Any, **kwargs: Any)` | hacer interno o sustituir |
| `lineage.LineageMemory.compact` | method | `(self, *, max_steps: int \| None=None)` | hacer interno o sustituir |
| `lineage.LineageMemory.explain` | method | `(self)` | conservar |
| `lineage.LineageMemory.human_text` | method | `(self, *, include_evidence: bool=True, max_evidence_chars: int=520, max_how_items: int=6, max_evidence_items: int=5, render_mode: Literal['compact', 'audit', 'debug']='audit')` | hacer interno o sustituir |
| `lineage.LineageMemory.to_prompt_context` | method | `(self, *, max_chars: int=1600)` | conservar |
| `lineage.LineageMemory.estimated_context_savings` | method | `(self, raw: Any, *, max_chars: int=1600)` | hacer interno o sustituir |
| `lineage.LineageMemory.to_dict` | method | `(self)` | conservar |
| `lineage.LineageStep` | class | `(*, step_id: str, kind: LineageKind, title: str, summary: str, source: str = '', why: str = '', evidence: dict[str, Any] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `lineage.LineageStep.step_id` | field | `str = requerido` | conservar dato documentado |
| `lineage.LineageStep.kind` | field | `LineageKind = requerido` | conservar dato documentado |
| `lineage.LineageStep.title` | field | `str = requerido` | conservar dato documentado |
| `lineage.LineageStep.summary` | field | `str = requerido` | conservar dato documentado |
| `lineage.LineageStep.source` | field | `str = ''` | conservar dato documentado |
| `lineage.LineageStep.why` | field | `str = ''` | conservar dato documentado |
| `lineage.LineageStep.evidence` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `lineage.LineageStep.compact` | method | `(self)` | hacer interno o sustituir |
| `toolkit.RunResult` | class | `(*, text: str = '', final: dict[str, Any] = Field(default_factory=dict), data: dict[str, Any] = Field(default_factory=dict), ok: bool = True, messages: list[dict[str, Any]] = Field(default_factory=list), tool_events: list[ToolEvent] = Field(default_factory=list), raw_responses: list[dict[str, Any]] = Field(default_factory=list), usage: dict[str, Any] = Field(default_factory=dict), engine: str = BEDROCK_RUNTIME_ENGINE, model: str = '', mode: str = 'default', trace_schema_version: str = TRACE_SCHEMA_VERSION, validation: dict[str, Any] \| None = None, errors: list[dict[str, Any]] = Field(default_factory=list), meta: dict[str, Any] = Field(default_factory=dict), execution_id: str \| None = None, parent_execution_id: str \| None = None, children: list['RunResult'] = Field(default_factory=list))` | conservar |
| `toolkit.RunResult.text` | field | `str = ''` | conservar dato documentado |
| `toolkit.RunResult.final` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `toolkit.RunResult.data` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `toolkit.RunResult.ok` | field | `bool = True` | conservar dato documentado |
| `toolkit.RunResult.messages` | field | `list[dict[str, Any]] = Field(default_factory=list)` | conservar dato documentado |
| `toolkit.RunResult.tool_events` | field | `list[ToolEvent] = Field(default_factory=list)` | conservar dato documentado |
| `toolkit.RunResult.raw_responses` | field | `list[dict[str, Any]] = Field(default_factory=list)` | conservar dato documentado |
| `toolkit.RunResult.usage` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `toolkit.RunResult.engine` | field | `str = BEDROCK_RUNTIME_ENGINE` | conservar dato documentado |
| `toolkit.RunResult.model` | field | `str = ''` | conservar dato documentado |
| `toolkit.RunResult.mode` | field | `str = 'default'` | conservar dato documentado |
| `toolkit.RunResult.trace_schema_version` | field | `str = TRACE_SCHEMA_VERSION` | conservar dato documentado |
| `toolkit.RunResult.validation` | field | `dict[str, Any] \| None = None` | conservar dato documentado |
| `toolkit.RunResult.errors` | field | `list[dict[str, Any]] = Field(default_factory=list)` | conservar dato documentado |
| `toolkit.RunResult.meta` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `toolkit.RunResult.execution_id` | field | `str \| None = None` | conservar dato documentado |
| `toolkit.RunResult.parent_execution_id` | field | `str \| None = None` | conservar dato documentado |
| `toolkit.RunResult.children` | field | `list['RunResult'] = Field(default_factory=list)` | conservar dato documentado |
| `toolkit.RunResult.native_result` | property | `(self)` | hacer interno |
| `toolkit.RunResult.add_child` | method | `(self, child: 'RunResult')` | hacer interno o sustituir |
| `toolkit.RunResult.walk` | method | `(self)` | conservar |
| `toolkit.RunResult.from_bedrock_runtime` | method | `(cls, runtime_result: Any, *, engine: str, model: str, mode: str='default', data: dict[str, Any] \| None=None, contract: AgentContract \| dict[str, Any] \| None=None)` | hacer interno o sustituir |
| `toolkit.RunResult.apply_validation` | method | `(self, validation: ValidationResult \| dict[str, Any])` | hacer interno o sustituir |
| `toolkit.RunResult.check_invariants` | method | `(self)` | conservar |
| `toolkit.RunResult.raise_if_inconsistent` | method | `(self)` | hacer interno o sustituir |
| `toolkit.RunResult.normalized` | method | `(self)` | hacer proyección interna |
| `toolkit.RunResult.to_dict` | method | `(self)` | conservar |
| `toolkit.RunResult.should_retry` | method | `(self)` | hacer interno o sustituir |
| `toolkit.RunResult.lineage` | method | `(self, **kwargs: Any)` | conservar |
| `toolkit.RunResult.compact_trace` | method | `(self)` | eliminar alias |
| `toolkit.RunResult.trace` | method | `(self, mode: str='compact')` | conservar |
| `toolkit.RunResult.validate` | method | `(self, contract: AgentContract \| dict[str, Any] \| None=None)` | hacer interno o sustituir |
| `schemas.results.ToolEvent` | class | `(*, id: str \| None = None, name: str, ok: bool, input: dict[str, JsonValue] = Field(default_factory=dict), output: JsonValue = None, error: ExecutionError \| None = None)` | tipo retornado; sin constructor alternativo |
| `schemas.results.ToolEvent.id` | field | `str \| None = None` | conservar dato documentado |
| `schemas.results.ToolEvent.name` | field | `str = requerido` | conservar dato documentado |
| `schemas.results.ToolEvent.ok` | field | `bool = requerido` | conservar dato documentado |
| `schemas.results.ToolEvent.input` | field | `dict[str, JsonValue] = Field(default_factory=dict)` | conservar dato documentado |
| `schemas.results.ToolEvent.output` | field | `JsonValue = None` | conservar dato documentado |
| `schemas.results.ToolEvent.error` | field | `ExecutionError \| None = None` | conservar dato documentado |
| `tools.events.ToolEvent` | class | `(*, id: str, name: str, input: dict[str, Any] = Field(default_factory=dict), output: dict[str, Any] = Field(default_factory=dict), ok: bool = True, error: dict[str, Any] \| None = None, duration_ms: float \| None = None, meta: dict[str, Any] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `tools.events.ToolEvent.id` | field | `str = requerido` | conservar dato documentado |
| `tools.events.ToolEvent.name` | field | `str = requerido` | conservar dato documentado |
| `tools.events.ToolEvent.input` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `tools.events.ToolEvent.output` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `tools.events.ToolEvent.ok` | field | `bool = True` | conservar dato documentado |
| `tools.events.ToolEvent.error` | field | `dict[str, Any] \| None = None` | conservar dato documentado |
| `tools.events.ToolEvent.duration_ms` | field | `float \| None = None` | conservar dato documentado |
| `tools.events.ToolEvent.meta` | field | `dict[str, Any] = Field(default_factory=dict)` | conservar dato documentado |
| `tools.events.ToolEvent.from_runtime_record` | method | `(cls, record: Any)` | hacer interno o sustituir |

## serving

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `toolkit.model_artifact` | function | `(model, *, base_model=None, adapter_path=None, tokenizer=None, revision=None, quantization=None, metadata=None)` | conservar |
| `toolkit.model_server` | function | `(artifact, **configuration)` | conservar |
| `schemas.serving.EndpointInfo` | class | `(*, schema_version: str = SERVING_SCHEMA_VERSION, backend: StrictStr, base_url: StrictStr, model_id: StrictStr, api_key_configured: StrictBool = False, pid: StrictInt \| None = None, owned: StrictBool = False)` | tipo retornado; sin constructor alternativo |
| `schemas.serving.EndpointInfo.schema_version` | field | `str = SERVING_SCHEMA_VERSION` | conservar dato documentado |
| `schemas.serving.EndpointInfo.supported_schema_version` | method | `(cls, value: str)` | hacer interno |
| `schemas.serving.EndpointInfo.backend` | field | `StrictStr = requerido` | conservar dato documentado |
| `schemas.serving.EndpointInfo.base_url` | field | `StrictStr = requerido` | exponer como url |
| `schemas.serving.EndpointInfo.model_id` | field | `StrictStr = requerido` | unificar nombre |
| `schemas.serving.EndpointInfo.api_key_configured` | field | `StrictBool = False` | conservar dato documentado |
| `schemas.serving.EndpointInfo.pid` | field | `StrictInt \| None = None` | conservar dato documentado |
| `schemas.serving.EndpointInfo.owned` | field | `StrictBool = False` | conservar dato documentado |
| `schemas.serving.ModelArtifact` | class | `(*, schema_version: str = SERVING_SCHEMA_VERSION, model_id: StrictStr, base_model_id: StrictStr \| None = None, adapter_path: StrictStr \| None = None, tokenizer_id: StrictStr \| None = None, revision: StrictStr \| None = None, quantization: StrictStr \| None = None, metadata: dict[str, JsonValue] = Field(default_factory=dict))` | tipo retornado; sin constructor alternativo |
| `schemas.serving.ModelArtifact.schema_version` | field | `str = SERVING_SCHEMA_VERSION` | conservar dato documentado |
| `schemas.serving.ModelArtifact.supported_schema_version` | method | `(cls, value: str)` | hacer interno |
| `schemas.serving.ModelArtifact.model_id` | field | `StrictStr = requerido` | unificar nombre |
| `schemas.serving.ModelArtifact.base_model_id` | field | `StrictStr \| None = None` | unificar nombre |
| `schemas.serving.ModelArtifact.adapter_path` | field | `StrictStr \| None = None` | conservar dato documentado |
| `schemas.serving.ModelArtifact.tokenizer_id` | field | `StrictStr \| None = None` | unificar nombre |
| `schemas.serving.ModelArtifact.revision` | field | `StrictStr \| None = None` | conservar dato documentado |
| `schemas.serving.ModelArtifact.quantization` | field | `StrictStr \| None = None` | conservar dato documentado |
| `schemas.serving.ModelArtifact.metadata` | field | `dict[str, JsonValue] = Field(default_factory=dict)` | conservar dato documentado |
| `schemas.serving.ServerHealth` | class | `(*, schema_version: str = SERVING_SCHEMA_VERSION, status: Literal['starting', 'healthy', 'stopped', 'failed', 'timeout'], endpoint: EndpointInfo, detail: StrictStr \| None = None)` | tipo retornado; sin constructor alternativo |
| `schemas.serving.ServerHealth.schema_version` | field | `str = SERVING_SCHEMA_VERSION` | conservar dato documentado |
| `schemas.serving.ServerHealth.supported_schema_version` | method | `(cls, value: str)` | hacer interno |
| `schemas.serving.ServerHealth.status` | field | `Literal['starting', 'healthy', 'stopped', 'failed', 'timeout'] = requerido` | conservar dato documentado |
| `schemas.serving.ServerHealth.endpoint` | field | `EndpointInfo = requerido` | conservar dato documentado |
| `schemas.serving.ServerHealth.detail` | field | `StrictStr \| None = None` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec` | class | `(*, schema_version: str = SERVING_SCHEMA_VERSION, backend: Literal['vllm'] = 'vllm', artifact: ModelArtifact, profile: Literal['fast', 'medium', 'power', 'custom'] = 'fast', served_model_name: StrictStr \| None = None, host: StrictStr = '127.0.0.1', port: StrictInt = Field(default=8000, ge=1, le=65535), gpu_memory_utilization: StrictFloat = Field(default=0.4, gt=0, le=1), max_model_len: StrictInt = Field(default=2048, ge=1), max_num_seqs: StrictInt = Field(default=4, ge=1), enable_auto_tool_choice: StrictBool = True, tool_call_parser: StrictStr \| None = 'hermes', reasoning_parser: StrictStr \| None = None, generation_config: StrictStr \| None = 'vllm', api_key: SecretStr = Field(default=SecretStr('vllm'), exclude=True, repr=False), startup_timeout_s: StrictFloat = Field(default=600.0, gt=0), log_path: StrictStr = 'vllm-server.log', binary: StrictStr = 'vllm', extra_args: tuple[StrictStr, ...] = ())` | tipo retornado; sin constructor alternativo |
| `schemas.serving.VLLMServerSpec.schema_version` | field | `str = SERVING_SCHEMA_VERSION` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.supported_schema_version` | method | `(cls, value: str)` | hacer interno |
| `schemas.serving.VLLMServerSpec.backend` | field | `Literal['vllm'] = 'vllm'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.artifact` | field | `ModelArtifact = requerido` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.profile` | field | `Literal['fast', 'medium', 'power', 'custom'] = 'fast'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.served_model_name` | field | `StrictStr \| None = None` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.host` | field | `StrictStr = '127.0.0.1'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.port` | field | `StrictInt = Field(default=8000, ge=1, le=65535)` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.gpu_memory_utilization` | field | `StrictFloat = Field(default=0.4, gt=0, le=1)` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.max_model_len` | field | `StrictInt = Field(default=2048, ge=1)` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.max_num_seqs` | field | `StrictInt = Field(default=4, ge=1)` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.enable_auto_tool_choice` | field | `StrictBool = True` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.tool_call_parser` | field | `StrictStr \| None = 'hermes'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.reasoning_parser` | field | `StrictStr \| None = None` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.generation_config` | field | `StrictStr \| None = 'vllm'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.api_key` | field | `SecretStr = Field(default=SecretStr('vllm'), exclude=True, repr=False)` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.startup_timeout_s` | field | `StrictFloat = Field(default=600.0, gt=0)` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.log_path` | field | `StrictStr = 'vllm-server.log'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.binary` | field | `StrictStr = 'vllm'` | conservar dato documentado |
| `schemas.serving.VLLMServerSpec.extra_args` | field | `tuple[StrictStr, ...] = ()` | conservar dato documentado |
| `serving.vllm.VLLMServer` | class | `(self, spec: VLLMServerSpec, *, popen_factory: Callable[..., subprocess.Popen[Any]]=subprocess.Popen, clock: Callable[[], float]=time.monotonic, sleeper: Callable[[float], None]=time.sleep)` | tipo retornado; sin constructor alternativo |
| `serving.vllm.VLLMServer.spec` | field | `Any = spec` | hacer interno |
| `serving.vllm.VLLMServer.endpoint` | property | `(self)` | conservar |
| `serving.vllm.VLLMServer.command` | property | `(self)` | conservar |
| `serving.vllm.VLLMServer.inspect` | method | `(self)` | conservar |
| `serving.vllm.VLLMServer.start` | method | `(self)` | conservar |
| `serving.vllm.VLLMServer.health` | method | `(self)` | conservar |
| `serving.vllm.VLLMServer.runtime` | method | `(self, *, scheduler: SchedulerConfig \| dict[str, Any] \| None=None, metadata: dict[str, Any] \| None=None)` | retirar del público |
| `serving.vllm.VLLMServer.stop` | method | `(self)` | conservar |
| `serving.vllm.VLLMServer.running` | method | `(self)` | retirar alternativa pública |
| `serving.vllm.VLLMServer.__enter__` | protocol | `(self)` | hacer interno o sustituir |
| `serving.vllm.VLLMServer.__exit__` | protocol | `(self, exc_type: type[BaseException] \| None, exc: BaseException \| None, traceback: TracebackType \| None)` | hacer interno o sustituir |

## skills

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `toolkit.skill` | function | `(*, name: str, description: str='', tools: Iterable[Any] \| None=None, prompts: dict[str, Any] \| None=None, contracts: dict[str, Any] \| None=None, policy: dict[str, Any] \| None=None, metadata: dict[str, Any] \| None=None, version: str='0.1.0')` | conservar |
| `toolkit.load_skill` | function | `(name_or_path: Any, **kwargs: Any)` | conservar |
| `skills.skill.Skill` | class | `(self, *, name: str, description: str='', tools: Iterable[Tool \| Callable[..., Any]] \| None=None, prompts: Mapping[str, Any] \| None=None, contracts: Mapping[str, Any] \| None=None, policy: Mapping[str, Any] \| None=None, metadata: Mapping[str, Any] \| None=None, version: str='0.1.0')` | tipo retornado; sin constructor alternativo |
| `skills.skill.Skill.name` | field | `Any = name.strip() if isinstance(name, str) else ''` | conservar dato documentado |
| `skills.skill.Skill.description` | field | `Any = str(description or '').strip()` | conservar dato documentado |
| `skills.skill.Skill.version` | field | `Any = str(version or '0.1.0')` | conservar dato documentado |
| `skills.skill.Skill.prompts` | field | `Any = _string_keyed_dict(prompts, field_name='prompts')` | sustituir o retirar |
| `skills.skill.Skill.contracts` | field | `Any = _string_keyed_dict(contracts, field_name='contracts')` | sustituir o retirar |
| `skills.skill.Skill.policy` | field | `Any = _string_keyed_dict(policy, field_name='policy')` | sustituir o retirar |
| `skills.skill.Skill.metadata` | field | `Any = _string_keyed_dict(metadata, field_name='metadata')` | conservar dato documentado |
| `skills.skill.Skill.identity` | property | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.compose` | method | `(cls, *skills: 'Skill', name: str, description: str='', version: str='0.1.0', metadata: Mapping[str, Any] \| None=None, on_conflict: str='error')` | hacer interno o sustituir |
| `skills.skill.Skill.composition` | method | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.tool_names` | property | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.tools` | property | `(self)` | conservar |
| `skills.skill.Skill.instructions` | property | `(self)` | conservar |
| `skills.skill.Skill.prompt` | method | `(self, name: str='user_prompt', default: Any \| None=None)` | hacer interno o sustituir |
| `skills.skill.Skill.tool` | method | `(self, name: str)` | hacer interno o sustituir |
| `skills.skill.Skill.available_tools` | method | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.info` | method | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.describe` | method | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.check` | method | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.__len__` | protocol | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.__iter__` | protocol | `(self)` | hacer interno o sustituir |
| `skills.skill.Skill.__repr__` | protocol | `(self)` | hacer interno o sustituir |

## tools

| Entrada / miembro | Tipo | Firma o dato actual | Decisión propuesta |
|---|---|---|---|
| `toolkit.tool` | function | `(function: Callable[..., Any] \| None=None, /, *, name: str \| None=None, description: str \| None=None, input_schema: type[BaseModel] \| None=None, output_schema: type[BaseModel] \| None=None, input_model: type[BaseModel] \| None=None, output_model: type[BaseModel] \| None=None, input: type[BaseModel] \| None=None, output: type[BaseModel] \| None=None, metadata: dict[str, Any] \| None=None, strict: bool=True)` | conservar |
| `tools.tool.Tool` | class | `(self, function: Callable[..., Any] \| None=None, *, name: str \| None=None, description: str \| None=None, input_schema: type[BaseModel] \| None=None, output_schema: type[BaseModel] \| None=None, input_model: type[BaseModel] \| None=None, output_model: type[BaseModel] \| None=None, input: type[BaseModel] \| None=None, output: type[BaseModel] \| None=None, metadata: dict[str, Any] \| None=None, strict: bool=True)` | tipo retornado; sin constructor alternativo |
| `tools.tool.Tool.name` | field | `Any = (name or inferred_name or '').strip() if isinstance(name or inferred_name, str) else ''` | conservar dato documentado |
| `tools.tool.Tool.function` | field | `Any = function` | conservar dato documentado |
| `tools.tool.Tool.input_schema` | field | `Any = _resolve_schema_alias('input', input_schema=input_schema, input_model=input_model, input=input)` | conservar dato documentado |
| `tools.tool.Tool.output_schema` | field | `Any = _resolve_schema_alias('output', output_schema=output_schema, output_model=output_model, output=output)` | conservar dato documentado |
| `tools.tool.Tool.metadata` | field | `Any = dict(metadata or {})` | conservar dato documentado |
| `tools.tool.Tool.strict` | field | `Any = bool(strict)` | conservar dato documentado |
| `tools.tool.Tool.identity` | property | `(self)` | hacer interno o sustituir |
| `tools.tool.Tool.info` | method | `(self)` | hacer interno o sustituir |
| `tools.tool.Tool.describe` | method | `(self)` | hacer interno o sustituir |
| `tools.tool.Tool.check` | method | `(self)` | hacer interno o sustituir |
| `tools.tool.Tool.run` | method | `(self, input_payload: Any=None, context: Any=None)` | conservar |

## Entradas estables de 2.1.2

Esta tabla es un cruce de nombres; no conserva firmas ni promete compatibilidad.

| Entrada anterior | Decisión | Destino |
|---|---|---|
| `skill` | conservar nombre; revisar firma | skill |
| `agent` | retirar entrada duplicada; preservar capacidad | Agent |
| `system` | retirar entrada duplicada; preservar capacidad | System |
| `environment` | retirar entrada duplicada; preservar capacidad | Environment |
| `eval` | retirar entrada duplicada; preservar capacidad | Eval |
| `runtime` | conservar nombre; revisar firma | runtime |
| `model_artifact` | conservar nombre; revisar firma | model_artifact |
| `model_server` | conservar nombre; revisar firma | model_server |
| `provider` | retirar entrada duplicada; preservar capacidad | runtime |
| `framework` | conservar nombre; revisar firma | framework |
| `scheduler` | retirar entrada duplicada; preservar capacidad | runtime (actor) / Limits (flujo) |
| `load_skill` | conservar nombre; revisar firma | load_skill |
| `AgenticSystem` | retirar entrada duplicada; preservar capacidad | System |
| `Agent` | conservar nombre; revisar firma | Agent |
| `Tool` | retirar entrada duplicada; preservar capacidad | tool |
| `ToolSet` | retirar entrada duplicada; preservar capacidad | skill(tools=...) |
| `Executable` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `AsyncExecutable` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `toolset` | retirar entrada duplicada; preservar capacidad | skill(tools=...) |
| `api_contract` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `exercise_api` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `ExecutionPlan` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `CompiledSystem` | retirar entrada duplicada; preservar capacidad | unit.compile() |
| `SequentialPlan` | retirar entrada duplicada; preservar capacidad | Sequence |
| `ParallelPlan` | retirar entrada duplicada; preservar capacidad | Parallel |
| `tool` | conservar nombre; revisar firma | tool |
| `expect` | retirar entrada duplicada; preservar capacidad | contract.tool_expectation (diccionario cerrado) |
| `human_result` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `Skill` | retirar entrada duplicada; preservar capacidad | skill |
| `LoadedSkill` | retirar entrada duplicada; preservar capacidad | load_skill devuelve Skill |
| `AgentContract` | retirar entrada duplicada; preservar capacidad | Agent.contract (diccionario cerrado) |
| `ContractPolicySpec` | retirar entrada duplicada; preservar capacidad | declaración de Agent |
| `RunPolicy` | retirar entrada duplicada; preservar capacidad | Agent.policy (diccionario cerrado) |
| `validate_contract_policy` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `RunResult` | conservar nombre; revisar firma | RunResult |
| `LineageMemory` | retirar entrada duplicada; preservar capacidad | result.lineage() |
| `LineageStep` | retirar entrada duplicada; preservar capacidad | result.lineage().steps |
| `lineage_memory` | retirar entrada duplicada; preservar capacidad | result.lineage() |
| `LINEAGE_SCHEMA_VERSION` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `AUTO_PROVIDER_ENV_VAR` | retirar comportamiento público | selección explícita de runtime; sin fallback |
| `DEFAULT_AUTO_PROVIDER_PRIORITY` | retirar comportamiento público | selección explícita de runtime; sin fallback |
| `RuntimeConfig` | retirar entrada duplicada; preservar capacidad | runtime |
| `ModelArtifact` | retirar entrada duplicada; preservar capacidad | model_artifact |
| `ModelServer` | retirar entrada duplicada; preservar capacidad | model_server |
| `VLLMServerSpec` | retirar entrada duplicada; preservar capacidad | model_server |
| `VLLMServer` | retirar entrada duplicada; preservar capacidad | model_server |
| `EndpointInfo` | retirar entrada duplicada; preservar capacidad | server.endpoint |
| `ServerHealth` | retirar entrada duplicada; preservar capacidad | server.health() |
| `ModelProviderConfig` | retirar entrada duplicada; preservar capacidad | runtime |
| `compatibility_matrix` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `dependency_target` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `compatibility_report` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `normalize_provider_priority` | retirar comportamiento público | selección explícita de runtime; sin fallback |
| `resolve_auto_provider` | retirar comportamiento público | selección explícita de runtime; sin fallback |
| `SchedulerConfig` | retirar entrada duplicada; preservar capacidad | runtime |
| `OutputSchema` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `final_answer` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `normalize_output` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `output_schema` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `FrameworkConfig` | retirar entrada duplicada; preservar capacidad | framework |
| `GraphApp` | retirar entrada duplicada; preservar capacidad | Graph |
| `AgenticGraph` | retirar entrada duplicada; preservar capacidad | Graph |
| `agent_node` | retirar entrada duplicada; preservar capacidad | Agent como nodo de Graph |
| `graph` | retirar entrada duplicada; preservar capacidad | Graph |
| `EvalReport` | retirar entrada duplicada; preservar capacidad | Eval.run().data |
| `JudgeRubric` | retirar entrada duplicada; preservar capacidad | Eval.judge / contrato de juez propuestos |
| `JudgeResult` | retirar entrada duplicada; preservar capacidad | Eval: resultado del juez |
| `Evaluator` | retirar entrada duplicada; preservar capacidad | Eval |
| `run_eval` | retirar entrada duplicada; preservar capacidad | Eval.run |
| `AgenticEnvironment` | retirar entrada duplicada; preservar capacidad | Environment |
| `build_agent_step_graph` | retirar entrada duplicada; preservar capacidad | Environment(unit=Agent(...)) |
| `agent_output` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `show_json` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `show` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `compose_result` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `aws_environment_snapshot` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `boto3_session_snapshot` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `ollama_environment_snapshot` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `openai_environment_snapshot` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `vllm_environment_snapshot` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `run_result_output` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `run_result_view` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `run_result_summary` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `environment_summary` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `eval_report_summary` | retirar helper público; conservar representación | RunResult / presentación de aplicación; requisitos de structured output deben probarse antes de retirar implementación |
| `core` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `providers` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `integrations` | hacer interno; sin alternativa pública paralela | docs/API_213_DISPOSITION.md: capacidad anterior y alcance pendiente |
| `__version__` | conservar nombre; revisar firma | __version__ |

## Límites del inventario

- Dynamic attributes on SDK/provider native objects are not statically enumerable; native handles should become private.
- Open mappings (framework SDK options, metadata, JSON payloads) are recorded as mappings, not a promise to enumerate upstream APIs.
- Generated dataclass/Pydantic constructors list declared and inherited fields; Field expressions retain source semantics.
- Submodule inventory includes implementation definitions, inherited members and imports; static presence does not imply supported public API.

Los métodos heredados de Pydantic y todos los símbolos de submódulos quedan enumerados en el JSON. No se ocultan de este inventario aunque se proponga retirarlos de la superficie pública.
