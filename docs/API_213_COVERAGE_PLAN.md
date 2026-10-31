> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Cobertura de la API 2.1.3

La gramática ya está implementada. La [superficie completa](API_213_SURFACE.md)
relaciona cada entrada, método y campo con capítulos, ejemplos y pruebas de su
familia. El [JSON](api_213_contract.json) incluye todos los parámetros y defaults.
Esos enlaces no afirman haber probado cada valor posible o cada SDK externo.

El curso tiene once capítulos y ejemplos focalizados, además del challenge de
pedidos. Cada ejemplo muestra input → proceso → output y aserciones. Los runners
escriben evidencia vinculada al hash del wheel instalado. El registro final y
sus límites están en [el informe actual](../revisions/2.1.3/framework-evidence/REPORT.md).

| Familia | Tutorials | Examples |
|---|---|---|
| Tools y contratos de tipos | 01 | tool_contracts |
| Skills y carga portable | 01 | portable_skills |
| Agent/System, secuencia, paralelo, decisiones y ciclos | 02–03 | flow_semantics |
| Ciclo de ejecución, async y límites | 07 | execution_lifecycle |
| Episodios, memoria, parada y truncación | 04 | episode_memory |
| Checks, métricas, juez y negativo | 05,10 | evaluation_checks |
| Contratos de actor y salida estructurada | 06,10 | agent_contracts |
| Proveedores y frameworks | 06 | provider_framework_conformance |
| Resultados, JSON, eventos y linaje | 07 | results_lineage |
| Artefactos, configuración y serving | 08 | model_serving |
| Instalación, CLI y scaffolder | 00 | package_install |
| Aplicación integrada | 09 | order_fulfillment |

Las suites actuales están en tests/v213. Las pruebas anteriores siguen como
historia de 2.1.2 y no definen una capa de compatibilidad. Las referencias
históricas del catálogo mantienen versión, evidencia y estado propios; no se
promueven a ejemplos 2.1.3 por cambiar su ubicación.

El curso y las pruebas unitarias permanecen offline: Python comprueba cuatro
frameworks, los jueces usan fixtures y start/health/stop se prueba con proceso y
HTTP simulados. La campaña externa es independiente: usa los modelos y el
presupuesto registrados, sin convertir fixtures en evidencia semántica. Añade
handoffs, MCP/A2A locales reales, checkpoint y Studio. GPU, IAM y la matriz
Python/CI conservan sus límites explícitos.
