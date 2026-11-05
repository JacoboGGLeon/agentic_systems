# Graph, Pydantic Tools and results · 2.1.4

[Notebook](01_checked_composition.ipynb) · [English reading view](01_checked_composition.md) · [Program](example.py). The folder name is historical; the current API has no check constructor.

Input 5000 cents → graph-backed Agent computes fee=50 and total=5050 → reviewer Agent applies Context → System approves. Environment also processes 12000 and returns pending_review. Pydantic Tools reject missing, incorrect and extra inputs.

compile prepares without business execution. Eval checks both cases using isolated Memory views; production Memory retains three episodes. human_results shows inputs, operations and decisions without repeating wrapper IDs. RunResult.to_dict/lineage retains complete evidence.

Reward is explicitly computed in update and retained in state/history. Matching the Environment oracle adds one; total_reward=2. The oracle is not passed to the System. There is no reward= parameter or automatic training.

[API](../../docs/API_214.md) · [Historical report](../../revisions/2.1.4/grammar-dev7/REPORT.md).
