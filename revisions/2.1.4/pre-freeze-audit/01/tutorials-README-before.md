# Tutorials · Agentic Systems 2.1.4.dev7

Empieza por core/00 y ejecuta las celdas en orden. Cada lección explica
input → proceso → output y contiene aserciones. Usamos `import agentic_systems
as toolkit` y Graph de LangGraph; no hay backend alternativo.

Instala el wheel local y los extras en [INSTALL](../INSTALL.md). Core funciona
sin Studio salvo los recursos del repositorio enlazados. Las secciones avanzadas
que usan Studio lo indican expresamente. El wheel no instala estos notebooks.

La ruta inicial es **00 Inicio → 01 Tools/Skills → 02 Agent → 03 System →
04 Environment → 05 Eval**. Context y Memory se incorporan cuando el caso
necesita referencia de dominio e historia. Después estudia controles y SDKs.
Las declaraciones son visibles: no se importa un experimento completo para
ocultar su construcción. Las funciones locales tienen su cuerpo en la lección.

## Core

| Lección | Qué aprendes |
| --- | --- |
| [00 Inicio](core/00_start.ipynb) | Tool, Agent y RunResult |
| [01 Tools/Skills](core/01_tools_skills.ipynb) | Capacidades y load_skill |
| [02 Agent](core/02_agent_flows.ipynb) | Secuencia, ramas y decisiones |
| [03 System](core/03_system_flows.ipynb) | Coordinar Agents con la misma gramática |
| [04 Environment](core/04_environment.ipynb) | state, observe, update, stop y Memory |
| [05 Eval](core/05_eval.ipynb) | Expectativas y control negativo |
| [06 Resultados](core/06_results.ipynb) | compile/run/arun, plazo raíz, JSON y linaje |
| [07 Pedidos](core/07_order_challenge.ipynb) | Siete Agents y siete casos de negocio |
| [08 Context/Memory](core/08_context_memory.ipynb) | Semántica, episodios y evidencia |

## Providers

| Lección | Alcance |
| --- | --- |
| [00 Python](providers/00_python.ipynb) | Operador real, sin LM |
| [01 OpenAI API key](providers/01_openai.ipynb) | Tool y evidencia live |
| [02 Ollama Cloud](providers/02_ollama.ipynb) | API key; Gemma4:31b autorizado porque Qwen cloud no estaba disponible |
| [03 Bedrock API key](providers/03_bedrock.ipynb) | Qwen, región y bearer token; no acredita IAM |
| [04 vLLM](providers/04_vllm_serving.ipynb) | Declaración offline; GPU/endpoint pendientes |
| [05 Ollama GPU](providers/05_ollama_gpu.ipynb) | Qwen local y evidencia de asignación GPU |

Las celdas live consumen inferencia. La prueba offline las omite explícitamente;
no acredita su generación. No hay sustitución automática de proveedor/modelo.

## Orquestación y frameworks

| Lección | Capacidad |
| --- | --- |
| [01 LangGraph](frameworks/01_langgraph.ipynb) | Único orquestador, pausa/reanudación |
| [02 OpenAI Agents](frameworks/02_openai_agents.ipynb) | Actor Python; handoff/sesión/guardrail live |
| [03 AWS Strands](frameworks/03_strands.ipynb) | Actor; MCP/A2A en perfil de servicios locales |
| [04 Interoperabilidad](frameworks/04_interoperability.ipynb) | Tres actores en un System |

native es el actor propio del toolkit, no un alias de LangGraph. AWS Strands
se selecciona con `framework('strands')`. Los modelos fixture de protocolos
no acreditan razonamiento de un LM.

## API

[01 Runtime/framework](api/01_runtime_framework.ipynb) separa los ejes.
[02 Contratos/jueces](api/02_contracts_judges.ipynb) añade negativos y un juez fixture.
[03 Runtime/scheduler y plazo raíz](api/03_execution_controls.ipynb) conserva los
pilares de ejecución y explica qué control pertenece a cada nivel.

[Inventario por notebook](../docs/NOTEBOOK_INVENTORY_214.md) ·
[Validación y pendientes](../docs/LEARNING_VALIDATION_214.md) ·
[Examples](../examples/README.md) · [Firmas completas](../docs/API_214_SURFACE.md)

[Estado por revisión](../docs/STATUS_214.md) ·
[Validación dev6](../revisions/2.1.4/grammar-dev7/REPORT.md).
La configuración del proveedor no acredita una prueba real. Las celdas live
omitidas offline y las pruebas de protocolos locales se registran por separado.

[Composición con Graph y compile](../examples/checked_composition/01_checked_composition.ipynb): Tools Pydantic, tres niveles de Graph y Memory aislada en Eval.
