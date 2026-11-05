# Graph, Context and resources · 2.1.4

[Notebook](01_common_graph.ipynb) · [English reading view](01_common_graph.md). Six Agent/System patterns cover Context, file-loaded Skills, Memory, Environment, Eval, pause/resume and model_artifact/model_server declarations. Execution is offline.

```python
from examples.common_graph.application import demonstrate
report = demonstrate()
print(report["output"])
```

Input: a 240 MXN order with a missing component. Agents normalize and classify; pricing and policy run in branches; a decision requires approval. Output: partial refund of 120 MXN with lineage. No funds are transferred.

All composition uses LangGraph Graph. Tools and units are nodes; edges define order and barriers synchronize branches. There is no alternate backend or duplicate composition constructor.

resources.py demonstrates load_skill and serving without startup. start/health/stop tests are simulated and do not certify GPU, weights or real vLLM availability. Current evidence is under revisions/2.1.4. Archived dev1 live results do not certify current artifacts.

[Historical Pydantic/human_results report](../../revisions/2.1.4/contracts-dev5/REPORT.md).
