# API 2.1.3: experiencia de usuario y validación local

> **Campaña anterior preservada.** La candidata final, el nuevo presupuesto y el inventario exhaustivo están en [el cierre actual](../closeout-evidence/REPORT.md).


La revisión conserva una API: `import agentic_systems as ag` → construir →
`run()` → `RunResult`. Agent y System comparten Sequence, Parallel y Graph;
las decisiones son funciones directas. `compile()` permite preparar la misma
declaración y no ejecuta inferencia.

No se publicó, creó tag, abrió PR ni lanzó CI remoto en este trabajo. Esto es
evidencia local de los escenarios descritos, no aceptación de un release.

## Material para aprender

- [Once tutorials](../../../tutorials/README.md), ejecutados offline: 40 celdas de aprendizaje. La guarda y el bootstrap solo se añaden a las copias ejecutadas del validador.
- [Catálogo de 48 entradas](../../../examples/README.md): las 34 experiencias históricas tienen una adaptación actual ejecutable con `run()`. Sus estados anteriores permanecen separados.
- Las adaptaciones son demostraciones pequeñas de contratos. No reproducen toda la complejidad ni transfieren la certificación semántica de los experimentos anteriores.
- Tres adaptaciones construyen configuración para vLLM/Colab, AWS IAM y ADA IAM: no ejecutan ni autentican esos entornos. Los textos creativos y jueces guardados son fixtures identificados.
- [Seis flujos](../../../examples/grammar_tour/README.md): value=3 produce 8 en secuencia/decisión y 10 en paralelo; value=-3 termina la decisión con -2. Tools → Skill → Agent/System → Environment → Eval.
- [Pedidos](../../../examples/order_fulfillment/README.md): siete Agents, controles paralelos, decisiones, episodios y Eval; 14 contratos en native/LangGraph, incluido fallo técnico con evidencia previa conservada.
- [Referencia completa](../../../docs/API_213_SURFACE.md): 186 entradas/miembros y 139 parámetros de firmas, asociados a familias de tutorial, ejemplo y pruebas. No significa cobertura exhaustiva de cada valor posible.
- [Criterios de experiencia](../../../docs/USER_EXPERIENCE_213.md): referencias oficiales de pandas, scikit-learn, PyTorch, NumPy y Polars; conceptos consistentes, ejemplos pequeños y opciones progresivas.

## Matriz de Tool y contrato: 16/16

Input: entero 37. Proceso: el actor debe invocar `certify`, conservar la llamada
observada y validar serialización e invariantes. Output: evidencia de 37 y verified.
Python usa los SDKs reales con ejecución determinista; no razona con lenguaje.

| Proveedor | native | LangGraph | OpenAI Agents | Strands |
|---|---|---|---|---|
| python-runtime | Pasa | Pasa | Pasa | Pasa |
| ollama-runtime | Pasa | Pasa | Pasa | Pasa |
| bedrock-runtime | Pasa | Pasa | Pasa | Pasa |
| openai-runtime | Pasa | Pasa | Pasa | Pasa |

[Resultados](matrix.json). Se mantuvieron los modelos y endpoints configurados:
OpenAI `gpt-4.1-mini`, Ollama `gemma4:31b-cloud` y Bedrock bearer
`qwen.qwen3-32b-v1:0`, región `us-east-2`. [Identidades sin claves](routes.json).

## Capacidades nativas: 15/15 en la pasada final

| Capacidad | Input → proceso → output | Alcance probado |
|---|---|---|
| LangGraph | solicitud → interrupt/checkpoint → Command resume y aprobación | StateGraph real, InMemorySaver local; extensión dentro de Action |
| OpenAI Agents | consulta de facturación → handoff → SPECIALIST_OK | Cuatro proveedores; callback, evento normalizado, SQLiteSession y control negativo de guardrail |
| Strands MCP | FRAMEWORKS_TOGETHER → cliente MCP y servicio local → eco observado | Cuatro proveedores, Streamable HTTP real |
| Strands A2A | mismo valor → agent card y agente remoto → evidencia recibida | Cuatro proveedores, JSON-RPC local real |
| Interoperabilidad | 42, trail vacío → cuatro actores → 46 y cuatro identidades | Python y mezcla native/Python, LangGraph/OpenAI, OpenAI Agents/Ollama, Strands/Bedrock |

Los servicios remotos de protocolo usan modelos deterministas; los actores
externos de los clientes sí hicieron inferencia. No se probó una red empresarial.
La transferencia de datos entre frameworks toma la salida observada del Tool;
el resultado completo conserva el actor original, sus eventos y su linaje.
La configuración de checkpointer no se anuncia como keyword portable de
`framework('langgraph')`: el ejemplo usa explícitamente el SDK nativo en la aplicación.
[Evidencia final](features.json) y [declaración compartida con Studio](../../../examples/framework_interop/README.md).

## Studio

