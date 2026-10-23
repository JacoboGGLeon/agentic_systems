# Comparar run y compile

Comprobar que preparar una unidad conserva su ejecución.

```python
from examples.validation.api_contract_lab.example import run

result = run()
result
```

value=3 → run directo y compile().run → mismo resultado; firmas públicas disponibles.

Código:
- [Current implementation](../../../examples/validation/api_contract_lab/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/validation/api_contract_lab/current.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/validation/api_contract_lab/runresults.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Exact published 2.1.2 wheel: 1435 offline tests, 223/223 concrete public callable entries observed and 16 Tool route cases passed. Twelve generation transports succeeded, but only eight literal READY checks passed; all four Bedrock results returned READY. The summary is not the full raw audit or a new release certification.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Preserved local audit summary](../../../examples/evidence/api-audit-2.1.2-summary.json)

</details>
