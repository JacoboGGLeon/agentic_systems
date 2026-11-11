# Quantitative analysis · Agentic Systems 2.1.8

Sum decimal amounts without binary floating-point arithmetic.

## Run

Follow the [shared execution guide](../../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/applications/quantitative_analysis/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

The supplied input is:

```json
{
  "rows": [
    {
      "revenue": "100.10",
      "cost": "60.05"
    },
    {
      "revenue": "20.20",
      "cost": "10.00"
    }
  ]
}
```

## Expected behavior and changes

Sum decimal amounts without binary floating-point arithmetic. The command prints serialized evidence after the
entrypoint assertions pass. An assertion failure exits unsuccessfully; an
intentional business rejection or controlled Tool error can be a passing test
when the example explicitly expects it. Change the supplied input and update
its business assertions together; do not remove checks to obtain PASS.

## Recorded offline result

The following data was observed by the 2026-11-08 review against the pinned
2.1.5 wheel. See the source assertions for the complete checks.

```json
{
  "revenue": "120.30",
  "cost": "70.05",
  "profit": "50.25"
}
```

## Validation scope

This is a deterministic or configuration-only lesson unless its source explicitly
requires the separate local-service profile. It does not demonstrate a model
reasoning about arbitrary inputs. Current offline review and historical artifact
identities are distinguished in [the review report](../../../docs/NARRATIVE_REVIEW_215.md).
