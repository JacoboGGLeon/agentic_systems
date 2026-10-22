# Validate the published wheel in additional environments

The 2.1.2 core release profile does not certify vLLM/Colab GPU, Bedrock IAM on
AWS, or Bedrock IAM in ADA. These are separate target-environment tests using
the same published wheel, not a new build under the same version.

1. Download the wheel and release manifest, verify its SHA-256, and create a
   fresh environment. Install the wheel non-editably with the optional SDKs
   needed for native, LangGraph, OpenAI Agents and Strands. In ADA resolve
   dependencies only through the approved Artifactory; record resolved versions,
   Python, OS and platform image. Do not modify a shared kernel.
2. Keep credentials outside bundles. For AWS and ADA IAM leave
   `AWS_BEARER_TOKEN_BEDROCK` empty and inherit the execution role. Confirm
   credential method, region and model without exporting credentials. For Colab
   use the existing vLLM GPU tutorial to start the model server explicitly;
   record GPU, server version, model revision and endpoint.
3. Download validation sources from the release commit. Set provider/model in
   a private `.env`. For vLLM run `scripts/run_semantic_matrix.py --providers
   vllm-runtime --wheel <published-wheel> --commit <release-commit> --env <env>
   --output <new-evidence.json> --review <new-review.md>`. For IAM use the
   equivalent `bedrock-runtime` command and the IAM attestation notebook under
   `release/notebooks/`. Run both passes to separate evidence files. The semantic
   runner defaults to all four frameworks; never silently substitute a route.
4. Agree live budget and transport guards before execution. Installation and
   preflight alone are not semantic acceptance. Retain failed attempts, outputs,
   Tool events, normalized results, usage and lineage. Include controlled Tool
   failure and serialization checks in the target acceptance.
5. Publish reviewed, redacted evidence naming the wheel hash and tested scope.
   A changed environment requires new evidence. Material or installer changes
   produce a new enterprise bundle revision; runtime fixes require a new library
   version and renewed affected-route testing.

There is no `[ada]` extra in 2.1.2. For Bedrock and four Frameworks use
`agentic-systems[bedrock,langgraph,openai-agents,strands]==2.1.2`. The core wheel,
Studio application and enterprise deployment bundle are separate deliveries.
