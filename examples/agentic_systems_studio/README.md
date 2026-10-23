# Studio

La misma aplicación se usa desde Python, notebook e interfaz.

```python
from agentic_systems_studio import build_conversational_system

studio = build_conversational_system()
answer = studio.run("Hola")
answer.text
```

El ejemplo inicial es un mock determinista de Python. Para abrir la interfaz:

```python
from agentic_systems_studio import launch_studio

launch_studio()
```

Selecciona proveedor y framework en la interfaz. `.env` contiene modelos,
endpoints y credenciales; no se copian al código ni a los resultados. La
campaña de validación usa su presupuesto persistente autorizado para las
llamadas externas. Python funciona sin una asignación de inferencia.

Desde Python también puedes elegir explícitamente:

```python
from agentic_systems_studio import ConversationConfig, build_conversational_system

config = ConversationConfig(provider="openai-runtime", framework="langgraph")
studio = build_conversational_system(config)
answer = studio.run("Calcula 17 * 19 usando la calculadora.")
answer.text
```

El contexto conserva un historial público acotado. El cálculo se verifica con
una Tool y su evidencia permanece en RunResult. La aplicación valida los
ejemplos de API que genera y conserva los intentos de reparación.

| Framework | Ejemplo disponible en la interfaz |
|---|---|
| native | Tools, contexto y coordinación mediante la API común |
| LangGraph | pausa, checkpoint y reanudación de una aprobación |
| OpenAI Agents | transferencia a especialista, guardrail y sesión |
| Strands | Tool MCP y agente A2A mediante servicios locales reales |
| Todos | una sola declaración con cuatro actores; Python o proveedores mixtos |

Los detalles específicos de SDK están en `src/agentic_systems_studio/lab/`.
No cambian la gramática pública. El catálogo de aplicaciones se construye
también con Agent/System; sus reasoners requieren un proveedor de lenguaje.

Instala este proyecto local junto al SDK 2.1.3 y el extra de interfaz/frameworks
que uses. La versión anterior y su evidencia se preservan en
`../history/2.1.2/studio/`; no se importan como compatibilidad.

La validación declara escenarios concretos, no éxito universal de cualquier
conversación. [Resultados, modelos, presupuesto y límites](../../revisions/2.1.3/framework-evidence/REPORT.md).
