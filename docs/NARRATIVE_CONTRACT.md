# Narrativa de producto · 2.1.4.dev8

Agentic Systems coordina código y agentes de distintos SDK, con contratos y
evidencia de ejecución compartidos. LangGraph es el único orquestador.

Tools ejecutan operaciones; Skills declaran capacidades e instrucciones;
Agent organiza operaciones o utiliza un actor; System coordina unidades;
Environment procesa episodios; Eval comprueba resultados explícitamente.
Context conserva referencia de dominio, State canales de trabajo, Memory
episodios locales y linaje evidencia observada. Son responsabilidades distintas.

Runtime y scheduler son pilares: conexión, ejecución y controles del actor.
Framework selecciona native, OpenAI Agents o Strands. El plazo raíz se comparte
entre unidades; la cantidad de nodos internos no impone una cuota.
Pydantic valida estados y contratos de ejecución. No se añaden Harness,
Scheduler, Policy ni otra forma de grafo como constructores públicos.

Un System puede definir la coordinación de un harness. El harness completo
incluye capacidades, contexto y controles; la palabra no acredita aislamiento,
persistencia o recuperación tras reinicio.

La enseñanza muestra declaraciones relevantes, funciones locales visibles,
input → proceso → output y aserciones. Importar otro experimento completo no
sustituye enseñar su construcción. CLI e inspección de paquetes se explican
como ejemplos de sus propias interfaces públicas.

Las afirmaciones separan configuración, ejecución offline, protocolos locales
y proveedor real. Un PASS debe identificar caso, revisión y artefacto. Un
resultado válido no certifica todos los parámetros ni toda la matriz de SDK.
Memory y continuaciones son locales; Environment no es una API RL completa.

[Estado](STATUS_214.md) · [API](API_214.md) · [Ruta de aprendizaje](LEARNING_PATH_214.md) ·
[Runtime/scheduler](RUNTIME_SCHEDULER_214.md) · [System/harness](SYSTEM_HARNESS_214.md).
