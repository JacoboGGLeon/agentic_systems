# Evaluation checks · Agentic Systems 2.1.5

Combine exact expectations, checks and a business metric with a negative control.

## Run

Follow the [shared execution guide](../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/evaluation_checks/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

## Expected behavior and changes

Combine exact expectations, checks and a business metric with a negative control. The command prints serialized evidence after the
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
  "passed": 1,
  "failed": 0,
  "cases": [
    {
      "name": "0",
      "ok": true,
      "input": {
        "value": 3
      },
      "execution_id": "run-6722b230ba19434a9744cbdb53553e7b",
      "checks": [
        {
          "ok": true,
          "path": "data"
        },
        {
          "ok": true,
          "issues": []
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
          "rationale": "Fixture: deterministic oracle confirmed the supplied case."
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
identities are distinguished in [the review report](../../docs/NARRATIVE_REVIEW_215.md).
