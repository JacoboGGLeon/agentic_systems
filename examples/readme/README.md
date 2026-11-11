# README execution examples

The repository README is the short learning path. Its eight Python blocks are exercised directly by:

```bash
python scripts/check_readme_examples.py
```

Run from the repository root with Agentic Systems 2.1.8 and the Bedrock/OpenAI Agents extras installed. The check uses local Tools, simulated Bedrock transport, and the repository's process-local offline guard. Outputs are written to `.tmp/readme-validation/`: `validation.json`, `evidence.json`, `execution.log`, and extracted `readme_local.py`.

The extended nested-actor tutorial is:

```bash
python examples/readme/incident_response.py
```

By default it uses a local deterministic Python actor. It demonstrates explicit Agent graphs, a conditional System, three acceptance cases including an expected failed lookup, a rejecting negative control, Environment episodes and stopping, independent Environment evaluation, and bounded Memory.

For a separately budgeted live campaign, the tutorial accepts `AS_PROVIDER=bedrock-runtime` and `AS_FRAMEWORK=native` or `openai-agents`, plus `AWS_REGION` and `BEDROCK_MODEL_ID`. This opt-in profile makes multiple real model requests, including evaluations and episodes. The default Python profile does not validate live model behavior or AWS permissions.

The extended tutorial's fixed-tool inspection actor and the README's two-tool support actor serve different teaching goals. Neither is a production monitoring integration; the tools use a small service snapshot and record escalation decisions without changing infrastructure.

These GitHub documentation changes do not modify the published PyPI 2.1.8 distribution.
