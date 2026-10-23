# Toda la API: de Tool a Eval

Recorrer la gramática completa y una aprobación de pedidos con resultados observables.

```python
from examples.api_walkthrough.example import run

result = run()
result
```

Tools y Skills → seis flujos Agent/System → dos pedidos, decisiones, memoria y Eval → resultados y linaje.

Código:
- [Notebook autónomo](../../../examples/api_walkthrough/01_api_user_guide.ipynb)
- [Declaración compartida](../../../examples/api_walkthrough/example.py)

Validación: **Live: escenario probado**. Notebook ejecutado offline. La declaración integrada se probó en 16 combinaciones; quote es determinista y los actores approve/review usan el runtime explícito. Conserva fallos previos y evidencia de Tools.

- [Nueva ejecución contra el wheel publicado](../../../revisions/2.1.3/learning-evidence-elevated/example-results/api_walkthrough/run.json)
- [RunResult y lineage](../../../revisions/2.1.3/learning-evidence-elevated/example-results/api_walkthrough/runresults.json)
