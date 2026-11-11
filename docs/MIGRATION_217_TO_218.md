# Migration from 2.1.7 to 2.1.8

2.1.8 is a candidate until publication. RunResult.evidence() becomes the primary export. Existing code remains valid:

```python
before = result.to_dict()
after = result.evidence()
assert before == after
```

Both return the same normalized/redacted dictionary, including children, with the existing trace schema. No deprecation warning or removal is introduced. Context.to_dict(), Lineage.to_dict() and Validation.to_dict() retain their names; they are not RunResult exports.

Agent/System/Environment/Eval construction, framework/provider selection, execution controls and CLI commands remain compatible. No new command, scaffolder, durable memory, distributed session transfer or LM capability is added. Documentation has a new [entry point](README.md); stable old guide URLs remain usable. Historical acceptance is not relabeled as 2.1.8.
