"""Borrow an AWS session: configuration only, not IAM or ADA certification."""

import json

import boto3
import agentic_systems as toolkit
import agentic_systems_ada as ada


# This explicit offline fixture avoids looking up credentials or metadata.
# In ADA, use the session supplied by your platform instead of fixture keys.
session = boto3.Session(
    region_name="us-east-2",
    aws_access_key_id="offline-fixture",
    aws_secret_access_key="offline-fixture",
)
connection = toolkit.runtime(
    provider="bedrock-runtime", model="qwen-model-enabled-in-your-account",
    session=session,
)
agent = toolkit.Agent("aws_worker", runtime=connection)
program = agent.compile()


def run():
    # compile prepares; it does not create clients or invoke a model.
    assert connection.region == "us-east-2"
    assert "session" not in connection.model_dump()
    report = ada.diagnose(session=session)
    assert not report["services_checked"] and not report["credentials_resolved"]
    return {
        "input": "Borrowed boto3 Session, model and region",
        "process": "Validate connection -> compile Agent -> inspect configuration without services",
        "output": {"runtime": connection.inspect(), "diagnostic": report},
        "validation_scope": "configuration-offline-passed",
        "pending": ["real AWS IAM", "real ADA IAM", "model access and business acceptance"],
        "inference_requests": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
