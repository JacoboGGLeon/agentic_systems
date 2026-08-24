# ADA and Colab validation

This is the final external release gate. It executes the same ten catalog
systems through agentic-systems, langgraph, openai-agents and strands.
Every report is credential-free and records engine alignment, stage count,
token usage, errors and RunResult invariants.

## Install the bundle

    python -m pip install -e .[all]
    python -m pip install -e examples/agentic_systems_studio
    agentic-systems doctor --live

If you are using the standalone Studio bundle, run the second command from its
root and use python scripts/validate_sandbox.py below.

## ADA with IAM credentials

Use the local, Git-ignored `.env` as the canonical configuration source. Leave
the bearer value empty so boto3 inherits the sandbox/SageMaker execution role:

    AWS_BEARER_TOKEN_BEDROCK=
    AWS_REGION=us-east-2
    BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
    RUN_BEDROCK_LIVE=1

Then run without exporting, unsetting or rewriting credentials in the notebook:

    python scripts/validate_sandbox.py \
      --provider bedrock-runtime \
      --model "$BEDROCK_MODEL_ID" \
      --output evidence/bedrock-ada-iam

## Bedrock API key

For the API-key route, put the fresh key in the same local `.env`; the file is
ignored by Git and must never be copied into notebooks, evidence or bundles:

    AWS_BEARER_TOKEN_BEDROCK=<fresh-api-key>
    AWS_REGION=us-east-2
    BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
    RUN_BEDROCK_LIVE=1

Then execute the same validator:

    python scripts/validate_sandbox.py \
      --provider bedrock-runtime \
      --model "$BEDROCK_MODEL_ID" \
      --output evidence/bedrock-api-key

To return to IAM, make the bearer value empty in `.env`. Agentic Systems and
the notebooks never mutate that decision.

## Colab with vLLM

Start an OpenAI-compatible vLLM server, then configure its URL and model:

    export VLLM_BASE_URL=http://127.0.0.1:8000/v1
    export VLLM_API_KEY=token
    python scripts/validate_sandbox.py \
      --provider vllm-runtime \
      --model "$VLLM_MODEL" \
      --output evidence/vllm-colab

## Passing contract

The matrix exits with status 0 only when every requested framework passes all
ten systems. A passing matrix therefore represents 40 system executions and
136 stage executions. Each child engine must be python-runtime for operators
or the requested provider for reasoning/review stages, and every hierarchical
RunResult must pass its invariants.