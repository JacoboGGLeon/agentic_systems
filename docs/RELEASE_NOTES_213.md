> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Agentic Systems 2.1.3

**Publicada:** [PyPI](https://pypi.org/project/agentic-systems/2.1.3/) · [GitHub](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.3).

Los números siguientes describen el sello original. El material actual tiene
19 tutorials y dos notebooks de examples, con [validación adicional](LEARNING_VALIDATION_213.md).
Los artefactos originales conservan sus bytes y sus notas aprobadas.

Una sola API para construir, ejecutar y comprobar sistemas. Es una revisión
incompatible de la gramática: los constructores anteriores no se conservan
como aliases. La versión 2.1.2 sigue disponible para aplicaciones anteriores.

- Agent y System usan Sequence, Parallel y Graph; las decisiones son funciones
  Python. Ambos ofrecen run, arun, compile e inspect coherentes.
- Tools implementan operaciones; Skills agrupan capacidades; Environment
  mantiene episodios y memoria; Eval mide resultados; RunResult conserva
  eventos, relaciones de ejecución y memoria de linaje.
- Proveedor y framework se eligen por separado. native, LangGraph, OpenAI Agents
  y Strands usan el mismo contrato de resultados, conservando sus capacidades.
- 13 notebooks vigentes y 49 programas en examples, con
  `import agentic_systems as toolkit`. Los 29 notebooks históricos se identifican
  como tales y no se presentan como validados con esta API.
- Studio es una aplicación separada: Python determinista, OpenAI, Ollama y
  Bedrock API key; handoffs, checkpoint, MCP y A2A tienen ejemplos específicos.

La campaña conservada pasó 75 escenarios finales, incluidos controles Python.
Registra 238 intentos y USD 9.673028 reservados; conserva también los fallos
anteriores. El informe de RunResult y Lineage Memory incluye 313 resultados raíz
offline observados. No son 313 aplicaciones ni llamadas facturables.

El wheel aprobado es
`b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283`.
Los workflows validan ese mismo archivo en Python 3.10–3.14 y promueven los
mismos bytes a TestPyPI y después a PyPI. La publicación terminó el 23 de
octubre de 2026 UTC; no se reconstruye esta versión al mejorar su documentación.

Pendientes de entornos propios: vLLM/Colab GPU, AWS IAM y ADA IAM. No se incluye
el extra `[ada]`, ADA Studio ni wallet. La validación de los escenarios descritos
no garantiza cualquier prompt o futuras versiones de SDKs externos.

La copia preparatoria de estas notas se conserva dentro del archivo de fuentes
didácticas publicado en el repositorio. La nueva campaña no sustituye ese sello.
