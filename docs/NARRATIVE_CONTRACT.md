# Teaching narrative · Agentic Systems 2.1.9

Explain what the library does and when it is useful before introducing the complete vocabulary. Teach through progressive blocks: one capability, model-selected actions, System composition, context and episodes, then inspection and evaluation. Each block must explain the meaning of its output and how the code and diagram produce it.

Use `User input` and `Agentic Systems output` for the teaching interaction. Local actuators receive structured data; explanatory answer text is formatted from their returned values, not fabricated model dialogue. Label unexecuted model responses as expected. Keep code declarations visible and explain why each new object is needed. Prefer a complete small example to unexplained fragments or a long catalog.

Use **model-backed agent actors** and **graph-based agent actuators** consistently. Runtime selects provider/model and execution limits; Framework selects actor execution. Context supplies immutable references; Memory retains bounded process-local history. State carries current work; lineage records observed execution. Environment and Eval are independent additions.

The first lesson needs no explicit Agent contracts or policies. Their existing reference remains available as advanced material; expanded acceptance is planned for 2.1.10. Do not describe contracts as removed from the API.

Active material targets 2.1.9. Historical outputs, hashes, acceptance reports and published release notes retain their recorded versions. A target-version edit is not a new passing execution. Keep published, configured, locally tested, simulated and live-tested claims separate. Write active teaching material in English.
