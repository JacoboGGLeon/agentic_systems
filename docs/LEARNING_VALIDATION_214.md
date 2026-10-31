# Validación vigente · 2.1.4.dev8

[Informe del wheel](../revisions/2.1.4/grammar-dev8/REPORT.md) · [Resumen](../revisions/2.1.4/grammar-dev8/summary.json).

469 regresiones pasaron contra el wheel instalado fuera del checkout, sin fallos
ni omisiones. Los 30 notebooks (22 tutorials y ocho examples) y 58 entrypoints
pasaron sus perfiles offline. Las celdas live/local omitidas aparecen en el
[inventario](NOTEBOOK_INVENTORY_214.md); no acreditan servicios externos.

La cobertura de sentencias del núcleo medido es 100%; el motor privado y las
plantillas quedan fuera por la política existente. No se afirma cobertura de
ramas ni de toda la distribución. Los tres actores ejecutan Python determinista;
las fixtures de SDK no acreditan razonamiento de un modelo.

El scaffolder se prueba fuera del checkout: aplicación, example, tests, tres
actores y notebook con kernel nuevo. Studio conserva 13 regresiones seleccionadas
y una demostración offline; esto no certifica toda su UI con modelos reales.
MCP/A2A conserva evidencia dev7 de su perfil local separado, sin aceptación dev8.

Cero inferencia en este cierre. La aceptación online de dev8 y la CI remota
Python 3.10–3.14 siguen pendientes. AWS/ADA IAM y vLLM GPU requieren sus entornos.
Los resultados históricos no se trasladan al wheel actual. No se publicó ni se
abrió un PR nuevo. [Estado](STATUS_214.md).
