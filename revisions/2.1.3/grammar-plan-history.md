# 2.1.3 — API única implementada

La instrucción vigente sustituye la compatibilidad: la implementación está en
`src/agentic_systems/`, con una sola API y sin fachada paralela.
La referencia normativa es [API 2.1.3](API_213.md); las firmas efectivas están
en el [inventario actual](API_213_SURFACE.md), las decisiones aplicadas en
[disposición](API_213_DISPOSITION.md) y la evidencia en el
[reporte offline](../revisions/2.1.3/implementation-evidence/REPORT.md).
El inventario anterior se conserva como fotografía histórica, no como API vigente.

## Plan histórico: compatibilidad con 2.1.2 (sustituido)

Status: design plus an isolated, executed offline prototype. The released runtime
remains unchanged; no deprecation, inference run or new release is authorized.

The goal is a shared control-flow model for Agent and System, followed by a
clear learning path. Both may own sequential, parallel or graph flows. Graph is
a representation of control flow, not a conceptual layer after System.

This is a future design contract, not a description of implemented symmetry.
The production runtime is untouched; the executed facade is isolated in an
example. It does not amend current 2.1.2 normative contracts, add released
methods or select final production constructor parameters. Keep all 89
existing stable exports, their signatures and the 468 export/member contract
IDs compatible with 2.1.2. Keep CLI commands, extras, serialization, error and
lineage behavior. Published wheels, tags and evidence remain immutable.

## Owner, flow and execution implementation

| Dimension | Meaning | Choices |
|---|---|---|
| Owner | Identity and boundary whose work is performed | Agent or System |
| Control flow | Dependencies, ordering, branching and synchronization | Sequential, parallel or graph |
| Flow backend | Implementation that prepares and executes the topology | Native implementation or an explicit adapter such as LangGraph |
| Agent framework | Implementation of an individual Agent action/loop | native, LangGraph, OpenAI Agents or Strands, where supported |
| Model provider | Runtime/endpoint for model-backed actions | Explicit runtime configuration; Python for deterministic operations |

The same flow semantics apply at both ownership levels. Agent retains its actor
identity and internal stages. System retains its composition identity and
coordinates executable units, including Agents and nested Systems. Neither
level forces every step to become another Agent. Skills package capabilities;
they do not acquire an autonomous execution loop.

An outer System's flow backend does not implicitly override a nested Agent's
framework or provider. Each boundary has one execution owner; adapters must not
execute a stage twice through competing loops.

```text
System flow: receive -> [Agent A || Agent B] -> decide
Agent A flow: normalize -> [lookup X || lookup Y] -> analyze
```

Both flows may contain conditional graph paths. Sequence and parallel are useful
control-flow forms; graphs can express them subject to backend capabilities.
This does not imply that the current portable graph supports parallel branches.

## Verified 2.1.2 behavior and the gap

| Current entry | Actual behavior | Gap to the target |
|---|---|---|
| `agent.run(input)` | Executes the configured Agent/framework path | No shared declared-flow lifecycle with System yet |
| `agent.pipeline(*steps, execution=...)` | Returns a new CompiledSystem containing `(agent, *steps)`; defaults to SequentialPlan | Does not install a flow used by later agent.run calls; its result is named System |
| `system.run(input, execution=...)` | Calls compile and runs the result | Already provides implicit preparation, unlike other entry paths |
| `system.compile(execution=...)` | Returns CompiledSystem; defaults to SequentialPlan | SequentialPlan and ParallelPlan share an interface, but there is no equivalent built-in graph plan |
| `toolkit.graph(...)` | Usually returns GraphApp with run/invoke; run returns backend state | Different preparation/result boundary; auto depends on installed packages |
| `system.graph(...)` | Returns a LangGraph builder; compile returns native CompiledStateGraph | Caller switches from run to native invoke |
| `framework="langgraph"` on Agent | Uses a real one-node StateGraph to invoke the engine | Does not compile arbitrary internal Agent stages into a business graph |

Sources: [Agent.pipeline](../src/agentic_systems/agents.py),
[System execution](../src/agentic_systems/system.py),
[plans and compiled execution](../src/agentic_systems/execution.py),
[graph integration](../src/agentic_systems/integrations/langgraph.py) and
[LangGraph Agent adapter](../src/agentic_systems/integrations/adapters/langgraph.py).

