# Gramática canónica · 2.1.4.dev8

15 funciones/constructores propios; cinco objetos originales de LangGraph
expuestos como Graph, START, END, Command y Send; más __version__.
Una sola API pública, sin check ni StateGraph como nombres alternativos.

| Palabra | Entrada → proceso → salida |
| --- | --- |
| tool | Función/esquemas Pydantic → operación → Tool con eventos |
| skill | Tools/instrucciones → capacidad → Skill |
| load_skill | Ruta confiable → carga local → Skill |
| Agent | Grafo de capacidad o runtime → ejecución → RunResult |
| System | Grafo de Agents → coordinación → RunResult |
| Environment | Grafo/records/state → episodios → outputs/history/summary |
| Eval | Unidad/casos/checks → aceptación con Memory aislada → RunResult |
| Context | Dominio/fuentes → snapshot → información contextual |
| Memory | Ejecuciones → episodios locales acotados → observaciones |
| RunResult | Evidencia → contrato serializable → human_results/lineage/trace |
| pause | Pregunta → interrupción → respuesta al reanudar |
| runtime | Proveedor/modelo/conexión/controles → configuración de ejecución |
| framework | SDK/opciones → implementación del actor |
| model_artifact | Identidad/configuración → artefacto declarado |
| model_server | Artefacto/serving → ciclo de vida explícito |
| Graph | Estado Pydantic/nodos/aristas → definición original de LangGraph |
| START / END | Extremos → conexiones → entrada/salida del grafo |
| Command / Send | Actualización/destino → control avanzado de LangGraph |

Graph define el trabajo; Agent/System/Environment.compile prepara el ejecutable;
run/arun ejecutan; human_results presenta resultados. compile valida estructura,
no corrección semántica ni efectos arbitrarios. Los constructores ya validan sus
contratos: no se necesita un segundo decorador check.

Los nodos didácticos usan funciones nombradas. Una proyección explícita llama
child.run(payload) y conserva el resultado hijo, incluso sus fallos. Tools
con input_schema reciben el modelo cuando tienen un solo parámetro de negocio.
Context se inyecta directamente en Tools y nodos, sin Runtime público.

[Uso](API_214.md) · [Firmas](API_214_SURFACE.md) ·
[Environment/rewards](ENVIRONMENT_214.md) · [Validación](STATUS_214.md).
