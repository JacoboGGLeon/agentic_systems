# System y harness

En el uso actual, harness describe el software y configuración que rodean al
modelo para convertirlo en un agente operativo: herramientas, contexto,
ejecución, estado y controles. LangChain lo define con ese alcance amplio en
[The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness).
Anthropic ilustra además la necesidad de artefactos de progreso y verificación
entre sesiones en
[Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents).
Es vocabulario de arquitectura, no una interfaz única estandarizada.

En Agentic Systems, **un System puede definir la coordinación de un harness**.
La correspondencia completa se reparte entre los elementos existentes:

| Elemento | Responsabilidad dentro del harness |
| --- | --- |
| Tools y Skills | Operaciones disponibles e instrucciones de capacidad. |
| Agent | Unidad operativa o actor con su bucle de SDK. |
| System y StateGraph | Composición, dependencias, decisiones y coordinación. |
| runtime y scheduler | Ejecución, conexión y controles del actor. |
| Context y Memory | Referencia de dominio y episodios seleccionados. |
| Environment | Evolución episódica cuando el trabajo necesita múltiples observaciones. |
| Plazo raíz, contract y policy | Límites y requisitos declarados. |
| RunResult y Eval | Evidencia de ejecución y comprobación de resultados. |

Esta correspondencia es nuestra interpretación de la API; no implica que
System incluya por sí solo toda infraestructura posible. Persistencia durable,
aislamiento de sistema operativo, permisos empresariales y recuperación tras
reinicio no aparecen automáticamente por construir un System.

No añadimos `Harness`, no renombramos System y no exigimos un Environment para
un trabajo de una sola ejecución. El harness puede ejecutar operaciones Python
deterministas o contener actores LM. Un flujo determinista no vuelve
determinista la respuesta de un modelo.

[Construcción visible](../examples/api_walkthrough/01_api_user_guide.ipynb) ·
[Runtime y scheduler](RUNTIME_SCHEDULER_214.md) · [Estado](STATUS_214.md).

En el [ejemplo financiero](../examples/applications/financial_harness/example.py)
usamos financial_system para la declaración y financial_harness para el
ejecutable devuelto por financial_system.compile(). Es una convención local
para distinguir definición y preparación, no un nuevo tipo público ni una
definición universal de harness.
