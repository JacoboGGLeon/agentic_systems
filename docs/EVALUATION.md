# Independent evaluation · 2.1.8

Eval targets an Agent, System or Environment. It does not require an Environment. Environment can also be used without Eval.

Declare cases as dictionaries with input and optional expected. expected supports ok and data; data compares the complete business dictionary. Custom checks receive (result, case) and return a dictionary with boolean ok and optional issues/metrics. For failure acceptance explicitly use expected={"ok": False}; a correct rejection can make Eval pass while its target fails.

Eval is fail-fast: later cases may not run after a failure. Use independent evaluations when you need every negative scenario reported. Check/judge evaluation gets an isolated view of toolkit Memory; files, services and SDK sessions are not sandboxed.

## Five executable cases

From the repository root, after installing the candidate SDK:

```bash
python examples/eval_recipes.py
```

| Evaluation | Target | Acceptance |
|---|---|---|
| correct_result | Agent | Exact fee output |
| required_tool | Agent | Correct sum and a successful add event with exact arguments |
| conditional_route | System | Correct high/low-risk branch and no forbidden Tool event |
| expected_failure | System | Failed inventory recorded; confirmation not executed |
| episodes_and_stop | Environment | Totals 2 then 5; stop before record 100 |

[Complete visible source](../examples/eval_recipes.py) declares all graphs and checks. It also reruns each evaluation with a deliberately rejecting check and requires unsuccessful acceptance. Expected output has five PASS lines and five NEGATIVE CONTROL PASS lines. No model requests are involved.

## Result versus trajectory

Checks inspect result.data for output, and result.walk()/tool_events/lineage for observed execution. Correct text alone does not prove a required Tool ran. Event membership proves recorded execution, not time ordering or actual overlap. To test concurrency, record intervals or synchronization explicitly.

For LM actors, use [actor contracts](ACTOR_CONTRACTS.md) to constrain required Tools, then independently inspect evidence. An optional judge Agent can consume model requests; deterministic fixture judges only test the protocol. Evaluating saved evidence is a different workflow from rerunning a unit: see [saved execution example](../examples/patterns/saved_execution_eval/README.md).
