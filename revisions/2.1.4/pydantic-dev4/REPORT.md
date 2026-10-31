# Pydantic y human_results · 2.1.4.dev4

Candidata local no publicada. Dos imports básicos: import pydantic e import agentic_systems as toolkit. La evidencia dev3 permanece histórica.

## Cambios

Estados Pydantic para grafos de Agent, System y Environment; modelos anidados, validadores, actualizaciones parciales, entrada/salida distintas, async, reducers, Send, Context y pausa/reanudación. RunResult.human_results() es una vista acotada de la misma evidencia, sin inferencia. Los objetos LangGraph se exponen por toolkit sin cambiar identidad ni motor.

Se eliminaron los tres helpers show. 26 notebooks y las declaraciones canónicas usan Pydantic; los Tools de negocio y sus muestras/aserciones se compararon por AST antes de aplicar lotes revisados. La migración masiva inicial fue rechazada por revisión automática; se usó staging, revisión y lotes pequeños. Los intentos fallidos permanecen en notebook-runs y examples.

Se corrigieron contratos reales: el rechazo de un pedido admite total_cents=null; un subtotal calculado no se exige en la entrada; los jueces tienen su propio estado. Los nulos explícitos se distinguen de campos opcionales que todavía no existen.

## Validación

- 26/26 notebooks offline; celdas live/local omitidas explícitamente y registradas.
- 53/53 entrypoints offline; los protocolos reales locales tienen perfil separado sin LM.
- Regresiones completas: ver offline-junit.xml. Incluyen conservación de validadores, errores antes de efectos, paralelismo, modelos por nodo, async, outputs Pydantic, Context, Memory, Eval, pausa/reanudación y presentación humana.

| Ruta | Modelo | Actor | Último resultado |
|---|---|---|---|
| openai-runtime | gpt-4.1-mini | openai-agents | PASS |
| bedrock-runtime | qwen.qwen3-32b-v1:0 | native | PASS |
| ollama-gpu | qwen3:4b-instruct-2507-q4_K_M | native | PASS |
| ollama-cloud | gemma4:31b | strands | PASS |

Estas son cuatro pruebas de integración Pydantic → Agent LM → System → RunResult/human_results, con input value=2 y output answer=3. No son las 12 combinaciones, ni una repetición avanzada de Tools/handoff/MCP/A2A/Studio en todos los modelos. Python cubrió esas composiciones offline.

El primer intento Ollama GPU fue bloqueado antes de transmitir porque el cliente nativo leyó un perfil de entorno que no coincidía con la ruta congelada. Se alineó en memoria el mismo Qwen/endpoint y se repitió solo esa celda. No se editó .env, no se sustituyó modelo y el fallo permanece en online. Los reintentos internos bloqueados no llegaron al proveedor.

Acumulado del contador: **300/300 solicitudes**, **USD 1.592210** reservados. Se agotaron las solicitudes; no se reinició ni se aplicó la ampliación a 340 que la revisión automática rechazó. Ningún trabajador sigue infiriendo y no se ejecutarán más llamadas con este contador.

Wheel SHA-256: `a06317a8bb14b3cf8ba42684880a3a722e7396603df41962e877e019b888680b`. [Wheel](builds/03/agentic_systems-2.1.4.dev4-py3-none-any.whl) · [sdist](builds/03/agentic_systems-2.1.4.dev4.tar.gz) · [JUnit](offline-junit.xml) · [Resumen y todos los intentos](summary.json).

## Límites y pendientes

vLLM sigue pendiente por decisión del usuario. Ollama cloud no ofrece Qwen: Gemma4 fue autorizado. El fallo previo de Bedrock/Qwen al omitir un null de una Tool permanece sin resolver: el PASS de esta prueba JSON sencilla no lo corrige ni lo sustituye. No hay aceptación global de release estable, CI multiversión de esta revisión ni publicación.

Context/Memory y los checkpoints siguen siendo snapshots locales; no hay persistencia durable. El estado de episodio de Environment y sus callbacks conservan el protocolo JSON documentado; el modelo Pydantic del grafo valida cada observación. Ollama nativo requiere que su perfil de entorno coincida con el runtime declarado.

[API](../../../docs/API_214.md) · [Inventario completo de notebooks](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults y linaje](../../../docs/RUNRESULTS_LINEAGE_214.md) · [Revisión de cambios de enseñanza](staged-semantic-review.json).

La suite final registró **239 pruebas aprobadas**, cero fallos/errores/omitidas. Los 13 avisos son una deprecación de una dependencia; no fallos de contrato.

[Skill portable](deliverables/agentic-systems-skill-2.1.4.dev4.zip) · [Scaffolder y skill](skill-validation.json). La instalación personal de Codex quedó sincronizada; el ZIP no instala automáticamente en la cuenta de ChatGPT.
