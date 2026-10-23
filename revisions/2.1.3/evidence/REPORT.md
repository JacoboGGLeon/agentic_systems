# Candidata 2.1.3 — evidencia offline

Fecha: 2026-10-22. Estado: candidata local validada en el alcance descrito;
integración en el build raíz, certificación de release y publicación pendientes.

El wheel contiene una API pública de 18 símbolos desde `agentic_systems`.
Los tutoriales y el proyecto generado usan el SDK instalado sin modo editable.
No dependen del prototipo histórico `unified_grammar` ni de 2.1.2 instalado.
Los motores internos reutilizados están contenidos dentro del mismo wheel.

## Resultados medidos

| Comprobación | Resultado |
|---|---|
| Contratos del SDK instalado | 24 pruebas aprobadas |
| Curso completo | 10 notebooks, 39 celdas de código aprobadas con kernel nuevo por notebook |
| Agent/System en secuencia, paralelo y decisiones | Ambos backends: native y LangGraph; ejecución directa y compilada |
| Frameworks con Python Runtime | native, LangGraph, OpenAI Agents y Strands |
| Challenge de pedidos | 14 contratos: siete por backend |
| Proyecto generado fuera del repositorio | 14 contratos, 12 pruebas y notebook de una celda aprobados |
| Inferencia | 0 solicitudes |
| Proveedores externos / serving | Solo configuración; sin ejecutar ni certificar |

Los rechazos de negocio son resultados correctos. El caso de fallo técnico de
inventario exige `ok=False`, conserva el precio ya calculado e impide ejecutar
la decisión final. Eval incluye seis casos de negocio y un control negativo
por backend que debe fallar. Ningún fallo se reclasifica como aceptación live.

## Artefacto y trazabilidad

- [Manifest con hashes, dependencias y verificación de bytes instalados](manifest.json).
- [Wheel candidato](../artifacts/agentic_systems-2.1.3-py3-none-any.whl).
- [Proyecto generado limpio](../artifacts/order_fulfillment_213.zip): su manifest
  dice `not-run`; la ejecución de una copia independiente se conserva abajo.
- [Pruebas SDK](tests.xml), [índice de notebooks ejecutados](tutorials.json).
- [Challenge generado](generated-project/challenge.json),
  [pruebas del proyecto](generated-project/tests.xml) y
  [notebook ejecutado](generated-project/01_order_challenge.ipynb).
- [Curso fuente](../../../tutorials/README.md),
  [catálogo de ejemplos y sus estados](../../../examples/README.md).

El colector compara cada archivo de paquete del wheel con los bytes instalados,
verifica los hashes de los notebooks y rechaza las entradas públicas retiradas
del artefacto. El manifest conserva los hashes de fuentes del build. Las
fuentes están en un árbol de trabajo con cambios, no en un nuevo tag publicado.

## Incidencias y límites

La ejecución inicial del notebook generado falló porque su ejecutor esperaba
`01_order_fulfillment.ipynb` y el generador producía `01_order_challenge.ipynb`.
Se corrigió el ejecutor, se añadió una regresión que comprueba la existencia de
la ruta declarada, se reconstruyó el wheel y se repitió la validación completa
contra sus nuevos bytes. Los resultados anteriores no acreditan este artefacto.

Pytest registra 13 avisos de deprecación de `asyncio.iscoroutinefunction` desde
LangSmith en cada suite. Jupyter registra su aviso de transporte TCP local.
Los guards de aplicación permanecieron activos; el transporte local de
Jupyter/asyncio necesita permiso del entorno Windows y no es inferencia.

Esta evidencia corresponde a Python 3.14 en este entorno. No acredita la matriz
Python 3.10–3.14, providers live, vLLM/Colab, AWS IAM, ADA IAM, Studio, TestPyPI,
PyPI, CI de release ni migración de todos los ejemplos históricos. El árbol
`src/` raíz conserva el baseline 2.1.2; la candidata se construye desde
`revisions/2.1.3/`. Esa promoción pendiente debe resolverse antes de publicar.
