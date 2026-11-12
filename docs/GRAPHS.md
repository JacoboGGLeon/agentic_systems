# Graphs · 2.1.9

Declare business channels in a Pydantic state model. A node returns partial updates; output channels absent from the declared schema can be projected away. A Tool with input_schema and one business argument receives the complete Pydantic model.

| Need | Graph declaration | Executable lesson |
|---|---|---|
| Sequence | add_edge('first', 'second') | [Flow semantics](../examples/flow_semantics/example.py) |
| Conditional route | add_conditional_edges with a named Python function | [Five evaluations](../examples/eval_recipes.py) |
| Parallel branches | Multiple outgoing edges | [Common graph](../examples/common_graph/01_common_graph.md) |
| Wait for branches | add_edge(['left', 'right'], 'join') | [Flow semantics](../examples/flow_semantics/example.py) |
| Nested composition | Add an Agent or System as a node | [Complete composition](../examples/checked_composition/example.py) |

Parallel writers need disjoint output channels or explicit reducers. A nested Agent returning its entire state can conflict with another branch; give it an output_schema selecting only its owned channels. Do not infer temporal overlap from result.walk() order: test synchronization or intervals when concurrency itself is the requirement.

Execute the graph through its Agent/System/Environment owner to obtain toolkit RunResult evidence. Raw LangGraph APIs have their own return contracts. The integrated subset restricts some native node caching/retry/error-handler options; see [construction guide](API_214.md).

[Concepts](CONCEPTS.md) · [Execution](EXECUTION.md)
