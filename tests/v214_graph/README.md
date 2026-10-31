# Contratos actuales · 2.1.4.dev3

84 regresiones offline sobre LangGraph como único orquestador. Incluyen
concurrencia/barreras/reducers, ciclos, Context en Tools y Runtime, memoria,
lineage de predecesores, evidencia fuera de checkpoints, pausa/reanudación,
episodios, Eval, fixtures de proveedor, Skill loader, ciclo simulado de serving
y scaffolder generado. Las suites v213 y v214 anteriores son históricas.

La puerta final instala un wheel no editable. El runner mantiene un guard de
aplicación contra conexiones e inferencia. Los notebooks se ejecutan en kernels
Jupyter nuevos, cada uno con su guard, como una puerta separada.
