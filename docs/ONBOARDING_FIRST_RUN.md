# First Run Onboarding

This is the shortest supported path from installation to an observable
Agentic Systems run. The user path is deliberately simple:

```text
install -> configure external boundary -> open notebook -> Run All
```

No notebook requires a hidden activation cell, a local adapter, or a manual
result construction.

## Install

For library and CLI use from PyPI:

```bash
python -m pip install -U pip
python -m pip install "agentic-systems[openai,bedrock]"
```

The notebooks are repository content; clone the repository before opening them:

```bash
git clone https://github.com/JacoboGGLeon/agentic_systems.git
cd agentic_systems
python -m pip install -U pip
python -m pip install -e ".[dev,openai,bedrock]"
```

The OpenAI extra also provides the OpenAI-compatible client used by a remote
vLLM endpoint. Install `agentic-systems[vllm]` only when the same supported
Linux environment must also host the vLLM server. Agentic Systems never starts
that server implicitly.

For development gates:

```bash
python -m pip install -e ".[dev,openai,bedrock,langgraph]"
```

## Verify The Local Contract First

These commands do not call an external model:

```bash
agentic-systems version
agentic-systems doctor --json
agentic-systems api --tier public --json
```

Then verify the public Python surface:

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="python-runtime")
system = toolkit.system(runtime=runtime)

assert toolkit.__version__ == "1.1.3"
assert callable(toolkit.tool)
assert callable(toolkit.skill)
assert callable(toolkit.agent)
assert callable(toolkit.system)
assert callable(toolkit.graph)
assert callable(toolkit.environment)
assert callable(toolkit.eval)

toolkit.show(runtime.describe(), title="Local runtime")
```

## Configure Provider Notebooks

Set configuration in the same shell that starts Jupyter. The explicit
`RUN_*_LIVE=1` values are optional because live execution is already the default
when readiness passes; they make intent visible in a demo session.

### POSIX Shell Or Git Bash

```bash
export OPENAI_API_KEY='...'
export OPENAI_MODEL='gpt-4.1-mini'
export RUN_OPENAI_LIVE=1

export VLLM_BASE_URL='http://127.0.0.1:8000/v1'
export VLLM_MODEL='your-model'
export RUN_VLLM_LIVE=1

export AWS_PROFILE='your-profile'
export AWS_REGION='us-east-1'
export BEDROCK_MODEL_ID='your-model-id'
export RUN_BEDROCK_LIVE=1

python -m jupyter lab
```

### PowerShell

```powershell
$env:OPENAI_API_KEY = '...'
$env:OPENAI_MODEL = 'gpt-4.1-mini'
$env:RUN_OPENAI_LIVE = '1'

$env:VLLM_BASE_URL = 'http://127.0.0.1:8000/v1'
$env:VLLM_MODEL = 'your-model'
$env:RUN_VLLM_LIVE = '1'

$env:AWS_PROFILE = 'your-profile'
$env:AWS_REGION = 'us-east-1'
$env:BEDROCK_MODEL_ID = 'your-model-id'
$env:RUN_BEDROCK_LIVE = '1'

python -m jupyter lab
```

The kernel inherits variables from the Jupyter process. Never paste real
credentials into notebooks, Markdown, commits or screenshots.

## What Run All Does

Provider notebooks evaluate readiness before crossing an external boundary:

| Notebook | Ready when | Run All behavior |
|---|---|---|
| `00_runtime_openai_provider_api.ipynb` | `OPENAI_API_KEY` is available | Executes `runtime -> system -> agent -> RunResult`. |
| `00_runtime_vllm_provider_api.ipynb` | `VLLM_BASE_URL` and `VLLM_MODEL` are configured | Calls the OpenAI-compatible endpoint through `vllm-runtime`. |
| `00_runtime_bedrock_provider_api.ipynb` | The standard AWS chain resolves credentials | Calls Bedrock through `bedrock-runtime`. |
| `06_integrations_strands_api.ipynb` | `provider="auto"` resolves a concrete provider | Executes the declarative Strands identity over that runtime. |
| `07_integrations_openai_runtime_api.ipynb` | `provider="auto"` resolves a concrete provider | Executes the OpenAI Agents-style identity over that runtime. |

If readiness fails, the notebook returns an actionable preflight skip; it does
not fabricate a `RunResult`. The pattern `RUN_*_LIVE=0` means choosing the corresponding provider-specific
flag. To deliberately suppress a configured provider,
set its flag to zero before starting Jupyter:

```bash
export RUN_OPENAI_LIVE=0
export RUN_VLLM_LIVE=0
export RUN_BEDROCK_LIVE=0
export RUN_STRANDS_IDENTITY_LIVE=0
export RUN_OPENAI_STYLE_LIVE=0
```

## Tutorial Order

Run notebooks top to bottom. Every code cell consumes the installed public API.

```text
00_runtime_api.ipynb
00_runtime_bedrock_provider_api.ipynb
00_runtime_openai_provider_api.ipynb
00_runtime_scheduler_api.ipynb
00_runtime_vllm_provider_api.ipynb
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
11_single_agentic_system_api.ipynb
12_multi_agentic_system_api.ipynb
13_multi_agentic_graph_api.ipynb
```

The deterministic notebooks run without external credentials. Graph notebooks
use `engine="auto"`: native LangGraph when available, otherwise the portable
backend.

## If A Provider Is Skipped Unexpectedly

Confirm that the Jupyter process inherited the configuration without printing
secrets:

```bash
python -c "import os; print('openai', bool(os.getenv('OPENAI_API_KEY')))"
python -c "import os; print('vllm', bool(os.getenv('VLLM_BASE_URL')), bool(os.getenv('VLLM_MODEL')))"
python -c "import os; print('aws-profile', bool(os.getenv('AWS_PROFILE')), 'region', bool(os.getenv('AWS_REGION')))"
```

Inspect provider resolution:

```bash
agentic-systems runtime --provider auto --json
```

Or from Python:

```python
import agentic_systems as toolkit

toolkit.show(
    toolkit.runtime(provider="auto").describe(),
    title="Resolved provider",
)
```

Default auto priority is Bedrock, OpenAI, then vLLM. A provider is selected only
when its environment signals are usable; a region alone is not AWS
authentication.

## Documentation Map

| Need | Document |
|---|---|
| Public surface and contracts | [API](API.md) |
| Tutorial teaching rules | [Tutorials](../tutorials/README.md) |
| Architecture and namespace ownership | [Architecture](ARCHITECTURE.md) |
| Runtime, Provider and Framework boundaries | [Runtime And Framework Contracts](RUNTIME_AND_FRAMEWORK_CONTRACTS.md) |
| CLI diagnostics | [CLI](CLI.md) |
| RunResult and final-answer invariants | [RunResult Contract](RUNRESULT_CONTRACT.md) |
| Version history | [Changelog](../CHANGELOG.md) |
