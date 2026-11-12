# Runtime and scheduler · Agentic Systems 2.1.9

runtime(...) is the sole public execution-configuration factory. It retains provider, model, connection and scheduler controls from earlier releases. The internal scheduler manages time, retries, backoff and executor capacity; no additional constructor is required.

| Declaration | Scope | Effect |
|---|---|---|
| Graph | Business dependencies | Sequence, branches, barriers and decisions |
| runtime(provider, model, region, endpoint, api_key) | Actor | Explicit connection; no fallback |
| runtime(timeout_s, max_retries, backoff_s, max_concurrency) | Actor scheduler | Waiting, attempts and executor capacity |
| runtime(max_turns, max_tool_calls, max_tokens) | Actor/generation | Local controls, not monetary budgets |
| Agent(policy, contract) | Actor/business | Verifiable behavior and requirements |
| run(timeout_s=60) | Complete root | Shared deadline; children inherit remaining time |
| Environment(max_steps, stop) | Episodes | Record ceiling and business stop |
| Persistent campaign counter | Real transports | USD/requests, including failures, retries and late workers |

There is no Limits, limits= or max_actions. nodes_observed measures activations; it does not decide acceptance. Adding wrappers does not exhaust a quota. Strict Pydantic controls reject invalid numbers, booleans and strings. max_tool_calls=0 forbids Tools; max_turns must be positive.

Effective scheduler timeout is the minimum of the local limit and remaining root time. No new retry starts after root expiry; backoff does not reset the deadline. Attempts, errors and usage remain recorded. Human waiting during pause does not consume active root time. A new run is a separate execution; resume retains the original time budget. Children cannot reset it with a new timeout_s.

Timeouts are cooperative. An existing thread can finish late; forced cancellation, rollback and exactly-once effects are not promised. Preserve idempotency and live metering until workers finish.

```python
execution = toolkit.runtime(provider="python-runtime", timeout_s=30,
    max_retries=0, max_turns=2, max_tool_calls=1)
# agent = toolkit.Agent(..., runtime=execution, skills=...)
result = system.run(input_data, timeout_s=60)
```

Tools and nodes read domain data through `*, context: toolkit.Context`. LangGraph Runtime remains internal rather than a second public API.

[Lesson](../tutorials/api/03_execution_controls.md) · [Program](../examples/execution_controls/example.py) · [API](API_214.md).
