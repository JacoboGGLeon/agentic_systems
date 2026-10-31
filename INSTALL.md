# Install Agentic Systems 2.1.4

Use Python 3.10–3.14 in a clean environment:

```bash
python -m venv .venv
# Activate .venv with your operating system's usual command.
python -m pip install --upgrade pip
python -m pip install "agentic-systems==2.1.4"
```

For the supported model-backed actor integrations:

```bash
python -m pip install "agentic-systems[openai,bedrock,openai-agents,strands]==2.1.4"
```

```python
import pydantic
import agentic_systems as toolkit
assert toolkit.__version__ == "2.1.4"
```

The wheel includes the SDK and CLI. Python execution does not require model credentials.
Configure OpenAI, Bedrock or Ollama credentials outside code and notebooks; do not
commit a .env file. Declare endpoint and key explicitly when mixing Ollama local/cloud.
The CLI's doctor checks installed dependencies, not provider access.

```bash
agentic-systems version
agentic-systems api
agentic-systems doctor
agentic-systems new my_project
```

## Studio, learning material and skill

Download the matching assets from the GitHub release:
https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.4

Extract agentic-systems-studio-2.1.4.zip. From its studio directory:

```bash
python -m pip install "wheels/agentic_systems_studio-2.1.4-py3-none-any.whl[ui,notebook]"
python -m streamlit run app.py
```

Follow the included Studio README for launch commands. Tutorials/examples and docs
are in agentic-systems-learning-2.1.4.zip. Install a Jupyter kernel in this same
environment before executing notebooks. Live cells require configured providers
and an explicitly authorized persistent budget; reading saved outputs costs nothing.

Extract agentic-systems-skill-2.1.4.zip into your Codex/ChatGPT skills directory,
retaining the agentic-systems folder and its SKILL.md, references, scripts and assets.
The optional ADA asset is separate; its diagnostics do not certify AWS/ADA access.

## Reproducibility

Verify SHA-256 against release-manifest.json before installation. TestPyPI, PyPI and
GitHub promote the same SDK distributions. Historical dev8 runs retain their original
artifact identities; stable acceptance explicitly uses approved executable-payload
equivalence plus stable offline CI, without claiming new stable live inference.
See docs/RELEASE_NOTES_214.md for known limitations and the acceptance scope.
