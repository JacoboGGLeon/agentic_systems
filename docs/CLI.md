# CLI

Agentic Systems exposes a small command line interface for package diagnostics,
runtime inspection and API inventory.

The CLI is not a second framework. It does not replace Python usage through:

```python
import agentic_systems as lab
```

It exists to make installs, provider selection and public API coverage
observable from a terminal.

## Commands

```bash
agentic-systems version
agentic-systems doctor
agentic-systems runtime
agentic-systems api
agentic-systems public-api
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
agentic-systems runtime --provider python-direct
agentic-systems runtime --provider openai-runtime --model gpt-4.1-mini
agentic-systems runtime --provider bedrock-runtime --region us-east-1
```

This command constructs `RuntimeConfig` and prints `runtime.describe()` without
executing a model. For `provider="auto"`, it reads environment signals such as
`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `AWS_REGION` and `AWS_PROFILE` to show the
effective provider selection.

OpenAI runtime also reads `AGENTIC_SYSTEMS_OPENAI_MODEL_ID`,
`OPENAI_MODEL_ID`, `OPENAI_MODEL`, `OPENAI_ORG_ID` and `OPENAI_PROJECT`.

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

Before running provider notebooks, configure credentials in the shell or host
environment that launches Jupyter/VSCode. The CLI and notebooks read these
variables; they do not ask for or persist secrets.

You can use either exported variables or a local `.env` file. `.env` is ignored
by git.

```powershell
$env:OPENAI_API_KEY="your_key_here"
agentic-systems runtime --provider auto --json
```

Git Bash:

```bash
export OPENAI_API_KEY="your_key_here"
agentic-systems runtime --provider auto --json
```

Expected OpenAI output includes:

```json
{
  "selected_provider": "openai-runtime",
  "mode": "auto",
  "model": "gpt-4o-mini",
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

Use `api` to inspect the API tiers from `agentic_systems.api`.

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
| `recommended` | Names to teach and use first. |
| `advanced` | Public advanced names, including systems, evals and notebook utilities. |
| `public` | 100 percent of `PUBLIC_API`. |

The JSON form returns:

```json
{
  "tier": "public",
  "count": 101,
  "symbols": ["agent", "runtime"]
}
```

The example above is shortened; the actual `symbols` list contains the complete
selected tier.

## Public API Compatibility Command

`public-api` remains available as a compact compatibility command:

```bash
agentic-systems public-api
agentic-systems public-api --all --json
```

Prefer `agentic-systems api --tier public --json` when validating 100 percent
of the API surface.

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
