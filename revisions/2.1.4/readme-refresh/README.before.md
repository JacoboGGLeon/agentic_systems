# Agentic Systems

<p align="center"><img src="docs/assets/logo_agentic_systems.png" alt="Agentic Systems" width="320"></p>

Construye operaciones Python y agentes de distintos SDK con una sola gramática:
**Pydantic declara los datos; Agentic Systems compone, ejecuta y explica**.
LangGraph es el único motor de orquestación.

Esta rama desarrolla **2.1.4.dev8**, sin publicar. El wheel y la evidencia de
revisiones anteriores conservan su identidad; no certifican automáticamente
los nuevos bytes. [Estado de la revisión](docs/STATUS_214.md).

```python
import pydantic
import agentic_systems as toolkit

class State(pydantic.BaseModel):
    amount: int = pydantic.Field(ge=0)
    decision: str | None = None

@toolkit.tool
def assess(amount: int, *, context: toolkit.Context) -> dict:
    return {"decision": "review" if amount > context.data["threshold"] else "approve"}

graph = toolkit.Graph(State)
graph.add_node("assess", assess)
graph.add_edge(toolkit.START, "assess")
graph.add_edge("assess", toolkit.END)

agent = toolkit.Agent("order_review", graph=graph,
    context=toolkit.Context({"threshold": 100}, sources=("sales-policy-v1",)))
harness = agent.compile()
result = harness.run(State(amount=125))
assert result.status == "completed" and result.ok and result.data["decision"] == "review"
print(result.human_results())
```

`toolkit.Graph`, START, END, Command y Send son los objetos
originales de LangGraph, expuestos desde toolkit. No hay otro constructor de
grafos ni otro motor. Pydantic se importa directamente; no creamos un modelo
base propio. Los reducers avanzados usan Annotated de Python cuando se necesita.

Agent organiza una capacidad mediante su grafo; System coordina agentes mediante
el grafo de la aplicación; Environment
procesa records con estado por episodio. Todos componen grafos y producen
RunResult. `run` ejecuta; `compile` prepara; `arun` ejecuta de forma asíncrona.
Las decisiones son funciones Python y el paralelo usa ramas y barreras del grafo.

**runtime y scheduler siguen siendo pilares.** runtime define proveedor,
conexión y controles de ejecución del actor; el scheduler aplica tiempos,
reintentos y capacidad del executor. `run(..., timeout_s=60)` aplica un plazo raíz compartido. El número de nodos
solo se observa; no constituye una cuota de ejecución.
[Alcance y precedencia](docs/RUNTIME_SCHEDULER_214.md). Un System define la
coordinación de un [harness](docs/SYSTEM_HARNESS_214.md), junto con capacidades,
contexto y controles; no necesita otro constructor.

Los nodos reciben modelos Pydantic y devuelven actualizaciones parciales.
Se conservan validadores y restricciones, incluidos modelos específicos de
entrada/salida. Los estados intermedios que aún no existen se declaran
opcionales; no se inventan datos para satisfacer una validación.

## Datos, capacidades y evidencia

- Tools realizan operaciones. Skills agrupan Tools e instrucciones de uso.
- `compile()` prepara y comprueba la estructura sin ejecutar el negocio.
- Context contiene datos de dominio y fuentes; admite un modelo Pydantic.
- Memory conserva episodios locales acotados. No es una base vectorial durable.
- State conserva los canales de cálculo; el linaje completo permanece separado.
- Eval comprueba resultados y contratos de manera explícita.
- `human_results()` presenta entrada, pasos observados, salida y errores de un
  RunResult, con límites de tamaño. No ejecuta inferencia ni crea otro contrato.

`result.lineage().to_prompt_context()` entrega evidencia resumida a otro agente.
`result.trace("full")` conserva el detalle para inspección. La presentación
humana no sustituye comprobaciones de ok, status, invariantes y datos de negocio.

## Aprende y ejecuta

- [Instalación local del wheel y Studio](INSTALL.md).
- [Tutorials: core, providers, frameworks y API](tutorials/README.md).
- [Guía de toda la API](examples/api_walkthrough/01_api_user_guide.ipynb).
- [Examples y estado real](examples/README.md).
- [Graph, Tools Pydantic y Eval aislada: ejemplo completo](examples/checked_composition/01_checked_composition.ipynb).
- [Contratos y firmas](docs/API_214_SURFACE.md).
- [Validación de esta revisión](revisions/2.1.4/grammar-dev8/REPORT.md).

## Sesiones AWS y ADA opcional

`runtime(provider="bedrock-runtime", model=..., session=supplied_session)`
reutiliza una sesión preparada por tu plataforma. Selecciona IAM explícitamente;
los conflictos con api_key, endpoint o región se rechazan. La sesión no entra
en Context, Memory, estado ni evidencia y no se cierra al terminar. El toolkit
serializa las invocaciones que la comparten; la coordinación con usos externos
es responsabilidad de su propietario y no se admite trasladarla a otro proceso.

[Ejemplo de configuración](examples/aws_session/01_aws_session.ipynb) ·
[Complemento ADA independiente](integrations/ada/README.md). El complemento es
opcional y no se incluye en all. Su diagnóstico no resuelve credenciales ni
consulta servicios; la prueba offline no certifica AWS IAM o ADA reales.

native, OpenAI Agents y Strands implementan actores dentro del grafo. Python,
OpenAI, Bedrock, Ollama y vLLM son runtimes; soporte de configuración, prueba
local y prueba con un proveedor real se informan por separado. vLLM continúa
pendiente y el caso de Bedrock/Qwen que omite un null mantiene su fallo previo
visible. La [corrección de transporte](revisions/2.1.4/contracts-dev5/bedrock-null-fix/REPORT.md)
está probada offline y pendiente de piloto real. La validación de otro build
no se atribuye al nuevo wheel.

El CLI `agentic-systems new mi_proyecto` genera una aplicación con esta misma
gramática. [Studio](examples/agentic_systems_studio/README.md) y la
[skill](skills/agentic-systems/SKILL.md) son entregables separados del SDK.
Las continuaciones y Memory siguen siendo locales al proceso; no se promete
recuperación durable después de reiniciar ni cobertura universal de los SDK.
