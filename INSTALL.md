# Install Agentic Systems 2.1.8

Install the matching versioned distribution when available. During pre-publication acceptance, install the supplied frozen wheel instead.
For pre-publication acceptance, install the exact supplied frozen wheel instead,
in the Python interpreter that actually runs the application:

```bash
python -m pip install "wheels/agentic_systems-2.1.8-py3-none-any.whl[bedrock]"
```

In Jupyter, use `%pip` in the target kernel and restart after installation.
Installing in Studio does not install packages in a remote EMR driver.

Use Python 3.10–3.14 in a clean environment:

```bash
python -m venv .venv
# Activate .venv with your operating system's usual command.
python -m pip install --upgrade pip
python -m pip install "agentic-systems==2.1.8"
```

For the supported model-backed actor integrations:

```bash
python -m pip install "agentic-systems[openai,bedrock,openai-agents,strands]==2.1.8"
```

```python
import pydantic
import agentic_systems as toolkit
assert toolkit.__version__ == "2.1.8"
```

The wheel includes the SDK and CLI. Python execution does not require model credentials.
Configure OpenAI, Bedrock or Ollama credentials outside code and notebooks; do not
commit a .env file. Declare endpoint and key explicitly when mixing Ollama local/cloud.
The CLI's doctor checks installed dependencies, not provider access.

```bash
agentic-systems version
agentic-systems api
agentic-systems doctor
agentic-systems skill info
agentic-systems skill install
```

## Studio, learning material and skill

Download the matching assets from the GitHub release:
https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.8

Extract agentic-systems-studio-2.1.8.zip. From its studio directory:

```bash
python -m pip install "wheels/agentic_systems_studio-2.1.8-py3-none-any.whl[ui,notebook]"
python -m streamlit run app.py
```

Follow the included Studio README for launch commands. Tutorials/examples and docs
are in agentic-systems-learning-2.1.8.zip. Install a Jupyter kernel in this same
environment before executing notebooks. Live cells require configured providers
and an explicitly authorized persistent budget; reading saved outputs costs nothing.

The SDK wheel includes the authoring skill. Use `agentic-systems skill install`
to copy it, or `agentic-systems skill export skill.zip` for manual import.
The optional ADA asset is separate; its diagnostics do not certify AWS/ADA access.

## Reproducibility

Verify SHA-256 against the release's manifest before installation. Historical
reports retain their original wheel identities. Current integration configurations
and scope are listed in [the historical 2.1.5 campaign report](docs/VALIDATION_215_20261108.md).
Editing documentation does not replace published artifacts or their metadata.

For vLLM server execution, use the separately pinned Python 3.12 GPU environment
in the campaign report; the SDK's Python range does not imply every GPU server
package supports that entire range.


## CLI migration

Version 2.1.8 removes `agentic-systems new`. Start applications from the
repository examples or the bundled skill assets. Existing projects are untouched.
