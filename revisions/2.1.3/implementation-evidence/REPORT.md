# Implementación 2.1.3 — resultado offline

> **Ejecución anterior de esta revisión.** Los hashes y resultados de este documento se conservan. La candidata y validación posteriores están en [el informe actual](../framework-evidence/REPORT.md).

**La gramática única está implementada en el SDK raíz y pasa la validación
offline del wheel instalado. No se ejecutó inferencia ni se publicó.**

El [manifiesto](manifest.json) identifica fuentes, entorno, resultados y hashes.
El commit base es `d2ea0d7a0fa1da8f4c38e24bc057c700eb4a31ab`; los cambios están
sin commit. Ese commit solo identifica el punto de partida: los hashes de
fuentes y artefactos identifican esta revisión.

## Artefacto comprobado

- [Wheel 2.1.3](../implementation-artifacts/agentic_systems-2.1.3-py3-none-any.whl).
- SHA-256: `d64aad238e5c8a98f5ad383e6436ac9b79a344cb819f60fc431b64a663bbfbe3`.
- Instalación no editable en un entorno dedicado; 116 archivos instalados
  coinciden byte por byte con el wheel. Las dependencias de prueba se
  reutilizaron desde el entorno local preparado anteriormente.
- Importación base en un proceso nuevo: ningún SDK opcional importado.
- [Proyecto generado limpio](../implementation-artifacts/agentic_systems_project-2.1.3.zip)
  con [sumas](../implementation-artifacts/SHA256SUMS.txt). Su manifiesto dice
  `not-run`: las pruebas se hicieron sobre otra copia fuera del repositorio.

## Cambios efectivos

Una sola importación, `agentic_systems`, y 18 nombres públicos. Se retiraron
los módulos públicos anteriores, factories duplicadas, Route, aliases y
métodos heredados de Pydantic. No se conserva compatibilidad de código con
2.1.2. Los adaptadores reutilizados son implementación privada en `_engine`.

Agent y System comparten Action, Sequence, Parallel y Graph con decisiones
mediante funciones directas. Ambos admiten `run`, `arun`, `inspect` y `compile`;
compilar prepara y valida sin llamar modelos. La ejecución de flujos utiliza
native o StateGraph real de LangGraph, con bifurcaciones, uniones y ciclos.

Se completaron esquemas de Tools, Skills portables con imports relativos,
memoria/observación/actualización/parada de Environment, replay, checks y
métricas de Eval, juez explícito, contratos de actor, salida JSON Schema,
serialización, eventos, linaje e invariantes. Los fallos controlados conservan
la evidencia; una rama fallida no produce una unión exitosa. Las opciones
incompatibles o no reenviadas se rechazan. Serving expone configuración y un
solo ciclo `start/health/stop`, comprobado aquí con proceso y HTTP simulados.

La [referencia de API](../../../docs/API_213.md), el
[inventario de métodos y parámetros](../../../docs/API_213_SURFACE.md) y las
[decisiones aplicadas](../../../docs/API_213_DISPOSITION.md) corresponden a la
implementación raíz. El inventario contiene 186 entradas y 139 parámetros;
los enlaces de cobertura son por familia, no una afirmación sobre todos los
valores posibles ni sobre todas las opciones de los SDK externos.

## Resultados

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Contratos del SDK instalado | 179 pasan; cero errores, fallos u omisiones | [JUnit](tests.xml) |
| Cobertura de sentencias de la API nueva | 1196/1196, 100% | [Cobertura](coverage.json) |
| Curso actual | 11 notebooks, 52 celdas de código pasan en kernels nuevos | [Registro](tutorials.json), [ejecutados](tutorials/) |
| Ejemplos focalizados | 11 pasan | [Resultados](examples.json) |
| Aplicación de pedidos | 7 casos por backend, 14 en total | [Evidencia](../../../examples/order_fulfillment/evidence/run.json) |
| Proyecto generado fuera del repositorio | 12 tests, 14 casos y notebook pasan | [JUnit](scaffold-tests.xml), [casos](scaffold-challenge.json), [notebook](scaffold-notebook.ipynb) |
| Archivos instalados y recursos | 116 archivos coinciden; 33 sumas del proyecto verificadas | [Empaquetado](packaging.json) |
| Arquitectura | 3 contratos conservados | [Registro](architecture.log) |
| Sintaxis e imports propios | 109 archivos compatibles con el parser 3.10; referencias locales resueltas | [Registro](static.json) |
| Lint, secretos y catálogo | pasan en el alcance actual | [Lint](lint.log), [secretos](secrets.log), [catálogo](catalog.log) |

El 100% corresponde a sentencias de la API nueva. Excluye los motores privados
reutilizados y los recursos de plantilla, probados aparte mediante el proyecto
generado. No se afirma cobertura de ramas ni aceptación completa de proveedores.
Python Runtime recorrió native, LangGraph, OpenAI Agents y Strands reales sin
modelos de lenguaje. Las pruebas de fronteras externas usaron stubs explícitos.
El juez de ejemplo verifica el protocolo con fixtures; no certifica semántica
de un modelo.

Cada capítulo y ejemplo enseña input → proceso → output. El challenge integrado
valida pedidos, consulta precio y stock en paralelo, aplica política y decide
aprobar, rechazar o revisar; coordina siete Agents, ocho Tools y siete Skills.
Incluye entradas inválidas, SKU duplicado y fallo de inventario, reteniendo el
resultado de precio ya completado. Environment y Eval usan la misma declaración.

## Alcance y pendientes

Las guardas de aplicación bloquean conexiones, DNS y procesos antes de ejecutar
unidades; hubo cero intentos bloqueados y cero inferencias reales. Jupyter y
asyncio utilizan su transporte local. La guarda de proceso no se presenta como
un aislamiento del sistema operativo. Los contadores sintéticos de fixtures no
son llamadas ni consumo real. No se gastó presupuesto de inferencia.

La ejecución local fue en **Python 3.14.2 / Windows**. La matriz offline de
GitHub Actions quedó configurada para 3.10–3.14, pero no fue despachada ni
acreditada aquí. Parsear con sintaxis 3.10 no demuestra ejecución en 3.10.

Siguen pendientes proveedores reales y jueces semánticos, serving real,
vLLM/Colab, AWS IAM y ADA IAM. No hay extra `[ada]`, ADA Studio ni wallet en esta
entrega. Studio y experimentos históricos mantienen versión y estado propios:
el catálogo separa 13 entradas actuales —curso y doce ejemplos— de 34 históricas.

Los workflows y validadores históricos de publicación/live no se declaran
migrados ni aceptados para 2.1.3. Antes de publicar se necesita su adaptación,
CI satisfactoria y una campaña autorizada vinculada a los bytes que se promuevan.
Los avisos observados fueron deprecaciones de LangSmith, un aviso de runpy en
la prueba de CLI y el transporte TCP local de Jupyter; no hubo tests fallidos.

## Intentos conservados

El primer build se descartó: un `build/lib` previo introdujo módulos públicos
retirados. El constructor actual usa staging nuevo y comprueba el contenido.
El segundo wheel fue intermedio; los cambios posteriores invalidaron su
aceptación. Las primeras mediciones de cobertura importaban el SDK demasiado
pronto; se corrigió el runner y se añadieron casos de frontera, que detectaron
un defecto real en la validación de claves JSON. El tercer build es el wheel
identificado arriba y toda la ejecución de aceptación se repitió sobre él.
Ninguna evidencia histórica de 2.1.2 o de las candidatas anteriores certifica
estos bytes. Cambiar el SDK o sus recursos invalida esta aceptación offline.
