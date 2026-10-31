> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Estado de las ideas · 2.1.4.dev2

Implementado en esta iteración: LangGraph como único orquestador, StateGraph
como único constructor de composición, graph= en Agent/System/Environment,
contexto heredado e inmutable, memoria episódica, linaje compacto entre unidades,
almacén de evidencia separado de checkpoints, pausa/reanudación local y ejemplos
de load_skill/model_artifact/model_server. Se actualiza el scaffolder.

Los checkpoints contienen negocio más hasta 32 referencias recientes; Context
aporta hasta ocho resúmenes precedentes. La evidencia completa se conserva aparte,
no se pretende almacenamiento infinito ni revelar razonamiento interno del LM.

Pendientes: checkpoints y memoria persistentes, retención de evidencia externa,
streaming público, políticas de cache/retry/error-handler ligadas a evidencia,
protocolos públicos de ejecutables, expresiones/pseudocódigo, migración del
catálogo histórico y Studio. Los SDK de actores conservan su bucle interno.

La validación real de LM de dev1 queda histórica. Esta candidata requiere nueva
campaña antes de afirmar compatibilidad live. vLLM real, GPU, IAM y ADA siguen
fuera de esta validación offline. No se añade un constructor Harness ni aliases
para gramáticas anteriores. No hay publicación.