Offline observations confirmed that an Agent returned 4, its returned pipeline
with an extra transformation returned 40, and the original Agent still returned
4. A portable graph returned a dict; a graph compiled through system.graph
exposed invoke rather than run. Preserve these existing behaviors on legacy
paths rather than silently reinterpreting them.

The portable graph currently supports a single active path with conditional
routing and bounded cycles. It rejects parallel branches; ParallelPlan supports
concurrent executable units separately. Composing a graph as a runnable unit
does not make it interchangeable with ExecutionPlan.

## Shared conceptual grammar: target, not Python syntax

```text
Owner       := Agent | System
OwnedFlow   := Owner + Flow + effective execution configuration
Flow        := Step | Sequential(Flow...) | Parallel(Flow..., join) | Graph(nodes, transitions)
Step        := an adapted executable action or nested owned unit
Lifecycle   := declare -> inspect -> compile -> run -> RunResult
Usual path  := declare -> run -> RunResult
```

These names describe semantics, not new exports, a parser or a public DSL.
Choose final Python names and opt-in configuration after an offline prototype
and compatibility review. Reuse existing plans/adapters where appropriate;
do not accumulate another set of equivalent public builders.

| Flow | Shared target semantics for Agent and System |
|---|---|
| Sequential | Execute declared steps in order with explicit next-input/output bindings. Keep the existing data/text/final forwarding rules on legacy paths. |
| Parallel | Independent branches start from a declared input snapshot with isolated branch state; an explicit mapping/reducer joins results. Preserve outcomes in declared order regardless of completion order. |
| Graph | Explicit nodes, transitions, routers and fork/join semantics. State schemas, merge rules, entry/exit behavior and cycle/step limits are inspectable. |
| Nested | A step may invoke an Agent or System with its own flow. Preserve its owner identity, state scope and child lineage rather than flattening the definition. |

Compile checks static contracts where possible; dynamic input, branch and output
checks remain runtime obligations. Define supported snapshot types and reducer
behavior before claiming arbitrary Python objects can safely be copied. Missing
reducers or unsupported topology fail explicitly.

Compile does not execute a router to predict its branch. An Agent's default
model/tool action is a leaf inside its flow, not an implicit callback to that
same Agent's run method. Reject explicit self-invocation cycles and bound runtime
recursion so installing a flow cannot recursively rerun its owner without limit.

## Coherent run and compile contract: target only

For either owner, run executes its declared flow and returns RunResult. It may
prepare a missing executable using the same compiler as explicit compile.
Calling compile is optional for normal use.

Compile validates known structure/contracts, resolves effective configuration
and backend, and produces a reusable executable representation. It must not call
a model, execute a Tool/router, connect MCP services or start a model server.
Optional SDK imports and local structural validation may occur; compilation
does not prove that external credentials, endpoints or services are ready.

Direct run and compile-then-run have equivalent step selection, bindings, errors
and result/lineage structure for the same definition, input and configuration.
This is behavioral equivalence, not identical generated IDs, timing or model
wording. Compile produces no execution events; implicit preparation must not
execute a stage twice.

The prepared artifact identifies its Agent/System owner, topology, resolved
configuration and backend. It snapshots structure/configuration, not arbitrary
callback closures or external resources. Definition changes invalidate cached
preparation. Repeated runs have isolated state and fresh execution IDs. Define
cache invalidation and concurrency behavior before claiming reusable compilation.

Async execution preserves the same flow and evidence semantics. Parent limits
and deadlines bound nested scopes; adapters cannot reset budgets or double-count
one observed attempt. Parallel cancellation accounts for workers finishing after
a timeout and retains their outcomes. Joins and semantic judging cannot hide a
required failure. Retry/effect and idempotency rules remain explicit.

The shared facade returns RunResult, retaining graph state as an explicit data
projection and native SDK objects as advanced access/evidence. Preserve owner,
execution/parent IDs, branch/node identity, Tool events, usage, errors and child
results. Specify exact serialization mappings before implementation. Do not
silently change GraphApp's current state return or existing closed schemas;
new projections need their own compatibility gates.

There is no Agent.compile in the current 2.1.2 public API. Shared compile behavior
is a target requiring implementation design. Do not advertise it as available
or invent a flow keyword on current factories in runnable examples.

## LangGraph integration and capability boundary

Keep two explicit roles: an Agent framework adapter and a backend for a declared
flow. The existing one-node Agent adapter proves an invocation boundary, not
automatic compilation of internal business steps.

