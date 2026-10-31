# Auditoría de bloqueos de 2.1.4.dev8

Continuación: [correcciones, pruebas y evidencia online](../revisions/2.1.4/problem-fixes/01/REPORT.md).
El análisis de abajo describe los bytes anteriores; los resultados nuevos se
registran por separado. Nulabilidad Bedrock/Qwen sigue siendo un bloqueo.

El [informe exhaustivo](../revisions/2.1.4/problem-analysis/01/REPORT.md) contiene evidencia histórica y nuevos replays offline sobre selección de Tools, nulabilidad Bedrock/Qwen, finalización Ollama y Studio.

No está listo para cierre: además de la pérdida de `required` en Strands, se demostraron traducciones incorrectas de `none`, respuesta vacía aceptada por OpenAI Agents, pérdida de evidencia de un fallo de síntesis Bedrock, validación aritmética insuficiente en Studio y un laboratorio desactualizado en su wheel.

La auditoría no modifica el SDK, no realiza inferencia y no publica. Sus siete regresiones rojas son diagnóstico explícito, no aceptación. La repetición online del caso exacto de nulabilidad y del System mixto sigue pendiente. vLLM GPU y las rutas IAM continúan pendientes de sus entornos.
