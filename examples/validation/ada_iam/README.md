# Ada iam · Agentic Systems 2.1.7

Inspect a Bedrock configuration for an enterprise workload.

## Run

Follow the [shared execution guide](../../../docs/EXAMPLES_GUIDE.md). From the repository root:

```bash
python scripts/run_example.py examples/validation/ada_iam/example.py
```

## Read the implementation

[Open the source](example.py). Start with the Tool body, then its Skill,
state model and Graph. Follow START, node names, conditional routes and END.
The entrypoint runs supplied cases and asserts their outcomes. The assertions
are executable expectations; inspect them before changing the scenario.

## Expected behavior and changes

Inspect a Bedrock configuration for an enterprise workload. The command prints serialized evidence after the
entrypoint assertions pass. An assertion failure exits unsuccessfully; an
intentional business rejection or controlled Tool error can be a passing test
when the example explicitly expects it. Change the supplied input and update
its business assertions together; do not remove checks to obtain PASS.

## Recorded offline result

The following data was observed by the 2026-11-08 review against the pinned
2.1.5 wheel. See the source assertions for the complete checks.

```json
{
  "mode": "ADA workload IAM",
  "runtime": {
    "provider": "bedrock-runtime",
    "model": "configure-in-target-environment",
    "region": "us-east-2",
    "endpoint": null,
    "api_key_configured": false,
    "session_configured": false,
    "authentication_mode": "provider-configuration",
    "timeout_s": 60.0,
    "max_retries": 0,
    "max_tool_calls": 5,
    "max_turns": 6,
    "max_tokens": null,
    "backoff_s": 0.0,
    "max_concurrency": 1
  },
  "application": {
    "name": "target",
    "kind": "agent",
    "graph": {
      "engine": "langgraph",
      "state": [
        "input",
        "output",
        "result_ref"
      ],
      "state_validation": "typed-dict",
      "nodes": [
        "actor"
      ],
      "edges": [
        {
          "source": "__start__",
          "target": "actor"
        },
        {
          "source": "actor",
          "target": "__end__"
        }
      ],
      "barriers": [],
      "decisions": {},
      "lineage": "bounded IDs in state; full records outside checkpoints"
    },
    "framework": "native",
    "continuations": "process-local",
    "checkpoint_state": "business data + bounded lineage references"
  },
  "status": "configuration-only; target environment not executed",
  "inference_requests": 0,
  "authentication": "Remove bearer token from the target IAM process; use its workload role. Never embed access keys."
}
```

## Validation scope

This is a deterministic or configuration-only lesson unless its source explicitly
requires the separate local-service profile. It does not demonstrate a model
reasoning about arbitrary inputs. Current offline review and historical artifact
identities are distinguished in [the review report](../../../docs/NARRATIVE_REVIEW_215.md).