The target flow adapter translates supported nodes, edges, input/output state,
routers, reducers and limits to StateGraph semantics. Compile through the SDK,
invoke through the shared facade, and map state/errors/usage/lineage back without
losing native details. Portable code must not alternate run and invoke according
to which backend implements its flow.

Checkpointing, streaming, interrupts and other SDK-specific features remain an
explicit advanced native escape hatch. They are not automatically portable.
Nested interoperability tests must show each node executes once with its own
identity, framework and provider preserved.

| Operation | Current portable graph | Current LangGraph integration | Planned gate |
|---|---|---|---|
| Ordered / conditional single-path routes | Supported subset | Explicit StateGraph topology | Same declared path and state on supported routes |
| Parallel units | Separate ParallelPlan; no graph fan-out | Native fork/join requires correct state reducers | Branch isolation, reducer and join tests; no claim of current portable graph parity |
| Bounded cycles | Portable safety limit | Native recursion/configuration semantics | Map declared bounds without silently using incompatible defaults |
| Agent internal flow | pipeline wraps Agent into CompiledSystem | Agent framework adapter is one node | Implement owned-flow execution and test nested Agent/System identity |
| Native-only lifecycle | Not provided | SDK-specific access | Advanced and explicitly unsupported in portable mode |

New flow definitions choose/resolve a backend explicitly and record it in
inspection. Missing required capabilities fail before action execution. Preserve
legacy graph engine="auto", including its dependency-based selection; the new
preferred path must not inherit that ambiguity silently. Native graph fan-out
is planned work, not something achieved by renaming ParallelPlan.

## Compatibility and migration mapping

| Existing 2.1.2 behavior | Compatibility requirement | Future preferred direction |
|---|---|---|
| toolkit.agent / system.agent and classes | Preserve signatures, ownership, registration, defaults and bind return semantics | One semantic Agent definition; separate internal execution services without another mandatory public context |
| agent.pipeline returns CompiledSystem with Agent first | Keep type/order and do not mutate original Agent | Separately specified opt-in owned flow; never silently reinterpret pipeline |
| system.run / compile with execution and entrypoint | Keep selection and plan semantics | Shared lifecycle behind adapters where equivalent |
| SequentialPlan / ParallelPlan | Keep forwarding, joins, ordering and result shapes | Common internal flow representation without changing old outputs |
| GraphApp.run / invoke returns state | Preserve state return and lifecycle | New facade projects state into RunResult; legacy calls still return state |
| system.graph().compile() returns native SDK object | Preserve type and invoke access | Explicit native escape hatch; common run boundary on the new facade |
| graph auto and framework routing | Preserve resolution and existing adapters | Explicit capability-aware backend on the future flow path |
| CLI, extras and serialized contracts | Preserve commands, requirements and schema meanings | Additions need API/schema/version review |

Offline characterization permits internal refactoring; compatibility does not
require preserving current coupling. This update introduces no rename, removal,
changed default, new required argument or deprecation warning. Schedule runtime
implementation in a separate release decision; breaking changes require a major
migration. Do not assign this architecture automatically to the already scoped
2.1.3/2.1.4 workstreams.

## User path

| User need | Teach first | Explain later |
|---|---|---|
| Implement an exact operation | `toolkit.tool` | `Tool`, schemas and advanced registration |
| Package reusable capabilities | `toolkit.skill`, `skills=[...]` | `load_skill`, `toolset`, `Skill`, `LoadedSkill` |
| Run one independent unit | `toolkit.agent` | Direct `Agent` construction and ownership |
| Coordinate units | System with its declared flow; run as the usual execution entry | Current registration/factory options and optional explicit compilation |
| Select provider and model | `toolkit.runtime` | Explicit precedence and per-agent overrides |
| Choose the execution loop | `framework="native"` initially | Optional framework adapters and their SDK features |
| Order, parallelize or branch work | The same flow vocabulary inside Agent or System | Current graph builders/adapters and backend-specific limits |
| Run episodes and steps | `toolkit.environment` | Environment types and graph adapters |
| Measure behavior | `toolkit.eval().evaluate(...)` | Rubrics, judges and report types |
| Read and retain a result | `result.text`, `result.normalized()`, `result.lineage()`, `toolkit.show` | Specialized views and summaries |

