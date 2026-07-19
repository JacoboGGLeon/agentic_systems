# Static System Inspection

Status: normative through Checkpoint 1.1.8.

## Contract

`AgenticSystem.inspect()` analyzes a configured System without executing Tools,
Agents, models, Providers, Framework graphs, or Environment transitions.

It returns public `InspectReport`, a backward-compatible dictionary with:

- `to_dict()` for a detached JSON-compatible structure;
- `human_text()` for a stable human projection;
- `raise_if_errors()` for configuration gates.

The report schema is `agentic_systems.inspect.v1`.

## Static Boundary

Inspection MAY:

- read registries and immutable configuration;
- inspect Python signatures and Pydantic schemas;
- call local validation methods that do not execute user functions;
- read declared Provider and Framework profiles;
- derive relationships, limits, conflicts, and degradation risks.

Inspection MUST NOT:

- call a Tool function;
- call `Agent.run` or `Agent.arun`;
- hydrate Provider SDK clients;
- make network, model, filesystem-discovery, or Framework execution calls;
- compile or invoke Graphs;
- mutate System composition or execution state.

The `side_effects` block records zero model and Tool executions. It is a
contract declaration, not a runtime counter around arbitrary plugin code.

## Structured Sections

| Section | Meaning |
|---|---|
| `entities` | System, Tools, Skills, Agents, and Toolkits with stable identities |
| `relationships` | ownership, packaging, grouping, usage, and requested adapter edges |
| `contracts` | Tool schemas, Skill contracts/policies, and Agent contracts/policies |
| `providers` | every static Provider profile plus `selected_by` provenance |
| `frameworks` | every Framework profile plus `selected_by` provenance |
| `capabilities` | declared Provider capabilities and selection status |
| `conflicts` | explicit `keep`/`replace` decisions and unresolved conflicts |
| `limits` | System defaults, scheduler configuration, and Agent policies |
| `degradation_risks` | selected Provider/Framework limitations |
| `diagnostics` | actionable normalized errors and warnings |

Legacy summary fields such as `tools`, `agents`, `warnings`, and `errors` remain
for compatibility.

## Relationships

Every relationship has:

```json
{
  "source": "agent:worker",
  "relation": "uses",
  "target": "tool:lookup"
}
```

Edges are sorted by source, relation, and target. Inspection describes declared
configuration, not proof that an edge executed.

## Diagnostics

Every normalized diagnostic contains:

```text
code
severity
message
path
suggestion
source
```

`suggestion` MUST contain a concrete next action. Errors make `ok=false` and
cause `raise_if_errors()` to fail. Warnings and degradation risks remain
inspectable without claiming the System is invalid.

Examples:

- a strict Tool without a dictionary return annotation recommends adding the
  annotation or an output schema;
- a selected Framework without an adapter recommends using LangGraph or treating
  the value as metadata;
- an unsupported Provider capability recommends selecting another Provider or
  designing around the limitation.

## Human Output

`human_text()` uses fixed section order:

```text
Agentic Systems static inspection
Status
Entities
Relationships
Providers
Frameworks
Diagnostics
```

It is intentionally compact and deterministic. Detailed entities, schemas, and
profiles remain in `to_dict()`.

## Serialization

`to_dict()` must pass a JSON encode/decode round trip. Provider and Framework
profiles use their existing versioned declarations. Pydantic input/output
schemas are projected with `model_json_schema()` and no executable object is
serialized.
