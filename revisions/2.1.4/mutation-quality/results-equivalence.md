# Results review closeout

The remaining 13 mutations are justified below for the SDK's normalized RunResult and JSON evidence domain. They remain counted by the strict gate; no exclusions are introduced.

| Function and mutation suffix | Count | Argument |
| --- | ---: | --- |
| `_preview` 7; `_Lineage.to_prompt_context` 11; `RunResult.human_results` 21; `RunResult.lineage` 273, 284 | 5 | `ensure_ascii=False` becomes `None`. Both are false in the JSON encoder branch and select the same Unicode encoder. Other arguments are unchanged. |
| `RunResult.__post_init__` 3, 4 | 2 | The first computed default status becomes always failed or always completed. Both are accepted statuses. For nonpaused results the next branch unconditionally recomputes status from ok; explicit paused status is unaffected. Invalid ok values still reach the same boolean type rejection. No intermediate status is exported. |
| `RunResult.to_dict` 8, 9, 10, 11 | 4 | A children/tool_events field is temporarily included in the initial ordinary payload dictionary. Before normalization, that same key is unconditionally overwritten with its normalized list. No initial payload is observable outside the method. This argument concerns ordinary SDK evidence records, not user-defined attribute access with external side effects. |
| `RunResult.human_results` 39 | 1 | The clipping lower bound changes from max(0, size-1) to max(1, size-1). Valid max_chars is an integer >=256, making room >=24. size-1 is therefore >=23, and neither lower bound applies. |
| `RunResult.human_results` 66 | 1 | The room lower bound changes from 16 to 17. With max_chars>=256, min(500,(max_chars-160)//4)>=24. Both lower bounds are inactive. |

All other survivors from the previous 98-case inventory are exercised by regression cases in test_results_closeout.py, alongside earlier evidence tests. The review includes direct malformed-input diagnostics, custom JSON serialization, detached resume snapshots, sequence types, exact prompt envelopes, failure priority, missing evidence, retry selection, Unicode summaries, operation allocation and final clipping boundaries.

Closing this review does not imply approval of the unchanged zero-survivor gate. Equivalences must be reconsidered if the implementation or supported input domain changes.
