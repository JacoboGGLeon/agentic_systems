# StateGraph, Context y recursos · 2.1.4.dev7

Abre `01_common_graph.ipynb`. Contiene seis patrones de Agent/System, Context,
una Skill cargada desde archivos, Memory, Environment, Eval, pausa/reanudación y
las declaraciones model_artifact/model_server. Todo lo ejecutado es offline.

```python
from examples.common_graph.application import demonstrate

report = demonstrate()
print(report["output"])
```

Input: pedido de 240 MXN con una pieza faltante. Proceso: Agents normalizan y
clasifican, precio y política se calculan en ramas, una decisión requiere
aprobación. Output: reembolso parcial de 120 MXN con linaje.

Toda composición usa Graph de LangGraph. Las Tools y unidades son nodos,
las aristas controlan el orden y las barreras coordinan ramas. No hay selección
de backend ni constructores duplicados de composición.

`resources.py` muestra load_skill y serving sin iniciar procesos. Las pruebas
de start/health/stop son simuladas; no acreditan GPU, pesos ni vLLM real.
La evidencia y cobertura actuales están en revisions/2.1.4. Las pruebas live
de dev1 permanecen archivadas y no se atribuyen a esta candidata.

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). Las revisiones previas se conservan como evidencia histórica.
