# Fixed judge pilot · Agentic Systems 2.1.5

Ensure an optimistic fixture judge cannot approve an incorrect exact result.

## Run

Follow the [shared execution guide](../../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/patterns/fixed_judge_pilot/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

## Expected behavior and changes

Ensure an optimistic fixture judge cannot approve an incorrect exact result. The command prints serialized evidence after the
entrypoint assertions pass. An assertion failure exits unsuccessfully; an
intentional business rejection or controlled Tool error can be a passing test
when the example explicitly expects it. Change the supplied input and update
its business assertions together; do not remove checks to obtain PASS.

## Recorded offline result

The following data was observed by the 2026-11-08 review against the pinned
2.1.5 wheel. See the source assertions for the complete checks.

```json
{
  "total": 1,
  "passed": 0,
  "failed": 1,
  "cases": [
    {
      "name": "0",
      "ok": false,
      "input": {
        "answer": "WRONG"
      },
      "execution_id": "run-60958df837274aca8c9c5cae55907371",
      "checks": [
        {
          "ok": false,
          "path": "data"
        }
      ],
      "judge": {
        "ok": true,
        "criteria": {
          "correctness": 1.0
        },
        "score": 1.0,
        "raw": {
          "criteria": {
            "correctness": 1.0
          },
          "findings": [],
          "rationale": "Intentionally optimistic fixture"
        },
        "findings": [],
        "consistent": true,
        "certification_recorded": true,
        "threshold": 0.9,
        "usage": {}
      }
    }
  ]
}
```

## Validation scope

This is a deterministic or configuration-only lesson unless its source explicitly
requires the separate local-service profile. It does not demonstrate a model
reasoning about arbitrary inputs. Current offline review and historical artifact
identities are distinguished in [the review report](../../../docs/NARRATIVE_REVIEW_215.md).