- Backend: **16/16** combinaciones, tres turnos cada una: introducir LINTERNA, recordar el nombre y verificar 17 × 19 = 323. [Resultados](studio.json).
- Widgets reales con Streamlit AppTest: **12/12** pares externos, consulta aritmética y evidencia de `safe_calculate`. [Resultados](studio-ui.json).
- Offline: **14 tests**, incluidas las cuatro interfaces Python, arranque sin `.env`, tipos, límites de contexto, presupuesto y construcción/inspección de diez catálogos. [JUnit](studio-offline-tests.xml).
- El razonamiento live de los diez catálogos de negocio no se ejecutó; construirlos no acredita sus respuestas.
- Wheel instalado sin editable: **21 archivos** iguales al artefacto; notebook de dos celdas ejecutado offline, servidor HTTP local y pantalla de chat comprobados. [Instalación](studio-install.json).
- Tras las pruebas live se ajustaron el launcher, la inspección de componentes y el texto del mock Python. Se validaron offline; las rutas de inferencia externas y el SDK de campaña permanecieron iguales. El wheel final de Studio no se presenta como artefacto de release certificado.

## Correcciones y fallos conservados

El SDK propagaba data pero perdía text/final al envolver el último hijo; se
corrigió y añadió regresión. El adaptador OpenAI Agents ahora conserva también
eventos nativos de handoff. Ambas correcciones están en el wheel de esta campaña.

Los primeros intentos de protocolo detectaron una dependencia de Windows
(`pywintypes`) y una firma incorrecta del modelo determinista A2A. Se corrigió
la preparación del entorno y el fixture. La composición mixta detectó una
proyección incorrecta de datos y después argumentos que el modelo calculaba
antes de llamar al Tool. Se precisó la instrucción para copiar los argumentos
intactos y se exigió la evidencia observada. No se cambió el modelo para aprobar.

Los fallos e intentos anteriores permanecen en sus archivos; la aceptación
acotada se refiere a la pasada final completa. [Índice de fallos conservados](failure-index.json).
Las pruebas de UI también detectaron selección por posición y una referencia
retirada a `Tool.identity`; ahora usan claves de widget e `inspect()`.

## Presupuesto

Campaña nueva autorizada: **USD 10 y 300 intentos**. Snapshot: **198
intentos y USD 8.189560 reservados**. Restan **102 intentos y
USD 1.810440**. Las reservas usan USD 5/M input y USD 20/M output,
bytes UTF-8 + 4096 como cota de entrada, máximo de salida declarado y 25% de
margen. Son cotas conservadoras, no facturación observada.

Se reserva antes del transporte; fallos, reintentos, evaluadores, Ollama y
respuestas posteriores a timeouts no se descuentan. El hook permanece instalado
hasta terminar cada proceso. Los servicios locales registrados no son llamadas
de inferencia. La campaña anterior permanece separada e inmutable.
[Ledger completo sin claves](budget.json). Intentos por fase: {'matrix': 24, 'features': 78, 'studio': 60, 'studio-ui': 36}.

## Artefactos y verificación

Wheel SDK de campaña: `2ec54f97c9f6d58c15f7bb73370eed066725a97d3d70fa638e3854a359a1a58e`. **116 archivos** instalados y fuente actual
iguales a los del wheel. Se verificaron import base sin SDKs opcionales, CLI y
proyecto generado fuera del repositorio, 33 checksums y 14 contratos. El
proyecto limpio está en [generated-project.zip](generated-project.zip).

Los cambios de documentación posteriores al build se entregan como fuente y
en el manifiesto. El README embebido en metadata del SDK conserva el snapshot
del build de campaña. No se selló un artefacto de publicación con documentación
actualizada; cualquier nuevo wheel requiere su aceptación correspondiente.

Tests SDK: **180 pasan**. Cobertura por sentencias de la **API canónica nueva**:
**100.00%**, 1196 sentencias; excluye el motor privado
histórico. [JUnit](tests.xml), [cobertura](coverage.json), [packaging](packaging.json).
Ruff, tres fronteras de arquitectura y escaneo de secretos pasaron localmente.
Python local: **3.14.2**; 3.10–3.13 y runners GitHub siguen sin
ejecución en esta tarea. El workflow offline incluye los nuevos ejemplos y Studio.

[SDK de campaña](../framework-artifacts/agentic_systems-2.1.3-py3-none-any.whl),
[Studio](../framework-artifacts/studio-user/agentic_systems_studio-2.1.3-py3-none-any.whl),
[bundle local limpio](../framework-artifacts/agentic-systems-studio-2.1.3-local.zip) y [manifiesto](manifest.json).
El bundle no incluye credenciales ni un wheelhouse de dependencias.

Siguen pendientes GPU/vLLM, AWS IAM, ADA IAM, entrega empresarial, extra [ada],
ADA Studio/wallet, serving real y CI multipython. Esta evidencia no certifica
calidad semántica general, cualquier prompt, SDK o versión futura de dependencias.
