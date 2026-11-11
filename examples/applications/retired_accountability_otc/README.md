# Retired accountability otc · Agentic Systems 2.1.7

Run a public synthetic replacement for a retired experiment.

## Run

Follow the [shared execution guide](../../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/applications/retired_accountability_otc/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

The supplied input is:

```json
{
  "claims": [
    {
      "id": "C1",
      "owner": "team-A",
      "evidence": [
        "E1"
      ]
    },
    {
      "id": "C2",
      "owner": "",
      "evidence": []
    }
  ]
}
```

## Expected behavior and changes

Run a public synthetic replacement for a retired experiment. The command prints serialized evidence after the
entrypoint assertions pass. An assertion failure exits unsuccessfully; an
intentional business rejection or controlled Tool error can be a passing test
when the example explicitly expects it. Change the supplied input and update
its business assertions together; do not remove checks to obtain PASS.

## Recorded offline result

The following data was observed by the 2026-11-08 review against the pinned
2.1.5 wheel. See the source assertions for the complete checks.

```json
{
  "unowned": [
    "C2"
  ],
  "unsupported": [
    "C2"
  ],
  "data": "public synthetic fixture"
}
```

## Validation scope

This is a deterministic or configuration-only lesson unless its source explicitly
requires the separate local-service profile. It does not demonstrate a model
reasoning about arbitrary inputs. Current offline review and historical artifact
identities are distinguished in [the review report](../../../docs/NARRATIVE_REVIEW_215.md).
