# CLI and generated projects · Agentic Systems 2.1.5

The SDK wheel installs `agentic-systems`. Run these commands in the environment
where you installed the SDK:

| Command | Result | Boundary |
|---|---|---|
| `agentic-systems version` | Installed SDK version | Does not inspect a repository checkout |
| `agentic-systems api` | JSON version and exported public names | Does not list signatures or provider capabilities |
| `agentic-systems doctor` | JSON flags for installed optional modules | Does not test credentials, service access or dependency compatibility |
| `agentic-systems new my_project` | New offline application directory | Refuses existing files/directories; does not install the project |

```bash
agentic-systems version
agentic-systems doctor
agentic-systems new my_project
cd my_project
python -m pip install -e '.[test]'
python examples/quote.py
python app.py
python -m pytest -q
```

Use `python -m agentic_systems.cli` if your environment's executable directory is
not on PATH. `--help` and `new --help` show accepted arguments. An existing
project destination is rejected with exit code 2; choose a different path.

Start with `examples/quote.py`: amount 5000 produces fee 50. Then read
`src/order_fulfillment/application.py` and run `app.py`: the supplied missing-item
order produces a partial refund of 120 MXN. The generated notebook exposes the
same declarations. `tests/test_refund.py` checks the business result and missing
required input. The notebook requires a Jupyter kernel in this environment.

The generated project includes Tools, Skills, Agents, System, Context, Memory,
Environment, Eval and recorded results. It uses deterministic Python, consumes
no model inference and needs no provider credentials. Generating it alone is
not validation; run its commands and tests. Do not attach a model merely to run
this starting example.

The separate ADA add-on installs `agentic-systems-ada doctor`. Its diagnostics
inspect configuration without resolving credentials or querying AWS.
[Installation](../INSTALL.md) · [API](API.md) · [AWS/ADA](ADA_214.md).
