# Run examples · Agentic Systems 2.1.5

Use a repository checkout or the matching learning archive. The SDK wheel
contains the library and CLI; it does not contain these application folders.
Keep the repository layout intact, including linked local Skill resources.

## Prepare once

Activate a clean Python 3.10–3.14 virtual environment, then install:

```bash
python -m pip install 'agentic-systems[openai,bedrock,openai-agents,strands]==2.1.5'
agentic-systems version
```

The optional SDK actors are needed by examples that exercise them even when they
use deterministic Python. No model credentials are required for the offline
runner. The borrowed-session lesson additionally needs the separate ADA add-on;
follow [its installation guide](../integrations/ada/README.md).

## Run one lesson

From the repository root:

```bash
python scripts/run_example.py examples/patterns/text_analysis/example.py
```

The supplied text is `evidence supports evidence`; expect data with words=3,
unique=2 and mentions=2. The entrypoint asserts that result before printing JSON.
A failed assertion gives a nonzero exit code. Check Tool events and invariants
as well as business data; `ok` describes execution, not universal truth.

The runner uses the installed 2.1.5 SDK and denies application networking and
subprocess execution. It refuses historical examples and the separate Strands
local-service case. It does not execute tagged live notebook cells or start
GPU/HTTP servers. The offline denial helper is a Python-level application guard,
not a hostile-code sandbox. Only run source and local Skills you trust.

## Make a meaningful change

Read the supplied input, Tool body and assertions. Change one input and predict
the output. Keep the original positive case and add a separate negative check.
For a refund rule, test both sides of its amount/age boundary; for typed inputs,
test a missing field and an incorrect type. A business `review` decision is not
necessarily a runtime failure. An intentionally failed Tool can be successful
validation if the test requires that failure.

When moving to a model, configure its provider, endpoint/region and actor
framework explicitly. Authorize and meter inference attempts, including errors
and finalization; do not reuse an offline PASS as provider certification.
[Required-tool recipe](ACTOR_CONTRACTS.md) · [Live configurations](VALIDATION_215_20261108.md).

## Read notebooks

Use a fresh Jupyter kernel in the installed environment and run cells in order.
[The notebook index](NOTEBOOKS.md) links sources and Markdown reading views.
Saved outputs may come from historical runs; narrative target version and
execution provenance are different. Regenerate reading views after editing source
notebooks with `python scripts/render_notebook_docs.py`.
