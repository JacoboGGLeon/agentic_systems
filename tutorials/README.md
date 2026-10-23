# Tutorials · Agentic Systems 2.1.3

Abre un notebook y ejecuta sus celdas en orden. Cada lección explica
**input → proceso → output** y usa `import agentic_systems as toolkit`.
Instala [el SDK y los extras necesarios](../INSTALL.md) en el kernel de Jupyter.
Los ejemplos de core son autónomos: no necesitan imports ocultos desde el repositorio.

## Core

Sigue 00–03 para empezar. Añade episodios, evaluación y observabilidad según tu tarea.

| Notebook | Lo que construyes |
|---|---|
| [00 · Inicio](core/00_start.ipynb) | Un Agent y su primer RunResult |
| [01 · Tools y Skills](core/01_tools_skills.ipynb) | Operaciones, contratos y carga de una Skill portable |
| [02 · Flujos de Agent](core/02_agent_flows.ipynb) | Secuencia, paralelo y decisiones; native y LangGraph |
| [03 · Flujos de System](core/03_system_flows.ipynb) | Coordinación de agentes con los mismos tres flujos |
| [04 · Environment](core/04_environment.ipynb) | Episodio, observe, update, stop y memoria |
| [05 · Eval](core/05_eval.ipynb) | Expectativas exactas, checks y errores detectados |
| [06 · Resultados y límites](core/06_results_limits.ipynb) | run/arun, compile, límites, JSON, eventos y lineage |
| [07 · Pedidos](core/07_order_challenge.ipynb) | Tools, Skills, varios Agents, System, decisiones, Environment y Eval |

## Providers

| Notebook | Ejecución y preparación |
|---|---|
| [00 · Python](providers/00_python.ipynb) | Tool real sin modelo de lenguaje ni credenciales |
| [01 · OpenAI API key](providers/01_openai.ipynb) | Modelo configurado → invocación real de Tool → evidencia |
| [02 · Ollama](providers/02_ollama.ipynb) | Endpoint y modelo explícitos → Tool → evidencia |
| [03 · Bedrock API key](providers/03_bedrock.ipynb) | Región, modelo y bearer token → Tool → evidencia |
| [04 · vLLM y serving](providers/04_vllm_serving.ipynb) | Artefacto, configuración de servidor y endpoint; sin iniciar GPU |

Los tres notebooks externos ejecutan inferencia al correr sus celdas **live**.
Necesitan las variables del proveedor; no hay fallback. La validación offline
omite esas celdas y reporta que la ruta live sigue sin ejecutarse en ese perfil.
No se presenta inspeccionar configuración como validación de un modelo.

## Frameworks

| Notebook | Capacidad que enseña |
|---|---|
| [01 · LangGraph](frameworks/01_langgraph.ipynb) | Checkpoint, pausa y reanudación con aprobación explícita |
| [02 · OpenAI Agents](frameworks/02_openai_agents.ipynb) | Agent común, handoff a especialista, sesión y guardrail |
| [03 · Strands](frameworks/03_strands.ipynb) | Agent común y Tools MCP / agente A2A sobre servicios locales |
| [04 · Interoperabilidad](frameworks/04_interoperability.ipynb) | Los cuatro frameworks coordinados por un System |

El primer Agent usa Python Runtime sin inferencia. Los laboratorios de handoff,
MCP/A2A e interoperabilidad reutilizan la implementación **instalada de Studio**,
identificada y enlazada en cada lección. Instala [Studio](../examples/agentic_systems_studio/README.md)
para esas secciones. MCP/A2A inicia servicios locales reales: no es una conexión
externa ni una certificación semántica de un modelo. La campaña live prueba
aparte las rutas configuradas de proveedores y frameworks.

## API

| Notebook | Consulta avanzada |
|---|---|
| [01 · Runtime y framework](api/01_runtime_framework.ipynb) | Los cuatro frameworks, opciones, límites del actor y configuración explícita |
| [02 · Contratos y jueces](api/02_contracts_judges.ipynb) | Tool expectations, salida estructurada, juez fixture y checks |

El juez fixture comprueba el protocolo de evaluación; no acredita juicio semántico.
La [referencia de firmas](../docs/API_213_SURFACE.md) complementa las lecciones.

[Examples](../examples/README.md) · [Studio notebook](../examples/agentic_systems_studio/notebooks/01_studio.ipynb) ·
[Inventario de gramática](../docs/NOTEBOOK_INVENTORY_213.md) · [Resultados actuales](../docs/LEARNING_VALIDATION_213.md)