This is the target learning order after implementing the shared facade. Until
then, runnable examples use only existing 2.1.2 methods. Graph is introduced as
a flow representation within either owner; Environment and Eval are optional
dimensions. An independent Agent does not require a user-declared System.
Python Runtime executes deterministic operations; it does not provide language
reasoning or substitute for a semantic judge.

## Construction and ownership decisions

Keep `toolkit.agent(...)` for an independent Agent. It creates its supporting
System internally. Keep `system.agent(...)` for shared ownership: it registers
the Agent and its concrete Tools/Skills in that System. Preserve those existing
contexts. The target is one semantic Agent definition whose execution does not
require beginners to understand hidden registries. Prototype the separation of
ownership and execution services before choosing final syntax.

Keep `Agent`, `AgenticSystem` and the other public classes for annotations,
extension and advanced lifecycle control. Move their direct construction out of
the first learning path; do not remove them. Document that `Agent.bind(system)`
returns the bound Agent. Passing `system=` to a class constructor must not be
taught as equivalent to registration through `system.agent(...)`.

`system.compile(...)` currently creates an executable boundary. SequentialPlan
and ParallelPlan share an interface; Graph follows a separate path. Contrary to
the earlier plan wording, `Agent.pipeline(...)` does not install an owned flow:
it returns a CompiledSystem wrapping the Agent and extra steps. Preserve that
behavior while designing internal Agent flow and external System composition
with a shared lifecycle.

## Decisions for the complete API

[grammar-api-decisions.csv](grammar-api-decisions.csv) contains one decision for
each of the 89 stable top-level names. It classifies placement and teaching
priority, not removal. The existing API contract remains authoritative for all
468 IDs; data fields and protocol methods are not 468 separate user decisions.

| Family | Compatible cleanup |
|---|---|
| Grammar and reusable capabilities | Use the factories above consistently; retain all classes and loaders. |
| Runtime, provider, framework and scheduler | Explain responsibilities and current override precedence with examples; retain all configuration forms. |
| Contracts and policy | Separate acceptance requirements from execution limits; document which scope owns each limit. |
| Results and lineage | Teach a small set of views while preserving every error, event, child result and schema version. |
| Structured output | Distinguish schema validation, normalization and final-answer construction; never repair evidence silently. |
| Composition and Graph | Unify owner/flow/lifecycle first; teach run before optional compile; retain existing plans, compiled objects and adapters. |
| Environment and Eval | Separate episodic state from process/AWS configuration; separate execution success from semantic acceptance. |
| Serving | Explain ModelArtifact/ModelServer/vLLM lifecycle in an optional infrastructure guide. |
| Diagnostics | Group compatibility, credential-chain and provider snapshots in the documentation; do not invent a new namespace in this change. |
| Rendering and maintenance | Move specialized helpers and API inventory tools to the advanced reference. |

## Work packages and exit criteria

| Phase | Deliverable | Exit criterion | Status in this change |
|---|---|---|---|
| 0. Characterize compatibility | Exact artifact identity, public inventory and legacy behavior tests | Cover Agent.pipeline, System run/compile, both graph entry paths and legacy output types | Artifact/inventory recorded; runtime untouched |
| 1. Agree shared semantics | Owner/flow/backend model, input/state/joins, run/compile and native access contract | Every target is distinguished from current behavior; no unimplemented syntax taught as available | Specified in this plan |
| 2. Prototype offline | One shared internal execution/compiler core and thin Agent/System adapters | Complete the owner × flow × backend matrix below, including nesting and no side effects during compile | Isolated prototype executed; measured scope and remaining limits below |
| 3. Review Python API and migration | Minimum opt-in surface, compatibility adapters and configuration precedence | Existing 89 exports/calls keep behavior; new methods/parameters reviewed and versioned separately | Planned after prototype; names not selected |
| 4. Implement and verify | Shared facade, explicit graph-state projection and LangGraph lowering | No doubled stages, stale compilation, evidence loss or implicit backend substitution; old paths stay compatible | Planned for a separately scoped release |
| 5. Redesign learning/examples | Three runnable progressive references, then refund application; historical catalog remains secondary | New reader runs Agent, composes System and changes flow without switching execution verbs | Catalog prepared; runnable extraction pending |
| 6. Release gates | API/CLI/serialization regressions, notebooks, packaging and later authorized live acceptance | No artifact inherits certification; offline success alone never certifies model routes | Planned; no publication or inference here |
| 7. Consider deprecation | Measured redundancy, replacement and migration guide | Separate release decision; no removals or warnings in this change | Deferred |

