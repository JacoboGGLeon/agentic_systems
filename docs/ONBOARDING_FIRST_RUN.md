# First Run Onboarding

This guide gets a new user from install to the first tutorial run.

## Install

```bash
python -m pip install -U pip
pip install -e .
```

Optional extras:

```bash
pip install -e ".[dev]"
pip install -e ".[tutorials]"
pip install -e ".[bedrock]"
pip install -e ".[langgraph]"
pip install -e ".[openai]"   # OpenAI client; also used by vllm-runtime
```

## Smoke Test

```bash
agentic-systems doctor
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
```

Python smoke:

```python
import agentic_systems as toolkit

assert callable(toolkit.tool)
assert callable(toolkit.agent)
assert callable(toolkit.runtime)
assert callable(toolkit.scheduler)
```

## Environment Variables

Configure provider credentials before opening notebooks so the Jupyter/VSCode
kernel inherits them.

Recommended local workflow:

```bash
cp .env.example .env
```

Then edit `.env` locally. The real `.env` file is ignored by git.

PowerShell example for OpenAI:

```powershell
$env:OPENAI_API_KEY="your_key_here"
```

Git Bash example for OpenAI:

```bash
export OPENAI_API_KEY="your_key_here"
```

PowerShell example for Bedrock:

```powershell
$env:AWS_REGION="us-east-1"
$env:AWS_PROFILE="your_profile"
```

Git Bash example for Bedrock:

```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="your_profile"
```

Git Bash example for vLLM/OpenAI-compatible Colab or local GPU server:

```bash
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_MODEL_ID="Qwen/Qwen3-0.6B"
export VLLM_API_KEY="EMPTY"
```

In Colab, install `agentic-systems[openai]` for the client and install/run
`vllm` separately for the GPU server.

Do not paste API keys into notebooks or repo files. `provider="auto"` reads
environment variables that already exist in the kernel process.

The CLI and `runtime.describe()` also load a local `.env` file when present,
without printing secret values.

For OpenAI runtime, install the SDK extra:

```bash
python -m pip install -e ".[openai]"
```

Verify selection from Python:

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="auto")
toolkit.show(runtime.describe(), title="Auto runtime - describe")
```

Expected `selected_provider` values:

```text
vllm-runtime     when VLLM_BASE_URL/vLLM config is available
openai-runtime   when OpenAI config is available
bedrock-runtime  when AWS config is available
auto             when no provider signal is available
```

Bedrock selection can use `AGENTIC_SYSTEMS_MODEL_ID`, `OTC_MODEL_ID`,
`BEDROCK_MODEL_ID`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_PROFILE`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN`. Runtime
and CLI diagnostics show safe flags only; actual execution uses the standard
boto3/AWS credential chain.

## First Tutorial Route

Open notebooks from the repo root:

```bash
jupyter lab tutorials
```

Run in order:

```text
00_runtime_api.ipynb
00_runtime_bedrock_provider_api.ipynb
00_runtime_openai_provider_api.ipynb
00_runtime_vllm_provider_api.ipynb
00_runtime_scheduler_api.ipynb
01_tool_api.ipynb
02_skill_api.ipynb
03_agent_api.ipynb
04_human_result_api.ipynb
05_lineage_memory_api.ipynb
06_integrations_strands_api.ipynb
07_integrations_openai_runtime_api.ipynb
08_system_api.ipynb
09_graph_api.ipynb
10_environment_eval_api.ipynb
```

## Runtime Selection

Use local deterministic execution first:

```python
runtime = toolkit.runtime(provider="python-runtime")
```

Use automatic selection when moving between local, vLLM, OpenAI and AWS environments:

```python
runtime = toolkit.runtime(provider="auto")
toolkit.show(runtime.describe())
```

If no provider signal is available, `auto` should fail explicitly instead of
silently inventing a backend.

`runtime.describe()` can be used before execution to show which provider `auto`
would select from the current environment.

## Where To Look

| Need | File |
|---|---|
| Public API | `docs/API.md` |
| CLI | `docs/CLI.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Boundaries | `docs/BOUNDARIES.md` |
| Final answer contract | `docs/RUNRESULT_FINAL_ANSWER.md` |
| Validation checklist | `docs/SMOKE_CHECKLIST_2_4_9.md` |
| Tutorial order | `tutorials/README.md` |
