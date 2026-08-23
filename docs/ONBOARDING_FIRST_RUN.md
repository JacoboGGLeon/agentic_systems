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
python -m pip install "agentic-systems[all]==2.1.0"
```

The notebooks are repository content; clone the repository before opening them:

```bash
git clone https://github.com/JacoboGGLeon/agentic_systems.git
cd agentic_systems
python -m pip install -U pip
python -m pip install -e ".[all]"
```

The OpenAI extra also provides the OpenAI-compatible client used by a remote
vLLM endpoint. Install `agentic-systems[vllm-server]` only when the same supported
Linux environment must also host the vLLM server. Agentic Systems can own that process only through an explicit `model_server(...).start()` call; constructing the server or runtime never starts it.

For development gates:

```bash
python -m pip install -e ".[all]"
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

assert toolkit.__version__ == "2.0.0"
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

Alternatively, copy `.env.example` to `.env` at the repository root and fill
only the Providers you use. Runtime factories, Provider environment snapshots,
notebooks and the CLI load the nearest `.env` while walking upward from the
current directory. Existing process variables take precedence over file values.
The file is ignored by Git; never paste credentials into notebooks, outputs or
commits.

### POSIX Shell Or Git Bash

```bash
export OPENAI_API_KEY='...'
export OPENAI_MODEL='gpt-4.1-mini'
export RUN_OPENAI_LIVE=1

export VLLM_BASE_URL='http://127.0.0.1:8000/v1'
export VLLM_MODEL='your-model'
export RUN_VLLM_LIVE=1

# Choose one Bedrock authentication mode:
export AWS_PROFILE='your-profile'  # standard AWS/ADA credential chain
# export AWS_BEARER_TOKEN_BEDROCK='...'  # native Bedrock API key
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

# Choose one Bedrock authentication mode:
$env:AWS_PROFILE = 'your-profile'  # standard AWS/ADA credential chain
# $env:AWS_BEARER_TOKEN_BEDROCK = '...'  # native Bedrock API key
$env:AWS_REGION = 'us-east-1'
$env:BEDROCK_MODEL_ID = 'your-model-id'
$env:RUN_BEDROCK_LIVE = '1'

python -m jupyter lab
```

The kernel inherits variables from the Jupyter process. Never paste real
credentials into notebooks, Markdown, commits or screenshots.

## What Run All Does

Provider notebooks evaluate readiness before crossing an external boundary:

| Notebook | Readiness | Behavior |
|---|---|---|
| providers/01_openai.ipynb | OPENAI_API_KEY | Executes runtime -> system -> agent -> RunResult |
| providers/03_vllm.ipynb | VLLM_BASE_URL and VLLM_MODEL | Calls the OpenAI-compatible endpoint |
| providers/02_bedrock.ipynb | Region plus SigV4 credentials or AWS_BEARER_TOKEN_BEDROCK | Calls the same boto3 bedrock-runtime Provider |
| frameworks/00_langgraph.ipynb | Always ready offline | Executes real LangGraph; Provider auto is optional |
| frameworks/01_openai_agents.ipynb | Always ready offline | Executes real OpenAI Agents; Provider auto is optional |
| frameworks/02_aws_strands.ipynb | Always ready offline | Executes real Strands and local MCP transports |

If readiness fails, the notebook returns an actionable preflight skip. A skip is
not counted as live evidence.

## Tutorial Order

Run notebooks in the canonical pedagogical order inherited from 1.1.3:

    tutorials/providers/00_auto.ipynb
    tutorials/providers/02_bedrock.ipynb
    tutorials/providers/01_openai.ipynb
    tutorials/core/00_runtime_scheduler.ipynb
    tutorials/providers/03_vllm.ipynb
    tutorials/core/01_tool.ipynb
    tutorials/core/02_skills.ipynb
    tutorials/core/03_agent.ipynb
    tutorials/core/04_results_lineage.ipynb
    tutorials/frameworks/02_aws_strands.ipynb
    tutorials/frameworks/01_openai_agents.ipynb
    tutorials/frameworks/00_langgraph.ipynb
    tutorials/core/05_system.ipynb
    tutorials/core/06_graph_native.ipynb
    tutorials/core/07_environment_eval.ipynb
    tutorials/core/08_single_agentic_system.ipynb
    tutorials/core/09_multi_agentic_system.ipynb
    tutorials/core/10_multi_agent_graph.ipynb
    tutorials/frameworks/03_provider_framework_matrix.ipynb
    tutorials/api/14_api_contract_matrix.ipynb

The 17 deterministic notebooks run without external credentials. Start Jupyter
with RUN_*_LIVE=0 when the machine must not cross an external boundary.

## If A Provider Is Skipped Unexpectedly

Confirm that the Jupyter process inherited the configuration without printing
secrets:

```bash
python -c "import os; print('openai', bool(os.getenv('OPENAI_API_KEY')))"
python -c "import os; print('vllm', bool(os.getenv('VLLM_BASE_URL')), bool(os.getenv('VLLM_MODEL')))"
python -c "import os; print('aws-profile', bool(os.getenv('AWS_PROFILE')), 'bedrock-api-key', bool(os.getenv('AWS_BEARER_TOKEN_BEDROCK')), 'region', bool(os.getenv('AWS_REGION')))"
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
when its environment signals are usable; a region alone is not authentication.
For Bedrock, either the standard AWS/ADA credential chain or
`AWS_BEARER_TOKEN_BEDROCK` satisfies the authentication signal.

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