## Offline acceptance matrix for implementation

Use deterministic Tools, controlled executable actions and local SDK graphs.
Block application network access and provider inference at the test boundary.
The prototype below measures a subset of this contract; production acceptance
still requires the full implementation and compatibility gates.

| Axis | Required cases |
|---|---|
| Owner × flow × backend | Agent and System × sequential, parallel and graph × native and LangGraph: 12 capability cells, each with direct run and explicit compile/run. Unsupported cells fail explicitly and remain incomplete, never counted as passing execution parity. |
| Nested ownership | System invokes Agent with its own different flow/backend; System invokes nested System. Inner framework/provider and boundary identity remain unchanged. |
| Lifecycle | Compile executes zero Tools, routers or models; direct run and compiled run select identical steps; repeated compilation causes no action; structural/configuration changes invalidate preparation. |
| Data and state | Sequential bindings; parallel isolation and reducer conflict; conditional branches, bounded loops and fork/join; independent state across runs and episodes. |
| Failure and limits | Tool/node failure, partial branch failure, invalid output, timeout, retry/effect policy, cancelled worker finishing late, parent/child limit accounting and unsupported capabilities. |
| Evidence | Owner/node/branch IDs, parent relationships, all attempts/events, aggregation without duplication, retained graph state and serializable results. |
| Native integration | LangGraph prepare/compile/invoke hidden behind the shared run facade; advanced native access retains SDK behavior. Test Agent framework selection independently of outer flow backend. |
| Legacy compatibility | Original Agent remains unchanged by pipeline construction; CompiledSystem types and unit order, System entrypoints, graph state returns, native invoke access and auto resolution stay unchanged. |

Do not label a rejected unsupported topology as an implemented feature. Publish
separate supported/executed/passed/failed/not-run states for this matrix. Use
fresh test inputs for direct and compiled paths so comparing them does not
duplicate real side effects. Native-only SDK features are outside parity unless
explicitly added to the portable contract.

Usability acceptance requires a fresh reader to run an Agent, add a Tool,
compose two Agents and change between sequence/parallel/conditional flow without
learning registry/bind internals or switching between run and invoke. Record
time, questions, changed lines and unexpected concepts; API inventory equality
alone is not evidence that the library is easier to learn.

The implementation owner must review the current code before writing precedence
tables. In particular, factory and direct-class defaults, `skill`/`skills`,
`engine`/runtime provider, model selection and `input`/`input_contract` mappings
must not be described as interchangeable without checking their behavior.

Documentation may prefer `skills=[...]` and explicit runtime routing immediately.
Existing singular aliases, direct classes, bind, manual registration and helper
functions continue to work. Behavioral changes, changed defaults, stricter
rejection of formerly accepted inputs and removals require a separate migration
and release decision. Breaking changes belong to a major version.

## Executed prototype and remaining scope

The runnable [offline prototype](../examples/unified_grammar/README.md) lives in
its own `unified_grammar` namespace. It imports the unchanged public 2.1.2 API;
it does not add Agent.compile to the released toolkit or patch any exports.

The [measured report](../examples/unified_grammar/evidence/REPORT.md) records
12/12 Agent/System × sequential/parallel/graph × native/LangGraph cells, direct
and compiled runs, 79 passing offline tests and a clean-kernel notebook with
six explicit examples and four alternate decision cases. The
non-editable published wheel was verified byte-for-byte; Python 3.14.2 and
LangGraph 1.2.16 were used. No inference was executed. The initial Windows
asyncio socketpair guard failure is retained separately from the passing suite.

Direct decision functions now occupy Graph edges without a Route wrapper or
duplicated target declarations. Returned destinations are checked against the
current graph's node names and END at runtime; compile never calls the router.
Legacy Route definitions retain their original declared-target restrictions.

The notebook also connects Skills to the same Agents and wraps all 12 units
in Environment and Eval: 24 passing episode steps, 24 passing evaluation
cases and two correctly detected wrong-expectation controls. Its 20 code
cells ran in a fresh offline kernel. No additional constructors were added.

The user assigned this API revision candidate the target version 2.1.3.
Its realistic order challenge covers seven Agents, seven Skills, eight
Tools and 14 contracts across native/LangGraph, including controlled
technical failure. A complete project scaffolder ran outside the repo
with 12 passing tests and a fresh-kernel notebook. SDK promotion is
pending; the verified published baseline remains 2.1.2.

