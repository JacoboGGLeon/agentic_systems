# Context, Memory y linaje · 2.1.4

[Notebook con declaraciones visibles](01_context_memory_lineage.ipynb) ·
[Código](application.py). Las capturas de Context se guardan fuera del estado
de negocio. Este ejemplo muestra entrega del contexto; para decisiones basadas
en la evidencia y la memoria, continúa con
[lineage, Memory, Environment y Eval](../lineage_memory/01_lineage_memory_decisions.ipynb).

Solo LangGraph: state/nodes/edges, Tools tipadas y System. Context conserva
política y fuentes fuera del estado de trabajo; Memory aporta episodios al
entrar; lineage conserva evidencia para humanos y agentes. El notebook muestra
input → proceso → output y se ejecuta offline. La guía de toda la gramática
actual está en el notebook examples/common_graph/01_common_graph.ipynb.

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). Las revisiones previas se conservan como evidencia histórica.
