> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Decisiones aplicadas en 2.1.3

La implementación está en src/ y el build raíz. No se publica en este trabajo.
La [propuesta original](../examples/history/2.1.3/API_213_DISPOSITION_PROPOSAL.md)
y el [inventario previo](api_inventory_213/INVENTORY.md) son históricos.
La [superficie efectiva](API_213_SURFACE.md) y el [contrato JSON](api_213_contract.json)
definen la API implementada, con métodos, campos, parámetros y cobertura por familia.

| Decisión | Implementación |
|---|---|
| Un constructor por concepto | 18 exports; módulos anteriores retirados de las rutas públicas |
| Mismos flujos Agent/System | Sequence, Parallel, Graph, decisiones directas; native y StateGraph real |
| Ejecución coherente | run/arun/compile/inspect en unidades, Environment, Eval y preparados |
| Tools/Skills | Esquemas únicos, instrucciones, carga exacta con imports relativos; sin aliases, compose ni políticas sin aplicación |
| Configuración | Factories únicas, sin coerce/auto/fallback; presupuesto de actor solo en runtime |
| Opciones de SDK | Reenvío explícito en OpenAI Agents/Strands; rechazo donde el adaptador no reenvía |
| Memoria temporal | observe/update/stop, episodios nuevos, replay, truncación y evidencia de fallos |
| Evaluación | expected exacto, checks y métricas/reward, juez/rúbrica explícitos, AND y controles negativos |
| Structured output | JSON Schema portable, referencias locales, validación y evidencia del resultado inválido |
| Resultados | DTO propio, JSON único, eventos/linaje/invariantes, sin herencia pública Pydantic |
| Serving | Parámetros explícitos, vistas de endpoint, ciclo único y credenciales redactadas |
| Empaquetado | Staging limpio; se comprueba ausencia de módulos públicos retirados y shims |

metrics opcional en el resultado de un check conserva medidas como reward sin
añadir otro evaluador o modificar la gramática de Environment. Los modelos de
lenguaje, IAM y GPU no se verifican mediante fixtures. La [campaña actual](../revisions/2.1.3/framework-evidence/REPORT.md)
documenta los modelos y escenarios ejecutados; IAM y GPU siguen pendientes.
Handoffs, sesiones, hooks y otras opciones de SDK conservan su frontera específica.
Aceptar configuración no acredita su comportamiento; las pruebas nativas se
documentan con sus resultados observados.
