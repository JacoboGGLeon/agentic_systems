# Episode memory · Agentic Systems 2.1.8

Observe, update and stop episodes while retaining execution identity.

## Run

Follow the [shared execution guide](../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/episode_memory/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

## Expected behavior and changes

Observe, update and stop episodes while retaining execution identity. The command prints serialized evidence after the
entrypoint assertions pass. An assertion failure exits unsuccessfully; an
intentional business rejection or controlled Tool error can be a passing test
when the example explicitly expects it. Change the supplied input and update
its business assertions together; do not remove checks to obtain PASS.

## Recorded offline result

The following data was observed by the 2026-11-08 review against the pinned
2.1.5 wheel. See the source assertions for the complete checks.

```json
{
  "outputs": [
    {
      "total": 2
    },
    {
      "total": 5
    }
  ],
  "history": [
    {
      "step": 0,
      "record": {
        "amount": 2
      },
      "state_before": {
        "total": 0
      },
      "state_after": {
        "total": 2
      },
      "execution_id": "run-820fcd3da3764c8faf6a9454568ff438"
    },
    {
      "step": 1,
      "record": {
        "amount": 3
      },
      "state_before": {
        "total": 2
      },
      "state_after": {
        "total": 5
      },
      "execution_id": "run-182ce835fc5846e1ae3a5430ac4018e1"
    }
  ],
  "summary": {
    "state": {
      "total": 5
    },
    "processed": 2,
    "terminated": true,
    "truncated": false,
    "reason": "stop"
  }
}
```

## Validation scope

This is a deterministic or configuration-only lesson unless its source explicitly
requires the separate local-service profile. It does not demonstrate a model
reasoning about arbitrary inputs. Current offline review and historical artifact
identities are distinguished in [the review report](../../docs/NARRATIVE_REVIEW_215.md).
