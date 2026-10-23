# Installation of the 2.1.3 candidate

This checkout implements **2.1.3**, which has not been published by this task.
Install a supplied local wheel, without editable mode:

```bash
python -m venv .venv
# Activate the environment, then install the candidate and required dependencies.
python -m pip install /path/to/agentic_systems-2.1.3-py3-none-any.whl
agentic-systems version
agentic-systems doctor
agentic-systems new my_project
```

For an offline installation, prepare a wheelhouse containing the candidate and
all required dependencies, then add `--no-index --find-links /path/to/wheelhouse`.
The candidate manifest identifies the exact accepted bytes; using a source
checkout is a development operation, not installed-wheel evidence.

Optional extras remain `openai`, `bedrock`, `langgraph`, `openai-agents`,
`strands`, `vllm`, `vllm-client`, `vllm-server`, `dev` and `all`. Select extras
on the local wheel path, for example `"/path/to/candidate.whl[langgraph]"`.
`all` excludes the platform-specific vLLM GPU server. No `[ada]` extra is
included. Installing an extra does not start a server or validate inference.

The base import keeps optional provider and framework SDKs lazy. Python 3.10
is the declared minimum; the report distinguishes locally executed Python
versions from the CI matrix still to run. See [API](docs/API_213.md),
[tutorials](tutorials/README.md), [scaffolder](docs/SCAFFOLDER_213.md) and
[evidence](revisions/2.1.3/framework-evidence/REPORT.md).

Studio is a separate application wheel. Install the supplied SDK wheel first,
then the Studio wheel with its `ui` extra. From Python:

```python
from agentic_systems_studio import launch_studio
launch_studio()
```

Python mode needs no credentials. Configure an external provider once in the
process environment or `.env`; live validation also requires its authorized
budget ledger. See [Studio](examples/agentic_systems_studio/README.md).

For historical published 2.1.2 instructions, consult
[the archived installation guide](examples/history/2.1.2/INSTALL.md).
