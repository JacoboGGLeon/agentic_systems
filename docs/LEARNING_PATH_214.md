# Ruta de aprendizaje · 2.1.4.dev8

Empieza por un recorrido pequeño. Cada notebook muestra sus datos,
declaraciones, ejecución y aserciones; las funciones locales se pueden leer.
No necesitas estudiar toda la referencia antes de ejecutar el primer caso.

| Paso | Lección | Pregunta que resuelve |
| --- | --- | --- |
| 1 | [Inicio](../tutorials/core/00_start.ipynb) | ¿Cómo ejecuto una operación y leo el resultado? |
| 2 | [Tools/Skills](../tutorials/core/01_tools_skills.ipynb) | ¿Qué capacidades expongo y cómo las reutilizo? |
| 3 | [Agent](../tutorials/core/02_agent_flows.ipynb) | ¿Cómo organizo operaciones y decisiones? |
| 4 | [System](../tutorials/core/03_system_flows.ipynb) | ¿Cómo coordino unidades con el mismo grafo? |
| 5 | [Environment](../tutorials/core/04_environment.ipynb) | ¿Cómo proceso observaciones conservando estado de episodio? |
| 6 | [Eval](../tutorials/core/05_eval.ipynb) | ¿Cómo demuestro un resultado y detecto uno incorrecto? |
| 7 | [Context/Memory](../tutorials/core/08_context_memory.ipynb) | ¿Qué información heredo y qué episodios consulto? |
| 8 | [Controles](../tutorials/api/03_execution_controls.ipynb) | ¿Qué gobiernan runtime, scheduler, policy, contract y plazo raíz? |
| 9 | [Pedidos](../tutorials/core/07_order_challenge.ipynb) | ¿Cómo se ven siete Agents con casos de negocio y fallos? |

Después elige una ruta de providers y su framework de actor. LangGraph ya
orquesta: no es otra casilla de framework que debas seleccionar. Los ejemplos
avanzados de SDK muestran handoff, sesión, guardrail y MCP/A2A en su frontera
propia. La prueba Python de un SDK no acredita razonamiento de un LM.

En la primera lectura usa `status`, `ok`, `data` y `human_results()`.
Para depurar consulta errores, invariantes y linaje. Para auditar conserva
la evidencia completa. Una pausa no es un resultado final aunque ok sea true.

[Todos los notebooks y vocabulario](NOTEBOOK_INVENTORY_214.md) ·
[Estado y evidencia](STATUS_214.md).
