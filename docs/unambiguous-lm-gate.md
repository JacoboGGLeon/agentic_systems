# Unambiguous LM conformance gate v1

## Scope

This gate certifies a deliberately narrow promise: given immutable JSON
observations and typed equality assertions, a configured provider/framework route
must return every exact `supported`, `contradicted`, or `unknown` decision through
the declared tool schema, and the library must preserve execution evidence and
lineage.

"Unambiguous" applies to the acceptance decision, not to arbitrary natural
language. Free prose, metaphors, implicit references, causal inference and
explanation quality belong to separate semantic experiments and cannot approve or
invalidate this gate.

## Agentic system

The public toolkit builds one sequential System:

```text
Python Agent: prepare_case
        |
        v
Configured LM Agent: model_decide
        |
        v
Python Agent: verify_decisions
```

1. `prepare_case` validates identities, JSON values, paths and assertion shape.
2. `model_decide` must call `record_assertion_decisions` exactly once.
3. `verify_decisions` independently resolves each path and compares canonical
   JSON values without coercion.

The LM never segments or copies prose, chooses evidence, invents a rubric,
explains a result, or determines the authoritative verdict. The final gate passes
only when execution integrity and the deterministic comparison both pass.

The returned `evaluation` does not inspect only the final answer. It evaluates
every agent boundary and every assertion. `evaluation_markdown` renders the same
facts as a didactic CI artifact.

## Input contract

Each assertion is atomic and complete:

```json
{
  "assertion_id": "a05-supported-number",
  "record_id": "lookup-a",
  "path": ["output", "value"],
  "operator": "eq",
  "expected": 47
}
```

The fixture is
`tests/fixtures/unambiguous_lm_gate_v1.json`. It covers booleans, a recorded
failure, nested values, strict number/string distinction, a missing path and a
missing record. No expected status is stored in the fixture; Python derives it
from the observations.

## Output contract

The LM returns only:

```json
{
  "decisions": [
    {
      "assertion_id": "a05-supported-number",
      "status": "supported",
      "evidence_ids": ["lookup-a"]
    }
  ]
}
```

Rules:

- preserve every assertion ID and its input order;
- `supported`: path exists and observed JSON value and type equal `expected`;
- `contradicted`: path exists and exact JSON equality fails;
- `unknown`: record or path is absent;
- cite exactly the record for `supported` or `contradicted`;
- cite nothing for `unknown`;
- never coerce `47`, `"47"`, `true` or `1`.

Missing, duplicate, reordered or invented decisions fail. A structurally valid but
incorrect model decision remains recorded and fails; there is no retry seeking a
favorable answer and no provider fallback.

## Reproduction

From the repository root, with the release source on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "src;."
python -m pytest tests/contracts/test_unambiguous_lm_gate.py -q
```

The offline run executes the same three-stage System through `native`,
`langgraph`, `openai-agents`, and `strands`, using Python only as an explicit
control. Those four controls prove topology, schema, deterministic comparison and
lineage; they are not LM semantic passes.

A live route must call `run_gate` with its exact provider, framework and model and
persist the returned normalized result and lineage. Example:

```python
import json
from pathlib import Path
from scripts.unambiguous_lm_gate import run_gate

case = json.loads(
    Path("tests/fixtures/unambiguous_lm_gate_v1.json").read_text(encoding="utf-8")
)
report = run_gate(case, "openai-runtime", "native", "gpt-4.1-mini")
assert report["passed"], report
```

The reproducible CLI persists immutable JSON evidence plus the didactic Markdown
report:

```powershell
python scripts/run_unambiguous_lm_gate.py `
  --provider openai-runtime `
  --framework native `
  --model gpt-4.1-mini `
  --commit <exact-commit> `
  --output <new-evidence-path>.json `
  --markdown <new-report-path>.md
```

Install the approved HTTP/Bedrock budget guard before invoking a paid route. The
CLI refuses to overwrite evidence and records UTC time and SHA-256 for its
application and fixture.

Live certification additionally records the source commit, source and fixture
SHA-256, provider, framework, model, request usage, normalized RunResult, lineage,
budget ledger and timestamp. A static compatibility declaration or Python control
cannot replace a successful live invocation.

## Acceptance matrix

For every declared live route:

| Boundary | Required result |
| --- | --- |
| Case validation | no duplicate/invalid identities or non-JSON values |
| Tool schema | one valid `DecisionBatch` |
| Coverage | every assertion exactly once and in order |
| Decision | exact match with deterministic Python oracle |
| Evidence | exact citation or empty for unknown |
| Execution | three expected actors and runtime engines |
| Lineage | retained normalized children and tool events |
| Fallback | none |
| Retry for favorable result | none |

One failure leaves that route uncertified. Results from language-rich exploratory
suites are reported separately because they test a different promise.

## Didactic report

The report contains two complementary levels:

1. **Agent and step evaluation** checks that each expected child ran, used the
   declared runtime/framework and Tool, retained the parent execution link and
   completed successfully. It also verifies the exact state transition: prepared
   packet into the model, recorded decisions into the verifier, and verifier
   output into the final report.
2. **Assertion evaluation** shows the record and JSON path, expected value,
   observed value when present, authoritative status, model status, evidence
   references, pass/fail and a deterministic explanation.

Consequently a correct final aggregate cannot hide an omitted assertion, an
incorrect intermediate inference, a failed Tool, a provider substitution or a
broken lineage edge.

## Preserved live pilot

The final v2 source was executed once on each selected route under its existing
independent USD 5 / 300-request allocation. Each execution used two provider
requests. Evidence is under `../unambiguous-lm-gate-v2/` relative to this
repository; earlier v1 evidence remains preserved because the transition checks
changed afterward.

| Provider / framework | Agent stages | Assertions | Gate |
| --- | ---: | ---: | --- |
| OpenAI / native (`gpt-4.1-mini`) | 3/3 | 10/10 | PASS |
| Ollama / native (`qwen3:4b-instruct-2507-q4_K_M`) | 3/3 | 10/10 | PASS |
| Bedrock API key / langgraph (`us.amazon.nova-pro-v1:0`) | 3/3 | 8/10 | FAIL |
| Bedrock API key / langgraph (`qwen.qwen3-32b-v1:0`) | 3/3 | 10/10 | PASS |

Bedrock completed the required Tool call and every execution-boundary check, but
omitted the two assertions whose correct status was `unknown`: one missing JSON
path and one missing record. The report therefore separates successful transport,
schema and lineage from an incomplete model decision. The failed route was not
repeated or promoted.

An isolated model A/B then ran the identical Bedrock/langgraph gate with Qwen3
32B. It passed all ten assertions, including both `unknown` cases, in two guarded
requests. Its evidence and independent USD 1 / four-request ledger are preserved
under `../unambiguous-lm-gate-qwen32/` and
`../qwen32-bedrock-langgraph-pilot/`. This proves the sampled Qwen route; it does
not erase the Nova result or establish universal reliability.

These three routes are a pilot, not the complete Provider x Framework matrix.
