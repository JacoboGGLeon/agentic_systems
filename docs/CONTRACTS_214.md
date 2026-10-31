# Contratos · 2.1.4.dev8

1. Una sola gramática pública: Graph, Agent/System/Environment y compile/run/arun.
   Graph es el StateGraph original de LangGraph, sin alias público StateGraph ni check.
2. Los constructores validan sus datos; compile prepara y verifica la estructura
   declarada sin ejecutar Tools, casos ni records. No prueba lógica Python arbitraria.
3. Los modelos Pydantic conservan restricciones, validadores, ausencias y null.
   No se crean defaults para satisfacer un dato faltante. El estado puede tener
   campos intermedios opcionales; el modelo de salida exige lo necesario al final.
4. Tools con input_schema y un único parámetro de negocio reciben ese modelo;
   una anotación incompatible se rechaza al declarar la Tool. Como nodo se
   proyectan los campos del esquema; output_schema valida la salida.
5. OpenAI Agents expone el contrato explícito de la Tool sin envolverlo con el
   nombre del parámetro Python. El JSON crudo se valida antes de ejecutar el
   cuerpo; no se permite coerción SDK previa que oculte el input original.
6. Context es un snapshot de dominio y fuentes, heredado sin conflictos silenciosos.
   Tools y nodos lo solicitan con *, context: toolkit.Context. Memory y lineage
   aportan observaciones separadas; el checkpoint solo guarda datos e IDs acotados.
7. RunResult conserva entrada de cada unidad, identidad, parentesco, errores,
   uso y eventos. human_results proyecta negocio con estados reales y un ID raíz;
   no elimina evidencia de to_dict/lineage/trace ni presenta resumen como status.
8. El plazo raíz se comparte y no depende de la cantidad de nodos. El scheduler
   mantiene controles del actor. Reintentos conservan intentos y consumo.
   Timeout es cooperativo, sin preempción forzosa ni rollback.
9. Pausa/reanudación conserva trabajo completado en el mismo objeto/proceso.
   El callback interrumpido puede reiniciar; los efectos requieren idempotencia.
10. Environment procesa records con observe/update/stop/state y max_steps como
    techo positivo o None. Una recompensa puede calcularse explícitamente en
    update/state/history; no existe reward= ni entrenamiento implícito de políticas.
11. Eval es fail-fast, no permite pausa y conserva fallos esperados. Cada caso
    tiene una vista privada de las Memory de toolkit; el progreso dentro de un
    Environment del caso se conserva, sin escribir en las instancias originales.
    Sesiones SDK, archivos y servicios externos no se aíslan por este mecanismo.
12. La aceptación se liga a versión, hash, fuentes y wheel no editable instalado
    fuera del checkout. Los resultados live históricos no certifican bytes nuevos.

## Selección de Tools y finalización

`policy.tool_choice` distingue `auto`, `required` y `none`. La selección del
modelo y la observación de una Tool obligatoria son controles distintos.
En Bedrock, `required` se traduce a `any`; `none` omite las definiciones y
rechaza peticiones inesperadas antes de ejecutar. No es una autorización
general sobre archivos, red u operaciones externas de una Tool.

Una respuesta vacía no se vuelve válida por serializarse como JSON. Cero,
falso y campos nulos siguen siendo valores distintos. Una Tool rechazada
por presupuesto se registra como tal, sin llamarla una respuesta vacía.
La síntesis posterior a Tools es una petición real y consume presupuesto;
un fallo conserva evidencia y no habilita un reintento implícito.

`RunResult.ok` refleja controles declarados, no verdad universal. Studio
valida la coherencia numérica de su cálculo observado; eso no certifica
todas las afirmaciones de una conversación libre.

[API](API_214.md) · [Estado](STATUS_214.md) ·
[Validación](../revisions/2.1.4/grammar-dev8/REPORT.md).
