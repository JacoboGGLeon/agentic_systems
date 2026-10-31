# Context, Memory y linaje · 2.1.4.dev7

```python
from examples.context_memory_lineage import demonstrate

report = demonstrate()
print(report["outputs"])
print(report["human_lineage"])
```

Solo LangGraph: state/nodes/edges, Tools tipadas y System. Context conserva
política y fuentes fuera del estado de trabajo; Memory aporta episodios al
entrar; lineage conserva evidencia para humanos y agentes. El notebook muestra
input → proceso → output y se ejecuta offline. La guía de toda la gramática
actual está en el notebook examples/common_graph/01_common_graph.ipynb.

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). La evidencia dev3 enlazada corresponde a la revisión anterior.
