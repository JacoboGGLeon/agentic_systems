# Strands protocol graph challenge

This challenge proves one complete route:

```text
Evaluator / AgenticEnvironment
└── System
    └── real LangGraph (CompiledStateGraph)
        └── Strands Agent using the selected Provider
            ├── real MCP Tool over stdio
            └── real remote A2A Agent over HTTP
└── python-runtime × native deterministic judge
    └── certify_protocol_episode Tool
```

The candidate must call both protocol boundaries exactly once and then produce a
natural public answer containing the exact verified tokens. The independent
judge checks answer, Tool outputs, provider/framework identity, and hierarchical
lineage. The runner then performs a second manual-style deterministic review of
`human_result`; `ok=true` alone cannot pass.

The evidence identifiers are capability-bound when the isolated MCP and A2A
resources are created. The language model chooses the Tools, but cannot rewrite
the authoritative identifiers as Tool arguments. This applies uniformly to
every provider and prevents a mutated argument from being certified as valid.

## Installation

Install the exact candidate wheel, followed by the challenge dependencies:

```bash
python -m pip install --force-reinstall --no-deps ./agentic_systems-2.1.2-py3-none-any.whl
python -m pip install -r semantic_challenges/strands_protocol_graph/requirements.txt
```

Copy `.env.example` to the repository/bundle root as `.env` and fill only the
credentials and models for the providers being tested. `.env` overrides process
environment; process environment is fallback.

## Local live matrix

With OpenAI, Bedrock API key, and Ollama configured:

```bash
python -m semantic_challenges.strands_protocol_graph.run_matrix \
  --providers openai-runtime bedrock-runtime ollama-runtime \
  --wheel ./agentic_systems-2.1.2-py3-none-any.whl \
  --output-dir ./outputs

python -m semantic_challenges.strands_protocol_graph.validate_attestation \
  ./outputs/strands-protocol-graph-attestation.json \
  --providers openai-runtime bedrock-runtime ollama-runtime \
  --require-bedrock-auth bedrock-api-key
```

## Colab vLLM

Use the same code and manifest. Set `AGENTIC_SYSTEMS_PROVIDER=vllm-runtime`,
configure the `VLLM_*` values in `.env`, start the tested vLLM server, then run:

```bash
python -m semantic_challenges.strands_protocol_graph.run_matrix \
  --providers vllm-runtime --wheel ./agentic_systems-2.1.2-py3-none-any.whl
```

## SageMaker / ADA Bedrock IAM

Leave `AWS_BEARER_TOKEN_BEDROCK=` empty. Boto3 inherits the execution role from
the normal AWS credential chain; do not copy local keys into ADA.

```bash
python -m semantic_challenges.strands_protocol_graph.run_matrix \
  --providers bedrock-runtime --wheel ./agentic_systems-2.1.2-py3-none-any.whl

python -m semantic_challenges.strands_protocol_graph.validate_attestation \
  ./outputs/strands-protocol-graph-attestation.json \
  --providers bedrock-runtime --require-bedrock-auth aws-credential-chain
```

## Passing evidence

The generated JSON and Markdown must agree on:

- root: declared Provider × LangGraph;
- only child: same Provider × Strands;
- Tool path: `fetch_mcp_evidence`, then `fetch_a2a_evidence`;
- exact MCP and A2A tokens in Tool evidence and public answer;
- judge: `python-runtime × native`, with one certification Tool;
- no fallback, retries, raw envelopes, reasoning blocks, or invariant failures.
