# Composición · 2.1.4.dev8

Agent y System usan Graph de LangGraph. Los nodos devuelven actualizaciones
parciales; un hijo publica los campos que escribió. Las ramas paralelas necesitan
canales disjuntos o reducers explícitos; la barrera espera sus dependencias.
Las decisiones son funciones Python que devuelven destinos declarados.

run y compile().run ejecutan la misma definición; compile no infiere.
Environment añade evolución episódica con el mismo grafo por observación.
Context se hereda sin contradicciones silenciosas; los hijos heredan el plazo raíz
sin reiniciarlo. Memory, estado de trabajo y linaje no se intercambian.

Los resultados de LM pueden variar aunque el control sea determinista. Pausa
reanuda el mismo programa local; el callback interrumpido puede reiniciarse.
No hay garantía implícita de efectos exactly-once.

[Seis flujos](../examples/common_graph/01_common_graph.ipynb) ·
[Contratos](CONTRACTS_214.md) · [Runtime y scheduler](RUNTIME_SCHEDULER_214.md).
