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

Do not set AWS_BEARER_TOKEN_BEDROCK. Let boto3 use the sandbox role and set
the region/model selected for ADA:

    export AWS_REGION=us-east-2
    python scripts/validate_sandbox.py \
      --provider bedrock-runtime \
      --model "$BEDROCK_MODEL_ID" \
      --output evidence/bedrock-ada-iam

## Bedrock API key

Use a fresh Bedrock API key in the standard AWS environment variable. Do not
write it into .env, notebooks, evidence or manifests:

    export AWS_BEARER_TOKEN_BEDROCK='fresh-key'
    export AWS_REGION=us-east-2
    python scripts/validate_sandbox.py \
      --provider bedrock-runtime \
      --model "$BEDROCK_MODEL_ID" \
      --output evidence/bedrock-api-key

Unset the bearer token before repeating the IAM path.

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