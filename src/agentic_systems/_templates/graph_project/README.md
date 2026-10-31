# Refund graph

Orchestration uses toolkit.Graph from LangGraph, state, nodes and edges. Python is the
offline operator runtime. Run `python app.py` or open the notebook. No provider
flags, model inference or GPU process is required. The application code is in
src/order_fulfillment/application.py. Resources demonstrates load_skill and
serving declarations without starting vLLM.

Start with `python examples/quote.py`: the Tool, Agent and Graph are visible.
Then inspect the refund application and its notebook with all declarations.
For the generated tests, install the test extra and run pytest:

```console
python -m pip install -e '.[test]'
python -m pytest -q
```

These tests check a real deterministic business outcome and missing input. They
do not call models or certify IAM/ADA. The SDK is pinned to the version that
generated this project; install that local wheel before the application.
