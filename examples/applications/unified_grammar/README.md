# Agent y System: seis flujos

Aprender secuencia, paralelo y decisiones con la misma interfaz.

```python
from examples.applications.unified_grammar.example import run

result = run()
result
```

value=3 → seis declaraciones en native y LangGraph, Environment y Eval → resultados y linaje verificables.

Código:
- [Current implementation](../../../examples/applications/unified_grammar/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/unified_grammar/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/unified_grammar/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: offline-only. Exact 2.1.2 installed wheel bytes verified. All 12 owner/flow/backend cells passed direct and compiled execution, plus 4 alternative decision cases. 79 offline tests passed, including direct-function/legacy-Route compatibility, invalid destinations, threshold behavior, negative controls and async. A fresh-kernel notebook passed all 20 code cells showing six explicit examples and their Skill/Environment/Eval connections. The added matrix passed 24 Environment steps, 24 Eval cases and two expected negative controls. The target-2.1.3 order challenge passed 14 contracts; its generated project ran outside the repository with 12 passing tests and a fresh-kernel notebook. The restricted Windows local-transport attempt and earlier socketpair guard failure remain documented separately. This is prototype acceptance, not release/model certification.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Measured report](../../../examples/history/prototype-213/evidence/REPORT.md)
- [Raw exact-wheel run](../../../examples/history/prototype-213/evidence/offline-run.json)
- [Final tests](../../../examples/history/prototype-213/evidence/tests.xml)

</details>
