# Judge calibration · Agentic Systems 2.1.7

Combine exact expectations with a deterministic fixture judge.

## Run

Follow the [shared execution guide](../../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/patterns/judge_calibration/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

## Expected behavior and changes

Combine exact expectations with a deterministic fixture judge. The command prints serialized evidence after the
entrypoint assertions pass. An assertion failure exits unsuccessfully; an
intentional business rejection or controlled Tool error can be a passing test
when the example explicitly expects it. Change the supplied input and update
its business assertions together; do not remove checks to obtain PASS.

## Recorded offline result

The following data was observed by the 2026-11-08 review against the pinned
2.1.5 wheel. See the source assertions for the complete checks.

```json
{
  "total": 2,
  "passed": 1,
  "failed": 1,
  "cases": [
    {
      "name": "0",
      "ok": true,
      "input": {
        "answer": "VALID"
      },
      "execution_id": "run-4a060d2c2f284bc183b6538e30e937db",
      "checks": [
        {
          "ok": true,
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
          "rationale": "Calibration fixture always approves"
        },
        "findings": [],
        "consistent": true,
        "certification_recorded": true,
        "threshold": 0.9,
        "usage": {}
      }
    },
    {
      "name": "1",
      "ok": false,
      "input": {
        "answer": "WRONG"
      },
      "execution_id": "run-f60012245a8c4313af3e5fe485a2ac8c",
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
          "rationale": "Calibration fixture always approves"
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
