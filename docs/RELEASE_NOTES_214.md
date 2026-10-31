# Agentic Systems 2.1.4

One public grammar built on Pydantic contracts and LangGraph orchestration.
Agents organize capabilities; Systems coordinate applications; Environments
process episodes. Context, bounded Memory, explanatory lineage, RunResult,
human_results and isolated Eval cases make execution inspectable.

This release fixes Tool selection across Bedrock adapters, empty-answer handling,
failed synthesis evidence, Studio numeric grounding and per-actor native Ollama
connections. Local/cloud native coexistence passed sync/arun tests and the
financial notebook with OpenAI, Bedrock and Ollama in one System.

## Installation

`pip install agentic-systems==2.1.4`

Optional provider/framework extras remain separate. Studio, the Codex/ChatGPT
skill, learning material and optional ADA diagnostics are GitHub release assets.
The ADA package does not certify real enterprise access and is not part of all.
The validation-evidence ZIP retains detailed historical attempts at their original
repository-relative paths; compact reports and summaries remain in the repository.

## Acceptance and limitations

Stable wheel/sdist come from one successful quality run across Python 3.10–3.14.
The user explicitly approved executable-payload equivalence to the development
wheel tested online, with only version/documentation changes and no new inference.
The candidate compares every Python payload file; only the initializer's version
literal and newline normalization are permitted. It records that no live calls
were executed against the stable artifact. TestPyPI, PyPI and GitHub promote the
same reviewed bytes and verify distribution hashes.

Bedrock/Qwen can omit a required nullable Tool argument despite strict schema.
Local validation rejects the malformed arguments without inventing defaults.
This is a known integration limitation excluded from passing acceptance, not a
successful compatibility case. Evidence remains available in the repository.
vLLM GPU, AWS IAM and ADA IAM await their environments. This release does not
claim universal SDK feature parity, durable Memory or cross-process resume.
