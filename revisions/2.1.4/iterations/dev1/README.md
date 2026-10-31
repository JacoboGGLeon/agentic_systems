# Desarrollo acumulativo 2.1.4

Candidata local actual: **2.1.4.dev1**, sin publicar.

- [Reporte de ejecución y beneficio](REPORT.md): input → proceso → output, matriz y límites reales.
- [Cierre medido](closeout.json): 278 regresiones offline; 6 rutas Python y 6 rutas OpenAI real satisfactorias.
- [Contratos](../../docs/CONTRACTS_214.md) y [gramática](../../docs/GRAMMAR_214.md).
- [Notebook de grafo común](../../examples/common_graph/01_common_graph.ipynb): seis patrones, caso integrado y pausa.
- [Notebook de Context/Memory](../../examples/context_memory_lineage/01_context_memory_lineage.ipynb).
- [Cobertura de palabras](../../docs/GRAMMAR_COVERAGE_214.md): 17/20, con definición explícita del denominador.
- [Ideas y pendientes](../../docs/IDEAS_214.md).

`validation.json` es la evidencia exclusivamente offline. `live-results.json`
conserva el piloto fallido, el piloto corregido y las seis aceptaciones sobre
el wheel corregido; `live-budget.json` conserva las 8 solicitudes y la reserva
conservadora USD 0.031772 del tope USD 1/20 solicitudes. `example-results.json`
contiene RunResults, memoria y vistas de linaje offline.

Los archivos de `iterations/dev0/` preservan la primera iteración. Los de
`iterations/dev1-pilot1/` preservan el fallo inicial y el wheel anterior, cuya
aceptación no se atribuye a la candidata corregida. El wheel final local está
en `candidate/`; su SHA-256 se registra en closeout.json. No hay tag ni release.

Pendientes: persistencia de memoria y checkpoints tras reinicio, reset/step,
delegación como capacidad, retirada del despacho histórico de varias Tools de
Python, protocolos públicos de ejecutables, expresiones/pseudocódigo, Studio,
capacidades remotas avanzadas y migración integral del catálogo histórico.
La validación de 2.1.3 permanece histórica y no acredita automáticamente 2.1.4.
