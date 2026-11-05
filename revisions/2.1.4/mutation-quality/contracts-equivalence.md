# Remaining contract mutations

The actor bridge has three remaining equivalent mutation candidates:

- `_invoke_actor_with_connection__mutmut_3` and `__mutmut_5`: the absent `tool_expectation` default changes from `{}` to `None`. Contracts have already been normalized to ordinary dictionaries. Both absent defaults are false, and the expectation value is only consumed inside `if expectation`. A present key is unaffected. Therefore these two default changes do not change bridge behavior for normalized contracts.
- `_invoke_actor_with_connection__mutmut_69`: `json.dumps(..., ensure_ascii=False)` becomes `ensure_ascii=None`. Both are false in the encoder's boolean check and select the same Unicode string encoder. No other argument changes.

These arguments apply to the current implementation and normalized input domain. They are not mutation exclusions. All three continue to count as survivors under the unchanged gate. Closing behavioral gaps does not imply a passing gate.
