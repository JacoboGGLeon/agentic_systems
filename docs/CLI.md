# CLI

Agentic Systems exposes a small command line interface for package diagnostics,
runtime inspection and API inventory.

The CLI is not a second framework. It does not replace Python usage through:

```python
import agentic_systems as toolkit
```

It exists to make installs, provider selection and public API coverage
observable from a terminal.

## Commands

```bash
agentic-systems version
agentic-systems contact
agentic-systems doctor
agentic-systems runtime
agentic-systems model-server inspect
agentic-systems api
agentic-systems public-api
agentic-systems tool run
agentic-systems skill inspect
agentic-systems agent run
agentic-systems system run
agentic-systems environment run
agentic-systems graph run
agentic-systems eval run
agentic-systems matrix check
```

If `agentic-systems` is not found after activating a virtual environment,
reinstall the package in editable mode so Python regenerates the console script:

```bash
python -m pip install -e .
```

You can always use the module form while diagnosing the environment:

```bash
python -m agentic_systems.cli doctor
```


## Contact

```bash
agentic-systems contact
agentic-systems contact --json
```

Prints package author and project contact information:

```text
Author: Jacobo Gerardo González León
E-Mail 1: jacobogerardo.gonzalez@bbva.com
E-Mail 2: jacoboggleon@gmail.com
LinkedIn: https://www.linkedin.com/in/jacoboggleon/
Github Repo: https://www.github.com/JacoboGGLeon/agentic_systems
```

## Version

```bash
agentic-systems version
```

Prints the installed package version.

## Doctor

```bash
agentic-systems doctor
agentic-systems doctor --json
```

Reports:

```text
package name
package version
Python version
supported engines
whether .env was loaded
safe environment presence flags
optional dependency availability
```

Use this before running notebooks in a new local, OpenAI or AWS sandbox.

Agentic Systems loads a local `.env` file for diagnostics and runtime
description. It never prints secret values and it does not override variables
that are already exported in the shell.

Use `.env.example` as the template:

```bash
cp .env.example .env
```

For OpenAI runtime, install the optional SDK dependency:

```bash
python -m pip install -e ".[openai]"
```

## Runtime

```bash
agentic-systems runtime --provider auto --json
agentic-systems runtime --provider python-runtime
agentic-systems runtime --provider openai-runtime --model gpt-4.1-mini
agentic-systems runtime --provider bedrock-runtime --region us-east-1
agentic-systems runtime --provider vllm-runtime --model unsloth/Qwen3-4B-Instruct-2507
```

This command constructs `RuntimeConfig` and prints `runtime.describe()` without
executing a model. For `provider="auto"`, it reads environment signals such as
`VLLM_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and paired
AWS region/authentication signals to show the effective provider selection.
For Bedrock, a region must be accompanied by `AWS_BEARER_TOKEN_BEDROCK` or by
static credentials, an AWS profile, web identity, container credentials, or a
shared credentials file.

Default auto priority is `bedrock-runtime`, then `openai-runtime`, `vllm-runtime`, and `ollama-runtime`. Override it with `--provider-priority bedrock-runtime,openai-runtime,vllm-runtime,ollama-runtime` or `AGENTIC_SYSTEMS_PROVIDER_PRIORITY`. Add `--allow-python-fallback` only when deterministic local fallback is intentional.

OpenAI runtime also reads `OPENAI_MODEL`.

vLLM runtime also reads `VLLM_MODEL` and `VLLM_API_KEY`. It uses the
OpenAI-compatible vLLM server API; the `runtime` command does not start the server.

Inspect the exact managed-server declaration without starting a process:

```bash
agentic-systems model-server inspect \
  --model unsloth/Qwen3-4B-Instruct-2507 \
  --profile fast \
  --reasoning-parser qwen3 \
  --json
```

The JSON is the same `VLLMServerSpec` consumed by `toolkit.model_server(...)`.
Process mutation remains explicit in Python through `server.start()` and
`server.stop()`; the CLI `inspect` subcommand is read-only.

Bedrock runtime reads `BEDROCK_MODEL_ID`, `AWS_REGION`, `AWS_DEFAULT_REGION`,
`AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
and `AWS_BEARER_TOKEN_BEDROCK`. CLI output only reports safe availability flags;
it never prints secret values.

Important fields:

```text
selected_provider
mode
model
region
scheduler
reason
configuration
```

Before running provider notebooks, copy `.env.example` to the local `.env` and
configure that environment. The CLI and notebooks read the nearest `.env`; they
do not ask for, persist, clear or replace secrets. `.env` is ignored by Git.

