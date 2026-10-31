> Justificación histórica del diseño dev7, conservado en dev8. Consulta la [API vigente](API_214.md) y el [informe actual](../revisions/2.1.4/grammar-dev8/REPORT.md).

> Actualización dev7: Graph es el nombre público único, se retiró check y compile prepara la estructura. Eval aísla Memory por caso. [API vigente](API_214.md).

# Simplificación implementada · 2.1.4.dev7

Estado: implementado en la revisión local dev7. Este documento conserva la
justificación del diseño; la [API vigente](API_214.md) y el [informe offline](../revisions/2.1.4/grammar-dev7/REPORT.md) describen los nuevos bytes.
Build03 es histórico; no se ha ejecutado inferencia ni publicado.

## 1. Retirar Limits y max_actions

Retirar el constructor público, el parámetro limits de run/arun y la cuota
basada en nodos internos. No reubicar max_actions en runtime ni conservar
una cuota oculta equivalente. La instrumentación puede contar nodos para
observabilidad, pero su número no determina la aceptación del negocio.

Conservar las capacidades de control que sí tienen significado estable:

| Necesidad | Superficie propuesta | Alcance |
| --- | --- | --- |
| Tiempo, reintentos y concurrencia del actor | runtime(timeout_s, max_retries, backoff_s, max_concurrency) | Invocación del actor, con sus controles y evidencia reales |
| Turnos, Tools y tokens | runtime(max_turns, max_tool_calls, max_tokens) | Bucle/generación del actor; no presupuesto monetario global |
| Plazo de toda la composición | run(input, timeout_s=...), arun(...) | Ejecución raíz; los hijos heredan el plazo restante |
| Número de records/condición de parada | Environment(max_steps=..., stop=...) | Trabajo episódico de negocio |
| Ciclos del grafo | Decisiones/condiciones del grafo y plazo raíz | Progreso real, no conteo de envoltorios internos |
| USD y solicitudes reales | Contador persistente de campaña | Transporte, fallos, reintentos y trabajadores que terminan tarde |

El plazo raíz es opcional; no hay un contador de acciones implícito. La
misma forma aplica a Agent/System/Environment/Eval y a su ejecutable compilado.
Environment y Eval usan records/cases declarados, sin argumento posicional de
input. Los hijos no reinician el plazo. Reanudar conserva el tiempo activo ya
consumido, sin cobrar el tiempo de espera de la intervención humana.
Un timeout es cooperativo; no promete matar hilos ni deshacer efectos.

Sintaxis implementada en dev7 (build03 conserva su API histórica):

```python
result = system.run(input_data)
bounded = system.run(input_data, timeout_s=60)
```

## 2. Un único runtime público y un único Context

Conservar toolkit.runtime: configura proveedor/modelo/conexión y controles.
Conservar el scheduler interno; no añadir Scheduler, Executor ni Execution
como constructores públicos ni mantener aliases.

Retirar toolkit.Runtime de la API pública propia. LangGraph mantiene su
Runtime original internamente. Context no pretende representar sus clientes,
stores o writers; es el contrato informacional de Agentic Systems.

Tools y nodos reciben el mismo parámetro explícito:

```python
@toolkit.tool
def assess(amount: int, *, context: toolkit.Context) -> dict:
    return {"review": amount > context.data["threshold"]}

def read_policy(state, *, context: toolkit.Context):
    return {"threshold": context.data["threshold"]}
```

Las Tools ya admiten esa firma. Los nodos necesitan adaptar la inyección en
el compilador de toolkit, sin sustituir StateGraph ni inventar un DSL. El
parámetro context es reservado, tipado e inyectado; no es un campo de estado
ni un argumento generado por un modelo. Una firma contextual incorrecta debe
fallar al compilar. No se relaja ni rellena el esquema de entrada de negocio.
Debe funcionar igual en ejecución sync/async, ramas, anidamiento y reanudación.

Una variable execution = toolkit.runtime(...) es una variable local, no un
constructor nuevo. Context permanece separado de configuración del proveedor,
recursos de ejecución, evidencia y Memory.

## 3. Otras superficies que revisar

| Elemento | Propuesta | Razón y capacidad conservada |
| --- | --- | --- |
| Action | Retirar del núcleo público | Repite el nombre del nodo y adapta un input; una función nodo puede llamar a agent.run(payload) y devolver RunResult, conservando evidencia |
| Actor como palabra de aprendizaje | Dejar en documentación interna de adaptadores | El usuario ya construye Agent; no necesita otro supuesto objeto |
| Harness como constructor | No añadir | Es el ejecutable devuelto por compile, además de un término de arquitectura |
| Varias presentaciones humanas | Enseñar human_results como entrada principal | Revisar render/explain duplicados antes de retirar métodos; preservar linaje estructurado y contexto acotado para agentes |
| Command y Send | Conservar como LangGraph avanzado | Tienen funciones distintas; no son necesarios para las decisiones sencillas |
| model_artifact/model_server | Conservar como serving opcional, fuera del recorrido básico | Hoy sirven a vLLM; no son requisitos para crear un Agent con un endpoint disponible |
| framework | Conservar | Aporta selección real de SDK y opciones de handoff/MCP/A2A; native puede seguir siendo el valor por defecto |
| Agent(graph) y System(graph) | Conservar, aclarando intención | Una capacidad compuesta y una aplicación pueden necesitar grafos; no introducir dos motores |
| run y compile | Conservar | Ejecución directa frente a preparación/reutilización/reanudación |
| Context/Memory/lineage | Conservar con fronteras explícitas | Datos de referencia, episodios guardados y evidencia de ejecución son responsabilidades distintas |
| Métodos heredados de Pydantic/SDKs | No enumerarlos como nuevas palabras de toolkit | Seguir disponibles donde corresponda, sin convertirlos en requisitos de aprendizaje |

La propuesta de retirar Action no elimina pasos del grafo ni delegación:

```python
def fee_step(state):
    return fee_agent.run({"amount_cents": state.amount_cents})

graph.add_node("fee", fee_step)
```

El compilador debe conservar el RunResult hijo completo. No convertir un
resultado fallido en un diccionario de éxito ni descartar sus eventos/linaje.

## 4. Contratos para implementar y comprobar

1. No existe Limits público, ni limits=, ni max_actions con otra ubicación.
2. La misma operación de negocio, con más o menos anidamiento, no falla por
   la cantidad de nodos internos.
3. El plazo raíz se comparte, los controles de actor siguen activos y los
   reintentos conservan intentos, errores y consumo. No se confunden turnos/
   tokens con dinero ni se promete preempción.
4. Context directo funciona en Tools y nodos sin Runtime público, con fuentes,
   Memory seleccionada y observaciones de linaje correctas por rama.
5. La proyección explícita de input y los contratos Pydantic siguen rechazando
   valores ausentes/incorrectos. No se añaden defaults para ocultar fallos.
6. run/arun/compile y pausa/reanudación conservan la evidencia y el trabajo
   completado. Eval mantiene la prohibición de pausas en sus casos.
7. Migrar scaffolder, skill, tutorials/examples y firmas activas, preservando
   los artefactos y resultados históricos.
8. Generar un nuevo wheel, instalarlo fuera del checkout y repetir offline.
   La aceptación live previa no se transfiere a nuevos bytes. No publicar.
