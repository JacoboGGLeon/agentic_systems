# Detectar señales en un prompt

Marcar instrucciones sospechosas mediante reglas visibles.

```python
from examples.applications.prompt_security.example import run

result = run()
result
```

Texto → coincidencias léxicas → flags y revisión requerida. No constituye una defensa completa.

Código:
- [Current implementation](../../../examples/applications/prompt_security/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/prompt_security/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/applications/prompt_security/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: historical-pass. Historical Ollama record dated 2026-08-20: qwen3:4b-instruct, framework identity recorded as agentic-systems (native path). This entry passed its recorded stage/engine/invariant checks in the 10/10 batch. No wheel hash establishes acceptance of the published 2.1.2 artifact; this is not an independent semantic certification.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Original historical 10-system record](../../../examples/agentic_systems_studio/evidence/ollama-native.json)

</details>