The notebook also connects Skills to the same Agents and wraps all 12 units
in Environment and Eval: 24 passing episode steps, 24 passing evaluation
cases and two correctly detected wrong-expectation controls. Its 17 code
cells ran in a fresh offline kernel. No additional constructors were added.

The prototype reuses real Tools, Skills, RunResult, Environment episodes and
Eval reports. Exact expected-data checks are supplied through a deterministic
Eval assertion, rather than assuming an unsupported expectation key is checked.
Nested identities, Skill resolution, negative controls, shared limits, parallel
isolation, error retention, bounded cycles and async Agent/System calls are tested.

This is not production acceptance of every gate above: fork/join is represented
by an explicit Parallel node within a graph, not arbitrary multi-edge DAGs.
Deadlines are cooperative and wait for started workers; stuck Python callbacks
cannot be killed. There is no compilation cache or deep freeze of external
Tools/callbacks, persistent SDK lifecycle, LLM judge or provider inference.
Environment/Eval wrappers are synchronous. Internal execution services and
final Python surface still require review before migrating production code.

## Examples and scaffolder

Keep [the experiment catalog](../examples/README.md) as an evidence/recovery
index. Historical reference cards are not ready-to-run teaching applications.
They link existing implementations instead of copying certification scripts.
The planned beginner entry point should feature three extracted, runnable
references rather than the whole research history:

1. One Agent and one Tool, then reuse those capabilities through a Skill.
2. A System coordinating two Agents, changing sequence to parallel through the
   same control-flow model and execution verb.
3. A conditional flow inside an Agent nested in a System flow; add Environment
   and Eval as optional observers/interaction dimensions.

Graph is introduced inside either owner, not as a layer after System. Provider
and framework guides, calibration failures and certification matrices remain
secondary paths. Keep historical failures discoverable without making them the
beginner's prerequisite reading.

When promoting a card, add a README with input/process/output, an explicit
dependency/environment contract, a single run command, synthetic fixtures,
focused offline tests and evidence identifying version, commit, wheel SHA-256,
provider, model, framework, cases, attempts and verdict. A notebook, if useful,
must call that same implementation. Large transcripts belong in release assets.

The existing Studio scaffolder remains unchanged in this phase. A later
compatible template change may add `examples/` with a sample input and a runner
for the generated application. Do not place the complete library catalog in
every generated project. Validate generated manifests, package names, notebook
imports and source identity before promotion. Historical generated `dist`
directories are not canonical templates or proof of current compatibility.

The refund challenge integrates both ownership levels: an outer System flow
coordinates Agents whose internal flows can use sequence, parallel or graph.
Teach one canonical construction and execution lifecycle. Current 2.1.2 examples
must use existing adapters until the new contract is implemented; they cannot
claim a missing Agent.compile method. Alternative constructors belong in
compatibility tests rather than duplicated applications.
The earlier eight-variant live proposal has not run; a revised frozen matrix and
explicit budget authorization are required before any inference.

## Validation and release boundaries

The 2.1.2 published acceptance is OpenAI, Bedrock API key and Ollama across four
frameworks, two passes, plus deterministic Python controls. Historical Studio,
MCP/A2A, judge calibration and long-case results have narrower or different
artifact scopes. Never aggregate them into a new certification claim.

Keep external validation of vLLM/Colab, AWS IAM and ADA IAM in the agreed 2.1.3
workstream. ADA is an enterprise environment, not another provider. The proposed
2.1.4 ADA extra/ADA Studio and future wallet design remain separate and deferred;
this cleanup adds no `[ada]` extra or enterprise capability.

No inference is executed in this work package. Do not reset request ledgers,
reuse a historical budget as fresh authorization or run live notebooks when
checking this catalog. Runtime validation and future live evidence must report
their own artifact identity and preserve every failed attempt.

## Offline review commands

From the repository root:

```text
python examples/catalog_tools.py --check
python -m pytest tests/release/test_api_documentation_contract.py -q
git diff --check
```

The catalog tool uses only Python's standard library, does not import the SDK,
and performs no network requests. The documentation test validates existing
names/signatures without invoking providers. These checks validate documentation
and inventory coherence; they do not implement the target, recertify inference
or publish a release.
