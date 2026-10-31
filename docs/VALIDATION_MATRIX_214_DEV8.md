# Validación online · 2.1.4.dev8

El challenge de pagos se ejecutó con cuatro rutas de runtime y tres frameworks,
usando el mismo wheel final instalado. [Informe, matriz y evidencia](../revisions/2.1.4/grammar-dev8/live-matrix/01/REPORT.md).

El perfil original con tool_choice=auto pasó 9/12 combinaciones. Un seguimiento
separado con required pasó en Bedrock/native y Bedrock/OpenAI Agents. Por tanto,
hay 11 configuraciones funcionales documentadas; la aceptación completa sigue
bloqueada por Strands + Bedrock. No se fusionan ambos perfiles como si fueran
una pasada uniforme ni se borran los fallos originales.

El adaptador Strands no traslada required al selector de Bedrock: una captura
offline del SDK real observa auto. El contrato rechaza correctamente la decisión
sin la Tool obligatoria. La corrección y la aceptación del nuevo wheel quedan
pendientes; no se modificó ni publicó el SDK durante esta campaña.

Consumo: 294/300 solicitudes (288 inferencias y seis consultas de metadatos),
USD 2.837193 de reserva conservadora sobre un máximo de USD 10. No es una factura.
Quedan seis solicitudes; el contador de la campaña anterior se conserva intacto.

La validación cubre Tools Pydantic, Skills, Agent con Graph y actores reales,
System con decisiones, Environment, Context, linaje, Memory entre episodios y
aislamiento de Eval. No acredita toda la API ni handoffs, MCP/A2A, Studio completo,
el caso previo amount:null, IAM/ADA o vLLM.
