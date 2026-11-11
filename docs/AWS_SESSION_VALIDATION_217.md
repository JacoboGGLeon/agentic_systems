# AWS session acceptance · frozen 2.1.7 candidate

Targeted Bedrock checks passed in SageMaker Studio, one standalone Processing job and two two-step SageMaker Pipelines. The evidence was supplied by the operator; it is not an independently fetched AWS attestation. This document records that limited acceptance, not a claim that every provider, framework or AWS execution environment is certified.

## Tested artifact

| Identity | Value |
|---|---|
| SDK | 2.1.7 frozen candidate, tested before publication |
| Wheel SHA-256 | `b3de241cad7bd6a9639a1c57417234c597bf97756f92bebaa98330d0912588fd` |
| Reviewed PR head | `5357691f4337a3321eed23f30085f4de5f8a4a43` |
| CI synthetic merge checkout | `e83a1269a691ae757d1837afc559abe4f6b9de85` |
| Installed package files compared against wheel | 115 |
| Provider / model | Bedrock / `us.amazon.nova-pro-v1:0` |
| Region | `us-east-1` |
| Boto3 in both supplied reports | 1.44.0 |

The reviewed head and CI checkout are different commits. The wheel hash binds the actual bytes tested. Later documentation commits and future release artifacts do not inherit that exact-wheel identity automatically.

## Observed results

| Check | Studio | Processing job |
|---|---|---|
| Borrowed-session reference retained; session excluded from configuration | PASS | PASS |
| Boto3 direct Converse | PASS, HTTP 200 | PASS, HTTP 200 |
| Agent with supplied session | PASS | PASS, reconstructed runtime |
| Agent without explicit session | PASS | NOT RUN in this job |
| JSON transferred from notebook; identical configuration reconstructed | Not this campaign's purpose | PASS |
| Agent RunResult invariants and reported lineage | PASS | PASS |
| Watched AWS environment unchanged | PASS | PASS |
| Recorded Bedrock HTTP attempt reservations | 3 | 2 |

Studio campaign: `20261111T050225_3988e763`, Python 3.12.9. Processing campaign: `20261111T052200Z-0cc57a3e`; job Completed and both worker/controller acceptance PASS. Its runtime JSON SHA-256 was `cd769c9575fb337d2e0f68bdf068d28be877a96224dec7531ece0e287f10d8af`.

The [machine-readable summary](evidence/217/aws-session-operator-summary.json) preserves the supplied execution IDs and outcomes without AWS account, role ARN, network IDs or private S3 locations. It is a summary, not the original report or a cryptographic verification of the original report. The operator retains the complete reports and persistent ledgers.

The initial campaign's direct Boto3 assertion failure remains unresolved at assertion level because its report did not preserve that detail. Its two agents passed. A subsequent attempt reused the spent ledger and was blocked by the request budget. Those outcomes are retained; neither is silently relabeled as a successful campaign or definitive credential failure. The later clean diagnostic campaign passed all three routes.

## Configuration travels; Session objects do not

```python
import json
import boto3
import agentic_systems as toolkit

# Source process: prepare a session, or reuse the application's existing one.
source_session = boto3.Session(region_name="us-east-1")
source_runtime = toolkit.runtime(
    provider="bedrock-runtime",
    model="us.amazon.nova-pro-v1:0",
    session=source_session,
)
config_json = source_runtime.model_dump_json()
assert "session" not in json.loads(config_json)

# Destination process: load only the JSON and create a local session.
config = json.loads(config_json)
local_session = boto3.Session(region_name=config["region"])
restored_runtime = toolkit.runtime(**config, session=local_session)
assert restored_runtime.session is local_session
assert restored_runtime.model_dump() == config
```

These declarations do not invoke a model. The operator's Processing report separately demonstrates the real cross-job reconstruction and live invocation. Neither exporting JSON nor constructing Session assigns an EMR runtime role. A common role does not imply shared object identity across jobs.

No credential values are extracted for the diagnostic. Boto3 resolves and signs requests during normal invocation. Excluding a session from this runtime's JSON does not mean arbitrary user state, logs or third-party configuration cannot contain secrets.

## Two-pipeline comparison: operator-reported PASS

| Variant | Campaign | Result | Jobs / agent executions |
|---|---|---|---|
| Automatic session resolution | `20261111T055851Z-e0a39fd5` | PASS; pipeline Succeeded | 2 / 4 |
| Supplied session shared inside each job | `20261111T060123Z-33897585` | PASS; pipeline Succeeded | 2 / 4 |

Both controller reports passed all 16 checks. They record two completed jobs per
variant, two HTTP attempt reservations per job (eight total), unchanged watched
environment, session exclusion from JSON, valid worker checks, artifact hash
continuity, application lineage, configured role agreement and dependency order.
The comparison reports the same runtime JSON SHA in both variants. Their worker,
bootstrap and support source hashes match the delivered bundle's local files.

The delivered worker requires two distinct session objects in automatic mode and
one session shared by its two actors in injected mode. A passing controller's
worker-policy checks therefore report these expectations as met. These are
operator-supplied controller results; the individual worker reports were not
independently fetched here. SDK invariants/lineage remain per actor; application
lineage links jobs through the received artifact without rewriting SDK parent IDs.

Sessions stayed process-local in both variants. This demonstrates configuration
and artifact transfer between jobs, not transfer of a Session object. No additional
model calls are needed to read these reports. Earlier simulated-HTTP tests remain
local evidence rather than being relabeled as these live executions.

## Pending and excluded scope
- EMR driver with the original runtime-role context: no live acceptance. The prepared EMR probe returned BLOCKED because the target context was unconfirmed.
- Spark executor/Python-worker execution and long-running credential refresh: NOT RUN.
- Effective-role attestation through STS: NOT RUN. The Processing controller checked the configured job role, not an STS identity response.
- Other models/providers/framework combinations: not certified by these small campaigns.

Do not turn a Studio-local Python result into EMR evidence by changing a confirmation flag. The EMR driver must actually execute inside the intended application/role context. A cluster with Spark and runtime-role support is a prerequisite, not proof of SDK acceptance.

## Release boundary

The runtime implementation is unchanged by 2.1.7. This release adds bundled authoring-skill distribution and simplifies the CLI. The targeted AWS reports supplement the existing reviewed release policy; they do not weaken its executable-payload, quality, mutation, sealing or publication gates. Final artifacts still require checks on the final main commit, TestPyPI verification and hash-consistent promotion. EMR/distributed Spark remain outside the closed acceptance scope.
