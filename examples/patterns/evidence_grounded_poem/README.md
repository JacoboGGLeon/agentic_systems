# Evidence grounded poem · Agentic Systems 2.1.9

Check supplied candidate poems for format and a verified number.

## Run

Follow the [shared execution guide](../../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/patterns/evidence_grounded_poem/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

The supplied input is:

```json
"Three items cost 300\nTax adds 48\nVerified total 348"
```

## Expected behavior and changes

Check supplied candidate poems for format and a verified number. The command prints serialized evidence after the
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
        "poem": "Three items cost 300\nTax adds 48\nVerified total 348"
      },
      "execution_id": "run-b9dc413fd59c48b4910601a011fa1297",
      "checks": [
        {
          "ok": true,
          "path": "ok"
        },
        {
          "ok": true,
          "issues": []
        }
      ],
      "judge": null
    },
    {
      "name": "1",
      "ok": false,
      "input": {
        "poem": "The moon computes forever"
      },
      "execution_id": "run-85a7b999d44f4ff4a8bb2afe96ec622d",
      "checks": [
        {
          "ok": true,
          "path": "ok"
        },
        {
          "ok": false,
          "issues": []
        }
      ],
      "judge": null
    }
  ]
}
```

## Validation scope

This is a deterministic or configuration-only lesson unless its source explicitly
requires the separate local-service profile. It does not demonstrate a model
reasoning about arbitrary inputs. Current offline review and historical artifact
identities are distinguished in [the review report](../../../docs/NARRATIVE_REVIEW_215.md).
