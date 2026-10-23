# Comprobar un juez optimista

Combinar expectativas exactas y un juez fixture.

```python
from examples.patterns.judge_calibration.example import run

result = run()
result
```

Respuestas VALID y WRONG → juez que siempre aprueba + expectativas → [True, False]; no es calibración empírica de un modelo.

Código:
- [Current implementation](../../../examples/patterns/judge_calibration/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Ejecución actual](../../../examples/patterns/judge_calibration/evidence/current.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: mixed. Calibration includes false approvals, schema/citation failures and source-only observations. A local holdout report recorded ok=true, but that does not certify a full candidate matrix or a new wheel. Prior failures remain part of the record.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Judge contract](../../../docs/judge-contract-v6.md)
- [Fixed pilot results](../../../docs/judge-v6-pilot-results.md)
- [Two-phase experiments](../../../docs/two-phase-212-status.md)

</details>
