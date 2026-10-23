# Contar texto

Usar un Tool para análisis básico reproducible.

```python
from examples.patterns.text_analysis.example import run

result = run()
result
```

Tres palabras → conteos → dos palabras únicas y dos menciones de evidence.

Código:
- [Current implementation](../../../examples/patterns/text_analysis/example.py)

Validación: **Offline ejecutado**. Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados.

- [Ejecución actual](../../../examples/patterns/text_analysis/evidence/current.json)

<details>
<summary>Evidencia del experimento anterior</summary>

Estado anterior: accepted-2.1.2. Published 2.1.2 core-12-live-v1 acceptance: OpenAI, Bedrock API key and Ollama Ã— native/LangGraph/OpenAI Agents/Strands, two passes. Four-framework Python controls are deterministic. This accepts the declared cases and routes only, not all SDK-specific features or arbitrary models.

La adaptación actual tiene pruebas propias. La evidencia anterior conserva su versión y no certifica estos bytes.

- [Published exact-wheel acceptance summary](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.2/final-certification-summary.json)
- [Published release](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.2)

</details>