For SageMaker/ADA IAM, keep `AWS_BEARER_TOKEN_BEDROCK=` empty so boto3 inherits
the execution role through its standard credential chain. Give it a non-empty
value only for the native Bedrock API-key route.

```powershell
$env:OPENAI_API_KEY="your_key_here"
agentic-systems runtime --provider auto --json
```

Git Bash:

```bash
export OPENAI_API_KEY="your_key_here"
agentic-systems runtime --provider auto --json
```

For vLLM/OpenAI-compatible local or Colab GPU inference:

```bash
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
export VLLM_MODEL="unsloth/Qwen3-4B-Instruct-2507"
export VLLM_API_KEY="EMPTY"
agentic-systems runtime --provider auto --json
```

Expected vLLM output includes:

```json
{
  "selected_provider": "vllm-runtime",
  "mode": "auto",
  "model": "unsloth/Qwen3-4B-Instruct-2507",
  "configuration": {
    "vllm": {
      "base_url_configured": true
    }
  }
}
```

Expected OpenAI output includes:

```json
{
  "selected_provider": "openai-runtime",
  "mode": "auto",
  "model": "gpt-4.1-mini",
  "configuration": {
    "openai": {
      "api_key_configured": true
    }
  }
}
```

For Bedrock:

```powershell
$env:AWS_REGION="us-east-1"
$env:AWS_PROFILE="your_profile"
agentic-systems runtime --provider auto --json
```

Git Bash:

```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="your_profile"
agentic-systems runtime --provider auto --json
```

Expected Bedrock output includes:

```json
{
  "selected_provider": "bedrock-runtime",
  "mode": "auto"
}
```

## API Inventory

Use `api` to inspect the canonical contract projected from
`agentic_systems.api_contract()`.

```bash
agentic-systems api
agentic-systems api --tier recommended
agentic-systems api --tier advanced
agentic-systems api --tier public
agentic-systems api --tier public --json
agentic-systems api --tier public --contains runtime --json
```

Tiers:

| Tier | Meaning |
|---|---|
| `recommended` | Recommended exports and all their public members. |
| `advanced` | Advanced exports and all their public members. |
| `public` | 100 percent of the export/member contract IDs. |

The JSON form returns:

```json
{
  "tier": "public",
  "count": 467,
  "ids": ["agent", "Agent.run", "runtime"]
}
```

The example above is shortened. `ids` contains contract IDs for both
exports and members; `recommended` and `advanced` form a disjoint partition.

## Public API Compatibility Command

`public-api` remains available as a compact compatibility command:

```bash
agentic-systems public-api
agentic-systems public-api --all --json
```

Prefer `agentic-systems api --tier public --json` when validating the exact
export/member surface.

## What The CLI Should Not Do

The CLI should stay diagnostic and package-oriented.

Do not add:

```text
business workflows
notebook-specific behavior
provider SDK side effects during import
hidden credential assumptions
long-running model execution as a default command
```

Model execution belongs in Python code and notebooks where contracts, runtime,
lineage and human output are explicit.

## Executable 2.1 workflows

The CLI exposes the same public grammar taught by the notebooks. Every workflow
runs through agentic_systems public factories; it is not a parallel
implementation.

| Concept | Command | Offline evidence |
|---|---|---|
| Tool | agentic-systems tool run --value ok --json | RunResult from Tool.run |
| Skill | agentic-systems skill inspect --json | Skill.describe |
| Agent | agentic-systems agent run --value ok --json | Python Runtime RunResult |
| System | agentic-systems system run --value ok --json | Compiled system RunResult |
| Graph | agentic-systems graph run --value ok --json | Portable Graph final state |
| Environment | agentic-systems environment run --value ok --json | One episode and summary |
| Eval | agentic-systems eval run --value ok --json | One deterministic EvalReport |
| Matrix | agentic-systems matrix check --json | Four offline passes and sixteen not-run rows |

Each workflow JSON includes `scenario` and `scenario_api_ids`, projected from
the shared Source manifest rather than maintained as a second CLI registry.

The API registry resolves every stable export and public member:

    agentic-systems api list --tier public --json
    agentic-systems api describe Agent.run --json
    agentic-systems api exercise Agent.run --json
    agentic-systems api exercise --all --json

To cross external Provider boundaries explicitly:

    agentic-systems matrix check --live --json
    agentic-systems matrix check --provider bedrock-runtime --live --require-pass --json

Without --live, external rows are not-run and include a reason. With --live,
configured rows are passed only after a real RunResult; Provider errors are
reported as failed. Add `--require-pass` in CI or live notebooks: the command
still emits its complete Rich/JSON evidence, but returns exit code 1 if any
selected row is failed or not-run. Credentials are read from the environment
and never printed.
