# Desarrollo actual · 2.1.4.dev4

[Estados Pydantic, human_results, notebooks y matriz actual](pydantic-dev4/REPORT.md). No publicado.

Las revisiones que siguen son históricas; no certifican los nuevos bytes.

# Desarrollo acumulativo 2.1.4

Candidata local **2.1.4.dev3**, sin publicar. Solo StateGraph de LangGraph.

- [Estado más reciente para el release](release-followup/REPORT.md): Ollama
  cloud/Gemma4 pasó los tres actores; el caso nulo de Bedrock/Qwen volvió a
  fallar. 226 pruebas offline pasaron. vLLM queda pendiente por indicación del
  usuario y 2.1.4 estable no está publicada.
- [Auditoría de tutorials/examples/Studio](learning-dev3/REPORT.md): fotografía
  previa; sus cifras originales no incluyen el suplemento anterior.

- [Corrección JSON/Markdown dev3](json-markdown-fix/REPORT.md): 120 pruebas offline y dos repeticiones Bedrock/Qwen aprobadas; contador acumulado 19/20, reserva USD 0.110939. Artefacto y evidencia nuevos en json-markdown-fix/.
- Los informes y el wheel dev2 enumerados a continuación son la base histórica, conservada intacta; no certifican automáticamente dev3.

- [Campaña posterior con OpenAI y Qwen](runtime-evidence/REPORT.md): 12 celdas ejecutadas, 10 PASS y 2 FAIL de formato en Bedrock; Ollama Cloud/Qwen y vLLM pendientes. Mismo wheel, sin publicación.
- [API de usuario](../../docs/API_214.md), [firmas completas](../../docs/API_214_SURFACE.md) y [notebook mínimo](../../examples/api_214/01_api.ipynb).

- [Reporte y alcance](REPORT.md).
- [Notebook principal](../../examples/common_graph/01_common_graph.ipynb).
- [Context/Memory](../../examples/context_memory_lineage/01_context_memory_lineage.ipynb).
- [Gramática](../../docs/GRAMMAR_214.md), [contratos](../../docs/CONTRACTS_214.md) y [cobertura](../../docs/GRAMMAR_COVERAGE_214.md).
- validation.json: 84 regresiones, wheel y hashes.
- example-results.json: resultados, recursos, memoria y linaje.
- kernel-notebooks.json y capturas: kernels nuevos y guard offline.
- closeout.json: cierre con hashes de evidencia.

Dev0 y dev1 están archivadas. La campaña OpenAI de dev1 no se atribuye a dev2.
El cierre offline base añadió cero llamadas; su evidencia permanece intacta.
La campaña posterior añadió nueve llamadas al mismo contador, sin reiniciarlo:
17/20 acumuladas y USD 0.085441 de reserva conservadora.
Las rutas pendientes están en REPORT.md. El wheel local está en candidate/.
