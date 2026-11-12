# Optional AWS/ADA diagnostics · 2.1.9

This independent optional package provides read-only configuration diagnostics.
It is not included in the SDK's `all` extra. It uses the existing Agent/System/Graph
and Bedrock runtime; it does not introduce another execution grammar or an `ada`
extra duplicating `bedrock`.

## Install and inspect

Install the matching SDK 2.1.9 first. For pre-publication acceptance, use the
supplied frozen SDK wheel and approved dependencies.
From the `ada` directory of the matching release asset:

```bash
python -m pip install "wheels/agentic_systems_ada-2.1.9-py3-none-any.whl"
agentic-systems-ada doctor
```

Alternatively, from the repository root after installing the matching SDK:

```bash
python -m pip install --no-deps --no-build-isolation ./integrations/ada
agentic-systems-ada doctor
```

The first install resolves the declared SDK/Bedrock dependencies through your
configured index or wheelhouse. The checkout command assumes they are already
installed. Installing in Studio does not install this package in a remote job.
The SDK session-injection feature itself does not require this add-on.

```python
import agentic_systems as toolkit
import agentic_systems_ada as ada

# supplied_session is the application's existing Boto3 Session in THIS process.
report = ada.diagnose(session=supplied_session)
connection = toolkit.runtime(
    provider="bedrock-runtime", model="enabled-model-in-your-account",
    session=supplied_session,
)
```

`diagnose` does not resolve credentials, query STS/metadata or change environment
variables. It does not certify identity, model access or ADA. It never silently
removes ambiguous credential settings; administering the credential chain remains
an explicit platform operation.

## Session ownership and evidence

A supplied session explicitly selects IAM. Conflicting API key, endpoint or region
settings are rejected. A global bearer does not override that supplied session.
Toolkit invocations sharing the session are serialized; its owner coordinates
external concurrent use and lifetime. The toolkit does not close the session or
serialize it into Context, state, Memory, results or runtime configuration.
The object cannot be moved across processes. Transfer JSON configuration instead,
then create and supply a session in the destination process.

Local adapter regressions use simulated transport. Separate operator-supplied
2.1.9 reports passed targeted Bedrock checks in Studio, Processing and two SageMaker
Pipelines. Those reports validate the SDK paths exercised, not live calls by this
diagnostic command. EMR, Spark executors and prolonged credential renewal remain
unverified. See [AWS acceptance and limits](../../docs/AWS_SESSION_VALIDATION_217.md)
in the repository or matching learning asset; the small ADA asset does not contain
the complete documentation tree.

This package does not configure Artifactory, proxies, CAs, IAM roles or credentials,
and does not include Studio or a wallet.
